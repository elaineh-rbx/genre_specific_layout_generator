"""Cross the spreadsheet's own `inferred_game_dimension` against our P5 routing.

P5 means "no traversable space, don't build". If a prompt is already marked
non-3D upstream, it arguably should never have reached a 3D layout skill at all
— that is a filtering question, not a routing one. This separates the two.
"""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "golden set 600 - genre and coverage eval.csv"
RECORDS = ROOT / "data" / "records"

P5_SUBGENRES = {
    "idle", "incremental_simulator", "music_audio",
    "match_merge", "word", "board_card_games",
}


def load_records():
    out = {}
    for path in sorted(RECORDS.glob("batch-*.jsonl")):
        for line in open(path, encoding="utf-8-sig"):
            line = line.strip().lstrip("\ufeff")
            if not line or line.startswith("```"):
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            out[rec.get("item_id")] = rec
    return out


def main():
    recs = load_records()
    dims = Counter()
    p5_by_dim = Counter()
    cand_dims = Counter()
    non3d_rows = []

    with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            item = f"P{i:04d}"
            rec = recs.get(item)
            if not rec:
                continue
            dim = (row.get("inferred_game_dimension") or "").strip() or "(blank)"
            sub = (row.get("inferred_game_subgenre") or "").strip()
            gc = ((rec.get("handoff") or {}).get("genre_choice")) or {}
            routed_p5 = "P5" in (gc.get("pipeline") or [])
            dims[dim] += 1
            if routed_p5:
                p5_by_dim[dim] += 1
            if sub in P5_SUBGENRES:
                cand_dims[dim] += 1
            if dim.lower() not in ("3d", "(blank)"):
                non3d_rows.append((item, dim, sub, routed_p5,
                                   " ".join((row.get("initial_prompt") or "").split())[:130]))

    print("=== spreadsheet's inferred_game_dimension, all evaluated rows ===")
    for d, n in dims.most_common():
        print(f"  {n:>4}  {d}   (we routed P5 on {p5_by_dim[d]})")

    print()
    print("=== dimension of the 23 P5-candidate-subgenre prompts ===")
    for d, n in cand_dims.most_common():
        print(f"  {n:>4}  {d}")

    print()
    print(f"=== rows the spreadsheet did NOT call 3D: {len(non3d_rows)} ===")
    for item, dim, sub, p5, text in non3d_rows:
        print(f"  {item}  dim={dim:<6} sub={sub:<22} ourP5={p5}")
        print(f"        {text}")


if __name__ == "__main__":
    main()
