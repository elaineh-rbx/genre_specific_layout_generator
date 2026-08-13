"""The text and vision model, behind one call.

Routing a prompt to a genre and judging whether a feature is visible in a render are
different jobs, but they are the same request: a system prompt, a user turn that may
carry images, and a strict JSON schema for the answer. Four copies of this call had
drifted apart in the original scratch tree - different retry counts, different error
handling - which made a failure mean different things depending on which one you hit.
"""

from __future__ import annotations

import base64
import json
import os
import pathlib
import threading
import urllib.error
import urllib.request

ENDPOINT = os.getenv("LAYOUTGEN_LLM_ENDPOINT", "https://rbx-mlp-east-us-2.openai.azure.com")
DEPLOYMENT = os.getenv("LAYOUTGEN_LLM_DEPLOYMENT", "gpt-5.6-terra")
API_VERSION = os.getenv("LAYOUTGEN_LLM_API_VERSION", "2024-12-01-preview")
TOKEN_FILE = pathlib.Path(
    os.getenv("LAYOUTGEN_LLM_TOKEN", "~/.cache/i2l/gpt-image-2-token")).expanduser()

#: This deployment rejects `temperature` and `top_p` - only the default temperature of
#: 1 is allowed - so sampling cannot be turned off directly. It does accept `seed`, and
#: empirically that is enough: a prompt that gave four different option sets in four
#: runs gives one. Reproducibility is best-effort on the provider's side rather than
#: guaranteed, so treat a repeat that differs as possible, not as a bug.
SEED = 7

RETRYABLE = (urllib.error.URLError, urllib.error.HTTPError, KeyError,
             json.JSONDecodeError, TimeoutError, IndexError)


class LLMError(RuntimeError):
    """The model could not be reached, or did not answer in the shape asked for."""


def api_key() -> str:
    key = os.getenv("LAYOUTGEN_LLM_KEY") or _read(TOKEN_FILE)
    if not key:
        raise LLMError(f"no key: set LAYOUTGEN_LLM_KEY or write one to {TOKEN_FILE}")
    return key


def _read(path: pathlib.Path) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def image_part(path: pathlib.Path) -> dict:
    """One image, inline, as a user-turn content part."""
    data = base64.b64encode(pathlib.Path(path).read_bytes()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}}


def text_part(text: str) -> dict:
    return {"type": "text", "text": text}


#: Which service `ask` talks to. The LLM Gateway is the supported path and the default;
#: Azure is kept because the older results in `results/` were produced through it, and a
#: comparison between two arms means nothing if what answered them changed unrecorded.
#:
#: Both serve `gpt-5.6-terra`, so the default swap is transport-only - deliberately, since
#: changing transport and model together would leave every difference with two possible
#: causes. `tools/run_blob_pipeline.py` folds whichever answered into its version hash.
PROVIDER = os.getenv("LAYOUTGEN_LLM_PROVIDER", "gateway").strip().lower()

#: Set by the last `ask` when the provider would not enforce the schema and it had to be
#: enforced locally. Worth checking after a batch: a run of loosely-enforced answers is
#: not the same contract as a run of strict ones.
degraded_calls = 0
_call = threading.local()


def schema_degraded() -> bool:
    """Whether this thread's most recent call used local schema enforcement."""
    return bool(getattr(_call, "degraded", False))


def served_by() -> str:
    """Which service and model would answer right now, for a record to store.

    Both providers serve the same model, so the difference is transport - but a result
    set half-answered through one and half through the other is not one set, and nothing
    else on disk would say which record came from where.
    """
    if PROVIDER == "gateway":
        from layoutgen.backends import gateway
        return f"gateway/{gateway.ENV}/{gateway.MODEL}"
    return f"azure/{DEPLOYMENT}"


def ask(system: str, user: str | list[dict], schema: dict, *, retries: int = 3,
        timeout: int = 300) -> dict:
    """One question, answered as JSON matching `schema`.

    `user` is either a string or a list of content parts, which is how images are
    attached. The schema is enforced by the provider rather than parsed out of prose,
    so a malformed answer is a transport failure and worth retrying.
    """
    if PROVIDER == "gateway":
        global degraded_calls
        from layoutgen.backends import gateway
        out, degraded = gateway.ask(system, user, schema, retries=retries,
                                    timeout=timeout)
        _call.degraded = degraded
        if degraded:
            degraded_calls += 1
        return out
    if PROVIDER != "azure":
        raise LLMError(f"unknown LAYOUTGEN_LLM_PROVIDER {PROVIDER!r}: "
                       f"expected 'gateway' or 'azure'")
    body = {"messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "response_format": {"type": "json_schema", "json_schema": schema},
            "seed": SEED}
    _call.degraded = False
    url = (f"{ENDPOINT.rstrip('/')}/openai/deployments/{DEPLOYMENT}/chat/completions"
           f"?api-version={API_VERSION}")
    last: Exception | None = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(
                url, data=json.dumps(body).encode(),
                headers={"api-key": api_key(), "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.load(resp)
            return json.loads(data["choices"][0]["message"]["content"])
        except RETRYABLE as exc:
            last = exc
    raise LLMError(f"call failed after {retries} tries: {last}")
