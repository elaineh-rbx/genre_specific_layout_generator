---
name: scope-reduce-default
description: Turns a game request that is too big to build in one pass into a set of build-ready zones and starts the build on one — with no user questions. Fires only when the request needs more than one buildable frame at the detail its gameplay demands. Collects genre, shape and options unchanged, interprets the whole request into zones (each with its own shape, route and options), auto-selects the main subject / core gameplay area / entry zone to build first, and marks that one to send to the pipeline now. Invoked by layout-intake after genre-choice, not directly.
disable-model-invocation: true
---

# Scope Reduce — Default (no user input)

The pipeline builds **P0 and P6 today, and nothing else** — `P2`, `P3`, `P4`
and `CHECK` are designed but not running (`docs/LayoutGen - Pipeline.md`,
readiness gate). A request that needs one of those, or one map too big for a
single frame at the detail its gameplay demands, cannot be built in one pass.

This skill does not fix that by building more. It **interprets the whole request
into zones** — each a complete, build-ready piece — and sends the pipeline the
one zone it can build now. The user asked for a world; we work out every part of
it and start on one.

It runs **after** `genre-choice` and `layout-intake` have produced a handoff.

**This is the no-questions variant.** It picks the starting zone itself, so the
pipeline can be exercised with no user in the loop.

## It interprets on top of genre / shape / options — it never rewrites them

**The genre, shape and options are already decided, and this skill leaves them
exactly as it found them.** `genre-choice` classified the game; `layout-intake`
added theme and scale. That block is the record of what the user asked for and
stays verbatim — `layout-intake`'s own rule already says so: *keep `genre_choice`
unmodified, or two skills end up in charge of the same fields.*

What this skill adds beside that record is `zones` — the whole request cut into
build-ready pieces — and `active`, naming the one zone we send to the pipeline
now. The pipeline builds `active`; `genre_choice` remains the full intent,
untouched.

```
genre-choice + layout-intake  →  full handoff (genre, shape, options, theme, scale)   ← preserved verbatim
                              →  scope-reduce reads it, changes nothing in it
                              →  emits the same handoff + zones[] (every part, build-ready) + active (the one we build now)
```

## What this is not

- **Not a rewriter.** The chosen genre, shape and options are preserved. If you
  find yourself editing a field inside `genre_choice`, stop — it belongs in a
  `zones` entry instead.
- **Not a router.** `genre-choice` decided the shape and modifiers; this skill
  reads them to detect overflow and derives a buildable route per zone.
- **Not a scope police.** It does not shrink a build that already fits. Most
  prompts are one ordinary map and this skill returns them unchanged, with no
  `zones` and no `active`.
- **Not a gameplay editor.** `mechanics` — combat, currency, day/night, UI —
  lives in `genre_choice` and stays there. Building one zone does not delete the
  combat system; it means the combat system runs on that zone.

## Workflow

```
- [ ] 0. Set the grain — how close does the player get? Gameplay sets the level of detail.
- [ ] 1. Confirm the overflow — does it need more than one P0/P6 frame at that grain?
- [ ] 2. Cut the request into zones and interpret each into a build-ready entry
- [ ] 3. Pick the zone to build first — the main gameplay area / entry, auto-selected, no questions
- [ ] 4. Emit — the full zones list plus the one active zone we send now
```

## 0. Set the grain

**The level of detail is set by how close the player gets to things, and that
decides whether we cut at all and how finely.** It is the same *smallest thing
you can pick out* idea `layout-intake` uses for the scale band, now driving the
decomposition.

- A city you **walk around in** has to be split into districts, because a player
  standing on a street needs that street to be rich — shopfronts, doors, props.
- The **same city in a flight simulator** is **one simple zone.** You only ever
  see it from above, so plain block geometry reads fine and there is nothing to
  cut.

**Cut down to the smallest thing the player actually needs to make out, and no
finer.** Read that off the gameplay, not off how big the world sounds. A request
can name a huge world and still be one zone if the game keeps the camera high.

## 1. Confirm the overflow

Reframe only when the request needs more than one buildable frame **at the grain
from step 0**. Any one signal fires it; none present means it does nothing —
return the handoff unchanged, with no `zones` and no `active`.

