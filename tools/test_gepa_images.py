from __future__ import annotations

import pathlib
import tempfile
import unittest
from unittest import mock

import httpx
import numpy as np
from PIL import Image

from layoutgen.backends import images
from layoutgen.optimize import gepa_images
from layoutgen.optimize.gepa_images import (
    GatewayReflectionLM,
    RenderEvaluator,
    SEED_CANDIDATE,
    SceneCase,
    WeakestActiveStageSelector,
    _split_all_75,
)
from layoutgen.optimize.similarity import (
    CompositeImageSimilarity,
    DinoFeatures,
    SimilarityBreakdown,
)


class FixedEncoder:
    def encode(self, path: pathlib.Path) -> DinoFeatures:
        del path
        return DinoFeatures(
            semantic=np.asarray([1.0, 0.0], dtype=np.float32),
            spatial=np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        )


class FixedScorer:
    def compare(
        self,
        candidate: pathlib.Path,
        target: pathlib.Path,
    ) -> SimilarityBreakdown:
        del candidate, target
        return SimilarityBreakdown(0.8, 0.9, 0.8, 0.7)


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
        colour = "blue" if len(self.calls) == 1 else "green"
        return images.Answer(Image.new("RGB", (32, 32), colour), "fake-gemini")


class FakeTargets:
    def __init__(self, root: pathlib.Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        for stage, colour in (("iso", "red"), ("td", "yellow")):
            target = root / f"{stage}.png"
            Image.new("RGB", (32, 32), colour).save(target)

    def get(self, scene: str, stage: str) -> pathlib.Path:
        del scene
        return self.root / f"{stage}.png"


class SimilarityTests(unittest.TestCase):
    def test_identical_images_receive_perfect_score(self) -> None:
        scorer = CompositeImageSimilarity(encoder=FixedEncoder())
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "same.png"
            Image.new("RGB", (64, 64), "purple").save(path)
            score = scorer.compare(path, path)

        self.assertAlmostEqual(score.score, 1.0, places=6)
        self.assertAlmostEqual(score.structure, 1.0, places=6)

    def test_structure_signal_distinguishes_different_images(self) -> None:
        scorer = CompositeImageSimilarity(encoder=FixedEncoder())
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            black, white = root / "black.png", root / "white.png"
            Image.new("RGB", (64, 64), "black").save(black)
            Image.new("RGB", (64, 64), "white").save(white)
            different = scorer.compare(black, white)
            identical = scorer.compare(black, black)

        self.assertLess(different.score, identical.score)


class RenderEvaluatorTests(unittest.TestCase):
    def test_standard_order_never_passes_gpt_target_to_gemini(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            provider = FakeProvider()
            targets = FakeTargets(root / "targets")
            case = SceneCase(
                scene="0001",
                order="std",
                iso_prompt="EXACT ISO CONTRACT",
                first_prompt="EXACT TOPDOWN CONTRACT",
                addendum="",
                spec={},
            )
            evaluator = RenderEvaluator(
                {"0001": case},
                provider,
                FixedScorer(),
                targets,
                root / "run",
                visual_feedback=False,
            )
            score, info = evaluator.evaluate(SEED_CANDIDATE, {"scene": "0001"})

            target_paths = {targets.get("0001", stage) for stage in ("iso", "td")}
            references = [path for _, refs in provider.calls for path in refs]

        self.assertAlmostEqual(score, 0.8)
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(provider.calls[0][1], [])
        self.assertEqual(len(provider.calls[1][1]), 1)
        self.assertTrue(target_paths.isdisjoint(references))
        self.assertIn("EXACT ISO CONTRACT", provider.calls[0][0])
        self.assertIn("EXACT TOPDOWN CONTRACT", provider.calls[1][0])
        self.assertEqual(info["scores"]["isometric_similarity"], 0.8)

    def test_layout_order_uses_deterministic_plan_then_generated_topdown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            provider = FakeProvider()
            targets = FakeTargets(root / "targets")
            case = SceneCase(
                scene="0022",
                order="layout",
                iso_prompt="ISO",
                first_prompt="TOPDOWN",
                addendum="",
                spec={"kind": "track"},
            )

            def plan_builder(scene: SceneCase, destination: pathlib.Path) -> pathlib.Path:
                self.assertEqual(scene.scene, "0022")
                destination.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (32, 32), "gray").save(destination)
                return destination

            evaluator = RenderEvaluator(
                {"0022": case},
                provider,
                FixedScorer(),
                targets,
                root / "run",
                visual_feedback=False,
                plan_builder=plan_builder,
            )
            evaluator.evaluate(SEED_CANDIDATE, {"scene": "0022"})

        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(provider.calls[0][1][0].name, "0022.png")
        self.assertEqual(provider.calls[1][1][0].name, "td.jpg")


class StageSelectorTests(unittest.TestCase):
    def test_selects_lowest_scoring_stage_that_affected_batch(self) -> None:
        selected = WeakestActiveStageSelector()(
            state=None,
            trajectories=[
                {
                    "Render order": "p6",
                    "isometric_metrics": {"score": 0.8},
                    "topdown_metrics": {"score": 0.4},
                }
            ],
            subsample_scores=[0.6],
            candidate_idx=0,
            candidate=SEED_CANDIDATE,
        )

        self.assertEqual(selected, ["plan"])

    def test_all75_split_is_complete_disjoint_and_deterministic(self) -> None:
        cases = {
            f"{index:04d}": SceneCase(
                scene=f"{index:04d}",
                order=("std", "p6", "layout")[(index - 1) % 3],
                iso_prompt="iso",
                first_prompt="first",
                addendum="",
                spec={},
            )
            for index in range(1, 76)
        }
        scenes = sorted(cases)
        train, val = _split_all_75(cases, scenes, seed=7)
        repeated = _split_all_75(cases, scenes, seed=7)

        self.assertEqual((train, val), repeated)
        self.assertEqual(len(train), 60)
        self.assertEqual(len(val), 15)
        self.assertEqual(set(train) | set(val), set(scenes))
        self.assertFalse(set(train) & set(val))
        self.assertEqual({cases[scene].order for scene in val}, {"std", "p6", "layout"})


class ReflectionTests(unittest.TestCase):
    def test_gateway_preserves_gepa_message_list(self) -> None:
        sent: dict = {}

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
                    json={"choices": [{"message": {"content": "new policy"}}]},
                    request=httpx.Request("POST", url),
                )

        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "inspect comparisons"}],
            }
        ]
        with (
            mock.patch.object(gepa_images.httpx, "Client", FakeClient),
            mock.patch.object(
                gepa_images.gateway, "base", return_value="https://gateway.test"
            ),
            mock.patch.object(gepa_images.gateway, "token", return_value="token"),
        ):
            output = GatewayReflectionLM().__call__(messages)

        self.assertEqual(output, "new policy")
        self.assertEqual(sent["body"]["messages"], messages)
        self.assertNotIn("modalities", sent["body"])


if __name__ == "__main__":
    unittest.main()
