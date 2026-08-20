#!/usr/bin/env python3
"""Show a real record for each reason the re-run cannot score 100%.

`predict_eval_ceiling.py` counts these; this prints the actual prompts so
the counts mean something. One worked example per reason, chosen as the
clearest rather than the first.
"""
from __future__ import annotations

import glob
import json
import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAYOUT_DESTINATIONS = {"image", "layout", "sky"}


def load_prompts() -> dict[str, str]:
    prompts: dict[str, str] = {}
    for path in glob.glob(str(ROOT / "evaluation/data/batches/*.json")):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        items = data.get("items") if isinstance(data, dict) else data
        for it in items or []:
            if isinstance(it, dict) and it.get("item_id"):
                for key in ("prompt", "text", "input", "raw"):
                    if it.get(key):
                        prompts[it["item_id"]] = it[key]
                        break
    return prompts


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


def wrap(text: str, indent: str = "    ") -> str:
    return textwrap.fill(" ".join(str(text).split()), 96,
                         initial_indent=indent, subsequent_indent=indent)


def show(rec: dict, prompts: dict[str, str], note: str) -> None:
    iid = rec["item_id"]
    print(f"  Record {iid}")
    if iid in prompts:
        text = " ".join(str(prompts[iid]).replace("\\n", " ").split())
        if len(text) > 460:
            text = text[:460] + " […]"
        print("\n  The prompt:")
        print(wrap(text, "    "))
    print(f"\n  {note}\n")
    for o in rec["gaps"].get("unmatched_options") or []:
        dest = (o.get("destination") or "unclear").lower()
        own = "OURS " if dest in LAYOUT_DESTINATIONS else "other"
        qty = f"  [quantity: {o['quantity']}]" if o.get("quantity") else ""
        print(f"    {own} {dest:<11} {str(o.get('canonical'))[:34]:<34} "
              f"{str(o.get('text'))[:60]}{qty}")
    print()


def main() -> int:
    prompts = load_prompts()
    recs = load_records()
    print(f"loaded {len(recs)} scored records, {len(prompts)} prompt texts\n")

    def dests(rec):
        return {(o.get("destination") or "unclear").lower()
                for o in rec["gaps"].get("unmatched_options") or []}

    print("=" * 100)
    print("ISSUE 1 — every gap belonged to another stream (78 records, 12.2%)")
    print("=" * 100)
    print("Nothing intake could ask would clear these. The prompt asked for")
    print("things layout does not build, and the score counted them anyway.\n")
    cands = [r for r in recs
             if dests(r) and not (dests(r) & LAYOUT_DESTINATIONS)
             and r["item_id"] in prompts]
    # Prefer a short prompt with several gaps: readable and still typical.
    cands = [r for r in cands if len(prompts[r["item_id"]]) < 900]
    cands.sort(key=lambda r: -len(r["gaps"].get("unmatched_options") or []))
    if cands:
        show(cands[0], prompts, "Every unmatched request, and who owns it:")

    print("=" * 100)
    print("ISSUE 2 — the request is ours but has no field (65 records, 10%)")
    print("=" * 100)
    print("A good question gets a good answer, and the handoff still has")
    print("nowhere to write it down.\n")
    holes = {
        "multi-map": re.compile(
            r"(multi[- ]?map|several maps|separate maps|map rotation"
            r"|each (world|island|level) is a)", re.I),
        "player count": re.compile(
            r"(player count|lobby size|\d+ ?v ?\d+|team size)", re.I),
    }
    for label, pat in holes.items():
        best = None
        for r in sorted(recs, key=lambda r: len(prompts.get(r["item_id"], "x"*9999))):
            if r["item_id"] not in prompts:
                continue
            for o in r["gaps"].get("unmatched_options") or []:
                if (o.get("destination") or "").lower() not in LAYOUT_DESTINATIONS:
                    continue
                if pat.search(f"{o.get('canonical')} {o.get('text')}"):
                    best = r
                    break
            if best:
                break
        if best:
            print(f"  --- no field for: {label} ---\n")
            show(best, prompts, "Every unmatched request, and who owns it:")

    print("=" * 100)
    print("ISSUE 3 — suggest_id is a name a worker invented, not a lookup")
    print("=" * 100)
    print("So we cannot count from the records how many of these we since")
    print("fixed. Only a re-run resolves it.\n")
    build = (ROOT / "docs" / "LayoutGen - Build.md").read_text(encoding="utf-8")
    real = set(re.findall(r"^\| `([a-z][a-z0-9-]+)`", build, re.M))
    invented: dict[str, str] = {}
    for r in recs:
        for o in r["gaps"].get("unmatched_options") or []:
            sid = o.get("suggest_id")
            if sid and sid not in real and sid not in invented:
                invented[sid] = f"{r['item_id']}: {str(o.get('text'))[:70]}"
    print(f"  {len(invented)} distinct suggest_id values name no row in "
          f"Build.md. A sample:\n")
    for sid, where in list(invented.items())[:14]:
        print(f"    {sid:<28} {where}")
    print("\n  Some of these are things we have since built under another "
          "name;\n  some are things we still do not have. The string cannot "
          "tell you which.\n")

    # Hand-resolved against the catalogue, to show what the string misses.
    resolved = {
        "water-feature": "water-body", "npc-crowd": "npc-population",
        "performance-stage": "venue-stage",
        "audience-stand": "spectator-bleachers",
        "district-urban": "settlement-density",
        "vehicle-as-map": "vehicle-deck", "target-dummy": "range-directed",
        "bridge-span": "obstacle-moving", "hazard-rising": "hazard-kill",
        "spawner-reward": "spawner-npc", "map-variants": None,
        "countdown-display": None, "wardrobe-station": None,
        "zone-difficulty": None,
    }
    print("  The same sample, resolved by hand against today's catalogue:\n")
    print(f"    {'worker wrote':<22} {'we call it':<24} verdict")
    print(f"    {'-' * 62}")
    covered = 0
    for wrote, now in resolved.items():
        if now and now in real:
            covered += 1
            print(f"    {wrote:<22} {now:<24} covered now")
        else:
            print(f"    {wrote:<22} {'—':<24} still missing")
    print(f"\n  {covered} of {len(resolved)} were already fixed, under names "
          f"no string match would find.\n  That is why this script prints no "
          f"predicted score.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
