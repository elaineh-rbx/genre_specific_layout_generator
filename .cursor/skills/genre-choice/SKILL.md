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
- [ ] 0. Triage what the prompt is asking for
- [ ] 1. Classify the prompt
- [ ] 2. Load the matching reference file(s)
- [ ] 3. Offer a preset
- [ ] 4. Tune, if the user wants to
- [ ] 5. Ask what is missing, then the open question
- [ ] 6. Emit
```

## 0. Triage the prompt

**Most prompts describe a game, not a scene.** Sort what the prompt says into
three piles. The first two are yours to build. The third is recorded and handed
on — **never discarded, and never counted against you.**

**Scene, stated outright.** Geometry the prompt names: "a fountain in the
middle", "three lanes", "a forest across the map". Build it.

**Scene, implied by a rule.** A gameplay statement that cannot be true unless
something exists in the map. **This is the pile that gets missed.** "Reaching
the exit wins" is a win condition — and it also means there *is* an exit, and an
exit is a place. "Drag a tower onto an allowed area" means the allowed areas are
geometry. "Waves get harder each round" means the waves enter somewhere. Read
past the rule to the place the rule needs, and build the place.

**Reason forward from the genre, too**, because a genre presupposes geometry the
prompt may never mention. A maze has an entrance and an exit whether or not
either was named — and a centre worth asking about, or a second exit, because
those are scene decisions the user may have an opinion on. A race has a start
and a finish. A tower defense has a spawn mouth and something being defended.
None of these are win conditions. They are **the geometry a win condition
presupposes**, and working them out is your job rather than something to look
up: no list here could anticipate the genre and prompt in front of you.

**Not scene.** Currency, scoring, round counts, level curves, controls, camera
behaviour, menus, buttons, HUD, audio, matchmaking, player and team counts. Put
them in `mechanics` so the stream that owns them receives them intact. **Do not
ask about them, do not hunt for an option to hold them, and do not treat them as
something you failed to cover.** A prompt can be three-quarters mechanics and
still be completely served by a correct map.

> A tower-defense prompt asked for coins, a shop button, rounds up to 50,
> drag-and-drop placement, and a range indicator shown while dragging. Four are
> UI and progression and belong in `mechanics`. The fifth is geometry: the
> placement areas. The build shipped `buildzone-grid` either side of the lane,
> `spawner-npc` at the mouth and `tracker-core` at the end. The map was
> complete. Nothing was missing, and a scorer counting the other four as misses
> would be measuring the wrong thing.

**This step and step 1 inform each other**, since you cannot reason forward from
a genre before you have one. Triage what is plainly there, classify, then sweep
the second and third piles again with the genre in hand. Two passes is normal.

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

**When the user names a genre, start from what they named.** Prompts often
self-declare — "Genre: Open-world Action RPG / Survival", "a casual strategy
auto-battler", "a 1+ speed clicker". That is the strongest single signal
available and it is routinely lost to a more vivid detail further down the
prompt. A parkour course described inside a clicker does not make the game an
obby; it makes it both, with the clicker named first.

Override a self-declared genre only when the described gameplay plainly
contradicts it, and **say so in `notes`** when you do. If the declaration names
two genres, that is a mix and both go in `genres` — the user already did the
classification.

**Match the user's words to the index, not to the genre name.** Users write
"clicker", "tycoon", "simulator", "grinder", "escape", "tower" — the *Recognise
from* column exists for exactly this. `clicker` is Simulation. Do not route a
clicker to P5 on the strength of the word alone; see stage B.

**Skip the question if stage B is plainly going to answer No.** Asking a user
to elaborate on their origami game, only to tell them there is no map to build,
wastes a round trip. Go straight to stage B.

### Stage B — is there a space?

**Two questions in this order, and do not merge them.** Merging them is the
single most common way this step goes wrong.

> **1. Is there a space at all?**
> **No** → route **P5**, emit the block in step 6, and stop. Do not offer options.
> **Yes** → ask question 2.

> **2. Does anyone walk through it?**
> **No** → continue to step 2 as normal, and add **`SET`** to `pipeline`.
> **Yes** → continue to step 2.

**Almost everything has a space.** P5 is for a prompt that is not a 3D game —
a chat-only quiz, a 2D screen game, a bare music player with no room around it.
Nothing else, and **genuinely non-3D prompts are very rare**, so if you are
about to emit P5 you are very probably wrong.

`SET` is the answer for the large middle: a space that is real and built and
never walked on. A floating board game, a chess table with two chairs, a
click-to-earn idle screen, a shooting gallery on rails, a diorama the camera
orbits. **Build all of it.** `SET` tells the pipeline to skip traversal
segmentation and jump-gap validation, because nothing needs to be reachable —
it does not skip the build.

`SET` sits alongside the route, it does not replace it: `["P0", "SET"]`,
`["P3", "SET"]`.

**Judge the concept, not the keyword.** "A music game where you hit notes to a
beat" is `SET` if there is a stage to look at and P5 only if it is bare UI. "A
music venue where people hang out and listen" is an ordinary walkable place —
Entertainment's `venue-stage`. An idle clicker is a `SET`, and usually a
Simulation tycoon you happen to leave running.

**When genuinely torn, build.** An unnecessary map costs less than a wrongly
refused one, and `SET` makes the cheap version available — you no longer have
to choose between a full traversal build and nothing.

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
| Shooter | `genres/shooter.md` | guns, FPS, deathmatch, battle royale, tactical, PvE waves, **aim trainer, shooting range, gun testing** |
| Simulation | `genres/simulation.md` | tycoon, simulator, farming, jobs, vehicles, mining, sandbox, **clicker, idle, incremental, rebirth, upgrade grind, "+1 speed", speed/strength training** |
| Strategy | `genres/strategy.md` | tower defense, RTS, unit placement, base defense, board games |
| Survival | `genres/survival.md` | survive, escape, killer, disaster, horror chase, resources |
| Sports | `genres/sports.md` | football, basketball, golf, stadium, scoring, teams on a field |
| Racing | `genres/racing.md` | race, laps, track, finish line, speed, driving competitively |
| Infinite Runner | `genres/infinite-runner.md` | endless runner, auto-run, dodge obstacles, subway-surfers style |
| Entertainment | `genres/entertainment.md` | showcase, hub, portals, environment demo, hangout to look at, **concert, festival, talent show, club, any stage with an audience** |

Two taxonomy notes, because users echo Roblox's own wording:

- Roblox files **Runner** under Obby & Platformer. A prompt saying "runner" or
  "endless obby" means Infinite Runner here.
- Roblox has one **Sports & Racing** genre. Split them by finish condition: a
  lap or finish line is Racing, a scored field or court is Sports.

**One family that hides behind other genres.** "+1 speed" games — grind a stat,
break a barrier the stat unlocks, buy upgrades, rebirth — borrow their activity
from whatever is convenient, so they read as an obby if the grind is a parkour
course, a puzzle if it is a keyboard escape, a racer if it is a lane. **They
are Simulation**, preset *Stat Grinder*, and the tell is that the number going
up is the game. Getting this wrong is not cosmetic: leading with Obby imports a
genre-wide P6 these games never needed. Name the second genre; do not let it
lead.

## 2. Load

**A stage A outcome of None loads `no-genre.md` and no genre file.** It has the
same sections as a genre file, Universal Options included, and the rest of this
skill applies to it unchanged. It is the right answer often enough to be an
ordinary destination rather than a last resort —
inventing a genre to avoid it builds a map the user never asked for.

Otherwise: **load the dominant genre first, and check its presets before
loading anything else.** A genre's presets often already cover what looked like
a second genre — Obby's *Vehicle Obby* covers "you can drive cars," so "an obby
where you drive cars" is not a mix.

**If a second genre is still doing real work after that check, load it.** What
you lose by skipping it is its **presets and its wording** — its options stay
reachable through `options.md` either way, but a preset is a bundled answer you
will not reconstruct from a catalogue row, and a sentence written for that genre
beats a neutral gloss. Two files is normal and costs nothing that matters. Three
is rare. Never read all fifteen.

**Read every preset in a loaded file before deciding none fits.** Presets are
named from published taxonomies, so the name often will not echo the user's
words — a prompt asking to "spell the word that shows up on the screen" is the
*Word / Quiz Puzzle* preset even though it never says puzzle or quiz. Match on
what the preset builds, not on whether its name appears in the prompt.

Each file holds a **Typical shapes** line (pick exactly one shape), sometimes an
**Its own wording** table, an **Options** table (combine freely), **Presets**,
**Genre notes**, and a **Universal Options** table. The notes carry boundary
rules worth checking your classification against, and sometimes cite Build.md
Part I for the engine baseline behind a number — that is background, not
something you need to read to execute this.

### Shapes are shared; the genre's list is only the shortlist

**Every shape in the system is reachable from every genre.** A genre's *Typical
shapes* line names the handful worth putting on screen and marks one
*(default)*. It is presentation, not a menu of what is permitted.

**When none of the typical shapes fits, read `shapes.md` — the whole catalogue —
and take any row in it.** Then say which shape you took, that it came from
outside the genre's usual set, and what it routes.

When a genre's shapes all seem to assume something your prompt is not, the
shape you want almost always exists one genre over rather than not at all. A concert inside a roleplay town wants
`venue-stage`; a fairground shooting gallery wants `range-directed`. Neither is
filed where you would look.

**Do not load `shapes.md` by default** — reaching for the whole catalogue when
five rows would do is how a short menu becomes an unusable one.

**A genre may reword a shape, never re-route one.** Where its wording differs
from the catalogue's, inject the genre's sentence: same ID, same route, its own
words, exactly as shared options work.

**And if the whole catalogue misses, describe the shape** rather than forcing
the nearest wrong answer — no ID, the five routing axes answered directly, the
user's own words as the description. `shapes.md` carries the rules; the bar is
one specific sentence, *name the catalogue shapes you rejected and why*, and if
you cannot write it then a catalogue shape fits. The emit form is under **The
three special cases** below.

**Universal Options are part of every genre's menu.** The same six rows are
appended to all fifteen files — who inhabits the space, enterable interiors,
water, settlement density, terrain relief, and island clusters. They are
genre-neutral environment features, so their wording is generic and **must** be
bent to the prompt's subject before it is emitted. Where a genre defines the
same ID in its own words, the genre's row wins.

### Options are shared too, on exactly the same terms

**Every option in the system is reachable from every genre.** The genre's table
is its shortlist and its wording, never the limit of what it can offer. Two
thirds of the options sit in exactly one genre's table, so a genre treating its
table as a fence reaches about a fifth of what the system can express — and the
row the prompt wanted is usually one genre over. A soccer prompt asking for a
lobby wants `social-hub`, which Sports does not list. A temple filling with lava
wants `hazard-kill`, which Puzzle does not list. Neither is missing; both are
filed elsewhere.

**So when the prompt asks for something the genre's table has no row for, work
down this order and stop at the first hit:**

| | Where you look | Why it is in this position |
| :---- | :---- | :---- |
| 1 | The loaded genre's own **Options** table | It has the wording written for this genre, and the ● marks tell you what is signature. |
| 2 | The six **Universal Options** | Most apparent misses are one of these in the prompt's clothes. A costume shop, a blacksmith, a pet store and a gear exchange are all `building-interior`. |
| 3 | **`options.md`** — the whole catalogue | The row exists and is filed under a genre you did not load. Say which genre you took it from. |
| 4 | `"id": null` with the prompt's words | Only after 1–3 genuinely miss. |

**Step 4 costs something the others do not, which is why it is last.** A
free-text pick carries no route, because the route comes from the row. Shipping
"a shop players can walk into" as free text drops the `P3` that
`building-interior` would have carried, and the build produces a facade instead
of an enterable room. Reach for an ID while one still fits.

**Do not load `options.md` by default.** Same reason as `shapes.md`: it is for
when the genre's table and the universal six have both missed.

**Take the ID; write the words from the prompt.** The ID is the dedupe key and
the route. The sentence in the catalogue is a neutral gloss, not something to
inject — Puzzle reaching for `hazard-kill` ships "lava rising through the temple
floor," not Action's bottomless pits. This is the universal-option rule applied
to the whole table.

**Three rows route differently depending on what the prompt meant**, and
`options.md` marks them *varies*. `spectator-zone` is `P0 + tiered` as raked
stands and P0 as a dugout. `teleporter-link` is `P4` as a portal to a separate
place and P0 as fast travel inside one map. `path-road-vehicle` is `P6` where
the road *is* the course and P0 where it is a street. Pick the route matching
the thing described, and say that you did.

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
volume self-occludes · `SET` real geometry that nobody walks on, so traversal
and jump-gap checks are skipped.

### Mixing genres

**Naming a second genre is free. Taking a second shape is not.** Keep these
apart — only the second one costs anything, and conflating them is the most
common classification error there is.

**One shape, chosen once — and it may come from anywhere.** A game still has
exactly one shape, because honouring several stacks pipeline cost out of a
single sentence. What no longer applies is that the shape must belong to the
dominant genre: shapes are shared, so pick whichever one actually describes the
space and name it. An action RPG whose defining feature is the dungeon takes
the dungeon shape without Action having to lose the argument first.

**The dominant genre does still own the genre-wide route** — Obby, Racing and
Infinite Runner are P6 whatever shape is chosen, and that P6 does not follow
the genre into a mix it does not lead.

**And it owns the wording.** Where two genres describe the same shape or option
differently, inject the dominant genre's sentence.

Secondary genres contribute **options** — union them and **drop duplicate
IDs**, presenting each concept once — and their **presets**, see step 3.

**But name it in `genres` regardless.** A game that is honestly two things is
recorded as two things. Losing the shape contest does not make a genre untrue,
and the downstream pipeline reads that list. Under-naming is not the safe
default it looks like: it also means the secondary genre's options table never
gets loaded, so features only it could express are gone before anyone notices.

The dominant genre is the one the sentence is *about*. "An obby but also you
can drive cars" is an obby. "A zombie shooter where you hold out against waves"
is a shooter. When a prompt is genuinely balanced, prefer the genre whose shape
is cheapest, and say in `notes` that it was close.

Four cases that need two genres, all drawn from real prompts that got one:

| Prompt, in brief | Emit |
| :---- | :---- |
| Stack milk crates into a staircase, then **race to climb to the top and back down** without it collapsing | `["simulation", "obby-platformer"]` — the stacking is the sim, the climb is the win condition |
| Self-described **"Open-world Action RPG / Survival"**, with quests, leveling, bosses, crafting, dungeon raids | `["rpg", "survival"]` — both stated in the prompt's own words |
| "An exact replica of the **Blox Fruits first sea**" | `["rpg", "adventure"]` — the reference is a leveling combat RPG, not just an explorable region |
| A **"1+ speed clicker"** where you buy anime characters with wins earned on a parkour course | `["simulation", "obby-platformer"]` — an upgrade progression wrapped around an obby earning loop |

**Two is the normal ceiling.** Three is rare and usually means the prompt is
being over-read. More than three means the dominant genre was never found.

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

**Drop preset options the prompt contradicts.** Do not carry one through just
because the preset lists it. Keeping `obstacle-maze` on a house-decorating
prompt builds a maze into the house — the wrong option is not inert, it is an
instruction to the image model.

### The preset's shape is a default you may replace

A preset is a shape **plus** options, and the two are independent. Options can
be added and dropped one at a time; shape is exclusive, so a preset whose mode
fits and whose shape does not would otherwise force a choice between a
contradicted map and no preset at all.

**Swap in any other shape and keep the options** — the genre's typical list
first, and `shapes.md` when none of those fits either. Then say so:

- Tell the user, in the offer, which shape you took instead.
- Quote the pipeline cost of **the shape you actually used**, not the preset's.
- Put a line in `notes` naming the preset, the substituted shape, and why.

> A prompt describing dispersed points of interest still gets *Team Deathmatch*
> — team bases, cover arrays, chokepoints — but on `open-battlefield` rather
> than the preset's `lane-network`, because the prompt said the opposite of
> lanes.

**Stop when the preset is no longer recognisable.** If you have swapped the
shape *and* dropped most of the options, you are building from scratch: say so
and emit `preset: null`. Keep the shape or keep most of the options, not
neither.

A **secondary genre's preset is fair game** for the same reason — taking its
options no longer drags its shape along.

If nothing fits well, skip to step 4.

## 4. Tune

Only if the user wants to. Show, at most:

- The **shape** question, if the prompt has not already answered it. Offer the
  genre's *Typical shapes* — that list is sized for this cap.
- The **`Core`** options they do not already have.

**Cap it at roughly five items on screen.** Never paste a whole table.

**Do not ask what the prompt already told you.** "A tower obby" has answered
shape. "Zombies chasing you through a mall" has answered shape and threat.
Confirm briefly instead of asking.

Say the pipeline cost in plain language when a pick carries one — "that needs
interiors generated separately, which is a slower build" — not as a code.

### Route from what the game is, not from what is built yet

**The route follows the intent. Readiness never overrides it.** P0 and P6 are
running today and P2, P3, P4 and `CHECK` are not ready. That is a fact about the pipeline's
schedule, not about the prompt, and bending a route to fit it would make the
handoff describe a game nobody asked for. A game that needs several maps needs
several maps whether or not P4 ships this quarter — emit `P4` and let the step
that knows the pipeline's state decide what to do about it. Re-routing is a
later concern and a separate system; **your job is to be right about the game.**

**Where the prompt is genuinely silent, take the route that stays on P0 or
P6.** This is a tie-breaker for silence and nothing more. It never competes
with a stated feature, and if you find yourself weighing the two, the feature
has already won.

**Read for the feature, not for the keyword.** This is where the rule goes
wrong if you rush it. A prompt never has to say "interior" to need `P3` —
"houses you sleep in", "shops you buy from", "temples with a boss inside" all
require going indoors. Much of the `P3` that looks assumed is really this.
**If the game plainly has the feature, the modifier is required.** What you are
steering is the judgement calls — *is this several maps or one*, *does anything
overhang*, *is the play volume 3D* — not whether a stated feature exists.

**A preset's own shape can carry a modifier, and that is not a reason to reject
the preset.** The city-traversal shape behind a web-swinging prompt is `P2`; if
that is the game, it is the route.

**Never push away from P6.** It is proven. An obby stays P6.

**Say what you did and offer the upgrade.** Never downgrade silently:

> Building this as one continuous map. Separate zones per biome is possible but
> isn't ready yet — say the word and I'll note it for when it is.

Put the deferral in `notes` so the pipeline knows what was set aside.

### When the shape's route contradicts the prompt

A shape row says what the space is like *and* how to build it. If the prompt
matches the description but rules out the build, **keep the shape and change
the route** — the shape was not wrong about the space.

This is rare and the bar is high. **Silence is not a contradiction**; when the
prompt says nothing about the route, take the default. Only act on an explicit
statement, and only for these:

| Route | Override when |
| :---- | :---- |
| `P4` on `world-biomes`, `world-open-biomes`, `world-chaptered`, `space-staged`, `world-hub-dungeon`, `hub-portals` | The prompt says one continuous map — "one big map", "seamless", zones joined by bridges or roads. Route `P0`. |
| `P3` on `settlement-claimable`, `settlement-buildable` | Nobody goes inside; the houses are facades. |
| `P2` on `arena-stacked`, `world-underground`, `route-multitier` | Nothing actually overhangs anything. |

**Never override a `P6`**, from a shape or from a genre. Obby, Racing and
Infinite Runner are P6 whatever shape they take, and `warren-looping`,
`lane-actor-track` and `puzzle-maze` carry it individually. In all of them the
structure has to be valid or the game does not work — an image model cannot
guarantee a solvable maze or a connected circuit, so dropping the P6 does not
make the build cheaper, it makes it broken.

Put the override and its justification in `notes`, and tell the user:

> Graded danger zones, but built as one continuous map since you asked for one
> big world — so it's a single-pass build rather than a separate map per zone.

### The run needs somewhere to end — but never ask how it is won

**Do not ask the user how the game is won.** A win condition is gameplay, not
layout: a ring-out and a bomb defusal share an identical map. It is the single
biggest thing intake is tempted to ask and can do nothing with, and most of
what gets asked is progression wearing a goal's clothing — where an item
spawns, what unlocks next. None of it reaches the image model or the placement
pass.

**What layout needs is the place the run ends**, because a map with no reachable
exit, finish, or objective fails validation — F6 in `LayoutGen - Pipeline.md`.
That part is spatial and already has homes: the shape says whether the space
loops or terminates, and `winner-zone` places the payoff.

**So infer it from the genre and the preset.** A race ends at the finish line,
an obby at the top, a maze at the exit. Emit the option that expresses it and
record the assumption in `notes`.

**One case earns a question**, and it is a shape question rather than a goal
one: when the prompt leaves genuinely open whether the space terminates at all.
*"Is there an end to this, or is it endless to roam?"* decides between a bounded
course and a loop, and that changes the map. Ask it that way.

## 5. Ask what is missing

**Ask about the holes, not in general.** There is no list of approved questions
to pick from — you write them from the prompt in front of you. What is fixed is
which holes are worth asking about and what shape the asking takes.

**One hole, one question, and the hole is always one of these.** Everything else
either was not yours (step 0) or is not worth a round trip.

| Hole | Ask when |
| :---- | :---- |
| **genre** | Stage A came back Unrecognised, or two genres fit and they lead to different shapes |
| **shape** | Nothing in the catalogue is clearly right, or two shapes fit and they route differently |
| **option** | A named thing could be built more than one way, and the ways differ in what gets built |
| **scale** | The prompt names an extent without naming what lives in it — see `layout-intake` |
| **theme** | The prompt says nothing about how it should look |

**Offer the answers. Do not ask for them.** Roughly three in four of your
questions should be a choice between named candidates, and you already hold the
candidates: the genre's typical shapes, the two options that both fit, the four
scale bands. A question with an answer space of four known values asked in the
open is how run 1 got told *"a trillion blocks."* If you can enumerate the
plausible answers, enumerate them.

**One subject per question.** *"Fountain or lake — which one, and how big?"* is
two questions and gets one answer, usually to the wrong half. Ask which, or ask
how big, and let the other ride on an assumption you state.

**Four questions is the ceiling and most prompts need fewer.** The final
"Anything else?" is part of those four, not a fifth question. Order by what
changes the build most: anything that moves the route or the shape outranks
theme. If a fifth is tempting, assume the least consequential one instead and
say in `notes` what you assumed.

**Never ask how the game is won, how many players it has, or anything else from
step 0's third pile** — see *The run needs somewhere to end* above. Asking about
the *place* the rule needs is fine and often necessary: not *"how do you win?"*
but *"is the exit a door out of the maze, or a room at the centre?"*

**Ask about a term you genuinely do not understand.** This is the one case where
open text beats a choice, because you cannot enumerate what you cannot parse. A
prompt saying "tmod" gets *"What does 'tmod' mean here?"* rather than a guess
dressed as a choice.

**Then close with the open one**, which is the only question that is not
targeted at a hole:

> Anything else you want in the space?

Classify whatever comes back yourself; there is no table row to look up:

**If a segmenter could identify it as geometry, it is `image`. If it is an
invisible volume, a marker, a trigger, or a property of geometry rather than
geometry itself, it is `layout`.**

A shrinking play boundary is `layout` — it has no geometry at all. A ruined
cathedral is `image`. A "checkpoint" is `both`: the pad is drawn, the respawn
is placed. If a request implies a shape change, say so and its cost before
accepting it.

**If the request matches an option, promote it to that option** so it dedupes
like any other pick, folding the user's wording into the text so the specifics
survive. **Work the same order as step 2** — the loaded genre's table, then the
universal six, then `options.md`, and only then `id: null`. An answer to this
question is not a lesser kind of request, so it does not get a lesser search.

"A giant neon sign you can see from anywhere" is `landmark-focal`, keeping the
user's neon sign as the text. It is in the catalogue, so it is a real pick here
whether or not the genre you loaded happens to list it. Free text is for what
the catalogue genuinely does not hold — a crashed helicopter in the courtyard —
and it costs the route, so it is the last resort rather than the easy one.

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
    { "id": "capture-zone", "text": "An open bomb site with clear approaches to attack and hold" },
    { "id": "island-cluster", "text": "Five rocky islets ringing the harbour", "count": 5 }
  ],
  "layout_placement": [
    { "id": "spawn-teambase", "type": "SpawnZone", "text": "Balanced bases at opposite ends, shielded from sniper lines" },
    { "id": "capture-zone", "type": "CaptureZone", "text": "An open bomb site with clear approaches to attack and hold" }
  ],
  "mechanics": ["Rounds are best of thirty", "Buy menu between rounds"],
  "notes": []
}
```

