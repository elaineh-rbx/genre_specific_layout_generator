### Hand-written files

| File | Line | Quoted snippet (<=15 words) | Category (1-6) | Recommended fix |
| :---- | :----: | :---- | :----: | :---- |
| `.cursor/skills/genre-choice/SKILL.md` | 354 | "About half of the rows that look…" | 1 | Delete the fraction; keep the operative rule ("read for the feature, not the keyword"). |
| `.cursor/skills/genre-choice/SKILL.md` | 71–72 | "They used to be one, and collapsing…" | 2 | Drop history and accuracy claim; keep "two questions, this order, do not merge." |
| `.cursor/skills/layout-intake/SKILL.md` | 132–134 | "Part V of Pipeline.md proposed wiring…" | 2 | State the rule only: goal is not a concern; ending place belongs to `genre-choice`. |
| `.cursor/skills/genre-choice/SKILL.md` | 44–420 | (no round-trip question budget stated) | 4 | Add Pipeline.md's three-question ceiling for the whole trip; preset counts as one; infer stage B when possible. |
| `.cursor/skills/genre-choice/SKILL.md` | 190 | "reaching for forty rows when five" | 6 | Change to 45 (matches `shapes.md` and Build.md). |
| `.cursor/skills/genre-choice/SKILL.md` | 232–237 | "One shape… may come from anywhere" | 4 | Align Build.md Mixing section (still says dominant genre owns shape) or add a cross-doc note in the skill. |
| `.cursor/skills/genre-choice/SKILL.md` | 557–566 | "## Maintenance" / `generate_genre_skills.py` | 2 | Remove from runtime skill; belongs in repo docs or generator header only. |

### Generated files (fix in Build.md or the generator)

| Generated file | Line | Quoted snippet (<=15 words) | Category (1-6) | Where in Build.md it comes from |
| :---- | :----: | :---- | :----: | :---- |
| `genre-choice/genres/*.md`, `no-genre.md` (×16) | ~70 | "wanted by only a small minority of prompts" | 1 | Universal Options block, ~line 546 |
| `genre-choice/genres/*.md`, `no-genre.md` (×16) | ~59 | "what produced the largest hole in the system" | 2 | Universal Options intro, ~line 535 |
| `genre-choice/genres/*.md`, `no-genre.md` (×16) | ~59 | "asked for across eleven to fifteen different genres" | 1 | Universal Options intro, ~line 535 |
| `genre-choice/genres/*.md`, `no-genre.md` (×16) | ~76 | "See *The Five Routing Axes* in Build.md" | 3 | Universal Options pipeline notes, ~line 552 |
| `genre-choice/genres/shooter.md` | ~64 | "see *Pipeline costs* in Build.md" | 3 | Shooter genre notes, ~line 987 |
| `genre-choice/genres/simulation.md` | ~47 | "see *Pipeline costs* in Build.md" | 3 | Simulation Idle note, ~line 1047 |

**Not flagged:** No remaining hits for 620, corpus, workers, or evaluation. Genre index (15 files), six universal options, and 45 shapes in `shapes.md` match current counts. Goal/win-condition policy and P0/P6-only production readiness agree across both SKILL files and Pipeline.md. Goal rules are consistent between `layout-intake` and `genre-choice`.

---

The worst problem is the **missing round-trip question cap** in `genre-choice/SKILL.md`. Pipeline.md Part V fixes the ceiling at three questions for the entire intake, counts the preset offer as one, and tells the agent to infer rather than ask — but the skill only caps individual steps (one clarifying question, one open question, ~five tune items) while stage B can still mandate two user-facing questions before preset, tune, and the mandatory step-5 question. An agent following the skill literally can blow past the budget every time. Second priority: evaluation-flavoured prose ("minority of prompts," "About half," "eleven to fifteen genres") still lives in the hand-written skill and in every generated Universal Options block via Build.md.
