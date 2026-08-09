# LayoutGen — Golden Set Evaluation

What happened when the layout-intake skill network was run against 620 real
user prompts, and what the results say we should change.

Source data: `evaluation/data/layout gen prompt golden set  - build 600 (prod subgenre balanced).csv`
Annotated output: `evaluation/data/golden set 600 - genre and coverage eval.csv` (+24 columns)
Raw records: `evaluation/data/records/batch-*.jsonl` (628 records)
Aggregates: `evaluation/data/aggregate.json`

Row ids map straight to the spreadsheet: **`P0087` is line 87**, so any claim
below can be checked by opening that row.

---

## 1. What was measured, and how

Each of the 620 evaluable prompts was run through the full intake flow — genre,
shape, preset, options, theme, scale band — by one of 62 workers who saw only
that prompt's text and an opaque id. **No worker ever saw the spreadsheet's own
genre label**, and the batches were shuffled so that batch composition could not
leak one. Verdicts were then computed by script rather than by any worker.

Three rows were excluded: two flagged `remove` in the source (one a
school-shooting prompt) and one whose cell was a spreadsheet error.

Two deliberate deviations from normal skill behaviour, both forced by running
without a human: workers could not ask clarifying questions, so they recorded
the question they would have asked instead; and an offered preset was treated as
accepted rather than as an unanswered question.

### Reliability of the measurement

Eight prompts were secretly issued twice, to different workers. A second,
accidental set of eight arrived later: worker 49 stalled at 2 of 10 records, a
rescue worker was given the missing 8, and the original then finished hours
later — so those 8 prompts were scored twice, blind, by workers who never saw
each other's output. Both samples are reported below.

| Measure | Planned 8 | Accidental 8 | Pooled |
|---|---|---|---|
| Genre | 5 of 8 | **8 of 8** | 13 of 16 (81%) |
| Shape | 5 of 8 | **8 of 8** | 13 of 16 (81%) |
| Pipeline route | — | 7 of 8 | — |
| Preset | — | **5 of 8** | — |
| Names given to the same asks | 0.27 | 0.33 | **~0.30** |

This is the most important table in the report, because everything else must be
read through it, and the shape of it is sharper than a single number.

**The structured decisions reproduce; the free-text vocabulary does not.** On
the accidental set, two workers agreed on genre 8 times out of 8 and shape 8 out
of 8, while naming only a third of the same asks. P0394 is the clean
illustration: identical genre, shape and route, and then `pop sound` versus
`pickup sound`, `shop menu` versus `purchase menu`, `speed meter` versus `stat
bar`, `character aura` versus `character cosmetic`. Same game, same
understanding, different words. P0220 does the same with `crew turf` versus
`territory claim` and `crew branding` versus `faction branding`.

That is the strongest single argument in this whole evaluation for a controlled
vocabulary in the context file: the disagreement is not about what users want,
it is about what to call it.

Counts of individual asks are therefore a **floor, not a census**, and the long
tail of apparent one-offs is substantially vocabulary variance rather than
genuine uniqueness. Every finding below that rests on a count is understated by
roughly 3–10× on the semantic merges' own estimate.

**Preset choice is the least reproducible structured field** — 5 of 8, against
8 of 8 for genre and shape. Two workers who agreed exactly on genre, shape and
route still disagreed on whether any preset applied: `Life` versus none on
P0220, `Classic Obby` versus none on P0394, `Childhood Game` versus none on
P0238. That corroborates §7 from an independent direction — the mechanism the
content analysis flagged as weakest is also the one measurement finds least
stable.

Read the two samples with one caveat: the planned 8 were spread across eight
different worker pairs, while the accidental 8 are a single pair scoring eight
prompts. Two workers who happen to agree well produce eight agreeing rows, so
the 8-of-8 results are one observation, not eight independent ones. The
vocabulary figure is the robust part — 0.27 and 0.33 from two
independently-constructed samples.

Two findings survived this noise floor so clearly that they are worth trusting
without qualification: the genre result in §2, and the missing-channel result in
§4.

### Two artifacts of the harness, not findings

- **`coverage: complete` is nearly unreachable.** It requires that no field was
  assumed, but intake instructs the scale band to be *inferred* rather than
  asked, so `scale.assumed` is true almost always. The resulting "6 of 620
  complete" figure measures the rubric, not the skill. Read the partial /
  insufficient split instead: **560 partial, 54 insufficient**.