| Signal | Reads as | Where to see it |
| :---- | :---- | :---- |
| **Multiple maps** | Several places a player loads into that cannot share one surface. | `pipeline` contains `P4`, or `genre_choice.segments` has two or more `kind: "map"` entries. |
| **Outside and inside** | The build goes out of a structure and into it — both are generated. | `pipeline` contains `P3`. |
| **One map too big for its grain** | A single surface that cannot hold, in one frame, the detail this gameplay needs. | `scale.band` is `region`, **or** a container of zones the frame cannot hold at the required detail. |
| **A modifier that cannot be built today** | The route is honest and the pipeline cannot run it. | `pipeline` contains `P2` or `CHECK`. |

**Judge the third signal at the grain, and it can decline to fire.** A
region-scale map is only overflow if the gameplay needs detail a single frame
cannot hold. The flyover city above is `region` and still one zone — do not fire
on it. A walkable city the same size does overflow. The band alone does not
decide; the band *plus the grain* does.

**Silence is not overflow.** An ordinary arena, course, town or lobby is one
P0/P6 map and fires nothing — return it untouched.

**Interior-only is not the outside/inside signal.** A game that stays entirely
indoors is a single roofless top-down and routes `P0` (`Pipeline.md`, P3 note).
The `P3` signal is the *transition* — a build with both an exterior and an
enterable interior.

**On the fourth signal, check the grain before you accept it, and there is one
test.** For both modifiers it is the same question: **at this grain, does more
than one playable surface sit at the same ground position?**

- **`CHECK`** asks whether the play *volume* self-occludes. A duck flying an
  ocean crossing occupies one altitude band over open water — the sea generates
  as an ordinary surface and the flight is an envelope above it, so nothing is
  hidden behind anything and the `CHECK` does not survive. Layered floating
  islands, an asteroid field or a 3D cave network do self-occlude, and it does.
- **`P2`** asks the same of built geometry. A rooftop sits above its own
  building, not above the road, so a city crossed roof to roof is one surface per
  position. A skybridge over traffic is two.

**Where the grain drops the modifier, take the win** — but record that you did.
Emit `route_cleared`: one sentence naming the modifier and why it does not
survive at this grain. Do **not** edit `pipeline` to remove it; that field is
inside `genre_choice` and this skill does not rewrite it.

That record is the whole point of the field. A handoff that comes back with
`CHECK` still in its route and nothing saying anyone looked at it is
indistinguishable from one nobody assessed, so the readiness gate downstream has
no choice but to reject a build that would in fact have run. Declining to fire
is a decision, and an unrecorded decision reads as an oversight.

Where it survives, this is the signal that fires, and step 3 is where it is
answered — by the twin lookup, or by an honest deferral when no twin exists.
Earlier versions of this file called `P2`/`CHECK` "a separate gap, not this
skill's to close" and left it there. That was the whole problem: `layout-intake`
dispatches here *because* of those modifiers, so declining them meant nobody
handled the one thing that sent us, and an unbuildable route went to the
pipeline untouched.

### Content breadth — a single-surface density trigger

The signals above catch *structural* overflow (`P4`/`P3`/`P2`/`CHECK`, the region
band). They miss a scene that is one contiguous `P0`/`P6` surface yet still too
dense to read in one frame — a walkable overworld with many named territories.
So `buildable_now` must test **semantic breadth, not just surface continuity**:
an overworld is a bare `P0` and was still shipped illegible because every
district was crammed into one frame.

**Territory Breadth Count.** Count the distinct *named regions* the prompt
requires at this grain — biomes, species territories, districts, arenas. Count
nouns, not adjectives: "dense", "sprawling", "massive" are style-flavour and
too brittle; ignore them and rely on the region count.

- At a **walkable** grain the limit is **one hub/district + at most one adjacent
  sub-zone**. If `count(distinct regions) > 1`, emit
  `overflow: content_breadth_exceeded`, set the zone `buildable_now: false`, and
  drill — even though its route is a bare `P0`/`P6` on a single surface.
- Any prompt specifying **N ≥ 3** distinct biomes, arenas, or districts at a
  walkable grain should immediately trigger this drill.
