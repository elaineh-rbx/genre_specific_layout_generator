"""How often did a shape's welded pipeline route actually contradict the prompt?

`eval_shape_route.py` counts how many rows landed on a route-bearing shape, which
bounds how often the coupling *could* bite. This asks the narrower question: of
those rows, how many show the prompt asking for the opposite of the route it got?

Each row on a route-bearing shape is sorted into three buckets:

  confirmed    the prompt says something that supports the route
  silent       the prompt says nothing either way, so the route was assumed
  contradicted the prompt says the opposite of the route

Only `contradicted` is a defect. `silent` is the cost of a default and is
usually right. P6 shapes are excluded: their route is a structural requirement
(a maze must be solvable, a tower-defense lane must be one continuous route),
not a judgement the prompt can overrule.

    python evaluation/tools/eval_route_conflict.py           # counts
    python evaluation/tools/eval_route_conflict.py --show    # + the prompts
"""
import csv
import json
import re
import sys
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CSV_PATH = DATA / "golden set 600 - genre and coverage eval.csv"
RECORDS = DATA / "records"

# shape -> the claim its route makes about the build
ROUTE_CLAIM = {
    "world-biomes": "P4",
    "world-open-biomes": "P4",
    "world-chaptered": "P4",
    "space-staged": "P4",
    "world-hub-dungeon": "P4",
    "hub-portals": "P4",
    "settlement-claimable": "P3",
    "settlement-buildable": "P3",
    "world-underground": "P2",
    "arena-stacked": "P2",
    "route-multitier": "P2",
    # P6 shapes deliberately omitted - see module docstring.
}

# "This really is several maps that cannot share one surface."
P4_SUPPORT = re.compile(
    r"\b(levels?|stages?|chapters?|floors? to unlock|multiple maps|different maps"
    r"|separate maps|each level|level select|lobby|rounds?|teleports? to|portals?"
    r"|different worlds|other worlds|minigames?|dungeons?|instances?)\b", re.I)
P4_CONTRA = re.compile(
    r"\b(one (big |large |single |huge |giant )?map|single map|one world|one big world"
    r"|seamless|open[- ]world|one continuous|all in one (map|place|world)"
    r"|no loading|one large (area|world|map)|single (continuous|seamless))\b", re.I)

# "Play really does move between outside and inside."
P3_SUPPORT = re.compile(
    r"\b(interiors?|inside|indoors?|enter (the |a |their )?(house|building|shop|store)"
    r"|furnish|decorate|rooms?|walk in|go in)\b", re.I)
P3_CONTRA = re.compile(
    r"\b(exterior only|no interiors?|outside only|facades?|from the (street|outside))\b", re.I)

# "Surfaces really do overhang each other."
P2_SUPPORT = re.compile(
    r"\b(floors?|multi[- ]?level|stacked|storey|stories|tower|bridges?|tunnels?"
    r"|underground|basement|upstairs|balcon|overhang|caves?)\b", re.I)
P2_CONTRA = re.compile(r"\b(flat|single (level|floor|surface)|one floor|ground level only)\b", re.I)

PATTERNS = {
    "P4": (P4_SUPPORT, P4_CONTRA),
    "P3": (P3_SUPPORT, P3_CONTRA),
    "P2": (P2_SUPPORT, P2_CONTRA),
}


def csv_rows():
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            row["item_id"] = f"P{i:04d}"
            yield row


def load_records():
    out = {}
    for path in sorted(RECORDS.glob("batch-*.jsonl")):
        for line in open(path, encoding="utf-8-sig"):
            line = line.strip().lstrip("\ufeff")
            if not line or line.startswith("```"):
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            iid = rec.get("item_id")
            if iid and not str(iid).endswith("b"):
                out[iid] = rec
    return out


def prompt_of(row):
    return " ".join(filter(None, [row.get("initial_prompt"),
                                  row.get("initial_scene_subprompt_enriched")]))


def main():
    show = "--show" in sys.argv
    recs = load_records()
    prompts = {r["item_id"]: prompt_of(r) for r in csv_rows()}

    buckets = defaultdict(Counter)
    hits = defaultdict(list)
    per_shape = defaultdict(Counter)

    for iid, rec in recs.items():
        gc = ((rec.get("handoff") or {}).get("genre_choice")) or {}
        shape = gc.get("shape") or {}
        sid = shape.get("id") if isinstance(shape, dict) else shape
        claim = ROUTE_CLAIM.get(sid)
        if not claim:
            continue
        text = prompts.get(iid, "")
        support, contra = PATTERNS[claim]
        if contra.search(text) and not support.search(text):
            verdict = "contradicted"
        elif support.search(text):
            verdict = "confirmed"
        else:
            verdict = "silent"
        buckets[claim][verdict] += 1
        per_shape[sid][verdict] += 1
        if verdict == "contradicted":
            hits[claim].append((iid, sid, text))

    total = sum(sum(c.values()) for c in buckets.values())
    print(f"rows on a route-bearing, overridable shape: {total}")
    print("(P6 shapes excluded - their route is structural, not a judgement)\n")
    print(f"{'route':<8}{'confirmed':>11}{'silent':>9}{'contradicted':>14}")
    for claim in ("P4", "P3", "P2"):
        c = buckets[claim]
        print(f"{claim:<8}{c['confirmed']:>11}{c['silent']:>9}{c['contradicted']:>14}")
    tot = Counter()
    for c in buckets.values():
        tot.update(c)
    print(f"{'all':<8}{tot['confirmed']:>11}{tot['silent']:>9}{tot['contradicted']:>14}")

    print("\nby shape:")
    for sid in sorted(per_shape, key=lambda s: -sum(per_shape[s].values())):
        c = per_shape[sid]
        print(f"  {sid:<24} {ROUTE_CLAIM[sid]:<4} "
              f"confirmed {c['confirmed']:>3}  silent {c['silent']:>3}  "
              f"contradicted {c['contradicted']:>3}")

    # Wider check: a route can also arrive from an option, so ask the question
    # straight - of every row whose prompt says "one map", how many got P4?
    one_map = split = 0
    split_ids = []
    for iid, rec in recs.items():
        text = prompts.get(iid, "")
        if not (P4_CONTRA.search(text) and not P4_SUPPORT.search(text)):
            continue
        one_map += 1
        gc = ((rec.get("handoff") or {}).get("genre_choice")) or {}
        if "P4" in (gc.get("pipeline") or []):
            split += 1
            shape = gc.get("shape") or {}
            split_ids.append((iid, shape.get("id") if isinstance(shape, dict) else shape))
    print(f"\nprompts that say one continuous map (any shape): {one_map}")
    print(f"  ...that still got P4 in the emitted pipeline : {split}")
    for iid, sid in sorted(split_ids):
        print(f"     {iid}  {sid}")

    if show:
        for claim in ("P4", "P3", "P2"):
            if not hits[claim]:
                continue
            print(f"\n{'=' * 78}\n{claim} contradicted ({len(hits[claim])})\n{'=' * 78}")
            for iid, sid, text in sorted(hits[claim]):
                print(f"\n{iid}  {sid}")
                print(textwrap.fill(" ".join(text.split())[:600], width=96,
                                    initial_indent="   ", subsequent_indent="   "))


if __name__ == "__main__":
    main()
