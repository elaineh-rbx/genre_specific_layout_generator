# GEPA optimization for Gemini image prompts

This experiment evolves three global Gemini instruction strings (`iso`, `topdown`, and
`plan`). The canonical strict spec, scene prompt, deterministic layout, and render order
are fixed. GPT Image 2 renders are frozen targets used only by the evaluator; they are
never attached to a Gemini generation request.

## Objective

Each scene produces a Gemini isometric and top-down image. Both are compared with the
corresponding GPT Image 2 targets:

- 55% global perceptual similarity
- 30% aligned-patch spatial similarity
- 15% grayscale structural similarity (SSIM)
- 50/50 average of the isometric and top-down stage scores

Raw pixel equality is deliberately excluded because independent image samples can be
equally correct without matching pixel-for-pixel. GEPA also receives a four-panel visual
comparison as actionable feedback through Gateway Gemini by default. Azure remains an
explicit optional reflection provider.

The default `--encoder auto` uses DINOv2 when PyTorch is healthy and otherwise falls
back to a deterministic, torch-free multiscale colour/composition/edge encoder. Use
`--encoder dino` to require DINOv2 and fail instead of falling back, or
`--encoder pyramid` to select the local fallback explicitly.

The default stress split is:

- Train: `0001,0011,0014,0022,0036,0053`
- Validation: `0002,0025,0030,0041`

## Preflight and run

The preflight downloads/checks the 20 frozen target images and makes no model calls:

```bash
uv sync
layoutgen-optimize-gemini --dry-run
```

Set a current Gateway token for Gemini rendering and reflection:

```bash
export LAYOUTGEN_GATEWAY_TOKEN=...
```

To use Azure reflection explicitly, pass
`--reflection-provider azure --reflection-deployment gpt-5.2` and configure
`LAYOUTGEN_LLM_KEY`.

Score the seed prompt once before spending an optimization budget:

```bash
layoutgen-optimize-gemini --run-name gemini_gepa_baseline --baseline-only
```

Run a small optimization:

```bash
layoutgen-optimize-gemini \
  --run-name gemini_gepa_stress10_v1 \
  --max-metric-calls 40 \
  --workers 2
```

Run the full 75-scene experiment with a deterministic 60/15 split, convergence
stopping, and a final score/render pass over all 75 scenes:

```bash
layoutgen-optimize-gemini \
  --run-name gemini_gepa_all75_v1 \
  --all-75 \
  --max-metric-calls 400 \
  --patience 12 \
  --workers 4
```

One metric call evaluates a full scene and normally makes two Gemini image calls. A
40-call budget therefore means approximately 80 generated images. When DINO is selected,
the first scorer run downloads `facebook/dinov2-small`; override it with `--dino-model`
if needed. Candidate renders and GEPA evaluations are content-addressed and disk-cached
under `run/gepa/<run-name>/`.

Outputs:

- `manifest.json`: immutable experiment inputs and target provenance
- `baseline.json`: seed scores when `--baseline-only` is used
- `best_candidate.json`: three optimized stage instructions
- `result.json`: candidate lineage and validation scores
- `final_all75_scores.json`: winning-candidate scores for all 75 scenes
- `renders/`: candidate outputs, exact prompts, and visual comparisons

## Use the winning candidate

The optimized profile is opt-in and does not replace production defaults:

```bash
export LAYOUTGEN_IMAGE_BACKEND=llm-gateway
export LAYOUTGEN_IMAGE_MODEL=gemini-3.1-flash-image
export LAYOUTGEN_IMAGE_PROMPT_PROFILE=gemini-gepa
export LAYOUTGEN_GEPA_CANDIDATE="$PWD/run/gepa/gemini_gepa_stress10_v1/best_candidate.json"

python -m layoutgen.pipeline.golden \
  --arm agent_gateway \
  --output-arm gemini_gepa_candidate \
  --only 0001,0002 \
  --workers 2 \
  --no-checklists
```

Do not promote a candidate from training scores alone. Compare its held-out validation
score and inspect the rendered pairs before rerendering all 75 scenes.
