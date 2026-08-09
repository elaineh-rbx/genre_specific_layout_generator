# Golden-set eval — standing lane brief

You are one lane in an evaluation of the LayoutGen skill network against a
golden set of real user prompts. Your job is to **execute the skill network
honestly on each prompt in your batch** and write down what it produced.

You are not grading anything. There is no reference answer in your batch file
and you must not go looking for one — the point of this exercise is to capture
what the skills do on a cold read, so a guess about "the expected answer" is
the one thing that would invalidate your output.

## Read scope

Read only these. Do not explore the repository beyond this list.

| Path | Why |
| :---- | :---- |
| `.cursor/skills/layout-intake/SKILL.md` | the workflow you are executing |
| `.cursor/skills/genre-choice/SKILL.md` | classification and emit rules |
| `.cursor/skills/genre-choice/genres/*.md` | **only** the files your classification calls for |
| `.cursor/skills/genre-choice/no-genre.md` | only when stage A lands on None |
| your assigned batch file under `evals/batches/` | your input |

`docs/LayoutGen - Build.md` is 115 KB and you do **not** need it. The genre
files carry everything required. Reading it will burn your budget.

Never read another batch file, any `evals/records/*.jsonl`, or the golden-set
CSV in `docs/`. The CSV holds the labels you are being compared against.

## What to do per prompt

Follow `layout-intake/SKILL.md` as written, including its dispatch to
`genre-choice`. Three deviations, because this is a batch run with no human:

1. **You cannot ask clarifying questions.** Where the skill says to ask one,
   make the call the skill's rules point to, and record the question you would
   have asked in `coverage.missing`. That list is a deliverable, not a failure.

   Do **not** record "could not confirm the user accepted the preset" as a
   missing question. Preset acceptance is an artifact of running without a
   human, not something we would ask a real user.

   **Take the whole preset. Keep every option it carries, label them all in
   `preset_derived`, and put anything the prompt positively contradicts in
   `preset_rejected` with a reason — but keep it in the handoff.** Do not
   silently drop preset options you judge unlikely.

   This is the one place the brief overrides your judgement, and it is
   deliberate. "The prompt did not imply this" and "the prompt contradicts
   this" are different thresholds, and two lanes applying different ones make
   their option counts non-comparable. Labelling loses nothing: the analysis
   can subtract `preset_derived` to see what the prompt alone produced, which
   dropping cannot be undone into. It also turns "this preset carries options
   that fight their own prompt" into a measurable finding instead of an
   invisible edit.

2. **Load genre files lazily and cache them** — read a genre file the first
   time a prompt in your batch needs it, then reuse the contents. Never read
   all fifteen.

3. **"Loaded files" means loaded for the prompt in front of you.** Caching is a
   way to avoid re-reading a file, not a way to widen what a prompt may match
   against. When step 5 of `genre-choice` says to promote free text only if it
   matches an option in a loaded file, that means a file *this prompt's*
   classification called for. An option from a genre you read three prompts ago
   is not available here. Otherwise a prompt's results would depend on its
   position in the batch, and `unmatched_options` — the field this whole
   exercise turns on — would be polluted by batch order.

### The two prompt fields

Each item has `prompt` and `enriched`.

**Classify and build the handoff from `prompt` alone.** That is the real user
input. Some are one line; some are 20 KB design briefs full of scripting, UI,
and monetization detail that has nothing to do with layout. Take the layout
content and let the rest go.

**Read `enriched` only after your handoff is written**, and only to fill
`coverage.enriched_invented`. It is a downstream system's expansion of the same
request, so it is useful as a check on what a good expansion committed to.
Anything concrete in `enriched` that the user never said is either a safe
inference or a question we should have asked. Do not revise your handoff
because of it.

## Output

Append one JSON object per prompt, **one per line**, to the record file named in
your task. No wrapping array, no markdown fences, no commentary in the file.

