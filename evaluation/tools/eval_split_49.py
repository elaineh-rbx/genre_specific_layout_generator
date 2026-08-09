"""Resolve the batch-49 / batch-49r collision without moving published numbers.

The aggregate was built from batch-49's first two records (P0069, P0316 — all
the stalled lane had produced) plus batch-49r's eight. The original lane later
finished and rewrote batch-49.jsonl with all ten, so eight records now exist
twice under the same item_ids.

Rather than let the merge's tie-break silently decide which scoring backs a
published number, this preserves the lane's full output outside the record
glob and leaves batch-49.jsonl holding exactly the two records the aggregate
always used. Nothing is deleted.
"""
import json
import shutil
from pathlib import Path

RECORD_DIR = Path(__file__).resolve().parent.parent / "data" / "records"
SRC = RECORD_DIR / "batch-49.jsonl"
FULL = RECORD_DIR / "late-batch-49-full.jsonl"
KEEP = {"P0069", "P0316"}


def main():
    records = []
    for line in open(SRC, encoding="utf-8-sig"):
        line = line.strip().lstrip("\ufeff")
        if not line or line.startswith("```"):
            continue
        records.append(json.loads(line))
    print(f"read {len(records)} records from {SRC}")

    shutil.copyfile(SRC, FULL)
    print(f"preserved full lane output -> {FULL} (outside batch-*.jsonl glob)")

    kept = [r for r in records if r.get("item_id") in KEEP]
    if len(kept) != len(KEEP):
        raise SystemExit(f"expected {sorted(KEEP)}, found {[r.get('item_id') for r in kept]}")

    with open(SRC, "w", encoding="utf-8", newline="\n") as fh:
        for rec in kept:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"rewrote {SRC} with {len(kept)} records: {sorted(r['item_id'] for r in kept)}")


if __name__ == "__main__":
    main()
