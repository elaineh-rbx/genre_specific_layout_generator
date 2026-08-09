"""Independently size the big merged concepts with a keyword sweep.

The semantic merges were done by readers, and a reader's total is a judgement
about which labels mean the same thing. This is a crude second opinion on the
same question: how many asks in the layout pipeline mention water at all, or an
interior at all? It will not agree exactly — keywords catch labels a reader
would rightly exclude and miss ones with no shared word — but it is enough to
tell a merge that is roughly right from one that is inflated.

    python tools/eval_verify_concepts.py
    python tools/eval_verify_concepts.py --dest ui progression
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGG = ROOT / "data" / "aggregate.json"

CONCEPTS = {
    "interior / rooms": r"\b(interior|indoor|room|rooms|building|buildings|floor ?plan)\b",
    "water": r"\b(water|river|lake|ocean|sea|waterfall|pond|underwater|swim\w*|beach)\b",
    "settlement": r"\b(city|town|village|settlement|block|street|urban|house|housing|shop)\b",
    "non-flat terrain": r"\b(mountain|hill|cliff|terrain|cave|canyon|chasm|valley)\b",
    "island": r"\b(island|islands|archipelago)\b",
    "vehicle": r"\b(vehicle|car|kart|boat|bike|truck|plane|ship)\b",
    "npc / character": r"\b(npc|character|enemy|enemies|creature|animal|boss|crowd|pedestrian)\b",
    "counts": r"\bcount\b|\bnumber of\b",
    "vegetation": r"\b(tree|trees|forest|grass|plant|flower|jungle|foliage)\b",
    "sky / lighting": r"\b(sky|skybox|light\w*|sun|moon|star|fog|weather|night|day)\b",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", nargs="*", default=["image", "layout"],
                    help="destinations to include")
    args = ap.parse_args()

    agg = json.loads(AGG.read_text(encoding="utf-8"))
    asks = [x for x in agg["unmatched_options"]
            if (x.get("destination") or "") in set(args.dest)]
    print(f"{len(asks)} asks in destinations: {', '.join(args.dest)}\n")

    for name, pattern in CONCEPTS.items():
        rx = re.compile(pattern, re.I)
        hits = [x for x in asks if rx.search(x.get("canonical") or "")]
        names = sorted({(x.get("canonical") or "").lower() for x in hits})
        print(f"{name:20} {len(hits):4} asks under {len(names):3} distinct labels")
        if names:
            print(f"                     e.g. {', '.join(names[:8])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
