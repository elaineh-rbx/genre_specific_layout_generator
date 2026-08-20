from __future__ import annotations

import unittest

from PIL import Image

import gemini_contract_repair_pilot


class FrameValidationTests(unittest.TestCase):
    def test_rejects_landscape_output(self) -> None:
        errors = gemini_contract_repair_pilot._frame_errors(
            Image.new("RGB", (32, 16), "white")
        )
        self.assertTrue(any("not square" in error for error in errors))

    def test_rejects_black_letterbox_bands(self) -> None:
        image = Image.new("RGB", (32, 32), "white")
        for y in (0, 1, 30, 31):
            for x in range(32):
                image.putpixel((x, y), (0, 0, 0))

        errors = gemini_contract_repair_pilot._frame_errors(image)

        self.assertIn("solid black top letterbox band", errors)
        self.assertIn("solid black bottom letterbox band", errors)

    def test_accepts_square_full_bleed_output(self) -> None:
        self.assertEqual(
            gemini_contract_repair_pilot._frame_errors(
                Image.new("RGB", (32, 32), "green")
            ),
            [],
        )


class ReviewScoreTests(unittest.TestCase):
    def test_weights_contract_above_camera(self) -> None:
        score = gemini_contract_repair_pilot._review_score(
            {"contract_adherence": 0.75, "camera_and_framing": 0.5}
        )
        self.assertAlmostEqual(score, 0.7)

    def test_clamps_scores_to_unit_interval(self) -> None:
        score = gemini_contract_repair_pilot._review_score(
            {"contract_adherence": 2, "camera_and_framing": -1}
        )
        self.assertAlmostEqual(score, 0.8)


if __name__ == "__main__":
    unittest.main()
