"""GEPA-optimize a Gemini adapter around exact GPT prompts with recaption feedback.

The exact GPT Image 2 prompt is immutable inside ``{prompt}``. Gemini generates from the
adapted text, blindly captions its own candidate, and GEPA receives both that caption and
Gemini's frozen caption of the GPT target. Image similarity remains the only objective.
Targets and target captions are evaluation-only and are never generation inputs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import random
import re
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
    _valid_image,
    _write_answer,
    _write_json,
)
from layoutgen.optimize.similarity import CompositeImageSimilarity, PyramidEncoder


TARGET_ARM = "agent_gpt52_upstream_cf94b18_gptimage2_260815"
DEFAULT_PROMPTS = paths.RUNS / f"{TARGET_ARM}_prompts.jsonl"
DEFAULT_CAPTIONS = (
    paths.RUN
    / "gemini_caption_gap"
    / "all75_iso_caption_only_260818"
    / "records.jsonl"
)
SEED_CANDIDATE = {"adapter": "{prompt}"}

OBJECTIVE = (
    "Improve one global Gemini execution adapter around immutable exact GPT Image 2 "
    "prompts so generated images maximize perceptual and structural similarity to frozen "
    "GPT targets across unseen scenes. Keep {prompt} exactly once. Image similarity is "
    "the objective; captions are diagnostic feedback. Never add scene-specific wording."
)

BACKGROUND = (
    "The seed adapter is exactly {prompt}. For every candidate, Gemini generates from the "
    "adapted GPT prompt without receiving the target image. Gemini then blindly captions "
    "its candidate. Reflection receives the frozen Gemini caption of the GPT target, the "
    "candidate caption, image similarity components, and a visual comparison. Use caption "
    "differences to diagnose missing objects, counts, topology, camera, framing, and "
    "materials, but optimize the global adapter rather than memorizing any scene. Require "
    "a natural square 1:1 image with no bars or border. This is target-leaky evaluation."
)

CANDIDATE_CAPTION_PROMPT = """Blindly describe this generated game-environment image.
Do not infer its source prompt or intended design. Report only visible evidence. Be
specific about camera, framing, footprint/topology, routes and openings, object counts and
placements, materials, lighting, labels/overlays, borders, and letterboxing.

