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
import time
from dataclasses import dataclass

import httpx
from PIL import Image

ENDPOINT = os.getenv("GSLG_IMAGE_ENDPOINT",
                     "https://rbx-mlp-east-us-2.openai.azure.com")
DEPLOYMENT = os.getenv("GSLG_IMAGE_DEPLOYMENT", "gpt-image-2")
API_VERSION = os.getenv("GSLG_IMAGE_API_VERSION", "2025-04-01-preview")
TOKEN_FILE = pathlib.Path(
    os.getenv("GSLG_IMAGE_TOKEN", "~/.cache/i2l/gpt-image-2-token")).expanduser()
KEY_ENV = "GPT_IMAGE_2_API_KEY"

SIZE = 1024
TIMEOUT_S = 600.0


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
                 retries: int = 3) -> Answer:
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
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
                last = exc
                if attempt < retries:
                    time.sleep(3 * attempt)
        raise ImageError(f"{type(last).__name__}: {last}")


_provider: Provider | None = None


def provider() -> Provider:
    """The shared provider, built on first use so importing costs no key lookup."""
    global _provider
    if _provider is None:
        _provider = Provider()
    return _provider


def generate(prompt: str, dest: pathlib.Path,
             references: list[pathlib.Path] | None = None) -> pathlib.Path:
    """One image, normalised and written to `dest`."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    answer = provider().generate(prompt, references)
    normalise(answer.image).save(dest, format="PNG")
    return dest
