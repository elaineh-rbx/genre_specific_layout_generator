"""Print the classification and prompt for specific item_ids.

For checking a claim about particular rows without re-reading a whole record
file by hand: `python tools/eval_peek.py P0398 P0410 P0536`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_golden_set as E  # noqa: E402


def find(rows: dict, pattern: str) -> list[str]:
    """item_ids whose prompt matches a regex, for checking a claim about a family."""
    rx = re.compile(pattern, re.I)
    return [iid for iid, r in rows.items() if rx.search(r.get("initial_prompt", ""))]


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    rows = {E.item_id(r): r for r in E.load_rows()}
    recs = {r["item_id"]: r for r in E.load_records(sorted(E.RECORD_DIR.glob(E.RECORD_GLOB)))}
    if argv[0] == "--find":
        argv = find(rows, argv[1])
        print(f"{len(argv)} matching prompts\n")
    for iid in argv:
        rec = recs.get(iid)
        if not rec:
            print(f"{iid}: no record")
            continue
        gc = rec["handoff"]["genre_choice"]
        # A calibration duplicate carries the source row of the prompt it copies.
        src = rows.get(iid[:-1] if iid.endswith("b") else iid) or {}
        shape = (gc.get("shape") or {}).get("id")
        print(f"{iid:8} genres={gc.get('genres')} shape={shape} preset={gc.get('preset')}")
        print(f"         csv_label={src.get('aligned_game_genre', '?')}")
        print(f"         prompt: {' '.join(src.get('initial_prompt', '').split())[:180]}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