Return JSON only:
{
  "summary": "concise complete visible description",
  "camera_and_framing": "visible camera and canvas treatment",
  "topology": "visible footprint, routes, zones, openings, and connectivity",
  "objects": ["visible object/count/placement", "..."],
  "materials_and_lighting": "visible appearance",
  "overlays_and_borders": ["visible text/UI/border/letterbox issue", "..."]
}
"""


@dataclass(frozen=True)
class PromptCase:
    scene: str
    order: str
    prompt: str
    target_caption: dict


def _json_rows(path: pathlib.Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_cases(
    prompts_path: pathlib.Path,
    captions_path: pathlib.Path,
    orders: set[str],
) -> dict[str, PromptCase]:
    captions = {
        str(row["scene"]): row["blind_caption"]
        for row in _json_rows(captions_path)
        if row.get("stage") == "iso"
    }
    cases: dict[str, PromptCase] = {}
    for row in _json_rows(prompts_path):
        scene = str(row.get("scene", ""))
        order = str(row.get("render_order", ""))
        iso = row.get("isometric") or {}
        if (
            not scene.isdigit()
            or not 1 <= int(scene) <= 75
            or order not in orders
            or iso.get("reference") is not None
        ):
            continue
        target_caption = captions.get(scene)
        if not isinstance(target_caption, dict):
            raise ValueError(f"missing frozen Gemini target caption for scene {scene}")
        prompt = str(iso.get("prompt") or "").strip()
        if not prompt:
            raise ValueError(f"missing exact GPT isometric prompt for scene {scene}")
        cases[scene] = PromptCase(scene, order, prompt, target_caption)
    if not cases:
        raise ValueError("no self-contained GPT prompt cases matched the selected orders")
    return cases


def _candidate_error(candidate: dict[str, str]) -> str:
    template = candidate.get("adapter")
    if not isinstance(template, str) or not template.strip():
        return "candidate must contain a non-empty 'adapter' template"
    if template.count("{prompt}") != 1:
        return "the adapter must contain {prompt} exactly once"
    if len(template) > 8_000:
        return "the adapter exceeds 8,000 characters"
    return ""


def _candidate_id(candidate: dict[str, str]) -> str:
    return hashlib.sha256(candidate["adapter"].encode("utf-8")).hexdigest()[:16]


def _generation_prompt(candidate: dict[str, str], case: PromptCase) -> str:
    return candidate["adapter"].replace("{prompt}", case.prompt)


def _json_object(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        text = text[first_newline + 1 :] if first_newline >= 0 else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].rstrip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("caption response contains no JSON object") from None
        candidate = re.sub(r",\s*([}\]])", r"\1", text[start : end + 1])
        value = json.loads(candidate)
    if not isinstance(value, dict):
        raise ValueError("caption response must be a JSON object")
    return value


class GeminiCandidateCaptioner:
    def __init__(self, model: str = "gemini-3.1-flash-image", retries: int = 3) -> None:
        self.reflection = GatewayReflectionLM(model=model)
        self.retries = retries

    def caption(self, image: pathlib.Path) -> dict:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": CANDIDATE_CAPTION_PROMPT},
                    images.LLMGatewayProvider._part(image),
                ],
            }
        ]
        last: Exception | None = None
        for _ in range(self.retries):
            try:
                return _json_object(self.reflection(messages))
            except (RuntimeError, ValueError) as exc:
                last = exc
        raise RuntimeError(f"candidate recaption failed after {self.retries}: {last}")


class AdapterModuleSelector:
    def __call__(
        self,
        state,
        trajectories: list[dict],
        subsample_scores: list[float],
        candidate_idx: int,
        candidate: dict[str, str],
    ) -> list[str]:
        del state, trajectories, subsample_scores, candidate_idx, candidate
        return ["adapter"]


class PromptRecaptionEvaluator:
    def __init__(
        self,
        cases: dict[str, PromptCase],
        provider: Provider,
        captioner: GeminiCandidateCaptioner,
        scorer: Scorer,
        targets: TargetStore,
        run_root: pathlib.Path,
        *,
        visual_feedback: bool = True,
    ) -> None:
        self.cases = cases
        self.provider = provider
        self.captioner = captioner
        self.scorer = scorer
        self.targets = targets
        self.run_root = run_root
        self.visual_feedback = visual_feedback

    def render_path(self, candidate: dict[str, str], scene: str) -> pathlib.Path:
        return self.run_root / "renders" / _candidate_id(candidate) / scene / "iso.png"

    def render_prompt(self, candidate: dict[str, str], scene: str) -> str:
        return _generation_prompt(candidate, self.cases[scene])

    def _render(self, candidate: dict[str, str], case: PromptCase) -> pathlib.Path:
        destination = self.render_path(candidate, case.scene)
        if not _valid_image(destination):
            destination.parent.mkdir(parents=True, exist_ok=True)
            _write_answer(
                self.provider.generate(_generation_prompt(candidate, case)),
                destination,
            )
            _write_json(
                destination.parent / "prompt.json",
                {
                    "scene": case.scene,
                    "adapter": candidate["adapter"],
                    "exact_gpt_prompt": case.prompt,
                    "generation_prompt": _generation_prompt(candidate, case),
                },
            )
        return destination

    def _caption(self, generated: pathlib.Path) -> tuple[dict | None, str | None]:
        path = generated.parent / "candidate_caption.json"
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8")), None
        try:
            caption = self.captioner.caption(generated)
        except RuntimeError as exc:
            return None, str(exc)
        _write_json(path, caption)
        return caption, None

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
            ("Gemini adapted-GPT-prompt candidate", generated, tile),
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
                "scores": {"image_similarity": 0.0},
                "adapter_specific_info": {
                    "Feedback": error,
                    "scores": {"image_similarity": 0.0},
                },
            }
        scene = example["scene"]
        case = self.cases[scene]
        generated = self._render(candidate, case)
        target = self.targets.get(scene, "iso")
        metrics = self.scorer.compare(generated, target)
        candidate_caption, caption_error = self._caption(generated)
        feedback = (
            "Use the target-versus-candidate caption differences and visual comparison to "
            "improve one reusable Gemini adapter. Preserve the exact GPT prompt inside "
            "{prompt}. Correct missing counts, topology, camera, framing, materials, and "
            "letterboxing without adding scene-specific facts."
        )
        side_info = {
            "Scene": scene,
            "Exact GPT Image 2 prompt": case.prompt,
            "Frozen Gemini caption of GPT target": case.target_caption,
            "Gemini caption of candidate": candidate_caption,
            "Candidate caption error": caption_error,
            "Generation prompt": _generation_prompt(candidate, case),
            "Feedback": feedback,
            "scores": {"image_similarity": metrics.score},
            "image_metrics": metrics.as_dict(),
            "adapter_specific_info": {
                "Feedback": feedback,
                "scores": {"image_similarity": metrics.score},
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


def _split(scenes: list[str], seed: int) -> tuple[list[str], list[str]]:
    shuffled = list(scenes)
    random.Random(seed).shuffle(shuffled)
    validation = set(shuffled[: max(1, round(len(shuffled) * 0.2))])
    return (
        [scene for scene in scenes if scene not in validation],
        [scene for scene in scenes if scene in validation],
    )


def _score_candidate(
    evaluator: PromptRecaptionEvaluator,
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
    evaluator: PromptRecaptionEvaluator,
    candidate: dict[str, str],
    scenes: list[str],
    destination: pathlib.Path,
    scores: list[dict],
) -> None:
    image_root = destination / "images" / "isometric"
    for scene in scenes:
        target = image_root / f"{scene}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(evaluator.render_path(candidate, scene), target)
    _write_json(
        destination / "s3_manifest.json",
        {
            "method": "GEPA exact GPT prompt with Gemini candidate recaption feedback",
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
    return f"gemini_gptprompt_recaption_gepa_{stamp}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", default=_run_name())
    parser.add_argument("--prompts", type=pathlib.Path, default=DEFAULT_PROMPTS)
    parser.add_argument("--captions", type=pathlib.Path, default=DEFAULT_CAPTIONS)
    parser.add_argument("--orders", default="std")
    parser.add_argument("--target-arm", default=TARGET_ARM)
    parser.add_argument("--image-model", default="gemini-3.1-flash-image")
    parser.add_argument(
        "--reflection-provider",
        choices=("azure", "gateway"),
        default="azure",
    )
    parser.add_argument("--reflection-deployment", default="gpt-5.2")
    parser.add_argument("--reflection-model", default="gemini-3.1-flash-image")
    parser.add_argument("--max-metric-calls", type=int, default=45)
    parser.add_argument("--patience", type=int, default=4)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--reflection-minibatch", type=int, default=2)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--no-visual-feedback", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or args.max_metric_calls < 1:
        raise ValueError("--workers and --max-metric-calls must be positive")
    orders = {part.strip() for part in args.orders.split(",") if part.strip()}
    cases = load_cases(args.prompts, args.captions, orders)
    scenes = sorted(cases)
    train, val = _split(scenes, args.seed)
    run_root = paths.RUN / "gepa" / args.run_name
    run_root.mkdir(parents=True, exist_ok=True)
    targets = TargetStore(args.target_arm)
    target_paths = targets.preflight(scenes, ("iso",))
    _write_json(
        run_root / "manifest.json",
        {
            "run_name": args.run_name,
            "method": "GEPA exact GPT prompt with Gemini recaption feedback",
            "target_leakage": True,
            "prompts": str(args.prompts),
            "captions": str(args.captions),
            "orders": sorted(orders),
            "selected_scenes": scenes,
            "train_scenes": train,
            "val_scenes": val,
            "image_model": args.image_model,
            "reflection_provider": args.reflection_provider,
            "reflection_model": (
                args.reflection_deployment
                if args.reflection_provider == "azure"
                else args.reflection_model
            ),
            "max_metric_calls": args.max_metric_calls,
            "patience": args.patience,
            "similarity": {
                "encoder": "pyramid",
                "weights": {"semantic": 0.55, "spatial": 0.30, "structure": 0.15},
            },
            "seed_candidate": SEED_CANDIDATE,
            "targets": target_paths,
        },
    )
    if args.dry_run:
        print(
            f"GPT-prompt recaption GEPA preflight: {len(train)} train + {len(val)} "
            f"validation scenes ({len(scenes)} self-contained total)\n"
            f"{run_root / 'manifest.json'}"
        )
        return

    evaluator = PromptRecaptionEvaluator(
        cases,
        images.LLMGatewayProvider(model=args.image_model),
        GeminiCandidateCaptioner(model=args.image_model),
        CompositeImageSimilarity(PyramidEncoder()),
        targets,
        run_root,
        visual_feedback=not args.no_visual_feedback,
    )
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
            module_selector=AdapterModuleSelector(),
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
        raise ValueError(f"GEPA returned invalid adapter: {error}")
    _write_json(run_root / "best_candidate.json", best)
    _write_json(run_root / "result.json", result.to_dict())
    scores = _score_candidate(
        evaluator,
        best,
        scenes,
        run_root / "final_scores.json",
        args.workers,
    )
    publish_root = paths.RESULTS / "gepa" / args.run_name
    _publish(evaluator, best, scenes, publish_root, scores)
    mean = statistics.mean(float(row["score"]) for row in scores)
    print(
        f"best validation similarity: "
        f"{result.val_aggregate_scores[result.best_idx]:.4f}\n"
        f"final selected-scene similarity: {mean:.4f}\n"
        f"candidate: {run_root / 'best_candidate.json'}\n"
        f"viewer artifacts: {publish_root}"
    )


if __name__ == "__main__":
    main()
