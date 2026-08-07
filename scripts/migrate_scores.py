"""Rewrite the score files that predate the generic comparison format.

The two judges that existed before each wrote their own shape: the pairwise one named
its arms `base` and `rules` and put a `base_met` beside a `rules_met`, and the
three-way one named its verdicts after the arms directly. Neither could describe a
fourth arm without another format.

Both are the same statement - for each requirement, which arms showed it - so both
convert without rejudging, and about a thousand model calls stay unspent.

Idempotent: a file already in the new format is left alone.

Usage:
    python scripts/migrate_scores.py
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from gslg import paths  # noqa: E402

#: old file -> (comparison, stage, how its verdict keys map onto arm ids)
OLD = {
    "three_way_iso.jsonl": ("three_way", "iso",
                            {"raw": "raw", "needs": "needs", "rules": "rules"}),
    "three_way_td.jsonl": ("three_way", "td",
                           {"raw": "raw", "needs": "needs", "rules": "rules"}),
    "rules_iso.jsonl": ("rules_vs_raw", "iso", {"base": "raw", "rules": "rules"}),
    "rules_td.jsonl": ("rules_vs_raw", "td", {"base": "raw", "rules": "rules"}),
}


def convert(row: dict, cmp: str, stage: str, keys: dict[str, str]) -> dict:
    arms = list(keys.values())
    items = [{"label": it["label"], "text": it["text"], "kind": it["kind"],
              "source": it.get("source", "rules"), "note": it.get("note", ""),
              "present": {arm: bool(it.get(old)) for old, arm in keys.items()}}
             for it in row["items"]]
    # The pairwise judge recorded only whether it swapped the two sides; the order
    # shown is that swap applied to the arms in their canonical order.
    shown = row.get("shown") or (arms[::-1] if row.get("swapped") else arms)
    return {"scene": row["scene"], "comparison": cmp, "stage": stage,
            "genre": row.get("genre", ""), "preset": row.get("preset", ""),
            "order": row.get("order", ""), "shown": shown,
            "items": items, "total": len(items),
            "met": {arm: sum(bool(it["present"][arm]) for it in items)
                    for arm in arms}}


def main() -> None:
    for name, (cmp, stage, keys) in OLD.items():
        src = paths.SCORES / name
        dest = paths.SCORES / f"{cmp}_{stage}.jsonl"
        if not src.is_file():
            print(f"  {name}: absent, skipping")
            continue
        rows = [json.loads(x) for x in src.open() if x.strip()]
        if rows and "met" in rows[0]:
            print(f"  {name}: already converted")
            continue
        out = [convert(r, cmp, stage, keys) for r in rows]
        out.sort(key=lambda r: r["scene"])
        dest.write_text("".join(json.dumps(r) + "\n" for r in out), encoding="utf-8")
        checks = sum(r["total"] for r in out)
        met = {a: sum(r["met"][a] for r in out) for a in out[0]["met"]}
        print(f"  {dest.name}: {len(out)} scenes, {checks} checks, "
              + "  ".join(f"{a} {100 * n / checks:.0f}%" for a, n in met.items()))
        if src != dest:
            src.unlink()


if __name__ == "__main__":
    main()
