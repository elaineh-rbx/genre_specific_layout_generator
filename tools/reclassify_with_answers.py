"""Re-route each scene with the intake's questions and their answers folded in.

Each imported scene already carries three things: the source prompt, the
upstream skill's first-pass genre/config, and (after `answer_questions.py`)
one answer per open question. This tool builds an enriched prompt from those,
runs it through `layoutgen.model.router.classify`, and writes the resulting
config to `results/routing/answered/<scene>.json`.

The three configurations then sit side by side for any diff worth caring
about:

    results/routing/rules.jsonl                one row per scene, the router's
                                               original pick from the bare
                                               prompt (75 golden scenes only)
    results/routing/skill/<scene>.json         the upstream skill's first-pass
                                               pick, one JSON per scene, 692
                                               total (75 legacy + 617 imported)
    results/routing/answered/<scene>.json      this file's output: the router's
                                               pick when the prompt is enriched
                                               with the scene's clarifications
    results/routing/raw/<scene>.json           `--no-answers`: the same router on
                                               the same scenes with the answers
                                               withheld, which is what the pipeline
                                               did before there was an intake

`--no-answers` exists because otherwise the answered arm has no baseline outside
the 75 golden scenes, and without one there is no way to tell how much of its
accuracy comes from having answers at all rather than from the routing. It walks
the same scene list, so the two are paired scene for scene.

The answers are inlined into the prompt rather than passed as a separate
channel because the router's system prompts already know how to weigh
prompt-quoted evidence, so a clarification given in the author's voice is
processed the same way as an author's original sentence.

Usage:
    python tools/reclassify_with_answers.py --limit 5           # pilot
    python tools/reclassify_with_answers.py                     # every answered scene
    python tools/reclassify_with_answers.py --only P0002,P0214  # named scenes
    python tools/reclassify_with_answers.py --force             # redo scenes already done
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen.backends import llm
from layoutgen.model import router
from layoutgen.paths import ROUTING

SKILL = ROUTING / "skill"
ANSWERED = ROUTING / "answered"
RAW = ROUTING / "raw"


def enriched_prompt(source: str, answers: list[dict]) -> str:
    """Append each Q&A pair to the prompt so the router sees the resolution
    in the same voice the prompt is written in."""
    if not answers:
        return source
    lines = [source.rstrip(), "", "--- clarifications from the author ---"]
    for a in answers:
        ans = (a.get("answer") or "").strip()
        if not ans:
            continue
        lines.append(f"- [{a.get('field','?')}] {a.get('ask','').rstrip('?')}? "
                     f"{ans}")
    return "\n".join(lines)


def load_scene(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def upstream_summary(row: dict) -> dict:
    """The bit of the upstream skill's pick worth carrying alongside for diffs."""
    block = row.get("block") or {}
    return {
        "genres": block.get("genres") or [],
        "shape": (block.get("shape") or {}).get("id") or "",
        "preset": block.get("preset") or "",
        "pipeline": block.get("pipeline") or [],
    }


def reclassify_one(path: pathlib.Path,
                   use_answers: bool = True) -> tuple[str, str, dict | None]:
    row = load_scene(path)
    scene = row.get("scene") or path.stem
    source = row.get("source") or ""
    answers = row.get("answers") or []
    if not source.strip():
        return scene, "skip:no-source", None
    try:
        s = router.classify(enriched_prompt(source, answers) if use_answers else source,
                            scene=scene)
    except Exception as exc:
        return scene, f"error:{type(exc).__name__}: {exc}", None
    out = {
        "scene": scene,
        "source": source,
        # Recorded even when withheld, so a raw record still shows what was available
        # and was not used - an empty list here would read as a scene without an intake.
        "answers": answers,
        "answered": bool(answers) and use_answers,
        "saw_answers": use_answers,
        "config": asdict(s),
        "upstream_skill": upstream_summary(row),
    }
    return scene, "ok", out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--include-unanswered", action="store_true",
                    help="also process scenes with no answers (e.g. the 75 legacy)")
    ap.add_argument("--force", action="store_true",
                    help="redo scenes already present under results/routing/answered/")
    ap.add_argument("--no-answers", action="store_true",
                    help="withhold the answers and write to results/routing/raw/: the "
                         "baseline the answered arm is measured against")
    args = ap.parse_args()

    out_dir = RAW if args.no_answers else ANSWERED
    out_dir.mkdir(parents=True, exist_ok=True)
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    paths = sorted(SKILL.glob("*.json"))
    todo: list[pathlib.Path] = []
    for p in paths:
        row = load_scene(p)
        scene = row.get("scene") or p.stem
        if only and scene not in only:
            continue
        # The same filter with or without answers, so the raw arm covers exactly the
        # scenes the answered arm covers and the two can be compared scene for scene.
        if not (row.get("answers") or []) and not args.include_unanswered:
            continue
        if (out_dir / f"{scene}.json").exists() and not args.force:
            continue
        todo.append(p)
    if args.limit:
        todo = todo[: args.limit]

    print(f"reclassifying {len(todo)} scenes via {llm.DEPLOYMENT} "
          f"({args.workers} workers, answers "
          f"{'WITHHELD -> ' + out_dir.name if args.no_answers else 'included'})",
          flush=True)

    lock = threading.Lock()
    done = 0
    ok = err = 0
    t0 = time.monotonic()

    def worker(p: pathlib.Path) -> None:
        nonlocal done, ok, err
        scene, status, out = reclassify_one(p, use_answers=not args.no_answers)
        with lock:
            done += 1
            if status == "ok" and out is not None:
                (out_dir / f"{scene}.json").write_text(
                    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
                ok += 1
                c = out["config"]
                print(f"  [{done}/{len(todo)}] {scene}  "
                      f"{c['genre']} :: {c['preset']}  ({c['shape']})",
                      flush=True)
            else:
                err += 1
                print(f"  [{done}/{len(todo)}] {scene}  {status}", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for _ in pool.map(worker, todo):
            pass

    dt = time.monotonic() - t0
    print(f"\n{ok} ok, {err} error in {dt:.1f}s ({(ok/dt if dt else 0):.1f} scenes/sec)")


if __name__ == "__main__":
    main()
