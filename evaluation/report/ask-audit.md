# Audit A — do the questions intake asks give a clear path to proceed?

The golden-set run recorded **1,494 questions across 617 of 620 prompts** and
never graded them. This grades them, offline, against the records already on
disk. No new generation, no LLM judge.

The question is not "are these good questions." It is the one that decides
whether the skill can proceed: **if the user answered every question, would we
have what we need — and is there anywhere to put the answer?**

Reproduce with:

```bash
python evaluation/tools/eval_ask_audit.py --pre    # what intake would raise
python evaluation/tools/eval_ask_audit.py          # + coverage.missing
```

---

## The headline

**The questions are well aimed. The schema is what is missing.** 78% are
closed, 74% of answers land somewhere, and the single largest failure is one
absent field rather than a targeting problem.

**Adding a `goal` field takes clear-path rows from 37% to 77%.** That one change
is worth more than every other fix in this report combined.

| Handoff gains | Rows with a clear path |
|---|---|
| today | 230 (37.1%) |
| **+ `goal`** | **477 (76.9%)** |
| + `goal`, `count` | 492 (79.4%) |
| + `goal`, `count`, `player count`, `progression` | 499 (80.5%) |

`plan.md` D5 already logs goal / win-condition as "the top open question" with
no owner in either skill. **This is the number that sizes it**, and it agrees
with the 48-row cluster Phase 6 found independently.

---

## Check 1 — landing: if the user answered, where does it go?

The handoff carries `genres`, `shape`, `preset`, `pipeline`, `image_prompt`,
`layout_placement`, `theme`, `scale`, and `notes`. `notes` is prose the pipeline
cannot act on, so it is not a home. Geometry and volumes always land, because
`genre-choice` lets free text enter the two streams with `id: null`.

On the 1,494 pre-pass questions:

| Landing | Questions | Share |
|---|---|---|
| a dedicated field | 1,066 | 71.4% |
| an option entry | 44 | 2.9% |
| **only partly** | 334 | 22.4% |
| **nowhere** | 50 | 3.3% |

**Four fields carry 89% of everything asked** — `scale` 440, `theme` 329,
`goal` 312, `shape` 254. Three of the four have a home. The one that does not
is the whole of the "only partly" column.

`goal` is scored *partial* rather than *none* deliberately: a win condition can
put a `WinnerZone` on the map, so the spatial half lands. The condition itself
— "hatch all six species", "climb to the top and back down" — has no field.

Everything with no home at all is small and long-tailed: `player count` 6,
`progression` 7, `ui` 3, `movement` 3, `platform` 3, `sky` 1, `multi-map` 1.
Real, but not what is blocking builds.

---

## Check 2 — closure: what stays open after every question is answered

`coverage.missing` and `open_questions` are gap+question pairs by construction,
so this check looks at gaps recorded *elsewhere* in the record — `skill_gap`,
`genre_gap`, and a null `theme` that raised no theme question.

| | Gaps | Rows |
|---|---|---|
| a question would fix it, but none was asked | 95 | 93 (15%) |
| **no question could fix it** — the schema has no field, option, or genre for the answer | 583 | 495 (80%) |

**The second row is the finding, and it is not a question defect.** 595 of 620
rows recorded a `skill_gap`; classified by whether *asking* would help, the
overwhelming majority are containers we do not have rather than facts we do not
know. The user already told us and we had nowhere to put it. That is check 1
seen from the other side, and it is the same missing-channel result as §4 of the
main report.

The genuinely unasked 95 are worth fixing but are a much smaller problem:
`spatial` 27, `shape` 14, `genre` 8, `multi-map` 6.

