from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from PIL import Image

from layoutgen.backends import images
from layoutgen.optimize.gepa_prompt_recaption import (
    SEED_CANDIDATE,
    PromptCase,
    PromptRecaptionEvaluator,
    _candidate_error,
    _generation_prompt,
    _json_object,
    load_cases,
)
from layoutgen.optimize.similarity import SimilarityBreakdown


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[pathlib.Path]]] = []

    def generate(
        self,
        prompt: str,
        references: list[pathlib.Path] | None = None,
        retries: int = 8,
    ) -> images.Answer:
        del retries
        self.calls.append((prompt, list(references or [])))
        return images.Answer(Image.new("RGB", (32, 32), "blue"), "fake")


class FakeCaptioner:
    def caption(self, image: pathlib.Path) -> dict:
        self.image = image
        return {"summary": "blue square arena"}


class FakeScorer:
    def compare(
        self,
        candidate: pathlib.Path,
        target: pathlib.Path,
    ) -> SimilarityBreakdown:
        del candidate, target
        return SimilarityBreakdown(0.7, 0.8, 0.6, 0.5)


class FakeTargets:
    def __init__(self, root: pathlib.Path) -> None:
        self.path = root / "target.png"
        Image.new("RGB", (32, 32), "red").save(self.path)

    def get(self, scene: str, stage: str) -> pathlib.Path:
        del scene
        assert stage == "iso"
        return self.path


class PromptCaseTests(unittest.TestCase):
    def test_loads_only_self_contained_selected_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            prompts = root / "prompts.jsonl"
            captions = root / "captions.jsonl"
            prompts.write_text(
                json.dumps(
                    {
                        "scene": "0001",
                        "render_order": "std",
                        "isometric": {"prompt": "EXACT GPT", "reference": None},
                    }
                )
                + "\n"
                + json.dumps(
                    {
                        "scene": "0002",
                        "render_order": "p6",
                        "isometric": {"prompt": "NEEDS PLAN", "reference": "topdown"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            captions.write_text(
                json.dumps(
                    {
                        "scene": "0001",
                        "stage": "iso",
                        "blind_caption": {"summary": "target"},
                    }
                )
                + "\n"
                + json.dumps(
                    {
                        "scene": "0002",
                        "stage": "iso",
                        "blind_caption": {"summary": "other"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            cases = load_cases(prompts, captions, {"std", "p6"})

        self.assertEqual(list(cases), ["0001"])
        self.assertEqual(cases["0001"].prompt, "EXACT GPT")

    def test_seed_adapter_is_exact_gpt_prompt(self) -> None:
        case = PromptCase("0001", "std", "EXACT GPT PROMPT", {"summary": "target"})
        self.assertEqual(_generation_prompt(SEED_CANDIDATE, case), case.prompt)

    def test_adapter_requires_exactly_one_prompt_placeholder(self) -> None:
        self.assertIn("exactly once", _candidate_error({"adapter": "missing"}))
        self.assertEqual(_candidate_error(SEED_CANDIDATE), "")

    def test_json_object_repairs_fenced_trailing_comma(self) -> None:
        self.assertEqual(
            _json_object('```json\n{"summary":"arena",}\n```'),
            {"summary": "arena"},
        )


class PromptEvaluatorTests(unittest.TestCase):
    def test_generates_without_target_reference_and_returns_caption_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            provider = FakeProvider()
            captioner = FakeCaptioner()
            case = PromptCase(
                "0001",
                "std",
                "EXACT GPT PROMPT",
                {"summary": "red target arena"},
            )
            evaluator = PromptRecaptionEvaluator(
                {"0001": case},
                provider,
                captioner,
                FakeScorer(),
                FakeTargets(root),
                root / "run",
                visual_feedback=False,
            )

            score, info = evaluator.evaluate(SEED_CANDIDATE, {"scene": "0001"})

        self.assertAlmostEqual(score, 0.7)
        self.assertEqual(provider.calls, [("EXACT GPT PROMPT", [])])
        self.assertEqual(
            info["Gemini caption of candidate"],
            {"summary": "blue square arena"},
        )
        self.assertEqual(
            info["Frozen Gemini caption of GPT target"],
            {"summary": "red target arena"},
        )


if __name__ == "__main__":
    unittest.main()
