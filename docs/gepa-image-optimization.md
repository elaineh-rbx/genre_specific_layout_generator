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

## Exact prompt change in the all-75 winner

The winning candidate is:

```text
run/gepa/gemini_gepa_all75_v1_260816/best_candidate.json
```

GEPA did **not** rewrite the canonical scene description, selected shape, options,
counts, or render order. It changed only the global execution-policy string appended
for each image stage.

Put differently, the final prompt changed like this:

```text
BEFORE OPTIMIZATION
  [unchanged canonical scene prompt]
  + [seed execution policy]

AFTER OPTIMIZATION
  [the exact same canonical scene prompt]
  + [winning execution policy]
```

The short, shareable diff of the execution policy is:

```diff
 ISOMETRIC
- polished Roblox-like image
- camera 30–35 degrees away from vertical nadir
- preserve reference geometry only when a reference is attached
+ highly detailed, polished, Game-Ready image
+ classic 45-degree isometric camera
+ preserve precise grid positions from an "immutable top-down reference"
+ add a continuous perimeter wall, fence, or cliff
+ add richer textures, bright lighting, and crisp shadows
+ generate terrain, water, and flora to fill empty space
+ minimize background void and fill the whole 1:1 canvas

 TOP-DOWN
- preserve geometry and use a 90-degree orthographic camera
- do not redesign, regularize, mirror, add, or omit
+ force walls to have zero visible height
+ retain detailed material textures and semantic lighting
+ fill the square canvas and position features relative to center and boundaries
+ do not rotate, flip, mirror, simplify, or redesign

 PLAN
  no change
```

Those `+` lines are the augmentation GEPA learned. The strongest likely cause of the
visual change was not hidden elsewhere in the pipeline: it was the combination of
**45-degree camera + richer materials/lighting + forced perimeter + filling empty space
with generated terrain, water, and flora**.

Two learned ISO lines are unsafe or internally inconsistent:

- `Generate complex terrain features ... to fill all empty space` can invent content
  absent from the canonical scene.
- `the associated immutable top-down reference` is unconditional, but standard-order
  scenes generate isometric first and have no top-down reference attached at that stage.

Every candidate prompt had this outer structure:

```text
CANONICAL SCENE CONTRACT — every requirement in this block is mandatory:
<the unchanged per-scene prompt>
END CANONICAL SCENE CONTRACT.

MODEL-SPECIFIC EXECUTION POLICY FOR <STAGE>:
<the GEPA candidate string below>

FINAL INVARIANT: the execution policy may improve how the model follows the contract,
but it may not remove, replace, merge, or contradict any canonical scene requirement.
```

### Isometric policy

Seed policy:

```text
Return one polished Roblox-like 3D environment image, not prose. This stage must use a steep elevated oblique camera whose optical axis is 30–35 degrees away from vertical nadir. Show unmistakable front and side faces, vertical height, depth, and cast shadows while keeping the map footprint axis-aligned. When a reference image is attached, preserve its exact geometry and use it only as the footprint authority; replace its camera rather than copying it. Silently verify every named structure, count, route, opening, and distinctive obstacle before returning the image. Render only the environment: no labels, captions, swatches, legend, UI, border, letterbox, or watermark.
```

Winning policy:

```text
Return one highly detailed, polished 3D environment image, rendered in a strict 3/4 isometric perspective, not prose. The render must maintain the exact same relative scale and precise grid-based spatial positions of all items seen in the associated immutable top-down reference, which serves as the geometric authority. Visualize the scene from a classic 45-degree isometric camera angle that simultaneously reveals the top, precise front face, and precise side face of every asset (e.g., specific roof shapes, building facades, wall textures, and tree types) while preserving their accurate spatial alignment and complex counts. A continuous perimeter structure (like a wall, fence, or cliff edge, as defined in the layout) must frame the entire scene. Emphasize a clean, stylized, Game-Ready aesthetic with richer, complex asset textures and bright, vibrant lighting, moving away from flat visuals. Generate complex terrain features (e.g., varying elevations, water bodies, and detailed flora) to fill all empty space between structures. The composition should minimize large areas of background void and utilize the entire 1:1 canvas. Generate distinct, crisp cast shadows. Visually verify every named asset type, structure, count, and opening. Render only the environment; include zero labels, captions, legends, swatches, UI elements, or letterboxing.
```

The material visual changes came primarily from these new instructions:

- camera changed from **30–35 degrees away from nadir** to a **classic 45-degree
  isometric angle**;
- add a **continuous perimeter structure** around the scene;
- use **richer textures, bright lighting, and crisp shadows**;
- generate **terrain, water, and flora to fill empty space**;
- minimize background void and fill the full square canvas.

The last two are not purely rendering guidance. They can invent scene content, so they
are the most likely source of improvements in visual density **and** regressions where
Gemini added terrain, water, vegetation, or a perimeter that the scene never requested.

### Top-down policy

Seed policy:

```text
Return one square environment image, not prose. Perform a camera conversion of the attached scene while preserving its exact geometry, content, object count, route, openings, and adjacency. Use an exactly 90-degree straight-down orthographic nadir camera with zero perspective, horizon, side faces, or visible wall height. Do not redesign, regularize, mirror, add, or omit scene features. Render only the physical game environment: no labels, captions, swatches, legend, UI, border, letterbox, or watermark.
```

Winning policy:

```text
Return one square environment image, not prose. Execute a camera conversion to a strict 90-degree top-down (nadir) orthographic projection. Do not apply perspective or any side-angle view; ensure all walls are vertical lines with zero visible height. Render the scene with the semantic lighting and detailed material textures (e.g., weathered wood, growing crops, dark swamp water, metallic symbols) required by the contract. The composition must be a square map filling the canvas, with all scene features accurately placed relative to the center and boundaries. Preserve the exact layout, geometry, asset count, routes, openings, and adjacency. Do not rotate, flip, mirror, simplify, or redesign the scene. The output is a physical map: no text, labels, UI, captions, swatches, legend, border, letterbox, or watermarks.
```

The top-down change mainly strengthened the nadir-camera test, material detail, canvas
fill, relative placement, and prohibitions against rotation, flipping, and
simplification.

### Plan policy

The winning plan policy was byte-for-byte unchanged from the seed:

```text
Return one square physical game-environment image, not prose or an infographic. Build every named structure and connection with exact counts and an unbroken playable route. Use an exactly 90-degree straight-down orthographic nadir camera with zero perspective, horizon, side faces, or visible wall height. Make topology and openings unambiguous without written annotations. Do not merge or omit requirements. No labels, captions, swatches, legend, UI, border, letterbox, or watermark.
```

Therefore, any change in authored-plan scenes came from the modified **isometric**
second-stage policy, not from a changed plan-generation policy.

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