### Field rules

| Field | Rule |
| :---- | :---- |
| `genres` | Slugs matching the loaded filenames, **dominant first**. `[]` for no-genre and P5. |
| `shape` | `id`, `type`, and `name` split from the shape row's `**Type (Flavor Name)**`. A shape with no type emits `"type": null`. When no catalogue shape fits, emit the **described** form below instead. |
| `preset` | The generic display name, or `null` if the user tuned from scratch. **Never the *Modelled on* text.** If you substituted a shape or dropped one of its options, keep the name and record what you changed in `notes`. |
| `pipeline` | `["P0"]` when nothing adds cost. Otherwise **list only the modifiers** — P0 is the baseline and is dropped once anything else is present. `SET` is the exception: it is a build-mode flag rather than a cost, so it is appended to whatever route applies and keeps `P0` alongside it — `["P0", "SET"]`. **Only options that are actually part of the build contribute a modifier.** An option you set aside because the prompt contradicts it does not price the route, even if you kept it recorded somewhere — a tag game whose preset offers `obstacle-maze` is not procedural-first because of a maze nobody asked for. |
| `image_prompt` | One entry per `image` or `both` pick. |
| `layout_placement` | One entry per `layout` or `both` pick. `type` is the Shared Vocabulary term — the part before the parenthesis in the option name. **An entry with no `type` is malformed.** The type is what tells the pipeline which volume to create, so an entry missing it reaches the pipeline and does nothing. It is never a judgement call: the option row you took the pick from prints it. `spawner-npc` is **Spawner (Enemy Wave Origin)**, so the type is `Spawner`. Copy it across; do not leave it out because the text seems self-explanatory. |
| `text` | The option's **What it is**, which is written to be lifted more or less directly into a prompt. Trim it to the visible half for `image_prompt` and the functional half for `layout_placement` when a `both` option splits cleanly. |
| `mechanics` | The third pile from step 0, in the user's own words, one entry each — scoring, currency, rounds, progression, controls, camera, UI, audio, player and team counts. **Kept separately from `notes` because it is addressed to a different reader:** `notes` is for the layout pipeline, this is for the stream that builds the game. Never empty on a prompt that described gameplay, and having entries here is a sign of correct triage rather than of something dropped. |
| `count` | **Optional.** The number the prompt stated for this pick — "five islands", "three floors", "about twenty houses". Omit it entirely when no number was given. Record what the user said, not a normalised value; "a few" is not a count, so leave it out and keep the words in `text`. Nothing else in the handoff can hold a number — the scale band is a four-value enum — so a stated quantity dropped here is lost. |
| `notes` | Anything the pipeline should know but cannot act on: a close shape call, a `CHECK` to look at, a request no option covered, and any **preset caveat** from the loaded file. |

