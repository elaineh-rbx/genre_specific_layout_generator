"""What did intake ask users, and about what?

Every record carries the questions the worker would have asked but could not,
in two places: `handoff.open_questions` (the ones intake would raise before the
forward pass) and `coverage.missing` (asks the option tables could not express).
Both are `{field, ask}`.

This summarises them and writes a compact browsable extract.

    python evaluation/tools/eval_questions.py                    # counts by field
    python evaluation/tools/eval_questions.py --pre              # ...pre-pass only
    python evaluation/tools/eval_questions.py --pre --show goal  # prompt + question pairs
    python evaluation/tools/eval_questions.py --pre --show all   # every pair, 1494 of them
    python evaluation/tools/eval_questions.py --dump             # write questions.json
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CSV_PATH = DATA / "golden set 600 - genre and coverage eval.csv"
RECORDS = DATA / "records"
OUT = DATA / "questions.json"

PROMPT_CAP = 700


def csv_rows():
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            row["item_id"] = f"P{i:04d}"
            yield row


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
            iid = rec.get("item_id")
            if iid and not str(iid).endswith("b"):
                out[iid] = rec
    return out


def clean(text, cap=PROMPT_CAP):
    text = re.sub(r"\s+", " ", (text or "").replace("\\n", " ")).strip()
    return text[:cap] + ("..." if len(text) > cap else "")


def collect():
    recs = load_records()
    prompts = {r["item_id"]: r for r in csv_rows()}
    rows = []
    for iid, rec in sorted(recs.items()):
        gc = ((rec.get("handoff") or {}).get("genre_choice")) or {}
        cov = rec.get("coverage") or {}
        asks = []
        seen = set()
        for src, items in (("before forward pass", (rec.get("handoff") or {}).get("open_questions") or []),
                           ("gap in the tables", cov.get("missing") or [])):
            for q in items:
                if not isinstance(q, dict):
                    continue
                text = clean(q.get("ask"), 240)
                if not text or text.lower() in seen:
                    continue
                seen.add(text.lower())
                asks.append({"field": (q.get("field") or "unknown").lower(),
                             "ask": text, "source": src})
        if not asks:
            continue
        meta = prompts.get(iid, {})
        rows.append({
            "id": iid,
            "prompt": clean(meta.get("initial_prompt")),
            "genres": gc.get("genres") or [],
            "shape": (gc.get("shape") or {}).get("id"),
            "preset": gc.get("preset"),
            "pipeline": gc.get("pipeline") or [],
            "asks": asks,
        })
    return rows, len(recs)


def main():
    rows, total = collect()
    # `--pre` keeps only the questions intake would put to the user before the
    # forward pass, dropping `coverage.missing` - which records what the option
    # tables could not express and is not necessarily a question at all.
    if "--pre" in sys.argv:
        for r in rows:
            r["asks"] = [a for a in r["asks"] if a["source"] == "before forward pass"]
        rows = [r for r in rows if r["asks"]]

    if "--show" in sys.argv:
        want = sys.argv[sys.argv.index("--show") + 1].lower()
        hits = [(r, a) for r in rows for a in r["asks"]
                if want == "all" or a["field"] == want]
        print(f"{want}: {len(hits)} question(s) across {len({r['id'] for r, _ in hits})} prompts\n")
        for r, a in hits:
            print(f"{r['id']}  {'+'.join(r['genres'])}  {r['shape']}  {'+'.join(r['pipeline'])}")
            print(f"   PROMPT  {r['prompt'][:260]}")
            print(f"   ASK     [{a['field']}] {a['ask']}\n")
        return

    fields = Counter(a["field"] for r in rows for a in r["asks"])
    per_row = Counter(len(r["asks"]) for r in rows)
    n_asks = sum(len(r["asks"]) for r in rows)

    print(f"rows scored: {total}")
    print(f"rows that raised at least one question: {len(rows)}  ({len(rows)/total:.0%})")
    print(f"total questions: {n_asks}   mean per asking row: {n_asks/len(rows):.1f}\n")
    print("by field:")
    for field, c in fields.most_common():
        print(f"  {c:>4}  {field}")
    print("\nquestions per row:")
    for k in sorted(per_row):
        print(f"  {k}: {per_row[k]}")

    if "--dump" in sys.argv:
        OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        kb = OUT.stat().st_size / 1024
        print(f"\nwrote {OUT.relative_to(ROOT.parent)}  ({len(rows)} rows, {kb:.0f} KB)")


if __name__ == "__main__":
    main()
