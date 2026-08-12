"""Publish the `/pipeline` image set and its per-scene provenance to S3.

The pipeline viewer draws one page per scene from four files that never sit
together: the routing decision, the run record, the checklist and the images.
This walks the same four and flattens them into one row per scene, so the set
can be read outside the viewer - and uploads the images the rows point at.

    results/routing/answered/<scene>.json   source prompt, Q&A, the router's config
    results/runs/answered.jsonl             the prompts actually sent, per stage
    results/eval/<scene>.json               the checklist of features asked for
    results/scenes/answered/{iso,td,plan}/  the images that landed

Every prompt column is the text as sent, not a reconstruction. `enriched_prompt`
is rebuilt with `reclassify_with_answers.enriched_prompt`, the same function that
produced the router's input, rather than a second implementation of it.

Usage:
    python tools/export_pipeline_to_s3.py --dry-run     # CSV only, nothing uploaded
    python tools/export_pipeline_to_s3.py               # CSV + 1247 images
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen.model import rules as br
from layoutgen.paths import EVAL, RESULTS, ROUTING, SCENES
from tools.build_pipeline_viewer import option_split, unescape_nl
from tools.reclassify_with_answers import enriched_prompt

ANSWERED = ROUTING / "answered"
ANSWERED_SCENES = SCENES / "answered"

BUCKET = "3dfm-data"
PREFIX = "users/elaineh/layoutgen_pipeline_260811"

#: Stage directory -> the folder it gets in the bucket. Renamed on the way out
#: because `iso`/`td` are this repo's shorthand and the CSV is read elsewhere.
STAGES = {"iso": "isometric", "td": "topdown", "plan": "plan"}

#: `order` as the runners record it -> which image was drawn first. The first
#: image is the authoritative one; the second is derived from it, so a row that
#: does not say which came first cannot be read correctly.
FIRST = {"std": "isometric", "p6": "topdown (plan)", "layout": "authored plan"}


def runs() -> dict[str, dict]:
    path = RESULTS / "runs" / "answered.jsonl"
    return {r["scene"]: r for line in path.open(encoding="utf-8")
            if line.strip() for r in [json.loads(line)]}


def english() -> dict[str, dict]:
    """The translated body, for the 64 prompts their authors did not write in
    English. The row carries both it and the original, because the original is
    what was asked for and the translation is what the image model was given."""
    path = ROUTING / "english.jsonl"
    if not path.is_file():
        return {}
    return {r["scene"]: r for line in path.open(encoding="utf-8")
            if line.strip() for r in [json.loads(line)]}


def numbered(items: list[str]) -> str:
    """One cell holding an ordered list. Numbered rather than newline-separated
    alone so that questions and answers in adjacent cells stay aligned by eye
    when a spreadsheet collapses the wrapping."""
    return "\n".join(f"{i}. {t}" for i, t in enumerate(items, 1))


def opts(entries: list[dict]) -> str:
    return "\n".join(f"{e['id']}: {e['label']} - {e['what']}" for e in entries)


def row_for(scene_path: pathlib.Path, run: dict, translated: dict) -> dict:
    d = json.loads(scene_path.read_text(encoding="utf-8"))
    scene = d["scene"]
    cfg = d.get("config") or {}
    answers = d.get("answers") or []
    source = d.get("source", "")

    img_opts, lay_opts = option_split(cfg.get("genre", ""), cfg.get("options") or [])

    # Which images exist decides both the URI columns and the artifact list, so
    # resolve it once. A scene whose render errored has neither.
    uris, present = {}, []
    for stage, folder in STAGES.items():
        if (ANSWERED_SCENES / stage / f"{scene}.png").is_file():
            uris[stage] = f"s3://{BUCKET}/{PREFIX}/{folder}/{scene}.png"
            present.append(folder)

    checklist = {"features": [], "excluded": []}
    ev = EVAL / f"{scene}.json"
    if ev.is_file():
        checklist = json.loads(ev.read_text(encoding="utf-8"))

    features = checklist.get("features") or []
    excluded = checklist.get("excluded") or []
    if features:
        present.append("checklist")
    if answers:
        present.append("clarifications")

    return {
        "scene": scene,
        "title": run.get("title", ""),
        "status": run.get("status", ""),
        "error": next(iter((run.get("error") or "").splitlines()), "")[:300],

        "genre": cfg.get("genre", ""),
        "secondary_genres": ", ".join(cfg.get("secondary") or []),
        "shape": cfg.get("shape") or "",
        "shape_label": cfg.get("shape_label") or "",
        "preset": cfg.get("preset") or "none",
        "confidence": cfg.get("confidence", ""),
        "route": ", ".join(cfg.get("route") or []) or "P0",
        "order": run.get("order", ""),
        "renders_first": FIRST.get(run.get("order", ""), ""),

        "original_prompt": unescape_nl(source),
        "source_language": translated.get("language", "en"),
        # What the image prompt was built around. Identical to the original for the
        # ~90% written in English, and its literal translation otherwise - except
        # where the translation was rejected, which the next column names.
        "body_sent": unescape_nl(
            source if translated.get("rejected") else
            (translated.get("english") or source)),
        "translation_note": translated.get("rejected", ""),
        "n_questions": len(answers),
        "questions": numbered([a.get("ask", "") for a in answers]),
        "answers": numbered([a.get("answer", "") for a in answers]),
        "qa_pairs": "\n\n".join(
            f"[{a.get('field', '?')}] Q: {a.get('ask', '')}\nA: {a.get('answer', '')}"
            for a in answers),
        "enriched_prompt": unescape_nl(enriched_prompt(source, answers)),

        "addendum": unescape_nl(cfg.get("addendum", "")),
        "iso_prompt_sent": unescape_nl(run.get("iso_prompt", "")),
        "td_prompt_sent": unescape_nl(run.get("td_prompt", "")),

        "s3_isometric": uris.get("iso", ""),
        "s3_topdown": uris.get("td", ""),
        "s3_plan": uris.get("plan", ""),

        "options_to_image": opts(img_opts),
        "options_to_layout": opts(lay_opts),
        "options_held": ", ".join(cfg.get("dropped_options") or []),

        "artifacts": ", ".join(present),
        "n_checklist_features": len(features),
        "checklist_features": "\n".join(
            f"- {f.get('name', '')} [{f.get('origin', '')}]"
            + (f" - {f['notes']}" if f.get("notes") else "") for f in features),
        "checklist_excluded": "\n".join(
            f"- {e.get('name', '')} ({e.get('why', '')})" for e in excluded),
    }


def collect() -> list[dict]:
    run, eng = runs(), english()
    return [row_for(p, run.get(p.stem, {}), eng.get(p.stem, {}))
            for p in sorted(ANSWERED.glob("*.json"))]


def write_csv(rows: list[dict], dest: pathlib.Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)


def upload(pairs: list[tuple[pathlib.Path, str]], workers: int) -> None:
    """Push every file, reporting as it goes.

    boto3 rather than `aws s3 sync` so a failure names the object that failed
    instead of ending the whole transfer on a summary line.
    """
    import boto3
    s3 = boto3.client("s3")
    done = 0

    def put(pair):
        src, key = pair
        ctype = "text/csv" if src.suffix == ".csv" else "image/png"
        s3.upload_file(str(src), BUCKET, key, ExtraArgs={"ContentType": ctype})

    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        for _ in pool.map(put, pairs):
            done += 1
            if done % 50 == 0 or done == len(pairs):
                print(f"  {done}/{len(pairs)}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="write the CSV locally and upload nothing")
    ap.add_argument("--csv-only", action="store_true",
                    help="upload the CSV but not the images")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    rows = collect()
    csv_path = RESULTS / "pipeline_export.csv"
    write_csv(rows, csv_path)
    ok = sum(r["status"] == "ok" for r in rows)
    print(f"{len(rows)} scenes -> {csv_path}  ({ok} rendered, {len(rows) - ok} failed)")

    pairs = [(csv_path, f"{PREFIX}/pipeline_scenes.csv")]
    if not args.csv_only:
        for stage, folder in STAGES.items():
            for f in sorted((ANSWERED_SCENES / stage).glob("*.png")):
                pairs.append((f, f"{PREFIX}/{folder}/{f.name}"))

    if args.dry_run:
        print(f"dry run - would upload {len(pairs)} objects to "
              f"s3://{BUCKET}/{PREFIX}/")
        return

    print(f"uploading {len(pairs)} objects to s3://{BUCKET}/{PREFIX}/")
    upload(pairs, args.workers)
    print("done")


if __name__ == "__main__":
    main()
