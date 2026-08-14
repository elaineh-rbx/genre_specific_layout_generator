"""Transcribe a Cursor agent's prose decision into the structured layout contract.

The Build Agent already fixed the scene prompt and the Cursor agent already decided the
layout in prose. This module owns the one strict Gateway transcription call plus
deterministic normalisation. It does not rewrite the prompt or decide the layout.

The option menu is generated from Build.md through ``rules``, so it cannot drift from
the tables used by deterministic prompt assembly.
"""

from __future__ import annotations

from layoutgen.backends import llm
from layoutgen.model import rules as br
from layoutgen.pipeline.carve import layout_kind

ORDERS = ("isometric", "topdown", "authored_plan")
MODIFIERS = ("P0", "P2", "P3", "P4", "P5", "P6", "tiered", "CHECK", "SET")
SCALES = ("small", "medium", "large", "huge")


#: The document's own rule about the six universal options, quoted rather than
#: paraphrased. It is here because leaving it out was measurable: with the options listed
#: inline and unmarked, the blob reached for a universal on 40.1% of scenes and used all
#: six, where the upstream agent - reading this paragraph - used one, `building-interior`,
#: on 15.1%. An option the author never asked for is not inert; it is an instruction to
#: the image model.
UNIVERSAL_WARNING = """\
Six options below are marked UNIVERSAL. They are shared across every genre, they are
never `core`, and no preset includes one. A universal option is a **landing place for a
request the author actually made** - never a default and never a suggestion. Each of them
reads as reasonable in almost any prompt, which is exactly why they get picked unasked.
Pick one only when the author named the thing it stands for; an option nobody asked for is
not inert, it is an instruction to the image model."""


#: The document's own rule about the shared catalogue, quoted because the whole point of
#: the shortlist is that it is not a restriction and a paraphrase would blur that.
CATALOG_HEADER = """\
Every shape lives in one catalogue and **every one is reachable from every genre**. What
a genre publishes below is a short list of typical shapes naming a default - the handful
worth putting on screen. That list is presentation and never a restriction: when a prompt
fits none of them, take any other row in the catalogue, and say which one you took and
that it came from outside the genre's usual set.

When the shortlist misses, the shape you want is almost always elsewhere in the catalogue
rather than missing from it. A prompt wanting one large interior finds Simulation assumes
an outdoor shared world and Roleplay's housing shapes are all towns - while
`interior-single` sits in the catalogue the whole time. Look before concluding nothing
fits. A shared catalogue nobody reaches past the first five closes nothing.

A genre may reword any shape: same ID, its genre's own sentence. The route below is the
shape's, wherever it is used from."""


def _catalog_lines() -> list[str]:
    """The 45 shapes, once. Emitted before the genres rather than inside each one.

    They were per-genre until the document made them shared, and rendering them per genre
    afterwards cost 675 lines to say what 45 say - it tripled the menu and, worse, implied
    fifteen separate catalogues at the exact moment the document had merged them into one.
    """
    out = [
        CATALOG_HEADER,
        "",
        "## The shape catalogue - pick exactly one, from any genre",
        "",
    ]
    for s in br.SHAPES.values():
        # Which shapes have a generator is a fact this repo holds and the blob was
        # otherwise guessing at - it read "speed run minigame" as not-a-circuit and asked
        # the image model to draw a plan a carver could have guaranteed.
        kind = layout_kind("", s.id, [])
        out.append(
            f"  `{s.id}` {s.label} — {s.what}"
            + (f" [{s.pipeline}]" if s.pipeline else "")
            + (f"  <-- CARVEABLE ({kind}): use `authored_plan`" if kind else "")
        )
    return out + [""]


