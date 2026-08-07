"""Turn a genre-choice handoff into the spec the pipeline runs on.

`.cursor/skills/genre-choice/` is a router with a person in the loop: it classifies the
prompt, offers the genre's menu, and emits its picks split into an image stream and a
layout stream. `model/router.py` answers the same question in two LLM calls and no
conversation. Both end at a genre, one shape and some options, so both can feed
`pipeline.spec.build` - this is the translation for the first one.

What it will not do is take the block at its word. The block is prose-shaped output
from an agent, not a validated payload, and two of its fields have already been seen
wrong: `pipeline` arrived as `["P0 + tiered"]` on one scene, a single string where a
list of modifiers belongs, and as a resolved subset on another where the document's
own cell is conditional. So every ID is checked against the parsed tables, the split
is checked against `Goes to`, and the route is recomputed. Disagreements are returned
rather than raised - a block that gets the shape right and the route wrong is still
worth generating from, and the disagreement is the interesting part.

The one thing the skill has that the router does not is per-option text written for
this scene. `path-road-vehicle` renders as "Vehicle-width roads between extraction
ground and processing structures" for every prompt that picks it; the skill wrote
"winding roads at least 20 studs wide, switchbacking up the terraces" for a mountain.
That lands in ``edits``, which the pipeline already honours.

Usage:
    python -m layoutgen.model.handoff results/routing/skill/0003.json
    python -m layoutgen.model.handoff block.json --scene 0001 --drop-free-text
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
from dataclasses import dataclass, field

from layoutgen.model import rules as br
from layoutgen.paths import PROMPTS as GOLDEN


def slug(title: str) -> str:
    """'Entertainment (Showcase & Hub)' -> 'entertainment', matching the skill's files."""
    return re.sub(r"[^a-z0-9]+", "-", title.split("(")[0].lower()).strip("-")


#: The skill names genres by the filename it loaded; the document names them in full.
GENRE_BY_SLUG = {slug(name): name for name in br.GENRES}

#: Problems that mean there is no spec to build. Everything else is worth reporting
#: and generating anyway.
FATAL = {"no-genre", "unknown-genre", "unknown-shape", "p5"}


@dataclass
class Problem:
    kind: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.kind}] {self.detail}"


@dataclass
class Handoff:
    """One adapted block: what to generate, and everything that did not add up."""

    spec: dict = field(default_factory=dict)
    genre: str = ""
    preset: str = ""
    options: list[str] = field(default_factory=list)
    route: list[str] = field(default_factory=list)      #: recomputed here
    claimed_route: list[str] = field(default_factory=list)   #: what the block said
    free_text: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    problems: list[Problem] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(p.kind in FATAL for p in self.problems)

    def add(self, kind: str, detail: str) -> None:
        self.problems.append(Problem(kind, detail))


def _rows(block: dict, key: str) -> list[dict]:
    return [e for e in (block.get(key) or []) if isinstance(e, dict)]


def _modifiers(claimed: list) -> list[str]:
    """Split however the block wrote its route into individual modifiers.

    The field is meant to be a list of them. It has also arrived as `["P0 + tiered"]`,
    one string holding two - which would otherwise diff as a whole modifier added and
    another dropped, rather than as the single `tiered` that actually differs.
    """
    out: list[str] = []
    for part in claimed:
        for m in re.split(r"[+,]", str(part)):
            if (m := m.strip()) and m not in out:
                out.append(m)
    return out


def _sentence(text: str) -> str:
    """End on punctuation. Every line in the document does, and the prompt builder
    appends the camera wording straight after the last bullet - so a tailored line
    without a full stop runs into "Polished square Roblox-like..." mid-sentence."""
    text = text.strip()
    return text if not text or text[-1] in ".!?:;" else text + "."


def _ids(rows: list[dict]) -> list[str]:
    seen: list[str] = []
    for e in rows:
        oid = e.get("id")
        if oid and oid not in seen:
            seen.append(oid)
    return seen


