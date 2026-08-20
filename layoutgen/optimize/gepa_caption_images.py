"""GEPA-optimize a global Gemini image template around blind GPT-target captions.

This is intentionally target-leaky: every immutable caption was produced by inspecting a
GPT Image 2 target. GEPA may also inspect target-versus-candidate comparison sheets, but
the target image is never attached to Gemini image generation. The held-out split tests
whether one global caption template transfers instead of memorizing scene-specific text.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import shutil
import statistics
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from PIL import Image, ImageDraw

from layoutgen import paths
from layoutgen.backends import images
from layoutgen.optimize.gepa_images import (
    AzureReflectionLM,
    GatewayReflectionLM,
    Provider,
    Scorer,
    TargetStore,
    _all_75,
    _selected_cases,
    _split_all_75,
    _valid_image,
    _write_answer,
    _write_json,
)
from layoutgen.optimize.similarity import CompositeImageSimilarity, PyramidEncoder


DEFAULT_CAPTION_RUN = (
    paths.RESULTS / "t2i" / "golden75_gemini_caption_summary_260818"
)
DEFAULT_RECORDS = DEFAULT_CAPTION_RUN / "scores.jsonl"
DEFAULT_SEED_IMAGES = DEFAULT_CAPTION_RUN / "images"
TARGET_ARM = "agent_gpt52_upstream_cf94b18_gptimage2_260815"
SEED_CANDIDATE = {"caption": "{caption}"}

OBJECTIVE = (
    "Improve one global caption-to-image prompt template so Gemini renders are as "
    "perceptually and structurally similar as possible to frozen GPT Image 2 targets "
    "across unseen blind captions. Higher similarity is better. Keep the required "
    "{caption} placeholder exactly once and never add scene-specific wording."
)

BACKGROUND = (
    "Each example supplies an immutable blind caption derived from a GPT Image 2 target. "
    "Only the global template around {caption} is mutable. The seed template is exactly "
    "{caption}, matching the existing caption-only experiment. Frozen GPT targets are "
    "evaluation and visual-reflection inputs only; they are never attached to Gemini "
    "generation. Optimize transferable camera, framing, composition, topology, material, "
    "and no-overlay guidance without inventing facts absent from a caption. This is a "
    "target-leaky diagnostic, not a fair benchmark."
)


@dataclass(frozen=True)
class CaptionCase:
    scene: str
    order: str
    caption: str


def load_cases(path: pathlib.Path) -> dict[str, CaptionCase]:
    cases: dict[str, CaptionCase] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("stage") != "iso":
            continue
        scene = str(row["scene"])
        blind = row.get("blind_caption") or {}
        caption = str(row.get("caption") or blind.get("summary") or "").strip()
        if not caption:
            raise ValueError(f"scene {scene} has no caption text")
        if scene in cases:
            raise ValueError(f"duplicate isometric caption for scene {scene}")
        cases[scene] = CaptionCase(
            scene=scene,
            order=str(row.get("render_order") or "std"),
            caption=caption,
        )
    if not cases:
        raise ValueError(f"no isometric caption records in {path}")
    return cases


def _candidate_error(candidate: dict[str, str]) -> str:
    template = candidate.get("caption")
    if not isinstance(template, str) or not template.strip():
        return "candidate must contain a non-empty 'caption' template"
    if template.count("{caption}") != 1:
        return "the 'caption' template must contain {caption} exactly once"
    if len(template) > 8_000:
        return "the 'caption' template exceeds 8,000 characters"
    return ""


def _candidate_id(candidate: dict[str, str]) -> str:
    encoded = candidate["caption"].encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _prompt(candidate: dict[str, str], case: CaptionCase) -> str:
    return candidate["caption"].replace("{caption}", case.caption)


class CaptionModuleSelector:
    def __call__(
        self,
        state,
        trajectories: list[dict],
        subsample_scores: list[float],
        candidate_idx: int,
        candidate: dict[str, str],
    ) -> list[str]:
        del state, trajectories, subsample_scores, candidate_idx, candidate
        return ["caption"]


class CaptionRenderEvaluator:
    def __init__(
        self,
        cases: dict[str, CaptionCase],
        provider: Provider,
        scorer: Scorer,
        targets: TargetStore,
        run_root: pathlib.Path,
        *,
        seed_images: pathlib.Path | None = None,
        visual_feedback: bool = True,
    ) -> None:
        self.cases = cases
        self.provider = provider
        self.scorer = scorer
        self.targets = targets
        self.run_root = run_root
        self.seed_images = seed_images
        self.visual_feedback = visual_feedback

    def render_path(self, candidate: dict[str, str], scene: str) -> pathlib.Path:
        return self.run_root / "renders" / _candidate_id(candidate) / scene / "iso.png"

    def render_prompt(self, candidate: dict[str, str], scene: str) -> str:
        return _prompt(candidate, self.cases[scene])

    def _seed_source(self, scene: str) -> pathlib.Path | None:
        if self.seed_images is None:
            return None
        source = self.seed_images / f"{scene}_iso.png"
        return source if _valid_image(source) else None

    def _render(self, candidate: dict[str, str], case: CaptionCase) -> pathlib.Path:
        destination = self.render_path(candidate, case.scene)
        if _valid_image(destination):
            return destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        if candidate == SEED_CANDIDATE and (source := self._seed_source(case.scene)):
            temporary = destination.with_suffix(".part")
            try:
                shutil.copy2(source, temporary)
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
        else:
            answer = self.provider.generate(_prompt(candidate, case))
            _write_answer(answer, destination)
        _write_json(
            destination.parent / "prompt.json",
            {
                "scene": case.scene,
                "candidate_id": _candidate_id(candidate),
                "template": candidate["caption"],
                "caption": case.caption,
                "prompt": _prompt(candidate, case),
            },
        )
        return destination

    @staticmethod
    def _comparison(
        target: pathlib.Path,
        generated: pathlib.Path,
        destination: pathlib.Path,
    ) -> pathlib.Path:
        tile, label = 384, 24
        sheet = Image.new("RGB", (tile * 2, tile + label), "white")
        draw = ImageDraw.Draw(sheet)
        for title, path, x in (
            ("GPT Image 2 target", target, 0),
            ("Caption-template candidate", generated, tile),
        ):
            draw.text((x + 5, 5), title, fill="black")
            with Image.open(path) as opened:
                image = opened.convert("RGB")
                image.thumbnail((tile, tile), Image.Resampling.LANCZOS)
            sheet.paste(image, (x + (tile - image.width) // 2, label))
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
                "scores": {"caption_similarity": 0.0},
                "caption_specific_info": {
                    "Feedback": error,
                    "scores": {"caption_similarity": 0.0},
                },
            }
        scene = example["scene"]
        case = self.cases[scene]
        generated = self._render(candidate, case)
        target = self.targets.get(scene, "iso")
        metrics = self.scorer.compare(generated, target)
        feedback = (
            "Improve target likeness using one reusable caption template. Focus on global "
            "composition, camera, footprint topology, object coverage, scale, materials, "
            "and full-frame presentation. Do not add scene IDs or facts absent from the "
            "immutable caption."
        )
        side_info = {
            "Scene": scene,
            "Render order": case.order,
            "Blind caption": case.caption,
            "Generation prompt": _prompt(candidate, case),
            "Feedback": feedback,
            "scores": {"caption_similarity": metrics.score},
            "caption_metrics": metrics.as_dict(),
            "caption_specific_info": {
                "Feedback": feedback,
                "scores": {"caption_similarity": metrics.score},
            },
        }
        if self.visual_feedback:
            from gepa import Image as FeedbackImage

            comparison = self._comparison(
                target,
                generated,
                generated.parent / "comparison.jpg",
            )
            side_info["Visual comparison"] = FeedbackImage(path=str(comparison))
        return metrics.score, side_info


def _score_candidate(
    evaluator: CaptionRenderEvaluator,
    candidate: dict[str, str],
    scenes: list[str],
    destination: pathlib.Path,
    workers: int,
) -> list[dict]:
    def score_scene(scene: str) -> dict:
        score, info = evaluator.evaluate(candidate, {"scene": scene})
        info.pop("Visual comparison", None)
        return {"scene": scene, "score": score, **info}

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        rows = list(pool.map(score_scene, scenes))
    for row in rows:
        print(f"  final {row['scene']}: {row['score']:.4f}", flush=True)
    _write_json(destination, rows)
    return rows


def _publish(
    evaluator: CaptionRenderEvaluator,
    candidate: dict[str, str],
    scenes: list[str],
    destination: pathlib.Path,
    scores: list[dict],
) -> None:
    image_root = destination / "images" / "isometric"
    for scene in scenes:
        source = evaluator.render_path(candidate, scene)
        target = image_root / f"{scene}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    _write_json(
        destination / "s3_manifest.json",
        {
            "method": "GEPA global template over target-derived blind captions",
            "target_leakage": True,
            "best_candidate": candidate,
            "scenes": [
                {
                    "scene": scene,
                    "prompts": {
                        "isometric": {
                            "text": evaluator.render_prompt(candidate, scene),
                        }
                    },
                }
                for scene in scenes
            ],
        },
    )
    _write_json(destination / "scores.json", scores)


def _run_name() -> str:
    stamp = dt.datetime.now(dt.UTC).strftime("%y%m%d_%H%M%S")
    return f"gemini_caption_gepa_{stamp}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", default=_run_name())
    parser.add_argument("--records", type=pathlib.Path, default=DEFAULT_RECORDS)
    parser.add_argument("--seed-images", type=pathlib.Path, default=DEFAULT_SEED_IMAGES)
    parser.add_argument("--target-arm", default=TARGET_ARM)
    parser.add_argument("--image-model", default="gemini-3.1-flash-image")
    parser.add_argument(
        "--reflection-provider",
        choices=("azure", "gateway"),
        default="azure",
    )
    parser.add_argument("--reflection-deployment", default="gpt-5.2")
    parser.add_argument("--reflection-model", default="gemini-3.1-flash-image")
    parser.add_argument("--max-metric-calls", type=int, default=60)
    parser.add_argument("--patience", type=int, default=4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--reflection-minibatch", type=int, default=2)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--no-visual-feedback", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--baseline-only", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be positive")
    if args.max_metric_calls < 1:
        raise ValueError("--max-metric-calls must be positive")

    cases = load_cases(args.records)
    all_scenes = _all_75(cases)
    train, val = _split_all_75(cases, all_scenes, args.seed)
    _selected_cases(cases, train, val)
    run_root = paths.RUN / "gepa" / args.run_name
    run_root.mkdir(parents=True, exist_ok=True)
    targets = TargetStore(args.target_arm)
    target_paths = targets.preflight(all_scenes, ("iso",))
    manifest = {
        "run_name": args.run_name,
        "method": "GEPA global template over target-derived blind captions",
        "target_leakage": True,
        "records": str(args.records),
        "seed_images": str(args.seed_images),
        "target_arm": args.target_arm,
        "target_role": "evaluation/reflection only; never attached to generation",
        "train_scenes": train,
        "val_scenes": val,
        "all_scenes": all_scenes,
        "image_model": args.image_model,
        "reflection_provider": args.reflection_provider,
        "reflection_model": (
            args.reflection_deployment
            if args.reflection_provider == "azure"
            else args.reflection_model
        ),
        "max_metric_calls": args.max_metric_calls,
        "patience": args.patience,
        "workers": args.workers,
        "similarity": {
            "encoder": "pyramid",
            "weights": {"semantic": 0.55, "spatial": 0.30, "structure": 0.15},
        },
        "seed_candidate": SEED_CANDIDATE,
        "targets": target_paths,
    }
    _write_json(run_root / "manifest.json", manifest)
    if args.dry_run:
        print(
            f"GEPA caption preflight ok: {len(train)} train + {len(val)} validation "
            f"scenes; {len(all_scenes)} targets available\n{run_root / 'manifest.json'}"
        )
        return

    evaluator = CaptionRenderEvaluator(
        cases,
        images.LLMGatewayProvider(model=args.image_model),
        CompositeImageSimilarity(PyramidEncoder()),
        targets,
        run_root,
        seed_images=args.seed_images,
        visual_feedback=not args.no_visual_feedback,
    )
    if args.baseline_only:
        rows = _score_candidate(
            evaluator,
            SEED_CANDIDATE,
            all_scenes,
            run_root / "final_all75_scores.json",
            args.workers,
        )
        _write_json(run_root / "best_candidate.json", SEED_CANDIDATE)
        _publish(
            evaluator,
            SEED_CANDIDATE,
            all_scenes,
            paths.RESULTS / "gepa" / args.run_name,
            rows,
        )
        return

    from gepa.optimize_anything import (
        EngineConfig,
        GEPAConfig,
        ReflectionConfig,
        optimize_anything,
    )
    from gepa.utils import NoImprovementStopper

    reflection = (
        AzureReflectionLM(deployment=args.reflection_deployment)
        if args.reflection_provider == "azure"
        else GatewayReflectionLM(model=args.reflection_model)
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
            reflection_lm=reflection,
            reflection_minibatch_size=min(args.reflection_minibatch, len(train)),
            module_selector=CaptionModuleSelector(),
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
    if error := _candidate_error(best):
        raise ValueError(f"GEPA returned an invalid best candidate: {error}")
    _write_json(run_root / "best_candidate.json", best)
    _write_json(run_root / "result.json", result.to_dict())
    rows = _score_candidate(
        evaluator,
        best,
        all_scenes,
        run_root / "final_all75_scores.json",
        args.workers,
    )
    publish_root = paths.RESULTS / "gepa" / args.run_name
    _publish(evaluator, best, all_scenes, publish_root, rows)
    mean = statistics.mean(float(row["score"]) for row in rows)
    print(
        f"best validation similarity: "
        f"{result.val_aggregate_scores[result.best_idx]:.4f}\n"
        f"final all-75 similarity: {mean:.4f}\n"
        f"candidate: {run_root / 'best_candidate.json'}\n"
        f"viewer artifacts: {publish_root}"
    )


if __name__ == "__main__":
    main()
