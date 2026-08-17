---
name: layout-blob
description: Turns a raw author message and intake answers into a self-contained prose decision containing the enriched image-ready scene body, genre, shape, config requirements, placement requirements, layout components, and render order. Use before the decoupler that structures the decision into JSON.
disable-model-invocation: true
---

# Layout Blob

You read the **author's original message** and their **intake answers**, then write
a **word blob**: prose that states everything the pipeline needs to decide, in
the order it needs to decide it.

## Inputs

The original message and intake answers are the only scene inputs. Do not expect
or create a separate cleaned brief before this decision.

| Read this | For |
| :---- | :---- |
| The author's original message | **Genre**, intent, stated numbers, and the raw spatial request. Its rules, economy, and scoring are strong genre signals. |
| Intake answers | Authoritative resolutions of layout-changing ambiguities. They override conflicting details in the original message. |

**Classify and extract the space from the original message, then apply the
answers.** Use `uprez-prompt` as guidance while writing section 2 inside this
same decision; it is not a separate generated input.

**But never let the mechanics into the layout.** The original message tells you
both what kind of game this is and what space the author requested. Nothing that
is only a rule, score, currency, UI flow, or script belongs in your layout
components — only geometry does.

Triage twice: first separate geometry stated outright, geometry implied by a
rule, and non-scene mechanics; then repeat after choosing the genre. "Reach the
exit to win" is a mechanic whose exit is still geometry. Currency and scoring
remain outside the layout unless they require a physical place.

Keep whole-build constraints active while writing the scene. Fidelity requests,
hard build rules and reference/adaptation requirements are not layout options,
but visible constraints such as "no baseplate" or "photorealistic" must still
govern the enriched image prompt. Preserve prohibitions instead of turning them
into extra objects.

**Write prose, not JSON.** A later stage decouples this blob into structured
JSON, and it does that job better than you would do it inline. Your job is to
*reason correctly and say so plainly*. Reaching for a schema here costs you the
reasoning.

**But name canonical IDs inline, in backticks.** The blob is prose that a
machine reads. When you mean a specific genre, shape or option from the menu
below, write its ID in backticks — `` `world-hub-dungeon` ``, `` `safezone-town`
`` — so the decoupler can bind it without guessing. Prose around the IDs is
where the scene-specific detail goes.

## What the blob must cover

Cover all nine, in this order, as flowing prose with a short heading per section.

### 1. Clarifications resolved

Use the exact heading `## Clarifications resolved`. Start with any real intake
questions and answers supplied in the input, marking each one `[author]`. Copy
their `field`, `ask`, and `answer` text verbatim, without translating,
paraphrasing, shortening, or renaming it.

Then use `layout-intake` and the loaded genre material to identify only unanswered
ambiguities whose resolution materially changes the generated space: counts,
scale, boundaries, zones, connectivity, elevation, enterability, or which image
must be authoritative. Do not ask about rules, scoring, economy, UI, or code.

This is an offline build with no user to interview. Resolve each necessary
question yourself using the narrowest, least inventive answer consistent with
the original message and existing author answers, and mark it
`[agent_inferred]`. Never disguise an inference as an author answer. If no
question is necessary, write `None`.

Write each resolution on one line:

```text
- [author] scale — Q: ... A: ...
- [agent_inferred] boundary — Q: ... A: ...
```

These answers become part of the context for the next section.

### 2. Enriched image prompt

Write one paragraph, or two short paragraphs, under the exact heading
`## Enriched image prompt`. This is the final scene description the image model
will receive, before the deterministic camera/style wrapper.

Synthesize the author's original message, every clarification answer, and the
spatial decisions below into a concise description of the 3D map. Treat answers
as the author continuing the original message; when an answer conflicts with an
earlier detail, the answer wins.

Translate mechanics into their smallest directly implied physical footprint:
bosses need boss encounter areas, minions need surrounding encounter ground,
progression between islands needs an ordered visible route, and physical
training needs a training space. This is not permission to invent unrelated
assets or genre decoration.

