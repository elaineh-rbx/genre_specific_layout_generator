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
| `.cursor/skills/genre-choice/options.md` | the full option catalogue, when the loaded genre and the universal six both miss |
| `.cursor/skills/genre-choice/shapes.md` | the full shape catalogue, when none of the genre's typical shapes fits |
| your assigned batch file under `evaluation/data/run-3/batches/` | your input |

The two catalogues are on demand, not by default — the skill says when to reach
for them. A genre file's own shortlist now carries `Type (Flavor Name)` for the
shapes it lists, so a typical shape that fits needs no catalogue read.

`docs/LayoutGen - Build.md` is 115 KB and you do **not** need it. The skill
files carry everything required. Reading it will burn your budget. If you find
yourself needing it, that is a finding — put it in `notes_for_us` and carry on
without it.

Never read another batch file, another lane's records, or the golden-set CSV in
`docs/`. The CSV holds the labels you are being compared against.

## What to do per prompt

Follow `layout-intake/SKILL.md` as written, including its dispatch to
`genre-choice`. Three deviations, because this is a batch run with no human:

1. **You cannot ask clarifying questions.** Where the skill says to ask one,
   make the call the skill's rules point to, and record the question you would
   have asked in `coverage.missing`. That list is a deliverable, not a failure.

   **It is the main deliverable this run.** A prompt passes when every
   scene-relevant request is either captured as genre, shape or option **or**
   covered by a question that would fill it. So write each question exactly as
   you would put it to a user, offering the candidate answers where you can
   enumerate them, one subject per question, four at most. Nobody answers them
   and they do not need answering — a question that plainly leads to the missing
   value is a pass on its own.

   Do **not** record "could not confirm the user accepted the preset" as a
   missing question. Preset acceptance is an artifact of running without a
   human, not something we would ask a real user.

   **Take the whole preset and record every option it carries in
   `preset_derived`**, including ones you would personally have left out. Do
   not silently drop preset options you judge unlikely — "the prompt did not
   imply this" is not a reason to omit one.

   **An option the prompt positively contradicts goes in `preset_rejected`
   with a reason, and does *not* go in `image_prompt` or `layout_placement`.**
   Record it, then leave it out of the build. The earlier version of this brief
   told you to keep it in the lists as well, on the reasoning that labelling
   loses nothing. That was wrong, and run 3 measured how wrong: 129 contradicted
   options reached the two lists a consumer actually reads, so a maze nobody
   asked for was an instruction to draw a maze. `genre-choice` step 3 says it
   plainly — the wrong option is not inert.

   Nothing is lost for the analysis, because `preset_rejected` carries the `id`
   and the reason: a build with the rejections added back is reconstructable
   from the record, which is what the old rule was trying to protect.

   **`preset_derived` means the preset is the only reason it is there.** An
   option the prompt already implied does not become preset-derived by also
   appearing in the preset — a maze prompt implies `obstacle-maze` whether or
   not Escape Room lists it, so that is prompt-derived. List it only when
   subtracting it would leave nothing in the prompt pointing at it.

   **Options you reasoned forward from the genre go in `genre_derived`**, the
   same shape of list. A maze has an exit whether or not the prompt named one,
   and step 0 tells you to build it; that is neither the prompt asking nor the
   preset supplying, and collapsing it into either makes both numbers lie.

   Keeping the two thresholds apart is the point. "The prompt did not imply
   this" and "the prompt contradicts this" are different bars, and two lanes
   applying different ones make their option counts non-comparable — so the
   first never removes an option and only the second does, and both are
   recorded either way. That turns "this preset carries options that fight
   their own prompt" into a measurable finding rather than an invisible edit,
   without shipping the fight to the image model.

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

## Start with the warm-up

**The first prompt in your batch file is `WARMUP`, and it is not scored.** Run it
exactly as you would any other, then throw the record away — do not write it to
your file. Scoring starts at the second prompt.

This is not busywork. Measured across run 1, a lane's later records logged
about 10% more questions than its first few, with the builds themselves
unchanged: the reporting warms up even when the work does not. Questions are
what this run measures, so the warm-up comes out of the sample.

## Output

Append one JSON object per prompt, **one per line**, to the record file named in
your task. No wrapping array, no markdown fences, no commentary in the file.

**Append each record as soon as you finish that prompt.** Do not hold all of
them in your head and write the file at the end. Two reasons: the parent watches
file size to tell a working lane from a hung one, and a lane that dies at minute
24 having buffered everything delivers nothing at all. Incremental appends make
"report what you have" actually mean something.

