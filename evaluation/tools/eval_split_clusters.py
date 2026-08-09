"""Split the mechanical ask clusters into per-destination files for review.

Destination is the right seam. An ask's destination is where the work would
actually happen, so two asks with different destinations are rarely the same
concept, and splitting there costs almost no true merges while making each
reviewer's job small enough to finish.

    python tools/eval_split_clusters.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "ask-clusters-slim.json"

# Grouped by who would consume the ask, not by volume.
GROUPS = {
    "layout": ["image", "layout"],
    "systems": ["mechanics", "constraint"],
    "context": ["progression", "ui", "audio", "sky", "metadata", "unclear"],
}


def main() -> int:
    clusters = json.loads(SRC.read_text(encoding="utf-8"))
    buckets: dict[str, list] = {k: [] for k in GROUPS}
    unplaced = []
    for c in clusters:
        dests = c.get("destinations") or {}
        if not dests:
            unplaced.append(c)
            continue
        # Assign on the destination the ask was most often filed under; a
        # cluster split evenly across two groups goes to both, since either
        # reviewer might be the one who recognises it.
        top = max(dests, key=lambda d: dests[d])
        placed = False
        for name, members in GROUPS.items():
            if top in members:
                buckets[name].append(c)
                placed = True
        if not placed:
            unplaced.append(c)

    for name, items in buckets.items():
        items.sort(key=lambda c: -c["total"])
        p = ROOT / "data" / f"ask-clusters-{name}.json"
        p.write_text(json.dumps(items, ensure_ascii=False, indent=0), encoding="utf-8")
        total = sum(c["total"] for c in items)
        print(f"{p.name}: {len(items)} clusters, {total} asks, {p.stat().st_size} bytes")
    if unplaced:
        print(f"{len(unplaced)} clusters had no destination and were dropped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