- **`quantity` was only recorded for unmatched asks.** A number attached to a
  request that *did* match an option had nowhere to go, so the "numbers are
  lost" finding in §5 is understated rather than overstated.

---

## 2. Genre classification is sound

The one question with a clean answer.

Where our label differed from the spreadsheet's, two reviewers who could see
both decided which was better. Unlike every other stage, this pass was
deliberately *not* blind — with both answers already fixed, hiding one would
only handicap the referee.

| Outcome | Rows | Share |
|---|---|---|
| Agree outright | 458 | 74% |
| Defensible (secondary genre, P5, no-genre, or a label with no equivalent) | 71 | 11% |
| Disagreed — **ours better** | 60 | 10% |
| Disagreed — tie or taxonomy artifact | 21 | 3% |
| Disagreed — **spreadsheet better** | 8 | 1.3% |

**Our classification is at least as good on 610 of 618 prompts and worse on
eight.** Of 89 genuine disagreements we won 60 and lost 8.

The recurring reason we win: the spreadsheet reaches for a broad thematic bucket
where the prompt names a specific mechanic. A prompt reading *"you die because
of other animals or not drinking or eating"* was labelled roleplay because the
player is an animal, when a hunger-and-thirst loop is stated outright.

The eight losses are real and worth keeping. The clearest is a crate-stacking
prompt whose win condition is climbing to the top and back down without
collapse — we built a shared world where the request is a vertical traversal
challenge.

### But consistency within a genre is uneven

The spreadsheet carries its own `inferred_game_subgenre`, assigned
independently, and the golden set was balanced across it at ~20 prompts each.
That turns "do we treat like things alike?" into a measurement.

**On average 78% of a subgenre's prompts share our top genre.** The spread is
what matters:

| Subgenre | Prompts | Genres we used | Largest share |
|---|---|---|---|
| open_world_action | 20 | **9** | 35% |
| runner | 19 | 5 | 42% |
| physics_sim | 7 | 3 | 43% |
| open_world_survival_rpg | 20 | 6 | 50% |
| pet_care | 10 | 2 | 60% |
| … | | | |
| classic_obby | 20 | 3 | 85% |
| pve_shooter | 20 | 4 | 85% |
| deathmatch_shooter | 18 | 3 | 89% |

**Read this metric carefully — a low score has two possible causes.** Either we
are inconsistent, or the spreadsheet's bucket is loose. They have to be told
apart by reading the prompts, and for the worst-looking row it turns out to be
the second.

`open_world_action` (rows 283–302) holds a UFO beaming up cows, a Spider-Man
web-swinging city, a trampoline combo game, a Dragon Ball tournament arena, a
police-vs-robber sandbox, a city-destruction game, an airship war, and a
Chinese-language dungeon roguelike. **Those are not the same game, and splitting
them across nine genres is the correct answer.** The 35% is measuring Roblox's
bucket, not our inconsistency. Same for `physics_sim` at 43%.

The metric earns its keep where the bucket is *tight*. `runner` (rows 380–399)
is the real one: 8 prompts went to infinite-runner correctly, but "quickly run
down a road and jump over oncoming cars" landed in obby-platformer, and the
speed-training family scattered — `1+ speed obby` to obby-platformer, `slip and
slide … treadmills to train your speed` to racing, `bmx game but you have to do
an obby to gain speed` to racing. That is one game family with no home, which is
the same conclusion the family sweep reached from the other direction.

This table should be preferred over judgement-based family lists. A separate
sweep claimed horror-escape splits "almost evenly" between survival and puzzle;
the subgenre data shows `escape` is 80% concentrated in survival. That family is
fine. `animal_sim` at 70% is likewise less fragmented than it appeared.

### One family that is genuinely scattered

"+1 Speed" / Keyboard Escape — walk or click to earn speed, buy upgrades, break
through barriers — is a large, well-known Roblox family. Thirteen keyboard
prompts split across obby-platformer (6), puzzle (5), simulation (1) and
no-genre (1), drawing five different presets, with more non-keyboard members in
entertainment and racing.

