# Audit: `docs/LayoutGen - Pipeline.md`

| Line | Quoted snippet (<=15 words) | Category (1-6) | Recommended fix |
| :---- | :---- | :----: | :---- |
| 10 | skill now owns behaviour this document used to only describe | 1 | Declarative: "Skills implement Part V/VI; this doc specifies the handoff they emit." |
| 43 | This replaces the `Q0` node in Part IV's tree | 1 | State current behaviour only: "Stage B answers Q0 before Tree A runs." |
| 75 | every prompt-and-question pair recorded by the evaluation | 2 | Delete; point to intake skills or Part V policy instead. |
| 78–80 | `eval_questions.py --pre` command block | 2 | Remove evaluation tooling from the routing spec entirely. |
| 83 | 41 prompts, at least one per genre | 2 | Delete corpus sample count; drop or replace canvas reference. |
| 83 | `intake-questions` canvas | 5 | Remove or link to a path that exists in-repo. |
| 96 | phase 4.5 work list, which had no home before | 1 | Present tense: "phase 4.5 consumes the `layout_placement` stream." |
| 126 | sizeable minority of prompts genuinely are | 2 | Drop measurement framing: "may hold two entries, dominant first." |
| 128 | three of them carry a route | 3 | Correct to four (`building-interior`, `terrain-relief`, `water-body`, `island-cluster`). |
| 160 | Five assumptions are hard-coded into it | 3 | Change to six, or drop the count and refer to the table. |
| 175 | paired images in `example_images/` | 5 | Verify path exists or remove image citations. |
| 291 | It is now **two** questions, not one | 1 | Declarative: "Stage B asks two questions: space exists? anyone walks?" |
| 317 | per Part I metrics in the Build doc | 5 | Cite the actual Build section (Obby presets / structure-criticality), not Part I. |
| 327 | This tree is now executed by the intake skills | 1 | "Executed by intake skills (Part 0); below is the specification." |
| 333 | **No longer blocking.** A prompt with no discernible genre | 1 | Present tense: "Genre is optional; no-genre routes via axes." |
| 390 | This replaces a sixteen-row genre grid | 1 | Delete migration note; keep "45 shapes, 45 rows." |
| 396 | The most-used shape in the catalogue | 2 | Remove frequency claim; keep spatial definition only. |
| 458 | 26 shapes share the all-defaults bundle | 3 | Reconcile with Build catalog (18 blank-Pipeline rows); fix or delete count. |
| 462 | Three of the six carry a route | 3 | Match line 128 fix: four options carry a route. |
| 246 | P2, P4, and P6 are real, buildable pipeline phases | 3 | Separate design intent from readiness: P6 is running; P2/P3/P4/CHECK are deferred. |
| 573 | Prioritize by triage-matrix frequency | 2 | Delete measurement cue; prioritize by genre-critical structures only. |
| 579 | a meaningful slice of prompts ask for it | 2 | Drop corpus framing; state the schema gap without prompt prevalence. |

**Worst problem:** Lines 75–83 embed the golden-set evaluation corpus directly into the routing spec — prompt-and-question pairs, field counts, and `eval_questions.py` invocations. That block is category-2 junk the user already stripped elsewhere; it also points at a missing `intake-questions` canvas. Removing it (and the nearby "41 prompts" line) is the highest-value cleanup. Secondary: internal contradictions on assumption count (five vs six), universal-option route count (three vs four), and the "26 all-default shapes" figure.