- At a **flyover / map** grain breadth does not overflow: the whole thing reads
  from above, so a many-region world stays one zone. This is what keeps a huge
  empty desert with one monolith (breadth 1) a single buildable zone regardless
  of footprint — you are counting semantic variety, not spatial size.

**Default active pick when a breadth drill fires: hub + one starter territory**
— not the bare hub (which renders as an empty plaza) and not all N (the clutter
we are removing). Take the entry hub plus one adjacent territory; its far edges
then double as the natural bound.

**Record the deferred siblings as child zones** so "now build territory 2" is
trivial later:

```json
{ "name": "Ember Territory", "kind": "zone", "buildable_now": false,
  "parent_hub": "Warden Village", "connector": "East Canyon Trail" }
```

## 2. Cut the request into zones

**We do the cutting.** Interpreting every part is the point of this step: it is
what lets step 3 pick a specific, named zone with confidence, and it means a
zone built later is already worked out rather than re-derived from scratch.

Cut to the grain from step 0, and **interpret each zone into a complete,
build-ready entry** — its own shape, route, theme, scale, and options, exactly
as if it were the whole prompt. The candidates come first from
`genre_choice.segments`; where the prompt named the parts loosely, name them
yourself as specific places.

**Fill thin zones by inheritance, never with a placeholder.** When the prompt
describes one part fully and the rest only as "harder" or "the same but bigger",
interpret the rest from the described one — World 2 inherits World 1's shape and
options with an escalated theme, marked `assumed`. A zone left as `shape: null`
is a hole that surfaces later; a reasoned inheritance is a build that can be
corrected.

**A structure's outside and inside are separate zones**, and the transition
between them decides how cleanly they separate — record it per zone:

| Transition | Reads as | Consequence |
| :---- | :---- | :---- |
| `none` | The zone has no inside/outside pair. | Ordinary single zone. |
| `gateway` | A door with a loading step, a teleport, a portal between out and in. | The interior is a **clean separate build** — the two barely entangle. Easy. |
| `seamless` | The player walks straight from outside to inside with no break. | The interior and exterior 3D have to agree in one continuous space. **The hard case.** |

**A zone that is still too big at its grain is not buildable now.** Mark it so,
name the cut it will need (its districts, its floors, its inside/outside), and
drill only the zone that step 3 selects. Do not expand every branch up front —
interpret the top-level zones fully, and drill only the one that gets built.

## 3. Pick the zone to build first

Do not ask. **Identify the one zone to build first and set it as `active`
yourself**, in this order of preference:

1. **The main gameplay area — where the core loop happens.** The arena a
   wave-survival is fought in, the runway a fashion show is judged on, the first
   world of a grinder, the hub every path radiates from. This is "the point of
   the game", and it is usually the right first build.
2. **Prefer the exterior and the entry.** Between two equally central zones, take
   the outdoor one and the one players arrive in — in 3D, an interior you also
   see from outside is fiddly (the two have to line up), so the exterior is the
   surer, more visible start, and a `seamless` interior is the hard case. The
   exception: when the point *is* the interior (an escape room, a shop or house
   sim, a story that opens indoors), that interior is the main area and wins.
3. **It must be `buildable_now` — and first work out *why* it is not.** There are
   two reasons and they have opposite fixes. **Too big** is a size problem: drill
   it by the same rule, take its main / exterior sub-zone, repeat until you reach
   a bare `P0`/`P6`, adding the chosen sub-zone to `zones`. **An unready route
   modifier is not a size problem, and drilling does not fix it** — every
   sub-zone of a `P2` zone is still `P2`, so drilling continues until it leaves
   the shape altogether and lands on whatever bare space it finds. That is how
   you end up shipping a plaza for a game about crossing a city. Reduce the shape
   instead: see below. Never emit an `active` that is not buildable now.

### When the route is what blocks it

**Which modifier is blocking decides the answer, and only one of them needs a
twin.**

- **`P4` or `P3`** — the cut itself is the answer, and step 2 has already made
  it. Separate maps become separate `zones`; an exterior and its interiors
  become an exterior zone plus `gateway` interior zones, and each of those is a
  bare `P0` on its own. Nothing is reduced and nothing is deferred: take the
  exterior as `active` by the ordinary order of preference above. Do not go
  looking for a twin, and do not write `core_deferred` — a Brookhaven town whose
  houses are separate interior zones has lost nothing.
