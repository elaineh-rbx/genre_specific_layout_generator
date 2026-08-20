# LayoutGen

LayoutGen turns a fixed Roblox scene brief into a layout-aware isometric/top-down image
pair and downstream segmentation artifacts.

The canonical architecture and current corpus are documented in
[`docs/layoutgen-pipeline-overview.md`](docs/layoutgen-pipeline-overview.md).

## Production pipeline

```text
Build Agent intake
  -> real Cursor agent reads the full layout skills
  -> oversized requests reduce to one buildable active zone
  -> prose layout decision with one enriched scene body
  -> one strict Gateway prose-to-JSON call
  -> deterministic normalisation and prompt assembly
  -> two GPT Image 2 calls
  -> image-to-layout segmentation
```

The Cursor agent decides. The Gateway only transcribes that decision into the strict
layout schema. Python owns validation, routing policy, render order, and prompt assembly.

After the Cursor agent returns prose, MapGen makes exactly:

- one text-model call;
- two image-model calls.

Evaluation checklist generation and image-to-layout segmentation have separate,
downstream call budgets.

## Key files

| Path | Purpose |
| --- | --- |
| `tools/agent_task.md` | Cursor-agent prose contract |
| `.cursor/skills/genre-choice/` | Genre, shape, option, and route decision workflow |
| `.cursor/skills/scope-reduce-default/SKILL.md` | No-question reduction to one buildable active zone |
| `.cursor/skills/layout-blob/SKILL.md` | Nine-section prose handoff |
| `results/routing/agent_blob/` | Self-contained prose decisions with enriched image-ready bodies |
| `tools/build_agent_arm.py` | One strict Gateway transcription per artifact |
| `layoutgen/model/blob.py` | Layout schema, strict transcription, and normalisation |
| `layoutgen/pipeline/mapper.py` | Deterministic spec-to-prompt mapping |
| `layoutgen/pipeline/golden.py` | Production `agent_gateway` render runner |
| `tools/run_i2l_segmentation.py` | Downstream image-to-layout batch |
| `tools/build_segmentation_manifest.py` | S3 corpus manifest |
| `tools/build_pipeline_viewer.py` | Per-scene production pipeline viewer |

`docs/LayoutGen - Build.md` is the source catalogue. `layoutgen/model/rules.py` parses it
at import, so the shared 46-shape and option model cannot drift from the document.

## Run the production flow

The workspace virtual environment must include system packages:

```bash
uv venv --seed --system-site-packages
```

Then:

```bash
# Cursor agents first write results/routing/agent_blob/P####.md.

# One provider-enforced JSON Schema call per prose artifact.
python tools/build_agent_arm.py

# Deterministic assembly plus two image calls.
python -m layoutgen.pipeline.golden

# Downstream segmentation and corpus manifest.
python tools/run_i2l_segmentation.py
python tools/build_segmentation_manifest.py

# Rebuild the current viewers.
python tools/build_pipeline_viewer.py
python tools/build_shifts_viewer.py
```

Useful focused forms:

```bash
python tools/build_agent_arm.py --only P0005 --workers 1
python -m layoutgen.pipeline.golden --only P0005 --no-checklists
```

## Strict transcription contract

`blob.decouple(prose)` sends `LAYOUT_SPEC_SCHEMA` through Roblox LLM Gateway with
`require_schema=True`.

- Provider-enforced structured output is required.
- A Gateway that cannot enforce the schema is a hard failure.
- The production call never falls back to unconstrained prose or custom JSON extraction.
- JSON transport decoding and deterministic `normalise()` still run locally.

Default text backend:

```text
provider: gateway
environment: production
model: gpt-5.5
```

The default Gateway path is unseeded. Override the model with
`LAYOUTGEN_GATEWAY_MODEL` when running comparisons or rolling back.

## Render orders

```text
std      text -> isometric -> top-down edit
p6       text -> top-down -> isometric edit
layout   deterministic plan -> top-down edit -> isometric edit
```

All orders use two image-model calls. `layout` additionally creates its initial blueprint
in deterministic code.

The mapper injects:

- the selected shared-catalogue shape;
- visible genre options;
- requested universal visible options;
- applicable non-default visual axes.

Layout-only requirements such as trigger volumes, spawn markers, checkpoints, pickups,
and emitters are withheld in `layout_placement` for downstream placement.

## Current corpus

The corrected production corpus contains 616 scenes.

```text
s3://3dfm-data/users/elaineh/layoutgen/results/scenes/agent_gateway_260813/
├── iso/
├── td/
├── plan/
├── seg/
├── i2l/
├── segmentation_manifest.jsonl
└── segmentation_manifest_summary.json
```

Verified segmentation totals:

- 616/616 scenes complete;
- 603 quality-gate passes;
- 13 best retained masks after the soft gate;
- 8,247 provenance artifacts.

The pipeline viewer is served at:

```text
https://8889--standard--elaineh-dev--elainehuang.devspaces.rbx.com/pipeline
```

It shows, per scene:

- raw author source and intake answers;
- Cursor-agent prose blob;
- its single enriched image-ready scene body;
- strict structured JSON;
- deterministic route/order and addendum;
- exact image prompts;
- rendered images and evaluation checklist.

## Results retained as evidence

Current production evidence lives in:

```text
results/routing/agent_input/
results/routing/agent_blob/
results/routing/agent_spec_gateway/
results/runs/agent_gateway.jsonl
results/runs/agent_gateway_segmentation_manifest.jsonl
results/runs/agent_gateway_segmentation_summary.json
results/eval/
```

Older routing and comparison records may remain under `results/` for provenance, but they
are not executable production entry points.

## Credentials

No credentials belong in the repository.

- Gateway: `LAYOUTGEN_GATEWAY_TOKEN`
- GPT Image 2: `GPT_IMAGE_2_API_KEY` or the configured local token cache
- AWS/S3: standard AWS credentials/profile resolution