Worth noting **how** this was found. It is invisible to every worker, because
each saw ten prompts and each instance looked locally reasonable. It is also
invisible to phrase-matching, because users write it as "+1 speed", "1+ speed",
"1+ keyboard escape" and in Arabic. It took reading across all 620 rows at once.

---

## 3. A concrete, reproducible defect: the Life preset

Three prompts name **Brookhaven** explicitly. All three matched the Life preset
and all three received `settlement-buildable` — a grid of empty lots players
build on. Brookhaven hands players **pre-built houses to claim**.

The preset names Brookhaven in its own *Modelled on* column, and the same genre
file's notes warn that player-built housing looks like the default and is
actually the least common model. So the preset gets the highest-cost decision in
the genre wrong, on the one game it was derived from, 3 times out of 3.

---

## 4. The largest finding: most of what users ask for has nowhere to go

3,785 recorded asks across 620 prompts. **1,406 belong to the layout pipeline;
2,379 do not.**

| Destination | Asks |
|---|---|
| image | 1,031 |
| mechanics | 781 |
| progression | 456 |
| constraint | 418 |
| ui | 383 |
| layout | 375 |
| sky | 101 |
| metadata | 100 |
| audio | 92 |
| unclear | 48 |

**The single most common ask in the entire dataset is the game's name.** 70
prompts state what their game is called and there is nowhere to record it.

Top asks after semantic merging, with where each would have to be routed:

| Ask | Count | Consumer |
|---|---|---|
| game title | 70 | metadata |
| leaderboard | 30 | ui |
| round timer | 29 | mechanics |
| currency | 24 | progression |
| drivable vehicle | 22 | mechanics, layout |
| sound effect | 20 | audio |
| boss arena | 19 | **layout** |
| player count | 19 | constraint |
| purchase menu | 17 | ui |
| day/night cycle | 13 | sky |
| floating island | 13 | **layout** |

Only two of those eleven are things the map pipeline could consume.

---

## 5. Missing layout options

942 clusters merged to 70 concepts; 61 of them at 8+ asks, covering 92% of
layout-pipeline asks. Recommended as new options, in priority order:

| Proposed option | Asks | Arrived under N names | What it must specify |
|---|---|---|---|
| **NPC / character population** | ~123 | 79 | Who is in the world: allies, vendors, crowds, ambient animals, named characters. Not `spawner-npc`, which means hostile waves. |
| **Interior rooms / enterable buildings** | 52 | 36 | Which buildings are enterable, how many rooms, named room types |
| **Water body** | 50 | 22 | Still / flowing / sea / underwater, extent, swimmable or barrier |
| **Settlement density** | 49 | 20+ | City / town / village tier, block spacing, building count |
| **Non-flat terrain** | 38 | 27 | Mountains, hills, cliffs, caves, chasms |
| **Island / archipelago** | 29 | 12 | Count, spacing, floating or sea-level |

**The NPC gap is the biggest single hole in the system**, and two independent
analyses reached it from different data: the layout merge found it the largest
concept in the map pipeline, and the context merge independently found that the
`unclear` bucket was "almost all descriptions of characters, enemies, and held
objects". Nothing anywhere can say who is in the world.

Also recurring, and probably one feature rather than eleven options: **eleven
separate "count of X" asks** (`room count`, `stage count`, `island count`,
`plot count`, `zone count`, `lane count`…). No field anywhere holds a number.

---

## 6. Missing channels — the context file

2,379 asks have no consumer at all. The good news from the merge: they are far
more structured than they look. Only about **6% genuinely resist structure**,
against a raw one-off rate of 77% — the difference is naming variance.

Proposed fields, with how much each absorbs:

- **progression (~470 asks):** `currencies[]`, `earning_rules[]`, `shop{sells,
  prices}`, `upgrade_targets[]`, `cosmetics[]`, `unlockables[]{thing, gate}`,
  `rarity{tiers, odds}`, `scoring{metrics, formula}`, `reset_loop`,
  `recurring_rewards[]`
- **ui (~330):** `hud.elements[]` as an enum absorbs ~99 asks that arrived under
  30+ names; `screens[]` absorbs ~175; then `world_markers[]`, `controls`,
  `dialogue`, `notifications[]`, `tutorial`
- **metadata (~106):** `title` alone is worth 70 asks — the largest single field
  in the design; plus `entity_names[]`, `story`, `deliverables[]`, `ip_flags[]`
