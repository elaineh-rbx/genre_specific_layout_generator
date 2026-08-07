# genre_specific_layout_generator

Turn a game prompt into a scene whose **layout** is right, not just its art.

The Python package is `layoutgen`, after the source document it is built from
(`LayoutGen - Build.md`).

Ask an image model for "a racing game map" and you get something that looks like one:
tarmac, kerbs, grandstands, and a road that forks, dead-ends, or quietly stops being a
loop. The picture is fine and the map is unplayable. This repo puts a layout model
between the prompt and the image, so what gets drawn is a space someone could actually
play in.

## The idea

Layout knowledge is genre-specific. `docs/build.md` is the source document, and its
Part II is a menu rather than a specification:

| | |
|---|---|
| **Shape** | Exactly one per game, mutually exclusive. Usually the decision that routes the pipeline: a flat arena and a stacked interior need different treatment. |
| **Option** | Additive on top of the shape, combined freely. Nothing is mandatory. |
| **Preset** | A shape plus a few option IDs, modelled on a real game - a starting point, not a constraint. |

`layoutgen/model/rules.py` parses that document at import, so the model in code cannot
drift from the model in prose. A router (`layoutgen/model/router.py`) reads a prompt
and picks a genre, a shape and whatever options the prompt gives a reason to want - and
picking almost nothing is a legitimate answer.

Each option carries a **Goes to** field, and it is enforced. Geometry a segmenter
could recover (`image`) is injected into the prompt; an invisible trigger volume or
spawn marker (`layout`) never is, because a later stage recovers geometry from the
render and cannot recover something that was never visible. The filter lives on the
server, so what the UI previews is what the model is sent.

## Three ways to draw the same prompt

The pipeline picks an order from what the routing implies:

```
std      text -> isometric -> top-down          the default
p6       text -> plan -> isometric              when the topology is the game
layout   blueprint -> top-down -> isometric     when we can author the topology outright
```

The `layout` order is the strongest guarantee available. A maze carved by
`layoutgen/layouts/maze.py` is a perfect maze - exactly one route between any two cells, so
it is solvable by construction rather than by luck. A circuit from
`layoutgen/layouts/track.py` is one continuous closed loop with no spurs and no ambiguous
self-crossings. The image model is handed that plan and asked to dress it, not to
invent it.

## What is in `results/`

75 prompts, each generated three ways, judged blind by a vision model against the
union of what both guided arms asked for. The three images are shuffled per scene and
labelled A/B/C, so position cannot correlate with arm.

| Arm | What it was given |
|---|---|
| `raw` | the prompt, plus the shared style tail. Nothing else. |
| `needs` | an older model: per-sub-genre Hard Needs, injected as mandatory demands. |
| `rules` | this repo: one shape plus the options the router picked, nothing mandatory. |

An arm is an entry in `layoutgen/arms.py` - a name, a colour, where its run lives and
what it demands - and a *comparison* is a set of arms judged together. Nothing counts to
three: the judge asks about however many images it is handed, the pages draw a column
per arm, and the card sizes its tiles to fit. Adding a fourth arm is one entry plus its
images under `results/scenes/<id>/`.

These results were generated before this repo existed, in a scratch tree, and were
brought across rather than rerun - the images cost about 900 model calls and none of
the arms changed. Two things were renamed on the way, which is worth knowing if you
compare against anything older: the arms `original` and `guided` became `raw` and
`needs`, and every arm's files became `{scene}.png` where one of them used to prefix
`scene_`. The judge output was later rewritten from one set of keys per comparison to
the generic `present`/`met` form, without rejudging, since both say the same thing.

Against the raw baseline on the features it asked for, the rules arm lands 82% of them
on the isometric and 83% on the top-down, where the baseline manages 63% of the same
list. Judged against the union of both guided arms' asks, the picture is more
interesting: the Hard Needs arm scores higher overall (78% against 60% on the
isometric), which is what a mandatory checklist buys - and what it costs is that every
scene in a sub-genre gets the same demands whether or not its prompt called for them.

## Layout

