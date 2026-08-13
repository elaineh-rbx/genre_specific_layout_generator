"""The front half of the pipeline: message -> scene prompt -> word blob -> spec.

The router this replaces asked the model to fill a schema while it was still deciding,
and the two jobs interfered. A schema field wants a slug; deciding whether a maze has
to be carved wants a sentence. Asked for both at once the model produced slugs that
were individually plausible and jointly incoherent - a shape from one reading of the
prompt beside options from another.

So the decision and its encoding are now separate calls:

    1. uprez     the user's message -> a scene prompt about space and nothing else
    2. describe  that scene prompt -> a word blob, prose, reasoned, IDs named inline
    3. decouple  that blob -> the structured spec, a transcription job

Stage 3 invents nothing. Everything it emits was already decided in stage 2's prose,
which is why it can be a small strict-schema call that either matches the blob or is
wrong in a way a diff will show. The spec it produces is the pipeline's contract, and
`layoutgen.pipeline.mapper` turns it into prompts with no further model involvement.

The instructions for stages 1 and 2 are the skill files under `.cursor/skills`, read
at call time rather than duplicated here, so an agent walking a single scene by hand
and this module running six hundred are following the same document. The option menu
is generated from Build.md through `rules`, so it cannot drift from the tables the
rest of the repo reads.
"""

from __future__ import annotations

import json

from layoutgen import paths
from layoutgen.backends import llm
from layoutgen.model import rules as br
from layoutgen.pipeline.carve import layout_kind

SKILLS = paths.ROOT / ".cursor" / "skills"

ORDERS = ("isometric", "topdown", "authored_plan")
MODIFIERS = ("P0", "P2", "P3", "P4", "P5", "P6", "tiered", "CHECK", "SET")
SCALES = ("small", "medium", "large", "huge")


# ---------------------------------------------------------------- the instructions

def skill(name: str) -> str:
    """A skill's body, YAML front matter stripped.

    The front matter addresses the agent runtime - when to invoke, whether the model
    may pick it up on its own - and none of that is instruction to a model already
    being handed the text.
    """
    text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    return text.strip()


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
    out = [CATALOG_HEADER, "", "## The shape catalogue - pick exactly one, from any genre",
           ""]
    for s in br.SHAPES.values():
        # Which shapes have a generator is a fact this repo holds and the blob was
        # otherwise guessing at - it read "speed run minigame" as not-a-circuit and asked
        # the image model to draw a plan a carver could have guaranteed.
        kind = layout_kind("", s.id, [])
        out.append(f"  `{s.id}` {s.label} — {s.what}"
                   + (f" [{s.pipeline}]" if s.pipeline else "")
                   + (f"  <-- CARVEABLE ({kind}): use `authored_plan`" if kind else ""))
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
            out.append(f"Typical shapes (default `{g.default_shape}`; any catalogue "
                       f"shape is allowed): " + " ".join(f"`{s}`" for s in g.typical))
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
            out.append(f"  `{o.id}` {o.label} — {o.what} ({bits})"
                       + ("  <-- UNIVERSAL: only if the author asked for it"
                          if o.universal else "")
                       + (f"  <-- picking this makes the scene CARVEABLE ({carves}): "
                          f"use `authored_plan`" if carves else ""))
        if g.presets:
            out.append("Presets:")
            for p in g.presets:
                # `Modelled on` names the real game a preset was built from. The
                # interactive skill calls it internal grounding and forbids saying it to a
                # user; it is exactly what lets a prompt describing Brookhaven land on
                # `Life` rather than `Home Builder`, so the deciding stage gets it.
                ref = f"  (modelled on {p.modelled_on})" if notes and p.modelled_on else ""
                out.append(f"  {p.name}: shape=`{p.shape}` "
                           f"options={', '.join(p.options) or '(none)'}{ref}")
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
    out = [f"### {g.name} — no genre names this; it is a place, not a game type",
           "Use this when the prompt describes a space and never implies a game: a lobby, "
           "a farm scene, a hangout, an environment showcase. Naming it is a complete "
           "answer, not a failure to decide. Do not invent a genre to escape it.", ""]
    if notes and g.notes:
        out.append("Notes on No Genre - read before you commit:")
        out += [f"  - {n}" for n in g.notes]
    out.append("Axes (answer these INSTEAD of picking a shape; every default is free):")
    for a in g.axes:
        vals = " | ".join(f"`{v}`" + (" (default)" if v == a.default else
                                      (f" [{a.routes[v]}]" if v in a.routes else ""))
                          for v in a.clauses)
        out.append(f"  `{a.key}`: {vals}")
        out.append(f"       {a.what}")
    out.append("Options (combine freely):")
    for o in g.options:
        bits = f"goes_to={o.goes_to}" + (" core" if o.core else "")
        out.append(f"  `{o.id}` {o.label} — {o.what} ({bits})"
                   + ("  <-- UNIVERSAL: only if the author asked for it"
                      if o.universal else ""))
    out.append("Presets:")
    for p in g.presets:
        ref = f"  (modelled on {p.modelled_on})" if notes and p.modelled_on else ""
        out.append(f"  {p.name}: options={', '.join(p.options)}{ref}")
    out.append("")
    return out