- **`P2` or `CHECK`** — the cut does not help, because every slice of an
  overhang still overhangs. This is the case the twin lookup below is for.

**For `P2`/`CHECK`, first ask whether this shape has a `tiered` twin, because
four do and two do not, and the two cases end differently.** Do not reduce a
shape until you have checked which case you are in — there is no general licence
here to flatten something into whatever will build.

| Blocked shape | Twin | What the twin gives up |
| :---- | :---- | :---- |
| `arena-stacked` | `arena-tiered` | catwalks and balconies over the floor |
| `course-tower` | `course-terraced` | platforms directly above each other |
| `route-multitier` | `route-circuit` | sections crossing over the course |
| `traversal-city` | `traversal-city-tiered` | skybridges and ledges over the road |
| `world-underground` | **none** | — the mine really is beneath the town |
| `volume-open-air` | **none** | — but its `CHECK` is usually benign; see step 1 |

**If there is a twin, take it.** The twin is the same place doing the same thing
with every bit of its elevation, giving up only the geometry that hangs over
other geometry. Keep the zone, carry the options across.

**If there is no twin, do not invent one.** Keep the zone
`buildable_now: false`, pick the next zone by the same order of preference, and
record in top-level `core_deferred` that the requested core is waiting on the
pipeline. Shipping a peripheral zone is acceptable **only** when it is labelled
as one. A surface town standing in for a mining game is an honest placeholder
with the label and a wrong answer without it.

**The twin goes in the zone's `shape`, never in `genre_choice.shape`.** That
block stays verbatim as the record of what was asked for, exactly as everywhere
else in this skill; the zone is where what we can build today is written. Those
two disagreeing is the point — it is how the deferral stays visible.

A rooftop is not an overhang — it sits above its own building, not above the
street — so a city crossed roof to roof keeps its rooftops, its ledges, its gaps
and the fall to the street. What it loses is the skybridges. That is a detail of
the city; the plaza was a different game.

**Whichever branch you took, two things must ride along or the reduction is
worse than useless.**

- **`tiered` only builds correctly if the elevation is captured.** Say so
  explicitly in the zone's `notes` — *the height range is load-bearing, do not
  build this flat* — because a rooftop city rendered flat is a car park.
- **Name what the step-down gave up**, in the zone's `notes` and in one entry
  under `reduced_from`. A reduction nobody can see is indistinguishable from
  having read the prompt wrong.

Record the pick so a reviewer (or the user, later) can see it was automatic and
correct it cheaply: set `active` to the chosen zone, `recommended` to the same
zone, `active_selection: "auto"`, `questions_asked: 0`, and add one line to the
active zone's `notes` saying why it is the main / first build.

## 4. Emit

Return the **full handoff unchanged**, with `zones` and `active` added.
`genre_choice` is not touched — read from it, write the new blocks.

