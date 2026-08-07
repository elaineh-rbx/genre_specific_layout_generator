"""Generate all 75 golden scenes under the Build.md Part II layout model.

Each scene uses the router's picks from `python -m layoutgen.model.router --golden`: a
genre, one shape, and whatever options that prompt gave a reason to want. The addendum
is built by the same code the interactive server previews - literally the same call, so
what lands here cannot drift from what the UI showed.

Order follows the route the picks force. A scene whose shape or options carry `P6`
has a topology that must be valid by construction, and a free image cannot guarantee
that - so the plan is drawn first and the isometric is dressed from it. Everything
else runs isometric-first and converts to a top-down afterwards.

The other two arms are not regenerated: `results/scenes/raw` and `results/scenes/needs`
already hold them, and reusing them keeps the comparison honest and saves 300 calls.

Usage:
    python -m layoutgen.pipeline.golden            # all 75
    python -m layoutgen.pipeline.golden --limit 4
    python -m layoutgen.pipeline.golden --only 0025,0053
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from layoutgen import paths
from layoutgen.backends import images
from layoutgen.model import rules as br
from layoutgen.pipeline import carve as cv
from layoutgen.pipeline import spec as sp

GOLDEN = paths.PROMPTS
CLASSIFIED = paths.ROUTING / "rules.jsonl"
ISO = paths.SCENES / "rules" / "iso"
TD = paths.SCENES / "rules" / "td"
PLAN = paths.SCENES / "rules" / "plan"
RUN = paths.RUNS / "rules.jsonl"

_lock = threading.Lock()
_done = 0


@dataclass
class Row:
    scene: str
    title: str
    prompt: str
    genre: str
    preset: str
    shape: str
    shape_label: str
    options: list[str]
    held: list[str]
    extras: list[dict]
    confidence: str
    evidence: str
    route: list[str]
    order: str
    addendum: str
    iso_prompt: str
    td_prompt: str
    iso: str = ""
    td: str = ""
    plan: str = ""
    layout_steps: int = 0
    status: str = "ok"
    error: str = ""
    seconds: float = 0.0
    _spec: dict = field(default_factory=dict, repr=False)


def rows() -> list[Row]:
    manifest = {m["scene"]: m for m in
                (json.loads(x) for x in GOLDEN.open() if x.strip())}
    out: list[Row] = []
    for r in (json.loads(x) for x in CLASSIFIED.open() if x.strip()):
        m = manifest.get(r["scene"])
        g = br.GENRES.get(r["genre"])
        if m is None or g is None:
            continue
        # A P6 route means the topology is the game, so the plan comes first. Where a
        # generator exists - mazes and racing circuits - the layout is authored
        # outright rather than asked for, which is the whole point of the route.
        kind = cv.layout_kind(g.name, r["shape"], r["options"])
        order = "layout" if kind else ("p6" if "P6" in r.get("route", []) else "std")
        spec = {"mode": order, "source": m["source_prompt"], "genre": r["genre"],
                "shape": r["shape"], "options": r["options"], "edits": {},
                "kind": kind or "maze", **cv.track_params(g.name, r["shape"]),
                "custom": [e["text"] for e in r.get("extras", [])
                           if e["goes_to"] == "image"],
                "stageB": True}
        built = sp.build(spec)
        shape = g.shape(r["shape"])
        out.append(Row(
            scene=r["scene"], title=m.get("title", ""), prompt=m["source_prompt"],
            genre=r["genre"], preset=r["preset"], shape=r["shape"],
            shape_label=shape.label if shape else "", options=r["options"],
            held=built["withheld"], extras=r.get("extras", []),
            confidence=r["confidence"], evidence=r["evidence"],
            route=r.get("route", []), order=order, addendum=built["addendum"],
            iso_prompt=built["iso"] or "",
            td_prompt=(built["plan"] if order == "p6" else built["topdown"]) or "",
            _spec=spec))
    out.sort(key=lambda x: x.scene)
    return out


def run_one(row: Row, total: int, redo: bool) -> Row:
    global _done
    t0 = time.monotonic()
    iso, td = ISO / f"{row.scene}.png", TD / f"{row.scene}.png"
    try:
        if row.order == "layout":
            # Seeded on the scene, so a rerun reproduces the same layout exactly.
            lay = cv.carve({**row._spec, "cells": 13 if row._spec.get("kind") ==
                            "track" else 12, "seed": int(row.scene)})
            plan = PLAN / f"{row.scene}.png"
            plan.write_bytes((paths.OUT / lay["layout"]).read_bytes())
            row.plan = plan.name
            row.layout_steps = lay["steps"]
            if redo or not td.is_file():
                images.generate(row.td_prompt, td, [plan])
            if redo or not iso.is_file():
                images.generate(row.iso_prompt, iso, [td])
        elif row.order == "p6":
            # plan first, then dress the isometric from it
            if redo or not td.is_file():
                images.generate(row.td_prompt, td)
            if redo or not iso.is_file():
                images.generate(row.iso_prompt, iso, [td])
        else:
            if redo or not iso.is_file():
                images.generate(row.iso_prompt, iso)
            if redo or not td.is_file():
                images.generate(row.td_prompt, td, [iso])
        row.iso, row.td = iso.name, td.name
    except Exception as exc:
        row.status, row.error = "error", f"{type(exc).__name__}: {exc}"
    row.seconds = round(time.monotonic() - t0, 1)
    with _lock:
        _done += 1
        flag = "" if row.status == "ok" else "  FAILED"
        print(f"  [{_done}/{total}] {row.scene}  {row.genre} :: {row.preset}"
              f"  ({row.order}, {row.seconds}s){flag}", flush=True)
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="comma-separated scene ids")
    ap.add_argument("--redo", action="store_true", help="regenerate existing images")
    args = ap.parse_args()

    for d in (ISO, TD, PLAN, paths.RUNS):
        d.mkdir(parents=True, exist_ok=True)

    todo = rows()
    if args.only:
        keep = {s.strip() for s in args.only.split(",")}
        todo = [r for r in todo if r.scene in keep]
    if args.limit:
        todo = todo[: args.limit]

    from collections import Counter
    by_order = Counter(r.order for r in todo)
    print(f"generating {len(todo)} scenes  "
          f"({by_order['std']} isometric-first, {by_order['p6']} plan-first, "
          f"{by_order['layout']} authored-layout-first), "
          f"{args.workers} workers", flush=True)
    t0 = time.monotonic()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        done = list(pool.map(lambda r: run_one(r, len(todo), args.redo), todo))

    done.sort(key=lambda r: r.scene)
    # Merge rather than replace: a --only or --limit run must not drop the scenes it
    # was never asked to touch, whose images are still on disk.
    kept = {}
    if RUN.is_file():
        kept = {d["scene"]: d for line in RUN.open() if line.strip()
                for d in [json.loads(line)]}
    for r in done:
        kept[r.scene] = {k: v for k, v in r.__dict__.items()
                         if not k.startswith("_")}
    with RUN.open("w") as fh:
        for scene in sorted(kept):
            fh.write(json.dumps(kept[scene]) + "\n")

    ok = [r for r in done if r.status == "ok"]
    bad = [r for r in done if r.status != "ok"]
    print(f"\n{len(ok)}/{len(done)} ok in {(time.monotonic()-t0)/60:.1f} min")
    print(f"wrote {RUN}")
    for r in bad:
        print(f"  FAILED {r.scene}: {r.error}")

    print("\norder:", dict(Counter(r.order for r in done)))
    print("genres:", dict(Counter(r.genre for r in done).most_common(6)))
    inj = [r for r in done if r.addendum]
    print(f"scenes with an injection: {len(inj)}/{len(done)}  "
          f"(mean {sum(len(r.addendum) for r in inj)//max(len(inj),1)} chars)")


if __name__ == "__main__":
    main()