def vocabulary(notes: bool = False) -> str:
    """The whole menu - 45 shapes, 15 genres, their options and presets.

    Small enough to hand over in full, which removes the classify-then-load round trip
    the interactive skill needs: a genre cannot be picked here and then have its own
    options turn out to be unavailable.

    `notes` adds the two parts of the document that are judgement rather than vocabulary:
    each genre's notes and the internal `Modelled on` column behind each preset. They are
    optional because only the deciding stage needs them - stage 3 transcribes a decision
    already made, and 7k tokens of guidance it must not act on is a liability there, not
    an asset. The upstream agents this pipeline is measured against read all of it, so
    withholding it from stage 2 was measuring two different documents against each other.
    """
    out = [UNIVERSAL_WARNING, ""] + _catalog_lines()
    for g in br.GENRES.values():
        head = f"### {g.name} — {g.tagline}"
        if g.route:
            head += f"  (genre-wide route: {g.route})"
        out.append(head)
        if notes and g.notes:
            out.append("Notes on this genre - read before you commit:")
            out += [f"  - {n}" for n in g.notes]
        if g.typical:
            out.append(
                f"Typical shapes (default `{g.default_shape}`; any catalogue "
                f"shape is allowed): " + " ".join(f"`{s}`" for s in g.typical)
            )
        # Only where this genre words a catalogue row its own way. The sentence that
        # reaches the image model is the genre's, so a decision made against the
        # catalogue's generic wording would be made against text nobody will send.
        if g.wording:
            out.append("This genre words these its own way:")
            for sid in g.wording:
                if (s := g.shape(sid)) is not None:
                    out.append(f"  `{s.id}` {s.label} — {s.what}")
        out.append("Options (combine freely):")
        for o in g.options:
            bits = f"goes_to={o.goes_to}"
            if o.core:
                bits += " core"
            if o.pipeline:
                bits += f" [{o.pipeline}]"
            carves = layout_kind(g.name, "", [o.id])
            out.append(
                f"  `{o.id}` {o.label} — {o.what} ({bits})"
                + (
                    "  <-- UNIVERSAL: only if the author asked for it"
                    if o.universal
                    else ""
                )
                + (
                    f"  <-- picking this makes the scene CARVEABLE ({carves}): "
                    f"use `authored_plan`"
                    if carves
                    else ""
                )
            )
        if g.presets:
            out.append("Presets:")
            for p in g.presets:
                # `Modelled on` names the real game a preset was built from. The
                # interactive skill calls it internal grounding and forbids saying it to a
                # user; it is exactly what lets a prompt describing Brookhaven land on
                # `Life` rather than `Home Builder`, so the deciding stage gets it.
                ref = (
                    f"  (modelled on {p.modelled_on})" if notes and p.modelled_on else ""
                )
                out.append(
                    f"  {p.name}: shape=`{p.shape}` "
                    f"options={', '.join(p.options) or '(none)'}{ref}"
                )
        out.append("")
    out += _no_genre_menu(notes)
    return "\n".join(out)


def _no_genre_menu(notes: bool) -> list[str]:
    """The sixteenth entry, which is not a genre and is not a fallback either.

    It was missing from this menu entirely while being the upstream agent's answer on 31
    of 614 scenes - 19 `Explorable Place`, 7 `Social Space`, 5 `Open Sandbox` - and the
    document puts it at 7% of prompts. The schema accepted the string `No Genre` the whole
    time, so the effect was worse than a plain absence: a stage could name it and then have
    no vocabulary to spend on it.

    It asks five axis questions where the others offer shapes, and every axis has a default
    that costs nothing, so leaving all five alone is a complete answer.
    """
    g = br.NO_GENRE
    out = [
        f"### {g.name} — no genre names this; it is a place, not a game type",
        "Use this when the prompt describes a space and never implies a game: a lobby, "
        "a farm scene, a hangout, an environment showcase. Naming it is a complete "
        "answer, not a failure to decide. Do not invent a genre to escape it.",
        "",
    ]
    if notes and g.notes:
        out.append("Notes on No Genre - read before you commit:")
        out += [f"  - {n}" for n in g.notes]
    out.append("Axes (answer these INSTEAD of picking a shape; every default is free):")
    for a in g.axes:
        vals = " | ".join(
            f"`{v}`"
            + (
                " (default)"
                if v == a.default
                else (f" [{a.routes[v]}]" if v in a.routes else "")
            )
            for v in a.clauses
        )
        out.append(f"  `{a.key}`: {vals}")
        out.append(f"       {a.what}")
    out.append("Options (combine freely):")
    for o in g.options:
        bits = f"goes_to={o.goes_to}" + (" core" if o.core else "")
        out.append(
            f"  `{o.id}` {o.label} — {o.what} ({bits})"
            + ("  <-- UNIVERSAL: only if the author asked for it" if o.universal else "")
        )
    out.append("Presets:")
    for p in g.presets:
        ref = f"  (modelled on {p.modelled_on})" if notes and p.modelled_on else ""
        out.append(f"  {p.name}: options={', '.join(p.options)}{ref}")
    out.append("")
    return out


