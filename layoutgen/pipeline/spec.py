"""A spec is what the playground sends; this turns it into prompts.

    genre    one of the 15 in Build.md's Genre List, or `No Genre`
    shape    exactly one, and almost always the pipeline-routing decision
    axes     what a `No Genre` spec carries instead of a shape: up to five answers,
             each of which costs nothing unless it is the non-default one
    options  any number, each with its own wording, plus anything typed in
    order    isometric first, plan first, or an authored layout first

Options marked `layout` never reach the image model. That is not a preference: a later
stage recovers geometry from the render, and an invisible trigger volume or spawn
marker cannot be recovered, so it is placed against the segmented layout afterwards.
The filter is applied here rather than in the browser, so what is previewed cannot
drift from what is sent.

The route the picks force is read off the document here too, for the same reason. One
of its modifiers changes what is sent: `SET` means the space is looked at rather than
walked through, so the frame holds the whole set and the traversal checks downstream
have nothing to validate.
"""

from __future__ import annotations

import re

import json

from layoutgen import paths
from layoutgen.model import rules as br
from layoutgen.pipeline import prompts
from layoutgen.pipeline.carve import (
    MAZE_OPTIONS, MAZE_SHAPES, TRACK_SHAPES, layout_kind, track_params,
)
from layoutgen.paths import PROMPTS as GOLDEN

#: Precomputed router picks, so a golden prompt opens already configured. Written by
#: `python -m layoutgen.model.router --golden`; missing or stale entries fall back to empty.
CLASSIFIED = paths.ROUTING / "rules.jsonl"

def addendum_from(spec: dict) -> tuple[str, list[str]]:
    """Assemble the addendum, and report which picks were withheld from the image.

    The ``Goes to`` filter is enforced here rather than in the browser, so an option
    that cannot survive segmentation can never reach the image model regardless of
    what the client sends.
    """
    g = br.genre(spec.get("genre", ""))
    if g is None:
        return "", []
    shape = g.shape(spec.get("shape") or "")
    edits = spec.get("edits") or {}
    visibility = spec.get("option_visible") or {}
    bullets, withheld = [], []
    for oid in spec.get("options") or []:
        o = g.option(oid)
        if o is None:
            continue
        destinations = br.option_destinations(g, oid)
        drawn = o.drawn if len(destinations) == 1 else bool(visibility.get(oid))
        if drawn:
            # `both` contributes only its visible part; the rest is placed later.
            bullets.append((o.label,
                            (edits.get(oid) or br.visible_text(g.name, o)).strip()))
        else:
            destination = o.goes_to if len(destinations) == 1 else "layout (explicit)"
            withheld.append(f"{o.label} ({destination})")
    bullets += [("", c.strip()) for c in (spec.get("custom") or []) if c.strip()]
    axis_text = br.axis_lines(g, spec.get("axes") or {})
    return br.render(g.name, shape, bullets, axis_text), withheld


def route_from(spec: dict) -> list[str]:
    """The pipeline modifiers this spec forces, read off the document.

    ``set`` is the exception the document leaves no room to derive: see ``build``.
    """
    g = br.genre(spec.get("genre", ""))
    if g is None:
        return []
    option_ids = spec.get("options") or []
    fixed_options = [
        option_id
        for option_id in option_ids
        if len(br.option_pipelines(g, option_id)) <= 1
    ]
    route = br.route_of(
        g,
        g.shape(spec.get("shape") or ""),
        fixed_options,
        spec.get("axes") or {},
    )
    # A cross-genre option can have different routes for different meanings:
    # a street is P0 while a road that is the course is P6. The structured
    # agent already records that semantic choice in ``claimed_route``. Admit
    # only tags that one of the option's source rows actually allows.
    variable_tags: set[str] = set()
    for option_id in option_ids:
        pipelines = br.option_pipelines(g, option_id)
        if len(pipelines) <= 1:
            continue
        for pipeline in pipelines:
            variable_tags.update(
                re.findall(r"\bP\d\b|\btiered\b|\bCHECK\b|\bSET\b", pipeline or "")
            )
    for tag in spec.get("claimed_route") or []:
        if tag in variable_tags and tag not in route:
            route.append(tag)
    if spec.get("set") and "SET" not in route:
        route.append("SET")
    return route


