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

**If the prompt is silent on theme, emit `null` and add an open question.** Do
not guess. Theme is the cheapest thing to change later and the most obviously
wrong when invented, and a null tells the next step to use a neutral dressing
rather than commit to something the user never said.

### Spatial scale and boundary

The pipeline needs a rough sense of extent to frame a single image. Infer it;
this is the one place where inference is strongly preferred to asking, because
users rarely think in studs.

Anchor to the avatar baseline in `docs/LayoutGen - Build.md` Part I: walk speed
is 16 studs per second, so a 30-second crossing is roughly 500 studs. Pick the
smallest band that fits what was described.

| Band | Roughly | Typical of |
| :---- | :---- | :---- |
| Room | under 100 studs | escape room, single arena, dress-up stage |
| Block | 100–500 studs | most arenas, courses, courts, lobbies |
| District | 500–2000 studs | towns, tycoon plots, raid maps |
| Region | over 2000 studs | open worlds, battle royale, biome maps |

State the band you assumed in the handoff so it can be corrected cheaply. If a
prompt demands something the band cannot hold — a hundred-floor tower in one
top-down — say so plainly and offer the decomposed alternative rather than
accepting an impossible frame.

## 3. Assemble the handoff

Emit the `genre-choice` block with the other concerns added alongside it:

```json
{
  "prompt": "<the user's original text, verbatim>",
  "genre_choice": { ...the block returned by genre-choice, unmodified... },
  "theme": "Post-Apocalyptic",
  "scale": { "band": "block", "assumed": true },
  "open_questions": [
    { "field": "theme", "ask": "No theme was stated — should this be grim and derelict, or bright and stylized?" }
  ]
}
```

- Keep `genre_choice` **unmodified**. Downstream reads it directly, and editing
  it here would put two skills in charge of the same fields.
- `theme` is free text — a string, not an enum. The table above is a starting
  vocabulary. If two themes fit equally, pick one and note the other.
- `assumed: true` marks a value inferred rather than confirmed, so a later step
  knows what is safe to revise.
- `open_questions` is for a **human** — things worth asking that were not worth
  interrupting for. Each entry is `{ "field", "ask" }`, where `field` names the
  key it would fill. `genre_choice.notes` is for the **pipeline** — things a
  later automated step must account for. When unsure, it is a note.

### Offline resolution

Some batch runs have no human available. In that mode, do not silently drop an
open question and do not pretend an automated answer came from the author.
Return the same question; the context-aware layout agent chooses the narrowest
answer grounded in the prompt, records it as `agent_inferred`, and uses it when
writing the enriched image prompt. Real answers already present in the intake
remain `author` and always outrank an inferred default.

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
