"""Independent check of the two counts the systems merge was asked to produce.

Reads the raw ask records rather than the merge report, so a mistake in the
merge cannot propagate into the final report.
"""
import argparse
import glob
import json
import os
import re
from collections import Counter
from pathlib import Path

RECORD_GLOB = "batch-*.jsonl"
RECORD_DIR = Path(__file__).resolve().parent.parent / "data" / "records"

NEGATIVE_EXPLICIT = re.compile(
    r"^(no|non|zero|never)\b|\bnot\b|^without\b|^anti[- ]", re.I
)
PROHIBITION_SHAPED = re.compile(
    r"\b(ban|banned|forbid|forbidden|prohibit|exclude|exclusion|omit|avoid|"
    r"prevent|restrict|restriction|limit|cap|only|disallow|disable|skip|"
    r"minimal|without)\b",
    re.I,
)

IDENTITY = re.compile(
    r"\b(player is|play as|player character|avatar|as an? (cat|dog|animal|ant|"
    r"bug|robot|mech|alien|blob|ball|car|vehicle|ufo|creature|monster|fish|"
    r"bird|dragon|slime|tank|plane))\b|\bplayer (species|form|body|model|size|"
    r"scale|shape)\b|\bnon[- ]humanoid\b|\btiny player\b|\bgiant player\b",
    re.I,
)
PLAYER_VEHICLE = re.compile(
    r"\bplayer (is|as) a? ?(car|vehicle|kart|tank|plane|boat|ship|train|mech)\b|"
    r"\b(drive|driving|piloting) as\b|\bvehicle[- ]?(player|body|avatar)\b|"
    r"\bplayer vehicle\b|\bcontrolled vehicle\b",
    re.I,
)
MOVEMENT = re.compile(
    r"\b(dash|dashing|grapple|grappling|hook|glide|gliding|fly|flying|flight|"
    r"jetpack|swim|swimming|wall[- ]?run|wall[- ]?jump|double jump|climb|"
    r"climbing|slide|sliding|teleport|dive|hover|walkspeed|walk speed|"
    r"movement speed|jump (power|height|boost)|gravity|sprint|roll|parkour|"
    r"vault|zipline|rope swing|swing)\b",
    re.I,
)

COSMETIC = re.compile(
    r"\b(customiz|customis|editor|skin|catalog|selection|shop|cosmetic|outfit|"
    r"wardrobe|dress|accessor|hat|emote)\w*", re.I
)

SYSTEMS_DESTS = {"mechanics", "constraint"}


def load(records_dir):
    rows = []
    for path in sorted(glob.glob(os.path.join(records_dir, RECORD_GLOB))):
        with open(path, encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip().lstrip("\ufeff")
                if not line or line.startswith("```"):
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def asks(rows, dests=None):
    out = []
    for rec in rows:
        if str(rec.get("item_id", "")).endswith("b"):
            continue
        gaps = rec.get("gaps") or {}
        for ask in gaps.get("unmatched_options") or []:
            if not isinstance(ask, dict):
                continue
            dest = (ask.get("destination") or "").strip().lower()
            if dests and dest not in dests:
                continue
            label = (ask.get("canonical") or "").strip()
            text = (ask.get("text") or "").strip()
            if label or text:
                out.append((label, text, dest, rec.get("item_id")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default=str(RECORD_DIR))
    args = ap.parse_args()

    rows = load(args.records)
    all_asks = asks(rows)
    sys_asks = asks(rows, SYSTEMS_DESTS)
    print(f"records: {len(rows)}  all asks: {len(all_asks)}  systems asks: {len(sys_asks)}")

    explicit = [a for a in sys_asks if NEGATIVE_EXPLICIT.search(a[0])]
    shaped = [a for a in sys_asks if PROHIBITION_SHAPED.search(a[0])]
    union_rows = {(a[0], a[3]) for a in explicit} | {(a[0], a[3]) for a in shaped}
    print()
    print("--- prohibitions (mechanics + constraint destinations, canonical label) ---")
    print(f"explicitly negative label : {len(explicit)} asks, {len({a[0] for a in explicit})} labels")
    print(f"prohibition-shaped        : {len(shaped)} asks, {len({a[0] for a in shaped})} labels")
    print(f"union                     : {len(union_rows)} asks")
    for label, n in Counter(a[0] for a in explicit + shaped).most_common(20):
        print(f"   {n:>3}  {label}")

    print()
    print("--- non-default player identity / movement (all destinations, canonical label) ---")
    ident = [a for a in all_asks if IDENTITY.search(a[0])]
    veh = [a for a in all_asks if PLAYER_VEHICLE.search(a[0])]
    mov = [a for a in all_asks if MOVEMENT.search(a[0])]
    union2 = {(a[0], a[3]) for a in ident + veh + mov}
    print(f"identity : {len(ident)}")
    print(f"vehicle  : {len(veh)}")
    print(f"movement : {len(mov)}")
    print(f"union (deduped by label+prompt): {len(union2)}")
    for label, n in Counter(a[0] for a in ident + veh + mov).most_common(25):
        print(f"   {n:>3}  {label}")

    # An avatar dress-up shop does not change player physics; only a changed
    # body or changed movement can invalidate jump-gap geometry.
    print()
    print("--- of those, which actually change the physics inputs ---")
    physics = [
        a
        for a in ident + veh + mov
        if not COSMETIC.search(a[0])
    ]
    cosmetic = [a for a in ident + veh + mov if COSMETIC.search(a[0])]
    print(f"physics-affecting : {len({(a[0], a[3]) for a in physics})} asks")
    print(f"cosmetic only     : {len({(a[0], a[3]) for a in cosmetic})} asks")
    for label, n in Counter(a[0] for a in physics).most_common(30):
        print(f"   {n:>3}  {label}")


if __name__ == "__main__":
    main()