**Bend `text` toward the prompt's subject.** The wording is a template, not a
quotation. `building-interior` reads "a house, apartment, or compound entered
from outside," but for an abandoned mall, write the mall — "a derelict shopping
mall entered from the parking lot." Keep the structural content that makes the
option what it is; replace the placeholder subject with the real one.

An option tagged `both` appears in **both** lists, under the same ID. Empty
lists are valid — a user who picked nothing emits empty lists and `["P0"]`.

### When the prompt names more than one space

**One shape is the rule, and `segments` is how you keep the rest.** Honouring
several shapes at the top level stacks pipeline cost out of control, which is
why step 3 makes you choose. But choosing is not the same as discarding: a
prompt naming a dance studio and a performance theatre gets one shape and the
theatre used to be demoted to an option, losing its own layout entirely.

Emit `segments` whenever the prompt names distinct spaces that would be built
differently. Each entry carries its own shape and its own lists:

```json
  "segments": [
    { "name": "Studio", "kind": "zone", "shape": { "id": "venue-stage", "type": "Zone", "name": "Performance Venue" },
      "theme": null, "image_prompt": [], "layout_placement": [] },
    { "name": "Theatre", "kind": "zone", "shape": { "id": "rooms-sequence", "type": "Path", "name": "Room Sequence" },
      "theme": "Art deco proscenium house", "image_prompt": [], "layout_placement": [] }
  ]
```