# ---------------------------------------------------------------- strict transcription


def _zone() -> dict:
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "role": {"type": "string", "description": "What happens here."},
            "where": {
                "type": "string",
                "description": "Position in the map or in frame: 'north end', "
                "'foreground left', 'centre'.",
            },
            "size": {
                "type": "string",
                "description": "Relative or stated size. Empty if unstated.",
            },
        },
        "required": ["name", "role", "where", "size"],
        "additionalProperties": False,
    }


def _path() -> dict:
    return {
        "type": "object",
        "properties": {
            "from": {"type": "string"},
            "to": {"type": "string"},
            "kind": {
                "type": "string",
                "description": "road, corridor, track, ramp, stair, bridge, "
                "portal, tunnel, open ground",
            },
        },
        "required": ["from", "to", "kind"],
        "additionalProperties": False,
    }


def _prop() -> dict:
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "count": {
                "type": "integer",
                "description": "The number the prompt stated. -1 when none was.",
            },
            "where": {"type": "string"},
        },
        "required": ["name", "count", "where"],
        "additionalProperties": False,
    }


def _option() -> dict:
    return {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "A canonical option ID."},
            "text": {
                "type": "string",
                "description": "What this looks like in THIS scene, from the "
                "blob's own wording - not the generic table text.",
            },
            "visible": {
                "type": "boolean",
                "description": "True when it is geometry the image model should "
                "draw. False for trigger volumes, spawn markers, "
                "pickups, emitters - anything placed after "
                "segmentation, which must never reach the image.",
            },
            "count": {"type": "integer", "description": "Stated number, or -1."},
        },
        "required": ["id", "text", "visible", "count"],
        "additionalProperties": False,
    }


def _placement() -> dict:
    """One thing the layout stage must place, which the image must never show.

    A block of its own rather than a flag on `options` because the two hold different
    facts. An option says the space has checkpoints; a placement says how many and
    against what. `where` is the whole reason it exists - a spawn marker with no rule
    for siting it is a wish rather than an instruction, and the stage that reads this
    runs against the segmented layout with the prompt long gone.
    """
    return {
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "description": "A canonical option ID whose menu `goes_to` is "
                "`layout` or `both`.",
            },
            "text": {
                "type": "string",
                "description": "What this is in THIS scene, in English, from the "
                "blob's own wording.",
            },
            "count": {"type": "integer", "description": "Stated number, or -1."},
            "where": {
                "type": "string",
                "description": "The siting rule: which zone, at what interval, "
                "against which piece of geometry.",
            },
        },
        "required": ["id", "text", "count", "where"],
        "additionalProperties": False,
    }


def _clarification() -> dict:
    """One layout-changing question resolved before the enriched prompt was written."""
    return {
        "type": "object",
        "properties": {
            "field": {
                "type": "string",
                "description": "Short concern key such as scale, shape, theme, or route.",
            },
            "ask": {"type": "string", "description": "The question that was considered."},
            "answer": {
                "type": "string",
                "description": "The answer used to construct the enriched scene prompt.",
            },
            "source": {
                "type": "string",
                "enum": ["author", "agent_inferred"],
                "description": "Whether the author supplied the answer or the offline "
                "agent chose a conservative spatial default.",
            },
        },
        "required": ["field", "ask", "answer", "source"],
        "additionalProperties": False,
    }


