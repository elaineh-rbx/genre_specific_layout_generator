# Running the genre-choice skill on 75 scenes

What happened when the skill in `.cursor/skills/genre-choice/` was executed as
written, by an agent, on every scene of this repository's golden set. It is a
report on the *document*, not on the scenes: the interesting output is the list
of places where a careful reader following the six steps could not tell what the
skill wanted, and had to decide for itself.

Written for mpalleschi/3D-LayoutBuild-Rules @ `5a3c636`.

## Method

Seventy-five scenes, one agent per scene, all pinned to the same model
(Claude Opus 5). Each agent was given the prompt text and nothing else: not the
golden set's own genre label, not this repository's rule-based router's answer,
and not any other agent's block. Each was told to read `SKILL.md` in full, follow
its six steps, and load only the files the skill directs it to — file choice is
part of what was being measured, so no agent was told which genre file to open.

There was no user to answer questions. Every offer, confirmation and open
question the skill asks for was instead recorded as a note prefixed
`would have asked:`, which is why there are 278 of them across the 75 blocks.
Agents were forbidden from running any validator, adapter or comparison, so
nothing downstream could leak back into the answer.

Results are one JSON block per scene in `results/routing/skill/`.

## What came out

| | |
|---|---|
| Blocks produced | 75 |
| Named a genre | 60 |
| Came back None | 15 |
| Named two genres | 9 |
| Entries emitted | 557, of which **218 carry no option id** |
| Unanswered offers | 278 `would have asked:` notes, in every one of the 75 blocks |

Against this repository's rule-based router, the skill agrees on genre in 47 of
the 75 and picks 120 options the router did not. That comparison is not part of
this report — neither side is ground truth, and the router is a fifteen-way enum
that cannot produce a None at all.

## Findings

Ordered by how many independent agents ran into each one. All fifteen None
outcomes and every scene id below can be read back from `results/routing/skill/`.

### 1. A modifier whose code contains `P0` has no defined spelling

The field rule says `P0` drops out of `pipeline` once a modifier is present. But
the modifier's own code is written `P0 + tiered`, with a `P0` inside it. So an
agent that has taken a tiered option has to decide whether to emit
`["P0 + tiered"]`, `["P0", "tiered"]`, or `["tiered"]`, and the document supports
all three readings.

Twenty-two blocks emitted the single token `P0 + tiered`. None split it. Two more
(`0014`, `0054`) emitted a bare `tiered` beside a `P6`, which is the same
question resolved the other way in a context where no `P0` was in play. The
output converged, but the reasoning did not — more than half a dozen agents
flagged the ambiguity explicitly while arriving at the same answer, which means
the convergence is luck rather than clarity.

**Suggested:** state the emitted form once, in the field table. Either the code
is an opaque token or `P0` is always dropped, but not both.

### 2. Parameterisation has no home in the block

Forty-nine of the 75 prompts ask for something to be adjustable — "expose
attributes for BuildingSize, CrateCount, FenceHeight", "make the fog level and
light intensity configurable", "TrackWidth and NeonColor". This is neither
geometry nor a placed marker, so step 5's image-or-layout test does not reach it,
and `count` holds a quantity of picks rather than a dimension. In all 49 blocks
it fell into `notes`, where nothing downstream can act on it.

The same gap swallows stated extents. "200x200 studs", "a 30x30 stud footprint"
and "about 100 studs high" are hard constraints the user wrote down, and every
one of them ended up as prose in a note. Scene `0059`'s agent observed that the
four-value scale band would destroy the stated size even if it were carried.

**Suggested:** a `parameters` field, or an explicit statement that build-time
parameters are out of scope for the block so the pipeline knows to look
elsewhere.

### 3. `no-genre.md` is the only file cited without its directory

Line 145 says a stage A outcome of None "loads `no-genre.md` and nothing else",
while all fifteen rows of the index table above it carry a `genres/` prefix.
The file really is at the skill root, but several agents guessed `genres/` first
and had to list the directory to recover.

**Suggested:** write the path the way the index writes paths.

### 4. None was the answer on a fifth of the set, not 7%

The skill says None "was the right answer on 7% of 620 real prompts". Here it was
the answer on 15 of 75, a fifth: `0001 0004 0005 0016 0027 0029 0034 0051 0055
0063 0068 0069 0071 0074 0075`.

This is most likely a property of the set rather than a defect. These scenes were
collected for a prompt-to-image pipeline, so they skew toward room and asset
briefs — two near-duplicate haunted lobbies (`0063`, `0068`), a 30x30 stud
campsite (`0069`), a decorative farm (`0071`), a swamp biome (`0074`), an alchemy
lab (`0075`). But it is worth knowing that on an image-generation workload the
None path is load-bearing rather than an edge case, because everything about how
it is written treats it as rare.

### 5. `SET` and the Explorable Place preset contradict each other

Scene `0071` accepted `SET` — a decorative farm scene nobody walks through — and
also took the `Explorable Place` preset, which is the preset None points at. That
preset ships `path-circulation`, which is walkable routes. Accepting both means
dropping a preset option in the same breath as taking the preset.