Include zones, paths, terrain, buildings, key props, counts, and camera-facing
composition. Include the visible, scene-specific form of chosen config options.
Exclude scoring, economy, UI, scripts, and every layout-only placement from
section 6. Write in English, present tense, normally 80–250 words when the
source is rich and shorter when it is not. Do not write catalogue prose: bend
every applicable concept to this scene.

The later transcriber copies this paragraph verbatim into
`initial_scene_subprompt_enriched`; prompt assembly uses that field verbatim.

### 3. Genre

The dominant genre, by canonical name. Name a secondary genre if the prompt is
honestly two things — but **the dominant genre owns the shape and any
genre-wide route.** Secondary genres contribute options only.

Two is the normal ceiling. If you are naming three, you have not found the
dominant one.

**`No Genre` is one of the answers.** A prompt that describes a place and never
implies a game — a lobby, a farm scene, a hangout, an environment showcase — has
no genre, and saying so is a complete answer rather than a failure to decide.
The test is whether the prompt names something a player *does* that a genre owns:
a score, a finish line, an enemy, a build loop, a round. If it names none of
those, do not supply one. Guessing "probably an obby" from a prompt that never
said so builds a map nobody asked for.

Choosing it changes one thing about your job. **`No Genre` has no shape; it
asks five axes instead**, listed in the menu. Answer only the ones the prompt
actually decides and say so by name — `enclosure`, `verticality`, `zone-count`,
`structure`, `play-space`. Every axis has a default that costs nothing, so
leaving all five alone is a complete answer, and the menu marks which non-default
answers force a pipeline pass.

### 4. Shape, and the preset it came from

**Exactly one shape**, by ID, from the shared catalogue. Say what that shape
means *for this scene* — not the catalogue's generic wording.

**Every shape is reachable from every genre.** Each genre publishes a short list
of typical shapes with a default, and that list is presentation, not a
restriction. When none of them fits, take any other row in the catalogue and say
you took it from outside the genre's usual set. The shape you want is almost
always elsewhere in the catalogue rather than missing from it — a prompt wanting
one large interior finds Simulation assumes an outdoor shared world and
Roleplay's housing shapes are all towns, while `interior-single` was there the
whole time. Look before you settle for the nearest wrong answer.

**When the catalogue genuinely has nothing, describe the shape instead.** Name no
ID, answer the five routing axes directly — `enclosure`, `verticality`,
`zone-count`, `structure`, `play-space` — and describe the space in the author's
own words. The bar is specific: you must be able to say which catalogue shapes
you rejected and why. Not "nothing fit" but *"`space-bounded` assumes one level
and this is a stack of floors the player moves between; `rooms-sequence` assumes
an order and these connect freely."* If you cannot write that sentence, a
catalogue shape fits and you should use it.

**Read the genre's presets before you settle, and name the one you matched.**
Each is a shape plus a bundle of options, and they carry judgement the shape
table cannot hold: which of two similar shapes a well-known game of this kind
actually uses, which option a whole family of games needs and no single prompt
thinks to ask for. Write the name in prose, spelled as the menu spells it — it
is a name, not an ID, so it takes no backticks.

**The prompt outranks the preset.** Take the shape the prompt describes even
when the preset would have given another, and say you did. Add the options the
prompt asked for that the preset lacks, and drop the ones it contradicts. A
wrong option is not inert — it is an instruction to the image model.

**Say `none` when the preset is no longer recognisable** — when you swapped its
shape *and* dropped most of its options, so no honest name is left. Keep the
shape or keep most of the options, not neither. `none` is a real answer, and a
wrong name is worse than none at all.