def _axes() -> dict:
    """What a spec carries in place of a shape, on the two paths that have no shape ID.

    Those are `No Genre`, which has no catalogue to pick from, and a **described shape**
    on any of the fifteen, which is the document's escape hatch for a prompt the catalogue
    does not cover. The axes are not genre-specific - every 3D game has a value on all
    five - so the same table serves both.

    Every axis is required with its default as a legal value, because a strict schema
    cannot express "only when there is no shape" - so the five arrive on every spec and
    `normalise` drops them where a shape already answered. Defaults cost nothing
    downstream: `route_of` only reads an axis when it is set away from its default.
    """
    return {
        "type": "object",
        "description": "Only meaningful when `shape` is empty - No Genre, or a described "
        "shape the catalogue does not cover. Leave every axis at its "
        "default unless the blob argued for another value.",
        "properties": {
            a.key: {
                "type": "string",
                "enum": list(a.clauses),
                "description": f"{a.name}. Default {a.default!r}. {a.what}",
            }
            for a in br.NO_GENRE.axes
        },
        "required": [a.key for a in br.NO_GENRE.axes],
        "additionalProperties": False,
    }


LAYOUT_SPEC_SCHEMA = {
    "name": "layout_spec",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "clarifications": {
                "type": "array",
                "items": _clarification(),
                "description": "Layout-changing questions and the answers actually used, "
                "including clearly labelled offline agent inferences.",
            },
            "initial_scene_subprompt_enriched": {
                "type": "string",
                "description": "The final image-ready scene paragraph under "
                "'Enriched image prompt', copied verbatim from the blob. "
                "Empty only when the blob contains no buildable space.",
            },
            "genre": {"type": "string", "enum": list(br.GENRES) + ["No Genre"]},
            "secondary": {
                "type": "array",
                "items": {"type": "string", "enum": list(br.GENRES)},
            },
            "shape": {
                "type": "string",
                "description": "Exactly one shape ID from the shared catalogue - "
                "any of the 45, not only the genre's typical ones. "
                "Empty string for No Genre, and for a described "
                "shape, where the axes answer instead.",
            },
            "preset": {"type": "string", "description": "Preset name, or 'none'."},
            "axes": _axes(),
            "options": {"type": "array", "items": _option()},
            "layout_placement": {"type": "array", "items": _placement()},
            "layout": {
                "type": "object",
                "properties": {
                    "composition": {
                        "type": "string",
                        "description": "How the space sits in frame: what is in the "
                        "foreground, midground, background, left, right.",
                    },
                    "zones": {"type": "array", "items": _zone()},
                    "paths": {"type": "array", "items": _path()},
                    "terrain": {
                        "type": "string",
                        "description": "Relief, water, ground material.",
                    },
                    "props": {"type": "array", "items": _prop()},
                    "boundary": {
                        "type": "string",
                        "description": "What encloses the play space, or that "
                        "it is open.",
                    },
                    "scale_band": {"type": "string", "enum": list(SCALES)},
                    "theme": {
                        "type": "string",
                        "description": "The visual register, a few words.",
                    },
                },
                "required": [
                    "composition",
                    "zones",
                    "paths",
                    "terrain",
                    "props",
                    "boundary",
                    "scale_band",
                    "theme",
                ],
                "additionalProperties": False,
            },
            "render": {
                "type": "object",
                "properties": {
                    "first": {
                        "type": "string",
                        "enum": list(ORDERS),
                        "description": "Which image is generated FIRST. 'isometric' is "
                        "the default: look leads, plan projected from it. "
                        "'topdown' draws the plan first and dresses the "
                        "isometric from it, when topology must be valid. "
                        "'authored_plan' means this repo carves the "
                        "geometry first - mazes and racing circuits.",
                    },
                    "then": {
                        "type": "string",
                        "enum": list(ORDERS) + ["none"],
                        "description": "Which image is generated second.",
                    },
                    "authoritative": {
                        "type": "string",
                        "enum": list(ORDERS),
                        "description": "Which image is ground truth for the geometry. "
                        "Always whichever was generated first.",
                    },
                    "why": {
                        "type": "string",
                        "description": "One clause. The test is whether an invalid "
                        "layout would make the game unplayable.",
                    },
                    "set_piece": {
                        "type": "boolean",
                        "description": "True when the geometry is real but nobody walks "
                        "on it, so the frame holds the whole set.",
                    },
                },
                "required": ["first", "then", "authoritative", "why", "set_piece"],
                "additionalProperties": False,
            },
            "route": {
                "type": "array",
                "items": {"type": "string", "enum": list(MODIFIERS)},
            },
            "notes": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "clarifications",
            "initial_scene_subprompt_enriched",
            "genre",
            "secondary",
            "shape",
            "preset",
            "axes",
            "options",
            "layout_placement",
            "layout",
            "render",
            "route",
            "notes",
        ],
        "additionalProperties": False,
    },
}

