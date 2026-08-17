---
name: layout-intake
description: Entry point for turning a user's game prompt into a LayoutGen build request. Interprets what the user wants, dispatches each concern to its specialist skill, and assembles the combined handoff for the generation pipeline. Use when a user describes a Roblox game, world, or map they want generated, or asks to start a layout build from a prompt.
---

# Layout Intake

The front door of the LayoutGen pipeline. The user writes free text describing
a game; this skill works out what they asked for, routes each **concern** to
whatever handles it, and assembles one handoff.

It decides *what needs interpreting*. It does not interpret genre itself.

## Workflow

```
- [ ] 1. Read the prompt and identify which concerns are in play
- [ ] 2. Dispatch each concern, genre first
- [ ] 3. Assemble the combined handoff
```

## 1. Identify concerns

A prompt ranges from three words to a design essay. Work out which of these it
touches, and note which it leaves silent.

| Concern | Handled by | Status |
| :---- | :---- | :---- |
| **Genre and layout features** | `genre-choice` skill | wired |
| **Visual theme** | inline, below | wired |
| **Spatial scale and boundary** | inline, below | wired |
| *(future concerns)* | see Extension point | — |

Genre is always in play, even when the answer is "no genre." Run it first: it
determines the pipeline route, and the other concerns are cheap by comparison.

## 2. Dispatch

### Genre and layout features

Read `.cursor/skills/genre-choice/SKILL.md` and follow it. It returns a JSON
block containing the genre, the shape, the picked options split into image and
layout streams, and the pipeline route.

If its `pipeline` is `["P5"]` there is no map to build. Skip the remaining
concerns, emit the handoff with `theme` and `scale` as `null`, and tell the
user in plain language why — the reason is in `genre_choice.notes`.

### Visual theme

Theme is set dressing layered over the layout — it never changes the route.
Infer it from the prompt where possible and only ask if the prompt is silent
*and* the user seems to care.

| Theme | Reads as |
| :---- | :---- |
| Sci-Fi / Cyberpunk | Neon lighting, metallic surfaces, industrial tech |
| High Fantasy | Stone, wood, torches, natural landscapes, glowing magic |
| Modern Urban | Asphalt, concrete, contemporary street props |
| Post-Apocalyptic | Overgrown foliage, rusted metal, debris, broken structures |
| Horror | Dim lighting, heavy fog, aged wood, distressed textures |
| Stylized / Toon | Oversaturated colors, soft lighting, playful oversized assets |

A prompt may describe a theme outside this list. Take it as written rather than
forcing the nearest match — the list is a starting vocabulary, not a constraint.

**A prompt that never mentions a look can still settle one.** "Swing around the
city" is Modern Urban; "a copy of prison life" is a prison, concrete and chain
link, whatever else is unresolved about it. Naming a place, a setting or a real
game is a theme statement made in different words, and reading it is the job —
`null` is for a prompt where nothing at all points at a look, not for one that
merely avoids the word.

**When you read it rather than being told it, mark it `assumed`** — the same
flag `scale` carries — so a later step knows it can be corrected cheaply and
does not mistake your inference for the user's own words.

**Emit `null` and ask only when nothing in the prompt points anywhere.** Do not
invent one then. Theme is the most obviously wrong thing to make up, and a null
tells the next step to use neutral dressing rather than commit to something
nothing in the prompt supports.

### Spatial scale and boundary

The pipeline frames the whole map in a **single isometric render**, so extent
and detail are the same budget spent twice. **Scaling out does not get you a
bigger picture — it gets you the same picture holding less.** A region-scale
request does not come back as a detailed world; it comes back as coastlines.

So what decides the band is not how big the user says the world is. It is **the
smallest thing they need to be able to pick out**, which is also the thing they
can actually answer.

Infer it when the prompt makes it obvious. An escape room means furniture; a
racing circuit means the track and its barriers; "an open world with four
biomes" means terrain.

**Most prompts name neither an extent nor its contents, and Block is the
default.** It is where most arenas, courses and lobbies land. Ship it marked
`assumed` rather than treating silence as a reason to say nothing.

**Spend a question when a different band would be built differently.** Not
whenever the prompt is silent — that is most of them — but when the choice is
live and you cannot settle it. "A 3d wasteland desert" is one: dunes you walk
between and a desert you see the horizon of are different maps. A hide-and-seek
game is another, and it shows the trap in *the detail wins*: the props you hide
behind are Room-sized, but nobody plays hide and seek in one room. **When the
smallest thing points somewhere the game plainly cannot fit, the game wins and
the band is worth asking about.**

| Smallest thing that matters | Band | Roughly | Typical of |
| :---- | :---- | :---- | :---- |
| furniture, props, clutter you interact with | Room | under 100 studs | escape room, single arena, dress-up stage |
| buildings, cars, street lights, doorways | Block | 100–500 studs | most arenas, courses, courts, lobbies |
| blocks and main roads, not individual cars | District | 500–2000 studs | towns, tycoon plots, raid maps |
| coastlines, forests, mountain ranges | Region | over 2000 studs | open worlds, battle royale, biome maps |

**Ask it closed, never open.** The field holds exactly four values, and asked in
the open it collects answers none of them can hold — one prompt answered *5,000
square kilometres*, another *a trillion blocks*, and both cost a second round
trip to negotiate back down.

> What's the smallest thing you want to be able to make out — furniture inside
> rooms, individual buildings and street lights, city blocks and main roads, or
> coastlines and forests?

The avatar baseline in `docs/LayoutGen - Build.md` Part I is the cross-check:
walk speed is 16 studs per second, so a 30-second crossing is roughly 500 studs.
If the stated extent and the required detail disagree, **the detail wins** — it
is the half the user will notice is missing.

