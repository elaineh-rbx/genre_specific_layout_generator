#!/usr/bin/env python3
"""One-shot: take the golden-set numbers out of Build.md.

Build.md says what the system is. The evaluation that justified a rule lives in
`evaluation/`, and the reasoning lives in `plan.md`. A rule can state its own
strength -- rare, common, a large share -- without citing a corpus, and that is
what a generated skill file actually needs.
"""
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent / "docs" / "LayoutGen - Build.md"

SUBS = [
    ("**The reason the list is only a shortlist is measured.** Of 620 real prompts, the rows reporting a shape problem overwhelmingly said *\"this genre's shapes all assume X\"* rather than *\"nothing describes this\"* \u2014 the shape they needed existed, filed one genre over. A prompt wanting one large interior finds Animal Sim assumes wilderness, Simulation assumes an outdoor shared world, and Roleplay's housing shapes are all towns. So when the shortlist misses, the answer is almost never a new shape.",
     "**When the shortlist misses, the shape you want is almost always elsewhere in the catalogue rather than missing from it.** A prompt wanting one large interior finds Animal Sim assumes wilderness, Simulation assumes an outdoor shared world, and Roleplay's housing shapes are all towns \u2014 while `interior-single` sits in the catalogue the whole time. Look before concluding that nothing fits."),

    ("Measured against 620 real prompts, **404 (65%) already route entirely on P0 or P6.** Of the 216 that carry a modifier, most earned it \u2014 186 modifier instances are required by something the prompt says, against 74 taken from a shape or preset default. So this rule moves roughly **54 rows, 9%**, and leaves the majority untouched. It is a tie-breaker, not a filter.",
     "Most builds already route entirely on P0 or P6, and most modifiers that do appear are required by something the prompt actually says rather than inherited from a default. So this rule moves few builds and leaves the majority untouched. **It is a tie-breaker, not a filter.**"),

    ("Roughly half of the apparently-assumed `P3` rows are like this.",
     "Much of the `P3` that looks assumed is like this."),

    ("It exists for a different problem \u2014 the prompt that is not a 3D game at all \u2014 and that problem is rare: across 620 real prompts **the corpus contained zero 2D games**, so a P5 that fires on \"nobody walks here\" is wrong far more often than right.",
     "It exists for a different problem \u2014 the prompt that is not a 3D game at all \u2014 and **that problem is genuinely rare**, so a P5 that fires on \"nobody walks here\" is wrong far more often than right."),

    ("Take neither. This is common enough to matter: in 620 real prompts, **182 \u2014 nearly a third \u2014 drew a preset that did not fit or actively fought the prompt**, almost always on the shape.",
     "Take neither. **This is common rather than exceptional** \u2014 a large share of prompts draw a preset whose mode is right and whose shape is wrong."),

    ("**Drop preset options the prompt contradicts.** 145 rows kept one, and it is not cosmetic",
     "**Drop preset options the prompt contradicts.** Keeping one is a frequent mistake, and it is not cosmetic"),

    ("Measured against 620 real prompts, **14% were genuinely two genres**, and the most common single classification error was naming one where the prompt meant two. Four worked cases:",
     "**Two-genre prompts are common, and the most frequent classification error is naming one where the prompt meant two.** Four worked cases:"),

    ("so this row does not introduce a second rule \u2014 it gives that answer somewhere to live on the shape axis, which four golden-set rows asked for after `SET` itself existed.",
     "so this row does not introduce a second rule \u2014 it gives that answer somewhere to live on the shape axis."),

    ("If that sentence cannot be written, a catalogue shape fits and should be used. The reason is not bureaucratic: the golden set's most useful gap notes are exactly this sentence, and a bundle described twice is how the catalogue earns its next row.",
     "If that sentence cannot be written, a catalogue shape fits and should be used. The reason is not bureaucratic: that sentence is what makes a described shape reviewable, and a bundle described twice is how the catalogue earns its next row."),

    ("Two prompts independently describing the same bundle *and* the same kind of space is how a described shape earns a name \u2014 twelve rows and five rows converging is precisely how the two shapes above were coined.",
     "Two prompts independently describing the same bundle *and* the same kind of space is how a described shape earns a name; that convergence is how the shapes above were coined."),

    ("**How often this actually bit:** in 620 real prompts, **4 rows**. Forty-seven prompts explicitly described one continuous map and forty-three were routed correctly. So this is a rule for a rare case, and it must not become a reason to second-guess a route the prompt never mentioned \u2014 **silence is not a contradiction.** When the prompt says nothing, take the default.",
     "**This is a rule for a rare case.** Nearly every prompt that describes one continuous map is already routed correctly without it, so it must never become a reason to second-guess a route the prompt did not mention \u2014 **silence is not a contradiction.** When the prompt says nothing, take the default."),

    ("They exist because the alternative is worse. Each was measured against 620 real prompts and requested in eleven to fifteen different genres, so filing them per-genre would restate the same row seventy-eight times \u2014 and leaving them out is what produced the largest hole in the system, with *who is in the world* having no home anywhere.",
     "They exist because the alternative is worse. Each is asked for across eleven to fifteen different genres, so filing them per-genre would restate the same row dozens of times \u2014 and leaving them out is what produced the largest hole in the system, with *who is in the world* having no home anywhere."),

    ("never a default and never a suggestion. Measured against 620 prompts, each of the six would fire on 6\u201315% of them, so a run that applies one unasked is wrong far more often than it is right.",
     "never a default and never a suggestion. Each of the six is wanted by only a small minority of prompts, so a run that applies one unasked is wrong far more often than right."),

    ("It exists and was chosen zero times in a 620-prompt evaluation, while a spelling game went to Party & Casual instead.",
     "It is easy to overlook, and spelling games get filed under Party & Casual instead."),

    ("They were one preset citing both, and it defaulted to buildable plots \u2014 so all three prompts in a 620-prompt evaluation that named Brookhaven outright got a grid of empty lots.",
     "A single preset citing both defaults to buildable plots, so a prompt naming Brookhaven outright gets a grid of empty lots."),

    ("It is a large, well-known Roblox family, and in a 620-prompt evaluation its members scattered across four genres and five presets, because each instance looks locally like whatever it borrowed:",
     "It is a large, well-known Roblox family whose members scatter across four genres and five presets, because each instance looks locally like whatever it borrowed:"),

    ("* **A stage with an audience is a layout, and it had no home.** In a 620-prompt evaluation, nine workers independently coined the phrase *performance venue* for concerts, festivals, talent shows and a dance institution. Every other shape here is architecture you walk around and look at,",
     "* **A stage with an audience is its own layout.** Concerts, festivals, talent shows and dance institutions are all the same build, and every other shape here is architecture you walk around and look at,"),

    ("A modelled vehicle, a pinball machine, a city you zoom into \u2014 three evaluation prompts asked for a build whose subject is an object rather than a place, and every shape here assumed an avatar moving around.",
     "A modelled vehicle, a pinball machine, a city you zoom into \u2014 the subject is an object rather than a place, and every other shape here assumes an avatar moving around."),

    ("This is not a rare fallback. Measured against 620 real prompts it was the right answer **46 times (7%)**, and its *Explorable Place* preset was chosen 19 times \u2014 more often than most of the 77 genre presets.",
     "**This is not a rare fallback.** It is the right answer on a meaningful share of prompts, and its *Explorable Place* preset is picked more often than most genre presets."),
]


def main() -> int:
    text = BUILD.read_text(encoding="utf-8")
    missing = [a for a, _ in SUBS if a not in text]
    for old, new in SUBS:
        text = text.replace(old, new, 1)
    BUILD.write_text(text, encoding="utf-8")
    print(f"applied {len(SUBS) - len(missing)}/{len(SUBS)}")
    for m in missing:
        print("  MISS:", m[:90])
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
