#!/usr/bin/env python3
"""Every `kebab-case-id` written in prose must name something real.

Prose drifts from tables. A rule that says "reach for `stage-performance`"
when the catalogue calls it `venue-stage` is worse than no rule, because an
agent reading the skill will look the name up and find nothing.

Scans Build.md, Pipeline.md and the skill files for backticked identifiers
that look like shape or option IDs, and reports any that no table defines.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import generate_genre_skills as g  # noqa: E402

TARGETS = [
    ROOT / "docs" / "LayoutGen - Build.md",
    ROOT / "docs" / "LayoutGen - Pipeline.md",
    *sorted((ROOT / ".cursor" / "skills").rglob("*.md")),
]

# `two-part-lowercase` or longer. Excludes single words, so `image`, `layout`
# and `notes` do not trip it.
ID_LIKE = re.compile(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`")

# Identifiers that are real but are not catalogue rows: schema fields, stream
# names, pipeline vocabulary, filenames, CSS/JS, and Roblox API names.
ALLOW = {
    # handoff / schema
    "layout-intake", "genre-choice", "uprez-prompt", "no-genre",
    "layout_placement",
    "axis-enclosure", "axis-verticality", "axis-zone-count",
    "axis-structure", "axis-play-space",
    # axis values
    "interior-only", "exterior-only", "single-surface", "multi-zone",
    "single-zone", "zone-count", "play-space", "top-down", "top-downs",
    # tooling and files
    "generate_genre_skills", "check_pipeline_sync", "check_shape_reachability",
    "check_viewer_chart", "measure_shape_gaps", "shape-migration",
    "pipeline-viewer", "widget_metadata", "eval_questions",
    "intake-questions", "scale-reframe",
    # roblox / engine
    "walk-speed", "jump-height", "can-touch", "can-collide",
    "roblox-studio", "part-count",
    # image / render vocabulary
    "isometric_a", "isometric_b", "isometric_c", "isometric_d", "isometric_e",
}


def known_ids(build_text: str) -> set[str]:
    genres, no_genre, catalog = g.parse_all(build_text)
    ids: set[str] = set(catalog)
    for section in (*genres, no_genre):
        for opt in section.get("options", []):
            ids.add(opt["id"])
        for shp in section.get("shapes", []):
            ids.add(shp["id"])
        for preset in section.get("presets", []):
            if preset.get("shape"):
                ids.add(preset["shape"])
            for oid in preset.get("options", []):
                ids.add(oid)
    for ax in no_genre.get("axes", []):
        ids.add(ax["id"])
        for choice in ax.get("choices", []):
            ids.add(choice["id"])
    return ids


def main() -> int:
    build = (ROOT / "docs" / "LayoutGen - Build.md").read_text(encoding="utf-8")
    ids = known_ids(build)
    problems = 0
    for path in TARGETS:
        if not path.exists():
            continue
        unknown: dict[str, list[int]] = {}
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in ID_LIKE.findall(line):
                if match in ids or match in ALLOW or match.endswith(".md"):
                    continue
                unknown.setdefault(match, []).append(n)
        if unknown:
            rel = path.relative_to(ROOT)
            print(f"\n{rel}")
            for name, lines in sorted(unknown.items()):
                where = ", ".join(str(x) for x in lines[:6])
                more = f" (+{len(lines) - 6} more)" if len(lines) > 6 else ""
                print(f"  {name:<28} line {where}{more}")
                problems += 1
    print(f"\n{problems} unknown identifier(s) referenced in prose")
    print(f"({len(ids)} ids defined in Build.md)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
