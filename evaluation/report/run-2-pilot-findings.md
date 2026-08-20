# Run 2 pilot — what twenty prompts found before the 620

Twenty prompts, one agent each, no shared context. Selected by failure mode
from run 1's evidence rather than sampled: unreachable options, mechanics-heavy
prompts, free-text-heavy prompts, terse references, multi-map, oversized scale,
and no-genre. Records in `evaluation/data/run-2/pilot/records/`.

The pilot existed to find what would break at 620, and it did. **Seven defects,
three of them in work landed the same day.** All seven are fixed; the pilot
records themselves predate the fixes and should not be read as a measurement of
the current skills.

## The questions worked

This was the run's deliverable, and it is the part that needs no changes.

| | Result | Target |
| :---- | ---: | ---: |
| questions per prompt | 3.80 | ≤ 4 |
| offering enumerated choices | 99% | ~75% |
| genuinely two-subject | 1 of 76 | 0 |
| about goals, scoring or player counts | **0** | 0 |

The forbidden-field result is the one that matters most. Run 1 spent 501
questions on goal conditions and 21 on player counts across 637 records; the
rewritten step 5 spent none, and the budget went to options instead — 30 of the
76, a field run 1 had no category for. They are load-bearing rather than
padding: *"Is the lobby part of the same map as the battlefield, or a separate
place players get teleported out of?"* is the P4 fork asked in the user's own
terms, and *"Where do players buy the better guns — at a shop they walk up to,
or from a menu on screen?"* is the inside/outside fork.

One record exceeded the cap at five questions. Its lane explained why:
`layout-intake` mandates a theme question on silence while step 5 caps the
total, and that prompt had five real holes. The theme fix below removes the
collision.

Question counts sit at the ceiling rather than the 2.5 estimated from run 1.
The estimate assumed dropping goal and player count would free budget; instead
option questions took it. Worth watching at 620, not worth acting on at 20.

## What the pilot broke

Counts are lanes reporting independently, out of 20.

**Shape names missing from the shortlist — 9 lanes.** Step 6 emits `shape.type`
and `shape.name`; a genre's *Typical shapes* line gave bare IDs; the split
existed only in `shapes.md`, which step 2 says not to load when the shortlist
fits. Lanes either broke read scope or emitted nulls. This would have hit the
common case in all 620. Fixed: the shortlist now carries `Type (Flavor Name)`
inline, using the genre's own rewording where it has one.

**The option catalogue had no Type — 6 lanes.** Same defect, one level down, in
`options.md` as shipped that morning. A lane reaching an option through the new
catalogue could not fill `layout_placement.type`. Fixed, and the guard now
asserts every row has one.

**The catalogue settled destinations the genres dispute — 1 lane.** Four
options have a `Goes to` that differs between the genres wording them.
The catalogue published whichever it saw first while its own preamble said the
destination came with the row. `trigger-scoring` was given as `layout` against
`sports.md`'s `both`. Marked `*varies*`, as routes already were.

**Theme: infer or emit null — 7 lanes.** Two lanes, same rule, opposite calls.
*"Swing around the city"* gave Modern Urban; *"a copy of prison life"* gave
`null` and spent a question on the look. Naming a place or a real game is a
theme statement in different words. Both now infer, marked `theme_assumed`.

**Scale: no rule for silence — 7 lanes.** The ask trigger fired only when a
prompt named an extent without its contents, so the common case — naming
neither — guessed a band silently. Block is now the default, with a question
spent when a different band would be built differently. One lane also found the
trap in *the detail wins*: hide-and-seek props are Room-sized, but nobody plays
hide and seek in one room.

**Presets padding terse prompts — 7 lanes.** *"uhmm a avatar tower"* produced
five picks, and its lane wrote: *"four of the four options in the handoff are
preset-derived, none traceable to the prompt."* Decision was to keep and label
rather than withhold. `preset_derived` now means the preset is the **only**
reason a pick is present, and options reasoned forward from the genre get their
own `genre_derived` list instead of distorting either count.

**Routes bent toward what is built — 6 lanes.** Step 4 said to prefer P0/P6
because P2 and P4 are not ready, and also that a plainly stated feature
requires its modifier. A prompt naming a lobby and a separate arena satisfies
both. Resolved in favour of intent: the skill emits what the game needs, and
re-routing against pipeline readiness belongs to a later system.

## Not a defect

Seven lanes could not fill `coverage.enriched_invented`. The pilot's
`prompts.json` was hand-built and carries only `item_id`, `bucket` and
`prompt`; the real batches in `evaluation/data/batches/` carry `enriched`. An
artifact of the harness, not of the skills.

## Reading the pilot records

They were written against the pre-fix skills. Six lanes' `notes_for_us` name
defects that no longer exist, and shape and option types are null or guessed in
records where the file could not supply them. **Do not pool them with the 620.**
