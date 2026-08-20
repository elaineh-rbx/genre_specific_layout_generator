"""Render the production ``agent_gateway`` specs.

The Cursor agents have already combined author input, intake answers, and layout choices
into self-contained prose decisions with enriched image-ready bodies.
``tools/build_agent_arm.py`` transcribes those decisions once through the Gateway; this
runner performs deterministic assembly and the two image calls.

Usage:
    python -m layoutgen.pipeline.golden
    python -m layoutgen.pipeline.golden --limit 4
    python -m layoutgen.pipeline.golden --only P0005,P0013
    python -m layoutgen.pipeline.golden \
        --spec-dir results/routing/agent_spec_gateway_scope_reduce_RUN \
        --output-arm agent_gateway_scope_reduce_RUN
"""

from __future__ import annotations

import argparse
import json
import pathlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from layoutgen import paths
from layoutgen.backends import images
from layoutgen.model import rules as br
from layoutgen.pipeline import carve as cv
from layoutgen.pipeline import mapper as mp

GOLDEN = paths.PROMPTS
AGENT_GATEWAY = paths.ROUTING / "agent_spec_gateway"

_lock = threading.Lock()
_done = 0


def _seed(scene: str) -> int:
    """A stable numeric seed for any scene id. Legacy scenes are already numeric;
    upstream scenes carry a `P` prefix that `int(...)` cannot swallow. Stripping
    non-digits keeps the seed deterministic without touching the filenames the
    scene ids are used as."""
    digits = "".join(c for c in scene if c.isdigit())
    return int(digits) if digits else abs(hash(scene)) % (2**31)


def dirs(arm: str) -> tuple:
    """Where one arm's images and run record live."""
    root = paths.SCENES / arm
    return root / "iso", root / "td", root / "plan", paths.RUNS / f"{arm}.jsonl"


@dataclass
class Row:
    scene: str
    title: str
    prompt: str
    genre: str
    preset: str
    shape: str
    shape_label: str
    options: list[str]
    held: list[str]
    extras: list[dict]
    confidence: str
    evidence: str
    route: list[str]
    order: str
    addendum: str
    iso_prompt: str
    td_prompt: str
    prompt_profile: str = "default"
    #: Per-scene option wording and axis answers retained for provenance.
    edits: dict = field(default_factory=dict)
    axes: dict = field(default_factory=dict)
    #: Cursor-agent reasoning and post-segmentation placement requirements.
    placements: list[dict] = field(default_factory=list)
    blob: str = ""
    why: str = ""
    iso: str = ""
    td: str = ""
    plan: str = ""
    layout_steps: int = 0
    status: str = "ok"
    error: str = ""
    seconds: float = 0.0
    _spec: dict = field(default_factory=dict, repr=False)


def _clean(text: str) -> str:
    """Turn the CSV import's literal escape sequences back into real whitespace.

    The upstream P-scene prompts landed in the manifest with `\\n` and `\\t` as
    two characters rather than newlines and tabs (the CSV column held them that
    way). Legacy scenes 0001-0075 already carry real newlines, so this is a
    no-op for them.
    """
    return (text.replace("\\r\\n", "\n").replace("\\n", "\n")
                .replace("\\t", "\t"))


def _english() -> dict[str, str]:
    """The English rendering of each prompt an author did not write in English.

    Written by `tools/translate_sources.py`; absent for the ~90% already in English.

    An entry carrying `rejected` is kept on file but not used. Translation can make
    a prompt's violence legible to the image model's content filter when the
    original slipped past it - "matarla" renders, "kill it" is a 400 - and a scene
    with no image at all is a worse outcome than one built from the author's own
    wording. The entry stays so the next reader knows the translation exists and
    why it is not being sent.
    """
    path = paths.ROUTING / "english.jsonl"
    if not path.is_file():
        return {}
    out = {}
    for line in path.open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        if (t := (r.get("english") or "").strip()) and not r.get("rejected"):
            out[r["scene"]] = t
    return out