```json
{
  "prompt": "<the user's original text, verbatim>",

  "genre_choice": {
    "genres": ["rpg", "adventure"],
    "shape": { "id": "world-open", "type": "Open World", "name": "Open World" },
    "preset": null,
    "pipeline": ["P4", "P3"],
    "image_prompt": [ "...the full request's picks, exactly as genre-choice emitted them..." ],
    "layout_placement": [ "..." ],
    "mechanics": ["24-minute day/night cycle", "3 classes with skill trees", "DataStore autosave every 60s"],
    "segments": [ "...all the spaces, exactly as genre-choice emitted them..." ],
    "notes": [ "...genre-choice's own notes, untouched..." ]
  },
  "theme": "Sci-fi/fantasy hybrid open world",
  "theme_assumed": true,
  "scale": { "band": "region", "assumed": true },
  "constraints": [],

  "active": "The Nexus Palace",
  "recommended": "The Nexus Palace",
  "active_selection": "auto",
  "questions_asked": 0,

  "zones": [
    {
      "name": "The Nexus Palace",
      "kind": "zone",
      "buildable_now": true,
      "shape": { "id": "space-bounded", "type": "Zone", "name": "Bounded Play Space" },
      "pipeline": ["P0"],
      "theme": "Ornate neutral palace hub",
      "theme_assumed": true,
      "scale": { "band": "block", "assumed": true },
      "transition": "none",
      "image_prompt": [
        { "id": "social-hub", "text": "A grand central palace hub where players arrive and regroup" },
        { "id": "landmark-focal", "text": "The palace itself as the orienting landmark, visible across the hub" }
      ],
      "layout_placement": [
        { "id": "teleporter-link", "type": "Teleporter", "text": "Departure points to the four zones" }
      ],
      "notes": ["Auto-selected first build: the entry hub every biome radiates from, and a bare P0."]
    },
    {
      "name": "Cyberpunk Metropolis",
      "kind": "zone",
      "buildable_now": false,
      "shape": { "id": "traversal-city", "type": "Zone", "name": "Traversal City" },
      "pipeline": ["P2", "P3"],
      "theme": "Neon cyberpunk city",
      "theme_assumed": false,
      "scale": { "band": "region", "assumed": true },
      "transition": "gateway",
      "cut_hint": ["the streets (exterior)", "the underground slums (interior, gateway)"],
      "image_prompt": [ { "id": null, "text": "Neon-lit skyscrapers with holographic ads over rainy asphalt streets" } ],
      "layout_placement": [ { "id": "building-interior", "type": "Zone", "text": "Accessible underground cyberpunk slums beneath the streets" } ],
      "notes": ["Walkable city, so it cuts into districts. Not buildable whole; drill when built."]
    },
    {
      "name": "Luminescent Forest",
      "kind": "zone",
      "buildable_now": false,
      "shape": { "id": "world-open", "type": "Open World", "name": "Open World" },
      "pipeline": ["P0"],
      "theme": "Bioluminescent fantasy forest",
      "theme_assumed": false,
      "scale": { "band": "region", "assumed": true },
      "transition": "none",
      "cut_hint": ["the glowing grove", "the neon-blue river"],
      "image_prompt": [ { "id": null, "text": "Giant ancient trees with glowing purple leaves and neon-blue rivers" } ],
      "layout_placement": [],
      "notes": ["Region-scale at a walkable grain; cuts into named sub-areas when built."]
    },
    {
      "name": "Celestial Floating Kingdom",
      "kind": "zone",
      "buildable_now": false,
      "shape": { "id": "volume-open-air", "type": "Zone", "name": "Open Airspace" },
      "pipeline": ["CHECK"],
      "theme": "Marble sky-island kingdom",
      "theme_assumed": false,
      "scale": { "band": "district", "assumed": true },
      "transition": "none",
      "image_prompt": [ { "id": null, "text": "White marble castles on floating sky islands with cloud platforms" } ],
      "layout_placement": [],
      "notes": ["Self-occluding open volume → CHECK, not buildable today. Flagged, not resolved by cutting."]
    }
  ],

  "open_questions": []
}
```

### Field rules

| Field | Rule |
| :---- | :---- |
| `genre_choice` | **Emitted verbatim.** Same block `layout-intake` assembled. If it differs, this skill has overstepped. |
| `zones[]` | Every part of the request, each a build-ready entry. Present only when the skill fired. |
| a zone's `buildable_now` | `true` when its route is a bare `P0`/`P6` (± `tiered`) at its grain, it needs no further cut, **and** (at a walkable grain) its Territory Breadth Count is ≤ 1 hub + 1 adjacent sub-zone. `false` when it is still too big, carries an unready modifier, or `overflow: content_breadth_exceeded`. |
| a zone's `pipeline` | The route for that zone alone. A `buildable_now: true` zone is `["P0"]` or `["P6"]`. |
| a zone's `transition` | `none`, `gateway`, or `seamless` — per step 2. Drives the exterior-first preference in step 3. |
| a zone's `cut_hint` | For a `buildable_now: false` zone, the named sub-zones it will cut into when built. Omit for buildable zones. |
| a zone's `theme_assumed` / inheritance | Mark `assumed` where the zone was filled by inheritance from a sibling rather than described. |
| a zone's `reduced_from` | Present only when step 3 stepped a `stacked` shape down to its `tiered` twin. `{ "shape": the id you started from, "gave_up": what the overhang would have been }` — *"skybridges and ledges cantilevered over the road"*. This is the record that the space was changed rather than misread, and it is the field a reviewer looks at first. |
| `route_cleared` | Top level, present only when a `P2` or `CHECK` in `pipeline` does not survive the grain and the skill therefore declined to fire. One sentence: the modifier, and why it is benign here. Emitted **with** the untouched handoff, and it is the only thing distinguishing "assessed and safe" from "never looked at". |
| `core_deferred` | Top level, present only when no honest reduction existed and `active` is therefore **not** where the game happens. One sentence naming the part of the request that is waiting on the pipeline and the modifier it waits on. Omit it entirely when `active` holds the core. Never ship a peripheral `active` without it. |
| `active` | The one zone sent to the pipeline now, auto-selected per step 3. It **must** be a `buildable_now: true` zone. If the main zone is not buildable, first ask why: an unready route modifier means step the shape down to its `tiered` twin and keep the zone; only genuine size means drill, add the chosen sub-zone to `zones`, and point `active` at that. |
| `recommended` | Same as `active` — no alternative was offered. |
| `active_selection` | `"auto"` — chosen without user input. |
| `questions_asked` | Always `0` for this variant. |

