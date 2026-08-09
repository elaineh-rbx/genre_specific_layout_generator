"""Pull the specific rows behind three questions, so they can be checked by hand.

    python evaluation/tools/eval_answer.py losses      # the 8 the spreadsheet won
    python evaluation/tools/eval_answer.py subgenre open_world_action
    python evaluation/tools/eval_answer.py p5          # P5-candidate subgenres
"""
import csv
import json
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CSV_PATH = DATA / "golden set 600 - genre and coverage eval.csv"
RECORDS = DATA / "records"

P5_SUBGENRES = {
    "idle",
    "incremental_simulator",
    "music_audio",
    "match_merge",
    "word",
    "board_card_games",
}


def rows():
    """item_id is derived from the spreadsheet line: P0043 is line 43."""
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            row["_csv_line"] = i
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
            out[rec.get("item_id")] = rec
    return out


def load_adjudication():
    verdicts = {}
    for path in sorted(RECORDS.glob("adjudication-*.jsonl")):
        for line in open(path, encoding="utf-8-sig"):
            line = line.strip().lstrip("\ufeff")
            if not line or line.startswith("```"):
                continue
            try:
                v = json.loads(line)
            except json.JSONDecodeError:
                continue
            verdicts[v.get("item_id")] = v
    return verdicts


def wrap(text, indent="      ", width=100):
    return textwrap.fill(" ".join((text or "").split()), width=width,
                         initial_indent=indent, subsequent_indent=indent)


def find_col(row, *names):
    for n in names:
        if n in row:
            return n
    return None


def cmd_losses():
    adj = load_adjudication()
    recs = load_records()
    by_id = {r.get("item_id"): r for r in rows() if r.get("item_id")}
    losses = [(k, v) for k, v in adj.items() if (v.get("better") or "").lower() == "spreadsheet"]
    print(f"{len(losses)} rows where the sighted reviewer preferred the spreadsheet\n")
    for item, v in sorted(losses):
        row = by_id.get(item, {})
        rec = recs.get(item, {})
        gc = ((rec.get("handoff") or {}).get("genre_choice")) or {}
        shape = gc.get("shape") or {}
        pcol = find_col(row, "initial_prompt", "prompt", "user_prompt")
        print(f"=== {item}   CSV line {row.get('_csv_line', '?')} ===")
        print(f"  spreadsheet : {row.get('aligned_game_genre', '?')}"
              f"   (subgenre {row.get('inferred_game_subgenre', '?')})")
        print(f"  ours        : {', '.join(gc.get('genres') or []) or '(none)'}"
              f"   shape {shape.get('id') if isinstance(shape, dict) else shape}"
              f"   pipeline {'+'.join(gc.get('pipeline') or [])}")
        print("  why the reviewer preferred the spreadsheet:")
        print(wrap(v.get("why", "")))
        print("  prompt:")
        print(wrap(row.get(pcol, "") if pcol else ""))
        print()


def cmd_subgenre(target):
    recs = load_records()
    hits = [r for r in rows() if (r.get("inferred_game_subgenre") or "").strip() == target]
    print(f"subgenre '{target}': {len(hits)} prompts\n")
    buckets = {}
    for row in hits:
        rec = recs.get(row.get("item_id"), {})
        gc = ((rec.get("handoff") or {}).get("genre_choice")) or {}
        genres = gc.get("genres") or []
        top = genres[0] if genres else "(no genre)"
        buckets.setdefault(top, []).append((row, gc))
    for top, items in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        print(f"--- our genre: {top}   ({len(items)} prompts) ---")
        for row, gc in items:
            shape = gc.get("shape") or {}
            pcol = find_col(row, "initial_prompt", "prompt", "user_prompt")
            text = " ".join((row.get(pcol) or "").split())
            print(f"  {row.get('item_id')}  line {row.get('_csv_line')}  "
                  f"shape={shape.get('id') if isinstance(shape, dict) else shape}")
            print(wrap(text[:300] + ("..." if len(text) > 300 else ""), indent="        "))
        print()


def cmd_p5():
    recs = load_records()
    hits = [r for r in rows()
            if (r.get("inferred_game_subgenre") or "").strip() in P5_SUBGENRES]
    print(f"{len(hits)} prompts from P5-candidate subgenres\n")
    for row in hits:
        rec = recs.get(row.get("item_id"), {})
        gc = ((rec.get("handoff") or {}).get("genre_choice")) or {}
        pipeline = gc.get("pipeline") or []
        shape = gc.get("shape") or {}
        pcol = find_col(row, "initial_prompt", "prompt", "user_prompt")
        text = " ".join((row.get(pcol) or "").split())
        flag = "P5" if "P5" in pipeline else "  "
        print(f"{flag} {row.get('item_id')}  line {row.get('_csv_line')}  "
              f"sub={row.get('inferred_game_subgenre')}  "
              f"ours={','.join(gc.get('genres') or []) or '(none)'}  "
              f"shape={shape.get('id') if isinstance(shape, dict) else shape}  "
              f"route={'+'.join(pipeline)}")
        print(wrap(text[:420] + ("..." if len(text) > 420 else "")))
        print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "losses":
        cmd_losses()
    elif cmd == "subgenre":
        cmd_subgenre(sys.argv[2] if len(sys.argv) > 2 else "open_world_action")
    elif cmd == "p5":
        cmd_p5()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
