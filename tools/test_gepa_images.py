from __future__ import annotations

import base64
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock

import httpx
import numpy as np
from PIL import Image

from layoutgen.backends import images
from layoutgen.optimize import gepa_images
from layoutgen.optimize import vlm_judge
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
from layoutgen.optimize.vlm_judge import GatewayVLMJudge, JudgeResult


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


class FakeVLMJudge:
    def score(
        self,
        image: pathlib.Path,
        author_prompt: str,
        spec: dict,
    ) -> JudgeResult:
        self.received = (image, author_prompt, spec)
        return JudgeResult(
            prompt_adherence=0.9,
            layout_following=0.7,
            isometric_camera=0.85,
            feedback="Restore the missing bridge.",
            missing_requirements=("bridge",),
            layout_errors=("route is disconnected",),
            camera_errors=(),
        )


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

    def test_iso_only_standard_order_skips_topdown_generation_and_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            provider = FakeProvider()
            case = SceneCase("0001", "std", "ISO", "TOPDOWN", "", {})
            evaluator = RenderEvaluator(
                {"0001": case},
                provider,
                FixedScorer(),
                FakeTargets(root / "targets"),
                root / "run",
                visual_feedback=False,
                iso_only=True,
            )
            score, info = evaluator.evaluate(SEED_CANDIDATE, {"scene": "0001"})

        self.assertAlmostEqual(score, 0.8)
        self.assertEqual(len(provider.calls), 1)
        self.assertIn("isometric_similarity", info["scores"])
        self.assertNotIn("topdown_similarity", info["scores"])

    def test_provider_prompt_limit_rejects_candidate_before_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            provider = FakeProvider()
            case = SceneCase("0001", "std", "X" * 120, "TOPDOWN", "", {})
            evaluator = RenderEvaluator(
                {"0001": case},
                provider,
                FixedScorer(),
                FakeTargets(root / "targets"),
                root / "run",
                visual_feedback=False,
                iso_only=True,
                max_prompt_chars=200,
            )
            candidate = {**SEED_CANDIDATE, "iso": "Y" * 120}
            score, info = evaluator.evaluate(candidate, {"scene": "0001"})

        self.assertEqual(score, 0.0)
        self.assertEqual(provider.calls, [])
        self.assertIn("above the provider limit", info["Feedback"])

    def test_vlm_judge_combines_prompt_layout_and_perceptual_scores(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            judge = FakeVLMJudge()
            case = SceneCase(
                "0001",
                "std",
                "ISO",
                "TOPDOWN",
                "",
                {"layout": {"boundary": "wall"}},
                "Build a castle with one bridge.",
            )
            evaluator = RenderEvaluator(
                {"0001": case},
                FakeProvider(),
                FixedScorer(),
                FakeTargets(root / "targets"),
                root / "run",
                visual_feedback=False,
                iso_only=True,
                vlm_judge=judge,
            )
            score, info = evaluator.evaluate(SEED_CANDIDATE, {"scene": "0001"})

        self.assertAlmostEqual(score, 0.8125)
        self.assertEqual(info["scores"]["prompt_adherence"], 0.9)
        self.assertEqual(info["scores"]["layout_following"], 0.7)
        self.assertEqual(info["scores"]["isometric_camera"], 0.85)
        self.assertIn("missing bridge", info["Feedback"])
        self.assertEqual(judge.received[1], "Build a castle with one bridge.")

    def test_near_topdown_camera_gates_entire_vlm_objective(self) -> None:
        class TopdownJudge(FakeVLMJudge):
            def score(self, image, author_prompt, spec):
                result = super().score(image, author_prompt, spec)
                return JudgeResult(
                    prompt_adherence=result.prompt_adherence,
                    layout_following=result.layout_following,
                    isometric_camera=0.2,
                    feedback="Camera is near-nadir.",
                    camera_errors=("near-top-down view",),
                )

        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            evaluator = RenderEvaluator(
                {
                    "0001": SceneCase(
                        "0001", "std", "ISO", "TOPDOWN", "", {}, "Build a castle."
                    )
                },
                FakeProvider(),
                FixedScorer(),
                FakeTargets(root / "targets"),
                root / "run",
                visual_feedback=False,
                iso_only=True,
                vlm_judge=TopdownJudge(),
            )
            score, info = evaluator.evaluate(SEED_CANDIDATE, {"scene": "0001"})

        self.assertAlmostEqual(score, 0.65 * (0.2 / 0.8))
        self.assertIn("near-top-down", info["Feedback"])

    def test_transient_vlm_failure_scores_only_sample_zero(self) -> None:
        class FailingJudge:
            def score(self, image, author_prompt, spec):
                raise RuntimeError("empty judge response")

        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            evaluator = RenderEvaluator(
                {
                    "0001": SceneCase(
                        "0001", "std", "ISO", "TOPDOWN", "", {}, "Build a castle."
                    )
                },
                FakeProvider(),
                FixedScorer(),
                FakeTargets(root / "targets"),
                root / "run",
                visual_feedback=False,
                iso_only=True,
                vlm_judge=FailingJudge(),
            )
            score, info = evaluator.evaluate(SEED_CANDIDATE, {"scene": "0001"})

        self.assertEqual(score, 0.0)
        self.assertIn("Transient VLM judge failure", info["Feedback"])
        self.assertEqual(info["scores"]["perceptual_similarity"], 0.8)

    def test_camera_retry_replaces_failed_render_selectively(self) -> None:
        class RepairJudge:
            def __init__(self):
                self.calls = 0

            def score(self, image, author_prompt, spec):
                self.calls += 1
                camera = 0.2 if self.calls == 1 else 0.9
                return JudgeResult(
                    prompt_adherence=0.9,
                    layout_following=0.8,
                    isometric_camera=camera,
                    feedback="Camera checked.",
                )

        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            provider = FakeProvider()
            judge = RepairJudge()
            evaluator = RenderEvaluator(
                {
                    "0001": SceneCase(
                        "0001", "std", "ISO", "TOPDOWN", "", {}, "Build a castle."
                    )
                },
                provider,
                FixedScorer(),
                FakeTargets(root / "targets"),
                root / "run",
                visual_feedback=False,
                iso_only=True,
                vlm_judge=judge,
                camera_retries=2,
            )
            score, info = evaluator.evaluate(SEED_CANDIDATE, {"scene": "0001"})
            prompt_record = next((root / "run" / "renders").glob("*/*/prompts.json"))
            saved_prompt = json.loads(prompt_record.read_text())

        self.assertAlmostEqual(score, 0.85)
        self.assertEqual(info["scores"]["isometric_camera"], 0.9)
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(saved_prompt["camera_retry"], 1)
        self.assertIn("CAMERA REPAIR ATTEMPT 1", saved_prompt["iso_prompt"])

    def test_camera_direct_fallback_runs_after_reference_repair_fails(self) -> None:
        class RepairJudge:
            def __init__(self):
                self.scores = iter((0.2, 0.3, 0.9))

            def score(self, image, author_prompt, spec):
                return JudgeResult(
                    prompt_adherence=0.8,
                    layout_following=0.7,
                    isometric_camera=next(self.scores),
                    feedback="Camera checked.",
                )

        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            provider = FakeProvider()
            evaluator = RenderEvaluator(
                {
                    "0001": SceneCase(
                        "0001", "std", "ISO", "TOPDOWN", "", {}, "Build a castle."
                    )
                },
                provider,
                FixedScorer(),
                FakeTargets(root / "targets"),
                root / "run",
                visual_feedback=False,
                iso_only=True,
                vlm_judge=RepairJudge(),
                camera_retries=1,
                camera_direct_fallback=True,
            )
            _, info = evaluator.evaluate(SEED_CANDIDATE, {"scene": "0001"})
            prompt_record = next((root / "run" / "renders").glob("*/*/prompts.json"))
            saved_prompt = json.loads(prompt_record.read_text())

        self.assertEqual(info["scores"]["isometric_camera"], 0.9)
        self.assertEqual(len(provider.calls), 3)
        self.assertEqual(saved_prompt["camera_retry"], "direct-fallback")
        self.assertIn("FINAL CAMERA FALLBACK", saved_prompt["iso_prompt"])


class SceneGenProviderTests(unittest.TestCase):
    def test_references_route_to_edit_model_as_data_urls(self) -> None:
        sent: dict = {}
        image = Image.new("RGB", (8, 8), "blue")
        encoded = io.BytesIO()
        image.save(encoded, format="PNG")

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def post(self, url, *, json):
                sent.update(url=url, body=json)
                return httpx.Response(
                    200,
                    json={
                        "data": [
                            {"b64_json": base64.b64encode(encoded.getvalue()).decode()}
                        ]
                    },
                    request=httpx.Request("POST", url),
                )

        with tempfile.TemporaryDirectory() as temporary:
            reference = pathlib.Path(temporary) / "reference.png"
            image.save(reference)
            provider = images.SceneGenProvider(
                "qwen-image",
                reference_model="qwen-image-edit",
                base_url="https://scenegen.test",
            )
            with mock.patch.object(images.httpx, "Client", FakeClient):
                answer = provider.generate("make isometric", [reference])

        self.assertEqual(answer.model, "qwen-image-edit")
        self.assertEqual(sent["body"]["model"], "qwen-image-edit")
        self.assertTrue(sent["body"]["image"][0].startswith("data:image/png;base64,"))


class VLMJudgeTests(unittest.TestCase):
    def test_gateway_vlm_sends_image_and_parses_bounded_json_scores(self) -> None:
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
                    json={
                        "choices": [
                            {
                                "message": {
                                    "content": (
                                        "```json\n{\"prompt_adherence\":1.2,"
                                        "\"layout_following\":0.6,"
                                        "\"isometric_camera\":1.1,"
                                        "\"feedback\":\"Missing gate\","
                                        "\"missing_requirements\":[\"gate\"],"
                                        "\"layout_errors\":[]}\n```"
                                    )
                                }
                            }
                        ]
                    },
                    request=httpx.Request("POST", url),
                )

        with tempfile.TemporaryDirectory() as temporary:
            image = pathlib.Path(temporary) / "candidate.jpg"
            Image.new("RGB", (8, 8), "green").save(image)
            with (
                mock.patch.object(vlm_judge.httpx, "Client", FakeClient),
                mock.patch.object(
                    vlm_judge.gateway, "base", return_value="https://gateway.test"
                ),
                mock.patch.object(vlm_judge.gateway, "token", return_value="token"),
            ):
                result = GatewayVLMJudge().score(
                    image,
                    "Build one castle gate.",
                    {"shape": "space-bounded"},
                )

        content = sent["body"]["messages"][0]["content"]
        self.assertEqual(result.prompt_adherence, 1.0)
        self.assertEqual(result.layout_following, 0.6)
        self.assertEqual(result.isometric_camera, 1.0)
        self.assertEqual(result.missing_requirements, ("gate",))
        self.assertEqual(content[1]["type"], "image_url")
        self.assertIn("Build one castle gate.", content[0]["text"])


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

        std_scenes = [scene for scene in scenes if cases[scene].order == "std"]
        std_train, std_val = _split_all_75(cases, std_scenes, seed=7)
        self.assertEqual(len(std_train), 20)
        self.assertEqual(len(std_val), 5)


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
