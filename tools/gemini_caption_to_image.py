"""Regenerate frozen GPT targets from Gemini's own blind captions.

This intentionally leaks target information through text: it is a caption-distillation
experiment, not a fair prompt benchmark. The source image is never attached to generation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import statistics
from concurrent.futures import ThreadPoolExecutor

from layoutgen import assets, paths
from layoutgen.backends import images
from layoutgen.optimize.similarity import (
    CompositeImageSimilarity,
    PyramidEncoder,
)


DEFAULT_RECORDS = (
    paths.RUN
    / "gemini_caption_gap"
    / "pilot__2026-08-18T19_00_00"
    / "records.jsonl"
)
DEFAULT_BASELINE_ARM = "agent_gpt52_upstream_cf94b18_gemini31_260816"


def _read_records(path: pathlib.Path) -> list[dict]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def _caption_prompt(record: dict, mode: str) -> str:
    caption = record["blind_caption"]
    if mode == "summary":
        return str(caption["summary"]).strip()
    if mode == "structured":
        return json.dumps(caption, ensure_ascii=False, separators=(",", ":"))
    raise ValueError(f"unknown caption mode: {mode}")


def _write_image(answer: images.Answer, destination: pathlib.Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f".part{destination.suffix}")
    try:
        images.normalise(answer.image).save(temporary, format="PNG")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def _write_json(path: pathlib.Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".part")
    try:
        temporary.write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _mean(rows: list[dict], key: str) -> float | None:
    values = [
        float(row[key]["score"])
        for row in rows
        if isinstance(row.get(key), dict) and "score" in row[key]
    ]
    return statistics.mean(values) if values else None


def _default_output() -> pathlib.Path:
    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H_%M_%S")
    return paths.RUN / "gemini_caption_to_image" / f"summary__{stamp}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=pathlib.Path, default=DEFAULT_RECORDS)
    parser.add_argument("--caption-mode", choices=("summary", "structured"), default="summary")
    parser.add_argument("--model", default=images.GATEWAY_MODEL)
    parser.add_argument("--baseline-arm", default=DEFAULT_BASELINE_ARM)
    parser.add_argument("--output", type=pathlib.Path, default=_default_output())
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="reuse completed image and row files in an existing output",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="resolve captions and comparison images without generating",
    )
    args = parser.parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be positive")
    if args.output.exists() and not args.resume:
        raise FileExistsError(f"output already exists: {args.output}")

    records = _read_records(args.records)
    if not records:
        raise ValueError("--records contains no rows")
    resolved: list[dict] = []
    for record in records:
        scene = str(record["scene"])
        stage = str(record["stage"])
        target = pathlib.Path(record["image"])
        if not target.is_file():
            raise FileNotFoundError(f"target image is missing: {target}")
        baseline = assets.fetch(f"scenes/{args.baseline_arm}/{stage}/{scene}.png")
        resolved.append(
            {
                "scene": scene,
                "stage": stage,
                "render_order": record["render_order"],
                "caption": _caption_prompt(record, args.caption_mode),
                "target": str(target),
                "baseline": str(baseline) if baseline else None,
            }
        )

    args.output.mkdir(parents=True, exist_ok=args.resume)
    _write_json(
        args.output / "manifest.json",
        {
            "model": args.model,
            "caption_mode": args.caption_mode,
            "source_records": str(args.records),
            "baseline_arm": args.baseline_arm,
            "target_leakage": (
                "captions were produced by inspecting GPT targets; similarity is "
                "diagnostic and not a fair prompt benchmark"
            ),
            "source_image_attached_to_generation": False,
            "cases": resolved,
        },
    )
    if args.dry_run:
        print(f"preflight ok: {len(resolved)} captions\n{args.output}")
        return

    def process(case: dict) -> dict:
        label = f"{case['scene']}/{case['stage']}"
        row_path = args.output / "rows" / f"{case['scene']}_{case['stage']}.json"
        destination = args.output / "images" / f"{case['scene']}_{case['stage']}.png"
        if args.resume and row_path.is_file() and destination.is_file():
            print(f"{label}: reuse completed render", flush=True)
            return json.loads(row_path.read_text(encoding="utf-8"))
        provider = images.LLMGatewayProvider(model=args.model)
        scorer = CompositeImageSimilarity(PyramidEncoder())
        print(f"{label}: generating from blind caption", flush=True)
        answer = provider.generate(case["caption"])
        _write_image(answer, destination)
        target = pathlib.Path(case["target"])
        caption_metrics = scorer.compare(destination, target).as_dict()
        baseline_metrics = (
            scorer.compare(pathlib.Path(case["baseline"]), target).as_dict()
            if case["baseline"]
            else None
        )
        row = {
            **case,
            "generated": str(destination),
            "caption_similarity": caption_metrics,
            "baseline_similarity": baseline_metrics,
            "score_delta": (
                caption_metrics["score"] - baseline_metrics["score"]
                if baseline_metrics
                else None
            ),
        }
        row_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(row_path, row)
        print(
            f"{label}: caption={caption_metrics['score']:.4f}"
            + (
                f" baseline={baseline_metrics['score']:.4f}"
                if baseline_metrics
                else ""
            ),
            flush=True,
        )
        return row

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        scored = list(pool.map(process, resolved))

    with (args.output / "scores.jsonl").open("w", encoding="utf-8") as destination:
        for row in scored:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    deltas = [
        float(row["score_delta"])
        for row in scored
        if row["score_delta"] is not None
    ]
    _write_json(
        args.output / "summary.json",
        {
            "cases": len(scored),
            "mean_caption_similarity": _mean(scored, "caption_similarity"),
            "mean_baseline_similarity": _mean(scored, "baseline_similarity"),
            "mean_score_delta": statistics.mean(deltas) if deltas else None,
            "target_leakage_warning": (
                "the prompt is a target-derived caption; use held-out human quality "
                "judgments before adopting caption prompting"
            ),
        },
    )
    print(f"wrote {args.output}", flush=True)


if __name__ == "__main__":
    main()
