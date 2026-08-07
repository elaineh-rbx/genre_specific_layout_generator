"""Judge all three arms of the golden set against one shared list of requirements.

    raw      the untouched prompt plus the golden set's style tail
    needs    yesterday's arm - the sub-genre's Hard Needs injected
    rules    today's arm - Build.md Part II, one shape plus the picked options

Scoring each arm against only what it asked for would flatter it, so the list for a
scene is the *union* of what both guided arms asked for, and every requirement carries
the arm that requested it. That makes the interesting question readable directly: does
an arm deliver only the features it named, or does it also happen to satisfy the
other's?

The three images are shuffled per scene by a fixed permutation of the scene number and
labelled A, B, C, so the judge never learns which arm is which and position cannot
correlate with arm.

Usage:
    python -m gslg.judges.three_way --workers 8
    python -m gslg.judges.three_way --stage iso
"""

from __future__ import annotations

import argparse
import itertools
import json
import pathlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from gslg import llm, paths
from gslg.judges import rules as rsc

ARMS = paths.ARMS
PERMS = list(itertools.permutations(range(3)))

STAGES = {
    "iso": dict(out="three_way_iso.jsonl", what="isometric"),
    "td": dict(out="three_way_td.jsonl", what="top-down"),
}

SYSTEM = """You audit game-layout concept images against explicit layout requirements.

You see three images of the same game scene, labelled A, B and C, and a numbered list
of layout requirements. For each requirement, decide independently whether it is
clearly visible in A, in B, and in C.

Judge only what is actually depicted. "Clearly visible" means a person reading the
image could point at the thing. Do not credit a requirement because the scene is the
right genre, because the thing is implied, or because it would be easy to add. If you
cannot point at it, it is absent.

The three images are unrelated attempts at the same brief - do not assume they should
agree, and do not let one image's answer influence another's.

Ignore art quality, lighting, colour and appeal entirely. You are checking presence
and arrangement, nothing else."""


def requirements(needs_row: dict, rules_row: dict) -> list[dict]:
    """What both guided arms asked for, each tagged with who asked."""
    out: list[dict] = []
    seen: set[str] = set()

    def add(label: str, text: str, source: str, kind: str) -> None:
        key = text.strip().lower()
        if not key or key in seen:
            return
        seen.add(key)
        out.append({"label": label, "text": text.strip(), "source": source,
                    "kind": kind})

    for n in needs_row.get("needs", []):
        add(n.get("id", "hard need"), n["visual"], "needs", "hard-need")
    for f in needs_row.get("fragments", []):
        add("invariant", f["text"], "needs", "invariant")
    for q in rsc.requirements(rules_row):
        add(q["label"], q["text"], "rules", q["kind"])
    return out


def _schema(n: int) -> dict:
    return {
        "name": "audit", "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "requirements": {
                    "type": "array", "minItems": n, "maxItems": n,
                    "items": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "integer"},
                            "in_a": {"type": "boolean"},
                            "in_b": {"type": "boolean"},
                            "in_c": {"type": "boolean"},
                            "note": {"type": "string"},
                        },
                        "required": ["index", "in_a", "in_b", "in_c", "note"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["requirements"],
            "additionalProperties": False,
        },
    }


def judge_paths(reqs: list[dict], thumbs: dict[str, pathlib.Path], key: int,
                retries: int = 3) -> tuple[list[dict], list[str]] | None:
    """Ask the judge about one trio of images, blinded, and return the marked list.

    Split out from `judge` so anything holding three images can be scored the same
    way the golden set is - a card built for a prompt typed into the playground has
    no scene number and no run row, but it deserves the identical blinded call
    rather than a second, laxer one written for it.
    """
    # A fixed permutation per key: the label an arm gets is unpredictable but
    # reproducible, and every ordering is used roughly equally across the set.
    shown = [ARMS[i] for i in PERMS[key % len(PERMS)]]   # position -> arm

    listing = "\n".join(f"{i + 1}. {r['label']} - {r['text']}"
                        for i, r in enumerate(reqs))
    content: list[dict] = [llm.text_part(f"REQUIREMENTS\n{listing}")]
    for pos, arm in zip("ABC", shown):
        content.append(llm.text_part(f"Image {pos}:"))
        content.append(llm.image_part(thumbs[arm]))
    content.append(llm.text_part(
        "For every requirement, mark presence in each image."))

    try:
        out = llm.ask(SYSTEM, content, _schema(len(reqs)), retries=retries)
    except llm.LLMError:
        return None
    items = []
    for i, r in enumerate(out["requirements"]):
        if i >= len(reqs):
            break
        by_pos = {"A": r["in_a"], "B": r["in_b"], "C": r["in_c"]}
        items.append({**reqs[i], "note": r["note"],
                      **{arm: by_pos[pos] for pos, arm in zip("ABC", shown)}})
    return items, shown


