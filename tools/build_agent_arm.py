"""Transcribe the subagents' prose blobs into specs through the LLM Gateway.

The subagents write prose per scene into `results/routing/agent_blob/` by reading
`genre-choice`, the selected genre file and `layout-blob`. They are deliberately forbidden
to emit JSON. This script gives that prose to `blob.decouple`, whose strict-schema call
through the LLM Gateway transcribes the already-made decisions into structured JSON. It
then derives render order and assembles the image prompts through the same mapper every
other arm uses.

The prose artifact is self-contained: its ``# Scene prompt`` section is the fixed Build
Agent handoff, and its ``# Agent decision`` section is the Cursor agent's reasoning. This
builder does not read or rerun any historical arm.

The agent records its requested order and route in prose. The transcriber copies both,
then deterministic policy derives the executed order so an arbitrary prose sentence
cannot change rendering behavior.

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

IN = paths.ROUTING / "agent_blob"          # prose the subagents wrote
OUT = paths.ROUTING / "agent_spec_gateway" # gateway-transcribed structured arm
INPUT = paths.ROUTING / "agent_input"       # source + answers used by the agent

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
#: allowance used by the archived upstream-tag evaluation.
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


def artifact(text: str) -> tuple[str, str]:
    """Return the fixed scene prompt and prose decision from one agent artifact."""
    scene_marker = "# Scene prompt"
    decision_marker = "# Agent decision"
    if scene_marker not in text or decision_marker not in text:
        raise ValueError(
            f"prose artifact requires {scene_marker!r} and {decision_marker!r} sections"
        )
    before, out = text.split(decision_marker, 1)
    body = before.split(scene_marker, 1)[1].strip()
    out = out.strip()
    if not out:
        raise ValueError("agent decision section is empty")
    return body, out


def build_one(scene: str, prose: str, body: str, source: str,
              said: list[dict]) -> dict:
    """Transcribe one agent's prose and assemble its prompts."""
    artifact_body, prose_decision = artifact(prose)
    if not artifact_body:
        raise ValueError("scene prompt section is empty")
    if artifact_body != body.strip():
        raise ValueError("agent artifact scene prompt differs from its input record")
    spec = blob.decouple(prose_decision, body)
    schema_degraded = llm.schema_degraded()
    # The provider-enforced schema pins the shape; canonicalisation resolves harmless
    # genre spelling variants without asking another model to reinterpret the decision.
    spec["genre"] = canon_genre(spec.get("genre", ""))
    spec["scene_prompt"] = body
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
            "scene_prompt_source": "agent_artifact",
            "order": built["order"], "first": built["first"],
            "mapper_notes": built["notes"]}


def process(path: pathlib.Path) -> tuple[str, str, dict | None, str]:
    """Read and transcribe one artifact; safe to run in a worker thread."""
    scene = path.stem
    try:
        prose = path.read_text(encoding="utf-8")
    except OSError as exc:
        return scene, "error", None, f"unreadable: {exc}"

    try:
        body, _ = artifact(prose)
        if not body:
            return scene, "skip", None, "agent artifact has no buildable scene prompt"
        input_path = INPUT / f"{scene}.json"
        inp = json.loads(input_path.read_text(encoding="utf-8")) \
            if input_path.is_file() else {}
        input_body = (inp.get("scene_prompt") or "").strip()
        if input_body and input_body != body:
            return scene, "error", None, "artifact scene prompt differs from agent input"
        said = [a for a in (inp.get("answers") or [])
                if (a.get("answer") or "").strip()]
        out = build_one(scene, prose, body, inp.get("source", ""), said)
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
    inputs = [p for p in sorted(IN.glob("*.md")) if not only or p.stem in only]
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

    print(f"\n{built} specs built, {skipped} skipped, {failed} failed")
    print(f"{degraded} gateway calls used locally-enforced rather than provider-enforced "
          "JSON schema")
    if repairs:
        print("repairs applied (each is in that spec's notes):")
        for k, n in sorted(repairs.items(), key=lambda kv: -kv[1]):
            print(f"  {n:4}  {k}")
    print(f"specs in {OUT}")


if __name__ == "__main__":
    main()