**When the skill does not fire**, emit the handoff exactly as received and add
neither `zones` nor `active`. Their absence means the build is the whole request.
The one exception is `route_cleared`: when what you declined to fire on was a
`P2` or `CHECK` you judged benign at the grain, that sentence rides along.
Nothing else about the handoff changes.

**Nothing is lost.** `zones` accounts for every part of the request; a follow-up
— "now build the Metropolis" — lifts that zone out, drills it if needed, and runs
it through the pipeline.

## Worked example — a four-biome RPG world

The prompt: a "massive, seamless" open-world RPG, four detailed mega-biomes
(Cyberpunk Metropolis, Luminescent Forest, Scrapyard Wasteland, Celestial
Floating Kingdom) around a central hub, "The Nexus Palace", each biome with its
own interiors, bosses, weather and combat.

0. **Grain.** It is a walkable RPG — players stand in these places — so the
   detail is high and the world genuinely needs cutting. *(Were it a flyover
   game over the same world, it would be one coarse zone and the skill would not
   fire.)*
1. **Overflow.** `P4` + `P3` and five spaces. It fires.
2. **Cut.** Interpret all five into build-ready zones: the hub is a bounded P0;
   the metropolis is a walkable city that will cut into streets (exterior) and
   slums (a `gateway` interior); the forest and wasteland are region-scale at a
   walkable grain; the sky kingdom is `CHECK` and not buildable today. Each gets
   its own shape, route, theme and options.
3. **Pick.** No question. The hub every biome radiates from — The Nexus Palace —
   is the entry, and it is a bare `P0`, so it is auto-selected as the first build.
4. **Emit.** `genre_choice` untouched; `zones` holds all five, fully interpreted;
   `active` is The Nexus Palace with `active_selection: "auto"` and
   `questions_asked: 0`. The hub goes to the pipeline; the rest are already worked
   out for whenever they are built.

## What we pass to image generation

The image model receives the **`active` zone's** `shape` and `image_prompt` only
— here, `space-bounded` (P0) and the hub's two picks. The `active` zone's
`layout_placement` goes to the post-segmentation placement pass. The other zones
in `zones` are not sent now; they wait, build-ready, for their turn.

**Scrub the deferred siblings from the active zone — prose AND structured fields.**
The mapper assembles the active zone's `image_prompt` *and a catalogue addendum
built from its `options` / `layout` / `layout_placement`* into one prompt. A
sibling territory named in the prose, or a `count: 6` / "across the six
territories" / a deferred dungeon left inside an `options` or `layout_placement`
entry, leaks straight back into the render and re-crowds the very frame the drill
was meant to thin. So when a breadth drill fires:

- rewrite every `count` to the active sub-zone (e.g. `count: 1`);
- drop options, paths and layout zones that named the deferred territories or the
  deferred dungeon;
- bound the active zone's outer edges with impassable terrain (treelines,
  ridgelines, water) instead of trailing off toward what was cut.

Empirically this is load-bearing: scrubbing the prose alone does **not** work —
the structured fields re-inject the deferred content through the addendum, and the
image still comes back with all N territories. Scrub both.
