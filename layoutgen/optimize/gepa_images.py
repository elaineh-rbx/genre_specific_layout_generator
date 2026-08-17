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
        "must use a steep elevated oblique camera whose optical axis is 30–35 degrees "
        "away from vertical nadir. Show unmistakable front and side faces, vertical "
        "height, depth, and cast shadows while keeping the map footprint axis-aligned. "
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


@dataclass(frozen=True)
class SceneCase:
    scene: str
    order: str
    iso_prompt: str
    first_prompt: str
    addendum: str
    spec: dict


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

    def preflight(self, scenes: list[str]) -> dict[str, dict[str, str]]:
        return {
            scene: {
                stage: str(self.get(scene, stage))
                for stage in ("iso", "td")
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
        plan_builder: Callable[[SceneCase, pathlib.Path], pathlib.Path] | None = None,
    ) -> None:
        self.cases = cases
        self.provider = provider
        self.scorer = scorer
        self.targets = targets
        self.run_root = run_root
        self.visual_feedback = visual_feedback
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
        generated_iso, generated_td, output_root = self._render(candidate, case)
        target_iso = self.targets.get(scene, "iso")
        target_td = self.targets.get(scene, "td")
        iso = self.scorer.compare(generated_iso, target_iso)
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
    remaining = [scene for scene in scenes if scene not in val]
    rng.shuffle(remaining)
    if len(val) < 15:
        val.extend(remaining[: 15 - len(val)])
    elif len(val) > 15:
        val = sorted(val)[:15]
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
) -> None:
    rows = []
    for scene in scenes:
        score, info = evaluator.evaluate(candidate, {"scene": scene})
        info.pop("Visual comparison", None)
        rows.append({"scene": scene, "score": score, **info})
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

    cases = load_cases(args.specs)
    all_scenes: list[str] = []
    if args.all_75:
        all_scenes = _all_75(cases)
        train, val = _split_all_75(cases, all_scenes, args.seed)
    else:
        train = _scene_list(args.train_scenes)
        val = _scene_list(args.val_scenes)
    _selected_cases(cases, train, val)
    run_root = paths.RUN / "gepa" / args.run_name
    run_root.mkdir(parents=True, exist_ok=True)
    targets = TargetStore(args.target_arm)
    target_paths = targets.preflight(train + val)
    manifest = {
        "run_name": args.run_name,
        "target_arm": args.target_arm,
        "target_role": "evaluation-only; never passed to Gemini",
        "specs": str(args.specs),
        "train_scenes": train,
        "val_scenes": val,
        "all_scenes": all_scenes,
        "image_model": args.image_model,
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
            "stage_weights": {"iso": 0.5, "td": 0.5},
        },
        "max_metric_calls": args.max_metric_calls,
        "patience": args.patience,
        "targets": target_paths,
        "seed_candidate": SEED_CANDIDATE,
    }
    _write_json(run_root / "manifest.json", manifest)
    if args.dry_run:
        print(
            f"GEPA preflight ok: {len(train)} train + {len(val)} validation scenes; "
            f"{2 * (len(train) + len(val))} frozen targets available\n"
            f"{run_root / 'manifest.json'}"
        )
        return

    provider = images.LLMGatewayProvider(model=args.image_model)
    if args.encoder == "dino":
        encoder = DinoEncoder(model=args.dino_model, device=args.device)
    elif args.encoder == "pyramid":
        encoder = PyramidEncoder()
    else:
        encoder = AutoEncoder(model=args.dino_model, device=args.device)
    scorer = CompositeImageSimilarity(encoder)
    evaluator = RenderEvaluator(
        cases,
        provider,
        scorer,
        targets,
        run_root,
        visual_feedback=not args.no_visual_feedback,
    )
    if args.baseline_only:
        _score_candidate(
            evaluator,
            SEED_CANDIDATE,
            train + val,
            run_root / "baseline.json",
            "baseline",
        )
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
        seed_candidate=SEED_CANDIDATE,
        evaluator=evaluator.evaluate,
        dataset=[{"scene": scene} for scene in train],
        valset=[{"scene": scene} for scene in val],
        objective=OBJECTIVE,
        background=BACKGROUND,
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
        )
    print(
        f"best validation similarity: {result.val_aggregate_scores[result.best_idx]:.4f}\n"
        f"candidate: {run_root / 'best_candidate.json'}"
    )


if __name__ == "__main__":
    main()