State the band you assumed in the handoff so it can be corrected cheaply.

**When extent and detail cannot both be honoured, say so and offer the split.**
A user wanting street lights across a whole continent is asking for two frames'
worth of information in one, and we cannot build that today. Offer the detailed
part now with the remainder as separate maps (`P4`), and record the deferral in
`genre_choice.notes`. **The same rule applies vertically** and always did: a
hundred-floor tower in one top-down cannot be framed either. Say so plainly and
offer the decomposed alternative rather than accepting an impossible frame.

## 3. Assemble the handoff

Emit the `genre-choice` block with the other concerns added alongside it:

```json
{
  "prompt": "<the user's original text, verbatim>",
  "genre_choice": { ...the block returned by genre-choice, unmodified... },
  "theme": "Post-Apocalyptic",
  "theme_assumed": true,
  "scale": { "band": "block", "assumed": true },
  "constraints": [
    { "kind": "fidelity", "text": "hyper realistic, as much detail as possible" },
    { "kind": "build_rule", "text": "make sure it's not on a baseplate" }
  ],
  "open_questions": [
    { "field": "scale", "ask": "What's the smallest thing you want to be able to make out — furniture inside rooms, individual buildings and street lights, city blocks and main roads, or coastlines and forests?" }
  ]
}
```

- Keep `genre_choice` **unmodified**. Downstream reads it directly, and editing
  it here would put two skills in charge of the same fields.
- `theme` is free text — a string, not an enum. The table above is a starting
  vocabulary. If two themes fit equally, pick one and note the other.
- **`theme` is a setting, never a rendering style.** "Hyper realistic", "cel
  shaded", "as much detail as possible" say how the build should be rendered,
  not where it is. Putting them in `theme` is the commonest misfiling there is,
  and it is silently wrong: downstream reads `theme` as a place, so "hyper
  realistic" arrives as a description of a location. They are `constraints`.
- `constraints` holds rules over the **whole build** — things the prompt says
  about how it must come out rather than what is in it. Omit the key entirely
  when there are none, which is the common case. Three kinds:

  | `kind` | For | Example from a real prompt |
  | :---- | :---- | :---- |
  | `fidelity` | How detailed or realistic the result must be | "hyper realistic", "many details" |
  | `build_rule` | A hard requirement or prohibition over everything | "make sure it's not on a baseplate", "do NOT expand the scope" |
  | `reference` | An existing game named as the specification | "an exact replica of the first sea in Blox Fruits" |

  Keep the user's own words in `text`. These are the one part of a prompt that
  cannot be expressed by adding something to the build — a constraint says what
  must *not* happen, or how, and every other field in this handoff is additive.
  A prompt that spends a third of its words on prohibitions has said something
  important, and before this field existed the only way to record it was to
  leave something out, which no downstream reader can detect.
- `genre_choice.segments` carries the per-space breakdown when the prompt named
  more than one space. It belongs to genre-choice and you pass it through
  untouched like the rest of the block; a per-space theme lives inside it,
  because a three-floor tower with a different look per floor cannot be
  described by the single top-level `theme`.
- `assumed: true` marks a value inferred rather than confirmed, so a later step
  knows what is safe to revise. `theme` stays a plain string because downstream
  reads it as one, so its flag sits beside it as `theme_assumed` — set it
  whenever you read the theme off a setting or a named game rather than off the
  user's own description of the look. Omit it when they described it.
- `open_questions` is for a **human** — things worth asking that were not worth
  interrupting for. Each entry is `{ "field", "ask" }`, where `field` names the
  key it would fill. `genre_choice.notes` is for the **pipeline** — things a
  later automated step must account for. When unsure, it is a note.
- **Spend the first question on genre or shape whenever either is unresolved.**
  They are not one concern among several: every later decision branches off
  them, and a question about an option is worth little if the genre it came
  from is a guess. Options and theme compete for whatever is left. A prompt with
  no genre and no shape may ask five rather than four — that is the one case
  where the cap moves, because the alternative is answering neither.
- **A prompt can refuse questions, and that refusal is binding.** "Make any
  reasonable creative decisions yourself", "DO NOT ASK ANY QUESTIONS JUST
  COMPLETE" — emit `open_questions: []`, take the default each rule points to,
  and mark what you inferred with the `assumed` flags that already exist. The
  flags are the whole answer here: they let a later step see every call you made
  on the user's behalf without asking them anything, which is exactly what they
  requested.
- `genre_choice.mechanics` is for **neither**: it is the gameplay the prompt
  asked for — scoring, currency, rounds, progression, controls, UI — routed to
  the stream that owns it. Pass it through untouched, do not turn its entries
  into `open_questions`, and do not read a full `mechanics` array as a sign the
  prompt was poorly served. It usually means the opposite.

## Extension point

Add a concern by giving it a row in the table in step 1, a section in step 2,
and a key in the handoff. Two rules keep this from tangling:

1. **One concern owns each field.** If a new concern wants to change the
   pipeline route, it does not edit `genre_choice.pipeline` — it adds its own
   modifier at the top level and lets the pipeline take the union.
2. **Concerns do not read each other's skills.** They return blocks to this
   skill, which is the only place that sees all of them.

**Goal / win-or-loop condition is deliberately not a concern here, and you must
not ask about it.** A win condition is gameplay, not layout — identical maps
carry different ones — so nothing downstream can use the answer.

Its one layout-bearing part, **the place the run ends**, belongs to
`genre-choice`: it is inferred from the genre and emitted as a shape or an
option, never asked. See that skill's step 4.

That split generalizes, and `genre-choice` step 0 applies it to the whole
prompt: a gameplay rule is not layout, but **the place the rule needs is**. "You
win by reaching the exit" is not a concern here; the exit is.
