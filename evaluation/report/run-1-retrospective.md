# Run 1 — what it found, and what we changed because of it

Run 1 put 620 real user prompts through the skill network and recorded what
came out. It was **a discovery exercise, not a benchmark.** Its job was to show
us where the network failed and what we had not thought to look for, and it did
both. Several of its most useful findings were about the evaluation itself
rather than about the skills.

Its numbers are **deliberately not comparable with any later run**, because the
definition of a failure changed as a result of what it found. Do not diff the
scores. The code that produced it is tagged `eval-run-1` (commit `47470a8`).

## Where the data lives

| | |
| :---- | :---- |
| Records | `evaluation/data/records/*.jsonl` — 727 records, 638 carrying a `gaps` block |
| Prompts | `evaluation/data/batches/*.json` |
| Report | `evaluation/report/LayoutGen - Golden Set Evaluation.md` |

Left in place rather than moved into a `run-1/` directory: two dozen tools under
`evaluation/tools/` resolve these paths, and rewriting all of them to preserve
history would have risked the history. **Run 2 writes to
`evaluation/data/run-2/` instead**, which gets the same isolation for free.

**179 records name 12 shape IDs that no longer exist**, because the shape
catalogue was rebuilt afterwards — `world-shared`, `arena-flat`,
`space-continuous` and nine others. The records are **not** migrated; they are
the historical artefact and rewriting them would defeat the point. The mapping
is in `tools/shape-migration.json`, to be applied at read time by anything that
needs current names.

## What it found

### 1. Most of what we were counting as failure was never ours

Every gap entry carries a `destination` naming the consumer it belongs to, which
turned out to be the single most valuable field in the schema.

| | Entries | |
| :---- | ---: | :---- |
| `image`, `layout`, `sky` | 1,546 | the layout pipeline's to build |
| `mechanics`, `progression`, `constraint`, `ui`, `metadata`, `audio` | 2,343 | somebody else's |

**Three fifths of recorded gaps belonged to another stream.** 96% of records
carried a `skill_gap`, and the most common labels were *"no goal condition
field"*, *"no player count field"* and *"no home for goal condition"* — things
the skill is explicitly instructed not to ask about, being logged as skill
failures. The brief had invited this by naming goal conditions and player counts
as examples of skill gaps.

This is the finding that reframed the whole exercise. A prompt can be
three-quarters gameplay and still be completely served by a correct map.

### 2. Free text was being counted as a miss

38.7% of layout-owned gaps had *already shipped* in the handoff as free-text
picks — "a large fountain or small lake at the centre", "75 lifeboats along the
sides of the ship". For 94 records, **every** layout gap was of this kind. The
request reached the image model; it was recorded as missing anyway.

### 3. The catalogue was reachable only in theory

574 distinct IDs were suggested for layout-owned gaps that matched no row in
Build.md. Hand-resolving a sample of 14 found **10 already existed under a name
no string match would find** — `performance-stage` was `venue-stage`,
`audience-stand` was `spectator-bleachers`, `npc-crowd` was `npc-population`.

Following that thread produced the largest structural finding of the run.
Options were filed per-genre with no rule permitting a genre to reach past its
own table, so **80 records asked for an option that existed in the system but
not in the genre they were assigned.** Sports and Shooter both asked for a lobby
and neither could reach `social-hub`. Puzzle asked for lava and could not reach
`hazard-kill`.

### 4. Prompts imply geometry they never state

The recurring near-miss was a gameplay rule whose *spatial consequence* went
unbuilt. "You win by reaching the exit" is a win condition, and it also means
there is an exit, and an exit is a place. Nothing in the skill told it to read
past the rule to the place the rule needs.

## What we changed

| Finding | Change |
| :---- | :---- |
| Gaps belonging to other streams scored as ours | Step 0 triage sorts every prompt into scene-stated, scene-implied and not-scene; a new `mechanics` array carries the third pile onward, and the brief no longer invites goal conditions and player counts as skill gaps |
| Prompts imply geometry they never state | The middle pile of that triage is named explicitly as the one that gets missed, with the genre used to reason forward to places the prompt never mentioned |
| Options unreachable across genres | Every option is now reachable from every genre, as every shape already was; a generated `options.md` holds all 91, and the skill has an explicit matching order ending in free text |
| Free text losing the route | Free text is now last in that order, because it is the only step that drops the pipeline route |
| Catalogue rows found by name-matching | The matching order puts the universal six ahead of free text, since most apparent misses are one of those in the prompt's clothes |
| Multi-map called a schema hole | Corrected: six shapes carry the request and route `P4`. It is a readiness gap, not an intake one |

## What run 2 tests

A different question from run 1, deliberately.

| Verdict | When |
| :---- | :---- |
| **Pass** | Every scene-relevant request is captured as genre, shape or option — **or** covered by a question that would fill it |
| **Fail** | A scene-relevant request is neither captured nor asked about |
| **Not counted** | Gameplay, UI, audio, progression, currency, controls |
| **Counted separately** | The right shape identified but not buildable today (`P4`) — a pipeline gap, not a tagging gap |

The second half of the pass rule is why run 2 waits on the targeted-question
work. Run 1's skill asked exactly one question — *"Anything else you want in the
space?"* — so a run held to this rule today would be measuring one half of it.
