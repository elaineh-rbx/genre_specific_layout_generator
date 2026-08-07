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
BUILD_DOC = DOCS / "build.md"                       # the layout rules, Part II
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

#: The three arms every comparison is between. `raw` is the prompt with nothing added,
#: `needs` is the older per-sub-genre Hard Needs, `rules` is Build.md Part II. These
#: names are also the keys in every scores file, so they are not free to change.
ARMS = ("raw", "needs", "rules")
STAGES = ("iso", "td")


def scene(arm: str, stage: str, sid: str) -> pathlib.Path:
    """One generated image. Every arm uses the same filename, unlike the runs these
    were imported from, where one arm prefixed the scene id and another did not."""
    return SCENES / arm / stage / f"{sid}.png"


def plan(sid: str) -> pathlib.Path:
    """The blueprint a layout-first scene was carved from, where there was one."""
    return SCENES / "rules" / "plan" / f"{sid}.png"


def thumb(arm: str, stage: str, sid: str) -> pathlib.Path:
    return THUMBS / f"{stage}_{arm}_{sid}.jpg"


def url(path: pathlib.Path) -> str:
    """A path under results/, as the browser sees it."""
    return "/results/" + path.relative_to(RESULTS).as_posix()
