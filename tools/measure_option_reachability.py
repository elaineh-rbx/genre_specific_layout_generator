#!/usr/bin/env python3
"""How big is the option-reachability gap that D12 fixed only for shapes?

Phase 6 gave shapes one shared catalogue every genre can reach, on the
reasoning that "a prompt needing one large interior found Animal Sim assumes
wilderness while the shape it needed sat one genre over". Options never got
the same treatment: they share IDs across genres, which is a dedupe key for
mixing, but a genre can only offer what its own table lists.

This measures what that costs, three ways:

  1. How concentrated options are -- how many are private to one genre.
  2. Which options a genre plausibly wants and cannot reach, judged by the
     option already appearing in several other genres.
  3. The recorded evidence: gaps in the golden set whose request names an
     option that exists in the system but not in the genre that was chosen.

The third is the one that matters, because it is measured rather than
argued.
"""
from __future__ import annotations

import glob
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_genre_skills as g  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "docs" / "LayoutGen - Build.md"
LAYOUT_DESTINATIONS = {"image", "layout", "sky"}


def main() -> int:
    text = BUILD.read_text(encoding="utf-8")
    genres, no_genre, catalog = g.parse_all(text)

    universal = {
        o["id"] for o in
        g.parse_universal_options(g.section_body(text, g.UNIVERSAL_HEADING))
    }

    by_genre: dict[str, set[str]] = {}
    slug_of: dict[str, str] = {}
    for section in genres:
        title = section.get("title") or section.get("name")
        slug = g.slugify(title) if hasattr(g, "slugify") else title
        by_genre[title] = {o["id"] for o in section.get("options", [])}
        slug_of[slug] = title

    owners: dict[str, set[str]] = defaultdict(set)
    for title, ids in by_genre.items():
        for oid in ids:
            owners[oid].add(title)

    all_options = set(owners)
    print(f"{len(all_options)} distinct options across {len(by_genre)} genres, "
          f"plus {len(universal)} universal\n")

    print("1. How private are options?")
    spread = Counter(len(v) for v in owners.values())
    for n in sorted(spread):
        bar = "#" * spread[n]
        label = "genre" if n == 1 else "genres"
        print(f"   in {n:2d} {label:<6} {spread[n]:4d}  {bar[:56]}")
    private = spread[1]
    print(f"\n   {private} of {len(all_options)} options "
          f"({private / len(all_options):.0%}) exist in exactly one genre.")
    print(f"   A genre's table averages "
          f"{sum(len(v) for v in by_genre.values()) / len(by_genre):.0f} "
          f"options; the union is {len(all_options)}.")
    print(f"   So a genre reaches about "
          f"{sum(len(v) for v in by_genre.values()) / len(by_genre) / len(all_options):.0%} "
          f"of what the system can express.\n")

    print("2. Options in 3+ genres that some genre still cannot reach")
    print("   (a concept that common is rarely genuinely absent from a genre)\n")
    common = {oid for oid, v in owners.items() if len(v) >= 3}
    rows = []
    for oid in sorted(common):
        missing = sorted(set(by_genre) - owners[oid])
        rows.append((len(owners[oid]), oid, missing))
    rows.sort(reverse=True)
    for n, oid, missing in rows[:12]:
        print(f"   {oid:<22} in {n:2d}, missing from {len(missing):2d}: "
              f"{', '.join(missing[:5])}"
              f"{' …' if len(missing) > 5 else ''}")

    print("\n3. Recorded evidence: golden-set gaps naming an option the")
    print("   system HAS but the chosen genre could not reach\n")
    recs = []
    for p in glob.glob(str(ROOT / "evaluation/data/records/*.jsonl")):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line:
                r = json.loads(line)
                if "gaps" in r and "handoff" in r:
                    recs.append(r)

    unreachable_hits: Counter[tuple[str, str]] = Counter()
    examples: dict[tuple[str, str], str] = {}
    affected = 0
    for r in recs:
        gc = (r["handoff"] or {}).get("genre_choice") or {}
        chosen = [slug_of.get(s, s) for s in (gc.get("genres") or [])]
        if not chosen:
            continue
        reachable = set(universal)
        for t in chosen:
            reachable |= by_genre.get(t, set())
        hit = False
        for o in r["gaps"].get("unmatched_options") or []:
            if (o.get("destination") or "").lower() not in LAYOUT_DESTINATIONS:
                continue
            sid = o.get("suggest_id")
            if sid and sid in all_options and sid not in reachable:
                key = (chosen[0], sid)
                unreachable_hits[key] += 1
                examples.setdefault(key, str(o.get("text"))[:62])
                hit = True
        if hit:
            affected += 1

    print(f"   {affected} records ({affected / len(recs):.1%}) asked for an "
          f"option that exists\n   in the catalogue but not in their genre.\n")
    print(f"   {'genre':<22} {'option it could not reach':<24} n   example")
    print(f"   {'-' * 92}")
    for (genre, oid), n in unreachable_hits.most_common(16):
        print(f"   {genre[:21]:<22} {oid:<24} {n:<3} {examples[(genre, oid)]}")

    print("\n   Note: this undercounts badly. It only catches gaps where the")
    print("   worker happened to write a suggest_id that matches a real row,")
    print("   and most invented a name instead.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