When the prompt names several distinct spaces, keep them all. Choose one
top-level shape: the largest containing shape when one contains the others, or
the dominant space otherwise. In section 7, name each subordinate map or zone,
its own spatial form and any distinct theme. Separate maps force `P4`; regions
inside one map do not. Never flatten a lobby plus match map, or differently
shaped floors, into one generic zone merely because the strict spec has one
top-level shape field.

### 5. Config requirements

Which options apply, by ID, each with one clause saying **what it looks like in
this scene**. Bend the generic wording to the prompt's subject: `safezone-town`
in a pirate prompt is a harbour town, not "a settlement".

**What the prompt asks for is already chosen.** A prompt naming a shop row has
picked the shop row. Do not pad with plausible extras the prompt never
mentioned, and do not withhold what it plainly asked for.

**The six options marked `UNIVERSAL` in the menu are the sharpest version of
that rule.** They are shared across every genre and they read as reasonable
almost anywhere — interiors, water, relief, NPCs — which is exactly why they get
picked unasked. Take one only when the author named the thing it stands for.

**Every option is reachable from every genre.** A genre's options are its
shortlist and preferred wording, not a fence. Look in this order: the dominant
genre, the six universal options, then the other genres' rows in the menu. Only
use free text when no canonical ID fits. When reaching outside the genre, take
the ID and structural metadata but write the clause from this prompt; never
inject the other genre's example sentence. If destination or route varies,
follow the physical thing this prompt describes and state that choice.

**This section is the image config only** — geometry the model draws. Anything
recovered after segmentation belongs in section 6 instead.

### 6. Layout requirements

What the layout stage must **place** once the image comes back. Trigger volumes,
spawn markers, checkpoints, pickups and emitters are sited against the segmented
layout rather than drawn, so they must never reach the image model — but they
still have to be decided, and this is where.

**This is a decision of its own, not a label on the picks above.** Ask what this
game needs to be playable that a picture would never show: where a player who
falls comes back, where enemies enter, what is collected and from where, which
volumes score. An obby with no `checkpoint-respawn` restarts the whole tower on
every fall, and no render will ever reveal that it is missing.

**Decide it from the prompt and the genre, not from the preset.** A preset naming
`spawner-npc` says the family usually wants one, which is not a finding about
this scene; a preset naming none is not a finding that this scene needs none.

Name each by ID, with the same scene-specific clause the config requirements
get, plus the two things a drawn option does not need:

- **How many** — when the prompt or the shape implies a number
- **Where** — the siting rule: which zone, at what interval, against what
  geometry. "One at the top of each of the four stacked sections", not
  "throughout the course"

The menu marks every option with `goes_to`. A `layout` option belongs here and
nowhere else. A `both` option belongs in both places — its drawn form in
section 5, its siting rule here. Say so plainly when the scene genuinely needs
nothing placed.

### 7. Layout components

The concrete build. This is the part the image model ultimately renders, so be
specific and spatial:

- **Zones** — each named space, its role, roughly where it sits, roughly how big
- **Paths** — what connects to what, and what kind of connection (road, corridor,
  track, ramp, portal)
- **Terrain** — relief, water, ground material
- **Props** — the named objects, **with counts when the prompt gave one**
- **Boundary** — what encloses the play space, or that it is open
- **Composition** — how it should sit in frame

**Carry every number the prompt stated.** "Five islands", "three floors", "about
twenty houses", "20 studs wide". Nothing downstream can recover a count you drop.

### 8. Render order

State which image is rendered **first**, and which is authoritative. Exactly
three orders exist. **Write the order's name in backticks, exactly as spelled
here** — these are the three values the next stage records, and it has no way to
recover a fourth spelling.

| Write this | First | Then | Use when |
| :---- | :---- | :---- | :---- |
| `isometric` | isometric drawn from text | top-down converted from the isometric | **Default.** The look leads and the plan is projected from it. |
| `topdown` | a top-down plan drawn from text by the image model | isometric dressed from that plan | The topology must be valid to play, and an isometric drawn look-first cannot guarantee it. |
| `authored_plan` | a blueprint **this repo generates in code** — no image model involved | top-down, then isometric, both built from that blueprint | **Required** for a supported maze or racing route. Nothing else can be carved. |

