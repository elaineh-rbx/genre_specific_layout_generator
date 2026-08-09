"""Print evaluated rows from the merged CSV for human review.

    python tools/eval_show.py                 # all evaluated rows
    python tools/eval_show.py --verdict disagree
"""

from __future__ import annotations

import argparse
import csv
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "data" / "golden set 600 - genre and coverage eval.csv"


def wrap(label: str, text: str, width: int = 96) -> str:
    if not text:
        return ""
    body = textwrap.fill(text, width=width, initial_indent="      ", subsequent_indent="      ")
    return f"    {label}:\n{body}\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(DEFAULT))
    ap.add_argument("--verdict", default="", help="agree | defensible | disagree")
    ap.add_argument("--prompt-chars", type=int, default=260)
    args = ap.parse_args()

    with open(args.csv, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["eval_status"] == "evaluated"]
    if args.verdict:
        rows = [r for r in rows if r["eval_genre_verdict"] == args.verdict]

    order = {"disagree": 0, "defensible": 1, "agree": 2}
    rows.sort(key=lambda r: (order.get(r["eval_genre_verdict"], 3), r["eval_our_genre"]))

    for i, r in enumerate(rows, 1):
        print("=" * 100)
        print(f"[{i}] {r['eval_genre_verdict'].upper()}   CSV: {r['aligned_game_genre']}"
              f" / {r['inferred_game_subgenre']}   OURS: {r['eval_our_genres_all'] or r['eval_our_genre']}")
        if r["eval_verdict_note"]:
            print(f"    why: {r['eval_verdict_note']}")
        print()
        print(wrap("prompt", r["initial_prompt"][: args.prompt_chars].replace("\n", " ")), end="")
        print(f"    shape={r['eval_shape'] or '-'}  preset={r['eval_preset'] or '-'}"
              f"  pipeline={r['eval_pipeline']}  scale={r['eval_scale_band']}"
              f"  theme={r['eval_theme'] or 'null'}")
        print(f"    coverage={r['eval_coverage_verdict']}"
              f"  questions={r['eval_question_count']}"
              f"  unmatched={r['eval_unmatched_count']}")
        print()
        print(wrap("would ask", r["eval_questions"]), end="")
        print(wrap("no option covered", r["eval_unmatched_options"]), end="")
        print(wrap("belongs to another consumer", r.get("eval_off_pipeline_asks", "")), end="")
        print(wrap("GENRE GAP", r["eval_genre_gap"]), end="")
        print(wrap("SKILL GAP", r["eval_skill_gap"]), end="")
    print("=" * 100)
    print(f"{len(rows)} rows shown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
