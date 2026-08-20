# Run 2 pilot — one prompt, one lane

You are executing the LayoutGen intake skills on **exactly one user prompt** and
writing down what they produced. This is a pilot ahead of a 620-prompt run; the
point is to find out whether the skills behave as written, so **execute them
faithfully rather than helpfully**. If a rule produces a poor result, follow it
and say so in the record. Do not improve on the skills.

## Budget

**15 minutes.** If you are not done, write the record with what you have and
mark `"incomplete": true`. A partial record delivered beats a complete one that
never arrives.

## Read scope

Read these and nothing else. Do not explore the repository.

- `.cursor/skills/layout-intake/SKILL.md` — start here, follow its dispatch
- `.cursor/skills/genre-choice/SKILL.md`
- `.cursor/skills/genre-choice/genres/<the one or two you classify into>.md`
- `.cursor/skills/genre-choice/no-genre.md` — only if you classify to no genre
- `.cursor/skills/genre-choice/shapes.md` — only if the genre's typical shapes miss
- `.cursor/skills/genre-choice/options.md` — only if the genre's own table and the
  universal six both miss
- `evaluation/LANE-BRIEF.md` — the record format and the field rules

`docs/LayoutGen - Build.md` and `Pipeline.md` are **out of scope.** The skills
are self-contained by design; needing them is itself a finding worth recording.

## What to produce

One JSON object written to the output file named in your task. Follow the record
format in `evaluation/LANE-BRIEF.md`, with three changes for this run:

1. **`coverage.missing` is the main deliverable.** Write each question out in
   full, exactly as you would put it to the user. Do not answer them. `field` is
   one of `genre`, `shape`, `option`, `scale`, `theme`, or a free string —
   **`goal` and `player count` are not valid**, and asking about either is a
   defect to note rather than a gap to record.
2. **`genre_choice.mechanics`** holds everything the prompt asked for that is
   not the scene. A full array is a sign of correct triage, not of failure.
3. Add a top-level **`"notes_for_us"`**: at most five short strings, anything
   about *the skills* that was wrong, ambiguous, contradictory, or missing. This
   is where you tell us the instructions failed you. Empty array if nothing.

Add `"item_id"` and `"bucket"` exactly as given in your task.

## Do not touch

Write **only** your own output file. Do not edit any skill, any file under
`docs/`, `pipeline-viewer.html`, `evaluation/LANE-BRIEF.md`, or any other lane's
output. **Do not run `git add`, `git commit`, or `git push`** — the parent
commits everything once, so that shared files are resolved in one place.
