#!/usr/bin/env python3
"""Guard the option catalogue the way check_shape_reachability guards shapes.

Options are now reachable from any genre, which means the generated
`options.md` is the only place some of them can be found. Three things can
quietly break that and none would fail the generator:

  missing from catalogue   an option in a genre table that options.md omits
  route drift              a row whose route changed without being marked
  lost concept             an option with no usable description anywhere,
                           so a genre reaching it has nothing to bend

The fourth check is the one that matters for intake. A genre table is now a
shortlist, so the skill has to be told the catalogue exists -- if the
matching-order rule ever falls out of SKILL.md, reachability becomes a
sentence in Build.md that nothing acts on. That failure is invisible to
every other check we run.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_genre_skills as g  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "docs" / "LayoutGen - Build.md"
SKILL = ROOT / ".cursor" / "skills" / "genre-choice" / "SKILL.md"
CATALOG = ROOT / ".cursor" / "skills" / "genre-choice" / "options.md"

ROW = re.compile(
    r"^\| `([a-z0-9-]+)` \| \*\*(.+?)\*\* \| (.*?) \| (`[a-z]+`|\*varies\*) \| (.*?) \| (.*?) \|$")
# `Type (Flavor Name)`. The handoff's layout_placement.type is the Type, and a
# lane that reaches a row only visible in the catalogue has nowhere else to
# read it -- the first pilot record hit exactly that and had to guess.
TYPED = re.compile(r"^(\w+) \(.+\)$")


def main() -> int:
    if not CATALOG.exists():
        print("FAIL: options.md does not exist -- run generate_genre_skills.py")
        return 1

    text = BUILD.read_text(encoding="utf-8")
    genres, no_genre, _ = g.parse_all(text)
    universal = {
        o["id"] for o in
        g.parse_universal_options(g.section_body(text, g.UNIVERSAL_HEADING))
    }

    in_tables: dict[str, list[str]] = {}
    dests: dict[str, set[str]] = {}
    sections = [
        *genres,
        {"title": "No Genre", "options": no_genre.get("options", [])},
    ]
    for section in sections:
        for o in section.get("options", []):
            in_tables.setdefault(o["id"], []).append(section["title"])
            dests.setdefault(o["id"], set()).add(o.get("goesTo") or "image")

    rows = {}
    for line in CATALOG.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if m:
            rows[m.group(1)] = {"typed": m.group(2).strip(),
                                "concept": m.group(3).strip(),
                                "goes": m.group(4).strip("`"),
                                "route": m.group(5).strip()}

    failures: list[str] = []

    missing = sorted(set(in_tables) - set(rows))
    for oid in missing:
        failures.append(f"missing from catalogue: {oid} "
                        f"(in {', '.join(in_tables[oid])})")

    extra = sorted(set(rows) - set(in_tables) - universal)
    for oid in extra:
        failures.append(f"catalogue row belongs to no source table: {oid}")

    for oid, row in sorted(rows.items()):
        if not row["concept"]:
            failures.append(f"no description to bend: {oid}")
        if row["goes"] not in {"image", "layout", "both", "*varies*"}:
            failures.append(f"bad destination: {oid} -> {row['goes']}")
        if not TYPED.match(row["typed"]):
            failures.append(f"no Type to put in the handoff: {oid} "
                            f"-> {row['typed']!r}")
        # Flattening a genuine disagreement is worse than not publishing the
        # column: the catalogue's preamble says the destination comes with the
        # row, so a silently-picked one reads as settled. A pilot lane caught
        # trigger-scoring stated as `layout` against Sports' `both`.
        d = dests.get(oid)
        if d and len(d) > 1 and row["goes"] != "*varies*":
            failures.append(f"catalogue settles a destination the genres "
                            f"dispute: {oid} -> {row['goes']} "
                            f"but genres say {'/'.join(sorted(d))}")

    # Presence of a string proves nothing -- "options.md" also appears in the
    # "do not load it by default" line, so an earlier version of this check
    # passed while the matching-order table was gone. What has to hold is the
    # order: genre table, then universal, then the catalogue, then free text.
    # Free text last is the load-bearing part, because it is the only step
    # that silently drops the route.
    skill = SKILL.read_text(encoding="utf-8")
    if "reachable from every genre" not in skill:
        failures.append("SKILL.md does not state that options are reachable")

    # Scoped to the section, not the whole file: several of these phrases
    # appear in earlier prose, and searching the document found those instead.
    HEAD = "### Options are shared too"
    start = skill.find(HEAD)
    if start < 0:
        failures.append(f"SKILL.md: '{HEAD}' section is gone")
        skill = ""
    else:
        end = skill.find("\n### ", start + len(HEAD))
        skill = skill[start:end if end > 0 else len(skill)]

    # A rule stated in one section and contradicted in another is the failure
    # this actually hit: step 2 said to reach into the catalogue while step 5
    # still said "do not go looking through the other genres for an ID". The
    # order check above is scoped to its section and cannot see that, so scan
    # the whole file for phrasings that re-fence options.
    whole = SKILL.read_text(encoding="utf-8").lower()
    for phrase in ("do not go looking through the other genres",
                   "match only against loaded files",
                   "only options from the loaded",
                   "options the loaded file does not have cannot"):
        if phrase in whole:
            failures.append(f"SKILL.md contradicts reachability: '{phrase}'")

    order = [
        ("genre's own **Options** table", "the genre's own table"),
        ("**Universal Options**", "the universal six"),
        ("**`options.md`**", "the catalogue"),
        ('`"id": null`', "the free-text escape hatch"),
    ]
    found = []
    for needle, label in order:
        i = skill.find(needle)
        if i < 0:
            failures.append(f"SKILL.md: matching order lost {label}")
        found.append((i, label))
    if all(i >= 0 for i, _ in found):
        ranked = [lbl for _, lbl in sorted(found)]
        if ranked != [lbl for _, lbl in found]:
            failures.append("SKILL.md: matching order is out of sequence -- "
                            f"reads {' then '.join(ranked)}")

    varies = sum(1 for r in rows.values() if "varies" in r["route"])
    print(f"{len(rows)} options in the catalogue, {len(universal)} universal, "
          f"{varies} with a route that varies by genre")
    private = sum(1 for v in in_tables.values() if len(v) == 1)
    print(f"{private} sit in exactly one source table and are reachable only "
          f"through options.md")

    if failures:
        print(f"\nFAIL ({len(failures)}):")
        for f in failures:
            print(f"  {f}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
