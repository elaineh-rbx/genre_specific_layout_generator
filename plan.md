# LayoutGen — Decision Log and Status

## What this file is

`docs/LayoutGen - Build.md` says **what the system is**. `docs/LayoutGen -
Pipeline.md` says **how a build gets routed**. The skills under `.cursor/skills/`
are generated from Build.md and are **what actually runs**.

This file says **why**, and nothing else. If a fact about how the system behaves
lives here and not in Build.md, that is a bug in Build.md.

Superseded planning detail — the original phase step lists, the v1/v2 draft
salvage tables, blast-radius grids, and the reasoning behind decisions that were
later reversed — is in git history and is deliberately not carried forward.

---

## Status

| Phase | What it did |
| :---- | :---- |
| **1–2** ✅ | Part II became a flat pool of pickable options per genre. Vocabulary gained `Zone`, `WinnerZone`, `Marker`, `Destructible`; `ObjectivePoint` retired for `Tracker`. |
| **2.5** ✅ | All fifteen genres finished to the presentation model: `Core`, `Goes to`, per-option pipeline tags, and presets. |
| **3** ✅ | The skills: `layout-intake` dispatches concerns, `genre-choice` classifies, loads, offers and emits. Generated from Build.md rather than hand-copied. |
| **4** ✅ | Cleanup and the drift guards. |
| **5** ✅ | Pipeline.md reconciled: Part 0 documents the handoff, phase 4.5 gave `layout_placement` a home, Part VI rekeyed from genre to shape. |
| **6** ✅ | The shape catalogue. Shapes left their genres, IDs merged, six shapes added, the described-shape catchall landed. |
| **7** ⏳ | Doc consolidation, then question quality, then a full eval re-run. |

**Current state:** branch `phase-6-shape-catalogue`, unmerged and unreviewed.
`master` has not moved.

### What Phase 6 measured

206 shape complaints across 198 golden-set prompts, every one read and given a
verdict in `tools/shape-gap-verdicts.json`. **113 are genuinely about shapes and
103 are answered.** The largest cluster by a wide margin — 38 rows — wanted a
shape that already existed under another genre and could not take it. Sharing
the catalogue did more than adding to it.

The other 93 mention shapes while asking for something else, 33 of them for a
multi-map handoff that does not exist.

---

## Decisions

Each is what we decided and **why it matters**, which is the part worth keeping.

### Settled

**D1 — `Core` ranks, it does not auto-fill.** If picks pre-select, a user who
chooses nothing still gets features they never asked for. A simple map is a
legitimate outcome. `Core` exists only so a long merged list has an obvious set
to lead with.

**D2 — Option IDs are shared across genres.** Mixing two genres has to offer
line-of-sight cover *once*, not twice under two flavour names. The ID is the
dedupe key; without it the model has to reason about whether two sentences mean
the same thing.

**D3 — Genre files are reference `.md`, not nested skills.** Fifteen nested
skills would each carry loading cost. One router plus flat reference files means
only the genres a prompt actually names get read.

**D4 — Build.md is canonical; everything else is generated.** Three
hand-maintained duplicates went stale during Phase 2.5 alone, so a second
hand-kept copy of fifteen tables was never going to survive.
`tools/generate_genre_skills.py --check` exits non-zero on drift. Run it after
editing Part II.

**D5 — Pipeline.md is reconciled with the skills.** It had been describing
intake as prose while the skills executed it, so the two could disagree silently.
Part VI is now keyed on shape, because shape *is* the routing decision.

**D6 — Shape is a pick-one block, not a flag on options.** The exclusive set is
always the routing decision, so making it structural puts the expensive choice
where its cost is visible. *(The per-genre scoping this originally implied was
replaced by D12.)*

**D7 — Presets are modelled on real games and shown under generic names.** The
reference game is how we get the layout right; the user sees "round-based bomb
defusal," not "Counter-Strike."

**D8 — The image/layout split needs a per-option tag *and* a stated rule.** A
`TriggerZone` cannot be segmented out of a render, so it must never reach the
image prompt. The tag handles known options; the rule handles free text, which
has no row to look up. Tagging roughly halves image-prompt load without capping
what a user may pick.

**D9 — One free-text box after the offered options.** It is what makes a short
menu safe. Truncating a ranked list to five silently drops the rest with no way
to discover them; five plus a box does not.

**D10 — Preset names come from Roblox's taxonomy first**, then established
industry terms, then plain description. Users echo Roblox's own wording, so
matching it is what makes a preset findable. The middle tier exists because
Roblox is often too coarse: *Deathmatch Shooter* covers four modes that need
four different maps.

**D11 — The skill detects non-spatial prompts, not the pipeline.** Stage B of
classification is the only step that has read both the prompt and the genre
notes, so it is the only one that can tell a rhythm game from a music venue.

**D12 — One shared shape catalogue.** *(Closed by Phase 6.)* Shapes used to be
private to a genre, so a prompt needing one large interior found Animal Sim
assumes wilderness, Simulation assumes an outdoor world and Roleplay's housing
shapes are all towns — while the shape it needed sat one genre over. The
sharpest evidence was an inversion: `no-genre.md` could describe spaces that
none of the fifteen genres could.

Two things this decision got wrong before it landed, both worth remembering.
**Routing identically does not make two shapes the same shape** — 26 IDs share
the all-defaults axis bundle and what separates them is entirely their
description, which no machine can merge. And **reachability was the fix, not
merging**: 38 of the measured rows needed nothing but permission to reach.

