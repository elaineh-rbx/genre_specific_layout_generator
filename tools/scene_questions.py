"""Show the intake questions that would be asked back for a scene.

The upstream handoff carries two related question lists per prompt, both stored
inside `results/routing/skill/<scene>.json` next to the picks:

    open_questions      the crisp asks the intake would forward to the user
                        before building - mean ~2.5 per scene, fields are
                        mostly scale/theme/goal/shape
    coverage_missing    the wider audit note of things the handoff had no
                        field for - mean ~3.5 per scene; a superset of the
                        above with the loose ends the skill couldn't route

Usage:
    python tools/scene_questions.py                       # summary of all scenes
    python tools/scene_questions.py P0002                 # one scene, both lists
    python tools/scene_questions.py P0002 P0214 P0620     # several
    python tools/scene_questions.py --field theme         # every theme question
    python tools/scene_questions.py --field shape --limit 20
    python tools/scene_questions.py --out results/questions.jsonl   # dump one row per scene
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen.paths import ROUTING

SKILL = ROUTING / "skill"


def load_all() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(SKILL.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows.append({
            "scene": raw.get("scene") or path.stem,
            "source": raw.get("source", ""),
            "genre": (raw.get("block") or {}).get("genres") or [],
            "theme": raw.get("theme") or "",
            "scale": raw.get("scale") or {},
            "open_questions": raw.get("open_questions") or [],
            "coverage_missing": raw.get("coverage_missing") or [],
        })
    return rows


def one_scene(row: dict) -> None:
    print(f"\n{'='*72}\n{row['scene']}   genre={row['genre'] or ['-']}"
          f"   scale={row['scale'].get('band') or '-'}"
          + (f"   assumed" if row['scale'].get('assumed') else ""))
    if row['theme']:
        print(f"theme: {row['theme']}")
    if row['source']:
        preview = row['source'].replace("\n", " ")[:160]
        print(f"prompt: {preview}{'…' if len(row['source'])>160 else ''}")
    print(f"\nopen_questions ({len(row['open_questions'])}) - what intake would ask back:")
    for q in row['open_questions']:
        print(f"  [{q.get('field','?')}] {q.get('ask','')}")
    cm = row['coverage_missing']
    only_in_cm = [q for q in cm
                  if not any((q.get('field') == oq.get('field')
                              and q.get('ask') == oq.get('ask'))
                             for oq in row['open_questions'])]
    if only_in_cm:
        print(f"\ncoverage_missing extras ({len(only_in_cm)}) - audit-only, not sent as asks:")
        for q in only_in_cm:
            print(f"  [{q.get('field','?')}] {q.get('ask','')}")


def summary(rows: list[dict]) -> None:
    print(f"{len(rows)} scenes on disk in {SKILL}")
    fields = Counter()
    total_q = 0
    zero = 0
    for r in rows:
        if not r['open_questions']:
            zero += 1
        for q in r['open_questions']:
            fields[q.get('field','?')] += 1
            total_q += 1
    print(f"open_questions: {total_q} total, {total_q/max(len(rows),1):.1f} per scene"
          f", {zero} scenes with zero")
    print("top question fields:")
    for k, v in fields.most_common(12):
        print(f"  {v:5}  {k}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scenes", nargs="*", help="scene ids like P0002, or 0025")
    ap.add_argument("--field", help="filter to one question field (scale, theme, shape, goal, …)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--include-missing", action="store_true",
                    help="when using --field, also include entries from coverage_missing")
    ap.add_argument("--out", type=pathlib.Path,
                    help="write one JSONL row per scene with scene/questions/theme/scale")
    args = ap.parse_args()

    rows = load_all()

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps({
                    "scene": r['scene'],
                    "theme": r['theme'],
                    "scale": r['scale'],
                    "open_questions": r['open_questions'],
                    "coverage_missing": r['coverage_missing'],
                }, ensure_ascii=False) + "\n")
        print(f"wrote {len(rows)} rows to {args.out}")
        return

    if args.field:
        printed = 0
        for r in rows:
            hits = [(r['scene'], q) for q in r['open_questions']
                    if q.get('field') == args.field]
            if args.include_missing:
                hits += [(r['scene'], q) for q in r['coverage_missing']
                         if q.get('field') == args.field
                         and not any(q.get('ask') == oq.get('ask') for oq in r['open_questions'])]
            for scene, q in hits:
                print(f"{scene}  [{q.get('field')}] {q.get('ask')}")
                printed += 1
                if args.limit and printed >= args.limit:
                    return
        return

    if not args.scenes:
        summary(rows)
        return

    wanted = set(args.scenes)
    for r in rows:
        if r['scene'] in wanted:
            one_scene(r)


if __name__ == "__main__":
    main()