# ---------------------------------------------------------------- 1. uprez

UPREZ_SCHEMA = {
    "name": "uprez", "strict": True,
    "schema": {
        "type": "object",
        "properties": {"initial_scene_subprompt_enriched": {"type": "string"}},
        "required": ["initial_scene_subprompt_enriched"],
        "additionalProperties": False,
    },
}


def clarified(message: str, answers: list[dict] | None = None) -> str:
    """The author's message with their answers to the intake's questions folded in.

    Appended in the author's own voice rather than passed as a second channel, because
    every rule about what to keep and what to drop is written about "the user message",
    and a clarification is that message continued. An answer saying the wilderness should
    take ten minutes to cross is a size; one saying the slice ends when the dungeon is
    cleared is a rule; both need to meet the same filter, and they only do if they arrive
    as the same kind of text.

    Formatted identically to `tools/reclassify_with_answers.enriched_prompt`, which is
    what the router's arm was given, so neither side of the comparison is reading a
    differently-shaped version of the same facts.
    """
    lines = [message.rstrip()]
    said = [a for a in (answers or []) if (a.get("answer") or "").strip()]
    if said:
        lines += ["", "--- clarifications from the author ---"]
        for a in said:
            ask = (a.get("ask") or "").rstrip("?")
            lines.append(f"- [{a.get('field', '?')}] {ask}? {a['answer'].strip()}")
    return "\n".join(lines)


def uprez(message: str, answers: list[dict] | None = None) -> str:
    """The user's message as a scene prompt. Empty string when there is no space.

    `answers` are the intake's open questions as the author resolved them. They are
    optional because not every scene has been through an intake, and a scene without one
    is not a different kind of scene - it is the same call with less to read.
    """
    if not message.strip():
        return ""
    out = llm.ask(skill("uprez-prompt"), clarified(message, answers).strip(),
                  UPREZ_SCHEMA)
    return (out.get("initial_scene_subprompt_enriched") or "").strip()


# ---------------------------------------------------------------- 2. describe

BLOB_SCHEMA = {
    "name": "layout_blob", "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "blob": {
                "type": "string",
                "description": "The word blob: prose covering genre, shape, config "
                               "requirements, layout components, render order, and "
                               "scale/theme/pipeline cost. Canonical IDs in backticks.",
            },
        },
        "required": ["blob"],
        "additionalProperties": False,
    },
}