`SET` and None are going to co-occur constantly, since a prompt with no gameplay
is exactly the kind that describes something looked at rather than entered.

**Suggested:** say what a `SET` build does with circulation, or give the None
file a set-piece preset.

### 6. A genre can be right about the game and wrong about the build

Scene `0060` describes a Tower Defense *lobby*: a walled courtyard with a portal
arch, benches and a fountain. Strategy is unarguably the game. But no Strategy
shape can express a lobby, so its agent demoted the self-declared genre and gave
the shape to Entertainment's `hub-portals`, naming Strategy second.

The override rule permits departing from a self-declared genre when "the gameplay
plainly contradicts it". Nothing here contradicts anything — the prompt is a true
statement about a part of the game that the genre's shape table does not cover.
Scene `0036` is the same shape of problem from the other side: a self-declared
backrooms *shooter* whose agent led with Puzzle because only `puzzle-maze`
carries the non-negotiable `P6` the labyrinth needs.

**Suggested:** cover the case where the named genre is correct but the requested
build is one of its rooms rather than its play space.

### 7. `course-tower` forces `P2` with no override row

The shape carries `P2` because a spiral puts platforms above each other, and step
4 says `P2` is not production-ready — but the override table has no entry for it,
so there is no sanctioned way to decline.

Agents split. Scene `0014`'s took `course-terraced` instead, avoiding the shape to
avoid the cost. Scenes `0017`, `0018`, `0020`, `0064` and `0067` took the shape
and accepted `P2`, recording the terraced fallback as a deferred question rather
than downgrading silently. Same tension, opposite resolutions, five to one.

**Suggested:** an override row saying whether a spiral ascent may be delivered as
a stepped one.

### 8. Options marked `layout` cannot carry visible geometry

`Goes to` is a two-way split, and several rows land on the wrong side of it for
prompts that ask to *see* the thing.

Scene `0059` wanted a visible dark stone archway where enemies appear; Strategy's
`spawner-npc` is `layout`-only, so the archway had no image-stream carrier and
its agent flagged the gap rather than inventing a duplicate entry. Scene `0071`'s
perimeter fence hit the same wall through `boundary-edge`, whose type is
`BoundaryZone` but whose `Goes to` is `image`-only, leaving `layout_placement`
empty. Grain stalks via `collectible-nodes` had the problem earlier in the set.

**Suggested:** allow a row to be split the way `both` splits, or review the
handful of rows whose geometry is plainly visible.

### 9. Universal options are only reachable through a conversation that did not happen

The universal rows are introduced as a landing place for a request the user
actually made, and the worked path to them runs through step 5's open question.
But prompts ask for the town fabric, the water and the terrain outright, in the
original text, with no conversation to route it through.

Forty universal picks were made across 29 scenes and they look right, so agents
found the path anyway. It is the framing that is wrong, not the outcome.

### 10. Style and palette are neither geometry nor placement

"Low-poly minimalist, flat colours", "dark fantasy science aesthetic", a stated
colour palette, fog. Step 5's test sends a property of geometry to `layout`,
which would file a palette as a placement; agents put these in `image_prompt`
instead, on the reasoning that the image model is what renders them, and flagged
the call. Scenes `0056`, `0063`, `0068`, `0074` and `0075` all raised it
independently.

### 11. Free text carries more than the option tables do

Two hundred and eighteen of 557 entries carry no option id, and 22 of the 75
blocks are *majority* free text. Scene `0061` is the clearest case: a heavily
specified backrooms environment where only `path-loop` matched a real option, so
the drywall, the drop ceiling, the carpet, the colour grading and the 36-room
grid all went in un-IDed.

Step 5 introduces `id: null` entries as a way to record answers to the open
question. In practice they are the main channel for everything the prompt spelled
out that no table covers. That is probably the right behaviour, but it is not the
behaviour the step describes, and it means the option tables are carrying less of
the signal than their prominence suggests.

## Smaller notes

- **Scene `0015`** asks for jump gaps of 10-20 studs, with a hard setting of 25,
  against the `P6` horizontal limit of 11 studs at default walk speed and jump
  height. The prompt and the genre file disagree on a number outright, and the
  skill does not say which wins; its agent recorded both the tightening and the
  raised-mobility alternative as a question.
- **A preset's unrequested options.** Step 3 says drop only what the prompt
  contradicts, while the opening rule forbids injecting options the user did not
  choose. A preset option the prompt neither asks for nor contradicts satisfies
  one and violates the other.
- **Step 6's example emits `["P0"]`** while including `island-cluster`, whose row
  carries `CHECK`. Scene `0066`'s agent followed the field rule rather than the
  example and said so.
- **Two picks resolving to one object.** In `0060`, `landmark-focal` and
  `teleporter-link` are both the single portal arch. Nothing says whether to keep
  both, and the agent kept them with a note asking the pipeline not to build two.
- **No `type` convention for free-text layout entries.** `0061`'s agent emitted
  `"type": null` by analogy with the shape rule.
