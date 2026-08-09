"""Group the canonical ask phrases so the long tail can be read at all.

Sixty-odd lanes each invented their own wording, so `soft currency`, `currency`
and `currency system` arrive as three separate concepts. This does the
mechanical part of putting them back together — morphological normalisation,
then head-noun grouping, then token-overlap merging — and leaves the genuinely
semantic merges (`coin` with `currency`) to a human or a bounded review pass.

    python tools/eval_cluster.py                  # clusters over the threshold
    python tools/eval_cluster.py --min 1 --all    # everything, including singletons
    python tools/eval_cluster.py --field genre_gap_names
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGG = ROOT / "data" / "aggregate.json"

# Words that carry no distinguishing meaning in a 2-4 word noun phrase. Dropping
# them is what makes "currency system" and "currency" land in the same bucket.
#
# "player" and "game" are deliberately NOT here. Stripping them collapses
# "player count" into "count", which then swallows "zone count" as a subset —
# and player count is one of the numbers lanes flagged as actually driving map
# size. A modifier that changes what the phrase refers to is not noise.
NOISE = {
    "a", "an", "the", "of", "for", "with", "and", "in", "on", "to",
    "system", "systems", "feature", "features", "element", "elements",
    "mechanic", "mechanics", "option", "options", "thing", "things",
    "generic", "custom",
}

# Over-merging silently destroys a distinction and cannot be undone downstream;
# under-merging just leaves two clusters for the semantic pass to join. So the
# threshold is set to split on a single differing modifier ("first person" vs
# "third person" share two of four tokens and must stay apart).
MERGE_OVERLAP = 0.6

# Gap names are sentences ("no home for the goal condition"), not the noun
# phrases the ask field asks for. The boilerplate is worse than useless: it
# splits one gap across "...field" and "...home for..." wordings while
# simultaneously inflating overlap enough to fuse "no player count field" with
# "no player vehicle field". Strip it and cluster on the concept that is left.
GAP_NOISE = {
    "no", "not", "none", "nowhere", "missing", "lack", "lacks", "cannot", "cant",
    "home", "channel", "carrier", "field", "way", "place", "slot", "key",
    "expression", "express", "record", "carry", "hold", "any", "exist", "exists",
}

# Hand-curated, and deliberately tiny. These are the few cases where two lanes
# picked different words for one concept often enough that leaving them apart
# would understate a top finding. Anything less clear-cut is left for the
# semantic pass, where a human can see what is being merged.
SYNONYM = {
    "win": "goal", "objective": "goal", "victory": "goal",
    "hud": "screenspace", "ui": "screenspace", "screen": "screenspace",
    "economy": "progression",
}

# Irregulars that the -s/-es/-ies rules below get wrong.
IRREGULAR = {
    "properties": "property", "enemies": "enemy", "abilities": "ability",
    "npcs": "npc", "uis": "ui", "vehicles": "vehicle", "bosses": "boss",
    "classes": "class", "areas": "area", "zones": "zone",
}


def singular(word: str) -> str:
    if word in IRREGULAR:
        return IRREGULAR[word]
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith(("ches", "shes", "sses", "xes")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def tokens(phrase: str, gap_style: bool = False) -> tuple[str, ...]:
    words = re.findall(r"[a-z0-9]+", phrase.lower())
    kept = [SYNONYM.get(singular(w), singular(w)) for w in words]
    drop = NOISE | GAP_NOISE if gap_style else NOISE
    kept = [w for w in kept if w not in drop]
    return tuple(kept) or tuple(singular(w) for w in words)


def head(toks: tuple[str, ...]) -> str:
    """Last surviving token — the noun the phrase is actually about."""
    return toks[-1] if toks else ""


def cluster(counts: dict[str, int], gap_style: bool = False) -> list[dict]:
    """Three passes, cheapest first, each only merging what it is sure of."""
    by_norm: dict[tuple[str, ...], dict[str, int]] = defaultdict(dict)
    for phrase, n in counts.items():
        by_norm[tokens(phrase, gap_style)][phrase] = n

    # Pass 2: same head noun and a shared modifier, or head noun alone.
    by_head: dict[str, list[tuple[tuple[str, ...], dict[str, int]]]] = defaultdict(list)
    for toks, members in by_norm.items():
        by_head[head(toks)].append((toks, members))

    clusters = []
    for h, entries in by_head.items():
        # Pass 3: inside a head-noun group, merge token sets that overlap enough
        # that they are near-certainly the same concept; keep the rest apart.
        buckets: list[tuple[set[str], dict[str, int]]] = []
        for toks, members in sorted(entries, key=lambda e: -sum(e[1].values())):
            tset = set(toks)
            placed = False
            for bset, bmembers in buckets:
                overlap = len(tset & bset) / max(1, len(tset | bset))
                if overlap >= MERGE_OVERLAP or tset <= bset or bset <= tset:
                    bset |= tset
                    for k, v in members.items():
                        bmembers[k] = bmembers.get(k, 0) + v
                    placed = True
                    break
            if not placed:
                buckets.append((set(tset), dict(members)))
        for bset, bmembers in buckets:
            total = sum(bmembers.values())
            label = min(bmembers, key=lambda k: (len(k), k))
            clusters.append({
                "label": label,
                "head": h,
                "total": total,
                "variants": dict(sorted(bmembers.items(), key=lambda kv: -kv[1])),
            })
    clusters.sort(key=lambda c: (-c["total"], c["label"]))
    return clusters


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="asks",
                    help="asks | genre_gap_names | skill_gap_names")
    ap.add_argument("--min", type=int, default=5, help="minimum cluster total to show")
    ap.add_argument("--all", action="store_true", help="show every cluster")
    ap.add_argument("--out", default="", help="also write clusters as JSON here")
    args = ap.parse_args()

    agg = json.loads(AGG.read_text(encoding="utf-8"))
    if args.field == "asks":
        counts = agg["asks"]["all_canonical"]
        # Destination is a property of the ask, not the phrase, so report the
        # spread per cluster rather than assuming one phrase has one home.
        dest_by_phrase: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for u in agg["unmatched_options"]:
            dest_by_phrase[(u.get("canonical") or "?").strip().lower()][
                u.get("destination") or "?"] += 1
    else:
        counts = agg[args.field]
        dest_by_phrase = {}

    clusters = cluster(counts, gap_style=args.field != "asks")
    shown = [c for c in clusters if args.all or c["total"] >= args.min]

    raw_total = sum(counts.values())
    print(f"{raw_total} mentions across {len(counts)} distinct phrases "
          f"-> {len(clusters)} clusters")
    print(f"showing {len(shown)} with total >= {args.min if not args.all else 1}\n")

    for c in shown:
        dests: dict[str, int] = defaultdict(int)
        for phrase in c["variants"]:
            for d, n in dest_by_phrase.get(phrase, {}).items():
                dests[d] += n
        dest_str = ", ".join(f"{d}:{n}" for d, n in
                             sorted(dests.items(), key=lambda kv: -kv[1])) or "-"
        print(f"{c['total']:4}  {c['label']}")
        print(f"      destinations: {dest_str}")
        if len(c["variants"]) > 1:
            variants = ", ".join(f"{k} ({v})" for k, v in c["variants"].items())
            print(f"      merged: {variants}")
        print()

    singles = sum(1 for c in clusters if c["total"] == 1)
    print(f"{singles} clusters are a single one-off mention "
          f"({singles / max(1, len(clusters)):.0%} of clusters)")

    if args.out:
        Path(args.out).write_text(json.dumps(clusters, indent=2, ensure_ascii=False),
                                  encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