DECOUPLE_SYSTEM = """\
You transcribe a layout word blob into structured JSON. This is stage 3 of the layout
pipeline.

**You are not deciding anything.** Stage 2 already decided the genre, the shape, the
options, the layout components and the render order, and wrote them down as prose. Your
only job is to move those decisions into fields without changing them.

# Rules

1. **Never contradict the blob.** If it names `world-hub-dungeon`, the shape is
   `world-hub-dungeon`. If it says the isometric is drawn first, `render.first` is
   `isometric`. A field you would rather fill differently is still the blob's call.
   Copy the paragraph under `Enriched image prompt` verbatim into
   `initial_scene_subprompt_enriched`; do not summarize it, replace it with the scene
   prompt, or append catalogue wording.
2. **Copy every row under `Clarifications resolved` into `clarifications`.** Preserve
   whether it is labelled `author` or `agent_inferred`; never report an inferred answer
   as the author's. If the section says none, emit an empty array.
3. **Never invent.** Do not add a zone, prop, path or option the blob does not contain.
   An empty array is correct when the blob gave you nothing for it.
4. **Take every canonical ID the blob names in backticks**, provided it appears in the
   menu below. Options belong to the dominant genre; shapes come from the shared
   catalogue and are not restricted by genre. Silently drop an ID that is in neither, and
   say so in `notes`.
5. **`text` on an option comes from the blob's wording for this scene**, not from the
   menu's generic description. That scene-specific phrasing is the whole point of the
   blob and copying the table over it discards it. Put it in **English**: a blob written
   in the prompt's own language still yields English `text`, because these strings are
   appended to the image prompt verbatim and this is the last stage that can keep a
   language the image model cannot read out of the render. Translating is not
   contradicting - hold the meaning exactly and change only the language.
6. **`visible` is the image/layout split.** Geometry the model should draw is `true`.
   Trigger volumes, spawn markers, pickups, emitters and anything else recovered after
   segmentation is `false`. Use the menu's `goes_to` when the blob is silent: `image` is
   true, `layout` is false, `both` is true.
7. **`layout_placement` is the blob's layout-requirements section, transcribed.** Every
   option the blob put there gets a row, and a row also stays in `options` so the picks
   remain one list - the two are the same decision seen from either end, not two
   decisions. `where` is the siting rule the blob gave; leave it an empty string rather
   than inventing one, and say so in `notes`. An option whose menu `goes_to` is `image`
   never belongs here however useful it would be to place.
8. **Carry every number.** A count stated anywhere in the blob goes in the matching
   `count` field. Use `-1` when no number was stated. Never normalise "a few" into a
   number - leave `-1` and keep the words in the text.
9. **`render.authoritative` always equals `render.first`.** The image generated first is
   the one the second is derived from.
10. **`route` holds the modifiers the blob named.** `["P0"]` when it named none.
11. **`render.first` is whichever of the three words the blob wrote, taken literally.**
    The blob writes `isometric`, `topdown` or `authored_plan`. Copy it across. In
    particular `authored_plan` means a blueprint generated in code, which only a maze or
    a racing circuit can be - a blob asking for a **top-down drawn first by the image
    model** is `topdown`, never `authored_plan`, however much its reasoning is about
    getting the plan right first.
12. **`set_piece` and a `SET` in `route` are the same fact.** If the blob argues for
    either, emit both.
13. **`preset` is the name the blob matched**, spelled as the menu spells it, or `none`.
    It is a display name rather than an ID, so it will not be in backticks - take it from
    the prose. Do not infer one from the shape and options when the blob named none: a
    preset the blob did not claim is a decision you would be making, not transcribing.
14. **`axes` carries meaning only when `shape` is empty.** Two builds have no shape ID:
    `No Genre`, and a **described shape** on one of the fifteen, where the blob says the
    catalogue had nothing and describes the space instead. Both answer the five axis
    questions in place of picking a shape, so take each answer the blob stated and leave
    the rest at the default the schema names. Whenever the blob did name a shape, leave
    all five at their defaults: the shape already said what they would say.
15. **A shape ID may come from any genre's usual set.** The catalogue is shared and every
    row is reachable from every genre, so `interior-single` on a Simulation build is not
    an error to correct - take the ID the blob named. Only drop one that is in no genre.

# Output

Fill the schema. Every field is required; use an empty string or empty array where the
blob genuinely has nothing.
"""


