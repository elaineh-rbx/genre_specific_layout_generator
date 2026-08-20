from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

import gemini_caption_to_image


class CaptionPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = {
            "blind_caption": {
                "summary": "A voxel mountain with one winding road.",
                "camera": {"view": "elevated-oblique"},
            }
        }

    def test_summary_mode_uses_only_blind_summary(self) -> None:
        self.assertEqual(
            gemini_caption_to_image._caption_prompt(self.record, "summary"),
            "A voxel mountain with one winding road.",
        )

    def test_structured_mode_preserves_caption_details(self) -> None:
        prompt = gemini_caption_to_image._caption_prompt(self.record, "structured")
        self.assertEqual(json.loads(prompt), self.record["blind_caption"])


class RecordTests(unittest.TestCase):
    def test_read_records_preserves_both_stages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "records.jsonl"
            path.write_text(
                '{"scene":"0001","stage":"iso"}\n'
                '{"scene":"0001","stage":"td"}\n',
                encoding="utf-8",
            )
            rows = gemini_caption_to_image._read_records(path)

        self.assertEqual([row["stage"] for row in rows], ["iso", "td"])


if __name__ == "__main__":
    unittest.main()
