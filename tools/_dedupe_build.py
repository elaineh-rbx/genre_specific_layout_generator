#!/usr/bin/env python3
"""One-shot: cut passages that restate what an earlier section already said.

Merging the shape prose into a single Shapes section left the Shape Catalog
still carrying its own copy of it -- what a shape is, that a game has one,
that every row is reachable from every genre, that a genre may reword one.
A catalogue only needs to say what is true of reading that table.

Each cut below removes a second telling, never the only telling. The kept
copy is named in the comment.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "docs" / "LayoutGen - Build.md"

CUTS: list[tuple[str, str, str]] = [
    # The catalogue intro restated the whole Shapes section. What survives is
    # the one fact particular to this table: whose wording a row carries.
    (
        "catalogue intro restating Shapes",
        "Every shape in the system, and **every one of them is reachable from every genre**. "
        "A shape answers one question — *what shape is this space?* — so a game has exactly one, "
        "and the pick is almost always the pipeline-routing decision. The route lives here and only here.\n"
        "\n"
        "Genres do not own shapes; they **recommend** a handful and name a default, in each genre's own "
        "**Typical shapes** line. That list is presentation, not a restriction: when a prompt fits none of "
        "them, take any other row in this table and say which one you took and why.\n"
        "\n"
        "**A genre may reword any row** — same ID, its own sentence, exactly as shared options work. "
        "The wording below is what a genre inherits when it states none of its own.",

        # No pointer to the Shapes section: this paragraph is also the opening of
        # the generated shapes.md, where "above" resolves to nothing.
        "Every shape in the system, and the **route lives here and only here**. "
        "The wording below is what a genre inherits when it states none of its own.",
    ),
    # Verbatim duplicate: the restructure copied this into Shapes and left the
    # original standing at the end of the catalogue.
    (
        "duplicated Shared Vocabulary type paragraph",
        "\n**A shape carries a Shared Vocabulary type when it is itself a region**, using the same "
        "`Type (Flavor Name)` form as an option — an arena is a `CombatZone` whatever form it takes, "
        "and segmentation needs it typed like anything else. Shapes that describe **map topology** "
        "rather than a place — *Open World* versus *Chaptered Journey* — carry no type, because there "
        "is no single region to name.\n\n## **Options**",

        "\n## **Options**",
    ),
    # The shortlist relationship is stated in Shapes; after the table it only
    # needs to settle that the count is the whole count.
    (
        "third telling of the Typical shapes shortlist",
        "**45 shapes, and the catalogue is the whole answer** — a genre's *Typical shapes* line is a "
        "shortlist drawn from this table, never a separate set.",

        "**45 shapes, and the catalogue is the whole answer.**",
    ),
    # The appendix opened by restating the scope note from the front matter and
    # the ControlZone/TriggerZone warning from Shared Vocabulary.
    (
        "appendix restating the mechanic-wiring scope note",
        "Primitives marked **mechanic** in the vocabulary are wired to gameplay behavior by a separate "
        "functional game framework (the mechanic wiring is out of scope for this document — these rules "
        "only define the layout role and name). This appendix captures guidance that spans that "
        "layout/gameplay boundary, independent of which framework does the wiring.",

        "Guidance that spans the layout/gameplay boundary, independent of which framework does the "
        "wiring. *Shared Vocabulary* above says where that boundary sits.",
    ),
    (
        "appendix restating the ControlZone warning",
        "* `ControlZone` **vs plain regions.** `ControlZone` is a capacity/occupancy area with an "
        "indicator (KotH-style). Plain regions that only need entry/exit detection are `TriggerZone`s. "
        "Never conflate the two.  ",

        None,  # stated in Shared Vocabulary, which is where a reader meets both
    ),
]


def main() -> int:
    text = BUILD.read_text(encoding="utf-8")
    before = len(text.splitlines())

    for label, old, new in CUTS:
        if old not in text:
            raise SystemExit(f"passage not found: {label}\n---\n{old[:160]}")
        if new is None:
            # Drop the whole line, including its newline.
            text = text.replace(old + "\n", "", 1)
        else:
            text = text.replace(old, new, 1)
        print(f"  cut  {label}")

    BUILD.write_text(text, encoding="utf-8")
    after = len(text.splitlines())
    print(f"\n{before} -> {after} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