def judge(job: tuple[dict, dict, str], retries: int = 3) -> dict | None:
    needs_row, rules_row, stage = job
    scene = rules_row["scene"]
    reqs = requirements(needs_row, rules_row)
    if not reqs:
        return None

    thumbs = {}
    for arm in ARMS:
        dest = paths.thumb(arm, stage, scene)
        if not rsc.thumb(paths.scene(arm, stage, scene), dest):
            return None
        thumbs[arm] = dest

    marked = judge_paths(reqs, thumbs, int(scene), retries)
    if marked is None:
        print(f"  {scene}: judging failed", flush=True)
        return None
    items, shown = marked
    return {"scene": scene, "genre": rules_row["genre"],
            "preset": rules_row["preset"], "order": rules_row["order"],
            "subgenre": needs_row.get("subgenre_id", ""),
            "shown": shown, "items": items, "total": len(items),
            **{f"{a}_met": sum(x[a] for x in items) for a in ARMS}}


def report(results: list[dict], what: str) -> None:
    tot = sum(r["total"] for r in results)
    print(f"\n{len(results)} scenes, {tot} requirement checks ({what})")
    for arm, label in (("raw", "raw prompt"), ("needs", "yesterday - Hard Needs"),
                       ("rules", "today - Build.md Part II")):
        m = sum(r[f"{arm}_met"] for r in results)
        print(f"  {label:28s} {m:4d}/{tot}  {100*m/tot:5.1f}%")

    print("\nsplit by which arm asked for the requirement:")
    for src in ("needs", "rules"):
        its = [it for r in results for it in r["items"] if it["source"] == src]
        if not its:
            continue
        line = "  ".join(f"{a} {100*sum(x[a] for x in its)/len(its):5.1f}%"
                         for a in ARMS)
        who = "yesterday asked for" if src == "needs" else "today asked for"
        print(f"  {who:22s} n={len(its):3d}   {line}")

    print("\nper scene, best arm:")
    win = Counter()
    for r in results:
        best = max(ARMS, key=lambda a: r[f"{a}_met"])
        top = [a for a in ARMS if r[f"{a}_met"] == r[f"{best}_met"]]
        win["tie" if len(top) > 1 else best] += 1
    print(" ", dict(win))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--stage", choices=tuple(STAGES) + ("both",), default="both")
    ap.add_argument("--only", default="", help="rescore just these scenes, e.g. "
                    "0053,0054 - the rest keep the scores already on disk")
    args = ap.parse_args()

    needs = {json.loads(x)["scene"]: json.loads(x)
             for x in (paths.RUNS / "needs.jsonl").open() if x.strip()}
    rules = [json.loads(x) for x in (paths.RUNS / "rules.jsonl").open() if x.strip()]
    rules = [r for r in rules if r["status"] == "ok" and r["scene"] in needs]
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    if only:
        rules = [r for r in rules if r["scene"] in only]
    paths.SCORES.mkdir(parents=True, exist_ok=True)

    for stage in (tuple(STAGES) if args.stage == "both" else (args.stage,)):
        st = STAGES[stage]
        print(f"\njudging {len(rules)} {st['what']} triples with {llm.DEPLOYMENT}",
              flush=True)
        jobs = [(needs[r["scene"]], r, stage) for r in rules]
        results = []
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for i, res in enumerate(pool.map(judge, jobs), 1):
                if res:
                    results.append(res)
                if i % 15 == 0:
                    print(f"  {i}/{len(jobs)}", flush=True)
        out = paths.SCORES / st["out"]
        if only and out.is_file():
            # Merge, so rescoring a few regenerated scenes keeps the scores for the
            # scenes this run never looked at.
            kept = {r["scene"]: r for x in out.open() if x.strip()
                    for r in [json.loads(x)]}
            kept.update({r["scene"]: r for r in results})
            results = list(kept.values())
        results.sort(key=lambda r: r["scene"])
        out.write_text("".join(json.dumps(r) + "\n" for r in results),
                       encoding="utf-8")
        report(results, st["what"])
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