**Append each record as soon as you finish that prompt.** Do not hold all of
them in your head and write the file at the end. Two reasons: the parent watches
file size to tell a working lane from a hung one, and a lane that dies at minute
24 having buffered everything delivers nothing at all. Incremental appends make
"report what you have" actually mean something.

```json
{
  "item_id": "P0042",
  "handoff": {
    "genre_choice": { "genres": ["obby-platformer"], "shape": {"id": "course-tower", "type": "Path", "name": "Tower / Spiral Ascent"}, "preset": "Tower Obby", "pipeline": ["P6", "P2"], "image_prompt": [{"id": "path-track", "text": "..."}], "layout_placement": [{"id": "winner-zone", "type": "WinnerZone", "text": "..."}], "notes": [] },
    "theme": "Stylized / Toon",
    "scale": { "band": "block", "assumed": true },
    "open_questions": [ { "field": "theme", "ask": "..." } ]
  },
  "coverage": {
    "verdict": "partial",
    "captured": ["tower shape", "timed platforms", "reward at the top"],
    "preset_derived": ["obstacle-timing", "obstacle-climb"],
    "preset_rejected": [ { "id": "hazard-kill", "why": "the prompt says falling is the only failure, so contact-lethal surfaces contradict it" } ],
    "missing": [ { "field": "theme", "ask": "Should the tower read as candy-coloured or grimy industrial?" } ],
    "enriched_invented": [ { "detail": "a rotating spotlight at the summit", "kind": "safe_inference" } ]
  },
  "gaps": {
    "unmatched_options": [
      { "canonical": "leaderboard", "text": "a leaderboard showing fastest ascent times", "destination": "layout", "suggest_id": "scoreboard-display", "quantity": null },
      { "canonical": "purchase menu", "text": "a shop menu on screen for buying coils", "destination": "ui", "suggest_id": null, "quantity": null },
      { "canonical": "tower height", "text": "the tower must be exactly 500 studs tall", "destination": "layout", "suggest_id": null, "quantity": "500 studs tall" }
    ],
    "genre_gap": null,
    "skill_gap": { "name": "no channel for screen-space requests", "why": "the shop is explicitly a GUI, so it had to be written as a layout entry or dropped" }
  }
}
```

### Field rules

`handoff` is the layout-intake handoff exactly as that skill defines it, with
`genre_choice` unmodified from what genre-choice emits. Drop the `prompt` key
to keep the file small — `item_id` already identifies it.

| Field | Rule |
| :---- | :---- |
| `genres` | Our slugs, dominant first, matching the genre filenames. `[]` for no-genre and for P5. |
| `pipeline` | Never empty. `["P0"]` when nothing adds cost. |
| `coverage.verdict` | `complete` — everything needed for a build is in the prompt. `partial` — buildable, but at least one field was assumed. `insufficient` — a real build would have to ask before starting. |
| `coverage.captured` | Short phrases naming what you pulled from the prompt. Enough to audit that you read it, not a transcript. |
| `coverage.preset_derived` | The option IDs in your handoff that came from the preset rather than from anything the user said. `[]` when every pick traces to the prompt. `genre-choice` forbids injecting options the user did not choose, and accepting a preset is the one sanctioned way extras enter — so this list is how we measure whether presets are quietly padding builds. Do not omit it to look clean. |
| `coverage.preset_rejected` | Preset options the prompt positively contradicts, as `{ "id", "why" }`. They stay in the handoff and in `preset_derived` as well; this field records the conflict rather than resolving it. `[]` is the common case. |
| `coverage.missing` | The questions you would have asked. `field` names the key it would fill (`theme`, `shape`, `scale`, `goal`, `genre`, or a free string). This is the answer to "what would you ask the user." |
| `coverage.enriched_invented` | Concrete things in `enriched` the user never said. `kind` is `safe_inference` when set dressing that could not be wrong enough to matter, or `should_have_asked` when it committed to something load-bearing the user might reject. Cap at 5 entries; you are sampling, not diffing. |
| `gaps.unmatched_options` | Every request that got `id: null` because no loaded option covered it. **This is the most important field in the record** — it is the entire input to the missing-options analysis. See the four sub-fields below. |
| `gaps.genre_gap` | `{ "name", "why" }`, only when the prompt is a real game concept that no genre in the index fits and you had to force it. `name` is a 2–4 word label for the *kind of game* — "performance venue", "destruction sandbox" — so gaps of the same kind group across hundreds of rows. `null` otherwise, which will be most rows. |
| `gaps.skill_gap` | `{ "name", "why" }`, only when the skill network itself could not express something — a concern with no home (goal condition, player count, progression), a rule that gave the wrong answer, an instruction that was ambiguous in a way that mattered. `name` is a short label reused across rows that hit the same wall. `null` otherwise. |

