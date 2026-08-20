#!/usr/bin/env python3
"""Check emitted records for the two failures run 2 could not see coming.

Run 2 passed classification on 95% of prompts and still failed 22% of them, all
downstream of the stage anyone was measuring. Two defects accounted for 78 of
the 141, and both are mechanical enough that a script catches them:

1. A `layout_placement` entry with no `type`. Type is what tells the pipeline
   which volume to build, so the entry arrives looking like work and is inert.
   94 entries across 68 prompts, and in half of them the type was printed on the
   option row the lane had already read.
2. A request recorded as unmatched that then appears nowhere in the handoff.
   10 prompts lost one outright -- a holding cell, a set of role spawn points.

Neither is visible in a record that parses, which is why run 2 shipped with both.

    python evaluation/tools/check_records_wellformed.py [--glob 'batch-*.jsonl']
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RECORDS = Path(__file__).resolve().parents[1] / "data/run-2/records"
BUILD = Path(__file__).resolve().parents[2] / "docs/LayoutGen - Build.md"
SPATIAL = {"image", "layout"}


def composite_shapes() -> set[str]:
    """Shapes that are a container by definition rather than one space.

    `space-staged` is "Zone (Lobby and Isolated Stage)" and `world-chaptered`
    is chapters as genuinely separate maps -- naming one of these at the top
    level and then listing its maps as segments is the shape working, not a
    disagreement. Read from the catalogue rather than listed here, because a
    hand-kept copy is a second source of truth that goes stale.
    """
    if not BUILD.exists():
        return set()
    rows = re.findall(r"^\| `([a-z0-9-]+)` \| \*\*.+?\*\* \| .+? \| `([^|]+)` \|$",
                      BUILD.read_text(encoding="utf-8"), re.M)
    return {sid for sid, route in rows if "P4" in route}


COMPOSITE = composite_shapes()


def words(text: object) -> set[str]:
    """Content words, for asking whether a request survived into the handoff.

    Deliberately loose: the lane rewords as it emits, so an exact match would
    report losses that did not happen. One shared word over three characters is
    enough to call it carried.
    """
    return {w for w in re.findall(r"[a-z]+", str(text).lower()) if len(w) > 3}


def handoff_body(gc: dict) -> set[str]:
    """Everywhere a request can legitimately end up.

    `mechanics` counts. A state change, a weather cycle or a player scale is
    not the layout's to carry, and sending it to the mechanics pile is the
    triage working -- but run 3 measured survival against the image and layout
    lists alone, so correct triage was indistinguishable from loss. 153
    out-of-scope requests were logged as unmatched and 95% of them sat in a
    record whose mechanics pile was populated, with nothing tying the two
    together.
    """
    parts = [str(e.get("text", "")) for e in (gc.get("image_prompt") or [])]
    parts += [str(e.get("text", "")) for e in (gc.get("layout_placement") or [])]
    parts += [str(n) for n in (gc.get("notes") or [])]
    parts += [str(m) for m in (gc.get("mechanics") or [])]
    return words(" ".join(parts))


def check(record: dict) -> list[str]:
    item = record.get("item_id", "?")
    gc = (record.get("handoff") or {}).get("genre_choice") or {}
    out = []

    for entry in gc.get("layout_placement") or []:
        if entry.get("type"):
            continue
        oid = entry.get("id")
        where = f"id {oid!r}" if oid else "free text"
        out.append(f"{item}: layout_placement entry with no type ({where}) -- "
                   f"{str(entry.get('text'))[:60]!r}")

    body = handoff_body(gc)
    for gap in ((record.get("gaps") or {}).get("unmatched_options") or []):
        if str(gap.get("destination") or "").lower() not in SPATIAL:
            continue
        target = words(gap.get("canonical")) | words(gap.get("text"))
        if target and not (target & body):
            out.append(f"{item}: unmatched request reaches nothing in the "
                       f"handoff -- {str(gap.get('canonical'))!r}")

    out += check_segments(item, (record.get("handoff") or {}), gc)
    return out


def check_segments(item: str, handoff: dict, gc: dict) -> list[str]:
    """The three ways a multi-space build can be internally inconsistent.

    `segments` is new, so unlike the checks above these are not measured
    failures -- they are the readings the regression batch showed lanes
    splitting on before the rule spelled both out.
    """
    segments = gc.get("segments") or []
    if not segments:
        return []

    out = []
    pipeline = gc.get("pipeline") or handoff.get("pipeline") or []
    maps = [s for s in segments if s.get("kind") == "map"]
    if maps and "P4" not in pipeline:
        out.append(f"{item}: segments disagree with route -- {len(maps)} `map` "
                   f"segments but pipeline {pipeline} has no P4")
    if not maps and "P4" in pipeline:
        out.append(f"{item}: segments disagree with route -- P4 but every "
                   f"segment is a zone")

    # Either the top-level shape leads the list, or it is a container the
    # segments sit inside. Both are ordinary; what is wrong is a top-level
    # shape that is neither one of the segments nor able to hold them.
    top = (gc.get("shape") or {}).get("id")
    first = (segments[0].get("shape") or {}).get("id")
    if top and first and top != first and top not in COMPOSITE:
        if any(s.get("kind") != "zone" for s in segments):
            out.append(f"{item}: segments disagree with shape -- top level is "
                       f"{top!r}, which is a single space, but the list leads "
                       f"with {first!r} and holds separate maps")

    for seg in segments:
        if not seg.get("name"):
            out.append(f"{item}: segment with no name -- a space nobody can "
                       f"refer to is not a space")
    return out


def count_contradicted(record: dict) -> int:
    """Preset options the prompt contradicts that still reached the lists.

    Reported but deliberately outside `check()`. Run 3's brief told lanes to
    keep these, so 129 of them are an instrument artifact rather than the
    skill failing, and folding them into the usable-handoff count would move
    the run 2 / run 3 comparison under its own definition. The brief now says
    to leave them out, so this should read 0 from run 4 on.
    """
    gc = (record.get("handoff") or {}).get("genre_choice") or {}
    shipped = {e.get("id") for e in (gc.get("image_prompt") or [])
               + (gc.get("layout_placement") or [])}
    rejected = (record.get("coverage") or {}).get("preset_rejected") or []
    return sum(1 for r in rejected if r.get("id") in shipped)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="batch-*.jsonl")
    ap.add_argument("--records", type=Path, default=RECORDS)
    ap.add_argument("--quiet", action="store_true",
                    help="counts only, no per-record lines")
    args = ap.parse_args()

    paths = sorted(args.records.glob(args.glob))
    if not paths:
        print(f"no record files matching {args.glob} in {args.records}")
        return 1

    untyped: list[str] = []
    lost: list[str] = []
    segments: list[str] = []
    contradicted = 0
    total = 0
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            total += 1
            contradicted += count_contradicted(record)
            for problem in check(record):
                if "no type" in problem:
                    untyped.append(problem)
                elif "segment" in problem:
                    segments.append(problem)
                else:
                    lost.append(problem)

    every = untyped + lost + segments
    if not args.quiet:
        for problem in every:
            print(f"  {problem}")
        if every:
            print()

    if not total:
        print("no records")
        return 1
    prompts = len({p.split(":")[0] for p in every})
    print(f"{total} records")
    print(f"  layout_placement entries with no type : {len(untyped)}")
    print(f"  requests that reach nothing           : {len(lost)}")
    print(f"  inconsistent `segments`               : {len(segments)}")
    print(f"  prompts affected                      : {prompts} "
          f"({prompts / total:.1%})")
    print(f"  contradicted options still shipped    : {contradicted} "
          f"(reported only, see count_contradicted)")
    return 1 if every else 0


if __name__ == "__main__":
    sys.exit(main())
