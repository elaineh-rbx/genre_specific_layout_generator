"""Import upstream evaluation handoffs into the shape the pipeline runs on.

The upstream repo `mpalleschi/3D-LayoutBuild-Rules` (mirrored under `evaluation/`)
carries ~625 real user prompts, each with a `handoff.genre_choice` block produced
by an agent following `.cursor/skills/genre-choice/`. Those blocks are the same
schema `results/routing/skill/*.json` uses, so this importer just:

    * pulls the source prompt out of the golden-set CSV
    * writes each block to `results/routing/skill/P<n>.json`, in the wrapped
      shape `handoff.load` accepts (`{scene, source, block}`)
    * appends a minimal row per scene to `results/prompts/golden_set.jsonl`
      so the pipeline's `_manifest()` can find it

After running this, `python -m layoutgen.pipeline.golden --arm skill` will
generate isometric + top-down for every imported scene (P6 scenes get a
plan-first order, others go isometric-first).

Item ids map straight to a CSV file line: `P0214` is line 214, with the header
on line 1, so the 0-indexed row is `int(id[1:]) - 2`. That is documented in
`evaluation/README.md` as "P0087 is line 87."

Usage:
    python tools/import_upstream_handoffs.py            # dry-run summary
    python tools/import_upstream_handoffs.py --write    # write skill blocks + prompts
    python tools/import_upstream_handoffs.py --write --limit 3
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import pathlib
import sys
from collections import Counter

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen import paths
from layoutgen.model import handoff as H

EVAL = REPO / "evaluation" / "data"
CSV_PROMPTS = EVAL / "layout gen prompt golden set  - build 600 (prod subgenre balanced).csv"
RECORDS_GLOB = str(EVAL / "records" / "batch-*.jsonl")


def load_prompt_index() -> dict[str, dict]:
    """Return `{item_id: {source_prompt, genre, subgenre, dimension, remove}}`
    keyed by the upstream `P0NNN` id, which is CSV file line N."""
    with CSV_PROMPTS.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out: dict[str, dict] = {}
    for line, row in enumerate(rows, start=2):        # data starts on file line 2
        item_id = f"P{line:04d}"
        out[item_id] = {
            "source_prompt": row.get("initial_prompt", ""),
            "genre": row.get("inferred_game_genre", ""),
            "subgenre": row.get("inferred_game_subgenre", ""),
            "dimension": row.get("inferred_game_dimension", ""),
            "remove": row.get("remove", "").strip() in ("1", "true", "True"),
        }
    return out


def iter_records():
    for path in sorted(glob.glob(RECORDS_GLOB)):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if "handoff" in rec and "genre_choice" in rec["handoff"]:
                yield rec


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="actually write files")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--include-remove", action="store_true",
                    help="don't filter rows the source spreadsheet flagged remove=1")
    args = ap.parse_args()

    prompts = load_prompt_index()
    print(f"CSV: {len(prompts)} data rows indexed as P{min(int(k[1:]) for k in prompts):04d}"
          f"..P{max(int(k[1:]) for k in prompts):04d}")

    skill_dir = paths.ROUTING / "skill"
    prompts_file = paths.PROMPTS

    already_have = {p.stem for p in skill_dir.glob("*.json")}
    print(f"skill blocks already on disk: {len(already_have)}")

    records = list(iter_records())
    print(f"upstream records with handoff.genre_choice: {len(records)}")

    modes = Counter()
    problem_kinds = Counter()
    skipped = Counter()
    to_write: list[tuple[str, dict, dict]] = []   # (scene, wrapped_block, meta)

    for rec in records:
        scene = rec["item_id"]
        meta = prompts.get(scene)
        if meta is None:
            skipped["no-csv-row"] += 1
            continue
        if meta["remove"] and not args.include_remove:
            skipped["remove=1"] += 1
            continue
        gc = rec["handoff"]["genre_choice"]
        h = H.adapt(gc, source=meta["source_prompt"])
        if not h.ok:
            for p in h.problems:
                if p.kind in H.FATAL:
                    skipped[p.kind] += 1
            continue
        modes[h.spec.get("mode", "?")] += 1
        for p in h.problems:
            problem_kinds[p.kind] += 1
        h_full = rec.get("handoff", {})
        wrapped = {
            "scene": scene,
            "source": meta["source_prompt"],
            "block": gc,
            "open_questions": h_full.get("open_questions") or [],
            "theme": h_full.get("theme") or "",
            "scale": h_full.get("scale") or {},
            "coverage_missing": (rec.get("coverage") or {}).get("missing") or [],
        }
        to_write.append((scene, wrapped, meta))

    if args.limit:
        to_write = to_write[: args.limit]

    print(f"\nadaptable & to import: {len(to_write)}")
    print(f"  by mode after adapt: {dict(modes)}")
    print(f"  skipped: {dict(skipped)}")
    print(f"  non-fatal problems (kept): {dict(problem_kinds)}")

    if not args.write:
        print("\ndry run — pass --write to actually create files")
        return

    skill_dir.mkdir(parents=True, exist_ok=True)
    prompts_file.parent.mkdir(parents=True, exist_ok=True)

    existing = {}
    if prompts_file.is_file():
        for line in prompts_file.open(encoding="utf-8"):
            if line.strip():
                row = json.loads(line)
                existing[row["scene"]] = row

    wrote_blocks = 0
    for scene, wrapped, meta in to_write:
        block_path = skill_dir / f"{scene}.json"
        block_path.write_text(json.dumps(wrapped, indent=2, ensure_ascii=False),
                              encoding="utf-8")
        wrote_blocks += 1
        title = f"Upstream {scene} — {meta.get('subgenre') or meta.get('genre') or 'unlabelled'}"
        existing[scene] = {
            "scene": scene,
            "title": title,
            "source_prompt": meta["source_prompt"],
            "upstream_genre": meta.get("genre", ""),
            "upstream_subgenre": meta.get("subgenre", ""),
            "upstream_dimension": meta.get("dimension", ""),
        }

    with prompts_file.open("w", encoding="utf-8") as fh:
        for scene in sorted(existing):
            fh.write(json.dumps(existing[scene], ensure_ascii=False) + "\n")

    print(f"\nwrote {wrote_blocks} skill blocks under {skill_dir}")
    print(f"prompts file now has {len(existing)} rows: {prompts_file}")


if __name__ == "__main__":
    main()