| Key | Rule |
| :---- | :---- |
| `name` | The user's own word for the space — "Desert Base", "the lobby", "Floor 3". |
| `kind` | `map` when they are separate places a player loads into, `zone` when they are regions of one map. `map` is what `P4` means; several `zone`s do **not** route P4. |
| `shape` | The same three-part form as the top-level shape, or `null` for a space the user named but never described — "the other nine maps in the rotation". Name it and leave the shape open rather than inventing one; a named segment with no shape is a known hole, an invented shape is a wrong answer that looks right. |
| `theme` | Only when this space looks different from the build's theme. `null` otherwise — do not repeat the top-level value. |

**The top-level shape is either the largest of the segments or the thing that
contains them, and which one decides whether it repeats.** Both readings are
ordinary and the difference is not a judgement call:

- **One space dominates and the others sit beside it** — a stage with a dance
  studio off it. The top-level shape is that dominant space, and it appears
  again as the **first entry**, so a consumer that ignores `segments` still
  builds the main space from the fields it already knows.
- **One space contains all of them** — an open-world city divided into a
  downtown, a docks and a prison. The top level is the container (`world-open`),
  the segments are what it is divided into, and **no segment repeats the
  top-level shape** because none of them is it.

Several shapes are containers by definition and are the natural top level
whenever the prompt names their parts: `space-staged` is *Lobby and Isolated
Stage*, `world-chaptered` is chapters as separate maps, `world-hub-dungeon` is a
hub feeding instances. Naming one of these above a list of its own parts is the
shape doing its job. **A container's segments need not be zones** — a lobby and
an arena under `space-staged` are two `map`s, which is why these shapes carry
`P4` in the catalogue.

