from __future__ import annotations

import base64
import io
import pathlib
import tempfile
import unittest
from unittest import mock

import httpx
from PIL import Image

from layoutgen.backends import images


def _encoded_image() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), "blue").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


class LLMGatewayImageProviderTest(unittest.TestCase):
    def test_gateway_sends_reference_and_image_modalities(self) -> None:
        sent: dict = {}
        uri = f"data:image/png;base64,{_encoded_image()}"

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def post(self, url, *, json, headers):
                sent.update(url=url, body=json, headers=headers)
                return httpx.Response(
                    200,
                    json={
                        "choices": [
                            {
                                "message": {
                                    "content": "",
                                    "images": [{"image_url": {"url": uri}}],
                                }
                            }
                        ]
                    },
                    request=httpx.Request("POST", url),
                )

        with tempfile.TemporaryDirectory() as temporary:
            reference = pathlib.Path(temporary) / "reference.png"
            Image.new("RGB", (8, 8), "red").save(reference)
            with (
                mock.patch.object(images.httpx, "Client", FakeClient),
                mock.patch.object(images.llm_gateway, "base", return_value="https://llm.test"),
                mock.patch.object(images.llm_gateway, "token", return_value="token"),
            ):
                answer = images.LLMGatewayProvider().generate(
                    "draw this scene", [reference]
                )

        self.assertEqual(answer.model, "gemini-3.1-flash-image")
        self.assertEqual(answer.image.size, (16, 16))
        self.assertTrue(sent["url"].endswith("/v1/chat/completions"))
        self.assertEqual(sent["body"]["modalities"], ["text", "image"])
        content = sent["body"]["messages"][0]["content"]
        self.assertEqual(content[0], {"type": "text", "text": "draw this scene"})
        self.assertTrue(content[1]["image_url"]["url"].startswith("data:image/png;base64,"))

    def test_gateway_retries_text_only_response(self) -> None:
        uri = f"data:image/png;base64,{_encoded_image()}"
        calls = 0

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def post(self, url, *, json, headers):
                nonlocal calls
                calls += 1
                images_payload = [] if calls == 1 else [
                    {"image_url": {"url": uri}}
                ]
                return httpx.Response(
                    200,
                    json={
                        "choices": [
                            {
                                "message": {
                                    "content": "Generated the requested image.",
                                    "images": images_payload,
                                }
                            }
                        ]
                    },
                    request=httpx.Request("POST", url),
                )

        with (
            mock.patch.object(images.httpx, "Client", FakeClient),
            mock.patch.object(images.llm_gateway, "base", return_value="https://llm.test"),
            mock.patch.object(images.llm_gateway, "token", return_value="token"),
            mock.patch.object(images.time, "sleep"),
        ):
            answer = images.LLMGatewayProvider().generate(
                "draw this scene", retries=2
            )

        self.assertEqual(calls, 2)
        self.assertEqual(answer.image.size, (16, 16))


if __name__ == "__main__":
    unittest.main()
