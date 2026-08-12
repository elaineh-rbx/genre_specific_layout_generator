"""Compare the upstream first-pass config against the answered config, per scene.

Each scene under `results/routing/answered/` carries two configs side by side:
its upstream first-pass pick (prompt only) and the answered pick (prompt +
author-answered clarifications). This tool tallies the shifts, buckets them
by axis, and prints a plain-text report so the character of the change is
visible before committing to render from the answered configs.

Axes reported (in order of how deep the shift goes):

    genre     the game type - deepest possible shift, changes every downstream
    shape     the shape id  - almost always the pipeline-routing decision
    preset    which preset  - a shape+options bundle; "none" means built option-
              by-option instead of from a preset
    route     the pipeline modifiers the picks force (P0/P3/P4/P6, +tiered, etc.)
    options   the option ids picked; reported as added / dropped counts

Usage:
    python tools/analyze_config_shifts.py                       # summary + top transitions
    python tools/analyze_config_shifts.py --show 5              # 5 example scenes per transition
    python tools/analyze_config_shifts.py --md report.md        # write a Markdown report
    python tools/analyze_config_shifts.py --scenes P0002,P0620  # inspect specific scenes
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter
from dataclasses import dataclass

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen.model.handoff import GENRE_BY_SLUG
from layoutgen.paths import ROUTING

ANSWERED = ROUTING / "answered"


def canon_genre(slug_or_name: str) -> str:
    if not slug_or_name:
        return "(none)"
    return GENRE_BY_SLUG.get(slug_or_name.lower(), slug_or_name)


@dataclass
class SceneDiff:
    scene: str
    prompt: str
    genre_from: str
    genre_to: str
    shape_from: str
    shape_to: str
    preset_from: str
    preset_to: str
    route_from: str
    route_to: str
    opts_added: list[str]
    opts_dropped: list[str]

    @property
    def genre_same(self) -> bool: return self.genre_from == self.genre_to
    @property
    def shape_same(self) -> bool: return self.shape_from.lower() == self.shape_to.lower()
    @property
    def preset_same(self) -> bool: return self.preset_from.lower() == self.preset_to.lower()
    @property
    def route_same(self) -> bool: return self.route_from == self.route_to
    @property
    def touched(self) -> int:
        """How many axes changed. 0 means answered config matches upstream exactly."""
        return sum([not self.genre_same, not self.shape_same,
                    not self.preset_same, not self.route_same]) \
             + (1 if self.opts_added or self.opts_dropped else 0)


def load_diffs() -> list[SceneDiff]:
    out: list[SceneDiff] = []
    for p in sorted(ANSWERED.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        up = d.get("upstream_skill", {})
        cfg = d.get("config", {})
        up_opts = []                # the upstream block doesn't have options in the summary
        # Recover the upstream options list from the sibling skill/<scene>.json.
        skill_path = ROUTING / "skill" / f"{d['scene']}.json"
        if skill_path.exists():
            skill = json.loads(skill_path.read_text(encoding="utf-8"))
            block = skill.get("block") or {}
            up_opts = [e.get("id") for e in (block.get("image_prompt") or []) if e.get("id")]
            up_opts += [e.get("id") for e in (block.get("layout_placement") or [])
                        if e.get("id") and e.get("id") not in up_opts]
        an_opts = cfg.get("options") or []
        added = [o for o in an_opts if o not in up_opts]
        dropped = [o for o in up_opts if o not in an_opts]
        out.append(SceneDiff(
            scene=d["scene"],
            prompt=d.get("source", "").replace("\n", " ")[:160],
            genre_from=canon_genre((up.get("genres") or [None])[0]),
            genre_to=cfg.get("genre", ""),
            shape_from=up.get("shape") or "(none)",
            shape_to=cfg.get("shape") or "(none)",
            preset_from=up.get("preset") or "none",
            preset_to=cfg.get("preset") or "none",
            route_from=" + ".join(up.get("pipeline") or []) or "(none)",
            route_to=" + ".join(cfg.get("route") or []) or "(none)",
            opts_added=added,
            opts_dropped=dropped,
        ))
    return out


def summary(diffs: list[SceneDiff]) -> list[str]:
    n = len(diffs)
    same = lambda k: sum(getattr(d, k) for d in diffs)
    lines = [f"scenes compared: {n}", ""]
    lines.append("agreement between upstream first-pass and answered config:")
    for label, attr in [("genre", "genre_same"), ("shape", "shape_same"),
                        ("preset", "preset_same"), ("route", "route_same")]:
        s = same(attr)
        lines.append(f"  {label:8}  {s}/{n}  ({100*s//n}% agree, {n-s} shifted)")
    opts_touched = sum(1 for d in diffs if d.opts_added or d.opts_dropped)
    lines.append(f"  {'options':8}  {n-opts_touched}/{n}  ({100*(n-opts_touched)//n}%"
                 f" identical set, {opts_touched} changed the picked set)")
    lines.append("")
    touched = Counter(d.touched for d in diffs)
    lines.append("scenes by number of axes shifted (out of 5):")
    for k in sorted(touched):
        lines.append(f"  {k} axis {'shifted' if k else 'unchanged'}: {touched[k]}")
    return lines


def transitions(diffs: list[SceneDiff], key: str, top: int = 15) -> list[str]:
    def pair(d: SceneDiff) -> tuple[str, str]:
        return getattr(d, f"{key}_from"), getattr(d, f"{key}_to")
    counts: Counter = Counter(pair(d) for d in diffs if pair(d)[0] != pair(d)[1]
                              or (key not in ("genre",) and
                                  pair(d)[0].lower() != pair(d)[1].lower()))
    counts = Counter({p: c for p, c in counts.items() if p[0] != p[1]})
    total_shift = sum(counts.values())
    lines = [f"top {key} shifts (of {total_shift} shifted scenes):"]
    for (a, b), c in counts.most_common(top):
        lines.append(f"  {c:4}  {a:>34}  ->  {b}")
    return lines


def examples(diffs: list[SceneDiff], key: str, top: int, per: int) -> list[str]:
    def pair(d: SceneDiff) -> tuple[str, str]:
        return getattr(d, f"{key}_from"), getattr(d, f"{key}_to")
    counts: Counter = Counter(pair(d) for d in diffs if pair(d)[0] != pair(d)[1])
    lines = [f"\nexamples of top {key} shifts (up to {per} per transition):"]
    for (a, b), c in counts.most_common(top):
        lines.append(f"\n  {a} -> {b}  ({c} scenes)")
        picked = 0
        for d in diffs:
            if pair(d) == (a, b):
                lines.append(f"    {d.scene}  {d.prompt}")
                picked += 1
                if picked >= per:
                    break
    return lines


def scene_details(diffs: list[SceneDiff], want: set[str]) -> list[str]:
    lines: list[str] = []
    for d in diffs:
        if d.scene not in want:
            continue
        lines.append(f"\n{'='*72}")
        lines.append(f"{d.scene}   {d.touched} axes shifted")
        lines.append(f"prompt: {d.prompt}")
        for lbl, u, a in [("genre", d.genre_from, d.genre_to),
                          ("shape", d.shape_from, d.shape_to),
                          ("preset", d.preset_from, d.preset_to),
                          ("route", d.route_from, d.route_to)]:
            mark = "  " if u.lower() == a.lower() else "* "
            lines.append(f"  {mark}{lbl:8}  {u!r}  ->  {a!r}")
        if d.opts_added or d.opts_dropped:
            lines.append(f"  * options  added={d.opts_added or '-'}  "
                         f"dropped={d.opts_dropped or '-'}")
        else:
            lines.append(f"    options  identical set")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--show", type=int, default=0,
                    help="print up to N example scenes per top transition")
    ap.add_argument("--top", type=int, default=15, help="how many transitions to show")
    ap.add_argument("--scenes", default="", help="comma-separated scene ids to detail")
    ap.add_argument("--md", type=pathlib.Path, help="write a Markdown report to this path")
    args = ap.parse_args()

    diffs = load_diffs()
    sections: list[str] = []
    sections.append("# Config shift analysis")
    sections.append("")
    sections.append("Diff between the upstream skill's first-pass config (prompt only)")
    sections.append("and the answered config (prompt + author-answered clarifications).")
    sections.append("")
    sections.append("## Summary")
    sections += summary(diffs)
    for key in ("genre", "shape", "preset", "route"):
        sections.append("")
        sections.append(f"## {key.title()} shifts")
        sections += transitions(diffs, key, top=args.top)
        if args.show:
            sections += examples(diffs, key, top=min(6, args.top), per=args.show)

    if args.scenes:
        want = {s.strip() for s in args.scenes.split(",") if s.strip()}
        sections.append("")
        sections.append("## Requested scenes")
        sections += scene_details(diffs, want)

    text = "\n".join(sections)
    print(text)

    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(text + "\n", encoding="utf-8")
        print(f"\n[markdown report saved to {args.md}]")


if __name__ == "__main__":
    main()