**D13 — P6 is not a family of generators.** *(Closed; the premise was wrong.)*
The claim was that four rows were stuck because genre-wide P6 validates
walking-jump spacing they never use. Reading the records refuted it: one routes
P0 with no genre and never saw P6, one got P6 from an option rather than a genre
route, one does not object to P6 at all, and one is not in the records.

**Why we still care:** grouping rows by the modifier they mention groups three
unrelated causes under one heading. The modifier is a symptom. Re-read source
rows before acting on a cluster.

**D14 — Near-duplicate shape IDs merge; the per-genre wording survives.** Same
pattern as options: one dedupe key, many descriptions, and the genre's own words
are what reach the image model. This was not really optional — `range-directed`
was already one ID carrying two names and two descriptions across Shooter and
Sports, so a catalogue that could not express that would break on the one shared
shape we had.

It cost the reversal of "existing IDs do not change": twelve IDs collapsed into
four, and `tools/shape-migration.json` carries the old→new map the 620 eval rows
still need.

**D15 — Goal / win condition is not an intake concern and is never asked.** It
was the largest thing intake wanted to ask and could do nothing with — 312 of
1,494 questions. The measurement settled it: adding a `goal` field takes rows
with a clear path from 37% to **76.9%**, and simply not asking takes them to
**76.8%**. Within one row, so the cheap direction wins.

A win condition is gameplay, not layout. The spatial half already has homes: the
shape says whether the space loops or terminates and `winner-zone` places the
payoff, both inferred from genre and preset. The one permitted question is a
*shape* question — is there an end to this, or is it endless to roam — because
that changes the map.

### Open

**D10a — Two genre splits that disagree with Roblox, and should be deliberate.**
Roblox files *Runner* under Obby & Platformer; we make Infinite Runner its own
genre, arguably right because a runner is P6 with elastic chunk spacing and
shares almost nothing with a difficulty-chart obby. Roblox has one *Sports &
Racing*; we split them, arguably right because they route differently. Both are
defensible, neither has been decided, and the skill has to reconcile them
whenever a prompt echoes Roblox's wording. Leaning keep-as-is on both.

**D16 — How to ask about spatial scale. Two drafts in `drafts/scale-reframe.md`;
the hybrid is chosen and not yet built.** `scale` is the most-asked field at 440
questions and **28% are asked open-ended against an answer space of exactly four
bands**. Open phrasing invites answers the field cannot hold, and does: one
prompt answered *5,000 square kilometres*, another *a trillion blocks*, and both
needed a second round trip to get back to something buildable.

The grounding is Pipeline.md A2 — the whole layout fits one isometric frame, so
extent is bought with detail. That gives exactly two deliverable outcomes for an
oversized request, which is what makes a closed question possible at all.

Draft A's proposed fourth column and draft B's first column are the same column,
so the answer is the hybrid: **use detail level as the inference aid, and keep
crop-or-compress for genuine overflow** — one new column, one new trigger, and
no extra question in the common case.

**Unresolved either way: where the overflow threshold sits.** A2 says cropping
happens, not at what extent street-level detail stops surviving. Both drafts
fall back on judgement. If render resolution and isometric framing are pinned
down anywhere, that arithmetic replaces the judgement, and `Region` is the band
where it matters.

---

## Known open work

**Schema holes, in measured order.** Multi-map is the largest — roughly 35 of
620 prompts ask for several maps and the handoff holds exactly one shape, one
theme and one scale. `P4` routes the build; nothing carries the request. Then
`count` and `player count`, worth about 3% together and cheap.

**The branch is unreviewed.** Everything since Phase 6 is on
`phase-6-shape-catalogue` and nobody but its author has read it.

**`check_intake_tab.py` has never run.** It gained the central Phase 6 assertion
— expand the picker, take a shape from outside the genre, confirm the handoff
carries it — and Playwright is not installed. It is the one unverified surface.

**The 620 eval records still hold retired shape IDs.** Until they are migrated
through `tools/shape-migration.json`, the golden set cannot be re-scored against
the catalogue it is being judged by, and Phase 6's "103 answered" stays a
reading rather than a measurement.

**The viewer cannot describe a shape.** Its no-genre path emits the right JSON,
so the schema is honest, but the catchall is not reachable in the UI.

**Two new shapes route to pipelines that are not production-ready** —
`traversal-city` is P2 and `volume-open-air` is `CHECK`. The alternative was
describing those spaces wrongly, but it does widen the set of prompts that route
to something we cannot deliver today.

**Hub portals may be routed too expensively.** They are `P4` because the
pipeline treats a portal as a zone transition, and Build.md now states the
exception — a portal to a genuinely separate Roblox *place* leaves the hub a
single-zone P0 layout with teleport markers. Nobody has confirmed which case is
the common one, and getting it wrong routes a cheap build to a pipeline that is
not production-ready.

**`genre-choice` has no round-trip question budget.** Pipeline.md caps the whole
intake at three questions and counts the offered preset as one of them, but the
skill only caps each step: one clarifying question, one open question, about
five items on screen when tuning. Followed literally, stage B's two questions
plus the preset plus the closing question already exceed the cap. This is a
question-design fix and belongs with the Part B skill work, not with a doc
cleanup.
