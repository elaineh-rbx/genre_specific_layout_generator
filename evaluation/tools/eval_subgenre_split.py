"""Check our genre assignment against the spreadsheet's own subgenre grouping.

The family sweep was a judgement call: a reader decided that some set of
prompts is "the same kind of game". The spreadsheet already carries an
independent answer in `inferred_game_subgenre`, assigned before we saw any of
this, and the golden set was deliberately balanced across those subgenres.

So for each subgenre we can ask an objective version of the same question: of
the prompts the spreadsheet considers one kind of game, how many genres did we
send them to? That corroborates or refutes a claimed family without anyone's
opinion entering into it.

    python tools/eval_subgenre_split.py
    python tools/eval_subgenre_split.py --min-rows 6
"""

from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_golden_set as E  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-rows", type=int, default=5)
    ap.add_argument("--limit", type=int, default=30)
    args = ap.parse_args()

    rows = {E.item_id(r): r for r in E.load_rows()}
    recs = {r["item_id"]: r
            for r in E.load_records(sorted(E.RECORD_DIR.glob(E.RECORD_GLOB)))}

    by_sub: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for iid, rec in recs.items():
        if iid.endswith("b"):  # calibration copies would double-count
            continue
        row = rows.get(iid)
        if not row:
            continue
        sub = (row.get("inferred_game_subgenre") or "").strip()
        if not sub:
            continue
        genres = rec["handoff"]["genre_choice"].get("genres") or ["(no genre)"]
        by_sub[sub].append((iid, genres[0]))

    report = []
    for sub, members in by_sub.items():
        if len(members) < args.min_rows:
            continue
        spread = collections.Counter(g for _, g in members)
        top_share = spread.most_common(1)[0][1] / len(members)
        report.append((sub, members, spread, top_share))

    # Lowest concentration first: those are the subgenres we split hardest.
    report.sort(key=lambda x: x[3])
    total = sum(len(m) for _, m, _, _ in report)
    print(f"{len(report)} subgenres with {args.min_rows}+ prompts, {total} prompts\n")
    print(f"{'subgenre':34} {'n':>3} {'genres':>6} {'largest':>8}  spread")
    for sub, members, spread, top_share in report[:args.limit]:
        pretty = ", ".join(f"{g}x{n}" if n > 1 else g for g, n in spread.most_common(5))
        print(f"{sub[:34]:34} {len(members):3} {len(spread):6} {top_share:7.0%}  {pretty}")

    if report:
        mean = sum(t for _, _, _, t in report) / len(report)
        print(f"\nmean concentration: {mean:.0%} of a subgenre's prompts share our top genre")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
