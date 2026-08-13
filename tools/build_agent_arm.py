"""Transcribe the subagents' prose blobs into specs through the LLM Gateway.

The subagents write prose per scene into `results/routing/agent_blob/` by reading
`genre-choice`, the selected genre file and `layout-blob`. They are deliberately forbidden
to emit JSON. This script gives that prose to `blob.decouple`, whose strict-schema call
through the LLM Gateway transcribes the already-made decisions into structured JSON. It
then derives render order and assembles the image prompts through the same mapper every
other arm uses.

Two things are deliberately held fixed so that *who chose the config* is the only thing
that moved.

The body is not rewritten. It is lifted from the blob arm's record for the same scene, so
both arms send the same uprezzed paragraph and every difference downstream is a difference
in the picks. Asking the subagents to uprez as well would have moved the body too, and a
gap in the images would then have had two causes and no way to separate them.

The order is derived, not stated. The subagents were not asked which image to draw first
and this does not let them say: it computes the route from the picks and takes the order
that follows, exactly as `mapper.build` and `golden._finish` do. `render.first` is set to
that derived order rather than left to default, purely so `mapper` does not record a
disagreement with an opinion this arm never expressed.

Writes `results/routing/agent_spec_gateway/<scene>.json`, leaving the earlier direct-JSON
experiment intact so the architecture change can be measured rather than overwriting its
baseline.

Usage:
    python tools/build_agent_arm.py
    python tools/build_agent_arm.py --only P0003,P0013
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from layoutgen import paths                                       # noqa: E402
from layoutgen.backends import llm                                # noqa: E402
from layoutgen.model import blob                                  # noqa: E402
from layoutgen.model import rules as br                           # noqa: E402
from layoutgen.pipeline import mapper                             # noqa: E402
from layoutgen.pipeline.carve import layout_kind                  # noqa: E402

IN = paths.ROUTING / "agent_blob"          # prose the subagents wrote
OUT = paths.ROUTING / "agent_spec_gateway" # gateway-transcribed structured arm
BLOB = paths.ROUTING / "blob"         # where the shared body comes from
ANSWERED = paths.ROUTING / "answered"

SKILL = pathlib.Path(__file__).resolve().parent.parent / ".cursor" / "skills" / "genre-choice"
TASK = pathlib.Path(__file__).resolve().parent / "agent_task.md"
LAYOUT_SKILL = pathlib.Path(__file__).resolve().parent.parent / \
    ".cursor" / "skills" / "layout-blob" / "SKILL.md"

def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


#: Canonical genre name, keyed by slug, so `rpg`, `RPG` and `Rpg` all land on one row.
#: The subagents write prose and `br.genre` matches exactly; without this a spelling
#: difference would read downstream as a genre nobody in the catalogue has - and an
#: unresolvable genre skips every check in `normalise`, so the option, preset and shape
#: validation silently stops happening for exactly those scenes.
#:
#: The parenthetical form is indexed as well as the full one. One genre is written
#: `Entertainment (Showcase & Hub)` and an agent that reads it naturally calls it
#: `Entertainment`, which is not a misreading to correct but a name to accept - the same
#: allowance `genre_truth.slug_to_genre` makes for the upstream tags.
_SLUG: dict[str, str] = {}
for _g in list(br.GENRES) + [br.NO_GENRE_NAME]:
    _SLUG[_slug(_g)] = _g
    _SLUG.setdefault(_slug(re.sub(r"\s*\(.*?\)", "", _g)), _g)


def canon_genre(name: str) -> str:
    """The catalogue's spelling of `name`, or `name` untouched if nothing matches."""
    return _SLUG.get(_slug(name), name)


def version() -> str:
    """A hash of the instructions this arm was decided under.

    The same discipline the blob arm's `version()` follows, and for the same reason: the
    subagents read these files at the moment they run, so editing one mid-run splits a
    batch into two instruction sets with nothing on disk to say which scene came from
    which. What goes in is the task brief plus every skill file a subagent is told to
    read - the workflow, the shared shape catalogue, the empty case, and all fifteen
    genre files, since which one gets opened depends on the answer.
    """
    h = hashlib.sha256()
    h.update(TASK.read_bytes())
    h.update(LAYOUT_SKILL.read_bytes())
    h.update(blob.DECOUPLE_SYSTEM.encode())
    h.update(json.dumps(blob.LAYOUT_SPEC_SCHEMA, sort_keys=True).encode())
    for path in [SKILL / "SKILL.md", SKILL / "shapes.md", SKILL / "no-genre.md",
                 *sorted((SKILL / "genres").glob("*.md"))]:
        h.update(path.read_bytes())
    return h.hexdigest()[:12]


