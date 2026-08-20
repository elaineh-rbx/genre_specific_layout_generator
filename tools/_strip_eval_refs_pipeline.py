#!/usr/bin/env python3
"""One-shot: same rule as `_strip_eval_refs.py`, applied to Pipeline.md.

Pipeline.md routes; it is not a place to report a study. Where a number was
the argument, the rule keeps its plain strength and the number goes back to
`evaluation/`.
"""
from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "docs" / "LayoutGen - Pipeline.md"

SUBS = [
    ("Part V's Decision Tree B is the full policy; the cap there is three questions and the measurement above says two or three is what the work actually needs.",
     "Part V's Decision Tree B is the full policy, and its cap is three questions."),

    ("**A preset counts as a question.** It is offered, not applied. Everything downstream assumes the user saw the preset and accepted it, so a run that silently applies one has skipped a step. *(The evaluation had to treat an offered preset as accepted, since its workers could not ask \u2014 which is why the preset numbers in the report are its least reliable measurement.)*",
     "**A preset counts as a question.** It is offered, not applied. Everything downstream assumes the user saw the preset and accepted it, so a run that silently applies one has skipped a step."),

    ("**To read the actual questions** rather than the counts, every prompt-and-question pair from the golden set is browsable:",
     "**To read what intake actually asks**, every prompt-and-question pair recorded by the evaluation is browsable:"),

    ("python evaluation/tools/eval_questions.py --pre --show all    # all 1,494 pairs",
     "python evaluation/tools/eval_questions.py --pre --show all    # every pair"),

    ("`genres` may hold **two entries, dominant first**. About 14% of real prompts are genuinely two genres.",
     "`genres` may hold **two entries, dominant first**, which a sizeable minority of prompts genuinely are."),

    ("It is the only phase that talks back to the user: on 617 of 620 real prompts it had at least one question to ask first, so treat phase 1 as a **round trip, not a read**.",
     "It is the only phase that talks back to the user, and almost every prompt gives it something to ask, so treat phase 1 as a **round trip, not a read**."),

    ("Against 620 real prompts, **404 (65%) already route entirely on the proven pipeline**, and of the 260 modifier instances among the rest, 186 were required by the prompt against 74 taken from a default \u2014 so the rule moves about 9% of rows. Two guards, both in Build.md's *Pipeline costs*:",
     "**Most builds already route entirely on the proven pipeline**, and most modifiers that do appear are required by something the prompt says rather than inherited from a default \u2014 so this rule moves few builds. Two guards, both in Build.md's *Pipeline costs*:"),

    ("**Question caps.** This section says \"cap at 3 questions,\" and the measurement in Part 0 supports it: across 620 real prompts intake wanted a mean of 2.4 questions, and 578 of them wanted either two or three. Three is the ceiling, not the target.",
     "**Question caps.** This section says \"cap at 3 questions,\" and Part 0 agrees: two or three is what the work needs. **Three is the ceiling, not the target.**"),

    ("Those are limits on each exchange; **the three-question cap here is the limit on the whole round trip**, and it is the one to hold to. Note that the earlier claim that most prompts take a single question was wrong: two is the single most common number and only 19 of 620 prompts needed just one.",
     "Those are limits on each exchange; **the three-question cap here is the limit on the whole round trip**, and it is the one to hold to. Do not read it as \"usually one\" \u2014 two is the common case and one is rare."),

    ("**Every axis defaults to the cheap answer** \u2014 exterior, single-surface, single zone, dressed, grounded \u2014 so the default is P0 and only a stated non-default costs anything. This was the right outcome on 7% of 620 real prompts, so it is a live path rather than a fallback.",
     "**Every axis defaults to the cheap answer** \u2014 exterior, single-surface, single zone, dressed, grounded \u2014 so the default is P0 and only a stated non-default costs anything. This is the right outcome often enough to be a live path rather than a fallback."),

    ("**`P6` is never a default** \u2014 structural validity is the game, and an image model cannot guarantee it. Measured against 620 prompts this fired on 4 rows, so it is a correction for an explicit contradiction, not a licence to re-derive routes the prompt never mentioned.",
     "**`P6` is never a default** \u2014 structural validity is the game, and an image model cannot guarantee it. This fires rarely: it is a correction for an explicit contradiction, not a licence to re-derive routes the prompt never mentioned."),

    ("Intake therefore prefers the route that stays on P0 or P6 whenever nothing in the prompt requires otherwise, states the deferral to the user rather than downgrading silently, and records it in `notes`. Against 620 real prompts, 404 (65%) already routed entirely on the proven pipeline, so this settles ties rather than filtering work.",
     "Intake therefore prefers the route that stays on P0 or P6 whenever nothing in the prompt requires otherwise, states the deferral to the user rather than downgrading silently, and records it in `notes`. Most builds are already there, so **this settles ties rather than filtering work.**"),

    ("`P4` routes the *build* when a shape happens to carry it, but nothing carries the *request*, and roughly 35 of 620 prompts asked for it. This is the largest remaining hole and it is a schema change, not a catalogue one.",
     "`P4` routes the *build* when a shape happens to carry it, but nothing carries the *request*, and a meaningful slice of prompts ask for it. This is the largest remaining hole, and it is a schema change rather than a catalogue one."),
]


def main() -> int:
    text = DOC.read_text(encoding="utf-8")
    missing = [a for a, _ in SUBS if a not in text]
    for old, new in SUBS:
        text = text.replace(old, new, 1)
    DOC.write_text(text, encoding="utf-8")
    print(f"applied {len(SUBS) - len(missing)}/{len(SUBS)}")
    for m in missing:
        print("  MISS:", m[:90])
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
