"""Show every row we actually routed P5, with its prompt."""
import csv
import json
import textwrap
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
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            item = f"P{i:04d}"
            rec = recs.get(item)
            if not rec:
                continue
            gc = ((rec.get("handoff") or {}).get("genre_choice")) or {}
            if "P5" not in (gc.get("pipeline") or []):
                continue
            print(f"=== {item}  line {i} ===")
            print(f"  spreadsheet: genre={row.get('aligned_game_genre')} "
                  f"sub={row.get('inferred_game_subgenre')} "
                  f"dim={row.get('inferred_game_dimension')}")
            print(f"  ours: genres={gc.get('genres')} shape={gc.get('shape')}")
            for n in (gc.get("notes") or [])[:3]:
                print(textwrap.fill(f"  note: {n}", 100,
                                    subsequent_indent="        "))
            text = " ".join((row.get("initial_prompt") or "").split())
            print(textwrap.fill(text[:600], 100, initial_indent="  ",
                                subsequent_indent="  "))
            print()


if __name__ == "__main__":
    main()
