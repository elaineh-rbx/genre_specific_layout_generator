"""Iteratively revise target-derived captions to improve Gemini image similarity.

For each scene, Gemini sees the frozen GPT Image 2 target and its current generated
candidate, rewrites the caption, and then generates a new image from text only. A
revision becomes the next step only when composite image similarity improves. This is
per-target optimization with strong target leakage, not a deployable prompt benchmark.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import statistics
from concurrent.futures import ThreadPoolExecutor

from layoutgen import paths
from layoutgen.backends import images
from layoutgen.optimize.similarity import CompositeImageSimilarity, PyramidEncoder

from gemini_caption_gap import GeminiCaptioner


DEFAULT_SOURCE = (
    paths.RESULTS
    / "t2i"
    / "golden75_gemini_caption_summary_260818"
)
DEFAULT_RECORDS = DEFAULT_SOURCE / "scores.jsonl"
DEFAULT_IMAGES = DEFAULT_SOURCE / "images"
DEFAULT_SCENES = (
    "0002",
    "0008",
    "0017",
    "0029",
    "0034",
    "0035",
    "0040",
    "0042",
    "0043",
    "0046",
)

REVISION_PROMPT = """You are revising a text-to-image prompt by comparing two images.

IMAGE 1 is the frozen GPT Image 2 target to reproduce.
IMAGE 2 is Gemini's current render from the CURRENT CAPTION.

CURRENT CAPTION:
{caption}

CURRENT SIMILARITY:
composite={score:.6f}; semantic={semantic:.6f}; spatial={spatial:.6f};
structure={structure:.6f}

Write a revised standalone caption that would make gemini-3.1-flash-image reproduce
IMAGE 1 more closely when the model receives text only. Correct concrete differences in
footprint, topology, routes, counts, object placement, camera, framing, scale, materials,
lighting, and exclusions. Preserve accurate details from the current caption. Do not
mention either image, this comparison, scores, or scene IDs. Require a true square 1:1
composition that fills the canvas naturally with no black bars, border, or letterboxing.
Do not use labels, callouts, legends, UI, or watermarks. Keep the revised caption under
1,500 characters.

Return JSON only:
{{
  "differences": ["short concrete difference", "..."],
  "summary": "the complete revised generation caption"
}}
"""

TARGET_ONLY_PROMPT = """Write a complete standalone text-to-image caption for this target.

CURRENT CAPTION:
{caption}

Preserve accurate details, but make the replacement caption more precise about footprint,
topology, routes, counts, object placement, camera, framing, scale, materials, lighting,
and exclusions visible in the target. Require a true square 1:1 composition that fills
the canvas naturally with no black bars, border, or letterboxing. Do not mention the
target, current caption, scores, or scene IDs. Do not request labels, callouts, legends,
UI, or watermarks. Keep the caption under 1,500 characters.