**One rule is measurably not firing.** Intake says that when the prompt is
silent on theme, emit `null` *and add an open question*. Five rows have a null
theme and no theme question — and two of those five (P0360 "dont ask for input
just build the game", P0569) are prompts that forbade questions, so the real
violation count is **three**. The rule essentially holds.

---

## Check 3 — form: closed or open-ended?

Most questions already offer alternatives to pick between, which is what the
answer spaces mostly want:

| Form | Questions | Share |
|---|---|---|
| closed — offers alternatives | 1,171 | 78.4% |
| open-ended | 323 | 21.6% |
| **two asks in one question** | 160 | 10.7% |

### The sharpest actionable defect: open-ended questions about a 4-value enum

`scale` is the most-asked field at 440, and `scale.band` accepts exactly four
values — Room, Block, District, Region. **124 of those 440 (28%) are asked
open-ended anyway.** The two styles sit side by side in the same records:

> P0006 open: *"How big is each dungeon zone?"*
> P0006 closed: *"How large should each dungeon zone be — a single room you can see across, or a hall that takes half a minute to cross?"*

The closed form translates the enum into walkable distance, which is what the
skill's own avatar baseline is for. The open form invites answers the field
cannot hold, and it demonstrably does: P0005 was told **5,000 square
kilometres**, and P0011 **a trillion blocks**. Both then needed a second round
trip to negotiate back down to something buildable.

`count` is the worst rate at 79% open, but the answer there is a number rather
than a choice, so multiple choice is the wrong fix — it needs a stated default
with a correction invited.

### Compound questions

10.7% carry two asks in one, which is the defect that breaks multiple choice:
*"How many horse maps, and how big is each one?"* (P0012) cannot be answered by
picking an option. These should split.

---

## The field label is unreliable, and the expensive decisions hide behind it

`field` is what tells downstream who consumes an answer, and it does not survive
inspection. Sampling the `scale` bucket finds at least three different questions
wearing one label:

| Row | Question filed as `scale` | What it actually decides |
|---|---|---|
| P0004 | *"a tight 40-stud room or a big open boss hall?"* | genuinely `scale.band` |
| P0010 | *"are the fifteen areas one continuous world you run between, or separate places you teleport to?"* | **`P4` — the most expensive route in the pipeline** |
| P0011 | *"one island cluster, or a set of separate maps unlocked as you level?"* | **`P4`** |
| P0012 | *"how many horse maps, and how big is each one?"* | a count, plus multi-map |

The one-map-or-many question is the 30-row cluster Phase 6 flagged as having no
field at all, and it is being asked under the label of the cheapest decision we
make. Requiring the router to name the *route* a question would change, rather
than the field, would separate these.

---

## What this does not measure

**Restraint is untested, and it is the thing the audit cannot reach.** The lane
brief forbade asking and told workers to record the question instead, so a
question cost nothing to raise. The recorded mean is **2.4 per row** against a
skill budget of about one. So these numbers measure *what was uncertain*, not
what the skill would say out loud, and nothing here shows whether it picks the
right single question. That needs a multi-turn run.

**349 near-duplicates were folded away** on the combined set — the same question
recorded terse in `open_questions` and fuller in `coverage.missing`. Counts on
the combined set were inflated by ~12% before collapsing; the `--pre` set is
unaffected.

**Field labels are keyword-normalised, not taken at face value**, because the
records hold 464 distinct `skill_gap` names and inter-worker naming overlap on
free text was 0.30. `unclear` residue is 23 of 1,494 pre-pass questions (1.5%),
listed by `--residual`.

**Question form is detected by regex**, not judged. It counts whether
alternatives are *offered*, not whether they are the right alternatives or
exhaustive.

---

## Recommendations, in order of measured value

1. **Add a `goal` field to the handoff.** 37% → 77% of rows get a clear path.
   Everything else on this list is rounding error next to it.
2. **Make `scale` questions always present the bands**, phrased as crossing
   time. 124 open-ended asks against a four-value enum, with two prompts already
   answering in square kilometres and trillions of blocks.
3. **Split compound questions.** 160 of 1,494 cannot be answered by picking.
4. **Have the router name the route a question would change, not the field.**
   Two `P4` decisions are currently filed as `scale`.
5. Add `count` and `player count` fields — worth ~3% together, cheap.

Items 2 and 3 are edits to `layout-intake/SKILL.md` and `genre-choice/SKILL.md`.
Item 1 is a schema change and touches the pipeline.

**Follow-up handling is a separate concern and is not measured here.** If an
answer does not resolve the gap, or comes back incoherent, nothing in the
current skills says what to do. Worth a rule, but it is not what is blocking the
620 rows.
