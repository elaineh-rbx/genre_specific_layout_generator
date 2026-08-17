#!/usr/bin/env python3
"""Count claims written in prose must match the tables under them.

Prose says "seven of Shooter's eight presets are lane networks". The table
says nine presets, six of them lane networks. Nobody notices, because adding
a preset does not touch the sentence describing the old ones.

For each genre section this reports every number the prose applies to
"preset(s)" or "shape(s)" next to the real count, so a drifted claim is
visible. It cannot know which noun a given number modifies, so it reports
rather than fails -- except for the totals, which it does check.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import generate_genre_skills as g  # noqa: E402

WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20,
}
NUM = r"(?:\d+|" + "|".join(WORDS) + r")"
NOUN = r"(presets?|shapes?)"
CLAIM = re.compile(rf"\b({NUM})\s+(?:\w+\s+){{0,2}}?{NOUN}\b", re.I)

# Phrasings where the number IS the section's total, so it must match exactly
# rather than merely not exceed it. "seven of Shooter's eight presets",
# "the other eight presets", "all five presets".
TOTALS = [
    re.compile(rf"\bof\s+(?:the\s+|\w+'s\s+)?({NUM})\s+{NOUN}\b", re.I),
    re.compile(rf"\ball\s+(?:of\s+the\s+)?({NUM})\s+{NOUN}\b", re.I),
]

# "the other N presets" is total-minus-a-subset, so it is not a total claim
# and not an over-claim either. Skip the number entirely.
SUBSET = re.compile(rf"\bthe\s+other\s+({NUM})\s+{NOUN}\b", re.I)

# Numbers that are almost always about the rule, not the table.
IGNORE_VALUES = {1}


def value(token: str) -> int:
    token = token.lower()
    return int(token) if token.isdigit() else WORDS[token]


def kindof(noun: str) -> str:
    return "preset" if noun.lower().startswith("preset") else "shape"


def main() -> int:
    build = (ROOT / "docs" / "LayoutGen - Build.md").read_text(encoding="utf-8")
    genres, no_genre, catalog = g.parse_all(build)

    print(f"totals: {len(genres)} genres, {len(catalog)} shapes in the catalogue, "
          f"{len(g.parse_universal_options(g.section_body(build, g.UNIVERSAL_HEADING)))} "
          f"universal options\n")

    lines = build.splitlines()
    # Map each line number to the section it falls in. No Genre has its own
    # presets and its own heading shape, so it needs a bound of its own --
    # without one its prose is charged to whichever genre precedes it.
    bounds = []
    for n, line in enumerate(lines, 1):
        m = g.GENRE_HEADING.match(line)
        if m:
            bounds.append((n, m.group(2)))
        elif g.NO_GENRE_HEADING.match(line):
            bounds.append((n, "No Genre"))
    bounds.append((len(lines) + 1, None))

    by_title = {s["title"]: s for s in genres}
    by_title["No Genre"] = no_genre
    flagged = 0

    for i, (start, title) in enumerate(bounds[:-1]):
        end = bounds[i + 1][0]
        section = by_title.get(title)
        if not section:
            continue
        real = {"preset": len(section.get("presets", [])),
                "shape": len(section.get("shapes", []))}
        rows = []
        for n in range(start, end):
            line = lines[n - 1]
            seen_total = {(value(t), kindof(nn)) for t, nn in SUBSET.findall(line)}
            for pat in TOTALS:
                for token, noun in pat.findall(line):
                    v, kind = value(token), kindof(noun)
                    seen_total.add((v, kind))
                    if v != real[kind]:
                        rows.append((n, token, noun, kind, real[kind],
                                     "states the total"))
            for token, noun in CLAIM.findall(line):
                v, kind = value(token), kindof(noun)
                if v in IGNORE_VALUES or (v, kind) in seen_total:
                    continue
                if v > real[kind]:
                    rows.append((n, token, noun, kind, real[kind],
                                 "more than exist"))
        if rows:
            print(f"{title}  ({real['preset']} presets, {real['shape']} shapes)")
            for n, token, noun, kind, actual, why in rows:
                print(f"  line {n}: \"{token} {noun}\" {why}, "
                      f"but the genre has {actual} {kind}s")
                flagged += 1
            print()

    # A genre can also be discussed by name from outside its own section --
    # the general Presets section cites Shooter, for instance. Those claims
    # are the easiest to leave behind when a table grows, so scan the whole
    # file for "<Genre>'s N presets" too.
    named = {}
    for section in genres:
        short = section["title"].split(" (")[0].split(" & ")[0].strip()
        named[short.lower()] = (section["title"], section)
    cross = re.compile(
        rf"\b({'|'.join(re.escape(k) for k in named)})'s\s+({NUM})\s+{NOUN}\b",
        re.I)
    for n, line in enumerate(lines, 1):
        for name, token, noun in cross.findall(line):
            title, section = named[name.lower()]
            kind = kindof(noun)
            actual = len(section.get(kind + "s", []))
            if value(token) != actual:
                print(f"{title} (cited from line {n}, outside its section)")
                print(f"  \"{name}'s {token} {noun}\" but the genre has "
                      f"{actual} {kind}s")
                print()
                flagged += 1

    flagged += check_pipeline(build)

    print(f"{flagged} count claim(s) disagreeing with the table they describe")
    print("(subset claims smaller than the total need a human read)")
    return 1 if flagged else 0


def check_pipeline(build: str) -> int:
    """Claims in Pipeline.md that a table in Build.md can settle."""
    doc = ROOT / "docs" / "LayoutGen - Pipeline.md"
    if not doc.exists():
        return 0
    text = doc.read_text(encoding="utf-8")
    flagged = 0

    universals = g.parse_universal_options(
        g.section_body(build, g.UNIVERSAL_HEADING))
    routed = sum(1 for o in universals if o.get("pipeline"))
    for m in re.finditer(rf"\b({NUM})\s+of\s+(?:them|the\s+{NUM})\s+carry\s+a\s+route",
                         text, re.I):
        if value(m.group(1)) != routed:
            line = text[:m.start()].count("\n") + 1
            print(f"Pipeline.md line {line}: \"{m.group(0)}\" but "
                  f"{routed} of the {len(universals)} universal options do")
            print()
            flagged += 1

    catalog = g.parse_shape_catalog(
        g.section_body(build, g.SHAPE_CATALOG_HEADING))
    for m in re.finditer(rf"\b({NUM})\s+shapes?,\s+({NUM})\s+rows?", text, re.I):
        if value(m.group(1)) != len(catalog) or value(m.group(2)) != len(catalog):
            line = text[:m.start()].count("\n") + 1
            print(f"Pipeline.md line {line}: \"{m.group(0)}\" but the "
                  f"catalogue holds {len(catalog)} shapes")
            print()
            flagged += 1

    # The assumptions table is Pipeline's own, so count its rows in place.
    rows = len(re.findall(r"^\| \*\*A\d+\*\* \|", text, re.M))
    for m in re.finditer(rf"\b({NUM})\s+assumptions\s+are\s+hard-coded", text, re.I):
        if rows and value(m.group(1)) != rows:
            line = text[:m.start()].count("\n") + 1
            print(f"Pipeline.md line {line}: \"{m.group(0)}\" but the table "
                  f"below lists {rows}")
            print()
            flagged += 1
    return flagged


if __name__ == "__main__":
    raise SystemExit(main())
