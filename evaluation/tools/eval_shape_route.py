"""How often did a shape choice carry a pipeline route the prompt did not ask for?

`LayoutGen - Pipeline.md` keys the route on shape by design: "It is now keyed on
shape and gives the answer." The consequence is that a shape's spatial character
and its pipeline route are one decision. A prompt wanting graded danger zones on
a single map must pick `world-biomes`, which means P4 (separate maps).

This counts how many rows landed on a route-bearing shape, which bounds how
often that coupling could bite.
"""
import glob
import json
import os
from collections import Counter
from pathlib import Path

RECORD_GLOB = "batch-*.jsonl"
RECORD_DIR = Path(__file__).resolve().parent.parent / "data" / "records"

# From the shape->route table in `docs/LayoutGen - Pipeline.md`.
ROUTE_BEARING = {
    "arena-stacked": "P2",
    "world-chaptered": "P4",
    "space-staged": "P4",
    "puzzle-maze": "P6",
    "world-open-biomes": "P4",
    "world-hub-dungeon": "P4+P3",
    "settlement-claimable": "P3",
    "settlement-buildable": "P3",
    "world-underground": "P2+P3",
    "lane-actor-track": "P6",
    "warren-looping": "P6",
    "world-biomes": "P4",
    "route-multitier": "P2",
    "hub-portals": "P4",
}
# Genres whose route applies whatever shape is chosen.
GENRE_WIDE_P6 = {"obby-platformer", "racing", "infinite-runner", "runner"}


def load(records_dir=RECORD_DIR):
    rows = []
    for path in sorted(glob.glob(os.path.join(records_dir, RECORD_GLOB))):
        for line in open(path, encoding="utf-8-sig"):
            line = line.strip().lstrip("\ufeff")
            if not line or line.startswith("```"):
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def main():
    rows = [r for r in load() if not str(r.get("item_id", "")).endswith("b")]
    shapes = Counter()
    route_bearing = 0
    genre_wide = 0
    both = 0
    for rec in rows:
        gc = ((rec.get("handoff") or {}).get("genre_choice")) or {}
        shape = gc.get("shape") or {}
        sid = shape.get("id") if isinstance(shape, dict) else shape
        genres = [g.lower() for g in (gc.get("genres") or [])]
        shapes[sid] += 1
        rb = sid in ROUTE_BEARING
        gw = bool(set(genres) & GENRE_WIDE_P6)
        route_bearing += rb
        genre_wide += gw
        both += rb and gw

    n = len(rows)
    print(f"rows: {n}")
    print()
    print(f"chose a route-bearing shape          : {route_bearing}  ({route_bearing/n:.0%})")
    print(f"in a genre with a genre-wide P6 route: {genre_wide}  ({genre_wide/n:.0%})")
    print(f"both                                 : {both}")
    union = route_bearing + genre_wide - both
    print(f"route fixed by classification, not asked for separately: {union}  ({union/n:.0%})")
    print()
    print("route-bearing shapes actually used:")
    for sid, route in sorted(ROUTE_BEARING.items(), key=lambda kv: -shapes[kv[0]]):
        if shapes[sid]:
            print(f"   {shapes[sid]:>3}  {sid:<24} -> {route}")


if __name__ == "__main__":
    main()
