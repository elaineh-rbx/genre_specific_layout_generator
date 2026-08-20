"""Train stage-specific Gemini policies on 600 upstream scenes.

The 600 upstream scenes are GEPA's reflection/training pool and the frozen golden 75
are the validation set. GPT Image 2 targets are evaluator-only. Candidate recaptioning
can be enabled for reflection feedback, but is never part of the objective.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import pathlib
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

from PIL import Image, ImageStat

from layoutgen import paths
from layoutgen.backends import images
from layoutgen.optimize.gepa_images import (
    AzureReflectionLM,
    RenderEvaluator,
    SEED_CANDIDATE,
    SceneCase,
    TargetStore,
    _candidate_error,
    _candidate_id,
    _valid_image,
    _write_json,
    load_cases,
)
from layoutgen.optimize.gepa_prompt_recaption import GeminiCandidateCaptioner
from layoutgen.optimize.similarity import CompositeImageSimilarity, PyramidEncoder
from layoutgen.optimize.vlm_judge import GatewayVLMJudge
from layoutgen.pipeline import golden


TARGET_ARM = "agent_gpt52_upstream_cf94b18_gptimage2_260815"
DEFAULT_MANIFEST = paths.RUNS / f"{TARGET_ARM}_manifest.json"
DEFAULT_RUN_NAME = "gemini_gepa_upstream600_golden75_v1_260819"
OBJECTIVE = (
    "Improve three global Gemini image-stage execution policies using 600 diverse "
    "upstream scenes. Maximize the validation objective on frozen golden scenes: 35% "
    "spatially weighted target-image similarity, 25% visible prompt adherence, 25% "
    "layout-contract adherence, and 15% isometric-camera adherence. A camera score below "
    "0.8 proportionally gates the score; letterboxed or bordered images score zero. "
    "Policies must remain global and must not contain scene-specific wording."
)
BACKGROUND = (
    "The iso, topdown, and plan strings are independent mutable stage policies. Every "
    "stored GPT Image 2 prompt remains immutable inside a canonical-contract wrapper. "
    "Gemini receives only that contract, the selected global policy, and normal pipeline "
    "references from its own earlier stage or a deterministic authored plan. It never "
    "receives the GPT target. Use the immutable prompt/layout contract and the direct VLM "
    "judge's missing-requirement, topology, count, camera, and framing errors to diagnose "
    "policy changes. "
    "Require a natural full-bleed square image with no black bars, frame, UI, or labels."
)
RECAPTION_OBJECTIVE = (
    " Candidate recaptions are reflection evidence only and never part of the score."
)
RECAPTION_BACKGROUND = (
    " After generation, Gemini blindly recaptions the candidate. Compare that "
    "visible-evidence caption against the immutable contract. Do not optimize caption "
    "wording or caption similarity."
)


class Captioner(Protocol):
    def caption(self, image: pathlib.Path) -> dict: ...


def optimization_context(recaption: bool) -> tuple[str, str]:
    """Return reflection instructions for the selected ablation."""
    if recaption:
        return OBJECTIVE + RECAPTION_OBJECTIVE, BACKGROUND + RECAPTION_BACKGROUND
    return OBJECTIVE, BACKGROUND


def load_exact_cases(
    specs: pathlib.Path = golden.AGENT_GATEWAY,
    manifest_path: pathlib.Path = DEFAULT_MANIFEST,
) -> dict[str, SceneCase]:
    """Join strict specs to the exact prompts used for frozen GPT target generation."""
    cases = load_cases(specs)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    joined: dict[str, SceneCase] = {}
    for row in manifest.get("scenes", []):
        scene = str(row.get("scene", ""))
        base = cases.get(scene)
        iso = row.get("isometric") or {}
        topdown = row.get("topdown") or {}
        iso_prompt = str(iso.get("prompt") or "").strip()
        first_prompt = str(topdown.get("prompt") or "").strip()
        order = str(row.get("render_order") or "").strip()
        if base and iso_prompt and first_prompt and order in {"std", "p6", "layout"}:
            joined[scene] = dataclasses.replace(
                base,
                order=order,
                iso_prompt=iso_prompt,
                first_prompt=first_prompt,
                author_prompt=str(row.get("author_prompt") or base.author_prompt),
            )
    return joined


def select_training_scenes(
    cases: dict[str, SceneCase],
    size: int = 600,
    seed: int = 19,
) -> tuple[list[str], list[str]]:
    """Deterministically select exactly ``size`` successful P-prefixed scenes."""
    eligible = sorted(scene for scene in cases if scene.startswith("P"))
    if len(eligible) < size:
        raise ValueError(f"need {size} upstream scenes, found {len(eligible)}")

    def rank(scene: str) -> str:
        return hashlib.sha256(f"{seed}:upstream:{scene}".encode()).hexdigest()

    selected_set = set(sorted(eligible, key=rank)[:size])
    return (
        sorted(selected_set),
        sorted(scene for scene in eligible if scene not in selected_set),
    )


def golden_validation_scenes(cases: dict[str, SceneCase]) -> list[str]:
    scenes = sorted(
        scene
        for scene in cases
        if scene.isdigit() and 1 <= int(scene) <= 75
    )
    if len(scenes) != 75:
        raise ValueError(f"expected 75 golden validation scenes, found {len(scenes)}")
    return scenes


def frame_errors(path: pathlib.Path) -> list[str]:
    """Find normalization bars and conspicuous solid-black outer framing."""
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    errors: list[str] = []
    if image.width != image.height:
        errors.append(f"output is {image.width}x{image.height}, not square")
    width, height = image.size
    vertical = max(1, round(height * 0.06))
    horizontal = max(1, round(width * 0.06))
    bands = (
        ("top", (0, 0, width, vertical)),
        ("bottom", (0, height - vertical, width, height)),
        ("left", (0, 0, horizontal, height)),
        ("right", (width - horizontal, 0, width, height)),
    )
    gray = image.convert("L")
    for label, box in bands:
        stat = ImageStat.Stat(gray.crop(box))
        if stat.mean[0] < 4 and stat.extrema[0][1] < 12:
            errors.append(f"solid black {label} letterbox/border band")
    return errors


def robust_objective(scores: list[float]) -> float:
    """80% mean plus 20% mean of the lowest-scoring quintile."""
    if not scores:
        raise ValueError("robust objective requires at least one score")
    lower_count = max(1, math.ceil(len(scores) * 0.2))
    lower = sorted(scores)[:lower_count]
    return 0.8 * statistics.fmean(scores) + 0.2 * statistics.fmean(lower)


def _reflection_contract(case: SceneCase) -> dict:
    return {
        "author_request": case.author_prompt[:6_000],
        "layout_addendum": case.addendum[:4_000],
        "shape": case.spec.get("shape"),
        "options": case.spec.get("options"),
        "layout": case.spec.get("layout"),
        "render": case.spec.get("render"),
    }


class RecaptioningRenderEvaluator(RenderEvaluator):
    """Add contract feedback, hard framing, and optional candidate recaptioning."""

    def __init__(
        self,
        *args,
        captioner: Captioner | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.captioner = captioner

    def _caption(
        self,
        image: pathlib.Path,
        destination: pathlib.Path,
    ) -> dict:
        if self.captioner is None:
            raise RuntimeError("candidate recaptioning is disabled")
        if destination.is_file():
            value = json.loads(destination.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                return value
        value = self.captioner.caption(image)
        _write_json(destination, value)
        return value

    def evaluate(
        self,
        candidate: dict[str, str],
        example: dict[str, str],
    ) -> tuple[float, dict]:
        score, info = super().evaluate(candidate, example)
        scene = example.get("scene", "")
        case = self.cases.get(scene)
        if not case or not all(
            isinstance(candidate.get(stage), str)
            for stage in ("iso", "topdown", "plan")
        ):
            return score, info
        output_root = self.run_root / "renders" / _candidate_id(candidate, case) / scene
        generated = output_root / "iso.jpg"
        if not _valid_image(generated):
            return score, info

        errors = frame_errors(generated)
        contract = _reflection_contract(case)
        info["Immutable contract for caption comparison"] = contract
        caption = None
        stage_feedback = ""
        if self.captioner is not None:
            try:
                caption = self._caption(
                    generated,
                    output_root / "candidate_recaption.json",
                )
                caption_feedback = json.dumps(caption, ensure_ascii=False)
            except RuntimeError as exc:
                caption = {"error": str(exc)}
                caption_feedback = f"Recaption attempt failed after retries: {exc}"
            info["Gemini blind candidate recaption"] = caption
            info["Caption role"] = (
                "Reflection-only visible evidence; do not use caption similarity as a "
                "score."
            )
            stage_feedback = (
                "\nBlind candidate recaption: "
                f"{caption_feedback}\nCompare it against the immutable contract to "
                "identify omissions, wrong counts/topology, camera, and framing."
            )
        active = ["iso"]
        if case.order == "p6":
            active.append("plan")
        elif case.order == "layout":
            active.append("topdown")
        for stage in active:
            key = f"{stage}_specific_info"
            value = info.setdefault(key, {"scores": {"combined_objective": score}})
            value["Immutable contract"] = contract
            if caption is not None:
                value["Candidate recaption"] = caption
            value["Feedback"] = str(value.get("Feedback", "")) + stage_feedback

        if errors:
            score = 0.0
            failure = "Hard framing gate failed: " + "; ".join(errors)
            info["Framing gate"] = {"passed": False, "errors": errors}
            info["Feedback"] = failure + ". " + str(info.get("Feedback", ""))
            if isinstance(info.get("scores"), dict):
                info["scores"]["combined_objective"] = 0.0
            for stage in active:
                info[f"{stage}_specific_info"]["scores"]["combined_objective"] = 0.0
                info[f"{stage}_specific_info"]["Feedback"] = (
                    failure + ". " + info[f"{stage}_specific_info"]["Feedback"]
                )
        else:
            info["Framing gate"] = {"passed": True, "errors": []}
        return score, info


class WeakestContractStageSelector:
    """Mutate the weakest active stage using final contract-objective scores."""

    def __call__(
        self,
        state,
        trajectories: list[dict],
        subsample_scores: list[float],
        candidate_idx: int,
        candidate: dict[str, str],
    ) -> list[str]:
        del state, subsample_scores, candidate_idx
        observed: dict[str, list[float]] = {"iso": [], "topdown": [], "plan": []}
        for trajectory in trajectories:
            scores = trajectory.get("scores") or {}
            value = float(scores.get("combined_objective", 0.0))
            observed["iso"].append(value)
            if trajectory.get("Render order") == "p6":
                observed["plan"].append(value)
            elif trajectory.get("Render order") == "layout":
                observed["topdown"].append(value)
        averages = {
            stage: statistics.fmean(values)
            for stage, values in observed.items()
            if values and stage in candidate
        }
        return [min(averages, key=averages.get)] if averages else ["iso"]


def _serializable(value):
    if isinstance(value, dict):
        return {key: _serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serializable(item) for item in value]
    path = getattr(value, "path", None)
    return {"path": str(path)} if path else value


def _score_winner(
    evaluator: RecaptioningRenderEvaluator,
    candidate: dict[str, str],
    scenes: list[str],
    destination: pathlib.Path,
    workers: int,
) -> list[dict]:
    def evaluate(scene: str) -> dict:
        score, info = evaluator.evaluate(candidate, {"scene": scene})
        return {"scene": scene, "score": float(score), "feedback": _serializable(info)}

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        rows = list(pool.map(evaluate, scenes))
    _write_json(destination, rows)
    return rows


def _run_name() -> str:
    return DEFAULT_RUN_NAME


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", default=_run_name())
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--specs", type=pathlib.Path, default=golden.AGENT_GATEWAY)
    parser.add_argument("--target-arm", default=TARGET_ARM)
    parser.add_argument("--train-size", type=int, default=600)
    parser.add_argument(
        "--seed-candidate",
        type=pathlib.Path,
        help="stage-policy JSON used to seed this run",
    )
    parser.add_argument("--image-model", default="gemini-3.1-flash-image")
    parser.add_argument("--caption-model", default="gemini-3.1-flash-image")
    parser.add_argument("--judge-model", default="gpt-5.5")
    parser.add_argument("--reflection-deployment", default="gpt-5.2")
    parser.add_argument("--max-metric-calls", type=int, default=250)
    parser.add_argument("--reflection-minibatch", type=int, default=8)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=19)
    parser.add_argument(
        "--no-recaption",
        action="store_true",
        help="omit candidate recaptions from GEPA reflection feedback",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    recaption_enabled = not args.no_recaption
    seed_candidate = (
        json.loads(args.seed_candidate.read_text(encoding="utf-8"))
        if args.seed_candidate
        else SEED_CANDIDATE
    )
    if error := _candidate_error(seed_candidate):
        raise ValueError(f"invalid --seed-candidate: {error}")

    cases = load_exact_cases(args.specs, args.manifest)
    train, excluded = select_training_scenes(cases, args.train_size, args.seed)
    validation = golden_validation_scenes(cases)
    run_root = paths.RUN / "gepa" / args.run_name
    run_root.mkdir(parents=True, exist_ok=True)
    targets = TargetStore(args.target_arm)
    target_paths = targets.preflight(train + validation, ("iso",))
    order_counts = {
        order: sum(cases[scene].order == order for scene in train)
        for order in ("std", "p6", "layout")
    }
    manifest = {
        "run_name": args.run_name,
        "source_manifest": str(args.manifest),
        "target_arm": args.target_arm,
        "target_role": "evaluation-only; never passed to Gemini",
        "training_scenes": train,
        "training_order_counts": order_counts,
        "excluded_successful_upstream_scenes": excluded,
        "validation_scenes": validation,
        "validation_role": "GEPA model selection; not an unbiased final test",
        "candidate_recaption": {
            "enabled": recaption_enabled,
            "model": args.caption_model if recaption_enabled else None,
            "role": "reflection-only; absent from objective",
        },
        "objective": {
            "image_similarity": 0.35,
            "prompt_adherence": 0.25,
            "layout_following": 0.25,
            "isometric_camera": 0.15,
            "image_similarity_components": {
                "semantic": 0.35,
                "spatial": 0.40,
                "structure": 0.25,
            },
            "minimum_camera_score": 0.8,
            "framing_gate": "zero for non-square or solid-black letterbox/border",
            "validation_aggregate": "0.8*mean + 0.2*mean(lowest 20%)",
        },
        "models": {
            "generation": args.image_model,
            "caption": args.caption_model if recaption_enabled else None,
            "judge": args.judge_model,
            "reflection": args.reflection_deployment,
        },
        "max_metric_calls": args.max_metric_calls,
        "reflection_minibatch": args.reflection_minibatch,
        "workers": args.workers,
        "seed": args.seed,
        "seed_candidate": seed_candidate,
        "seed_candidate_file": (
            str(args.seed_candidate) if args.seed_candidate else None
        ),
        "targets": target_paths,
    }
    _write_json(run_root / "manifest.json", manifest)
    if args.dry_run:
        print(
            f"Preflight complete: {len(train)} training + {len(validation)} validation "
            f"scenes; orders={order_counts}; {run_root / 'manifest.json'}",
            flush=True,
        )
        return

    scorer = CompositeImageSimilarity(
        PyramidEncoder(),
        semantic_weight=0.35,
        spatial_weight=0.40,
        structure_weight=0.25,
    )
    evaluator = RecaptioningRenderEvaluator(
        cases,
        images.LLMGatewayProvider(model=args.image_model),
        scorer,
        targets,
        run_root,
        captioner=(
            GeminiCandidateCaptioner(model=args.caption_model)
            if recaption_enabled
            else None
        ),
        visual_feedback=True,
        iso_only=True,
        vlm_judge=GatewayVLMJudge(
            model=args.judge_model,
            cache_root=run_root / "judge_cache",
        ),
        judge_weights=(0.25, 0.25, 0.15, 0.35),
        minimum_camera_score=0.8,
        camera_retries=0,
        camera_direct_fallback=False,
    )

    from gepa.optimize_anything import (
        EngineConfig,
        GEPAConfig,
        ReflectionConfig,
        optimize_anything,
    )

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
            reflection_lm=AzureReflectionLM(
                deployment=args.reflection_deployment
            ),
            reflection_minibatch_size=min(args.reflection_minibatch, len(train)),
            module_selector=WeakestContractStageSelector(),
            skip_perfect_score=True,
            perfect_score=1.0,
        ),
    )
    objective, background = optimization_context(recaption_enabled)
    result = optimize_anything(
        seed_candidate=seed_candidate,
        evaluator=evaluator.evaluate,
        dataset=[{"scene": scene} for scene in train],
        valset=[{"scene": scene} for scene in validation],
        objective=objective,
        background=background,
        config=config,
    )
    result_dict = result.to_dict()
    _write_json(run_root / "result.json", result_dict)

    robust_rows = []
    for index, subscores in enumerate(result_dict["val_subscores"]):
        values = [float(value) for value in subscores.values()]
        robust_rows.append(
            {
                "candidate_index": index,
                "complete_validation": len(values) == len(validation),
                "validation_count": len(values),
                "mean": statistics.fmean(values) if values else 0.0,
                "lower_tail_mean": (
                    statistics.fmean(
                        sorted(values)[: max(1, math.ceil(len(values) * 0.2))]
                    )
                    if values
                    else 0.0
                ),
                "robust_objective": robust_objective(values) if values else 0.0,
            }
        )
    complete = [row for row in robust_rows if row["complete_validation"]]
    if not complete:
        raise RuntimeError("GEPA produced no candidate with complete golden validation")
    selected = max(complete, key=lambda row: row["robust_objective"])
    best_index = int(selected["candidate_index"])
    best = result_dict["candidates"][best_index]
    _write_json(
        run_root / "robust_selection.json",
        {"selected_candidate_index": best_index, "candidates": robust_rows},
    )
    _write_json(run_root / "best_candidate.json", best)
    rows = _score_winner(
        evaluator,
        best,
        validation,
        run_root / "golden75_scores.json",
        args.workers,
    )
    print(
        f"Selected candidate {best_index}: robust={selected['robust_objective']:.4f}, "
        f"mean={statistics.fmean(row['score'] for row in rows):.4f}; "
        f"{run_root / 'best_candidate.json'}",
        flush=True,
    )


if __name__ == "__main__":
    main()
