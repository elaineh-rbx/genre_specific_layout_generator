#!/usr/bin/env python3
"""One-shot: the Pipeline.md findings from the audit lane.

Three verified factual bugs, one dangling reference, and a run of sentences
describing how the document changed rather than how the pipeline works.

The factual three were each checkable against something that is not prose:
`check_pipeline_sync.py` reports four universal options carrying a route
where two sentences said three; the assumptions table runs A1-A6 where the
sentence above it said five; and the support-status note called P2 and P4
"real, buildable" a hundred lines above a readiness gate that lists them as
not production-ready.
"""
from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "docs" / "LayoutGen - Pipeline.md"

SUBS = [
    # --- verified factual bugs --------------------------------------------
    ("They arrive by ID like any other pick, and three of them carry a route (see Part VI).",
     "They arrive by ID like any other pick, and four of them carry a route (see Part VI)."),

    ("Build.md's **Universal Options** are inherited by all fifteen genres, so they cannot be listed in the per-genre column above. Three of the six carry a route:",
     "Build.md's **Universal Options** are inherited by all fifteen genres, so they cannot be listed in the per-genre column above. Four of the six carry a route:"),

    ("The pipeline is, in effect, a **single-surface, all-exterior, single-zone heightfield generator**. Five assumptions are hard-coded into it.",
     "The pipeline is, in effect, a **single-surface, all-exterior, single-zone heightfield generator**. Six assumptions are hard-coded into it."),

    ("> **Support status.** **P2** (elevation), **P4** (multi-zone), and **P6** (procedural-first) are real, buildable pipeline **phases**.",
     "> **Support status \u2014 designed versus running.** **P2** (elevation), **P4** (multi-zone) and **P6** (procedural-first) are all *designable* phases: none needs a capability the pipeline cannot have. Only **P6** is running today. See the readiness gate later in this Part for what can actually be delivered, and prefer P0 or P6 whenever the prompt does not require otherwise."),

    ("That is also why the catalogue is not generated *from* the axes \u2014 26 shapes share the all-defaults bundle, and what separates them is entirely their description.",
     "That is also why the catalogue is not generated *from* the axes \u2014 many shapes share the all-defaults bundle, and what separates them is entirely their description."),

    # --- dangling reference and the evaluation tooling block ---------------
    ("""**To read what intake actually asks**, every prompt-and-question pair recorded by the evaluation is browsable:

```
python evaluation/tools/eval_questions.py --pre              # counts by field
python evaluation/tools/eval_questions.py --pre --show goal   # every goal question, with its prompt
python evaluation/tools/eval_questions.py --pre --show all    # every pair
```

A worked selection \u2014 41 prompts, at least one per genre, filterable by field \u2014 is also rendered in the `intake-questions` canvas.

""",
     ""),

    # --- archaeology --------------------------------------------------------
    ("Part 0 below describes what they hand over; the two Parts note where the skill now owns behaviour this document used to only describe.",
     "Part 0 below describes what they hand over; where the two disagree, the skill is the live behaviour and this document is what needs updating."),

    ("Then *does anyone walk through it?* \u2014 no appends **`SET`**. This replaces the `Q0` node in Part IV's tree. |",
     "Then *does anyone walk through it?* \u2014 no appends **`SET`**. This answers Part IV's `Q0` before that tree runs. |"),

    ("This is the step the rest of this document used to skip, and it is not incidental: **almost every prompt leaves intake wanting to ask about something.**",
     "This step is not incidental: **almost every prompt leaves intake wanting to ask about something.**"),

    ("It is what keeps the image prompt from being saturated with things the image model cannot draw, and it is the source of the phase 4.5 work list, which had no home before.",
     "It is what keeps the image prompt from being saturated with things the image model cannot draw, and it is what phase 4.5 consumes as its work list."),

    ("* **`Q0` is already answered before the tree runs.** The non-spatial cutoff lives in `genre-choice` stage B (Part 0). It is now **two** questions, not one: *is there a space at all?*",
     "* **`Q0` is already answered before the tree runs.** The non-spatial cutoff lives in `genre-choice` stage B (Part 0), and it is **two** questions rather than one: *is there a space at all?*"),

    ("> **This tree is now executed by the intake skills** (Part 0), not by a human reading this section. What follows is the specification they implement;",
     "> **This tree is executed by the intake skills** (Part 0), not by a human reading this section. What follows is the specification they implement;"),

    ("| **Genre / reference game** | Loads the genre's shape, options, and presets | **No longer blocking.** A prompt with no discernible genre routes to the `no-genre` path, which asks the routing axes directly and builds. | `genre-choice` stage A |",
     "| **Genre / reference game** | Loads the genre's shape, options, and presets | **Not blocking.** A prompt with no discernible genre routes to the `no-genre` path, which asks the routing axes directly and builds. | `genre-choice` stage A |"),

    ("**Keyed on shape, and since Phase 6 there is exactly one table to key on.** Build.md's **Shape Catalog** holds every shape in the system",
     "**Keyed on shape, and there is exactly one table to key on.** Build.md's **Shape Catalog** holds every shape in the system"),

    ("This replaces a sixteen-row genre grid in which the same shape appeared under several genres and could disagree with itself. 45 shapes, 45 rows, no duplicates.",
     "One row per shape, so a shape cannot disagree with itself across genres. 45 shapes, 45 rows, no duplicates."),

    ("| `space-bounded` | P0 | The most-used shape in the catalogue: one bounded, single-level space. Arena, court, lobby and round map alike. |",
     "| `space-bounded` | P0 | One bounded, single-level space. Arena, court, lobby and round map alike. |"),

    ("**Two corrections this rekeying forced.** Sports previously read `P6-lite (template field)`, which is not a real modifier and is not what Build.md specifies \u2014 Sports is P0. Infinite Runner previously read `P6 / P5-adjacent`, but a runner has a very real 3D map; it is P6, and nothing about it is non-spatial.",
     "**Two routes that are easy to get wrong.** Sports is **P0** \u2014 there is no `P6-lite` modifier and a template field is not one. Infinite Runner is **P6** and is never P5-adjacent: a runner has a very real 3D map."),

    # --- residual evaluation framing ---------------------------------------
    ("`genres` may hold **two entries, dominant first**, which a sizeable minority of prompts genuinely are.",
     "`genres` may hold **two entries, dominant first**, which is a normal outcome rather than an edge case."),

    ("Each genre-critical structure needs one. Prioritize by triage-matrix frequency.",
     "Each genre-critical structure needs one."),

    ("`P4` routes the *build* when a shape happens to carry it, but nothing carries the *request*, and a meaningful slice of prompts ask for it. This is the largest remaining hole, and it is a schema change rather than a catalogue one.",
     "`P4` routes the *build* when a shape happens to carry it, but nothing carries the *request*. This is the largest remaining hole, and it is a schema change rather than a catalogue one."),
]


def main() -> int:
    text = DOC.read_text(encoding="utf-8")
    missing = [a for a, _ in SUBS if a not in text]
    for old, new in SUBS:
        text = text.replace(old, new, 1)
    DOC.write_text(text, encoding="utf-8")
    print(f"applied {len(SUBS) - len(missing)}/{len(SUBS)}")
    for m in missing:
        print("  MISS:", m[:95])
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