Be honest in `gaps`. A run where every row is `null` tells us nothing and is
the failure mode we are trying to avoid. A forced classification recorded as
clean is worse than no data.

### The four sub-fields of `unmatched_options`

Six hundred prompts will produce a couple of thousand of these. Nobody is going
to read them one at a time, so each entry has to carry enough structure to be
counted and sorted mechanically.

**`canonical`** — a 2–4 word noun phrase naming the *thing*, stripped of this
prompt's specifics. "leaderboard", "wardrobe station", "timed spawner",
"performance stage". This is the grouping key: it is how we tell a common ask
that deserves a new option from a one-off that never needs one, which is the
central question of the whole run. Reuse the obvious plain-English word rather
than inventing a distinctive one — two lanes writing "scoreboard" and "leader
board" for the same concept is the failure mode. Lowercase, singular.

**`text`** — the request in context, as before. The specifics live here so
nothing is lost when the canonical phrase flattens them.

**`destination`** — which consumer this ask actually belongs to. The layout
pipeline draws a top-down or isometric image and then places volumes; plenty of
what users ask for is real and belongs to neither. Tagging it here is what lets
us separate "we are missing a layout option" from "this was never ours to
build."

| Value | For |
| :---- | :---- |
| `image` | Visible geometry the image model should draw |
| `layout` | Volumes, markers, triggers, spawns — placed after segmentation |
| `ui` | Screen-space: menus, HUDs, shop GUIs, leaderboard displays |
| `audio` | Music, sound effects, voice |
| `sky` | Skybox, weather, time of day, global lighting mood |
| `progression` | Economy, currency, scoring, unlocks, stats, inventory |
| `mechanics` | Scripting and behaviour with no spatial footprint |
| `constraint` | A rule over the whole build — "no 2D UI", "photorealistic", "use Studio's terrain generator" |
| `metadata` | Game title, description, and other non-build text |
| `unclear` | You genuinely cannot tell. Use it rather than guessing. |

Judge by where the work would have to happen, not by the words. A leaderboard
*display* mounted on a wall in the map is `image`; the same leaderboard as an
on-screen overlay is `ui`. If an ask splits across two consumers, write two
entries.

**`quantity`** — any number, count, or dimension attached to the ask, verbatim:
`"75 lifeboats"`, `"1000 studs wide"`, `"exactly 3 zones"`. `null` when there
isn't one, which is most of the time. The pilot found numbers are load-bearing
and currently survive nowhere, so this field exists to measure how often that
happens and what kinds of numbers they are.

## Budget

**Budget: 25 minutes.** If you are not done, write the records you have and
report which `item_id`s you completed. A partial batch delivered beats a
complete one that never arrives. Do not restart or rewrite finished records to
make them prettier.

Report back: how many records you wrote, the item_ids you skipped if any, and
the two or three most interesting things you hit — a genre that did not fit, an
option that was missing, a rule in the skill that was ambiguous.

## Do not touch

Do not edit, and do not `git add`, `git commit`, or `git push`:

- any file under `.cursor/skills/` or `docs/`
- `tools/eval_golden_set.py`
- `evals/LANE-BRIEF.md`
- any batch file, or any record file other than the one named in your task

Your record file is the only file you write. The parent commits.
