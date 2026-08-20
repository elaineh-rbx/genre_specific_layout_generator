#!/usr/bin/env python3
"""One-shot: spend words where the idea is unfamiliar, not where it is obvious.

A preset is a premade bundle. Everybody has met one. Build.md was spending
nine paragraphs on it, and seven of those were runtime tuning rules that
`genre-choice` step 3 already states in its own words -- swap the shape,
drop contradicted options, emit `preset: null`, a secondary genre's preset
is fair game. Build.md keeps what only it can say: what a preset is made
of, what the `Modelled on` column means, and where display names come from,
which is authoring guidance for whoever adds a row.

Shape is the opposite case. It is this system's own word for something most
people have no term for, and the section opened with a formal definition
that only lands if you already know what it is naming. It gets a sentence
of plain meaning first.

Also fixes numbered list items left split mid-sentence by the paragraph
unwrapping in the Part II restructure.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "docs" / "LayoutGen - Build.md"

SHAPES_OLD = (
    "**A shape is one answer on each of the five routing axes, plus a description of the "
    "space.** That is the whole definition. The axes give it a route; the description is "
    "what reaches the image model. Because a shape answers a single question — *what shape "
    "is this space?* — the answers are mutually exclusive and a game has exactly one, with "
    "every option additive on top of it."
)

SHAPES_NEW = (
    "**Shape is this system's word for the overall form a play space takes** — an arena, a "
    "lap circuit, a tower, a run of rooms, one open world, a board on a table. Most ways of "
    "describing a game name the *genre* and leave the form implied, so there is no common "
    "word for this, but the form is the thing that actually has to be built. Hence a term of "
    "our own.\n"
    "\n"
    "Concretely, **a shape is one answer on each of the five routing axes plus a description "
    "of the space**. The axes give it a route; the description is what reaches the image "
    "model. It answers a single question — *what shape is this space?* — so the answers are "
    "mutually exclusive, a game has exactly one, and every option is additive on top of it."
)

PRESETS_OLD_START = "## **Presets**\n"
PRESETS_OLD_END = "\n## **Offering, tuning and mixing**"

PRESETS_NEW = """## **Presets**

A preset is a **premade pick — one shape plus a few option IDs** — modelled on a real game, so the common case is one decision rather than a dozen. It is a suggestion rather than a package, and the shape it names is a **default rather than a member of the bundle**: shape is exclusive, so a preset whose mode is right and whose shape is wrong should lose the shape, not the preset. Tuning one at runtime — substituting the shape, adding and dropping options, when to emit `preset: null` — is `genre-choice` step 3.

**Every preset carries two names and only one is shown.** The *Modelled on* column names the real game and is **internal reference only**; it grounds the preset in something concrete so the intent is unambiguous. What a user sees is the generic style name — a Counter-Strike map is offered as "round-based bomb defusal", never by the game's name. Reference games are drawn from 3D games generally, with Roblox examples wherever the platform has a canonical one, since Roblox convention is often what a user is picturing.

**Take that display name from a published taxonomy rather than inventing one**, so the user recognises it immediately. Roblox's own subgenre where one fits, since that is what a creator sees in the Creator Dashboard and what Discovery sorts by — *Battlegrounds*, *Tower Obby*, *Escape Room*, *Tycoon*, *Battle Royale*, *Open World Action*. The established industry term where Roblox's taxonomy is too coarse: it files Team Deathmatch, Capture the Flag and free-for-all all under *Deathmatch Shooter*, and those are three different layouts. A plain descriptive name only when neither exists.
"""


def main() -> int:
    text = BUILD.read_text(encoding="utf-8")
    before = len(text.splitlines())

    if SHAPES_OLD not in text:
        raise SystemExit("Shapes opening not found")
    text = text.replace(SHAPES_OLD, SHAPES_NEW, 1)
    print("  reworked  Shapes opening")

    start = text.index(PRESETS_OLD_START)
    end = text.index(PRESETS_OLD_END, start)
    cut = len(text[start:end].splitlines())
    text = text[:start] + PRESETS_NEW + text[end:]
    print(f"  trimmed   Presets ({cut} lines -> {len(PRESETS_NEW.splitlines())})")

    BUILD.write_text(text, encoding="utf-8")
    print(f"\n{before} -> {len(text.splitlines())} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