What is wrong is a top-level shape that is neither one of the segments nor able
to hold them. A single-space shape sitting above a list of separate maps means
the shape above is the wrong one.

Omit `segments` entirely for the ordinary single-space prompt.

**`P4` and `segments` must agree.** If the route says separate maps, there are
at least two `map` segments saying which. A bare `P4` with nothing to describe
it tells the pipeline a split exists and not what is on either side of it.

**Free text that matches no option still goes in the lists**, with `id: null`
and the user's own words as the text, classified by the rule in step 5. A
crashed helicopter in the courtyard is `{ "id": null, "text": "a crashed
helicopter in the courtyard" }` in `image_prompt`. Only put it in `notes` if it
cannot be built at all.

**Free text may enter `layout_placement` only if you can name its Type**, and
then it carries that type with `id: null` — six claimable house lots are
`{ "id": null, "type": "Plot", "text": "six claimable house lots with
driveways" }`, and an inspect point in front of a portrait is a `TriggerZone`.
**If no Shared Vocabulary term fits it, it is description, not placement, and it
belongs in `image_prompt`.** A crashed helicopter is scenery; it goes in the
image list and nowhere else. The test is the type, not how spatial the request
sounds — an untyped entry in the placement list is the one thing that reaches
the pipeline looking like work and is not.