def describe(scene: str, source: str = "", notes: bool = True) -> str:
    """The word blob. Prose, because this is the call that is actually deciding.

    **One call where `model.router` made three**, and that is a real difference from the
    arm this is compared against rather than a reformatting of it. The router asked for a
    genre against fifteen one-line descriptions, then a preset, then - only if no preset
    fit - a shape and options; each call was blind to the others and the genre could not be
    revisited once `GENRES[...]` had been indexed. This call sees the whole menu while it
    chooses, so it can pick a genre because of the shape it wants, and it treats a preset as
    a starting point to add to and subtract from where the router took one verbatim and
    stopped. That shows up as 100 genres and 169 shapes differing across 613 scenes, and
    as 90% against the upstream agents' tags where the router gets 85%.

    Worth being explicit that the prose format did not require this. Three calls could
    have fed a fourth that wrote the blob, leaving the config identical and only the
    structure changed. Collapsing them was a second, separate decision, kept deliberately
    for the accuracy, at the cost of the arms differing in two ways at once.

    Both texts go in, and the reason is a measured one. Given only the scene prompt this
    stage classified genre from a description that uprez had, correctly, stripped of
    rules, scoring and economy - so a tycoon arrived as a town and an RPG as an
    explorable world. Across 611 scenes the genre flowed systematically out of
    Simulation (-35), RPG (-16) and Entertainment (-15) and into Roleplay (+45) and
    Adventure (+24), and on a sample of high-confidence disagreements showing the
    original message recovered the router's genre in 19 of 40.

    Genre is a fact about the game and layout is a fact about the space, so the stage
    that decides both needs both. Uprez still owns what reaches the image model; this
    only widens what the classifier may read.

    `notes` is here to be turned off by `tools/ablate_notes.py`, not by callers: the
    judgement material it adds is the one part of the menu whose effect is contested, and
    an ablation needs both versions reachable from the same code path.
    """
    if not scene.strip():
        return ""
    system = f"{skill('layout-blob')}\n\n# The menu\n\n{vocabulary(notes=notes)}"
    user = scene.strip()
    if source.strip():
        user = (f"# The author's original message\n\nRead this for genre, intent and any "
                f"stated numbers. It contains rules and mechanics that must NOT reach "
                f"the layout description.\n\n{source.strip()}\n\n"
                f"# The layout scene prompt derived from it\n\nThis is the space to "
                f"describe.\n\n{scene.strip()}")
    return (llm.ask(system, user, BLOB_SCHEMA).get("blob") or "").strip()


# ---------------------------------------------------------------- 3. decouple

def _zone() -> dict:
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "role": {"type": "string", "description": "What happens here."},
            "where": {"type": "string",
                      "description": "Position in the map or in frame: 'north end', "
                                     "'foreground left', 'centre'."},
            "size": {"type": "string",
                     "description": "Relative or stated size. Empty if unstated."},
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
            "kind": {"type": "string",
                     "description": "road, corridor, track, ramp, stair, bridge, "
                                    "portal, tunnel, open ground"},
        },
        "required": ["from", "to", "kind"],
        "additionalProperties": False,
    }


def _prop() -> dict:
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "count": {"type": "integer",
                      "description": "The number the prompt stated. -1 when none was."},
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
            "text": {"type": "string",
                     "description": "What this looks like in THIS scene, from the "
                                    "blob's own wording - not the generic table text."},
            "visible": {"type": "boolean",
                        "description": "True when it is geometry the image model should "
                                       "draw. False for trigger volumes, spawn markers, "
                                       "pickups, emitters - anything placed after "
                                       "segmentation, which must never reach the image."},
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
            "id": {"type": "string",
                   "description": "A canonical option ID whose menu `goes_to` is "
                                  "`layout` or `both`."},
            "text": {"type": "string",
                     "description": "What this is in THIS scene, in English, from the "
                                    "blob's own wording."},
            "count": {"type": "integer", "description": "Stated number, or -1."},
            "where": {"type": "string",
                      "description": "The siting rule: which zone, at what interval, "
                                     "against which piece of geometry."},
        },
        "required": ["id", "text", "count", "where"],
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
            a.key: {"type": "string", "enum": list(a.clauses),
                    "description": f"{a.name}. Default {a.default!r}. {a.what}"}
            for a in br.NO_GENRE.axes
        },
        "required": [a.key for a in br.NO_GENRE.axes],
        "additionalProperties": False,
    }