- **sky (~99):** `time_of_day` (value *or* cycle), `lighting.mood`,
  `weather{conditions, dynamic}`, `fog`, `skybox`
- **audio (~94):** `music`, `sfx[]`, `ambience`, `voice`

**Add a destination the current list is missing: character and creature
appearance.** It is where the 48 `unclear` asks actually belong, and it is
distinct from NPC placement — one is what a creature looks like, the other is
where it stands.

### Two things the schema cannot express at all

**Prohibitions.** **27–29 asks carry an explicitly negative label**; between 53
and 68 depending on how widely "prohibition-shaped" is read (a reader working
from the free text finds more than a regex over the canonical labels). The
most-forbidden thing is not a game feature but the generator's own behaviour:
**"don't ask clarifying questions" arrived under six distinct labels totalling
exactly 11 asks** — a figure the merge and an independent sweep agree on to the
unit. Scope caps total 12. One prompt spent half its words listing what not to
build and received a town square and a den anyway. There is no field in which
anything downstream could notice the conflict.

**Non-default player identity and movement.** ~102 asks by the merge, 107 by an
independent sweep — call it **~105, or 8.3% of all asks**. A cat, an ant, a
mech, a UFO, a rolling tyre; dash, grapple, flight, modified WalkSpeed, swimming.

One correction to the merge's reading: **~17 of these are cosmetic avatar
customization** (skin shops, outfit editors, dress-up catalogues) which change
nothing about physics. The claim that essentially all of them break jump-gap
validation applies to the other **~90**, which is still 7% of asks and still
enough to invalidate generated geometry silently. The 10–16 vehicle-player cases
are the worst: a car cannot clear a validated gap at all.

The cosmetic ones are not noise — they belong in the context file under
progression `cosmetics[]`. They simply do not belong in this hazard.

---

## 7. Presets are the weakest mechanism in the network

| Outcome | Rows | Share |
|---|---|---|
| Preset supplied at least one option | 539 | 88% |
| Preset carried an option **contradicting the prompt** | 145 | 23% |
| No preset fit at all (`preset: null`) | 38 | 6% |

**182 rows — nearly a third — got a preset that either did not fit or actively
fought the prompt.**

The cause is structural, not a matching bug: **a preset is a shape plus options
taken together, and shape is exclusive.** Options can be kept and labelled;
shape cannot. When a preset carries the right mode and the wrong shape, the
choice is to accept a contradicted shape or discard the preset entirely.

### The same coupling one level deeper: shape carries the pipeline route

`LayoutGen - Pipeline.md` keys the route on shape deliberately — *"It is now
keyed on shape and gives the answer."* That fixed a real problem, but it means a
shape's spatial character and its pipeline route are a single indivisible
choice.

**140 rows (23%) chose a shape that carries a route**; another 91 sit in a genre
with a genre-wide P6. **229 rows — 37% — had their route fixed by classification
rather than by anything the prompt said about geometry.**

| Shape used | Rows | Route it forces |
|---|---|---|
| `warren-looping` | 30 | P6 |
| `lane-actor-track` | 18 | P6 |
| `world-open-biomes` | 17 | P4 |
| `space-staged` | 12 | P4 |
| `arena-stacked` | 11 | P2 |
| `settlement-claimable` | 10 | P3 |
| `settlement-buildable` | 8 | P3 |
| `world-biomes` | 8 | P4 |
| `world-chaptered` | 7 | P4 |
| `puzzle-maze` | 7 | P6 |
| `world-hub-dungeon` | 5 | P4+P3 |
| `world-underground` | 4 | P2+P3 |
| `hub-portals` | 3 | P4 |

The failure mode is concrete. An Apocalypse Rising clone asked for **one big
map** with areas of differing danger. The only Survival shape expressing graded
danger is `world-biomes`, which hard-codes **P4 — genuinely separate maps**.
There is no way to take the shape without the route. A dungeon prompt hit it
from the other side: it described one dungeon, and RPG's only dungeon-bearing
shape is `world-hub-dungeon`, which forces a safe hub plus P4 and P3 onto a
prompt that asked for neither. 25 rows sit on the two biome shapes and every one
of them was routed to separate maps.

