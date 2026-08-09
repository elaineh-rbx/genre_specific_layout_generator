"""Compare the late-arriving batch-49 against its rescue file batch-49r.

The original batch-49 lane stalled at 2 of 10 records and a rescue lane was
launched for the missing 8. The original then finished hours later, so the two
files now overlap. Any prompt scored by both is an unplanned blind duplicate:
two lanes, same brief, same prompt, no contact. That is exactly the shape of
the calibration set, so the overlap is worth more as measurement than as a
merge conflict.
"""
import json
import sys
from pathlib import Path

RECORD_DIR = Path(__file__).resolve().parent.parent / "data" / "records"


def load(path):
    out = {}
    for n, line in enumerate(open(path, encoding="utf-8-sig"), 1):
        line = line.strip().lstrip("\ufeff")
        if not line or line.startswith("```"):
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"  {path}:{n} PARSE FAIL: {exc}")
            continue
        out[rec.get("item_id")] = rec
    return out


def summarize(rec):
    h = rec.get("handoff") or {}
    gc = h.get("genre_choice") or {}
    gaps = rec.get("gaps") or {}
    shape = gc.get("shape") or {}
    return {
        "genres": gc.get("genres") or [],
        "shape": shape.get("id") if isinstance(shape, dict) else shape,
        "preset": gc.get("preset"),
        "pipeline": gc.get("pipeline") or [],
        "verdict": (rec.get("coverage") or {}).get("verdict"),
        "asks": [
            (a.get("canonical") or "").strip()
            for a in (gaps.get("unmatched_options") or [])
            if isinstance(a, dict)
        ],
    }


def jaccard(a, b):
    sa, sb = {x for x in a if x}, {x for x in b if x}
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def main():
    orig = load(RECORD_DIR / "batch-49.jsonl")
    resc = load(RECORD_DIR / "batch-49r.jsonl")
    print(f"batch-49 : {len(orig)} records  {sorted(orig)}")
    print(f"batch-49r: {len(resc)} records  {sorted(resc)}")
    overlap = sorted(set(orig) & set(resc))
    print(f"overlap  : {len(overlap)}  {overlap}")
    print(f"only in batch-49 : {sorted(set(orig) - set(resc))}")
    print(f"only in batch-49r: {sorted(set(resc) - set(orig))}")

    if not overlap:
        return
    print()
    print("=== unplanned blind duplicate pairs ===")
    g_agree = s_agree = p_agree = 0
    overlaps = []
    for item in overlap:
        a, b = summarize(orig[item]), summarize(resc[item])
        ga = a["genres"][:1] == b["genres"][:1]
        sa = a["shape"] == b["shape"]
        pa = sorted(a["pipeline"]) == sorted(b["pipeline"])
        g_agree += ga
        s_agree += sa
        p_agree += pa
        ov = jaccard(a["asks"], b["asks"])
        overlaps.append(ov)
        print(f"\n{item}")
        print(f"  genre    {'OK ' if ga else 'DIFF'}  {a['genres']}  vs  {b['genres']}")
        print(f"  shape    {'OK ' if sa else 'DIFF'}  {a['shape']}  vs  {b['shape']}")
        print(f"  preset         {a['preset']}  vs  {b['preset']}")
        print(f"  pipeline {'OK ' if pa else 'DIFF'}  {a['pipeline']}  vs  {b['pipeline']}")
        print(f"  verdict        {a['verdict']}  vs  {b['verdict']}")
        print(f"  ask overlap    {ov:.2f}   ({len(a['asks'])} vs {len(b['asks'])} asks)")
        print(f"    only 49 : {sorted(set(a['asks']) - set(b['asks']))}")
        print(f"    only 49r: {sorted(set(b['asks']) - set(a['asks']))}")

    n = len(overlap)
    print()
    print(f"genre agreement    : {g_agree}/{n}")
    print(f"shape agreement    : {s_agree}/{n}")
    print(f"pipeline agreement : {p_agree}/{n}")
    print(f"mean ask overlap   : {sum(overlaps)/n:.2f}")


if __name__ == "__main__":
    sys.exit(main())
