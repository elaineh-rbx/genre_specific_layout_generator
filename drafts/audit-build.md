# Build.md junk audit

| Line | Quoted snippet (<=15 words) | Category (1-6) | Recommended fix |
| :-- | :-- | :-- | :-- |
| 56 | `(was TravelPoint)` | 1 | Drop rename history; keep current term only. |
| 57 | `(was NPC/mob SpawnZone)` | 1 | Same — vocabulary is current state, not changelog. |
| 284 | `P0 and P6 are proven and running` | 4 | Replace with one sentence pointing to Pipeline.md Part IV readiness gate. |
| 290 | `Most builds already route entirely on P0 or P6` | 2 | Delete corpus-frequency claim; keep tie-breaker rule without measurement. |
| 308 | `that problem is genuinely rare` | 2 | State P5 scope as a rule; drop frequency justification. |
| 322 | `nobody proposed routing chess to P5` | 1 | Replace with flat SET rule; drop rejected-alternative narrative. |
| 336 | `Seven of Shooter's eight presets` | 3 | Correct to nine presets, six on `lane-network` (or drop counts). |
| 370 | `Two-genre prompts are common` | 2 | Keep worked examples; delete frequency claim. |
| 495 | `Stage B already asks…Strategy already had` | 1 | Describe `set-display`/`SET` operatively; drop pipeline-stage archaeology. |
| 501 | `no-genre.md has always asked` | 1 | Say axes match No Genre table; drop temporal wording. |
| 507 | `how the shapes above were coined` | 1 | Keep described-shape rule; delete catalogue-evolution provenance. |
| 535 | `largest hole in the system` | 1 | State why universal options exist; drop project-history framing. |
| 546 | `small minority of prompts…wrong far more often` | 2 | Rule: never auto-apply universal options; delete frequency stats. |
| 819 | `Build's original version demanded sealed` | 1 | Keep gate-not-enclosure rule; delete prior-docversion contrast. |
| 821 | `reference failure case (topdown_k)` | 2 | Keep P6 rationale; drop eval artifact name and failure provenance. |
| 874 | `bundle this doc already had` | 1 | List presets; drop self-history wording. |
| 919 | `Build's original version wrongly demanded` | 1 | Keep conditional-roads rule; delete version archaeology. |
| 986 | `had no preset at all…preset: null` | 3 | Update or delete — **Aim Trainer** preset now exists (line 974). |
| 1047 | `the old rule read that as no layout` | 1 | State Idle→SET rule; drop superseded-rule narrative. |
| 1145 | `Build's original version only described` | 1 | Keep region-vs-actor distinction; delete prior-version contrast. |
| 1195 | `Build's original version required team enclosures` | 1 | Keep dugout rule; delete prior-version contrast. |
| 1294 | `arguably layout…Kept here framed` | 1, 6 | Flat placement rule; drop scope-debate and keep-here rationale. |
| 1295 | `Kept separate here because a runner routes` | 1 | State runner as distinct genre operationally; drop editorial keep/separate. |
| 1346 | `Open question on hub portals…Worth confirming` | 6 | Pick P4 vs P0 rule or cross-ref Pipeline.md; remove open question. |
| 1357 | `meaningful share of prompts` | 2 | Delete — evaluation frequency data. |
| 1357 | `picked more often than most genre presets` | 2 | Delete — evaluation pick-rate data. |
| 1427 | `which is what the whole of Part II now assumes` | 1 | End on flat rule; drop temporal “now assumes” framing. |

The single worst problem is the **No Genre evaluation leakage at lines 1357–1358** (“meaningful share of prompts,” preset pick rates): it cites golden-set measurement that belongs only in `evaluation/`, and it weakens a normative doc with stats the reader cannot verify from Build.md itself. A close second is the **cluster of “Build’s original version” notes** (819, 919, 1145, 1195) — five instances of document archaeology that read like plan.md decision log, not system definition. Stale counts at **336** (Shooter presets) and **986** (Aim Trainer now has a preset) are the clearest self-contradictions against the file’s own tables.
