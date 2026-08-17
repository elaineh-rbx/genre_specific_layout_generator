"""The image backend: one Azure deployment, generation and reference-conditioned edits.

Every image in this project is made by the same call, differing only in the prompt and
in whether a reference image is attached. Generation with a reference is what makes the
pipeline's stages hold together - the top-down is an edit of the isometric, the
isometric is an edit of the top-down, and a layout-first scene is an edit of a
blueprint this repo drew itself.

Output is always square and always the same size, because the stages feed each other
and a size change between them shows up as a crop or a letterbox.
"""

from __future__ import annotations

import os
import pathlib
import random
import time
from dataclasses import dataclass

import httpx
from PIL import Image

from layoutgen.backends import gateway as llm_gateway

ENDPOINT = os.getenv("LAYOUTGEN_IMAGE_ENDPOINT",
                     "https://rbx-mlp-east-us-2.openai.azure.com")
DEPLOYMENT = os.getenv("LAYOUTGEN_IMAGE_DEPLOYMENT", "gpt-image-2")
BACKEND = os.getenv("LAYOUTGEN_IMAGE_BACKEND", "azure").strip().lower()
GATEWAY_MODEL = os.getenv(
    "LAYOUTGEN_IMAGE_MODEL", "gemini-3.1-flash-image"
).strip()
API_VERSION = os.getenv("LAYOUTGEN_IMAGE_API_VERSION", "2025-04-01-preview")
TOKEN_FILE = pathlib.Path(
    os.getenv("LAYOUTGEN_IMAGE_TOKEN", "~/.cache/i2l/gpt-image-2-token")).expanduser()
KEY_ENV = "GPT_IMAGE_2_API_KEY"

SIZE = 1024
TIMEOUT_S = 600.0

#: Statuses worth offering again. A 429 is the deployment admitting work more slowly than
#: we are handing it over, which says nothing about the request; the 5xx family is
#: transient by definition. Everything else - a 400 for a prompt the content filter
#: refuses, a 401 for a stale key - is permanent, and trying it twice more only delays
#: the report by the length of the backoff.
RETRYABLE = {408, 409, 429, 500, 502, 503, 504}


def _hold(response: httpx.Response | None, attempt: int) -> float:
    """How long to wait before offering a rejected request again.

    This deployment answers a 429 with `Retry-After: 4`, and taking it at its word beats
    guessing in both directions. The rejection itself arrives in about a fifth of a
    second, so a worker that waits the four seconds it was asked for has still spent an
    order of magnitude less than the generation it is queueing for - which is what makes
    it safe to run more workers than the limiter will admit at once. The exponential
    fallback is only for a limiter that declines to say.

    The jitter matters more than its size: without it, every worker rejected in the same
    burst comes back in the same instant and rebuilds the burst it was throttled for.
    """
    hinted = response.headers.get("retry-after") if response is not None else None
    if hinted:
        try:
            return min(float(hinted) + random.uniform(0, 0.5), 60.0)
        except ValueError:
            pass
    return min(2**attempt + random.uniform(0, 1), 60.0)


class ImageError(RuntimeError):
    """The backend could not produce an image."""


@dataclass
class Answer:
    image: Image.Image
    model: str


def api_key() -> str:
    key = os.getenv(KEY_ENV) or _read(TOKEN_FILE)
    if not key:
        raise ImageError(f"no image key: set {KEY_ENV} or write one to {TOKEN_FILE}")
    return key


