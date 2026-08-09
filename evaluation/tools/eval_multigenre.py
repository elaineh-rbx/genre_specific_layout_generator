"""How often did we assign more than one genre, and did the grader reward it?

The handoff schema has always allowed `genres` to be a list. This measures
whether that capability was actually used, and what the grader did with it.
"""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "golden set 600 - genre and coverage eval.csv"
RECORDS = ROOT / "data" / "records"


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
    counts = Counter()
    verdict_by_n = {}
    pairs = Counter()
    multi_rows = []

    with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            item = f"P{i:04d}"
            rec = recs.get(item)
            if not rec:
                continue
            if row.get("eval_status") != "evaluated":
                continue
            gc = ((rec.get("handoff") or {}).get("genre_choice")) or {}
            genres = gc.get("genres") or []
            n = len(genres)
            counts[n] += 1
            verdict = row.get("eval_genre_verdict") or "(none)"
            verdict_by_n.setdefault(n, Counter())[verdict] += 1
            if n >= 2:
                pairs["+".join(genres[:2])] += 1
                multi_rows.append((item, genres, row.get("aligned_game_genre"), verdict))

    total = sum(counts.values())
    print(f"evaluated rows: {total}\n")
    print("=== how many genres we assigned ===")
    for n in sorted(counts):
        share = counts[n] / total
        print(f"  {n} genre(s): {counts[n]:>4}  ({share:.0%})")

    print("\n=== verdict, split by how many genres we gave ===")
    for n in sorted(verdict_by_n):
        row = verdict_by_n[n]
        tot = sum(row.values())
        parts = "  ".join(f"{k}={v}" for k, v in row.most_common())
        print(f"  {n} genre(s) (n={tot}): {parts}")

    print("\n=== most common genre pairs ===")
    for pair, n in pairs.most_common(15):
        print(f"  {n:>3}  {pair}")

    # Did a secondary genre ever rescue a row the primary would have lost?
    rescued = [r for r in multi_rows if r[3] == "defensible"]
    print(f"\n=== multi-genre rows graded 'defensible': {len(rescued)} ===")
    for item, genres, csv_label, _ in rescued[:20]:
        print(f"  {item}  ours={'+'.join(genres)}   csv={csv_label}")


if __name__ == "__main__":
    main()