**Parse your own file before you report, and do it as a loop over lines rather
than by eye.** In run 3 roughly fifteen lanes independently dropped the brace
closing `coverage` on their first appends. Every one that checked caught it and
repaired it in a single pass; the risk is the lane that does not check. Line
endings count too — one lane's file failed to parse on trailing `\r`, not on
its JSON.

**Do not invent keys.** The field table below is the whole schema. Run 3
collected `enriched_note`, `gate_note`, `segments_note` and `missing_note`,
each from a lane that had something to say and no obvious place for it. That
place is `notes_for_us`, which is read; an invented key is not, so the
observation is lost and the record no longer matches its siblings.

```json
{
  "item_id": "P0042",
  "handoff": {
    "genre_choice": { "genres": ["obby-platformer"], "shape": {"id": "course-tower", "type": "Path", "name": "Tower / Spiral Ascent"}, "preset": "Tower Obby", "pipeline": ["P6", "P2"], "image_prompt": [{"id": "path-track", "text": "..."}], "layout_placement": [{"id": "winner-zone", "type": "WinnerZone", "text": "..."}], "mechanics": [], "notes": [] },
    "theme": "Stylized / Toon",
    "theme_assumed": true,
    "scale": { "band": "block", "assumed": true },
    "open_questions": [ { "field": "scale", "ask": "..." } ]
  },
  "coverage": {
    "verdict": "partial",
    "captured": ["tower shape", "timed platforms", "reward at the top"],
    "preset_derived": ["obstacle-timing", "obstacle-climb"],
    "genre_derived": ["winner-zone"],
    "preset_rejected": [ { "id": "hazard-kill", "why": "the prompt says falling is the only failure, so contact-lethal surfaces contradict it" } ],
    "missing": [ { "field": "theme", "ask": "Should the tower read as candy-coloured or grimy industrial?" } ],
    "enriched_invented": [ { "detail": "a rotating spotlight at the summit", "kind": "safe_inference" } ]
  },
  "notes_for_us": [ "Two rules collided: step 4 sanctions asking where the run ends, step 5 forbids win-condition questions, and on this prompt they are the same question." ],
  "gaps": {
    "unmatched_options": [
      { "canonical": "leaderboard", "text": "a leaderboard showing fastest ascent times", "destination": "layout", "suggest_id": "scoreboard-display", "quantity": null, "routed_to": "layout" },
      { "canonical": "purchase menu", "text": "a shop menu on screen for buying coils", "destination": "ui", "suggest_id": null, "quantity": null, "routed_to": "mechanics" },
      { "canonical": "tower height", "text": "the tower must be exactly 500 studs tall", "destination": "layout", "suggest_id": null, "quantity": "500 studs tall", "routed_to": "constraints" }
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
| `coverage.preset_derived` | The option IDs in your handoff that are there **only** because the preset carries them. `[]` when every pick traces to the prompt. An option the prompt already implied stays out of this list even when the preset also lists it. This is how we measure whether presets quietly pad builds — one pilot prompt of three words came back with five picks, none of them the user's — so do not omit it to look clean. |
| `coverage.genre_derived` | Option IDs you reasoned forward from the genre under step 0 rather than reading off the prompt or taking from the preset — the exit a maze must have, the finish a race must have. `[]` when you reasoned none. Kept separate so neither of the other two numbers absorbs it. |
| `coverage.preset_rejected` | Preset options the prompt positively contradicts, as `{ "id", "why" }`. They stay in `preset_derived` but are **left out of `image_prompt` and `layout_placement`** — see rule 1. This field is what makes that removal reversible. `[]` is the common case. |
| `coverage.missing` | The questions you would have asked, **written out in full as you would put them to the user** — the wording is the thing being measured this run, not just the field name. `field` is `genre`, `shape`, `option`, `scale`, `theme`, or a free string. **`goal` and `player count` are no longer valid values**: the skill is instructed not to ask them, so a question about either is a defect rather than a gap. Do not answer your own questions; an unanswered question that would fill the hole is a pass. |
| `coverage.enriched_invented` | Concrete things in `enriched` the user never said. `kind` is `safe_inference` when set dressing that could not be wrong enough to matter, or `should_have_asked` when it committed to something load-bearing the user might reject. Cap at 5 entries; you are sampling, not diffing. |
| `notes_for_us` | Up to five short strings per record, addressed to the people who wrote the skills — a rule that contradicted another, an instruction you could not follow as written, a field the files could not fill. Not gameplay observations and not a summary of what you built; the two `gaps` fields already cover missing content. `[]` when the skills held up. The twenty-prompt pilot filed a hundred of these and seven turned into fixes, so this field is worth the words. |
| `gaps.unmatched_options` | Every request that got `id: null` because no loaded option covered it. **This is the most important field in the record** — it is the entire input to the missing-options analysis. See the five sub-fields below. Logging one here does **not** mean the request was dropped; `routed_to` says where it went, and only `nothing` means lost. |
| `handoff.constraints` | Rules over the whole build — `fidelity`, `build_rule`, `reference`. Omit the key when the prompt states none. New this run: 32 prompts in run 2 had one and nowhere to put it, so a run where this is never populated is a sign the rule is not being read. |
| `genre_choice.segments` | Present only when the prompt named several distinct spaces. New this run, for the same reason: 41 prompts in run 2 flattened a multi-space build into one shape. |
| `gaps.genre_gap` | `{ "name", "why" }`, only when the prompt is a real game concept that no genre in the index fits and you had to force it. `name` is a 2–4 word label for the *kind of game* — "performance venue", "destruction sandbox" — so gaps of the same kind group across hundreds of rows. `null` otherwise, which will be most rows. |
| `gaps.skill_gap` | `{ "name", "why" }`, only when the skill network itself could not express something **that was the scene's to carry** — a rule that gave the wrong answer, an instruction ambiguous in a way that mattered, a spatial request with nowhere to go. `name` is a short label reused across rows that hit the same wall. `null` otherwise. |
| | **Goal conditions, player counts, scoring and progression are not skill gaps.** They belong to another stream, they route to `genre_choice.mechanics`, and the skill is instructed not to ask about them. Logging them here was the largest source of false gaps in the first run. Their *spatial consequences* still count — "you win at the exit" means an exit, and a missing exit is a real gap. |

Be honest in `gaps`. A run where every row is `null` tells us nothing and is
the failure mode we are trying to avoid. A forced classification recorded as
clean is worse than no data.

### The six sub-fields of `unmatched_options`

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

**`suggest_id`** — the option ID you would have used had it existed, when you
can name one that nearly fit, `null` when nothing came close. It is how a
proposed catalogue row gets its name; a cluster of entries all suggesting the
same ID is the strongest case for adding it.

**`routed_to`** — where the request actually ended up. One of `layout`,
`image`, `mechanics`, `constraints`, or `nothing`.

This is the field that separates "we have no option ID for this" from "this
request is gone", and they are not remotely the same problem. Run 2 logged 927
spatial requests here and 900 of them had in fact reached the handoff and were
perfectly readable downstream — a vegetation description in `image_prompt` is
the catch-all working, not failing. Without this the run read as far worse than
it was, and it took a full analysis pass to unpick. Only 27 were genuinely lost,
and those are the ones worth anyone's time.

It replaces run 3's `carried`, which was a boolean covering only the image and
layout lists. That was too narrow in the one place it mattered most. A request
for a day–night cycle, an on-screen shop menu or a cat-sized player belongs in
`mechanics`; sending it there is correct, and `carried: false` recorded it as
a loss. 153 such requests were logged in run 3 and 95% sat in a record with a
populated `mechanics` pile, but nothing connected the request to the pile, so
the two cases could not be told apart and both were counted as gaps.

**`routed_to` is not `destination`.** `destination` is the consumer that
*should* handle the ask; `routed_to` is where you actually put it. They differ
exactly when something went somewhere imperfect, which is the interesting case
— an on-screen menu with `destination: ui` and `routed_to: mechanics` is a
sensible landing, the same ask with `routed_to: layout` built a GUI as a wall.

`nothing` is the only value that means the request was lost. Use it honestly;
it is rare and it is the number everyone reads.

Set it by looking, not by remembering: after you write the record, check that
the words are actually in the list you named.

**`quantity`** — any number, count, or dimension attached to the ask, verbatim:
`"75 lifeboats"`, `"1000 studs wide"`, `"exactly 3 zones"`. `null` when there
isn't one, which is most of the time. The pilot found numbers are load-bearing
and currently survive nowhere, so this field exists to measure how often that
happens and what kinds of numbers they are.

## Budget

**Budget: 35 minutes.** If you are not done, write the records you have and
report which `item_id`s you completed. A partial batch delivered beats a
complete one that never arrives. Do not restart or rewrite finished records to
make them prettier.

Report back: how many records you wrote, the item_ids you skipped if any, and
the two or three most interesting things you hit — a genre that did not fit, an
option that was missing, a rule in the skill that was ambiguous.

## Do not touch

Do not edit, and do not `git add`, `git commit`, or `git push`:

- any file under `.cursor/skills/` or `docs/`
- `evaluation/tools/*`
- `evaluation/LANE-BRIEF.md`
- any batch file, or any record file other than the one named in your task

Your record file is the only file you write. The parent commits.