def _read(path: pathlib.Path) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def normalise(image: Image.Image, size: int = SIZE) -> Image.Image:
    """Pad to square, then resize, so every stage hands on the same frame.

    Padding before resizing rather than scaling to fit keeps the aspect ratio, which
    matters when the next stage is an edit of this image: a stretched reference bends
    the geometry the edit is supposed to preserve.
    """
    img = image.convert("RGB")
    w, h = img.size
    if w != h:
        side = max(w, h)
        square = Image.new("RGB", (side, side), (0, 0, 0))
        square.paste(img, ((side - w) // 2, (side - h) // 2))
        img = square
    return img if img.size == (size, size) else img.resize((size, size), Image.LANCZOS)


class Provider:
    """One Azure image deployment, called for both generations and edits."""

    def __init__(self, size: int = SIZE, quality: str = "auto",
                 deployment: str = DEPLOYMENT):
        self.size, self.quality, self.model = size, quality, deployment
        self._key = api_key()

    def generate(self, prompt: str, references: list[pathlib.Path] | None = None,
                 retries: int = 8) -> Answer:
        import base64
        import io

        op = "edits" if references else "generations"
        url = (f"{ENDPOINT.rstrip('/')}/openai/deployments/{self.model}/images/{op}"
               f"?api-version={API_VERSION}")
        size = f"{self.size}x{self.size}"
        last: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                with httpx.Client(timeout=TIMEOUT_S) as client:
                    if references:
                        files = [("image[]", (p.name, p.read_bytes(), "image/png"))
                                 for p in references]
                        r = client.post(url, headers={"api-key": self._key},
                                        data={"prompt": prompt, "n": "1",
                                              "size": size, "quality": self.quality},
                                        files=files)
                    else:
                        r = client.post(url, headers={"api-key": self._key},
                                        json={"prompt": prompt, "n": 1,
                                              "size": size, "quality": self.quality})
                    r.raise_for_status()
                    payload = r.json()
                    out = (payload.get("data") or [{}])[0]
                    if out.get("b64_json"):
                        blob = base64.b64decode(out["b64_json"])
                    elif out.get("url"):
                        blob = client.get(out["url"]).content
                    else:
                        raise ImageError(f"{self.model} returned no image")
                with Image.open(io.BytesIO(blob)) as im:
                    return Answer(im.convert("RGB").copy(), self.model)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in RETRYABLE:
                    raise ImageError(f"HTTP {exc.response.status_code}: "
                                     f"{exc.response.text[:200]}") from exc
                last = exc
                if attempt < retries:
                    time.sleep(_hold(exc.response, attempt))
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
                last = exc
                if attempt < retries:
                    time.sleep(_hold(None, attempt))
        raise ImageError(f"gave up after {retries} attempts, "
                         f"{type(last).__name__}: {last}")


class LLMGatewayProvider:
    """Gemini image generation through the Gateway's OpenAI-compatible chat route."""

    def __init__(self, size: int = SIZE, model: str = GATEWAY_MODEL):
        self.size, self.model = size, model

    @staticmethod
    def _part(path: pathlib.Path) -> dict:
        import base64

        mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{data}"},
        }

    @staticmethod
    def _decode(raw: str) -> Image.Image:
        import base64
        import io

        payload = raw.partition(",")[2] if raw.startswith("data:") else raw
        with Image.open(io.BytesIO(base64.b64decode(payload))) as image:
            return image.convert("RGB").copy()

    def generate(self, prompt: str, references: list[pathlib.Path] | None = None,
                 retries: int = 8) -> Answer:
        # Gemini's native image-editing examples put the instruction before the image.
        # Preserve that ordering through the OpenAI-compatible Gateway route: camera and
        # exclusion rules must be established before the model conditions on a plan.
        content = [{"type": "text", "text": prompt}]
        content.extend(self._part(path) for path in references or [])
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "modalities": ["text", "image"],
        }
        url = f"{llm_gateway.base().rstrip('/')}/v1/chat/completions"
        last: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                with httpx.Client(timeout=TIMEOUT_S) as client:
                    response = client.post(
                        url,
                        json=body,
                        headers={
                            "Authorization": f"Bearer {llm_gateway.token()}",
                            "Content-Type": "application/json",
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                choices = data.get("choices") or []
                message = choices[0].get("message") or {} if choices else {}
                image_data = ""
                for item in message.get("images") or []:
                    image_url = item.get("image_url") if isinstance(item, dict) else item
                    image_data = (
                        image_url.get("url", "")
                        if isinstance(image_url, dict)
                        else str(image_url or "")
                    )
                    if image_data:
                        break
                if not image_data:
                    last = ImageError(f"{self.model} returned text but no image")
                    if attempt < retries:
                        time.sleep(_hold(None, attempt))
                        continue
                    raise last
                return Answer(self._decode(image_data), self.model)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in RETRYABLE:
                    raise ImageError(
                        f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
                    ) from exc
                last = exc
                if attempt < retries:
                    time.sleep(_hold(exc.response, attempt))
            except (httpx.HTTPError, KeyError, IndexError, ValueError, OSError) as exc:
                last = exc
                if attempt < retries:
                    time.sleep(_hold(None, attempt))
        raise ImageError(
            f"gave up after {retries} attempts, {type(last).__name__}: {last}"
        )


_provider: Provider | LLMGatewayProvider | None = None


def model_name() -> str:
    """The image model selected for this process."""
    return GATEWAY_MODEL if BACKEND == "llm-gateway" else DEPLOYMENT


def provider() -> Provider | LLMGatewayProvider:
    """The shared provider, built on first use so importing costs no key lookup."""
    global _provider
    if _provider is None:
        if BACKEND == "azure":
            _provider = Provider()
        elif BACKEND == "llm-gateway":
            _provider = LLMGatewayProvider()
        else:
            raise ImageError(
                f"unknown LAYOUTGEN_IMAGE_BACKEND {BACKEND!r}; use azure or llm-gateway"
            )
    return _provider


def generate(prompt: str, dest: pathlib.Path,
             references: list[pathlib.Path] | None = None) -> pathlib.Path:
    """One image, normalised and written to `dest`.

    Saved beside the destination and moved into place, because the runners take an
    existing file to be a finished one and skip it. A process killed mid-save otherwise
    leaves a partial PNG that every later resume steps over as done - and which surfaces
    much later as an unreadable reference to the stage built from it, or on a stage
    nothing else reads, not at all.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    answer = provider().generate(prompt, references)
    tmp = dest.with_suffix(f".part{os.getpid()}")
    try:
        normalise(answer.image).save(tmp, format="PNG")
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)
    return dest