**`topdown` and `authored_plan` are not two strengths of the same thing.** With
`topdown` the image model still draws the plan, and it is trusted to. With
`authored_plan` the geometry is computed — a maze solver, a track generator —
and the image model is only allowed to dress it. Asking for `authored_plan` on
anything but a supported maze or racing route asks for a blueprint that cannot
be produced.

So: an RPG whose biomes must stay connected is `topdown`, **not**
`authored_plan`. A hedge maze is `authored_plan`. A kart circuit or
point-to-point race track is `authored_plan`. Everything else that needs valid
topology is `topdown`. The deterministic mapper enforces this for
`puzzle-maze`, `route-circuit`, `route-multitier`, and
`route-point-to-point`, even if this section accidentally selects another order.

Say **why** in one clause. The test is not "is it complex" — it is **"would an
invalid layout make the game unplayable?"** A maze with a sealed corridor, a
circuit that does not close, an obby whose jump chain has an impossible gap.
Those need a plan first. A town that is merely intricate does not.

### 9. Scale, theme, and pipeline cost

- **Scale band** — small / medium / large / huge, and what drove it. This is the
  strict-spec spelling of intake's Room / Block / District / Region bands,
  respectively. Choose from the smallest detail that must remain legible in one
  isometric frame, not from the grandest stated world extent; when extent and
  detail cannot both fit, preserve the detailed build and state the map split.
- **Theme** — the visual register, in a few words
- **Pipeline modifiers** the picks force, by code, each with a clause:

| Code | Means |
| :---- | :---- |
| `P0` | Default. No deviation. |
| `tiered` | Relief with **no overhang** — one surface still, but capture the elevation. |
| `P2` | Surfaces **overhang** each other, so one top-down would occlude some of them. |
| `P3` | Play crosses an **outside↔inside** boundary — needs two linked top-downs. |
| `P4` | **Separate maps**, not one space. |
| `P6` | Structure **must be valid by construction**. |
| `CHECK` | Volumetric play-space — fine unless the volume self-occludes. |
| `SET` | Real geometry **nobody walks on** — skip traversal and jump-gap checks. |

Name a modifier only when the geometry forces it, and be able to point at the
thing that forces it. Each one buys a real cost — an extra capture path — so the
test is whether a single top-down of a single surface would actually lose
information, not whether the scene is elaborate. `P0` means the geometry forced
nothing, which is a finding, not a blank.

## The empty case

If the author input is empty, or describes no buildable space at all (a chat-only
quiz, a bare 2D screen game, pure UI), say so plainly in one line and emit
`P5` as the only modifier. Do not invent a space to fill the blob.

The test for `P5` is whether there is any three-dimensional space at all — not
whether the space is small, simple, or unwalkable. A board, a table and four
seats is a layout. A space that is real and built but never walked on is `SET`,
not `P5`. Only a game with no room around it — numbers on a screen, a chat
window — is `P5`.

## Style

Plain declarative prose. Short headings. No bullet-point dumps of the whole
option table, no restating these instructions, no hedging. Roughly 200–450
words: enough to be specific, short enough that every sentence is load-bearing.

**Write in English, whatever language the prompt was written in.** About one
prompt in ten arrives in Spanish, Portuguese, Arabic or Korean, often with its
clarifications in the same language, and answering in kind is the natural thing
to do. It is also the one style choice here that reaches the render: the next
stage copies your wording for each option into the spec verbatim, and the spec's
wording is appended to the image prompt. An option described in Arabic is an
instruction the image model cannot read, sitting in a prompt whose every other
line is English.

Read the author in their own language — that costs nothing and the genre is
often clearest in the words they chose. Only what **you** write comes out in
English.

Write it as if handing off to a colleague who will build the map and has not read
the prompt.
