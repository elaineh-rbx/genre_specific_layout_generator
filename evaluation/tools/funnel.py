#!/usr/bin/env python3
"""The four intake stages, counted the same way for every run.

Run 2 was reported at 95% on genre and then shipped 22% unusable handoffs,
because the first three stages were measured and the fourth was not. This
counts all four from the records, so the comparison between runs is one
definition rather than three analyses.

    python evaluation/tools/funnel.py data/run-2/records data/run-3/records
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_records_wellformed import check  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIDELITY = re.compile(
    r"hyper.?real|photo.?real|ultra.?real|realistic|many details|highly detailed",
    re.I)


def load(folder: Path) -> list[dict]:
    out = []
    for path in sorted(folder.glob("batch-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def report(folder: Path) -> None:
    records = load(folder)
    if not records:
        print(f"{folder}: no records")
        return
    n = len(records)

    genre = shape = preset = usable = 0
    fidelity_in_theme = segs = cons = 0
    for r in records:
        gc = (r.get("handoff") or {}).get("genre_choice") or {}
        genre += bool(gc.get("genres")) and not (r.get("gaps") or {}).get("genre_gap")
        shape += bool((gc.get("shape") or {}).get("id"))
        preset += bool(gc.get("preset"))
        usable += not check(r)

        if FIDELITY.search(str((r.get("handoff") or {}).get("theme") or "")):
            fidelity_in_theme += 1
        segs += bool(gc.get("segments"))
        cons += bool((r.get("handoff") or {}).get("constraints"))

    print(f"\n{folder.name if folder.name != 'records' else folder.parent.name}"
          f"  ({n} records)")
    for label, passed in (("Classify the genre", genre),
                          ("Choose a shape", shape),
                          ("Suggest a preset", preset),
                          ("Emit a usable handoff", usable)):
        bar = "#" * round(passed / n * 40)
        print(f"  {label:<24} {passed:>4} / {n}  {passed/n:>5.0%}  {bar}")
    print(f"  {'-' * 62}")
    print(f"  fidelity wedged into `theme`  {fidelity_in_theme:>4}")
    print(f"  emitted `segments`            {segs:>4}")
    print(f"  emitted `constraints`         {cons:>4}")


def main() -> int:
    folders = [Path(a) if Path(a).is_absolute() else ROOT / a
               for a in (sys.argv[1:] or ["data/run-2/records",
                                          "data/run-3/records"])]
    for folder in folders:
        report(folder)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