def build(spec: dict) -> dict:
    add, withheld = addendum_from(spec)
    source = (spec.get("source") or "").strip()
    body = source + (f"\n\n{add}" if add else "")
    mode = spec.get("mode", "std")
    route = route_from(spec)
    # `SET` is orthogonal to the order rather than one of its alternatives: the space
    # is looked at rather than crossed, so the frame holds all of it and the traversal
    # checks downstream have nothing to validate. It cannot apply to an authored maze
    # or track, both of which exist precisely to be moved along.
    #
    # It is also the one modifier a caller may assert, which `route_from` has already
    # folded in. Only `Strategy/board-grid` carries it in a cell, so for every other
    # build it is a judgement about the prompt that no combination of picks can
    # express - and one nothing here could recompute.
    set_piece = "SET" in route and mode != "layout"
    out = {"addendum": add, "withheld": withheld, "route": route, "set": set_piece}
    if mode == "layout":
        kind = layout_kind(spec.get("genre", ""), spec.get("shape") or "",
                           spec.get("options"))
        if kind == "track":
            p = track_params(spec.get("genre", ""), spec.get("shape") or "")
            x = int(spec.get("crossings", p["crossings"]) or 0)
            cl = bool(spec.get("closed", p["closed"]))
            out.update(topdown=prompts.track_topdown(body, x, cl),
                       iso=f"{body}\n\n{prompts.track_isometric(x, cl)}",
                       plan=None, kind="track")
        else:
            out.update(topdown=prompts.maze_topdown(body),
                       iso=f"{body}\n\n{prompts.MAZE_ISO_FROM_TOPDOWN}",
                       plan=None, kind="maze")
    elif mode == "p6":
        out.update(plan=prompts.plan(body),
                   iso=prompts.isometric_from_plan(body, set_piece=set_piece),
                   topdown=None)
    else:
        out.update(iso=prompts.isometric(body, set_piece=set_piece),
                   topdown=prompts.topdown(body), plan=None)
    profile = prompts.profile_name()
    for stage in ("iso", "topdown", "plan"):
        if out.get(stage):
            out[stage] = prompts.for_model(
                out[stage], stage, profile, requirements=add
            )
    out["prompt_profile"] = profile
    return out


# ---------------------------------------------------------------- payloads

def catalog() -> dict:
    genres = []
    descs = dict(br.GENRE_DESCS)
    for g in br.GENRES.values():
        genres.append({
            "name": g.name, "desc": descs.get(g.name, g.tagline), "tagline": g.tagline,
            "route": g.route, "notes": g.notes,
            "shapes": [{"id": s.id, "label": s.label, "name": s.name, "what": s.what,
                        "pipeline": s.pipeline,
                        "maze": (g.name, s.id) in MAZE_SHAPES,
                        "track": (g.name, s.id) in TRACK_SHAPES,
                        **track_params(g.name, s.id)} for s in g.shapes],
            "options": [{"id": o.id, "label": o.label, "name": o.name, "what": o.what,
                         "inject": br.visible_text(g.name, o),
                         "core": o.core, "goes": o.goes_to, "pipeline": o.pipeline,
                         "drawn": o.drawn, "maze": (g.name, o.id) in MAZE_OPTIONS,
                         "shared": br.SHARED_IDS.get(o.id, [])} for o in g.options],
            "presets": [{"name": p.name, "ref": p.modelled_on, "shape": p.shape,
                         "options": p.options} for p in g.presets],
        })

    picks = {}
    if CLASSIFIED.is_file():
        for r in (json.loads(x) for x in CLASSIFIED.open() if x.strip()):
            g = br.GENRES.get(r["genre"])
            if g is None or not g.shape(r["shape"]):
                continue
            held = [o.label for oid in r.get("dropped_options", [])
                    if (o := g.option(oid))]
            picks[r["scene"]] = {
                "genre": r["genre"], "preset": r["preset"], "shape": r["shape"],
                "options": [o for o in r["options"] if g.option(o)],
                "extras": r.get("extras", []), "confidence": r["confidence"],
                "evidence": r["evidence"], "route": r.get("route", []),
                "secondary": r.get("secondary", []), "held": held}

    prompts = []
    if GOLDEN.is_file():
        for m in (json.loads(x) for x in GOLDEN.open() if x.strip()):
            genre = m.get("genre", "")
            prompts.append({"scene": m["scene"], "title": m.get("title", ""),
                            "source": m["source_prompt"],
                            "genre": genre if genre in br.GENRES else "",
                            "defaults": picks.get(m["scene"])})
    return {"genres": genres, "prompts": prompts}


# ---------------------------------------------------------------- layout
