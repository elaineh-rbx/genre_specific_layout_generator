"""Score a comparison across the golden set, one stage at a time.

A comparison names its arms; this fetches each arm's image for a scene, builds the
checklist from whichever arms asked for something, and hands the set to the blinded
judge. Adding a comparison is an entry in `layoutgen.arms`, not a new file here.

Both stages are scored because they disagree often enough to matter: a feature can
survive the isometric and be lost when it is converted to a top-down, and reporting
one number would have to pick a stage silently.

Usage:
    python -m layoutgen.evaluate.score all_arms
    python -m layoutgen.evaluate.score rules_vs_raw --stage iso --workers 8
    python -m layoutgen.evaluate.score all_arms --only 0053,0054
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from layoutgen import arms as A
from layoutgen import paths
from layoutgen.evaluate import judge as J

THUMB_PX = 420


def thumb(src: pathlib.Path, dest: pathlib.Path) -> bool:
    """A judge-sized copy, made once and reused.

    The judge is shown thumbnails rather than full renders: a set of 1024px images
    costs several times as many image tokens, and the features being marked - a
    circuit, a row of lanes, a central hub - survive the downscale intact.
    """
    from PIL import Image

    if not src.is_file():
        return False
    if dest.is_file() and dest.stat().st_mtime >= src.stat().st_mtime:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert("RGB")
        im.thumbnail((THUMB_PX, THUMB_PX), Image.LANCZOS)
        im.save(dest, format="JPEG", quality=82)
    return True


def score_scene(cmp: A.Comparison, scene: str, rows: dict[str, dict],
                stage: str) -> dict | None:
    reqs = cmp.requirements(rows)
    if not reqs:
        return None
    thumbs = {}
    for arm in cmp.arms:
        dest = paths.thumb(arm, stage, scene)
        if not thumb(paths.scene(arm, stage, scene), dest):
            return None
        thumbs[arm] = dest

    marked = J.judge(reqs, thumbs, int(scene))
    if marked is None:
        print(f"  {scene}: judging failed", flush=True)
        return None
    items, shown = marked

    # Whatever the arms recorded about how they got here, so a page can show the
    # routing beside the verdict without opening the run files again.
    meta = {}
    for arm in cmp.runs:
        row = rows.get(arm.id, {})
        for k in ("genre", "preset", "order"):
            meta.setdefault(k, row.get(k, ""))
    return {"scene": scene, "comparison": cmp.id, "stage": stage, **meta,
            "shown": shown, "items": items, "total": len(items),
            "met": {a: sum(bool(x["present"].get(a)) for x in items)
                    for a in cmp.arms}}


def report(cmp: A.Comparison, results: list[dict], stage: str) -> None:
    tot = sum(r["total"] for r in results)
    if not tot:
        print("  nothing scored")
        return
    print(f"\n{len(results)} scenes, {tot} requirement checks ({stage})")
    for arm in cmp:
        met = sum(r["met"].get(arm.id, 0) for r in results)
        print(f"  {arm.title:34s} {met:4d}/{tot}  {100 * met / tot:5.1f}%")

    if len(cmp.asking) > 1:
        print("\nsplit by which arm asked for the requirement:")
        for asker in cmp.asking:
            its = [it for r in results for it in r["items"]
                   if it["source"] == asker.id]
            if not its:
                continue
            line = "  ".join(
                f"{a.short} {100 * sum(bool(x['present'].get(a.id)) for x in its) / len(its):5.1f}%"
                for a in cmp)
            print(f"  {asker.title:26s} n={len(its):3d}   {line}")

    win = Counter()
    for r in results:
        best = max(cmp.arms, key=lambda a: r["met"].get(a, 0))
        top = [a for a in cmp.arms if r["met"].get(a, 0) == r["met"][best]]
        win["tie" if len(top) > 1 else best] += 1
    print("\nper scene, best arm:", dict(win))


def run(cmp: A.Comparison, stage: str, scenes: list[str],
        runs: dict[str, dict[str, dict]], workers: int) -> list[dict]:
    jobs = [(s, A.rows_for(s, runs)) for s in scenes]
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, res in enumerate(pool.map(
                lambda j: score_scene(cmp, j[0], j[1], stage), jobs), 1):
            if res:
                results.append(res)
            if i % 15 == 0:
                print(f"  {i}/{len(jobs)}", flush=True)
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("comparison", nargs="?", default="", choices=[""] + list(A.COMPARISONS),
                    help="which comparison to score; omit for all of them")
    ap.add_argument("--stage", choices=paths.STAGES + ("both",), default="both")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--only", default="", help="rescore just these scenes, e.g. "
                    "0053,0054 - the rest keep the scores already on disk")
    args = ap.parse_args()

    runs = A.load_runs()
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    chosen = [A.COMPARISONS[args.comparison]] if args.comparison else list(
        A.COMPARISONS.values())
    stages = paths.STAGES if args.stage == "both" else (args.stage,)
    paths.SCORES.mkdir(parents=True, exist_ok=True)

    for cmp in chosen:
        scenes = sorted(set.intersection(*(set(runs[a.id]) for a in cmp.runs)))
        scenes = [s for s in scenes if not only or s in only]
        for stage in stages:
            print(f"\n{cmp.id}: judging {len(scenes)} {stage} sets "
                  f"({len(cmp.arms)} arms)", flush=True)
            results = run(cmp, stage, scenes, runs, args.workers)
            out = cmp.scores(stage)
            if only and out.is_file():
                # Merge, so rescoring a few regenerated scenes keeps the scores for
                # the scenes this run never looked at.
                kept = {r["scene"]: r for x in out.open() if x.strip()
                        for r in [json.loads(x)]}
                kept.update({r["scene"]: r for r in results})
                results = list(kept.values())
            results.sort(key=lambda r: r["scene"])
            out.write_text("".join(json.dumps(r) + "\n" for r in results),
                           encoding="utf-8")
            report(cmp, results, stage)
            print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
