"""The per-scene checklist of visible features a render is judged against.

One file per *scene*, not per arm, and deliberately so: the comparison pages score two
arms against a list neither of them wrote, and `arms._author_asks` keeps only the
features traced back to the author's own words for exactly that reason. A checklist
written per arm would be each arm marking its own homework, and the two columns would
stop being comparable.

The addendum still has to come from somewhere, so it comes from whichever arm rendered
the scene first and is recorded in `addendum_from`. It only feeds the `addendum`-origin
half of the list, which the cross-arm comparisons filter out anyway.

Written by `tools/extract_checklist.py`, and by `pipeline.golden` at the end of a render
so a scene cannot be generated without one.
"""

from __future__ import annotations

import json
import pathlib
import threading
from concurrent.futures import ThreadPoolExecutor

from layoutgen import paths
from layoutgen.backends import llm

SYSTEM = """You are building an EVAL CHECKLIST from a game-layout prompt.

You will be shown the exact prompt sent to an image model - a source scene
description plus a structured addendum listing the picked shape and the
picked options. Your job is to enumerate the concrete VISUAL features a
rendered top-down or isometric image of this scene must contain, so that
a downstream evaluator can check the render against each item.

Rules:
1. VISUAL ONLY. Include features that would be identifiable in a bird's-eye
   render: buildings, terrain features, roads, water, distinct props,
   boundaries, spawn points, cover, etc. EXCLUDE mechanics, controls, save
   systems, UI, monetization, cutscenes, narrative, and anything that
   cannot be seen from a top-down image.
2. SHORT. Each item's `name` is 2-6 words, in noun-phrase form. No verbs,
   no punctuation, no articles. "central village" not "there is a village".
3. CONCRETE. Prefer items that a segmenter could find. "open wilderness"
   is good; "sense of adventure" is not.
4. DEDUPE. Two items should not describe the same visible element - merge
   them into one.
5. CATEGORIZE. Each item's `origin` says whether it came from the source
   prompt (the part before the addendum) or from the addendum itself. If
   both mention essentially the same thing, prefer `prompt` since that is
   the user's own words.
6. QUANTIFY when the prompt does. Put counts, sizes, or spatial hints in
   `notes` when the prompt gives them: "at least three", "in the middle",
   "wide enough for vehicles". Leave blank if unspecified.
7. RANGE. Aim for 5 to 15 items. Fewer is fine if the prompt is truly
   sparse; more is fine if the prompt is rich, but don't pad."""


CHECKLIST_SCHEMA = {
    "name": "eval_checklist", "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "features": {
                "type": "array",
                "description": "Concrete visible features the render should contain, "
                               "5-15 items typical.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Short noun phrase, 2-6 words.",
                        },
                        "origin": {
                            "type": "string",
                            "enum": ["prompt", "addendum"],
                            "description": "Where the feature came from.",
                        },
                        "notes": {
                            "type": "string",
                            "description": "Counts, sizes, positions from the prompt. "
                                           "Empty string if none.",
                        },
                        "quote": {
                            "type": "string",
                            "description": "A short verbatim quote from the prompt or "
                                           "addendum that justifies this item.",
                        },
                    },
                    "required": ["name", "origin", "notes", "quote"],
                    "additionalProperties": False,
                },
            },
            "excluded": {
                "type": "array",
                "description": "Non-visual asks that the prompt made but that a render "
                               "cannot show (mechanics, save/load, controls, etc.). "
                               "Kept so we know why the checklist is shorter than the "
                               "prompt is long.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "why": {"type": "string",
                                "description": "One short phrase saying why it was "
                                               "excluded, e.g. 'gameplay mechanic'."},
                    },
                    "required": ["name", "why"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["features", "excluded"],
        "additionalProperties": False,
    },
}


def path(scene: str) -> pathlib.Path:
    return paths.EVAL / f"{scene}.json"


def _user_turn(scene: str, source: str, addendum: str) -> str:
    parts = [f"SCENE: {scene}", "", "SOURCE PROMPT",
             '"""', source.strip(), '"""', ""]
    if addendum.strip():
        parts += ["ROUTER'S ADDENDUM (shape + option picks appended to the source)",
                  '"""', addendum.strip(), '"""', ""]
    else:
        parts += ["(no addendum \u2014 the router picked no options for this scene)", ""]
    parts.append("List the visible features the image model should render.")
    return "\n".join(parts)


def extract_one(scene: str, source: str, addendum: str) -> dict:
    return llm.ask(SYSTEM, _user_turn(scene, source, addendum), CHECKLIST_SCHEMA)


def ensure(rows, arm: str = "", workers: int = 12,
           force: bool = False) -> tuple[int, int]:
    """Write a checklist for every row that has none. Returns (written, failed).

    Takes rows rather than scene ids because the prompt and the addendum are what the
    call needs, and a row is the only place both are recorded as sent. `source` is the
    author's message rather than the body some arm rewrote it into: the file is shared,
    so the half of it that two arms are compared on has to mean the same thing on both.
    """
    todo = [r for r in rows if force or not path(r.scene).is_file()]
    if not todo:
        return 0, 0
    paths.EVAL.mkdir(parents=True, exist_ok=True)
    print(f"extracting {len(todo)} eval checklists via {llm.DEPLOYMENT}", flush=True)

    lock = threading.Lock()
    done = ok = err = 0

    def worker(r) -> None:
        nonlocal done, ok, err
        try:
            resp = extract_one(r.scene, r.prompt, r.addendum)
        except Exception as exc:
            with lock:
                done += 1
                err += 1
                print(f"  [{done}/{len(todo)}] {r.scene}  "
                      f"error:{type(exc).__name__}: {exc}", flush=True)
            return
        out = {
            "scene": r.scene,
            # Which arm's addendum the second half was read out of. The file is shared
            # and the addendum is not, so leaving this off made the provenance of half
            # the list unrecoverable once a second arm rendered the same scene.
            "addendum_from": arm,
            "served_by": llm.served_by(),
            "genre": r.genre,
            "shape": r.shape,
            "preset": r.preset,
            "route": r.route,
            "iso_prompt_len": len(r.iso_prompt),
            "features": resp.get("features", []),
            "excluded": resp.get("excluded", []),
        }
        path(r.scene).write_text(json.dumps(out, indent=2, ensure_ascii=False),
                                 encoding="utf-8")
        with lock:
            done += 1
            ok += 1
            print(f"  [{done}/{len(todo)}] {r.scene}  {len(out['features'])} features, "
                  f"{len(out['excluded'])} excluded", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for _ in pool.map(worker, todo):
            pass
    return ok, err
