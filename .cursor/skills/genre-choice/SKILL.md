---
name: genre-choice
description: Classifies a game prompt into Roblox layout genres, offers the matching layout options as a short menu, and emits the picks split into an image-generation stream and a layout-placement stream with the pipeline route. Use when a user describes a game they want built and the layout genre, layout features, or pipeline route needs to be determined.
disable-model-invocation: true
---

# Genre Choice

Turns a game prompt into a set of chosen layout features and a pipeline route.

**Nothing here is mandatory.** The user picks; if they pick nothing they get a
simple map, and that is a legitimate outcome.

Never inject an option the user did not choose — but **what the prompt asks for
is already chosen.** A prompt naming a shop town has picked the shop town, and
shipping the course without it discards a third of what they said. The rule
forbids padding the map with plausible extras they never mentioned, not
building what they wrote.

## Workflow

```
- [ ] 1. Classify the prompt
- [ ] 2. Load the matching reference file(s)
- [ ] 3. Offer a preset
- [ ] 4. Tune, if the user wants to
- [ ] 5. Ask the open question
- [ ] 6. Emit
```

## 1. Classify

Two stages, in this order. Do not skip to stage B.

### Stage A — match a genre

| Outcome | Meaning | Then |
| :---- | :---- | :---- |
| **Genre** | One genre in the index below clearly fits. | Stage B |
| **Mixed** | Two or more genres fit, and the prompt means both. | Stage B |
| **Unrecognised** | A real game concept that matches no genre. | Ask **one** clarifying question. If the answer lands on a genre, it is Genre. If not, it is None. |
| **None** | No game type is discernible — a place, a mood, a theme. | Stage B |

Ask at most one clarifying question, and only for Unrecognised. Do not
interrogate. A prompt that is merely brief is not unrecognised — "make me a
zombie game" is Survival with a theme attached.

**Skip the question if stage B is plainly going to answer No.** Asking a user
to elaborate on their origami game, only to tell them there is no map to build,
wastes a round trip. Go straight to stage B.

### Stage B — is there a space?

One question, asked of every outcome including Genre:

> **Does the player move through a space?**

**No** → route **P5**, emit the block in step 6, and stop. Do not offer options.
**Yes** → step 2, carrying the stage A outcome.

Concepts that usually have no space: idle and incremental clickers, coloring
and drawing, match-and-merge, word games, rhythm games, video watching, and
chat-only quizzes with no physical set.

**Judge the concept, not the keyword.** "A music game where you hit notes to a
beat" has no space and is P5. "A music venue where people hang out and listen"
has a room, a stage, and a crowd — it is a place, so it goes to Entertainment
or no-genre. Routing it to P5 would refuse to build something perfectly
buildable.

**When genuinely torn, build.** An unnecessary map costs less than a wrongly
refused one. "A game where you fold origami" has no space and is P5; "a game
where you fold origami in a little paper studio" has one, and is no-genre.

### Genre index

| Genre | File | Recognise from |
| :---- | :---- | :---- |
| Action | `genres/action.md` | fighting, battlegrounds, brawler, melee, arena, boss, hack and slash |
| Adventure | `genres/adventure.md` | exploration, quests, story, scavenger hunt, secrets |
| Obby & Platformer | `genres/obby-platformer.md` | obby, parkour, jumping, tower climb, difficulty chart |
| Party & Casual | `genres/party-casual.md` | minigames, tag, hide-and-seek, trivia, lobby, rounds |
| Puzzle | `genres/puzzle.md` | puzzles, escape room, maze, riddles, logic |
| RPG | `genres/rpg.md` | levels, stats, quests plus combat, dungeons, loot, grinding |
| Roleplay & Avatar Sim | `genres/roleplay-avatar-sim.md` | roleplay, town life, houses, pets, dress up, animal sim |
| Shooter | `genres/shooter.md` | guns, FPS, deathmatch, battle royale, tactical, PvE waves |
| Simulation | `genres/simulation.md` | tycoon, simulator, farming, jobs, vehicles, mining, sandbox |
| Strategy | `genres/strategy.md` | tower defense, RTS, unit placement, base defense, board games |
| Survival | `genres/survival.md` | survive, escape, killer, disaster, horror chase, resources |
| Sports | `genres/sports.md` | football, basketball, golf, stadium, scoring, teams on a field |
| Racing | `genres/racing.md` | race, laps, track, finish line, speed, driving competitively |
| Infinite Runner | `genres/infinite-runner.md` | endless runner, auto-run, dodge obstacles, subway-surfers style |
| Entertainment | `genres/entertainment.md` | showcase, hub, portals, environment demo, hangout to look at |

