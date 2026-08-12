"""The Roblox LLM Gateway, behind the same call shape as the Azure backend.

Two things differ from Azure and both matter here.

The **auth** is a short-lived LCA token rather than a long-lived key. `sapi` cannot run
inside a devspace, so the token is minted on a laptop and pasted in through the
environment, and it expires every 12 hours. A request without a valid one is not
rejected outright - it registers as `client=None` against a shared master-key budget and
comes back "budget exceeded", which reads like a quota problem rather than an auth
problem. That failure is translated here so it says what it actually is.

The **schema enforcement** cannot be assumed. The gateway is OpenAI-shaped, but it fronts
Gemini and Claude as well as GPT, and `response_format: json_schema` is not uniformly
supported behind it. The Azure path relies on provider-side enforcement, so losing it
silently would turn a strict contract into whatever prose the model felt like. Instead
the schema is attempted, and if the gateway refuses it the call retries with the schema
inlined in the system prompt and the reply parsed here - degraded, reported, and never
silent.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import urllib.error
import urllib.request

#: Per the gateway docs. `production` is the default; the sitetests are here so a run can
#: be pointed at one without editing code.
BASES = {
    "production": "https://llm-gateway.simulprod.com/llm-gateway-internal",
    "sitetest1": "https://snc2-apis.sitetest1.simulpong.com/llm-gateway",
    "sitetest2": "https://snc2-apis.sitetest2.simulpong.com/llm-gateway",
    "sitetest3": "https://apis.sitetest3.simulpong.com/llm-gateway",
}

#: The `-a` argument to `sapi lca-token`, which differs per environment.
AUDIENCE = {"production": "rbx.prod.llm-gateway", "sitetest1": "rbx.st1.llm-gateway",
            "sitetest2": "rbx.st2.llm-gateway", "sitetest3": "rbx.st3.llm-gateway"}

ENV = os.getenv("LAYOUTGEN_GATEWAY_ENV", "production")

#: The same model the Azure backend serves, deliberately. Switching transport is a change
#: worth making on its own; switching transport *and* model at once would mean every
#: difference from the existing results has two possible causes and no way to separate
#: them. The gateway serves `gpt-5.6-terra` too, so the swap can be transport-only.
MODEL = os.getenv("LAYOUTGEN_GATEWAY_MODEL", "gpt-5.6-terra")
MAX_TOKENS = int(os.getenv("LAYOUTGEN_GATEWAY_MAX_TOKENS", "8192"))
TOKEN_FILE = pathlib.Path(
    os.getenv("LAYOUTGEN_GATEWAY_TOKEN_FILE", "~/.cache/llm-gateway-token")).expanduser()

RETRYABLE = (urllib.error.URLError, TimeoutError, KeyError, IndexError,
             json.JSONDecodeError)


class GatewayError(RuntimeError):
    """The gateway could not be reached, or refused the request."""


def base() -> str:
    if ENV not in BASES:
        raise GatewayError(f"unknown LAYOUTGEN_GATEWAY_ENV {ENV!r}; "
                           f"one of {', '.join(BASES)}")
    return BASES[ENV]


def token() -> str:
    """The LCA token, from the environment or a file.

    Deliberately not minted here: `sapi` is not available in a devspace, so a token this
    process could generate does not exist. The message therefore says how to make one
    somewhere else rather than pretending it can recover.
    """
    tok = os.getenv("LAYOUTGEN_GATEWAY_TOKEN", "").strip()
    if not tok and TOKEN_FILE.is_file():
        tok = TOKEN_FILE.read_text().strip()
    if not tok:
        raise GatewayError(
            "no LCA token. `sapi` cannot run in a devspace, so mint one on your laptop:\n"
            f"    sapi login\n"
            f"    sapi lca-token -a {AUDIENCE.get(ENV, 'rbx.prod.llm-gateway')} "
            f"| tail -n1\n"
            f"then either export LAYOUTGEN_GATEWAY_TOKEN=<token> or write it to "
            f"{TOKEN_FILE}.\nTokens expire every 12 hours.")
    return tok


def models() -> list[str]:
    """What this environment will actually serve, via `GET /v1/models`."""
    req = urllib.request.Request(
        f"{base()}/v1/models",
        headers={"Authorization": f"Bearer {token()}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    return sorted(m.get("id", "") for m in data.get("data", []))


def _post(body: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        f"{base()}/v1/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {token()}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        # An expired or absent token does not come back as 401: the request is attributed
        # to `client=None` and charged to a shared budget, so it fails as a quota error.
        # Reporting that verbatim sends the reader to the wrong problem.
        if "budget" in detail.lower():
            raise GatewayError(
                f"budget exceeded, which usually means the LCA token is missing or "
                f"expired (12h TTL) - the request was attributed to client=None and "
                f"charged to the shared master key. Re-mint with `sapi lca-token -a "
                f"{AUDIENCE.get(ENV, 'rbx.prod.llm-gateway')}`. Gateway said: {detail}"
            ) from exc
        raise GatewayError(f"HTTP {exc.code} from gateway: {detail}") from exc


def _schema_unsupported(exc: GatewayError) -> bool:
    return bool(re.search(r"response_format|json_schema|schema", str(exc), re.I))


def ask(system: str, user: str | list[dict], schema: dict, *, retries: int = 3,
        timeout: int = 300, model: str | None = None) -> tuple[dict, bool]:
    """One question, answered as JSON matching `schema`.

    Returns the answer and whether the schema had to be enforced here rather than by the
    provider, so a caller that cares about the strength of its contract can tell.
    """
    name = model or MODEL
    # Resolved once, outside the retry loop: a token that is absent or an environment
    # that is misspelled will not become valid by asking again, and three rounds of it
    # buries the message that says what to do.
    base(), token()
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    strict = {"model": name, "messages": messages, "max_tokens": MAX_TOKENS,
              "response_format": {"type": "json_schema", "json_schema": schema}}

    last: Exception | None = None
    for _ in range(retries):
        try:
            data = _post(strict, timeout)
            return json.loads(data["choices"][0]["message"]["content"]), False
        except GatewayError as exc:
            if _schema_unsupported(exc):
                last = exc
                break                      # no point retrying an unsupported feature
            last = exc
        except RETRYABLE as exc:
            last = exc

    # Fallback: the gateway would not enforce the schema, so state it in the prompt and
    # enforce it here. Weaker, and the caller is told so.
    inlined = (f"{system}\n\n# Output format (STRICT)\n\nReturn one JSON object and "
               f"nothing else - no prose, no code fence - matching this JSON schema "
               f"exactly:\n\n{json.dumps(schema.get('schema', schema))}")
    loose = {"model": name, "messages": [{"role": "system", "content": inlined},
                                         {"role": "user", "content": user}],
             "max_tokens": MAX_TOKENS}
    for _ in range(retries):
        try:
            data = _post(loose, timeout)
            return _parse(data["choices"][0]["message"]["content"]), True
        except (GatewayError, *RETRYABLE) as exc:
            last = exc
    raise GatewayError(f"call failed after {retries} tries: {last}")


def _parse(text: str) -> dict:
    """The first JSON object in a reply that was asked for JSON and nothing else."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, depth = text.find("{"), 0
        if start == -1:
            raise
        for i, ch in enumerate(text[start:], start):
            depth += (ch == "{") - (ch == "}")
            if depth == 0:
                return json.loads(text[start:i + 1])
        raise