Return JSON only:
{{
  "differences": ["important correction", "..."],
  "summary": "the complete revised generation caption"
}}
"""


def _read_rows(path: pathlib.Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("stage") == "iso":
            rows[str(row["scene"])] = row
    return rows


def _csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _write_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    try:
        temporary.write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_image(answer: images.Answer, destination: pathlib.Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f".part{destination.suffix}")
    try:
        images.normalise(answer.image).save(temporary, format="PNG")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def _valid_image(path: pathlib.Path) -> bool:
    if not path.is_file():
        return False
    try:
        from PIL import Image

        with Image.open(path) as opened:
            opened.verify()
        return True
    except (OSError, ValueError):
        return False


def _default_output() -> pathlib.Path:
    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H_%M_%S")
    return paths.RESULTS / "t2i" / f"gemini_recaption_pilot__{stamp}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=pathlib.Path, default=DEFAULT_RECORDS)
    parser.add_argument("--source-images", type=pathlib.Path, default=DEFAULT_IMAGES)
    parser.add_argument("--scenes", default=",".join(DEFAULT_SCENES))
    parser.add_argument(
        "--target-only-scenes",
        default="",
        help="comma-separated scenes that should skip two-image comparison",
    )
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--model", default=images.GATEWAY_MODEL)
    parser.add_argument("--output", type=pathlib.Path, default=_default_output())
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.iterations < 1:
        raise ValueError("--iterations must be positive")
    if args.workers < 1:
        raise ValueError("--workers must be positive")
    if args.output.exists() and not args.resume:
        raise FileExistsError(f"output already exists: {args.output}")

    rows = _read_rows(args.records)
    scenes = _csv(args.scenes)
    target_only_scenes = set(_csv(args.target_only_scenes))
    missing = sorted(set(scenes) - rows.keys())
    if missing:
        raise ValueError(f"caption records are missing scenes: {', '.join(missing)}")
    unknown_target_only = sorted(target_only_scenes - set(scenes))
    if unknown_target_only:
        raise ValueError(
            "--target-only-scenes are outside --scenes: "
            + ", ".join(unknown_target_only)
        )
    cases = []
    for scene in scenes:
        row = rows[scene]
        source = args.source_images / f"{scene}_iso.png"
        target = pathlib.Path(row["target"])
        if not _valid_image(source):
            raise FileNotFoundError(f"missing seed image: {source}")
        if not _valid_image(target):
            raise FileNotFoundError(f"missing target image: {target}")
        cases.append(
            {
                "scene": scene,
                "caption": str(row["caption"]),
                "source": str(source),
                "target": str(target),
            }
        )
    args.output.mkdir(parents=True, exist_ok=args.resume)
    _write_json(
        args.output / "manifest.json",
        {
            "model": args.model,
            "method": "iterative target/candidate recaption hill climb",
            "target_leakage": True,
            "source_image_attached_to_generation": False,
            "iterations": args.iterations,
            "scenes": scenes,
            "target_only_scenes": sorted(target_only_scenes),
            "cases": cases,
        },
    )
    if args.dry_run:
        print(f"preflight ok: {len(cases)} scenes\n{args.output}")
        return

    def optimize(case: dict) -> dict:
        scene = case["scene"]
        state_path = args.output / "states" / f"{scene}.json"
        if args.resume and state_path.is_file():
            state = json.loads(state_path.read_text(encoding="utf-8"))
        else:
            seed = args.output / "images" / f"{scene}_iter0.png"
            seed.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(case["source"], seed)
            scorer = CompositeImageSimilarity(PyramidEncoder())
            metrics = scorer.compare(seed, pathlib.Path(case["target"])).as_dict()
            state = {
                "scene": scene,
                "target": case["target"],
                "seed_caption": case["caption"],
                "seed_image": str(seed),
                "seed_similarity": metrics,
                "best_caption": case["caption"],
                "best_image": str(seed),
                "best_similarity": metrics,
                "best_iteration": 0,
                "history": [],
            }
            _write_json(state_path, state)

        start = len(state["history"]) + 1
        for iteration in range(start, args.iterations + 1):
            captioner = GeminiCaptioner(model=args.model)
            provider = images.LLMGatewayProvider(model=args.model)
            scorer = CompositeImageSimilarity(PyramidEncoder())
            current = state["best_similarity"]
            print(f"{scene}: recaption iteration {iteration}", flush=True)
            if scene in target_only_scenes or state.get("target_only"):
                revision = captioner.ask(
                    TARGET_ONLY_PROMPT.format(caption=state["best_caption"]),
                    pathlib.Path(state["target"]),
                )
            else:
                try:
                    revision = captioner.ask(
                        REVISION_PROMPT.format(
                            caption=state["best_caption"],
                            score=current["score"],
                            semantic=current["semantic"],
                            spatial=current["spatial"],
                            structure=current["structure"],
                        ),
                        [
                            pathlib.Path(state["target"]),
                            pathlib.Path(state["best_image"]),
                        ],
                    )
                except RuntimeError as exc:
                    print(
                        f"{scene}: two-image recaption failed; using target-only "
                        f"fallback ({exc})",
                        flush=True,
                    )
                    state["target_only"] = True
                    _write_json(state_path, state)
                    revision = captioner.ask(
                        TARGET_ONLY_PROMPT.format(caption=state["best_caption"]),
                        pathlib.Path(state["target"]),
                    )
            candidate_caption = str(revision["summary"]).strip()
            if not candidate_caption:
                raise ValueError(f"{scene}: iteration {iteration} returned an empty caption")
            candidate_image = (
                args.output / "images" / f"{scene}_iter{iteration}.png"
            )
            answer = provider.generate(candidate_caption)
            _write_image(answer, candidate_image)
            metrics = scorer.compare(
                candidate_image,
                pathlib.Path(state["target"]),
            ).as_dict()
            accepted = float(metrics["score"]) > float(current["score"])
            state["history"].append(
                {
                    "iteration": iteration,
                    "caption": candidate_caption,
                    "image": str(candidate_image),
                    "similarity": metrics,
                    "accepted": accepted,
                    "revision": revision,
                }
            )
            if accepted:
                state["best_caption"] = candidate_caption
                state["best_image"] = str(candidate_image)
                state["best_similarity"] = metrics
                state["best_iteration"] = iteration
            _write_json(state_path, state)
            print(
                f"{scene}: {current['score']:.4f} -> {metrics['score']:.4f} "
                f"({'accept' if accepted else 'reject'})",
                flush=True,
            )

        viewer_image = args.output / "images" / f"{scene}_iso.png"
        shutil.copy2(state["best_image"], viewer_image)
        result = {
            **state,
            "generated": str(viewer_image),
            "score_delta": (
                float(state["best_similarity"]["score"])
                - float(state["seed_similarity"]["score"])
            ),
        }
        _write_json(args.output / "rows" / f"{scene}.json", result)
        return result

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(optimize, cases))
    with (args.output / "scores.jsonl").open("w", encoding="utf-8") as destination:
        for result in results:
            destination.write(json.dumps(result, ensure_ascii=False) + "\n")
    baseline = [float(row["seed_similarity"]["score"]) for row in results]
    final = [float(row["best_similarity"]["score"]) for row in results]
    canonical = [
        float(rows[row["scene"]]["baseline_similarity"]["score"])
        for row in results
        if rows[row["scene"]].get("baseline_similarity")
    ]
    _write_json(
        args.output / "summary.json",
        {
            "scenes": len(results),
            "iterations": args.iterations,
            "mean_seed_similarity": statistics.mean(baseline),
            "mean_best_similarity": statistics.mean(final),
            "mean_score_delta": statistics.mean(final) - statistics.mean(baseline),
            "mean_canonical_similarity": (
                statistics.mean(canonical) if canonical else None
            ),
            "mean_vs_canonical_delta": (
                statistics.mean(final) - statistics.mean(canonical)
                if canonical
                else None
            ),
            "improved_scenes": sum(
                float(row["score_delta"]) > 0 for row in results
            ),
            "beats_canonical_scenes": sum(
                float(row["best_similarity"]["score"])
                > float(rows[row["scene"]]["baseline_similarity"]["score"])
                for row in results
                if rows[row["scene"]].get("baseline_similarity")
            ),
            "target_leakage_warning": (
                "each caption revision inspected the GPT target and current candidate"
            ),
        },
    )
    print(f"wrote {args.output}", flush=True)


if __name__ == "__main__":
    main()
