#!/usr/bin/env python3
"""One-shot: the skills findings, plus the Build.md source of a generated leak.

A skill is read by an agent at runtime, so a sentence that does not change a
decision is cost with no return. These cut history and self-assessment and
keep the instruction.

The Universal Options rewrites are in Build.md rather than in a skill because
that block generates into all sixteen genre files; fixing it once fixes them
all.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENRE_CHOICE = ROOT / ".cursor" / "skills" / "genre-choice" / "SKILL.md"
INTAKE = ROOT / ".cursor" / "skills" / "layout-intake" / "SKILL.md"
BUILD = ROOT / "docs" / "LayoutGen - Build.md"

EDITS: list[tuple[Path, str, str]] = [
    # --- genre-choice ------------------------------------------------------
    (GENRE_CHOICE,
     "**Two questions in this order, and do not merge them.** They used to be one,\n"
     "and collapsing them is what made this the least accurate step in the skill.",
     "**Two questions in this order, and do not merge them.** Merging them is the\n"
     "single most common way this step goes wrong."),

    (GENRE_CHOICE,
     "**Do not load `shapes.md` by default** \u2014 reaching for forty rows when five would\n"
     "do is how a short menu becomes an unusable one.",
     "**Do not load `shapes.md` by default** \u2014 reaching for the whole catalogue when\n"
     "five rows would do is how a short menu becomes an unusable one."),

    (GENRE_CHOICE,
     "\"houses you sleep in\", \"shops you buy from\", \"temples with a boss inside\" all\n"
     "require going indoors. About half of the rows that look like an assumed `P3`\n"
     "are really this. **If the game plainly has the feature, the modifier is\n"
     "required.**",
     "\"houses you sleep in\", \"shops you buy from\", \"temples with a boss inside\" all\n"
     "require going indoors. Much of the `P3` that looks assumed is really this.\n"
     "**If the game plainly has the feature, the modifier is required.**"),

    (GENRE_CHOICE,
     "## Maintenance\n\n"
     "`genres/*.md` are generated from `docs/LayoutGen - Build.md` Part II, which is\n"
     "canonical. Edit Build.md, then run:\n\n"
     "```bash\n"
     "python tools/generate_genre_skills.py\n"
     "```\n\n"
     "`--check` verifies the files are current and exits non-zero if not.",
     "## Maintenance\n\n"
     "`genres/*.md`, `shapes.md` and `no-genre.md` are generated from\n"
     "`docs/LayoutGen - Build.md`. **Never edit them directly** \u2014 edit Build.md and\n"
     "run `python tools/generate_genre_skills.py`."),

    # --- layout-intake -----------------------------------------------------
    (INTAKE,
     "**Goal / win-or-loop condition is deliberately not a concern here.** Part V of\n"
     "`docs/LayoutGen - Pipeline.md` proposed wiring it in as the next one; the\n"
     "decision went the other way. A win condition is gameplay \u2014 identical maps carry\n"
     "different ones \u2014 so intake does not ask about it, and asking was the largest\n"
     "source of questions nothing could use.",
     "**Goal / win-or-loop condition is deliberately not a concern here, and you must\n"
     "not ask about it.** A win condition is gameplay, not layout \u2014 identical maps\n"
     "carry different ones \u2014 so nothing downstream can use the answer."),

    # --- Build.md, because this block generates into all sixteen genre files
    (BUILD,
     "They exist because the alternative is worse. Each is asked for across eleven to fifteen different genres, so filing them per-genre would restate the same row dozens of times \u2014 and leaving them out is what produced the largest hole in the system, with *who is in the world* having no home anywhere.",
     "They exist because the alternative is worse. Each is wanted across nearly every genre, so filing them per-genre would restate the same row dozens of times, and leaving them out strands common requests \u2014 *who is in the world* would have no home anywhere."),

    (BUILD,
     "never a default and never a suggestion. Each of the six is wanted by only a small minority of prompts, so a run that applies one unasked is wrong far more often than right.",
     "never a default and never a suggestion. Most builds want none of them, so a run that applies one unasked is wrong far more often than right."),
]


def main() -> int:
    missing = []
    by_file: dict[Path, str] = {}
    for path, old, _ in EDITS:
        if path not in by_file:
            by_file[path] = path.read_text(encoding="utf-8")
        if old not in by_file[path]:
            missing.append((path.name, old[:70]))
    for path, old, new in EDITS:
        by_file[path] = by_file[path].replace(old, new, 1)
    for path, text in by_file.items():
        path.write_text(text, encoding="utf-8")
    print(f"applied {len(EDITS) - len(missing)}/{len(EDITS)}")
    for name, snippet in missing:
        print(f"  MISS in {name}: {snippet}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