```
docs/build.md               the layout rules; rules.py parses this, nothing hardcodes it
docs/subgenre-catalogue.html the 44 sub-genres of the older Hard Needs model

layoutgen/paths.py               where everything lives
layoutgen/arms.py                what an arm is, which exist, and which sets get compared

layoutgen/model/rules.py         Build.md Part II -> genres, shapes, options, presets
layoutgen/model/router.py        prompt -> genre, shape, options (two constrained LLM calls)
layoutgen/model/hardneeds/       the older per-sub-genre model, kept for the comparison

layoutgen/backends/images.py     the image backend: generation and reference edits
layoutgen/backends/llm.py        the text/vision model behind one JSON-schema call

layoutgen/pipeline/prompts.py    every wrapper sent to the image model, in one file
layoutgen/pipeline/spec.py       a playground spec -> the prompts it produces
layoutgen/pipeline/carve.py      authored layouts, and the overlays that check them
layoutgen/pipeline/run.py        one spec all the way to images, in any of the three orders
layoutgen/pipeline/golden.py     the same, batched over the 75 golden prompts
layoutgen/layouts/               authored topology: mazes, racing circuits

layoutgen/evaluate/judge.py      one blinded judge, any number of arms
layoutgen/evaluate/score.py      run a comparison over the golden set
layoutgen/evaluate/card.py       one sheet per prompt: the arms and the checklist

layoutgen/web/server.py          the HTTP layer, and the page/results host
layoutgen/web/playground.html    the playground itself
layoutgen/web/build.py           rebuild every page from results/
layoutgen/web/pages/             the static pages under site/

scripts/serve.sh            keep 8887 and 8888 up, with a supervisor each - the one
                            thing here that is not Python. Anything importable lives
                            in the package and runs with -m.

layoutgen/assets.py         finds a scene's images, on this disk or in the bucket

.cursor/skills/genre-choice/  the agent-facing version of the same model: classify a
                            prompt, offer the genre's options as a menu, emit the picks
                            split into an image stream and a layout stream. Copied from
                            mpalleschi/3D-LayoutBuild-Rules @ 61d65ed; it covers the
                            same 15 genres this repo parses, so the two agree on what
                            exists, but it is a copy and can drift

results/                    the evidence. The runs, routing picks and judge scores are
                            committed; the 700 MB of renders are not - they live in
                            S3 and are fetched on demand
site/                       the built pages
run/                        anything a live server writes, plus the image cache
```

## Running it

```bash
pip install -e .                     # pillow, numpy, httpx, matplotlib
scripts/serve.sh                     # 8887 the playground, 8888 the viewers
scripts/serve.sh status
```

Both ports run the same program and answer every path identically; they differ only in
what `/` opens on. The server also serves `results/` and the pages in `site/`, so
nothing needs a second origin.

Regenerating from scratch, in order:

```bash
python -m layoutgen.model.router --golden  # route all 75 prompts
python -m layoutgen.pipeline.golden   # generate the rules arm
python -m layoutgen.evaluate.score         # judge every comparison, blind, both stages
python -m layoutgen.web.build         # rebuild the pages
```

A single card, without a server:

```bash
python -m layoutgen.evaluate.card --scene 0025
```

## Where the images live

The renders are about 700 MB and cost roughly 900 model calls to make, so they are
kept in S3 rather than in git:

```
s3://3dfm-data/users/elaineh/layoutgen/results/{scenes,thumbs}/
```

The bucket blocks public access, so the pages do not address it directly. They ask
this server for `/results/...` as they always have, and the server fetches anything
the clone does not carry, caching it under `run/cache/`. A page URL is therefore never
a presigned link with an expiry date, and a fresh clone works as soon as the machine
running the server can read the bucket.

Point it somewhere else with `LAYOUTGEN_S3` and `LAYOUTGEN_S3_PROFILE`, or set
`LAYOUTGEN_S3_OFF=1` to refuse the network and serve only what is on disk.

## Credentials

No credential is stored in this repo, and none should ever be. One Azure key covers
both the image deployment and the text/vision model; it is read at run time from
`~/.cache/i2l/gpt-image-2-token`, or from `GPT_IMAGE_2_API_KEY` and
`LAYOUTGEN_LLM_KEY`. AWS reads `~/.aws/credentials` in the usual way. Endpoints and deployment names are environment-overridable; see the
constants at the top of `layoutgen/backends/images.py` and `layoutgen/backends/llm.py`.

The judge deployment rejects `temperature` and `top_p` and accepts `seed`, so
determinism is best-effort: a repeat that differs is possible rather than a bug.
