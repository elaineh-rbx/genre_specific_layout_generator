"""Which genres, shapes and presets did 620 real prompts actually reach?

Also: how many prompts would have used each new Universal Option, which bounds
the risk of the skill over-applying them.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent.parent
REPO = EVAL_ROOT.parent
RECORDS = EVAL_ROOT / "data" / "records"
BUILD_MD = REPO / "docs" / "LayoutGen - Build.md"

GENRE_HEADING = re.compile(r"^## \*\*(\d+)\\\. (.+?)\*\*\s*$")
LAYOUT_DESTS = {"image", "layout"}

# Same patterns used to place the universal options.
CONCEPTS = {
    "npc-population": re.compile(
        r"\b(npc|pedestrian|crowd|villager|townsfolk|citizen|bystander|ally|allies|"
        r"vendor|shopkeeper|merchant|trader|guard|passerby|onlooker|spectator crowd|"
        r"ambient animal|wildlife|critter|companion|follower|mount|pet npc|"
        r"quest giver|questgiver|boss npc|named character|civilian)\b", re.I),
    "building-interior": re.compile(
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
    "island-cluster": re.compile(
        r"\b(island|islands|archipelago|atoll|isle|floating island|sky island)\b", re.I),
}


def slugify(title):
    return re.sub(r"[^a-z0-9]+", "-", title.split("(")[0].lower()).strip("-")


def build_inventory():
    """Every genre slug, and every preset name declared in Build.md."""
    text = BUILD_MD.read_text(encoding="utf-8")
    lines = text.splitlines()
    genres, presets = [], defaultdict(list)
    current = None
    in_presets = False
    for line in lines:
        m = GENRE_HEADING.match(line)
        if m:
            current = slugify(m.group(2))
            genres.append(current)
            in_presets = False
            continue
        if current and line.lstrip().startswith("**Presets"):
            in_presets = True
            continue
        if current and line.lstrip().startswith("**Genre notes"):
            in_presets = False
            continue
        if in_presets and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            name = re.sub(r"\*\*", "", cells[0]).strip()
            if name and name.lower() not in ("preset", ":----") and "----" not in name:
                presets[current].append(name)
    return genres, presets


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
    genres_declared, presets_declared = build_inventory()
    all_presets = {p for ps in presets_declared.values() for p in ps}

    genre_use, shape_use, preset_use = Counter(), Counter(), Counter()
    concept_prompts = defaultdict(set)
    any_concept = set()
    total = 0

    for rec in load():
        item = rec.get("item_id") or ""
        if item.endswith("b"):
            continue
        total += 1
        gc = ((rec.get("handoff") or {}).get("genre_choice")) or {}
        for g in (gc.get("genres") or []):
            genre_use[g] += 1
        shape = gc.get("shape") or {}
        sid = shape.get("id") if isinstance(shape, dict) else shape
        if sid:
            shape_use[sid] += 1
        if gc.get("preset"):
            preset_use[gc["preset"].strip()] += 1
        for ask in ((rec.get("gaps") or {}).get("unmatched_options") or []):
            if not isinstance(ask, dict):
                continue
            if (ask.get("destination") or "").lower() not in LAYOUT_DESTS:
                continue
            blob = f"{ask.get('canonical', '')} {ask.get('text', '')}"
            for name, pat in CONCEPTS.items():
                if pat.search(blob):
                    concept_prompts[name].add(item)
                    any_concept.add(item)

    print(f"prompts: {total}\n")

    print("=== genre usage ===")
    for g in genres_declared:
        n = genre_use.get(g, 0)
        flag = "  <-- NEVER USED" if n == 0 else ""
        print(f"  {n:>4}  {g}{flag}")
    extra = set(genre_use) - set(genres_declared)
    if extra:
        print(f"  (assigned but not a declared slug: {sorted(extra)})")

    print("\n=== presets never chosen ===")
    unused = sorted(p for p in all_presets if preset_use.get(p, 0) == 0)
    print(f"  {len(unused)} of {len(all_presets)} declared presets never chosen")
    for p in unused:
        owner = next(g for g, ps in presets_declared.items() if p in ps)
        print(f"    {p}  ({owner})")

    print("\n=== top presets ===")
    for p, n in preset_use.most_common(12):
        mark = "" if p in all_presets else "   <-- not a declared preset name"
        print(f"  {n:>3}  {p}{mark}")

    print("\n=== how often a Universal Option would have been picked ===")
    for name in CONCEPTS:
        n = len(concept_prompts[name])
        print(f"  {n:>4} prompts ({n/total:.0%})  {name}")
    print(f"  {len(any_concept):>4} prompts ({len(any_concept)/total:.0%})  at least one")


if __name__ == "__main__":
    main()
