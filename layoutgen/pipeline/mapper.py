"""A layout spec, turned into image prompts. No model is called here.

This is stage 4, and its whole value is that it is a pure function. Given the same spec
it emits the same two prompts, byte for byte, so a difference between two runs is a
difference in the spec and can be diffed as one. The judgement all happened upstream in
`layoutgen.model.blob`; what is left is assembly, and assembly is not a thing to ask a
model to do.

The assembly is `pipeline.spec.build`, the same deterministic function every other arm
goes through. A current agent spec carries `initial_scene_subprompt_enriched`: the
context-aware agent's final image-ready description, already containing the visible,
scene-specific realization of its picks. That text becomes the body and is followed by
the canonical Build.md shape and visible-option requirements. Keeping both is deliberate:
the enriched prose provides scene context, while the catalogue addendum guarantees that
no selected layout constraint disappears during enrichment. Older specs without the field
retain the legacy scene-prompt plus catalogue-addendum assembly.

That was not always so. An earlier version of this file composed the body itself out of
the spec's zones, paths and props and never sent the scene prompt at all, which made the
comparison unreadable: the new arm was writing a differently-shaped prompt as well as
choosing differently, so a gap in the images had two causes and no way to separate them.
The spec still carries that decomposition and it is still worth recording - it is what
the blob argued about - but roughly half of it restates the scene prompt in other words,
and the scene prompt is now sent.

The context-aware agent's explicit `render.first` decision controls execution for scenes
that this repository cannot author procedurally. A supported maze or racing route is the
exception: its available generator always wins, because accepting an image-model plan
would discard the topology guarantee the generator exists to provide. Route modifiers
still describe downstream pipeline costs. The three orders are:

    std     text -> isometric -> top-down          the default
    p6      text -> plan -> isometric              the route carries `P6`
    layout  blueprint -> top-down -> isometric     a carveable maze or circuit

`authored_plan` remains constrained by what this repository can actually carve. If an
agent asks for it on a shape with no maze/track generator, execution safely degrades to an
image-model top-down first and records the repair.

The skill explicitly excludes options marked invisible from the enriched paragraph. A
trigger volume or spawn marker is recovered from the render by a later stage, and it
cannot be recovered from a render that drew it. The structured placement rows remain on
the mapper result for that downstream stage.
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
    enriched = (spec.get("initial_scene_subprompt_enriched") or "").strip()
    scene = enriched or (spec.get("scene_prompt") or "").strip()
    notes: list[str] = []
    if not scene:
        # Without it there is no body, and composing one from the decomposition is what
        # this stage stopped doing. Better to say so than to emit a prompt made only of
        # an addendum and a style tail, which renders as a generic scene and looks like
        # a layout failure rather than a missing field.
        notes.append("spec carries no scene_prompt: rebuild it from the self-contained "
                     "agent artifact with `tools/build_agent_arm.py`")

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

    # A supported maze or racing route must be valid by construction. The repository's
    # procedural capability is authoritative here: never let an agent-selected image
    # order bypass a generator that can guarantee the topology.
    requested_order = ORDER.get(wanted, "std")
    if kind:
        order = "layout"
        if requested_order != "layout":
            notes.append(
                f"{kind} generator available; overriding {wanted} with authored_plan"
            )
    elif requested_order == "layout":
        notes.append(
            "authored_plan requested but no maze/track carver exists; using topdown first"
        )
        order = "p6"
    else:
        order = requested_order
    set_piece = set_piece and order != "layout"

    prompt_spec = {
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
    }
    built = sp.build(prompt_spec)

    return {"order": order, "first": FIRST[order],
            "then": {"std": "topdown", "p6": "isometric",
                     "layout": "topdown"}.get(order, "none"),
            "why": render.get("why", ""),
            # Keep the catalogue-derived route and the agent's claimed route separately:
            # order follows `render.first`, while these modifiers drive downstream work.
            "route": route, "claimed_route": list(spec.get("route") or []),
            "wanted": wanted,
            "set": set_piece, "body": scene, "addendum": built["addendum"],
            "prompt_source": (
                "agent_enriched_plus_catalogue"
                if enriched else "scene_plus_catalogue"
            ),
            "withheld": built["withheld"], "kind": built.get("kind"),
            # Carried rather than assembled. Nothing here sites anything - the stage
            # that does runs against a segmented render this function never sees - but
            # a requirement that stops at the spec is one no run row can be scored on.
            "placements": list(spec.get("layout_placement") or []),
            "plan": built.get("plan"), "iso": built["iso"],
            "topdown": built.get("topdown"), "notes": notes}
