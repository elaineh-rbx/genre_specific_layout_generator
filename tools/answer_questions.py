"""Answer the intake's open questions for each imported scene.

The upstream handoff records, for every prompt, the crisp follow-up asks the
intake skill would have sent back to the user before building - things like
"Fountain or lake?" or "How big should the wilderness be?". This tool plays
the user's part: for each scene, it sends the prompt and its open questions
through a single JSON-schema-constrained LLM call, gets one answer per
question, and writes them back into the scene JSON.

The answers are what a decisive prompt author would say: pick the choice best
supported by the prompt, otherwise the simplest default the prompt does not
rule out. Short prose, not multiple choice - the downstream router reads them
as clarifications, so an answer that says "roughly ten shops, arranged around
the plaza" is more useful than one that just names an enum.

Idempotent: scenes that already carry an `answers` field are skipped unless
`--force` is passed. Scenes with no `open_questions` are silently skipped -
the 75 legacy scenes and a handful of upstream ones that started fully
specified fall into that bucket.

Usage:
    python tools/answer_questions.py --limit 5              # small pilot
    python tools/answer_questions.py                        # every remaining scene
    python tools/answer_questions.py --only P0002,P0214     # named scenes
    python tools/answer_questions.py --force --only P0214   # redo one
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen.backends import llm
from layoutgen.paths import ROUTING

SKILL = ROUTING / "skill"

SYSTEM = """You are the user who wrote a Roblox game prompt. The layout intake
has read your prompt and sent back a short list of follow-up questions before
it builds - each one flags a genuine ambiguity that a specific answer would
resolve.

Answer each question as decisively as the prompt lets you:

1. If the prompt already names or strongly implies an answer, say that. Don't
   re-open a decision you already made in the prompt.
2. If the prompt is silent, pick the simplest, most conventional choice for
   the game you're describing - the one that keeps the build small and
   plainly playable. Explain in the same breath.
3. Keep it short - one sentence or two, in the voice of the prompt author.
   You are giving the intake enough to build, not rewriting the design doc.
   Always answer in English, even when the prompt is written in another
   language. The answers are appended to the prompt and read by the router
   and by the reviewers, both of which work in English; matching the prompt's
   language instead leaves the enriched prompt half in one language and half
   in another. Keep proper nouns as the author spelled them.
4. If a question offers a "or" between two structural options (e.g. "fountain
   or lake?", "instanced or same surface?"), pick one. Straddling is not an
   answer.
5. If a question asks about theme or look and you haven't specified one, pick
   a plainly-matching common theme (High Fantasy, Modern, Cartoon, Sci-Fi,
   etc.) rather than inventing something bespoke.
6. If a question asks about scale, prefer the smaller side of what the prompt
   is compatible with. A vertical slice built on a small map is a better
   first result than a sprawling one that runs out of budget.
7. Never invent mechanics, characters, or story beats the prompt did not
   name. If a question probes for one, say the prompt doesn't call for it and
   answer with the default the intake can carry."""


ANSWER_SCHEMA = {
    "name": "intake_answers", "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "answers": {
                "type": "array",
                "description": "One answer per question, in the same order the "
                               "questions were given. Length must equal the "
                               "number of questions.",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string",
                                  "description": "Echo the question's field tag."},
                        "ask": {"type": "string",
                                "description": "Echo the question verbatim so "
                                               "the mapping is unambiguous."},
                        "answer": {"type": "string",
                                   "description": "One or two sentences, in "
                                                  "the voice of the prompt "
                                                  "author, resolving the ask."},
                    },
                    "required": ["field", "ask", "answer"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["answers"],
        "additionalProperties": False,
    },
}


def _user_turn(prompt: str, questions: list[dict]) -> str:
    lines = [f"YOUR PROMPT\n\"\"\"\n{prompt.strip()[:6000]}\n\"\"\"\n",
             f"THE INTAKE'S FOLLOW-UP QUESTIONS ({len(questions)})"]
    for i, q in enumerate(questions, 1):
        lines.append(f"  {i}. [{q.get('field','?')}] {q.get('ask','')}")
    lines.append("\nAnswer each question, in order. One or two sentences each.")
    return "\n".join(lines)


def answer_one(path: pathlib.Path) -> tuple[str, str, dict | None]:
    """Returns (scene, status, patched_row). status is 'ok', 'skip', or 'error'."""
    row = json.loads(path.read_text(encoding="utf-8"))
    scene = row.get("scene") or path.stem
    questions = row.get("open_questions") or []
    if not questions:
        return scene, "skip:no-questions", None
    prompt = row.get("source") or ""
    if not prompt.strip():
        return scene, "skip:no-source", None
    try:
        resp = llm.ask(SYSTEM, _user_turn(prompt, questions), ANSWER_SCHEMA)
    except Exception as exc:
        return scene, f"error:{type(exc).__name__}", None
    answers = resp.get("answers") or []
    # Guard against the model returning a different-length list. Zip against
    # the questions so each answer is anchored to the question it belongs to,
    # and drop any orphan entries at either end.
    aligned = []
    for q, a in zip(questions, answers):
        aligned.append({
            "field": q.get("field", ""),
            "ask": q.get("ask", ""),
            "answer": (a or {}).get("answer", "").strip(),
        })
    row["answers"] = aligned
    row["answers_missing"] = len(questions) - len(aligned)
    return scene, "ok", row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="",
                    help="comma-separated scene ids to answer, ignoring the rest")
    ap.add_argument("--force", action="store_true",
                    help="redo scenes that already have answers")
    args = ap.parse_args()

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    paths = sorted(SKILL.glob("*.json"))
    todo: list[pathlib.Path] = []
    for p in paths:
        row = json.loads(p.read_text(encoding="utf-8"))
        scene = row.get("scene") or p.stem
        if only and scene not in only:
            continue
        if not (row.get("open_questions") or []):
            continue
        if row.get("answers") and not args.force:
            continue
        todo.append(p)
    if args.limit:
        todo = todo[: args.limit]

    print(f"answering {len(todo)} scenes via {llm.DEPLOYMENT} ({args.workers} workers)",
          flush=True)

    lock = threading.Lock()
    done = 0
    ok = err = skipped = 0
    t0 = time.monotonic()

    def worker(p: pathlib.Path) -> None:
        nonlocal done, ok, err, skipped
        scene, status, patched = answer_one(p)
        with lock:
            done += 1
            if status == "ok" and patched is not None:
                p.write_text(json.dumps(patched, indent=2, ensure_ascii=False),
                             encoding="utf-8")
                ok += 1
                n = len(patched.get("answers") or [])
                print(f"  [{done}/{len(todo)}] {scene}  {n} answered", flush=True)
            elif status.startswith("skip"):
                skipped += 1
            else:
                err += 1
                print(f"  [{done}/{len(todo)}] {scene}  {status}", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for _ in pool.map(worker, todo):
            pass

    dt = time.monotonic() - t0
    print(f"\n{ok} ok, {err} error, {skipped} skipped in {dt:.1f}s "
          f"({(ok/dt if dt else 0):.1f} scenes/sec)")


if __name__ == "__main__":
    main()
