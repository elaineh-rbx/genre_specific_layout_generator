#!/usr/bin/env python3
"""A section named in prose must be a section that exists.

Build.md and Pipeline.md point at each other's sections by name -- "see
*Pipeline costs* in Build.md", "the readiness gate in Part IV". Renaming or
merging a heading leaves those pointing at nothing, and because the text
still reads fine nobody notices. Reorganising Part II broke two of them.

Collects every heading in both docs plus the skills, then checks each
italicised cross-reference resolves to one.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DOCS = [
    ROOT / "docs" / "LayoutGen - Build.md",
    ROOT / "docs" / "LayoutGen - Pipeline.md",
]
SKILLS = sorted((ROOT / ".cursor" / "skills").rglob("*.md"))

HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$")

# "see *Foo*", "*Foo* in Build.md", "*Foo* above/below"
REFERENCE = re.compile(
    r"(?:see\s+|\bin\s+)?\*([A-Z][A-Za-z0-9'’\- ]{3,50})\*"
    r"(?=\s+(?:in|of)\s+(?:`?LayoutGen - )?(?:Build|Pipeline)\.md"
    r"|\s+(?:above|below)\b)")

# Italics that are emphasis or a proper noun, not a pointer to a section.
IGNORE = {
    "Modelled on", "Typical shapes", "Deathmatch Shooter", "Battle Royale",
    "Explorable Place", "Open World Action", "Escape Room", "Tower Obby",
    "Battlegrounds", "Tycoon", "Chaptered Journey", "Open World",
    "Team Deathmatch", "Idle", "Incremental Simulator", "Physics Sim",
    "Sandbox", "Vehicle Sim", "Animal Sim", "Dress Up", "Life",
    "Morph Roleplay", "Pet Care", "Action RPG", "Turn-based RPG",
    "Board", "Card Games", "Tower Defense", "Aim Trainer", "Video",
}


def normalise(text: str) -> str:
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"[`\\]", "", text)
    text = re.sub(r"^\d+\.\s*", "", text)
    text = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    return " ".join(text.split())


def main() -> int:
    headings: set[str] = set()
    for path in DOCS + SKILLS:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            m = HEADING.match(line)
            if m:
                headings.add(normalise(m.group(1)))
    # Part and section numbering referenced in prose.
    headings |= {f"part {n}" for n in ("0", "i", "ii", "iii", "iv", "v", "vi", "vii")}

    problems = 0
    for path in DOCS + SKILLS:
        if not path.exists():
            continue
        rel = path.relative_to(ROOT)
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for name in REFERENCE.findall(line):
                if name.strip() in IGNORE:
                    continue
                key = normalise(name)
                if key in headings:
                    continue
                # A reference may name only the start of a longer heading.
                if any(h.startswith(key) for h in headings):
                    continue
                print(f"{rel}:{n}: *{name}* names no heading that exists")
                problems += 1

    print(f"\n{problems} dangling section reference(s) "
          f"({len(headings)} headings known)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
