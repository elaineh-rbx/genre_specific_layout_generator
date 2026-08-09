"""Two questions the mixed-genre discussion raised.

1. The grader rewards the *dominant* genre. If a correctly-identified genre was
   ranked second it scored "defensible", not "agree". How many rows is that?
2. "clicker" appears nowhere in the genre index, and its only mention anywhere
   in the skill is the P5 list of concepts with no space. Where did clicker
   prompts actually land?
"""
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "golden set 600 - genre and coverage eval.csv"
RECORDS = ROOT / "data" / "records"

# Same coarse-label mapping the harness uses.
COARSE = {
    "obby_and_platformer": {"obby-platformer", "infinite-runner"},
    "sports_and_racing": {"sports", "racing"},
    "roleplay_and_avatar_sim": {"roleplay-avatar-sim"},
    "party_and_casual": {"party-casual"},
    "other_entertainment": {"entertainment"},
}


def expected(label):
    label = (label or "").strip().lower()
    if label in COARSE:
        return COARSE[label]
    return {label.replace("_", "-")}


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
    promoted = []
    clicker = []
    verdicts = Counter()

    with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            item = f"P{i:04d}"
            rec = recs.get(item)
            if not rec or row.get("eval_status") != "evaluated":
                continue
            gc = ((rec.get("handoff") or {}).get("genre_choice")) or {}
            ours = gc.get("genres") or []
            verdict = row.get("eval_genre_verdict") or ""
            verdicts[verdict] += 1
            want = expected(row.get("aligned_game_genre"))

            # Correct genre present but not ranked first.
            if verdict != "agree" and len(ours) > 1 and set(ours[1:]) & want:
                promoted.append((item, ours, row.get("aligned_game_genre"), verdict))

            prompt = row.get("initial_prompt") or ""
            if re.search(r"\bclicker\b", prompt, re.I):
                pipeline = gc.get("pipeline") or []
                clicker.append((item, ours or ["(none)"], "+".join(pipeline),
                                " ".join(prompt.split())[:110]))

    print("=== published verdicts ===")
    for k, v in verdicts.most_common():
        print(f"  {v:>4}  {k}")

    print(f"\n=== correct genre present but ranked second: {len(promoted)} rows ===")
    for item, ours, label, verdict in promoted:
        print(f"  {item}  ours={'+'.join(ours):<38} csv={label:<24} scored={verdict}")

    agree = verdicts.get("agree", 0)
    print(f"\n  agree as published            : {agree}")
    print(f"  agree if order is not scored  : {agree + len(promoted)}")

    print(f"\n=== prompts containing 'clicker': {len(clicker)} ===")
    print("  ('clicker' is absent from the genre index; its only mention in the")
    print("   skill is the P5 list of concepts with no space.)")
    for item, ours, pipeline, text in clicker:
        print(f"  {item}  ours={'+'.join(ours):<24} route={pipeline}")
        print(f"        {text}")


if __name__ == "__main__":
    main()
