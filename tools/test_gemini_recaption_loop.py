from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from PIL import Image

from layoutgen.backends import images

import gemini_recaption_loop


class RecaptionHelpersTests(unittest.TestCase):
    def test_read_rows_keeps_only_isometric_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "scores.jsonl"
            path.write_text(
                json.dumps({"scene": "0001", "stage": "iso", "caption": "iso"})
                + "\n"
                + json.dumps({"scene": "0001", "stage": "td", "caption": "td"})
                + "\n",
                encoding="utf-8",
            )

            rows = gemini_recaption_loop._read_rows(path)

        self.assertEqual(list(rows), ["0001"])
        self.assertEqual(rows["0001"]["caption"], "iso")

    def test_write_image_normalises_landscape_to_square(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = pathlib.Path(temporary) / "image.png"
            answer = images.Answer(Image.new("RGB", (32, 16), "blue"), "fake")

            gemini_recaption_loop._write_image(answer, destination)
            with Image.open(destination) as generated:
                size = generated.size

        self.assertEqual(size, (1024, 1024))

    def test_revision_prompt_requires_square_without_letterboxing(self) -> None:
        self.assertIn("square 1:1", gemini_recaption_loop.REVISION_PROMPT)
        self.assertIn("no black bars", gemini_recaption_loop.REVISION_PROMPT)
        self.assertIn("square 1:1", gemini_recaption_loop.TARGET_ONLY_PROMPT)


if __name__ == "__main__":
    unittest.main()