Two taxonomy notes, because users echo Roblox's own wording:

- Roblox files **Runner** under Obby & Platformer. A prompt saying "runner" or
  "endless obby" means Infinite Runner here.
- Roblox has one **Sports & Racing** genre. Split them by finish condition: a
  lap or finish line is Racing, a scored field or court is Sports.

## 2. Load

**A stage A outcome of None loads `no-genre.md` and nothing else.** It has the
same four sections as a genre file and the rest of this skill applies to it
unchanged.

Otherwise: **load the dominant genre first, and check its presets before
loading anything else.** A genre's presets often already cover what looked like
a second genre —
Obby's *Vehicle Obby* covers "you can drive cars," so "an obby where you drive
cars" is not a mix. Only load a second file for something the first genuinely
cannot express. Never read all fifteen.

Each file holds a **Shape** table (pick exactly one), an **Options** table
(combine freely), **Presets**, and **Genre notes**. The notes carry boundary
rules worth checking your classification against, and sometimes cite Build.md
Part I for the engine baseline behind a number — that is background, not
something you need to read to execute this.

### Reading the tables

| Column | Meaning |
| :---- | :---- |
| **ID** | Stable slug, shared across genres when it is the same concept. The dedupe key. |
| **Core** ● | Signature to the genre. A ranking aid for long lists — **not** auto-include. |
| **Goes to** | `image` = drawn by the image model · `layout` = placed after segmentation · `both` = visible part drawn, rest placed. |
| **Pipeline** | Blank = P0. Otherwise the modifier this pick forces. |

Pipeline codes: `P0 + tiered` elevation with no overhang · `P2` overhanging
surfaces · `P3` outside↔inside transition · `P4` separate maps · `P6`
structure must be valid by construction · `CHECK` only a problem if the play
volume self-occludes.

### Mixing genres

**The dominant genre owns the shape and the preset.** Shape answers compete
across genres, and honouring several stacks pipeline cost out of one sentence.
The preset follows the shape for the same reason — a preset is a shape plus
options, so taking one from a secondary genre would smuggle its shape in.

Secondary genres contribute **options only**. Union them and **drop duplicate
IDs**, presenting each concept once using the dominant genre's wording. If a
secondary genre's shape carried something the user clearly wants, offer it as
an ordinary option instead of a shape.

The dominant genre is the one the sentence is *about*. "An obby but also you
can drive cars" is an obby. "A zombie shooter where you hold out against waves"
is a shooter. When a prompt is genuinely balanced, prefer the genre whose shape
is cheapest, and say in `notes` that it was close.

## 3. Offer a preset

Match the prompt to the closest preset and offer **that one preset** — a single
decision instead of a dozen. Name the shape and features in plain language.

**Show the generic preset name only.** The *Modelled on* column is internal
grounding for you; never say "this is the Counter-Strike layout."

> Sounds like a round-based bomb defusal map: two team bases at opposite ends,
> three lanes between them, cover through the middle, and a bomb site to attack
> or hold. Want that, or would you rather build it up yourself?

**Add any options the prompt asked for that the preset lacks**, and name them
in the offer so accepting covers them. A preset is a starting point, not a
ceiling. If the prompt asked for something no option covers, carry it to step 5
rather than dropping it.

If nothing fits well, skip to step 4.

## 4. Tune

Only if the user wants to. Show, at most:

- The **shape** question, if the prompt has not already answered it.
- The **`Core`** options they do not already have.

**Cap it at roughly five items on screen.** Never paste a whole table.

**Do not ask what the prompt already told you.** "A tower obby" has answered
shape. "Zombies chasing you through a mall" has answered shape and threat.
Confirm briefly instead of asking.

Say the pipeline cost in plain language when a pick carries one — "that needs
interiors generated separately, which is a slower build" — not as a code.

## 5. Ask the open question

Always finish with one open question:

> Anything else you want in the space?

Classify whatever comes back yourself; there is no table row to look up:

**If a segmenter could identify it as geometry, it is `image`. If it is an
invisible volume, a marker, a trigger, or a property of geometry rather than
geometry itself, it is `layout`.**

A shrinking play boundary is `layout` — it has no geometry at all. A ruined
cathedral is `image`. A "checkpoint" is `both`: the pad is drawn, the respawn
is placed. If a request implies a shape change, say so and its cost before
accepting it.