def decouple(blob: str, scene: str = "") -> dict:
    """The blob as the pipeline's structured contract.

    A transcription rather than a judgement, so a mismatch between this and the prose it
    came from is a bug that can be read off the pair rather than a difference of opinion.
    """
    if not blob.strip():
        raise ValueError("nothing to decouple: blob is empty")
    system = f"{DECOUPLE_SYSTEM}\n\n# The menu\n\n{vocabulary()}"
    user = f"# The word blob\n\n{blob.strip()}"
    if scene.strip():
        user = f"{user}\n\n# The scene prompt it was written from\n\n{scene.strip()}"
    # This production handoff must be one schema-enforced call. Do not fall back to
    # extracting JSON from unconstrained prose: a gateway without structured-output
    # support is a hard failure, not a weaker transcription path.
    spec = llm.ask(system, user, LAYOUT_SPEC_SCHEMA, require_schema=True)
    return normalise(spec)


# ---------------------------------------------------------------- validation

#: The two `Goes to` values that mean a pick is sited after segmentation rather than,
#: or as well as, drawn.
_PLACED = ("layout", "both")


def _reconcile_placements(g: br.Genre, spec: dict, notes: list[str]) -> list[dict]:
    """Make `layout_placement`, `options` and the document's `Goes to` agree.

    Three facts have to line up: what the document says a pick is for, whether it is in
    `options`, and whether it has a placement row. Stage 3 can write any two without the
    third, and a missing placement is the one error no render reveals - nothing about a
    picture shows that the checkpoints nobody placed are absent. So the document decides,
    both lists are brought to it, and every correction is a note.
    """
    picks = {o["id"]: o for o in spec.get("options") or []}
    rows: dict[str, dict] = {}
    for p in spec.get("layout_placement") or []:
        oid = p.get("id", "")
        o = g.option(oid)
        if o is None:
            notes.append(f"dropped placement {oid!r}: not in {g.name}")
            continue
        if o.goes_to not in _PLACED:
            notes.append(
                f"dropped placement {oid!r}: the document draws it "
                f"(goes_to={o.goes_to}) rather than placing it"
            )
            continue
        if not (p.get("where") or "").strip():
            notes.append(f"placement {oid!r} carries no siting rule")
        rows[oid] = p
        if oid not in picks:
            # A thing to place is still a pick. Only `options` reaches `route_from`, so
            # a placement missing from it is a requirement the route never costed.
            notes.append(f"placement {oid!r} added to options")
            picks[oid] = {
                "id": oid,
                "text": p.get("text", ""),
                "visible": o.goes_to == "both",
                "count": p.get("count", -1),
            }

    for oid in list(picks):
        o = g.option(oid)
        if o is None or o.goes_to not in _PLACED or oid in rows:
            continue
        # Something that has to be placed was picked with nothing said about siting it.
        # Mirrored rather than dropped: the requirement is real either way, and a row
        # with an empty `where` is the honest record of a half-made decision.
        notes.append(f"placement mirrored from option {oid!r}: no siting rule given")
        rows[oid] = {
            "id": oid,
            "text": picks[oid].get("text", ""),
            "count": picks[oid].get("count", -1),
            "where": "",
        }

    for oid, pick in picks.items():
        o = g.option(oid)
        if o is not None and pick.get("visible") != (drawn := o.goes_to != "layout"):
            notes.append(f"visible on {oid!r} set from goes_to={o.goes_to}")
            pick["visible"] = drawn

    spec["options"] = list(picks.values())
    return [rows[i] for i in picks if i in rows]