LAYOUT_SPEC_SCHEMA = {
    "name": "layout_spec", "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "genre": {"type": "string", "enum": list(br.GENRES) + ["No Genre"]},
            "secondary": {"type": "array",
                          "items": {"type": "string", "enum": list(br.GENRES)}},
            "shape": {"type": "string",
                      "description": "Exactly one shape ID from the shared catalogue - "
                                     "any of the 45, not only the genre's typical ones. "
                                     "Empty string for No Genre, and for a described "
                                     "shape, where the axes answer instead."},
            "preset": {"type": "string",
                       "description": "Preset name, or 'none'."},
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
                    "terrain": {"type": "string",
                                "description": "Relief, water, ground material."},
                    "props": {"type": "array", "items": _prop()},
                    "boundary": {"type": "string",
                                 "description": "What encloses the play space, or that "
                                                "it is open."},
                    "scale_band": {"type": "string", "enum": list(SCALES)},
                    "theme": {"type": "string",
                              "description": "The visual register, a few words."},
                },
                "required": ["composition", "zones", "paths", "terrain", "props",
                             "boundary", "scale_band", "theme"],
                "additionalProperties": False,
            },
            "render": {
                "type": "object",
                "properties": {
                    "first": {
                        "type": "string", "enum": list(ORDERS),
                        "description": "Which image is generated FIRST. 'isometric' is "
                                       "the default: look leads, plan projected from it. "
                                       "'topdown' draws the plan first and dresses the "
                                       "isometric from it, when topology must be valid. "
                                       "'authored_plan' means this repo carves the "
                                       "geometry first - mazes and racing circuits.",
                    },
                    "then": {"type": "string", "enum": list(ORDERS) + ["none"],
                             "description": "Which image is generated second."},
                    "authoritative": {
                        "type": "string", "enum": list(ORDERS),
                        "description": "Which image is ground truth for the geometry. "
                                       "Always whichever was generated first.",
                    },
                    "why": {"type": "string",
                            "description": "One clause. The test is whether an invalid "
                                           "layout would make the game unplayable."},
                    "set_piece": {
                        "type": "boolean",
                        "description": "True when the geometry is real but nobody walks "
                                       "on it, so the frame holds the whole set.",
                    },
                },
                "required": ["first", "then", "authoritative", "why", "set_piece"],
                "additionalProperties": False,
            },
            "route": {"type": "array",
                      "items": {"type": "string", "enum": list(MODIFIERS)}},
            "notes": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["genre", "secondary", "shape", "preset", "axes", "options",
                     "layout_placement", "layout", "render", "route", "notes"],
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
2. **Never invent.** Do not add a zone, prop, path or option the blob does not contain.
   An empty array is correct when the blob gave you nothing for it.
3. **Take every canonical ID the blob names in backticks**, provided it appears in the
   menu below. Options belong to the dominant genre; shapes come from the shared
   catalogue and are not restricted by genre. Silently drop an ID that is in neither, and
   say so in `notes`.
4. **`text` on an option comes from the blob's wording for this scene**, not from the
   menu's generic description. That scene-specific phrasing is the whole point of the
   blob and copying the table over it discards it. Put it in **English**: a blob written
   in the prompt's own language still yields English `text`, because these strings are
   appended to the image prompt verbatim and this is the last stage that can keep a
   language the image model cannot read out of the render. Translating is not
   contradicting - hold the meaning exactly and change only the language.
5. **`visible` is the image/layout split.** Geometry the model should draw is `true`.
   Trigger volumes, spawn markers, pickups, emitters and anything else recovered after
   segmentation is `false`. Use the menu's `goes_to` when the blob is silent: `image` is
   true, `layout` is false, `both` is true.
6. **`layout_placement` is the blob's layout-requirements section, transcribed.** Every
   option the blob put there gets a row, and a row also stays in `options` so the picks
   remain one list - the two are the same decision seen from either end, not two
   decisions. `where` is the siting rule the blob gave; leave it an empty string rather
   than inventing one, and say so in `notes`. An option whose menu `goes_to` is `image`
   never belongs here however useful it would be to place.
7. **Carry every number.** A count stated anywhere in the blob goes in the matching
   `count` field. Use `-1` when no number was stated. Never normalise "a few" into a
   number - leave `-1` and keep the words in the text.
8. **`render.authoritative` always equals `render.first`.** The image generated first is
   the one the second is derived from.
9. **`route` holds the modifiers the blob named.** `["P0"]` when it named none.
10. **`render.first` is whichever of the three words the blob wrote, taken literally.**
    The blob writes `isometric`, `topdown` or `authored_plan`. Copy it across. In
    particular `authored_plan` means a blueprint generated in code, which only a maze or
    a racing circuit can be - a blob asking for a **top-down drawn first by the image
    model** is `topdown`, never `authored_plan`, however much its reasoning is about
    getting the plan right first.
