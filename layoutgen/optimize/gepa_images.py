"""Optimize Gemini stage instructions against frozen GPT Image 2 render targets.

The GPT Image 2 images are evaluation-only. Gemini receives the same canonical scene
contract and normal pipeline references (generated predecessor or deterministic plan),
never the GPT target image.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import pathlib
import random
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Protocol

import httpx
from PIL import Image, ImageDraw

from layoutgen import assets, paths
from layoutgen.backends import gateway, images
from layoutgen.backends import llm as text_llm
from layoutgen.pipeline import carve, golden, prompts
from layoutgen.optimize.similarity import (
    AutoEncoder,
    CompositeImageSimilarity,
    DinoEncoder,
    PyramidEncoder,
    SimilarityBreakdown,
)
from layoutgen.optimize.vlm_judge import GatewayVLMJudge, JudgeResult


TARGET_ARM = "agent_gpt52_upstream_cf94b18_gptimage2_260815"
STRESS_SCENES = (
    "0001",
    "0002",
    "0011",
    "0014",
    "0022",
    "0025",
    "0030",
    "0036",
    "0041",
    "0053",
)
DEFAULT_TRAIN = ("0001", "0011", "0014", "0022", "0036", "0053")
DEFAULT_VAL = ("0002", "0025", "0030", "0041")

SEED_CANDIDATE = {
    "iso": (
        "Return one polished Roblox-like 3D environment image, not prose. This stage "
        "must use a true isometric elevated-oblique camera: 30–40 degrees above the "
        "horizontal ground plane, equivalently 50–60 degrees away from vertical nadir. "
        "Show unmistakable front and side faces, vertical height, depth, and cast shadows "
        "while keeping the map footprint axis-aligned. "
        "When a reference image is attached, preserve its exact geometry and use it "
        "only as the footprint authority; replace its camera rather than copying it. "
        "Silently verify every named structure, count, route, opening, and distinctive "
        "obstacle before returning the image. Render only the environment: no labels, "
        "captions, swatches, legend, UI, border, letterbox, or watermark."
    ),
    "topdown": (
        "Return one square environment image, not prose. Perform a camera conversion "
        "of the attached scene while preserving its exact geometry, content, object "
        "count, route, openings, and adjacency. Use an exactly 90-degree straight-down "
        "orthographic nadir camera with zero perspective, horizon, side faces, or "
        "visible wall height. Do not redesign, regularize, mirror, add, or omit scene "
        "features. Render only the physical game environment: no labels, captions, "
        "swatches, legend, UI, border, letterbox, or watermark."
    ),
    "plan": (
        "Return one square physical game-environment image, not prose or an infographic. "
        "Build every named structure and connection with exact counts and an unbroken "
        "playable route. Use an exactly 90-degree straight-down orthographic nadir "
        "camera with zero perspective, horizon, side faces, or visible wall height. "
        "Make topology and openings unambiguous without written annotations. Do not "
        "merge or omit requirements. No labels, captions, swatches, legend, UI, border, "
        "letterbox, or watermark."
    ),
}

OBJECTIVE = (
    "Improve the three global Gemini image-stage instruction policies so Gemini renders "
    "are perceptually and structurally similar to the frozen GPT Image 2 reference "
    "renders across unseen scenes. Higher similarity is better. Preserve every canonical "
    "scene requirement and the existing render order."
)

BACKGROUND = (
    "Only the iso, topdown, and plan policy strings are mutable. The evaluator appends "
    "each policy to an immutable canonical scene contract generated from the exact same "
    "strict spec used by GPT Image 2. GPT Image 2 target images are never attached to "
    "Gemini; they are used only after rendering for global perceptual and aligned-patch "
    "spatial similarity plus grayscale structural similarity. A visual "
    "target-versus-candidate comparison is evaluation feedback for the reflection model, "
    "not an image-generation input. Policies must remain global and must not mention "
    "scene IDs or memorize a specific scene."
)

ISO_OBJECTIVE = (
    "Improve the global isometric image-stage instruction policy so candidate renders "
    "are perceptually and structurally similar to frozen GPT Image 2 isometric targets "
    "across unseen scenes. Preserve every canonical scene requirement and render order."
)

ISO_BACKGROUND = (
    "Only the iso policy is selected for mutation. Top-down predecessor images remain "
    "necessary inputs for top-down-first scenes, but only the final isometric output is "
    "scored. GPT Image 2 targets are evaluator-only and are never generation inputs. "
    "The policy must remain global and must not mention or memorize scene IDs."
)

VLM_OBJECTIVE = (
    "Improve the global isometric image policy for faithful rendering of the original "
    "user request and structured layout/config contract across unseen scenes. The score "
    "combines VLM-judged visible prompt adherence, layout following, strict isometric "
    "camera adherence, and GPT Image 2 perceptual similarity. Near-top-down images "
    "fail the camera constraint regardless of layout quality. Never add scene-specific "
    "wording."
)

VLM_BACKGROUND = (
    "Only the global iso policy is mutable. A separate vision-language judge sees the "
    "candidate image, original user request, and structured layout/config contract. It "
    "scores visible requested content and exact zones, routes, counts, adjacency, "
    "boundaries, placements, and whether the result is unmistakably elevated-oblique "
    "rather than top-down. Camera scores below the configured floor proportionally gate "
    "the whole objective. Image text is ignored as untrusted. GPT Image 2 is evaluation-"
    "only for the perceptual anchor and is never a generation input."
)


@dataclass(frozen=True)
class SceneCase:
    scene: str
    order: str
    iso_prompt: str
    first_prompt: str
    addendum: str
    spec: dict
    author_prompt: str = ""


class Provider(Protocol):
    def generate(
        self,
        prompt: str,
        references: list[pathlib.Path] | None = None,
        retries: int = 8,
    ) -> images.Answer: ...


class Scorer(Protocol):
    def compare(
        self,
        candidate: pathlib.Path,
        target: pathlib.Path,
    ) -> SimilarityBreakdown: ...


class VLMJudge(Protocol):
    def score(
        self,
        image: pathlib.Path,
        author_prompt: str,
        spec: dict,
    ) -> JudgeResult: ...


@contextlib.contextmanager
def _default_prompt_profile():
    name = "LAYOUTGEN_IMAGE_PROMPT_PROFILE"
    previous = os.environ.get(name)
    os.environ[name] = "default"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


def load_cases(specs: pathlib.Path = golden.AGENT_GATEWAY) -> dict[str, SceneCase]:
    """Rebuild canonical prompts from current strict specs with no model adaptation."""
    with _default_prompt_profile():
        rows = golden.agent_rows(specs)
    return {
        row.scene: SceneCase(
            scene=row.scene,
            order=row.order,
            iso_prompt=row.iso_prompt,
            first_prompt=row.td_prompt,
            addendum=row.addendum,
            spec=row._spec,
            author_prompt=row.prompt,
        )
        for row in rows
    }


class TargetStore:
    def __init__(self, arm: str = TARGET_ARM) -> None:
        self.arm = arm

    def get(self, scene: str, stage: str) -> pathlib.Path:
        rel = f"scenes/{self.arm}/{stage}/{scene}.png"
        target = assets.fetch(rel)
        if target is None:
            raise FileNotFoundError(
                f"missing frozen GPT Image 2 target results/{rel}; check S3 access"
            )
        return target

    def preflight(
        self,
        scenes: list[str],
        stages: tuple[str, ...] = ("iso", "td"),
    ) -> dict[str, dict[str, str]]:
        return {
            scene: {
                stage: str(self.get(scene, stage))
                for stage in stages
            }
            for scene in scenes
        }


def _candidate_error(candidate: dict[str, str]) -> str:
    for stage in ("iso", "topdown", "plan"):
        text = candidate.get(stage)
        if not isinstance(text, str) or not text.strip():
            return f"candidate must contain a non-empty {stage!r} string"
        if len(text) > 8_000:
            return f"{stage!r} instruction exceeds 8,000 characters"
    return ""


def _used_stages(case: SceneCase) -> tuple[str, str]:
    return ("plan" if case.order == "p6" else "topdown"), "iso"


def _candidate_id(candidate: dict[str, str], case: SceneCase) -> str:
    used = {stage: candidate[stage] for stage in _used_stages(case)}
    encoded = json.dumps(used, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def _valid_image(path: pathlib.Path) -> bool:
    if not path.is_file():
        return False
    try:
        with Image.open(path) as opened:
            opened.verify()
        return True
    except (OSError, ValueError):
        return False


def _write_answer(answer: images.Answer, destination: pathlib.Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f".part{os.getpid()}")
    try:
        image = images.normalise(answer.image)
        if destination.suffix.lower() in {".jpg", ".jpeg"}:
            image.save(temporary, format="JPEG", quality=92, optimize=True)
        else:
            image.save(temporary, format="PNG")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def _stable_seed(scene: str) -> int:
    digits = "".join(character for character in scene if character.isdigit())
    return int(digits) if digits else abs(hash(scene)) % (2**31)


class RenderEvaluator:
    def __init__(
        self,
        cases: dict[str, SceneCase],
        provider: Provider,
        scorer: Scorer,
        targets: TargetStore,
        run_root: pathlib.Path,
        *,
        visual_feedback: bool = True,
        iso_only: bool = False,
        max_prompt_chars: int | None = None,
        vlm_judge: VLMJudge | None = None,
        judge_weights: tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25),
        minimum_camera_score: float = 0.8,
        camera_retries: int = 0,
        camera_direct_fallback: bool = False,
        plan_builder: Callable[[SceneCase, pathlib.Path], pathlib.Path] | None = None,
    ) -> None:
        self.cases = cases
        self.provider = provider
        self.scorer = scorer
        self.targets = targets
        self.run_root = run_root
        self.visual_feedback = visual_feedback
        self.iso_only = iso_only
        self.max_prompt_chars = max_prompt_chars
        self.vlm_judge = vlm_judge
        if abs(sum(judge_weights) - 1.0) > 1e-9 or min(judge_weights) < 0:
            raise ValueError("judge weights must be non-negative and sum to 1")
        self.judge_weights = judge_weights
        if not 0.0 <= minimum_camera_score <= 1.0:
            raise ValueError("minimum camera score must be between 0 and 1")
        self.minimum_camera_score = minimum_camera_score
        if camera_retries < 0:
            raise ValueError("camera retries must be non-negative")
        self.camera_retries = camera_retries
        self.camera_direct_fallback = camera_direct_fallback
        self.plan_builder = plan_builder or self._build_plan

    def _build_plan(self, case: SceneCase, destination: pathlib.Path) -> pathlib.Path:
        if _valid_image(destination):
            return destination
        params = {
            **case.spec,
            "cells": 13 if case.spec.get("kind") == "track" else 12,
            "seed": _stable_seed(case.scene),
        }
        layout = carve.carve(params)
        source = paths.OUT / layout["layout"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(f".part{os.getpid()}")
        try:
            shutil.copyfile(source, temporary)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return destination

    def _generate(
        self,
        prompt: str,
        destination: pathlib.Path,
        references: list[pathlib.Path] | None = None,
    ) -> pathlib.Path:
        if _valid_image(destination):
            return destination
        answer = self.provider.generate(prompt, references)
        _write_answer(answer, destination)
        return destination

    def _render(
        self,
        candidate: dict[str, str],
        case: SceneCase,
    ) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
        candidate_id = _candidate_id(candidate, case)
        root = self.run_root / "renders" / candidate_id / case.scene
        iso, topdown = root / "iso.jpg", root / "td.jpg"
        first_stage = "plan" if case.order == "p6" else "topdown"
        first = prompts.with_instruction(
            case.first_prompt, first_stage, candidate[first_stage]
        )
        iso_text = prompts.with_instruction(case.iso_prompt, "iso", candidate["iso"])

        if case.order == "layout":
            plan = self.plan_builder(
                case, self.run_root / "plans" / f"{case.scene}.png"
            )
            self._generate(first, topdown, [plan])
            self._generate(iso_text, iso, [topdown])
        elif case.order == "p6":
            self._generate(first, topdown)
            self._generate(iso_text, iso, [topdown])
        else:
            self._generate(iso_text, iso)
            if not self.iso_only:
                self._generate(first, topdown, [iso])

        root.mkdir(parents=True, exist_ok=True)
        (root / "prompts.json").write_text(
            json.dumps(
                {
                    "scene": case.scene,
                    "order": case.order,
                    "candidate_id": candidate_id,
                    "first_stage": first_stage,
                    "first_prompt": first,
                    "iso_prompt": iso_text,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return iso, topdown, root

    @staticmethod
    def _iso_sheet(
        target: pathlib.Path,
        generated: pathlib.Path,
        destination: pathlib.Path,
    ) -> pathlib.Path:
        tile, label = 384, 24
        sheet = Image.new("RGB", (tile * 2, tile + label), "white")
        draw = ImageDraw.Draw(sheet)
        for title, path, x in (
            ("GPT Image 2 target — isometric", target, 0),
            ("Candidate — isometric", generated, tile),
        ):
            draw.text((x + 5, 5), title, fill="black")
            with Image.open(path) as opened:
                image = opened.convert("RGB")
                image.thumbnail((tile, tile), Image.Resampling.LANCZOS)
            sheet.paste(image, (x + (tile - image.width) // 2, label))
        destination.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(destination, format="JPEG", quality=88, optimize=True)
        return destination

    @staticmethod
    def _sheet(
        target_iso: pathlib.Path,
        generated_iso: pathlib.Path,
        target_td: pathlib.Path,
        generated_td: pathlib.Path,
        destination: pathlib.Path,
    ) -> pathlib.Path:
        tile, label = 384, 24
        sheet = Image.new("RGB", (tile * 2, (tile + label) * 2), "white")
        draw = ImageDraw.Draw(sheet)
        cells = (
            ("GPT Image 2 target — isometric", target_iso, 0, 0),
            ("Gemini candidate — isometric", generated_iso, tile, 0),
            ("GPT Image 2 target — top-down", target_td, 0, tile + label),
            ("Gemini candidate — top-down", generated_td, tile, tile + label),
        )
        for title, path, x, y in cells:
            draw.text((x + 5, y + 5), title, fill="black")
            with Image.open(path) as opened:
                image = opened.convert("RGB")
                image.thumbnail((tile, tile), Image.Resampling.LANCZOS)
            sheet.paste(image, (x + (tile - image.width) // 2, y + label))
        destination.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(destination, format="JPEG", quality=88, optimize=True)
        return destination

    def evaluate(
        self,
        candidate: dict[str, str],
        example: dict[str, str],
    ) -> tuple[float, dict]:
        if error := _candidate_error(candidate):
            return 0.0, {
                "Feedback": error,
                "scores": {"isometric_similarity": 0.0, "topdown_similarity": 0.0},
            }
        scene = example["scene"]
        case = self.cases[scene]
        if self.max_prompt_chars:
            combined = prompts.with_instruction(
                case.iso_prompt, "iso", candidate["iso"]
            )
            if len(combined) > self.max_prompt_chars:
                return 0.0, {
                    "Scene": scene,
                    "Render order": case.order,
                    "Feedback": (
                        f"The combined isometric prompt is {len(combined)} characters, "
                        f"above the provider limit of {self.max_prompt_chars}. Shorten "
                        "the global isometric policy while preserving its key rules."
                    ),
                    "scores": {"isometric_similarity": 0.0},
                    "iso_specific_info": {
                        "scores": {"isometric_similarity": 0.0},
                        "Feedback": "Shorten the isometric policy below the prompt limit.",
                    },
                }
        generated_iso, generated_td, output_root = self._render(candidate, case)
        target_iso = self.targets.get(scene, "iso")
        iso = self.scorer.compare(generated_iso, target_iso)
        if self.iso_only:
            try:
                judge = (
                    self.vlm_judge.score(
                        generated_iso,
                        case.author_prompt,
                        case.spec,
                    )
                    if self.vlm_judge
                    else None
                )
            except RuntimeError as exc:
                return 0.0, {
                    "Scene": scene,
                    "Render order": case.order,
                    "Feedback": f"Transient VLM judge failure; sample scored zero: {exc}",
                    "scores": {
                        "combined_objective": 0.0,
                        "prompt_adherence": 0.0,
                        "layout_following": 0.0,
                        "isometric_camera": 0.0,
                        "perceptual_similarity": iso.score,
                    },
                    "iso_specific_info": {
                        "scores": {
                            "combined_objective": 0.0,
                            "prompt_adherence": 0.0,
                            "layout_following": 0.0,
                            "isometric_camera": 0.0,
                            "perceptual_similarity": iso.score,
                        },
                        "Feedback": f"Transient VLM judge failure: {exc}",
                    },
                }
            if (
                judge
                and self.vlm_judge
                and self.camera_retries
                and judge.isometric_camera < self.minimum_camera_score
            ):
                prompt_record_path = output_root / "prompts.json"
                prompt_record = json.loads(prompt_record_path.read_text(encoding="utf-8"))
                base_prompt = prompt_record["iso_prompt"]
                references = [] if case.order == "std" else [generated_td]
                for attempt in range(1, self.camera_retries + 1):
                    repair_prompt = (
                        f"{base_prompt}\n\nCAMERA REPAIR ATTEMPT {attempt}: The prior "
                        "render was rejected as too close to top-down. Discard the "
                        "reference image's camera completely while preserving only its "
                        "footprint geometry. Re-render from a true three-quarter "
                        "isometric camera 30-35 degrees above the horizontal ground "
                        "plane (55-60 degrees away from vertical nadir). It is acceptable "
                        "and expected for footprint edges to recede diagonally. Vertical "
                        "front and side faces must occupy a substantial, clearly visible "
                        "portion of structures and terrain; include depth, thickness, "
                        "occlusion, and cast shadows. Never return a plan, minimap, "
                        "orthographic overhead, or shallow extrusion."
                    )
                    retry_path = output_root / f"iso-camera-retry-{attempt}.jpg"
                    self._generate(repair_prompt, retry_path, references)
                    try:
                        retry_judge = self.vlm_judge.score(
                            retry_path,
                            case.author_prompt,
                            case.spec,
                        )
                    except RuntimeError:
                        continue
                    if retry_judge.isometric_camera > judge.isometric_camera:
                        temporary = generated_iso.with_suffix(f".repair{os.getpid()}")
                        try:
                            shutil.copyfile(retry_path, temporary)
                            temporary.replace(generated_iso)
                        finally:
                            temporary.unlink(missing_ok=True)
                        judge = retry_judge
                        iso = self.scorer.compare(generated_iso, target_iso)
                        prompt_record["iso_prompt"] = repair_prompt
                        prompt_record["camera_retry"] = attempt
                        prompt_record_path.write_text(
                            json.dumps(prompt_record, indent=2) + "\n",
                            encoding="utf-8",
                        )
                    if judge.isometric_camera >= self.minimum_camera_score:
                        break
                if (
                    self.camera_direct_fallback
                    and judge.isometric_camera < self.minimum_camera_score
                ):
                    direct_prompt = (
                        f"{base_prompt}\n\nFINAL CAMERA FALLBACK: Generate directly from "
                        "this text without copying any reference image or overhead "
                        "viewpoint. Use a true three-quarter isometric camera 30-35 "
                        "degrees above the horizontal ground plane (55-60 degrees away "
                        "from vertical nadir). Show substantial vertical front and side "
                        "faces, depth, thickness, occlusion, and cast shadows. Preserve "
                        "every layout/config requirement described in the text."
                    )
                    direct_path = output_root / "iso-camera-direct.jpg"
                    self._generate(direct_prompt, direct_path)
                    try:
                        direct_judge = self.vlm_judge.score(
                            direct_path,
                            case.author_prompt,
                            case.spec,
                        )
                    except RuntimeError:
                        direct_judge = None
                    if (
                        direct_judge
                        and direct_judge.isometric_camera > judge.isometric_camera
                    ):
                        temporary = generated_iso.with_suffix(f".repair{os.getpid()}")
                        try:
                            shutil.copyfile(direct_path, temporary)
                            temporary.replace(generated_iso)
                        finally:
                            temporary.unlink(missing_ok=True)
                        judge = direct_judge
                        iso = self.scorer.compare(generated_iso, target_iso)
                        prompt_record["iso_prompt"] = direct_prompt
                        prompt_record["camera_retry"] = "direct-fallback"
                        prompt_record_path.write_text(
                            json.dumps(prompt_record, indent=2) + "\n",
                            encoding="utf-8",
                        )
            if judge:
                score = (
                    self.judge_weights[0] * judge.prompt_adherence
                    + self.judge_weights[1] * judge.layout_following
                    + self.judge_weights[2] * judge.isometric_camera
                    + self.judge_weights[3] * iso.score
                )
                if (
                    self.minimum_camera_score
                    and judge.isometric_camera < self.minimum_camera_score
                ):
                    score *= judge.isometric_camera / self.minimum_camera_score
            else:
                score = iso.score
            feedback = (
                (
                    f"{judge.feedback} Missing visible requirements: "
                    f"{'; '.join(judge.missing_requirements) or 'none identified'}. "
                    f"Layout errors: {'; '.join(judge.layout_errors) or 'none identified'}. "
                    f"Camera errors: {'; '.join(judge.camera_errors) or 'none identified'}."
                )
                if judge
                else (
                    "Improve isometric target likeness in camera, global composition, "
                    "geometry, and feature coverage without scene-specific wording."
                )
            )
            scores = (
                {
                    "combined_objective": score,
                    "prompt_adherence": judge.prompt_adherence,
                    "layout_following": judge.layout_following,
                    "isometric_camera": judge.isometric_camera,
                    "perceptual_similarity": iso.score,
                }
                if judge
                else {"isometric_similarity": iso.score}
            )
            side_info = {
                "Scene": scene,
                "Render order": case.order,
                "Feedback": feedback,
                "scores": scores,
                "isometric_metrics": iso.as_dict(),
                "iso_specific_info": {
                    "scores": scores,
                    "Feedback": feedback,
                },
            }
            if judge:
                side_info["vlm_judge"] = judge.as_dict()
            if self.visual_feedback:
                from gepa import Image as FeedbackImage

                comparison = self._iso_sheet(
                    target_iso,
                    generated_iso,
                    output_root / "comparison.jpg",
                )
                side_info["Visual comparison"] = FeedbackImage(path=str(comparison))
            return score, side_info

        target_td = self.targets.get(scene, "td")
        topdown = self.scorer.compare(generated_td, target_td)
        score = (iso.score + topdown.score) / 2.0
        lower = "isometric" if iso.score <= topdown.score else "top-down"
        feedback = (
            f"The {lower} stage is the weaker match. Improve target likeness in camera, "
            "global composition, geometry, and feature coverage without introducing "
            "scene-specific wording. GPT Image 2 images are evaluator-only and were not "
            "provided to Gemini."
        )
        side_info: dict = {
            "Scene": scene,
            "Render order": case.order,
            "Feedback": feedback,
            "scores": {
                "isometric_similarity": iso.score,
                "topdown_similarity": topdown.score,
            },
            "isometric_metrics": iso.as_dict(),
            "topdown_metrics": topdown.as_dict(),
            "iso_specific_info": {
                "scores": {"isometric_similarity": iso.score},
                "Feedback": (
                    "Optimize the oblique-view policy using the isometric half of the "
                    "visual comparison and its semantic/spatial/structural scores."
                ),
            },
        }
        first_key = "plan" if case.order == "p6" else "topdown"
        side_info[f"{first_key}_specific_info"] = {
            "scores": {"topdown_similarity": topdown.score},
            "Feedback": (
                "Optimize this first-stage policy using the top-down half of the visual "
                "comparison and its semantic/spatial/structural scores."
            ),
        }
        if self.visual_feedback:
            from gepa import Image as FeedbackImage

            comparison = self._sheet(
                target_iso,
                generated_iso,
                target_td,
                generated_td,
                output_root / "comparison.jpg",
            )
            side_info["Visual comparison"] = FeedbackImage(path=str(comparison))
        return score, side_info


class WeakestActiveStageSelector:
    """Reflect on the lowest-similarity stage that affected this minibatch."""

    def __call__(
        self,
        state,
        trajectories: list[dict],
        subsample_scores: list[float],
        candidate_idx: int,
        candidate: dict[str, str],
    ) -> list[str]:
        del state, subsample_scores, candidate_idx
        observed: dict[str, list[float]] = {
            "iso": [],
            "topdown": [],
            "plan": [],
        }
        for trajectory in trajectories:
            if value := trajectory.get("isometric_metrics"):
                observed["iso"].append(float(value["score"]))
            if value := trajectory.get("topdown_metrics"):
                stage = "plan" if trajectory.get("Render order") == "p6" else "topdown"
                observed[stage].append(float(value["score"]))
        active = {
            stage: sum(scores) / len(scores)
            for stage, scores in observed.items()
            if scores and stage in candidate
        }
        return [min(active, key=active.get)] if active else ["iso"]


class AzureReflectionLM:
    """GEPA reflection callable backed directly by an Azure GPT deployment."""

    RETRYABLE = {408, 409, 429, 500, 502, 503, 504}

    def __init__(
        self,
        deployment: str = "gpt-5.2",
        *,
        endpoint: str = text_llm.ENDPOINT,
        api_version: str = text_llm.API_VERSION,
        key: str | None = None,
        timeout: float = 600.0,
        retries: int = 4,
    ) -> None:
        self.deployment = deployment
        self.endpoint = endpoint
        self.api_version = api_version
        self.key = key or os.getenv("LAYOUTGEN_GEPA_REFLECTION_KEY") or text_llm.api_key()
        self.timeout = timeout
        self.retries = retries

    def __call__(self, prompt: str | list[dict]) -> str:
        url = (
            f"{self.endpoint.rstrip('/')}/openai/deployments/{self.deployment}/"
            f"chat/completions?api-version={self.api_version}"
        )
        is_messages = (
            isinstance(prompt, list)
            and bool(prompt)
            and all("role" in item and "content" in item for item in prompt)
        )
        messages = prompt if is_messages else [{"role": "user", "content": prompt}]
        body = {"messages": messages}
        last: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        url,
                        json=body,
                        headers={"api-key": self.key, "Content-Type": "application/json"},
                    )
                    response.raise_for_status()
                    data = response.json()
                return str(data["choices"][0]["message"]["content"])
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in self.RETRYABLE:
                    detail = exc.response.text[:1_000]
                    raise RuntimeError(
                        f"Azure reflection HTTP {exc.response.status_code}: {detail}"
                    ) from exc
                last = exc
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
                last = exc
            if attempt < self.retries:
                time.sleep(min(2**attempt + random.random(), 30.0))
        raise RuntimeError(
            f"Azure reflection failed after {self.retries} attempts: {last}"
        )


class GatewayReflectionLM:
    """GEPA visual reflection through the same Gateway used for Gemini rendering."""

    RETRYABLE = {408, 409, 429, 500, 502, 503, 504}

    def __init__(
        self,
        model: str = "gemini-3.1-flash-image",
        *,
        timeout: float = 600.0,
        retries: int = 4,
    ) -> None:
        self.model = model
        self.timeout = timeout
        self.retries = retries

    def __call__(self, prompt: str | list[dict]) -> str:
        is_messages = (
            isinstance(prompt, list)
            and bool(prompt)
            and all("role" in item and "content" in item for item in prompt)
        )
        messages = prompt if is_messages else [{"role": "user", "content": prompt}]
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": gateway.MAX_TOKENS,
        }
        url = f"{gateway.base().rstrip('/')}/v1/chat/completions"
        last: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        url,
                        json=body,
                        headers={
                            "Authorization": f"Bearer {gateway.token()}",
                            "Content-Type": "application/json",
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                return str(data["choices"][0]["message"]["content"])
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in self.RETRYABLE:
                    detail = exc.response.text[:1_000]
                    raise RuntimeError(
                        f"Gateway reflection HTTP {exc.response.status_code}: {detail}"
                    ) from exc
                last = exc
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
                last = exc
            if attempt < self.retries:
                time.sleep(min(2**attempt + random.random(), 30.0))
        raise RuntimeError(
            f"Gateway reflection failed after {self.retries} attempts: {last}"
        )


def _scene_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _run_name() -> str:
    stamp = dt.datetime.now(dt.UTC).strftime("%y%m%d_%H%M%S")
    return f"gemini_similarity_{stamp}"


def _write_json(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def _selected_cases(
    cases: dict[str, SceneCase],
    train: list[str],
    val: list[str],
) -> None:
    overlap = sorted(set(train) & set(val))
    if overlap:
        raise ValueError(f"train and validation scenes overlap: {', '.join(overlap)}")
    missing = sorted((set(train) | set(val)) - cases.keys())
    if missing:
        raise ValueError(f"strict specs are missing scenes: {', '.join(missing)}")
    if not train or not val:
        raise ValueError("both train and validation splits must be non-empty")


def _all_75(cases: dict[str, SceneCase]) -> list[str]:
    scenes = sorted(
        scene
        for scene in cases
        if scene.isdigit() and 1 <= int(scene) <= 75
    )
    if len(scenes) != 75:
        raise ValueError(f"expected 75 numeric golden scenes, found {len(scenes)}")
    return scenes


def _split_all_75(
    cases: dict[str, SceneCase],
    scenes: list[str],
    seed: int,
) -> tuple[list[str], list[str]]:
    """Deterministic 80/20 split, stratified across the three render orders."""
    rng = random.Random(seed)
    groups: dict[str, list[str]] = {}
    for scene in scenes:
        groups.setdefault(cases[scene].order, []).append(scene)
    val: list[str] = []
    for order in sorted(groups):
        group = groups[order]
        rng.shuffle(group)
        val.extend(group[: round(len(group) * 0.2)])
    # Rounding per stratum can be one scene off. Keep the held-out set exactly 20%.
    target_validation = round(len(scenes) * 0.2)
    remaining = [scene for scene in scenes if scene not in val]
    rng.shuffle(remaining)
    if len(val) < target_validation:
        val.extend(remaining[: target_validation - len(val)])
    elif len(val) > target_validation:
        val = sorted(val)[:target_validation]
    val_set = set(val)
    return (
        [scene for scene in scenes if scene not in val_set],
        [scene for scene in scenes if scene in val_set],
    )


def _score_candidate(
    evaluator: RenderEvaluator,
    candidate: dict[str, str],
    scenes: list[str],
    destination: pathlib.Path,
    label: str,
    workers: int = 1,
) -> None:
    def score_scene(scene: str) -> dict:
        score, info = evaluator.evaluate(candidate, {"scene": scene})
        info.pop("Visual comparison", None)
        return {"scene": scene, "score": score, **info}

    rows = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for scene, row in zip(scenes, pool.map(score_scene, scenes), strict=True):
            rows.append(row)
            score = row["score"]
            assert isinstance(score, float)
            print(f"  {label} {scene}: {score:.4f}", flush=True)
    _write_json(destination, rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", default=_run_name())
    parser.add_argument("--target-arm", default=TARGET_ARM)
    parser.add_argument("--specs", type=pathlib.Path, default=golden.AGENT_GATEWAY)
    parser.add_argument("--train-scenes", default=",".join(DEFAULT_TRAIN))
    parser.add_argument("--val-scenes", default=",".join(DEFAULT_VAL))
    parser.add_argument(
        "--all-75",
        action="store_true",
        help="use a deterministic 60/15 split and score the winner on all 75",
    )
    parser.add_argument("--image-model", default="gemini-3.1-flash-image")
    parser.add_argument(
        "--candidate-file",
        type=pathlib.Path,
        help="use this policy JSON instead of the built-in seed candidate",
    )
    parser.add_argument(
        "--image-provider",
        choices=("gateway", "scenegen"),
        default="gateway",
    )
    parser.add_argument("--reference-image-model")
    parser.add_argument(
        "--scenegen-url",
        default=(
            "https://8080--standard--h200-training--akashgarg.devspaces.rbx.com"
        ),
    )
    parser.add_argument(
        "--iso-only",
        action="store_true",
        help="score and optimize only final isometric outputs",
    )
    parser.add_argument(
        "--vlm-judge",
        action="store_true",
        help="add Gateway VLM prompt-adherence and layout-following scores",
    )
    parser.add_argument("--judge-model", default="gpt-5.5")
    parser.add_argument("--prompt-adherence-weight", type=float, default=0.25)
    parser.add_argument("--layout-following-weight", type=float, default=0.25)
    parser.add_argument("--camera-weight", type=float, default=0.25)
    parser.add_argument("--perceptual-weight", type=float, default=0.25)
    parser.add_argument("--minimum-camera-score", type=float, default=0.8)
    parser.add_argument(
        "--camera-retries",
        type=int,
        default=0,
        help="selectively regenerate images below the minimum camera score",
    )
    parser.add_argument(
        "--camera-direct-fallback",
        action="store_true",
        help="use text-only isometric generation if reference-conditioned retries fail",
    )
    parser.add_argument(
        "--orders",
        default="std,p6,layout",
        help="comma-separated eligible render orders",
    )
    parser.add_argument(
        "--reflection-provider",
        choices=("gateway", "azure"),
        default="gateway",
    )
    parser.add_argument(
        "--reflection-model",
        default="gemini-3.1-flash-image",
        help="Gateway model used to inspect comparisons and mutate instructions",
    )
    parser.add_argument("--reflection-deployment", default="gpt-5.2")
    parser.add_argument(
        "--encoder",
        choices=("auto", "dino", "pyramid"),
        default="auto",
        help="similarity feature encoder; auto falls back if PyTorch cannot load",
    )
    parser.add_argument("--dino-model", default="facebook/dinov2-small")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-metric-calls", type=int, default=40)
    parser.add_argument(
        "--patience",
        type=int,
        default=0,
        help="stop after this many proposals without validation improvement",
    )
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--reflection-minibatch", type=int, default=2)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--no-visual-feedback", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate specs, splits, and frozen targets without model calls",
    )
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help="score the seed candidate without asking GEPA for mutations",
    )
    args = parser.parse_args()
    seed_candidate = (
        json.loads(args.candidate_file.read_text(encoding="utf-8"))
        if args.candidate_file
        else SEED_CANDIDATE
    )
    if error := _candidate_error(seed_candidate):
        raise ValueError(f"invalid --candidate-file: {error}")
    if args.vlm_judge and not args.iso_only:
        raise ValueError("--vlm-judge currently requires --iso-only")
    judge_weights = (
        args.prompt_adherence_weight,
        args.layout_following_weight,
        args.camera_weight,
        args.perceptual_weight,
    )
    if min(judge_weights) < 0 or abs(sum(judge_weights) - 1.0) > 1e-9:
        raise ValueError("judge weights must be non-negative and sum to 1")
    if not 0.0 <= args.minimum_camera_score <= 1.0:
        raise ValueError("--minimum-camera-score must be between 0 and 1")
    if args.camera_retries < 0:
        raise ValueError("--camera-retries must be non-negative")

    cases = load_cases(args.specs)
    orders = {value.strip() for value in args.orders.split(",") if value.strip()}
    unknown_orders = orders - {"std", "p6", "layout"}
    if unknown_orders:
        raise ValueError(f"unknown render orders: {', '.join(sorted(unknown_orders))}")
    all_scenes: list[str] = []
    if args.all_75:
        all_scenes = [
            scene for scene in _all_75(cases) if cases[scene].order in orders
        ]
        train, val = _split_all_75(cases, all_scenes, args.seed)
    else:
        train = _scene_list(args.train_scenes)
        val = _scene_list(args.val_scenes)
        ineligible = [
            scene for scene in train + val if cases.get(scene) and cases[scene].order not in orders
        ]
        if ineligible:
            raise ValueError(f"scenes excluded by --orders: {', '.join(ineligible)}")
    _selected_cases(cases, train, val)
    run_root = paths.RUN / "gepa" / args.run_name
    run_root.mkdir(parents=True, exist_ok=True)
    targets = TargetStore(args.target_arm)
    target_stages = ("iso",) if args.iso_only else ("iso", "td")
    target_paths = targets.preflight(train + val, target_stages)
    manifest = {
        "run_name": args.run_name,
        "target_arm": args.target_arm,
        "target_role": "evaluation-only; never passed to Gemini",
        "specs": str(args.specs),
        "train_scenes": train,
        "val_scenes": val,
        "all_scenes": all_scenes,
        "image_model": args.image_model,
        "image_provider": args.image_provider,
        "reference_image_model": args.reference_image_model,
        "iso_only": args.iso_only,
        "vlm_judge": {
            "enabled": args.vlm_judge,
            "model": args.judge_model if args.vlm_judge else None,
            "weights": {
                "prompt_adherence": args.prompt_adherence_weight,
                "layout_following": args.layout_following_weight,
                "isometric_camera": args.camera_weight,
                "perceptual_similarity": args.perceptual_weight,
            },
            "minimum_camera_score": args.minimum_camera_score,
            "camera_retries": args.camera_retries,
            "camera_direct_fallback": args.camera_direct_fallback,
        },
        "orders": sorted(orders),
        "reflection_provider": args.reflection_provider,
        "reflection_model": (
            args.reflection_model
            if args.reflection_provider == "gateway"
            else args.reflection_deployment
        ),
        "reflection_deployment": args.reflection_deployment,
        "similarity": {
            "encoder": args.encoder,
            "model": args.dino_model,
            "weights": {"semantic": 0.55, "spatial": 0.30, "structure": 0.15},
            "stage_weights": (
                {"iso": 1.0} if args.iso_only else {"iso": 0.5, "td": 0.5}
            ),
        },
        "max_metric_calls": args.max_metric_calls,
        "patience": args.patience,
        "targets": target_paths,
        "seed_candidate": seed_candidate,
        "candidate_file": str(args.candidate_file) if args.candidate_file else None,
    }
    _write_json(run_root / "manifest.json", manifest)
    if args.dry_run:
        print(
            f"GEPA preflight ok: {len(train)} train + {len(val)} validation scenes; "
            f"{len(target_stages) * (len(train) + len(val))} frozen targets available\n"
            f"{run_root / 'manifest.json'}"
        )
        return

    if args.image_provider == "gateway":
        provider = images.LLMGatewayProvider(model=args.image_model)
    else:
        provider = images.SceneGenProvider(
            model=args.image_model,
            reference_model=args.reference_image_model,
            base_url=args.scenegen_url,
        )
    if args.encoder == "dino":
        encoder = DinoEncoder(model=args.dino_model, device=args.device)
    elif args.encoder == "pyramid":
        encoder = PyramidEncoder()
    else:
        encoder = AutoEncoder(model=args.dino_model, device=args.device)
    scorer = CompositeImageSimilarity(encoder)
    vlm_judge = (
        GatewayVLMJudge(
            model=args.judge_model,
            cache_root=run_root / "judge_cache",
        )
        if args.vlm_judge
        else None
    )
    evaluator = RenderEvaluator(
        cases,
        provider,
        scorer,
        targets,
        run_root,
        visual_feedback=not args.no_visual_feedback,
        iso_only=args.iso_only,
        max_prompt_chars=8000 if args.image_provider == "scenegen" else None,
        vlm_judge=vlm_judge,
        judge_weights=judge_weights,
        minimum_camera_score=args.minimum_camera_score,
        camera_retries=args.camera_retries,
        camera_direct_fallback=args.camera_direct_fallback,
    )
    if args.baseline_only:
        destination = (
            run_root / "final_all75_scores.json"
            if all_scenes
            else run_root / "baseline.json"
        )
        _score_candidate(
            evaluator,
            seed_candidate,
            train + val,
            destination,
            "baseline",
            args.workers,
        )
        if all_scenes:
            _write_json(run_root / "best_candidate.json", seed_candidate)
        return

    from gepa.optimize_anything import (
        EngineConfig,
        GEPAConfig,
        ReflectionConfig,
        optimize_anything,
    )
    from gepa.utils import NoImprovementStopper

    if args.reflection_provider == "gateway":
        reflection = GatewayReflectionLM(model=args.reflection_model)
    else:
        reflection = AzureReflectionLM(deployment=args.reflection_deployment)
    config = GEPAConfig(
        engine=EngineConfig(
            run_dir=str(run_root / "gepa"),
            seed=args.seed,
            max_metric_calls=args.max_metric_calls,
            parallel=args.workers > 1,
            max_workers=args.workers,
            cache_evaluation=True,
            cache_evaluation_storage="disk",
            track_best_outputs=False,
            display_progress_bar=True,
            raise_on_exception=True,
        ),
        reflection=ReflectionConfig(
            reflection_lm=reflection,
            reflection_minibatch_size=min(args.reflection_minibatch, len(train)),
            module_selector=WeakestActiveStageSelector(),
            skip_perfect_score=True,
            perfect_score=1.0,
        ),
        stop_callbacks=(
            NoImprovementStopper(args.patience) if args.patience > 0 else None
        ),
    )
    result = optimize_anything(
        seed_candidate=seed_candidate,
        evaluator=evaluator.evaluate,
        dataset=[{"scene": scene} for scene in train],
        valset=[{"scene": scene} for scene in val],
        objective=(
            VLM_OBJECTIVE
            if args.vlm_judge
            else ISO_OBJECTIVE if args.iso_only else OBJECTIVE
        ),
        background=(
            VLM_BACKGROUND
            if args.vlm_judge
            else ISO_BACKGROUND if args.iso_only else BACKGROUND
        ),
        config=config,
    )
    best = result.best_candidate
    assert isinstance(best, dict)
    _write_json(run_root / "best_candidate.json", best)
    _write_json(run_root / "result.json", result.to_dict())
    if all_scenes:
        _score_candidate(
            evaluator,
            best,
            all_scenes,
            run_root / "final_all75_scores.json",
            "final",
            args.workers,
        )
    print(
        f"best validation similarity: {result.val_aggregate_scores[result.best_idx]:.4f}\n"
        f"candidate: {run_root / 'best_candidate.json'}"
    )


if __name__ == "__main__":
    main()
