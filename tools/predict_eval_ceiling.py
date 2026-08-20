#!/usr/bin/env python3
"""What a re-run of the golden set cannot fix, and why.

Phase 7 changes wording, questions and the shape catalogue. It changes no
schema. So before re-running it is worth separating the recorded gaps this
round can plausibly close from the ones that have nowhere to land however
well intake is worded -- the second group is the ceiling.

Deliberately not a score. Two things make a numeric prediction impossible
from these records alone:

  * `suggest_id` is a name the scoring worker invented, not a lookup. Workers
    wrote `stage-performance` for what is now `venue-stage` and `zone-biome`
    for `world-biomes`, so matching those strings against Build.md
    undercounts badly and matching them loosely overcounts. Only a re-run
    resolves it.
  * A gap was recorded whenever the handoff could not carry something the
    prompt asked for -- including things LayoutGen was never meant to carry.

So this prints an accounting of where the gaps sit, which is the part that
does not depend on guessing.
"""
from __future__ import annotations

import glob
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# What the layout handoff is actually responsible for. Everything else is a
# real user request that belongs to another stream and another team.
LAYOUT_DESTINATIONS = {"image", "layout", "sky"}

# Subjects with no field in the handoff. Wording cannot fix these; only a
# schema change can, and this round makes none.
#
# A per-pick quantity used to be listed here and no longer is: `count` was
# added to the handoff, so "20 floors" and "3 lanes" now have somewhere to
# land. Counted separately below as work the first run's gaps already
# credit us for.
NO_FIELD = {
    "multi-map": r"(multi[- ]?map|several maps|separate maps|map rotation"
                 r"|lobby (and|\+|plus)|each (world|island|level) is a)",
    "player count": r"(player count|how many players|lobby size"
                    r"|\d+ ?v ?\d+|team size)",
}


def load_records() -> list[dict]:
    out = []
    for path in glob.glob(str(ROOT / "evaluation/data/records/*.jsonl")):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                rec = json.loads(line)
                if "gaps" in rec:
                    out.append(rec)
    return out


def main() -> int:
    recs = load_records()
    n = len(recs)

    dest_opts: Counter[str] = Counter()
    recs_with_layout_gap = 0
    recs_with_only_other_stream = 0
    no_field_hits: Counter[str] = Counter()
    recs_no_field = 0
    recs_with_quantity = 0

    for rec in recs:
        gaps = rec["gaps"]
        opts = gaps.get("unmatched_options") or []
        dests = {(o.get("destination") or "unclear").lower() for o in opts}
        for d in dests:
            dest_opts[d] += 1
        if dests & LAYOUT_DESTINATIONS:
            recs_with_layout_gap += 1
        elif dests:
            recs_with_only_other_stream += 1

        # Only a gap that was layout's to carry can be a hole in layout's
        # schema. A player count wanted by the mechanics stream is not our
        # missing field, and scoping this was worth 4 points of apparent
        # ceiling.
        layout_opts = [o for o in opts
                       if (o.get("destination") or "").lower()
                       in LAYOUT_DESTINATIONS]
        blob = " ".join(str(o.get(k) or "") for o in layout_opts
                        for k in ("canonical", "text")).lower()
        blob += " " + " ".join(str(gaps.get(k) or "")
                               for k in ("skill_gap", "genre_gap")).lower()
        hit = {label for label, pat in NO_FIELD.items()
               if re.search(pat, blob)}
        for label in hit:
            no_field_hits[label] += 1
        if hit:
            recs_no_field += 1

        if any(o.get("quantity") for o in layout_opts):
            recs_with_quantity += 1

    def pct(x: int) -> str:
        return f"{x:4d}  {x / n:5.1%}"

    print(f"scored records: {n}\n")

    print("Records by where their unmatched requests were headed")
    print("(a record can want several things, so these overlap):")
    for dest, count in dest_opts.most_common():
        own = "layout" if dest in LAYOUT_DESTINATIONS else "another stream"
        print(f"  {pct(count)}   {dest:<12} {own}")

    print(f"\n  {pct(recs_with_layout_gap)}   had at least one gap that is "
          f"layout's to fix")
    print(f"  {pct(recs_with_only_other_stream)}   had gaps, but none of them "
          f"layout's  <- cannot reach 100% by improving layout")

    print(f"\nRecords naming something the schema has no field for "
          f"({recs_no_field}, {recs_no_field / n:.0%}):")
    for label, count in no_field_hits.most_common():
        print(f"  {pct(count)}   {label}")
    print("\nThese are the hard ceiling for this round: no schema changes were "
          "made,\nso a perfectly worded question still has nowhere to put the "
          "answer.")

    print(f"\nFor contrast, {pct(recs_with_quantity).strip()} of records had a "
          f"layout-bound request carrying a\nstated quantity — \"20 floors\", "
          f"\"3 lanes\". Those had nowhere to land at the first\nrun and have "
          f"`count` now, so they are the part of the hole this round closed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
