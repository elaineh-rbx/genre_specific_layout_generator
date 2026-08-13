"""Where everything lives, in one place.

Three roots, because they have three different lifetimes: `docs/` is the input the
model is built from, `results/` is evidence worth keeping and committing, and `run/`
is scratch the server rewrites constantly. The web server maps them to three URL
prefixes, so a page can link to any of them without knowing where the repo sits.
"""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

DOCS = ROOT / "docs"

#: The two source documents, kept under the names they carry in the repo they are
#: written in, so that the references they make to each other resolve here too.
BUILD_DOC = DOCS / "LayoutGen - Build.md"           # the layout rules, Part II
PIPELINE_DOC = DOCS / "LayoutGen - Pipeline.md"     # the companion, not read yet
SHAPE_MIGRATION = DOCS / "shape-migration.json"     # old shape id -> its catalogue row
SUBGENRE_DOC = DOCS / "subgenre-catalogue.html"     # the 44 sub-genres, for Hard Needs

SITE = ROOT / "site"                                # the built viewer pages
RESULTS = ROOT / "results"
RUN = ROOT / "run"                                  # anything a live server writes
OUT = RUN / "out"
LOGS = RUN / "logs"

PROMPTS = RESULTS / "prompts" / "golden_set.jsonl"
ROUTING = RESULTS / "routing"                       # what each router chose per scene
RUNS = RESULTS / "runs"                             # what each arm generated
SCORES = RESULTS / "scores"                         # what the judges found
SCENES = RESULTS / "scenes"                         # the images themselves
THUMBS = RESULTS / "thumbs"

#: Per-scene checklists of the layout features a prompt asked for, each traced back to
#: the words it came from and marked as the author's own or an arm's injection. One file
#: per scene and shared by every arm, so two arms are compared on a list neither wrote.
#: Written by `pipeline.golden` at the end of a render, and by `tools/extract_checklist.py`
#: for scenes generated before that was true.
EVAL = RESULTS / "eval"

#: The two stages every arm produces. Which arms exist is `layoutgen.arms`, not here: an
#: arm is a thing with a name, a colour and a set of demands, and this module only
#: knows where files sit.
STAGES = ("iso", "td")


def scene(arm: str, stage: str, sid: str) -> pathlib.Path:
    """One generated image. Every arm uses the same filename, unlike the runs these
    were imported from, where one arm prefixed the scene id and another did not."""
    return SCENES / arm / stage / f"{sid}.png"


def plan(sid: str, arm: str = "rules") -> pathlib.Path:
    """The blueprint a layout-first scene was carved from, where there was one.

    Per arm, because which scenes get one is a consequence of the picks: two arms
    reading the same prompt can disagree about whether the topology is the game.
    """
    return SCENES / arm / "plan" / f"{sid}.png"


def thumb(arm: str, stage: str, sid: str) -> pathlib.Path:
    return THUMBS / f"{stage}_{arm}_{sid}.jpg"


def url(path: pathlib.Path) -> str:
    """A path under results/, as the browser sees it."""
    return "/results/" + path.relative_to(RESULTS).as_posix()
