from __future__ import annotations

import json
import pathlib
import tempfile
import unittest
from unittest import mock

from PIL import Image

import gemini_caption_gap


class JsonObjectTests(unittest.TestCase):
    def test_parses_fenced_json(self) -> None:
        self.assertEqual(
            gemini_caption_gap._json_object('```json\n{"summary": "arena"}\n```'),
            {"summary": "arena"},
        )

    def test_extracts_json_from_wrapping_prose(self) -> None:
        self.assertEqual(
            gemini_caption_gap._json_object('Result:\n{"summary": "track"}\nDone.'),
            {"summary": "track"},
        )

    def test_repairs_trailing_commas(self) -> None:
        self.assertEqual(
            gemini_caption_gap._json_object(
                '{"summary": "arena", "objects": ["tower",],}'
            ),
            {"summary": "arena", "objects": ["tower"]},
        )

    def test_recovers_summary_when_later_fields_are_malformed(self) -> None:
        self.assertEqual(
            gemini_caption_gap._json_object(
                '{"summary": "arena with two towers", "objects": ["bad" "json"]}'
            ),
            {"summary": "arena with two towers"},
        )


class MessageTextTests(unittest.TestCase):
    def test_accepts_openai_string_content(self) -> None:
        self.assertEqual(
            gemini_caption_gap._message_text({"content": '{"ok": true}'}),
            '{"ok": true}',
        )

    def test_accepts_multimodal_text_parts(self) -> None:
        message = {
            "content": [
                {"type": "text", "text": '{"ok":'},
                {"type": "text", "text": "true}"},
            ]
        }
        self.assertEqual(gemini_caption_gap._message_text(message), '{"ok":\ntrue}')


class GeminiCaptionerTests(unittest.TestCase):
    def test_ask_attaches_multiple_images_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            target, candidate = root / "target.png", root / "candidate.png"
            Image.new("RGB", (8, 8), "red").save(target)
            Image.new("RGB", (8, 8), "blue").save(candidate)
            response = mock.Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "choices": [{"message": {"content": '{"summary":"revised"}'}}]
            }
            client = mock.MagicMock()
            client.__enter__.return_value = client
            client.post.return_value = response

            with (
                mock.patch.object(
                    gemini_caption_gap.httpx,
                    "Client",
                    return_value=client,
                ),
                mock.patch.object(
                    gemini_caption_gap.gateway,
                    "base",
                    return_value="https://gateway.example",
                ),
                mock.patch.object(
                    gemini_caption_gap.gateway,
                    "token",
                    return_value="token",
                ),
            ):
                result = gemini_caption_gap.GeminiCaptioner().ask(
                    "compare",
                    [target, candidate],
                )

        content = client.post.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertEqual(result, {"summary": "revised"})
        self.assertEqual([part["type"] for part in content], [
            "text",
            "image_url",
            "image_url",
        ])


class LoadCasesTests(unittest.TestCase):
    def test_jsonl_rows_preserve_multiple_stages_for_one_scene(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "records.jsonl"
            path.write_text(
                '{"scene":"0001","stage":"iso"}\n'
                '{"scene":"0001","stage":"td"}\n',
                encoding="utf-8",
            )
            rows = gemini_caption_gap._read_jsonl_rows(path)

        self.assertEqual([row["stage"] for row in rows], ["iso", "td"])

    def test_resolves_all_75_numeric_golden_scenes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "prompts.jsonl"
            rows = [{"scene": f"{scene:04d}"} for scene in range(1, 76)]
            rows.extend(({"scene": "candidate-1"}, {"scene": "0076"}))
            path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )

            scenes = gemini_caption_gap._numeric_golden_scenes(path)

        self.assertEqual(len(scenes), 75)
        self.assertEqual((scenes[0], scenes[-1]), ("0001", "0075"))

    def test_resolves_stage_prompts_and_images(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest = root / "prompts.jsonl"
            manifest.write_text(
                json.dumps(
                    {
                        "scene": "0001",
                        "render_order": "p6",
                        "image_model": "gpt-image-2",
                        "isometric": {"prompt": "ISO CONTRACT"},
                        "topdown": {"prompt": "TOPDOWN CONTRACT"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            iso = root / "iso.png"
            topdown = root / "td.png"
            Image.new("RGB", (8, 8), "blue").save(iso)
            Image.new("RGB", (8, 8), "green").save(topdown)

            def fetch(relative: str) -> pathlib.Path:
                return iso if "/iso/" in relative else topdown

            with mock.patch.object(gemini_caption_gap.assets, "fetch", side_effect=fetch):
                cases = gemini_caption_gap._load_cases(
                    manifest,
                    "target-arm",
                    ["0001"],
                    ["iso", "td"],
                )

        self.assertEqual([case.expected_prompt for case in cases], [
            "ISO CONTRACT",
            "TOPDOWN CONTRACT",
        ])
        self.assertEqual([case.image for case in cases], [iso, topdown])
        self.assertEqual({case.render_order for case in cases}, {"p6"})


if __name__ == "__main__":
    unittest.main()