**If the request matches an option in a file you have loaded, promote it to
that option** so it dedupes like any other pick, folding the user's wording
into the text so the specifics survive. Match only against loaded files — do
not go looking through the other genres for an ID.

"A giant neon sign you can see from anywhere" becomes `landmark-focal` when a
loaded file offers it, keeping the user's neon sign as the text. When no loaded
file has it, the same request is `{ "id": null, "text": "a giant neon sign
visible from anywhere in the map" }`. Both are correct; which one you get
depends on what is loaded.

## 6. Emit

Output this block. It is the handoff to the pipeline.

```json
{
  "genres": ["shooter"],
  "shape": { "id": "lane-network", "type": "Lane", "name": "Lane Network" },
  "preset": "Bomb Defusal",
  "pipeline": ["P0"],
  "image_prompt": [
    { "id": "cover-los", "text": "Waist-high and full-body cover distributed evenly across every lane" },
    { "id": "capture-zone", "text": "An open bomb site with clear approaches to attack and hold" }
  ],
  "layout_placement": [
    { "id": "spawn-teambase", "type": "SpawnZone", "text": "Balanced bases at opposite ends, shielded from sniper lines" },
    { "id": "capture-zone", "type": "CaptureZone", "text": "An open bomb site with clear approaches to attack and hold" }
  ],
  "notes": []
}
```

### Field rules

| Field | Rule |
| :---- | :---- |
| `genres` | Slugs matching the loaded filenames, **dominant first**. `[]` for no-genre and P5. |
| `shape` | `id`, `type`, and `name` split from the shape row's `**Type (Flavor Name)**`. A shape with no type emits `"type": null`. |
| `preset` | The generic display name, or `null` if the user tuned from scratch. **Never the *Modelled on* text.** |
| `pipeline` | `["P0"]` when nothing adds cost. Otherwise **list only the modifiers** — P0 is the baseline and is dropped once anything else is present. |
| `image_prompt` | One entry per `image` or `both` pick. |
| `layout_placement` | One entry per `layout` or `both` pick. `type` is the Shared Vocabulary term — the part before the parenthesis in the option name. |
| `text` | The option's **What it is**, which is written to be lifted more or less directly into a prompt. Trim it to the visible half for `image_prompt` and the functional half for `layout_placement` when a `both` option splits cleanly. |
| `notes` | Anything the pipeline should know but cannot act on: a close shape call, a `CHECK` to look at, a request no option covered, and any **preset caveat** from the loaded file. |

**Bend `text` toward the prompt's subject.** The wording is a template, not a
quotation. `building-interior` reads "a house, apartment, or compound entered
from outside," but for an abandoned mall, write the mall — "a derelict shopping
mall entered from the parking lot." Keep the structural content that makes the
option what it is; replace the placeholder subject with the real one.

An option tagged `both` appears in **both** lists, under the same ID. Empty
lists are valid — a user who picked nothing emits empty lists and `["P0"]`.

**Free text that matches no option still goes in the lists**, with `id: null`
and the user's own words as the text, classified by the rule in step 5. A
crashed helicopter in the courtyard is `{ "id": null, "text": "a crashed
helicopter in the courtyard" }` in `image_prompt`. Only put it in `notes` if it
cannot be built at all.

### The two special cases

**No genre.** There is no shape row, so `id`, `type`, and `name` are all
`null`, and the five axes carry the answer instead. Omit any axis left at its
default; `"axes": {}` when every axis is default, which is the common case and
routes `["P0"]`.

```json
{
  "genres": [],
  "shape": { "id": null, "type": null, "name": null,
             "axes": { "enclosure": "transition", "verticality": "stacked" } },
  "preset": "Explorable Place",
  "pipeline": ["P3", "P2"],
  "image_prompt": [ "..." ],
  "layout_placement": [],
  "notes": []
}
```

**P5.** Emit the determination and nothing else, so the caller has a reason to
show rather than a silent stop.

```json
{
  "genres": [],
  "shape": null,
  "preset": null,
  "pipeline": ["P5"],
  "image_prompt": [],
  "layout_placement": [],
  "notes": ["P5: folding paper is object manipulation with no space to move through."]
}
```

## Maintenance

`genres/*.md` are generated from `docs/LayoutGen - Build.md` Part II, which is
canonical. Edit Build.md, then run:

```bash
python tools/generate_genre_skills.py
```

`--check` verifies the files are current and exits non-zero if not.