def normalise(spec: dict) -> dict:
    """Repair what the schema cannot express, and record every repair in `notes`.

    A strict schema pins types and enums but not the relations between fields: it cannot
    say that a shape must belong to the genre beside it, nor that `authoritative` must
    equal `first`. Those are checked here rather than trusted, and a silent correction
    would be worse than none - the notes are what make a bad stage-3 call visible.
    """
    notes = list(spec.get("notes") or [])
    # Specs produced before the enriched-prompt contract remain readable. They keep the
    # legacy prompt assembly until their agent artifact is regenerated with the new
    # section; Python must not pretend it can author the missing prose.
    spec.setdefault("clarifications", [])
    spec.setdefault("initial_scene_subprompt_enriched", "")
    # Defaulted rather than required so a spec written before this block existed can be
    # renormalised in place: its picks still say what has to be placed.
    spec.setdefault("layout_placement", [])
    g = br.genre(spec.get("genre", ""))

    # Axes and shape are alternatives, not companions: a shape already answers all five,
    # so a shape plus a non-default axis is two answers to one question and the axis would
    # add a pipeline pass the shape never asked for. What decides which is in play is the
    # *shape*, not the genre - the document's described-shape escape hatch answers the
    # axes directly on any of the fifteen when nothing in the catalogue fits, and No Genre
    # is only the case where that is the sole option.
    if spec.get("genre") == br.NO_GENRE_NAME and spec.get("shape"):
        notes.append(f"cleared shape {spec['shape']!r}: No Genre has axes, not shapes")
        spec["shape"] = ""
    if spec.get("shape"):
        moved = [
            f"{k}={v}"
            for k, v in (spec.get("axes") or {}).items()
            if (a := br.NO_GENRE.axis(k)) is not None and v != a.default
        ]
        if moved:
            notes.append(f"cleared axes on a shape build: {', '.join(moved)}")
        spec["axes"] = {}

    if g is not None:
        # A spec written against the per-genre shape tables names ids the shared
        # catalogue absorbed. Renaming beats dropping: the build was decided, and an
        # empty shape would read downstream as a described shape nobody described.
        if (old := spec.get("shape")) and g.shape(old) is None:
            if new := br.SHAPE_MIGRATION.get(old):
                notes.append(
                    f"migrated shape {old!r} -> {new!r}: the catalogue merged it"
                )
                spec["shape"] = new
            else:
                notes.append(f"dropped shape {old!r}: not in the shape catalogue")
                spec["shape"] = ""
        kept = []
        for o in spec.get("options") or []:
            if g.option(o["id"]) is None:
                notes.append(f"dropped option {o['id']!r}: not in {g.name}")
                continue
            kept.append(o)
        spec["options"] = kept
        spec["layout_placement"] = _reconcile_placements(g, spec, notes)
        if spec.get("preset") and spec["preset"] != "none":
            if not any(p.name == spec["preset"] for p in g.presets):
                notes.append(f"unknown preset {spec['preset']!r}")
                spec["preset"] = "none"

    r = spec.setdefault("render", {})
    if r.get("authoritative") != r.get("first"):
        notes.append(f"authoritative {r.get('authoritative')!r} -> {r.get('first')!r}")
        r["authoritative"] = r.get("first")
    # `then` is a consequence of `first` in all three orders, so it is derived rather
    # than believed: an authored plan produces both images from the carve.
    want = {
        "isometric": "topdown",
        "topdown": "isometric",
        "authored_plan": "topdown",
    }.get(r.get("first", ""), "none")
    if r.get("then") != want:
        r["then"] = want
    route = [m for m in (spec.get("route") or []) if m in MODIFIERS]
    # `set_piece` and a `SET` in the route are one fact in two places, and stage 3 can
    # write either without the other - the blob argues for `SET` in prose about the
    # route and the boolean lives in the render block. Reconcile both ways: whichever
    # said it, it was said. Only `mapper` reads the boolean and only reports read the
    # route, so a disagreement is silent until the frame comes back wrong.
    if "SET" in route and not r.get("set_piece"):
        notes.append("set_piece set from SET in route")
        r["set_piece"] = True

    # `SET` says nobody crosses the space; an authored maze or circuit exists to be
    # moved along, so the two cannot both be true.
    if r.get("first") == "authored_plan" and r.get("set_piece"):
        notes.append("set_piece cleared: an authored layout is walked through")
        r["set_piece"] = False
        route = [m for m in route if m != "SET"]

    if r.get("set_piece") and "SET" not in route:
        route.append("SET")
    if not route:
        route = ["P0"]
    spec["route"] = route
    spec["notes"] = notes
    return spec