def decision(text: str) -> str:
    """The prose decision inside a self-contained agent artifact."""
    marker = "# Agent decision"
    if marker not in text:
        raise ValueError(f"prose artifact has no {marker!r} section")
    out = text.split(marker, 1)[1].strip()
    if not out:
        raise ValueError("agent decision section is empty")
    return out


def build_one(scene: str, prose: str, body: str, source: str,
              said: list[dict]) -> dict:
    """Transcribe one agent's prose and assemble its prompts."""
    prose_decision = decision(prose)
    spec = blob.decouple(prose_decision, body)
    schema_degraded = llm.schema_degraded()
    # The strict schema pins the spelling. Canonicalisation also protects the weaker
    # locally-enforced gateway fallback without asking another model to reinterpret it.
    spec["genre"] = canon_genre(spec.get("genre", ""))
    spec["scene_prompt"] = body
    spec = blob.normalise(spec)

    # The route is the agent's decision, transcribed from prose. Order is a deterministic
    # consequence of that route, as requested: a carveable shape is layout-first, another
    # P6 build is top-down-first, and everything else is isometric-first. This deliberately
    # overrides any order sentence the transcriber copied, so route and order cannot drift.
    kind = layout_kind(spec["genre"], spec.get("shape") or "",
                       [o["id"] for o in spec["options"]])
    route = spec.get("route") or ["P0"]
    order = "layout" if kind else ("p6" if "P6" in route else "std")
    spec["render"]["first"] = mapper.FIRST[order]
    spec["render"]["authoritative"] = mapper.FIRST[order]
    spec = blob.normalise(spec)

    built = mapper.build(spec)
    return {"scene": scene, "source": source, "answers": said,
            "scene_prompt": body, "blob": prose_decision,
            "agent_artifact": prose,
            "agent_notes": prose_decision,
            "secondary": spec.get("secondary") or [],
            "spec": spec, "stage": "done", "status": "ok", "error": "",
            "pipeline_version": version(),
            "served_by": f"subagent/genre-choice -> {llm.served_by()}",
            "schema_degraded": schema_degraded,
            "reused_uprez": True,
            "order": built["order"], "first": built["first"],
            "mapper_notes": built["notes"]}


def process(path: pathlib.Path) -> tuple[str, str, dict | None, str]:
    """Read and transcribe one artifact; safe to run in a worker thread."""
    scene = path.stem
    try:
        prose = path.read_text(encoding="utf-8")
    except OSError as exc:
        return scene, "error", None, f"unreadable: {exc}"

    rec = BLOB / f"{scene}.json"
    old = json.loads(rec.read_text(encoding="utf-8")) if rec.is_file() else {}
    body = (old.get("scene_prompt") or "").strip() if old.get("status") == "ok" else ""
    if not body:
        return scene, "skip", None, "waiting on a body from the blob arm"
    said = [a for a in (old.get("answers") or []) if (a.get("answer") or "").strip()]
    try:
        out = build_one(scene, prose, body, old.get("source", ""), said)
    except Exception as exc:                                      # noqa: BLE001
        return scene, "error", None, f"{type(exc).__name__}: {exc}"
    return scene, "ok", out, ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", default="", help="comma-separated scene ids")
    ap.add_argument("--workers", type=int, default=12,
                    help="concurrent Gateway transcription calls")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    stamp = version()
    print(f"agent-arm instruction version {stamp}")

    built = skipped = failed = degraded = 0
    repairs: dict[str, int] = {}
    inputs = [p for p in sorted(IN.glob("P*.md")) if not only or p.stem in only]
    print(f"transcribing {len(inputs)} prose artifacts with {args.workers} workers")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = pool.map(process, inputs)
        for scene, status, out, detail in results:
            if status == "skip":
                skipped += 1
                continue
            if status == "error" or out is None:
                print(f"  {scene}  {detail}")
                failed += 1
                continue
            for n in out["spec"].get("notes") or []:
                repairs[n.split(":")[0].split("'")[0].strip()] = \
                    repairs.get(n.split(":")[0].split("'")[0].strip(), 0) + 1
            degraded += int(out["schema_degraded"])
            (OUT / f"{scene}.json").write_text(
                json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
            built += 1
            if built % 25 == 0 or built == len(inputs):
                print(f"  {built}/{len(inputs)}", flush=True)

    print(f"\n{built} specs built, {skipped} waiting on a body from the blob arm, "
          f"{failed} failed")
    print(f"{degraded} gateway calls used locally-enforced rather than provider-enforced "
          "JSON schema")
    if repairs:
        print("repairs applied (each is in that spec's notes):")
        for k, n in sorted(repairs.items(), key=lambda kv: -kv[1]):
            print(f"  {n:4}  {k}")
    print(f"specs in {OUT}")


if __name__ == "__main__":
    main()
