"""Cases for the three-way genre verdict. Run: python tools/test_eval_grade.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_golden_set import grade

CASES = [
    # (csv_label, our_genres_dominant_first, pipeline, expected_verdict)
    ("obby_and_platformer", ["obby-platformer"], ["P6"], "agree"),
    # Roblox files Runner under Obby, so our split still agrees with the bucket.
    ("obby_and_platformer", ["infinite-runner"], ["P6"], "agree"),
    ("sports_and_racing", ["racing"], ["P0"], "agree"),
    ("sports_and_racing", ["sports"], ["P0"], "agree"),
    ("sports_and_racing", ["simulation"], ["P0"], "disagree"),
    ("simulation", ["simulation"], ["P0"], "agree"),
    # The CSV label is one of ours, just not the one we called dominant.
    ("simulation", ["roleplay-avatar-sim", "simulation"], ["P0"], "defensible"),
    ("simulation", ["shooter"], ["P0"], "disagree"),
    ("unknown", ["shooter"], ["P0"], "defensible"),
    ("", ["shooter"], ["P0"], "defensible"),
    ("avatar_shopping", ["roleplay-avatar-sim"], ["P0"], "defensible"),
    ("social", ["entertainment"], ["P0"], "defensible"),
    # Outcomes the CSV taxonomy cannot express at all.
    ("simulation", [], ["P5"], "defensible"),
    ("simulation", [], ["P0"], "defensible"),
    ("other_entertainment", ["entertainment"], ["P0"], "agree"),
]


def main() -> int:
    failures = 0
    for label, ours, pipeline, want in CASES:
        got, note = grade(label, ours, pipeline)
        status = "OK  " if got == want else "FAIL"
        if got != want:
            failures += 1
        shown_label = label or "(blank)"
        shown_ours = ours or "[]"
        suffix = f"   {note}" if note else ""
        print(f"{status} {shown_label:22} {str(shown_ours):42} {pipeline} -> {got}{suffix}")
    print(f"\n{len(CASES)} cases, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
