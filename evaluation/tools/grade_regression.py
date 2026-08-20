#!/usr/bin/env python3
"""Grade the run-3 regression batch against the run-2 failure it reproduces.

Every prompt in this batch failed run 2 in a known, specific way. A fix that
lands in the skill files but does not change what a lane emits has not landed,
so each row is graded against its own defect rather than against a general
notion of quality.

    python evaluation/tools/grade_regression.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RECORDS = Path(__file__).resolve().parents[1] / "data/run-3/regression"

# item_id -> (what run 2 got wrong, which check has to pass now)
CASES: dict[str, tuple[str, str]] = {
    "P0341": ("layout entry `spawner-npc` had no type", "typed"),
    "P0149": ("layout entry `spawner-npc` had no type", "typed"),
    "P0251": ("untyped entry, and a rejected option priced the route", "typed"),
    "P0286": ("untyped entry, and the sky platforms were dropped", "typed+kept"),
    "P0235": ("house lots sat untyped in layout_placement", "typed"),
    "P0118": ("interaction triggers sat untyped in layout_placement", "typed"),
    "P0062": ("training dummy sat untyped in layout_placement", "typed"),
    "P0443": ("inspect point sat untyped in layout_placement", "typed"),
    "P0288": ("the holding cell reached nothing in the handoff", "kept"),
    "P0218": ("role spawn points reached nothing in the handoff", "kept"),
    "P0034": ("the rooftop route reached nothing in the handoff", "kept"),
    "P0554": ("the speed effect reached nothing in the handoff", "kept"),
    "P0256": ("two venues flattened into one shape", "segments"),
    "P0100": ("graded zones flattened into one shape", "segments"),
    "P0308": ("seasons and starting farms flattened", "segments"),
    "P0214": ("'hyper realistic' was filed as theme", "constraints"),
    "P0451": ("'many details' was forced onto an option", "constraints"),
    "P0349": ("a build rule was dropped", "constraints"),
    "P0194": ("realism was filed as theme", "constraints"),
    "P0192": ("questions were asked despite the prompt refusing", "noquestions"),
    "P0422": ("questions were asked despite the prompt refusing", "noquestions"),
    "P0189": ("questions were asked despite the prompt refusing", "noquestions"),
}

FIDELITY = re.compile(
    r"hyper.?real|photo.?real|ultra.?real|realistic|many details|highly detailed",
    re.I)


def words(text: object) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", str(text).lower()) if len(w) > 3}


def grade(rec: dict) -> tuple[bool, str]:
    gc = (rec.get("handoff") or {}).get("genre_choice") or {}
    check = CASES[rec["item_id"]][1]

    if "typed" in check:
        bad = [e for e in (gc.get("layout_placement") or []) if not e.get("type")]
        if bad:
            return False, f"{len(bad)} layout entr{'y' if len(bad)==1 else 'ies'} still untyped"

    if "kept" in check:
        body = words(" ".join(
            [str(e.get("text", "")) for e in (gc.get("image_prompt") or [])]
            + [str(e.get("text", "")) for e in (gc.get("layout_placement") or [])]
            + [str(n) for n in (gc.get("notes") or [])]))
        for g in ((rec.get("gaps") or {}).get("unmatched_options") or []):
            if str(g.get("destination") or "").lower() not in ("image", "layout"):
                continue
            t = words(g.get("canonical")) | words(g.get("text"))
            if t and not (t & body):
                return False, f"still loses {str(g.get('canonical'))!r}"

    if check == "segments":
        segs = gc.get("segments") or []
        if len(segs) < 2:
            return False, "no `segments` — the extra spaces are still gone"
        if any(not (s.get("shape") or {}).get("id") and not s.get("name") for s in segs):
            return False, "a segment carries neither a name nor a shape"

    if check == "constraints":
        cons = (rec.get("handoff") or {}).get("constraints") or []
        if not cons:
            return False, "no `constraints` — the build-wide rule is still homeless"
        theme = str((rec.get("handoff") or {}).get("theme") or "")
        if FIDELITY.search(theme):
            return False, f"fidelity is still inside `theme`: {theme[:45]!r}"

    if check == "noquestions":
        # Only `open_questions` counts. The brief tells every lane to write the
        # questions it would have put to a user into `coverage.missing` and
        # calls that list a deliverable, so entries there are the harness
        # working, not the prompt's refusal being ignored.
        qs = (rec.get("handoff") or {}).get("open_questions") or []
        if qs:
            return False, f"still emitted {len(qs)} open_questions"
        scale = (rec.get("handoff") or {}).get("scale") or {}
        if not scale.get("assumed"):
            return False, "took a default without flagging it `assumed`"

    return True, "fixed"


def main() -> int:
    records = {}
    for path in sorted(RECORDS.glob("batch-r*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    print(f"  unparseable line in {path.name}")
                    continue
                records[r.get("item_id")] = r

    passed = failed = 0
    missing = []
    for item, (was, _) in CASES.items():
        rec = records.get(item)
        if rec is None:
            missing.append(item)
            continue
        ok, detail = grade(rec)
        mark = "PASS" if ok else "FAIL"
        passed += ok
        failed += not ok
        print(f"  [{mark}] {item}  run 2: {was}")
        if not ok:
            print(f"         now: {detail}")

    print()
    print(f"{passed} fixed, {failed} still failing"
          + (f", {len(missing)} not yet recorded {missing}" if missing else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