This is worth separating from the preset problem because the fix is different.
Presets need shape decoupled from options; shapes need the *spatial* claim
("danger scales with distance") separated from the *build* claim ("these are
separate maps").

> **Correction — the 140 is exposure, not failure.** The counts above measure how
> many rows sat on a shape that *could* impose an unwanted route. A follow-up
> pass measured how often it actually did
> (`evaluation/tools/eval_route_conflict.py`), and the answer is far smaller.
>
> **47 prompts explicitly describe one continuous map** — "one big map",
> "seamless", "open-world", zones joined by bridges. **43 of them were routed
> correctly. 4 got P4 anyway**, all four from the shape rather than from an
> option: P0319 (Apocalypse Rising 2, "a big map and multiple areas to loot"),
> P0561 (Antarctica, "large seamless" world), P0021 (Blox Fruits, islands
> "connected by water routes or bridges"), and P0017, which is arguable.
>
> P3 produced **zero** contradictions. The three P2 candidates were false
> positives in the matcher — all fired on the bare word "flat", which in those
> prompts means flat shading, and a platform fighter and a city with rooftops
> genuinely need stacked surfaces.
>
> The finding that survives is smaller and different: of 85 rows on an
> overridable route-bearing shape, **47 had the route confirmed by the prompt,
> 31 had it assumed** with the prompt silent either way, and 7 were flagged as
> contradicted of which 3–4 are real. A default that is right this often is
> working. The fix is therefore an **override for the explicit-contradiction
> case**, not the decoupling of shape from route that this section argued for —
> and recommendation 4's second half should be read at that scale.

### Representative preset cases

- Seven of Shooter's eight presets are lane networks, so a prompt describing
  dispersed points of interest must accept a lane network or emit `preset: null`
- The Platform Fighter preset pins a shape defined as having *nothing
  overhanging*, in a format whose whole premise is platforms you jump through
- A prompt reading "so far just make the lobby" received team bases, lane cover
  and choke points for a match map the user explicitly deferred
- Keeping a contradicted option is not cosmetic: `obstacle-maze` kept on a house
  facade with no interior dragged **P6 onto the pipeline route** for a maze that
  does not exist

---

## 8. P5 is the wrong abstraction — and my first read of it was wrong too

**Correction to an earlier draft of this report.** I originally scored P5 by
selecting 23 prompts from subgenres that "should" route there — idle,
incremental, match/merge, board and card, word, music — and reported that only 1
of 23 did, as a defect. That test was invalid, and it was invalid for exactly
the reason I was accusing the skill of: **I picked the candidates by concept
name rather than by what the prompts described.**

The spreadsheet carries its own `inferred_game_dimension`, assigned upstream and
independently. Checking against it settles the question:

| Dimension | Rows |
|---|---|
| `3d` | 613 |
| `unspecified` | 7 |
| `2d` | **0** |

**All 23 of the supposed P5 candidates are marked `3d`.** So are all 620 rows —
the corpus contains no 2D games at all. The workers who read those prompts, saw
described geometry, and built were **right**, and the 1-of-23 figure is not a
defect rate. It measures my test set.

### The real defect points the other way: P5 discards geometry

Three rows routed P5. In two of the three, the worker wrote a note objecting to
its own verdict:

> *"This is a strained P5. The prompt does describe a buildable 3D set — a deep
> wicker basket, a pile of physics-settled fruit and vegetable models, and a
> tray — which nothing downstream will now receive."* (P0236, match-3)

> *"Worth flagging to the caller: the tower, the table it stands on and the
> camera framing are all geometry someone has to build, even though the layout
> pipeline declines the job."* (P0337, 3D Jenga)

The third is a door welded to an avatar body, written in colloquial Arabic
(P0572) — a rigging request, and the only one of the three where declining to
build is clearly right.

**P5 conflates two independent things: "the player does not walk through this"
and "there is no geometry to build."** In this corpus those come apart
constantly. A Jenga tower, a basket of produce, a chess board, an idle room with
two lights — every one has a real 3D set and no player locomotion.

The fix is not to make P5 fire more accurately. It is to split the concept:
build the set, but skip traversal segmentation and jump-gap validation, and let
the camera be fixed. **Strategy's `board-grid` shape already does exactly this**
— it is defined as a board players act on rather than move through, and it
routes P0. The pattern exists; P5 is the wrong sibling to reach for. Catan is
the flat contradiction: stage B says "no space" while `board-grid` says "build
it", and nothing says which wins.

Nine workers hit some version of this and each named it differently, so no
clustering would have grouped them; it was found by searching the records for
P5 directly.

---

## 9. Structural gaps reported by many independent workers

Named here because each survived the 0.27 noise floor by being reported
independently under different wordings.

| Gap | Independent reports |
|---|---|
| No goal / win condition field | 40 |
| No channel for screen-space (UI) requests | 19 |
| No home for economy or progression | 16 |
| No player count field | 15 |
| `performance venue` — no genre owns a stage with an audience | 9 |
| No sky or lighting channel | 6 |
| One prompt, several maps | 5+ |

**`performance venue`** deserves separate mention: nine workers coined that exact
phrase independently for concerts, festivals, talent shows and a dance
institution. Entertainment's presets are architecture you walk around and look
at — no stage, no audience orientation, no backstage — so the stage gets forced
into `landmark-focal`.

**Multi-map** is near-universal on Roblox and unrepresentable: P4 exists as a
pipeline code but only a shape can carry it, and most genres have no shape that
does. A ten-map request can only be honoured by reclassifying the game.

---

## 10. What to do

Ordered by evidence strength, not by effort.

1. **Add an NPC / character population option.** Largest single gap, corroborated
   by two independent analyses.
2. **Build the context file**, starting with `title` (70 asks), `hud.elements[]`
   (~99) and `screens[]` (~175). Add *character and creature appearance* as a
   destination.
3. **Add a goal / win condition field.** 40 independent reports; intake's own
   notes already flag it.
4. **Decouple preset shape from preset options**, or allow a labelled shape
   override. Fixes ~182 rows. Separately, allow a **shape's pipeline route to be
   overridden when the prompt explicitly contradicts it** — 140 rows were
   exposed to a welded route, though on re-measurement only 4 were actually
   routed against what their prompt said. Small fix, not a refactor; see the
   correction in §7.
5. **Split P5 into "no locomotion" and "no geometry."** The corpus has no 2D
   games at all, so P5-as-a-filter has almost nothing to catch; when it did fire
   it threw away a buildable set two times out of three. Follow the
   `board-grid` precedent: build the set, skip traversal segmentation and
   jump-gap validation, fix the camera.
6. **Add the six layout options** in §5.
7. **Fix the Life preset's housing model**, and audit other presets against
   their own *Modelled on* references.
8. **Add fields for player identity, movement, and prohibitions.** ~90
   physics-affecting asks and 27–68 prohibitions; the first silently invalidates
   generated geometry.
9. **Give the "+1 speed" / speed-training family a home.** It is the one
   confirmed case of a real game family with no owner, visible in both the
   family sweep and the `runner` subgenre split. `open_world_action`'s 35%
   turned out to be a loose bucket, not our problem.

## Known limitations

- Ask counts are floors. Inter-worker naming overlap was 0.27.
- Genre reproducibility is 13 of 16 across two small samples, one of which is a
  single worker pair (§1). Treat it as indicative, not as a rate.
- `evaluation/data/records/batch-49.jsonl` holds only the 2 records the stalled worker had
  produced when the aggregate was built; its other 8 prompts are backed by
  `batch-49r.jsonl`. When the original worker finished late, its full 10-record
  output was preserved as `late-batch-49-full.jsonl`, deliberately outside the
  `batch-*.jsonl` glob so the merge's tie-break could not silently swap which
  scoring backs a published number. Those 8 late records are used only as the
  second calibration sample.
- The `complete` coverage verdict is unusable (§1).
- Workers were told an all-null gap run "tells us nothing", which is a nudge
  toward reporting gaps. Defence: the findings above are weighted by repeated
  independent reports rather than by raw volume.
- The adjudication reviewers saw both labels by design. They were instructed to
  return `tie` for pure taxonomy artifacts, and did so on 21 of 89.
- Every headline count above was re-derived from the raw records independently
  of the analysis that first reported it (`evaluation/tools/eval_verify_concepts.py`,
  `eval_subgenre_split.py`, `eval_verify_systems.py`). Two claims
  did not survive: a family list's horror-escape fragmentation (§2) and the
  scope of the player-identity hazard (§6). Both are corrected in place.