def _manifest() -> dict[str, dict]:
    """Every scene's identity and original author prompt.

    The two are separate because they answer different questions. `source_prompt`
    is what the author wrote and is the record of what was asked for; `body` is what
    the image model is given, which for a prompt written in another language is its
    English translation. Sixty-four of these prompts are in Spanish, Portuguese,
    Arabic, Korean and seven other languages, and the wrapper and addendum around
    them are English either way, so sending the original left the one part of the
    prompt that describes the map in a language the rest of it does not use.

    The translation is literal - see `tools/translate_sources.py`. Production rendering
    uses the enriched image-ready field carried by the structured agent spec; this
    manifest remains the source of scene titles and original-prompt provenance.
    """
    english = _english()
    out = {}
    for line in GOLDEN.open():
        if not line.strip():
            continue
        m = json.loads(line)
        m["source_prompt"] = _clean(m.get("source_prompt", ""))
        m["body"] = english.get(m["scene"]) or m["source_prompt"]
        out[m["scene"]] = m
    return out


def agent_rows(specs: pathlib.Path = AGENT_GATEWAY) -> list[Row]:
    """Read Gateway-transcribed Cursor-agent specs and assemble their prompts.

    `mapper.build` uses the agent-enriched prompt when present, recomputes the catalogue
    route for downstream work, and executes the agent's transcribed render order.

    Specs come from ``tools/build_agent_arm.py``. A scene without a successful strict
    transcription is skipped rather than rendered from an incomplete contract.
    """
    manifest = _manifest()
    out: list[Row] = []
    for path in sorted(specs.glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        scene = d.get("scene") or path.stem
        m = manifest.get(scene)
        if m is None:
            print(f"  skipped {scene}: not in manifest")
            continue
        if d.get("status") != "ok" or not d.get("spec"):
            print(f"  skipped {scene}: {d.get('status')} at {d.get('stage')}")
            continue
        spec = d["spec"]
        # `br.genre` rather than `GENRES[...]`: No Genre is a real answer here, worth 7% of
        # prompts by the document's own count, and it is absent from that dict.
        g = br.genre(spec.get("genre", ""))
        shape = g.shape(spec.get("shape") or "") if g else None
        built = mp.build(spec)
        out.append(Row(
            scene=scene, title=m.get("title", ""), prompt=m["source_prompt"],
            genre=spec.get("genre", ""), preset=spec.get("preset") or "none",
            shape=spec.get("shape") or "", shape_label=shape.label if shape else "",
            options=[o["id"] for o in spec.get("options") or []],
            edits={o["id"]: o.get("text", "") for o in spec.get("options") or []
                   if (o.get("text") or "").strip()},
            held=built["withheld"], placements=built["placements"],
            # No extras: every pick this arm makes has a row in the tables. Scene-specific
            # option wording is recorded in `edits` and injected through the canonical
            # addendum, while `extras` remains reserved for uncatalogued freeform picks.
            extras=[],
            confidence="", evidence=built["why"],
            route=built["route"], order=built["order"],
            addendum=built["addendum"],
            iso_prompt=built["iso"] or "",
            td_prompt=(built["plan"] if built["order"] == "p6"
                       else built["topdown"]) or "",
            prompt_profile=built["prompt_profile"],
            blob=d.get("blob", ""), why=built["why"],
            _spec={**spec, "mode": built["order"], "kind": built["kind"] or "maze",
                   **cv.track_params(spec.get("genre", ""), spec.get("shape") or ""),
                   "stageB": True}))
    out.sort(key=lambda x: x.scene)
    return out


SOURCES = {"agent_gateway": agent_rows}


def run_one(row: Row, total: int, redo: bool, arm: str) -> Row:
    global _done
    t0 = time.monotonic()
    ISO, TD, PLAN, _ = dirs(arm)
    iso, td = ISO / f"{row.scene}.png", TD / f"{row.scene}.png"
    try:
        if row.order == "layout":
            # Seeded on the scene, so a rerun reproduces the same layout exactly.
            lay = cv.carve({**row._spec, "cells": 13 if row._spec.get("kind") ==
                            "track" else 12, "seed": _seed(row.scene)})
            plan = PLAN / f"{row.scene}.png"
            plan.write_bytes((paths.OUT / lay["layout"]).read_bytes())
            row.plan = plan.name
            row.layout_steps = lay["steps"]
            if redo or not td.is_file():
                images.generate(row.td_prompt, td, [plan])
            if redo or not iso.is_file():
                images.generate(row.iso_prompt, iso, [td])
        elif row.order == "p6":
            # plan first, then dress the isometric from it
            if redo or not td.is_file():
                images.generate(row.td_prompt, td)
            if redo or not iso.is_file():
                images.generate(row.iso_prompt, iso, [td])
        else:
            if redo or not iso.is_file():
                images.generate(row.iso_prompt, iso)
            if redo or not td.is_file():
                images.generate(row.td_prompt, td, [iso])
        row.iso, row.td = iso.name, td.name
    except Exception as exc:
        row.status, row.error = "error", f"{type(exc).__name__}: {exc}"
    row.seconds = round(time.monotonic() - t0, 1)
    with _lock:
        _done += 1
        flag = "" if row.status == "ok" else "  FAILED"
        print(f"  [{_done}/{total}] {row.scene}  {row.genre} :: {row.preset}"
              f"  ({row.order}, {row.seconds}s){flag}", flush=True)
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arm", default="agent_gateway", choices=sorted(SOURCES),
                    help="which arm's picks to generate from")
    ap.add_argument(
        "--spec-dir",
        type=pathlib.Path,
        default=AGENT_GATEWAY,
        help="Gateway-transcribed spec directory for the agent_gateway arm",
    )
    ap.add_argument(
        "--output-arm",
        default="",
        help="isolated output namespace; defaults to the source arm name",
    )
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="comma-separated scene ids")
    ap.add_argument("--prefix", default="",
                    help="only scenes whose id starts with this")
    ap.add_argument("--redo", action="store_true", help="regenerate existing images")
    ap.add_argument("--no-checklists", action="store_true",
                    help="skip the eval checklists this would otherwise backfill")
    args = ap.parse_args()

    output_arm = args.output_arm or args.arm
    ISO, TD, PLAN, RUN = dirs(output_arm)
    for d in (ISO, TD, PLAN, paths.RUNS):
        d.mkdir(parents=True, exist_ok=True)

    todo = (
        agent_rows(args.spec_dir)
        if args.arm == "agent_gateway"
        else SOURCES[args.arm]()
    )
    if args.only:
        keep = {s.strip() for s in args.only.split(",")}
        todo = [r for r in todo if r.scene in keep]
    if args.prefix:
        todo = [r for r in todo if r.scene.startswith(args.prefix)]
    if args.limit:
        todo = todo[: args.limit]

    from collections import Counter
    by_order = Counter(r.order for r in todo)
    print(f"generating {len(todo)} {args.arm} scenes into {output_arm}  "
          f"({by_order['std']} isometric-first, {by_order['p6']} plan-first, "
          f"{by_order['layout']} authored-layout-first), "
          f"{args.workers} workers", flush=True)
    t0 = time.monotonic()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        done = list(pool.map(
            lambda r: run_one(r, len(todo), args.redo, output_arm), todo))

    done.sort(key=lambda r: r.scene)
    # Merge rather than replace: a --only or --limit run must not drop the scenes it
    # was never asked to touch, whose images are still on disk.
    kept = {}
    if RUN.is_file():
        kept = {d["scene"]: d for line in RUN.open() if line.strip()
                for d in [json.loads(line)]}
    for r in done:
        kept[r.scene] = {k: v for k, v in r.__dict__.items()
                         if not k.startswith("_")}
    with RUN.open("w") as fh:
        for scene in sorted(kept):
            fh.write(json.dumps(kept[scene]) + "\n")

    ok = [r for r in done if r.status == "ok"]
    bad = [r for r in done if r.status != "ok"]
    print(f"\n{len(ok)}/{len(done)} ok in {(time.monotonic()-t0)/60:.1f} min")
    print(f"wrote {RUN}")
    for r in bad:
        print(f"  FAILED {r.scene}: {r.error}")

    if not args.no_checklists:
        # Here rather than left to a separate tool: a scene with images and no checklist
        # is invisible to every score, and the arms that predate the extraction each ran
        # for months before anyone noticed they had none. Only the missing are written,
        # so this is free on a re-render.
        from layoutgen.evaluate import checklist
        checklist.ensure(ok, arm=output_arm, workers=args.workers)

    print("\norder:", dict(Counter(r.order for r in done)))
    print("genres:", dict(Counter(r.genre for r in done).most_common(6)))
    inj = [r for r in done if r.addendum]
    print(f"scenes with an injection: {len(inj)}/{len(done)}  "
          f"(mean {sum(len(r.addendum) for r in inj)//max(len(inj),1)} chars)")


if __name__ == "__main__":
    main()
