from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from PIL import Image

from layoutgen.backends import images
from layoutgen.optimize.gepa_caption_images import (
    SEED_CANDIDATE,
    CaptionCase,
    CaptionRenderEvaluator,
    _candidate_error,
    _prompt,
    load_cases,
)
from layoutgen.optimize.similarity import SimilarityBreakdown


class FakeProvider:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(
        self,
        prompt: str,
        references: list[pathlib.Path] | None = None,
        retries: int = 8,
    ) -> images.Answer:
        del references, retries
        self.prompts.append(prompt)
        return images.Answer(Image.new("RGB", (32, 32), "blue"), "fake")


class FakeScorer:
    def compare(
        self,
        candidate: pathlib.Path,
        target: pathlib.Path,
    ) -> SimilarityBreakdown:
        self.paths = (candidate, target)
        return SimilarityBreakdown(0.75, 0.8, 0.7, 0.6)


class FakeTargets:
    def __init__(self, root: pathlib.Path) -> None:
        self.target = root / "target.png"
        Image.new("RGB", (32, 32), "red").save(self.target)

    def get(self, scene: str, stage: str) -> pathlib.Path:
        del scene
        assert stage == "iso"
        return self.target


class CaptionCaseTests(unittest.TestCase):
    def test_loads_scores_and_blind_caption_record_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "records.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "scene": "0001",
                        "stage": "iso",
                        "render_order": "std",
                        "caption": "mountain road",
                    }
                )
                + "\n"
                + json.dumps(
                    {
                        "scene": "0002",
                        "stage": "iso",
                        "render_order": "p6",
                        "blind_caption": {"summary": "castle arena"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            cases = load_cases(path)

        self.assertEqual(cases["0001"].caption, "mountain road")
        self.assertEqual(cases["0002"].caption, "castle arena")
        self.assertEqual(cases["0002"].order, "p6")

    def test_seed_template_preserves_caption_exactly(self) -> None:
        case = CaptionCase("0001", "std", "exact blind caption")
        self.assertEqual(_prompt(SEED_CANDIDATE, case), case.caption)

    def test_candidate_requires_one_caption_placeholder(self) -> None:
        self.assertIn("exactly once", _candidate_error({"caption": "no placeholder"}))
        self.assertIn(
            "exactly once",
            _candidate_error({"caption": "{caption}\n{caption}"}),
        )
        self.assertEqual(_candidate_error(SEED_CANDIDATE), "")


class CaptionEvaluatorTests(unittest.TestCase):
    def test_seed_candidate_reuses_existing_caption_render(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            seed_images = root / "seed"
            seed_images.mkdir()
            Image.new("RGB", (32, 32), "green").save(seed_images / "0001_iso.png")
            provider = FakeProvider()
            evaluator = CaptionRenderEvaluator(
                {"0001": CaptionCase("0001", "std", "a green arena")},
                provider,
                FakeScorer(),
                FakeTargets(root),
                root / "run",
                seed_images=seed_images,
                visual_feedback=False,
            )

            score, info = evaluator.evaluate(SEED_CANDIDATE, {"scene": "0001"})

        self.assertAlmostEqual(score, 0.75)
        self.assertEqual(provider.prompts, [])
        self.assertEqual(info["caption_metrics"]["score"], 0.75)

    def test_mutated_template_generates_without_target_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            provider = FakeProvider()
            evaluator = CaptionRenderEvaluator(
                {"0001": CaptionCase("0001", "std", "a mountain road")},
                provider,
                FakeScorer(),
                FakeTargets(root),
                root / "run",
                visual_feedback=False,
            )
            candidate = {"caption": "Square isometric render:\n{caption}"}

            evaluator.evaluate(candidate, {"scene": "0001"})

        self.assertEqual(
            provider.prompts,
            ["Square isometric render:\na mountain road"],
        )


if __name__ == "__main__":
    unittest.main()
