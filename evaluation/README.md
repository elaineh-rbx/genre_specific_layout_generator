# Evaluation

Everything produced by the golden-set evaluation of the LayoutGen intake skill
network. Kept separate from `docs/`, which holds the canonical build documents
the system actually runs on.

**Start here:** [`report/LayoutGen - Golden Set Evaluation.md`](report/LayoutGen%20-%20Golden%20Set%20Evaluation.md)

Row ids map straight to the source spreadsheet: **`P0087` is line 87.**

## Layout

```
evaluation/
  LANE-BRIEF.md          the standing brief every scoring worker was given
  report/                written findings
  data/                  inputs, raw records, and derived results
  tools/                 the harness and the analysis scripts
```

### report/

| File | What it is |
|---|---|
| `LayoutGen - Golden Set Evaluation.md` | The main report. Read this first. |
| `ask-audit.md` | Audit A — grades the 1,494 questions intake asks back. Adding one `goal` field takes clear-path rows from 37% to 77% |
| `ask-merge-layout.md` | 942 ask clusters merged to 70 layout concepts |
| `ask-merge-context.md` | 632 clusters merged to 71 context-file concepts |
| `ask-merge-systems.md` | 757 clusters merged to ~150 mechanics/constraint concepts |
| `family-sweep-findings.md` | Cross-row search for game families split across genres. Carries an appended correction — read that too. |

### data/

| Path | What it is |
|---|---|
| `layout gen prompt golden set  - build 600 (prod subgenre balanced).csv` | Source: 623 real user prompts with the spreadsheet's own genre labels |
| `golden set 600 - genre and coverage eval.csv` | The same sheet with 24 evaluation columns added |
| `aggregate.json` | All counts the report quotes |
| `records/batch-*.jsonl` | 628 raw scoring records, one per prompt |
| `records/adjudication-*.jsonl` | Sighted verdicts on the 89 genre disagreements |
| `records/late-batch-49-full.jsonl` | Held deliberately outside the record glob — see the report's limitations |
| `batches/` | The prompt batches as issued to workers |
| `ask-clusters*.json` | Mechanical clustering output feeding the three merges |

### tools/

Run everything from the repo root.

```bash
python evaluation/tools/eval_golden_set.py check     # validate all records
python evaluation/tools/eval_golden_set.py merge     # rebuild the CSV + aggregate.json
python evaluation/tools/test_eval_grade.py           # unit tests for the verdict rule
```

| Script | Purpose |
|---|---|
| `eval_golden_set.py` | The harness: `batch`, `check`, `calibrate`, `merge` |
| `test_eval_grade.py` | 15 unit tests pinning the agree/defensible/disagree rule |
| `eval_answer.py` | `losses`, `subgenre <name>`, `p5` — pulls the rows behind a claim |
| `eval_dimension.py` | Crosses the spreadsheet's 2D/3D column against our P5 routing |
| `eval_p5_rows.py` | Every row routed P5, with prompt and worker notes |
| `eval_shape_route.py` | How often a shape choice forced a pipeline route |
| `eval_subgenre_split.py` | Genre concentration per spreadsheet subgenre |
| `eval_cluster.py`, `eval_split_clusters.py` | Mechanical ask clustering, split by destination |
| `eval_verify_concepts.py`, `eval_verify_systems.py` | Independent re-derivation of merge claims |
| `eval_check_49.py`, `eval_split_49.py` | The batch-49 duplicate incident |
| `eval_questions.py` | What intake asks users back. `--pre` for the pre-forward-pass round trip, `--show <field>` for prompt-and-question pairs |
| `eval_ask_audit.py` | Grades those questions: does the answer have a home, was any gap left unasked, is the question closed or open-ended. `--pre`, `--landing <none\|partial>`, `--residual` |
| `eval_peek.py`, `eval_show.py`, `eval_families.py` | Ad-hoc inspection |

## Reading the numbers honestly

Two workers given the *same* prompt agreed on genre and shape but named only
about 30% of the same asks. **Every ask count is a floor, not a census.** The
report states this up front and it applies to all of it.

Three claims in earlier drafts did not survive independent re-derivation and are
corrected in place rather than deleted: the horror-escape family, the scope of
the player-identity hazard, and the entire P5 result.