11. **`set_piece` and a `SET` in `route` are the same fact.** If the blob argues for
    either, emit both.
12. **`preset` is the name the blob matched**, spelled as the menu spells it, or `none`.
    It is a display name rather than an ID, so it will not be in backticks - take it from
    the prose. Do not infer one from the shape and options when the blob named none: a
    preset the blob did not claim is a decision you would be making, not transcribing.
13. **`axes` carries meaning only when `shape` is empty.** Two builds have no shape ID:
    `No Genre`, and a **described shape** on one of the fifteen, where the blob says the
    catalogue had nothing and describes the space instead. Both answer the five axis
    questions in place of picking a shape, so take each answer the blob stated and leave
    the rest at the default the schema names. Whenever the blob did name a shape, leave
    all five at their defaults: the shape already said what they would say.
14. **A shape ID may come from any genre's usual set.** The catalogue is shared and every
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
    user = (f"# The word blob\n\n{blob.strip()}")
    if scene.strip():
        user = f"{user}\n\n# The scene prompt it was written from\n\n{scene.strip()}"
    spec = llm.ask(system, user, LAYOUT_SPEC_SCHEMA)
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
            notes.append(f"dropped placement {oid!r}: the document draws it "
                         f"(goes_to={o.goes_to}) rather than placing it")
            continue
        if not (p.get("where") or "").strip():
            notes.append(f"placement {oid!r} carries no siting rule")
        rows[oid] = p
        if oid not in picks:
            # A thing to place is still a pick. Only `options` reaches `route_from`, so
            # a placement missing from it is a requirement the route never costed.
            notes.append(f"placement {oid!r} added to options")
            picks[oid] = {"id": oid, "text": p.get("text", ""),
                          "visible": o.goes_to == "both", "count": p.get("count", -1)}

    for oid in list(picks):
        o = g.option(oid)
        if o is None or o.goes_to not in _PLACED or oid in rows:
            continue
        # Something that has to be placed was picked with nothing said about siting it.
        # Mirrored rather than dropped: the requirement is real either way, and a row
        # with an empty `where` is the honest record of a half-made decision.
        notes.append(f"placement mirrored from option {oid!r}: no siting rule given")
        rows[oid] = {"id": oid, "text": picks[oid].get("text", ""),
                     "count": picks[oid].get("count", -1), "where": ""}

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
        moved = [f"{k}={v}" for k, v in (spec.get("axes") or {}).items()
                 if (a := br.NO_GENRE.axis(k)) is not None and v != a.default]
        if moved:
            notes.append(f"cleared axes on a shape build: {', '.join(moved)}")
        spec["axes"] = {}

    if g is not None:
        # A spec written against the per-genre shape tables names ids the shared
        # catalogue absorbed. Renaming beats dropping: the build was decided, and an
        # empty shape would read downstream as a described shape nobody described.
        if (old := spec.get("shape")) and g.shape(old) is None:
            if new := br.SHAPE_MIGRATION.get(old):
                notes.append(f"migrated shape {old!r} -> {new!r}: the catalogue merged it")
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
    want = {"isometric": "topdown", "topdown": "isometric",
            "authored_plan": "topdown"}.get(r.get("first", ""), "none")
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


# ---------------------------------------------------------------- the whole front half

def run(message: str) -> dict:
    """All three stages, with every intermediate kept.

    The intermediates are the point: when a render is wrong, the question is always
    which stage lost it, and that is only answerable if the scene prompt and the blob
    were both written down.
    """
    scene = uprez(message)
    if not scene:
        return {"scene_prompt": "", "blob": "", "spec": None,
                "notes": ["uprez found no describable space"]}
    blob = describe(scene, message)
    if not blob:
        return {"scene_prompt": scene, "blob": "", "spec": None,
                "notes": ["blob stage returned nothing"]}
    return {"scene_prompt": scene, "blob": blob, "spec": decouple(blob, scene),
            "notes": []}


if __name__ == "__main__":
    import sys
    msg = " ".join(sys.argv[1:]) or sys.stdin.read()
    print(json.dumps(run(msg), indent=2))