### Before you emit, check these two things

Both take a few seconds and both catch a failure that is invisible afterwards.

1. **Every `layout_placement` entry has a `type`.** See the rule above.
2. **Every request you could not match appears somewhere in the handoff.** A
   request that got no option should be free text in one of the two lists, or in
   `notes` if it cannot be built at all. Losing it entirely is the worst outcome
   available: the user asked for something and no part of the system now knows.

### The three special cases

**No genre.** There is no shape row, so `id`, `type`, and `name` are all
`null`, and the five axes carry the answer instead. Omit any axis left at its
default; `"axes": {}` when every axis is default, which is the common case and
routes `["P0"]`.

```json
{
  "genres": [],
  "shape": { "id": null, "type": null, "name": null,
             "axes": { "axis-enclosure": "transition", "axis-verticality": "stacked" } },
  "preset": "Explorable Place",
  "pipeline": ["P3", "P2"],
  "image_prompt": [ "..." ],
  "layout_placement": [],
  "notes": []
}
```

**A described shape**, when a genre is known but nothing in the catalogue fits.
Same axis form, plus `text` in the user's own words and `rejected` naming the
catalogue shapes you turned down.

```json
{
  "genres": ["simulation"],
  "shape": { "id": null, "type": null, "name": null,
             "text": "a single skyscraper, played floor by floor from the lobby up",
             "axes": { "axis-enclosure": "interior-only", "axis-verticality": "stacked" },
             "rejected": [
               { "id": "interior-single", "why": "one enclosed space; this is forty stacked ones" },
               { "id": "world-underground", "why": "layers, but its whole description is below ground" }
             ] },
  "preset": null,
  "pipeline": ["P2"],
  "image_prompt": [ "..." ],
  "layout_placement": [],
  "notes": ["described shape: interior-only + stacked"]
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

`genres/*.md`, `shapes.md`, `options.md` and `no-genre.md` are generated from
`docs/LayoutGen - Build.md`. **Never edit them directly** — edit Build.md and
run `python tools/generate_genre_skills.py`.
