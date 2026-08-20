#!/usr/bin/env python3
"""Re-measure the golden set's shape complaints against the Phase 6 catalogue.

Every record whose `skill_gap` or `genre_gap` prose says "shape" is pulled out
and sorted into what Phase 6 did or did not do for it. The word is a wide net
on purpose -- a large share of the catch turns out to be some other missing
field that merely mentions shapes in passing, and separating those out is half
the measurement.

**Verdicts come from reading all 206 gap texts, not from matching their
titles.** An earlier version of this file bucketed on keywords in the
complaint's short name; spot-reading 20 rows found 9 of them misfiled, which is
D13's lesson arriving on schedule. `shape-gap-verdicts.json` holds one verdict
per row, keyed `item_id|name`, and `_shape_gap_verdicts.py` records how it was
built. New records will show up here as `unread` rather than being guessed at.

The test applied to each row, for the four buckets that count as answered:

  reach     the shape already existed under another genre and the mixing rule
            forbade taking it. Step 1 made every shape reachable from every
            genre, so the row now has a shape to point at.
  new       nothing could say it; one of step 2's five new shapes now can.
  preset    the shape was right but welded to a preset the prompt contradicts.
  catchall  no catalogue row fits, but the space is describable in a sentence
            and the five axes route it correctly. Step 4.

And for the three that do not:

  two-shapes  the prompt wants more than one shape at once. Refused on purpose.
  multimap    needs several maps in one handoff. There is no such field.
  field       needs something that is not a shape at all -- a goal, a count, a
              player number, a movement model, a temporal state.
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECORDS = ROOT.parent / "evaluation" / "data" / "records"
VERDICTS = ROOT / "shape-gap-verdicts.json"

ANSWERED = {
    "reach": "fixed: step 1, shape existed one genre over",
    "new": "fixed: step 2, new shape",
    "preset": "fixed: step 3, shape prised off its preset",
    "catchall": "fixed: step 4, described shape",
    "route": "fixed: the route-is-a-default rule",
}
UNANSWERED = {
    "two-shapes": "by design: one shape per build",
    "multimap": "open: needs a multi-map handoff",
    "field": "open: needs a field that is not a shape",
    "open": "open: no answer yet",
    "unread": "not yet read",
}
ORDER = list(ANSWERED) + list(UNANSWERED)


def load() -> list[dict]:
    """Every gap whose prose mentions a shape, in a stable order."""
    rows = []
    for path in sorted(glob.glob(str(RECORDS / "*.jsonl"))):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                rec = json.loads(line)
                for field in ("skill_gap", "genre_gap"):
                    gap = rec.get("gaps", {}).get(field)
                    if isinstance(gap, dict) and re.search(
                        r"\bshapes?\b", f"{gap.get('name','')} {gap.get('why','')}", re.I
                    ):
                        rows.append({"id": rec["item_id"], "field": field,
                                     "name": gap.get("name", ""),
                                     "why": gap.get("why", "")})
    return rows


def main() -> int:
    rows = load()
    verdicts = json.loads(VERDICTS.read_text(encoding="utf-8"))
    for row in rows:
        row["verdict"] = verdicts.get(f"{row['id']}|{row['name']}", "unread")

    counts = {v: [r for r in rows if r["verdict"] == v] for v in ORDER}
    answered = sum(len(counts[v]) for v in ANSWERED)
    shape_side = answered + len(counts["two-shapes"]) + len(counts["open"])

    print(f"{len(rows)} shape complaints across {len({r['id'] for r in rows})} prompts")
    print(f"all read in full; verdicts in {VERDICTS.name}\n")
    width = max(len(v) for v in ORDER)
    for verdict in ORDER:
        hits = counts[verdict]
        if hits:
            label = ANSWERED.get(verdict) or UNANSWERED[verdict]
            print(f"  {verdict:<{width}}  {len(hits):>3}  {label}")

    print(f"\n  a shape problem:            {shape_side}")
    print(f"    of which answered:        {answered}")
    print(f"    refused by design:        {len(counts['two-shapes'])}")
    print(f"    still unanswered:         {len(counts['open'])}")
    print(f"  not a shape problem:        {len(counts['multimap']) + len(counts['field'])}")
    print(f"    needs a multi-map handoff:{len(counts['multimap']):>3}")
    print(f"    needs some other field:   {len(counts['field']):>3}")
    if counts["unread"]:
        print(f"\n  {len(counts['unread'])} rows have no verdict -- rerun _shape_gap_verdicts.py")

    if "--list" in sys.argv:
        for verdict in ORDER:
            if not counts[verdict]:
                continue
            print(f"\n--- {verdict} ---")
            for r in counts[verdict]:
                print(f"  {r['id']:<7} {r['name']}")
    return 1 if counts["unread"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
