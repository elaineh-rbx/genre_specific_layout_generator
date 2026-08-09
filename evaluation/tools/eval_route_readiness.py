"""How many rows landed on an unproven pipeline route without the prompt asking?

P0 and P6 are built and working. P2, P3, P4 and CHECK are not yet production
ready. So a route modifier the prompt never asked for is not a neutral default
-- it is a build that cannot currently be delivered.

For every emitted route modifier this asks whether the prompt contains language
requiring it:

  required   the prompt says something only that modifier can build
  assumed    the prompt is silent; the modifier came from a shape or preset

`assumed` is the population a "prefer P0/P6 on silence" rule would move.

    python evaluation/tools/eval_route_readiness.py
    python evaluation/tools/eval_route_readiness.py --show P4
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

PROVEN = {"P0", "P6"}

# Language that genuinely requires each modifier. Deliberately generous: a
# false "required" understates the finding, which is the safe direction.
REQUIRES = {
    "P4": re.compile(
        r"\b(levels?|stages?|chapters?|multiple maps|different maps|separate maps"
        r"|each level|level select|lobby|rounds?|teleports? to|portals?"
        r"|different worlds|other worlds|minigames?|dungeons?|instances?|biomes?"
        r"|regions?|zones?|islands?|planets?|worlds to)\b", re.I),
    "P3": re.compile(
        r"\b(interiors?|inside|indoors?|enter (the |a |their )?(house|building|shop|store|room)"
        r"|furnish|decorate|rooms?|walk in|go in|houses? you can)\b", re.I),
    "P2": re.compile(
        r"\b(floors?|multi[- ]?level|stacked|storey|stories|towers?|bridges?|tunnels?"
        r"|underground|basement|upstairs|balcon|overhang|caves?|elevators?|stairs)\b", re.I),
    "CHECK": re.compile(
        r"\b(fly|flying|flight|swim|swimming|underwater|space|zero[- ]?g|jetpack"
        r"|glider?|hover|dive|diving|aerial|airborne)\b", re.I),
}
TRACKED = ("P4", "P3", "P2", "CHECK")


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
    show = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--show" else None
    recs = load_records()
    prompts = {r["item_id"]: prompt_of(r) for r in csv_rows()}

    verdicts = defaultdict(Counter)
    assumed_rows = defaultdict(list)
    unproven_rows = set()
    all_proven = 0

    for iid, rec in recs.items():
        gc = ((rec.get("handoff") or {}).get("genre_choice")) or {}
        route = [str(p).strip() for p in (gc.get("pipeline") or [])]
        text = prompts.get(iid, "")
        unproven = [m for m in TRACKED if any(m in r for r in route)]
        if not unproven:
            all_proven += 1
            continue
        unproven_rows.add(iid)
        for mod in unproven:
            if REQUIRES[mod].search(text):
                verdicts[mod]["required"] += 1
            else:
                verdicts[mod]["assumed"] += 1
                shape = gc.get("shape") or {}
                assumed_rows[mod].append(
                    (iid, shape.get("id") if isinstance(shape, dict) else shape, route, text))

    n = len(recs)
    print(f"rows: {n}")
    print(f"  routed entirely on proven pipeline (P0 / P6): {all_proven}  ({all_proven/n:.0%})")
    print(f"  carrying at least one unproven modifier      : {len(unproven_rows)}  "
          f"({len(unproven_rows)/n:.0%})")
    print()
    print(f"{'modifier':<10}{'required':>10}{'assumed':>10}")
    tot = Counter()
    for mod in TRACKED:
        c = verdicts[mod]
        tot.update(c)
        print(f"{mod:<10}{c['required']:>10}{c['assumed']:>10}")
    print(f"{'all':<10}{tot['required']:>10}{tot['assumed']:>10}")

    movable = {iid for mod in TRACKED for iid, *_ in assumed_rows[mod]}
    fully = {iid for iid in movable
             if all(not verdicts_has_required(recs, prompts, iid, mod) for mod in TRACKED)}
    print(f"\nrows with at least one assumed modifier: {len(movable)}  ({len(movable)/n:.0%})")
    print(f"rows that would move fully to P0/P6    : {len(fully)}  ({len(fully)/n:.0%})")

    if show:
        rows = assumed_rows.get(show, [])
        print(f"\n{'=' * 78}\n{show} assumed ({len(rows)})\n{'=' * 78}")
        for iid, sid, route, text in sorted(rows)[:40]:
            print(f"\n{iid}  shape={sid}  route={route}")
            print(textwrap.fill(" ".join(text.split())[:400], width=96,
                                initial_indent="   ", subsequent_indent="   "))


def verdicts_has_required(recs, prompts, iid, mod):
    gc = ((recs[iid].get("handoff") or {}).get("genre_choice")) or {}
    route = [str(p).strip() for p in (gc.get("pipeline") or [])]
    if not any(mod in r for r in route):
        return False
    return bool(REQUIRES[mod].search(prompts.get(iid, "")))


if __name__ == "__main__":
    main()
