#!/usr/bin/env python3
"""Which pipeline modifiers can actually be delivered, stated once per file.

The readiness split is asserted in Build.md, twice in Pipeline.md and once in
`genre-choice/SKILL.md`, because each of them needs it in front of a different
decision. Four copies of a fact that changes is four chances to disagree, and
they already did once: a support-status note called P2 and P4 "real, buildable"
a hundred lines above a gate listing them as not production-ready.

So the duplication stays and becomes checked. Every file that names the split
must name the same one.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TARGETS = [
    ROOT / "docs" / "LayoutGen - Build.md",
    ROOT / "docs" / "LayoutGen - Pipeline.md",
    ROOT / ".cursor" / "skills" / "genre-choice" / "SKILL.md",
    ROOT / ".cursor" / "skills" / "layout-intake" / "SKILL.md",
]

MODIFIER = r"`?(P[0-6]|CHECK|SET|tiered)`?"

READY = re.compile(
    rf"((?:{MODIFIER}[,\s]*(?:and\s+)?){{1,6}})\s+(?:are|is)\s+"
    r"(?:proven and running|built and running|running today)", re.I)
NOT_READY = re.compile(
    rf"((?:{MODIFIER}[,\s]*(?:and\s+)?){{1,6}})\s+(?:are|is)\s+"
    r"not\s+(?:production-ready|ready)", re.I)

TOKEN = re.compile(MODIFIER)


def modifiers(blob: str) -> frozenset[str]:
    return frozenset(m.group(1).upper() for m in TOKEN.finditer(blob))


# Files that must each carry the split. A file dropping its copy is as bad as
# a file disagreeing, because the reader in front of that decision loses it.
MUST_STATE = {
    "LayoutGen - Build.md",
    "LayoutGen - Pipeline.md",
    "SKILL.md",  # genre-choice, which acts on it
}


def main() -> int:
    ready: dict[str, list[str]] = {}
    unready: dict[str, list[str]] = {}
    stating: set[str] = set()

    for path in TARGETS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern, bucket in ((READY, ready), (NOT_READY, unready)):
            for m in pattern.finditer(text):
                key = ", ".join(sorted(modifiers(m.group(1))))
                line = text[:m.start()].count("\n") + 1
                bucket.setdefault(key, []).append(f"{path.name}:{line}")
                stating.add(path.name)

    problems = 0
    for label, bucket in (("running", ready), ("not production-ready", unready)):
        if not bucket:
            print(f"no statement found for '{label}' -- the checker is stale "
                  f"or the fact was deleted")
            problems += 1
            continue
        print(f"{label}:")
        for key, where in sorted(bucket.items()):
            print(f"  {key:<28} {', '.join(where)}")
        if len(bucket) > 1:
            print(f"  ^ {len(bucket)} different answers for '{label}'")
            problems += 1
        print()

    for r in ready:
        for u in unready:
            both = set(r.split(", ")) & set(u.split(", "))
            if both:
                print(f"a modifier is called both running and not ready: "
                      f"{', '.join(sorted(both))}")
                problems += 1

    missing = MUST_STATE - stating
    if missing:
        print(f"file(s) that should state the split and do not: "
              f"{', '.join(sorted(missing))}")
        problems += 1

    print(f"{problems} disagreement(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