def adapt(block: dict, source: str = "", keep_free_text: bool = True) -> Handoff:
    """Adapt one emitted block. Never raises on bad content; see ``.problems``."""
    h = Handoff(claimed_route=_modifiers(block.get("pipeline") or []),
                notes=list(block.get("notes") or []))

    genres = block.get("genres") or []
    if not genres:
        # The skill's two special cases. Both are real answers, neither is a spec:
        # P5 says there is no space to build, no-genre says there is one but no
        # genre file describes it, and the shape then lives in five axes instead.
        kind = "p5" if "P5" in h.claimed_route else "no-genre"
        h.add(kind, "the block names no genre, so there is no shape table to build from")
        return h

    name = GENRE_BY_SLUG.get(genres[0])
    if name is None:
        h.add("unknown-genre", f"{genres[0]!r} is not one of the {len(br.GENRES)} genres")
        return h
    g = br.GENRES[name]
    h.genre = name
    if len(genres) > 1:
        h.notes.append("secondary genres named: " + ", ".join(genres[1:]))

    sh = block.get("shape") or {}
    shape_id = sh.get("id") if isinstance(sh, dict) else None
    shape = g.shape(shape_id or "")
    if shape is None:
        h.add("unknown-shape", f"{shape_id!r} is not a shape of {name}")
        return h

    image, layout = _rows(block, "image_prompt"), _rows(block, "layout_placement")
    in_image, in_layout = _ids(image), _ids(layout)

    picks: list[str] = []
    for oid in in_image + [o for o in in_layout if o not in in_image]:
        if g.option(oid) is None:
            h.add("unknown-option", f"{oid!r} is not an option of {name}, dropped")
            continue
        picks.append(oid)
    h.options = picks

    # The skill performs its own image/layout split; the server does the same from the
    # document's `Goes to`. They should agree, and where they do not the document wins
    # - the filter in `pipeline.spec` is what actually runs.
    for oid in picks:
        o = g.option(oid)
        here = (oid in in_image, oid in in_layout)
        want = {"image": (True, False), "layout": (False, True), "both": (True, True)}
        expect = want.get(o.goes_to)
        if expect and here != expect:
            h.add("goes-to", f"{oid} is `{o.goes_to}` but the block put it in "
                             f"{'image' if here[0] else ''}{'+' if all(here) else ''}"
                             f"{'layout' if here[1] else ''} only")

    preset = block.get("preset")
    if preset:
        p = g.preset(preset)
        if p is None:
            h.add("unknown-preset", f"{preset!r} is not a preset of {name}")
        else:
            h.preset = p.name
            added = [o for o in picks if o not in p.options]
            gone = [o for o in p.options if o not in picks]
            if added:
                h.notes.append("added to the preset: " + ", ".join(added))
            if gone:
                h.notes.append("dropped from the preset: " + ", ".join(gone))

    h.route = br.route_of(g, shape, picks)
    if h.claimed_route and h.claimed_route != h.route:
        # Which way it differs is the useful part. A modifier the block invented is a
        # judgement it made about the scene that no picked row carries; one it left out
        # is usually a conditional cell it resolved and `route_of` did not.
        gained = [m for m in h.claimed_route if m not in h.route]
        lost = [m for m in h.route if m not in h.claimed_route]
        h.add("route", f"block said {h.claimed_route}, document gives {h.route}"
                       + (f"; block added {gained}" if gained else "")
                       + (f"; block dropped {lost}" if lost else ""))

    # Free text the skill could not map to an option. It reaches the image as its own
    # bullet - but the source prompt is sent in full alongside, so anything here that
    # merely restates the prompt is duplication rather than instruction.
    h.free_text = [_sentence(e["text"]) for e in image
                   if not e.get("id") and (e.get("text") or "").strip()]

    edits = {}
    for e in image:
        oid, text = e.get("id"), _sentence(e.get("text") or "")
        if oid in picks and text:
            edits[oid] = text          # the image half, for a `both` option
    for e in layout:
        oid, text = e.get("id"), _sentence(e.get("text") or "")
        if oid in picks and oid not in edits and text:
            edits[oid] = text

    h.spec = {
        "genre": name,
        "shape": shape.id,
        "options": picks,
        "edits": edits,
        "custom": list(h.free_text) if keep_free_text else [],
        "mode": "p6" if "P6" in h.route else "std",
        "source": source,
    }
    return h


def load(path: pathlib.Path) -> tuple[dict, str, str]:
    """Accept a bare emitted block, or one wrapped with its scene and source prompt."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if "block" in raw:
        return raw["block"], raw.get("source", ""), raw.get("scene", "")
    return raw, raw.get("source", ""), raw.get("scene", "")


def golden_source(scene: str) -> str:
    if not GOLDEN.is_file():
        return ""
    for line in GOLDEN.open():
        if line.strip():
            row = json.loads(line)
            if row["scene"] == scene:
                return row["source_prompt"]
    return ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=pathlib.Path, help="the emitted JSON block")
    ap.add_argument("--scene", default="", help="take the source prompt from the golden set")
    ap.add_argument("--drop-free-text", action="store_true",
                    help="withhold the id-less entries, which the source prompt may cover")
    args = ap.parse_args()

    block, source, scene = load(args.path)
    scene = args.scene or scene
    source = golden_source(scene) if scene and not source else source

    h = adapt(block, source=source, keep_free_text=not args.drop_free_text)
    print(f"genre     {h.genre or '(none)'}")
    print(f"preset    {h.preset or 'none'}")
    print(f"shape     {h.spec.get('shape', '(none)')}")
    print(f"options   {', '.join(h.options) or '(none)'}")
    print(f"route     {' + '.join(h.route) or '(none)'}"
          + (f"   [block said {' + '.join(h.claimed_route)}]"
             if h.claimed_route and h.claimed_route != h.route else ""))
    print(f"mode      {h.spec.get('mode', '-')}")
    print(f"tailored  {len(h.spec.get('edits', {}))} of {len(h.options)} options rewritten")
    print(f"free text {len(h.free_text)} entries with no option")

    if h.problems:
        print(f"\nproblems ({len(h.problems)}):")
        for p in h.problems:
            print(f"  {p}")
    if h.notes:
        print(f"\nnotes ({len(h.notes)}):")
        for n in h.notes:
            print(f"  - {n}")

    if not h.ok:
        print("\nnothing to generate from this block")
        return

    from layoutgen.pipeline.spec import addendum_from
    add, withheld = addendum_from(h.spec)
    print("\n--- addendum this would inject ---\n" + (add or "(nothing)"))
    if withheld:
        print("\nwithheld from the image model: " + ", ".join(withheld))

    generic, _ = addendum_from({**h.spec, "edits": {}, "custom": []})
    if generic != add:
        print("\n--- the same picks with the document's own wording ---\n" + generic)


if __name__ == "__main__":
    main()
