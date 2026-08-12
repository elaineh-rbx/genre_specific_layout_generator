"""A layout spec, turned into image prompts. No model is called here.

This is stage 4, and its whole value is that it is a pure function. Given the same spec
it emits the same two prompts, byte for byte, so a difference between two runs is a
difference in the spec and can be diffed as one. The judgement all happened upstream in
`layoutgen.model.blob`; what is left is assembly, and assembly is not a thing to ask a
model to do.

The assembly is `pipeline.spec.build`, the same function every other arm goes through:
the scene prompt is the body and the picked options are rendered into the addendum after
it. This arm therefore differs from the router's arms in *what it decided*, not in how a
decision becomes a prompt, which is the only way the two can be held against each other
and the difference attributed to anything.

That was not always so. An earlier version of this file composed the body itself out of
the spec's zones, paths and props and never sent the scene prompt at all, which made the
comparison unreadable: the new arm was writing a differently-shaped prompt as well as
choosing differently, so a gap in the images had two causes and no way to separate them.
The spec still carries that decomposition and it is still worth recording - it is what
the blob argued about - but roughly half of it restates the scene prompt in other words,
and the scene prompt is now sent.

The order is derived from the route the picks force, exactly as `golden._finish` derives
it for every other arm: a shape or option carrying `P6` has a topology that must be valid
by construction, so the plan is drawn first and the isometric is dressed from it, and a
shape with a generator has its blueprint carved outright. The three orders are the ones
the wrappers in `prompts` already implement:

    std     text -> isometric -> top-down          the default
    p6      text -> plan -> isometric              the route carries `P6`
    layout  blueprint -> top-down -> isometric     a carveable maze or circuit

The spec's own `render.first` is *not* what decides this, though the blob still states it
and it is still recorded. This followed the precedent already set for the route in
`model.handoff`: the block there claims a set of modifiers, `br.route_of` recomputes them
from the picked rows, and the document wins while the claim is kept as a note. Letting the
blob's stated order through instead moved 177 of 613 scenes off look-first, which is a
second difference between the arms on top of who chose the config - and with two
differences at once, a gap in the images has no attributable cause. `render.first` is now
a measurable opinion rather than an instruction: `tools/prompt_similarity.py` can report
how often the blob wanted an order the route did not give it.

Options the spec marked invisible never reach a prompt. A trigger volume or a spawn
marker is recovered from the render by a later stage, and it cannot be recovered from a
render that drew it, so the filter is applied here where both prompts are built rather
than anywhere a caller could forget it.
"""

from __future__ import annotations

from layoutgen.pipeline import spec as sp
from layoutgen.pipeline.carve import layout_kind, track_params

#: `render.first` -> the order name the runners and the results tree already use.
ORDER = {"isometric": "std", "topdown": "p6", "authored_plan": "layout"}
#: The same map inverted, for saying which image the derived order draws first.
FIRST = {v: k for k, v in ORDER.items()}


# ---------------------------------------------------------------- the mapping

def build(spec: dict, *, crossings: int | None = None,
          closed: bool | None = None) -> dict:
    """The spec's two prompts, plus everything a report needs to explain them."""
    render = spec.get("render") or {}
    wanted = render.get("first") or "isometric"
    scene = (spec.get("scene_prompt") or "").strip()
    notes: list[str] = []
    if not scene:
        # Without it there is no body, and composing one from the decomposition is what
        # this stage stopped doing. Better to say so than to emit a prompt made only of
        # an addendum and a style tail, which renders as a generic scene and looks like
        # a layout failure rather than a missing field.
        notes.append("spec carries no scene_prompt: run "
                     "`tools/run_blob_pipeline.py --renormalise` to backfill it")

    picks = [o["id"] for o in spec.get("options") or []]
    # Whether a blueprint can be generated is this repo's fact, not the spec's.
    kind = layout_kind(spec.get("genre", ""), spec.get("shape") or "", picks)

    # The modifiers these picks force, read off the document. `set_piece` is passed in
    # because `SET` is the one modifier the tables cannot produce - it answers whether
    # anybody walks through the space, which is a reading of the prompt rather than a
    # property of a picked row - and it is the same exception `model.handoff` makes.
    set_piece = bool(render.get("set_piece"))
    route = sp.route_from({"genre": spec.get("genre", ""), "shape": spec.get("shape") or "",
                           "options": picks, "axes": spec.get("axes") or {},
                           "set": set_piece})

    # One line, and deliberately the same one `golden._finish` uses, so that order is a
    # function of the picks on every arm and cannot be a reason the images differ.
    order = "layout" if kind else ("p6" if "P6" in route else "std")
    if (asked := ORDER.get(wanted, "std")) != order:
        # Kept as a note rather than obeyed. The blob argued for an order and the argument
        # is worth having on the record - it is the one part of its reasoning the pipeline
        # now declines to act on.
        notes.append(f"blob asked for {wanted} first; the route "
                     f"{route or ['P0']} gives {FIRST[order]}")
    set_piece = set_piece and order != "layout"

    # The shape `pipeline.spec.build` takes, so this arm's prompts come out of the same
    # assembly as every other arm's. `edits` is left empty deliberately: the blob words
    # each option for its own scene, but injecting its wording as well as its picks would
    # be a second difference from the router, and only one difference at a time can be
    # attributed. The wording is still on the spec for anyone who wants to measure it.
    built = sp.build({
        "source": scene,
        "genre": spec.get("genre", ""),
        "shape": spec.get("shape") or "",
        # A No Genre build has no shape, and its axes are what say the thing a shape
        # would have said. `spec.build` already reads them; withholding them here left
        # those scenes with a body and no layout instruction at all.
        "axes": spec.get("axes") or {},
        "options": [o["id"] for o in spec.get("options") or []],
        "edits": {},
        "custom": [],
        "mode": order,
        "kind": kind or "maze",
        "set": set_piece,
        **track_params(spec.get("genre", ""), spec.get("shape") or ""),
        **({"crossings": crossings} if crossings is not None else {}),
        **({"closed": closed} if closed is not None else {}),
        "stageB": True,
    })

    return {"order": order, "first": FIRST[order],
            "then": {"std": "topdown", "p6": "isometric",
                     "layout": "topdown"}.get(order, "none"),
            "why": render.get("why", ""),
            # The document's route, because it is what chose the order. The blob's own
            # claim rides alongside rather than replacing it: the comparison tools read
            # both off the spec, and overwriting either would hide a disagreement.
            "route": route, "claimed_route": list(spec.get("route") or []),
            "wanted": wanted,
            "set": set_piece, "body": scene, "addendum": built["addendum"],
            "withheld": built["withheld"], "kind": built.get("kind"),
            # Carried rather than assembled. Nothing here sites anything - the stage
            # that does runs against a segmented render this function never sees - but
            # a requirement that stops at the spec is one no run row can be scored on.
            "placements": list(spec.get("layout_placement") or []),
            "plan": built.get("plan"), "iso": built["iso"],
            "topdown": built.get("topdown"), "notes": notes}
