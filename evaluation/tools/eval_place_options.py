"""Which genres asked for each proposed new option?

The six options recommended by the layout merge have to be placed in specific
genre tables. This groups the asks behind each concept by the genre we actually
assigned, so placement follows the evidence instead of a guess.

Counts are asks, not prompts; a prompt can ask twice. Only layout-pipeline
destinations (`image`, `layout`) are counted, since these are map features.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECORDS = ROOT / "data" / "records"

LAYOUT_DESTS = {"image", "layout"}

CONCEPTS = {
    "npc-population": re.compile(
        r"\b(npc|pedestrian|crowd|villager|townsfolk|citizen|bystander|ally|allies|"
        r"vendor|shopkeeper|merchant|trader|guard|passerby|onlooker|spectator crowd|"
        r"ambient animal|wildlife|critter|companion|follower|mount|pet npc|"
        r"quest giver|questgiver|boss npc|named character|civilian)\b", re.I),
    "interior-rooms": re.compile(
        r"\b(interior|enterable|walk in|walk-in|go inside|inside the building|"
        r"furnished|room|rooms|bedroom|kitchen|lobby interior|apartment|"
        r"house interior|shop interior|floor plan)\b", re.I),
    "water-body": re.compile(
        r"\b(water|river|lake|ocean|sea|pond|waterfall|swim|swimming|underwater|"
        r"beach|shore|shoreline|stream|creek|lagoon|harbor|harbour|waves|"
        r"boat|dock|pier)\b", re.I),
    "settlement-density": re.compile(
        r"\b(city|cities|town|village|settlement|urban|downtown|street|streets|"
        r"neighborhood|neighbourhood|block|blocks|skyline|skyscraper|suburb|"
        r"metropolis|shopping district|main street)\b", re.I),
    "terrain-relief": re.compile(
        r"\b(mountain|mountains|hill|hills|cliff|cliffs|cave|caves|canyon|valley|"
        r"ravine|chasm|plateau|dune|crater|volcano|slope|terrain|rocky|"
        r"underground tunnel)\b", re.I),
    "island": re.compile(
        r"\b(island|islands|archipelago|atoll|isle|floating island|sky island)\b", re.I),
}


def load():
    for path in sorted(RECORDS.glob("batch-*.jsonl")):
        for line in open(path, encoding="utf-8-sig"):
            line = line.strip().lstrip("\ufeff")
            if not line or line.startswith("```"):
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def main():
    by_concept = defaultdict(Counter)
    prompts_by_concept = defaultdict(set)
    samples = defaultdict(list)

    for rec in load():
        item = rec.get("item_id") or ""
        if item.endswith("b"):
            continue
        gc = ((rec.get("handoff") or {}).get("genre_choice")) or {}
        genres = gc.get("genres") or ["(no genre)"]
        primary = genres[0]
        for ask in ((rec.get("gaps") or {}).get("unmatched_options") or []):
            if not isinstance(ask, dict):
                continue
            if (ask.get("destination") or "").lower() not in LAYOUT_DESTS:
                continue
            blob = f"{ask.get('canonical', '')} {ask.get('text', '')}"
            for name, pat in CONCEPTS.items():
                if pat.search(blob):
                    by_concept[name][primary] += 1
                    prompts_by_concept[name].add(item)
                    if len(samples[name]) < 4:
                        samples[name].append(
                            f"{item} [{primary}] {ask.get('canonical')}: "
                            f"{' '.join((ask.get('text') or '').split())[:90]}")

    for name in CONCEPTS:
        counts = by_concept[name]
        total = sum(counts.values())
        print(f"\n=== {name} ===")
        print(f"  {total} asks across {len(prompts_by_concept[name])} prompts, "
              f"{len(counts)} genres")
        for genre, n in counts.most_common():
            bar = "#" * min(n, 40)
            print(f"    {n:>3}  {genre:<22} {bar}")
        print("  samples:")
        for s in samples[name]:
            print(f"    {s}")


if __name__ == "__main__":
    main()
