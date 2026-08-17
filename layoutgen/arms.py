"""What an arm is, which ones exist, and which sets of them get compared.

An *arm* is one way of turning a prompt into a scene. The point of the repo is that
there is more than one, and that they can be held against each other on identical
prompts - so an arm is described here as data rather than spelled out inside a judge,
a page and a card that each have their own idea of how many there are.

Adding an arm is one entry below plus its images under `results/scenes/<id>/`. Nothing
else counts arms: the judge asks about however many it is handed, the pages draw one
column per arm, and the card sizes its tiles to fit.

Two things an arm may have, and both are optional:

  a run file   the record of how its scenes were generated, which is also where its
               injected text and its routing come from
  asks         the layout features it demanded. An arm with none is a control - it
               can be scored, but only ever against what somebody else asked for.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from layoutgen import paths


@dataclass(frozen=True)
class Arm:
    id: str
    title: str          #: how pages introduce it
    short: str          #: three or four characters, for a tick column
    blurb: str          #: what it was given, in one sentence
    sub: str            #: the same thing in four words, for a heading
    accent: str         #: hex, so a page and a card tint it the same way
    run: str = ""       #: results/runs/<run>.jsonl, if it kept one
    asks: Callable[[dict], list[dict]] | None = None
    chips: Callable[[dict], list[str]] = field(default=lambda row: [])
    #: (what to call it, which run-row field holds it) for the prompts it sent
    sent: tuple[tuple[str, str], ...] = ()
    #: what decided this arm's requirements, for grouping them on a catalogue page
    group: Callable[[dict], str] = field(default=lambda row: "")

    @property
    def guided(self) -> bool:
        """Whether this arm contributed requirements of its own."""
        return self.asks is not None

    def row(self, scene: str, rows: dict[str, dict]) -> dict:
        return rows.get(self.id, {})

    def addendum(self, row: dict) -> str:
        """The text this arm added to the prompt, if any."""
        return (row or {}).get("addendum", "")


def _needs_asks(row: dict) -> list[dict]:
    """Yesterday's arm asked for its sub-genre's Hard Needs, plus any invariants."""
    out = [{"label": n.get("id", "hard need"), "text": n["visual"], "kind": "hard-need"}
           for n in row.get("needs", [])]
    out += [{"label": "invariant", "text": f["text"], "kind": "invariant"}
            for f in row.get("fragments", [])]
    return out


def _rules_asks(row: dict) -> list[dict]:
    """Today's arm asked for its shape, its drawn options, and any typed-in extra.

    Imported here rather than at module scope because the requirement text is derived
    from the parsed rules document, and that parse should not be forced on anything
    that only wants to know an arm's colour.
    """
    from layoutgen.model import rules as br

    g = br.GENRES.get(row.get("genre", ""))
    if g is None:
        return []
    out = []
    if (s := g.shape(row.get("shape", ""))) is not None:
        out.append({"label": s.label, "text": s.what, "kind": "shape"})
    for oid in row.get("options", []):
        if (o := g.option(oid)) is not None and o.drawn:
            out.append({"label": o.label, "text": br.visible_text(g.name, o),
                        "kind": o.goes_to})
    for e in row.get("extras", []):
        if e.get("goes_to") == "image":
            out.append({"label": "unlisted request", "text": e["text"], "kind": "extra"})
    return out


def _skill_asks(row: dict) -> list[dict]:
    """The skill's arm asked for the same kinds of thing, in its own words.

    The difference worth seeing is that last part. The router injects an option's
    document wording on every prompt that picks it; the skill rewrote each one for the
    scene in front of it, so `edits` is preferred over the generic text wherever it has
    something to say. A scene with no genre has axes where the others have a shape.
    """
    from layoutgen.model import rules as br

    g = br.genre(row.get("genre", ""))
    if g is None:
        return []
    edits = row.get("edits") or {}
    out = []
    if (s := g.shape(row.get("shape") or "")) is not None:
        out.append({"label": s.label, "text": s.what, "kind": "shape"})
    for line in br.axis_lines(g, row.get("axes") or {}):
        out.append({"label": "the space itself", "kind": "shape",
                    "text": line.split(" - ", 1)[-1]})
    for oid in row.get("options", []):
        if (o := g.option(oid)) is not None and o.drawn:
            out.append({"label": o.label, "kind": o.goes_to,
                        "text": edits.get(oid) or br.visible_text(g.name, o)})
    for e in row.get("extras", []):
        if e.get("goes_to") == "image":
            out.append({"label": "unlisted request", "text": e["text"], "kind": "extra"})
    return out


def _blob_spec(scene: str) -> dict:
    """The structured spec the blob arm was built from.

    Read from the routing file rather than the run row because the row stores option
    *ids* only, and the ids are the least of what this arm asked for: the wording is
    per-scene, and the zones, paths and props it invented have no counterpart in any
    other arm's row to be stored alongside.
    """
    import json

    path = paths.ROUTING / "blob" / f"{scene}.json"
    if not path.is_file():
        return {}
    d = json.loads(path.read_text(encoding="utf-8"))
    return d.get("spec") or {}


def _blob_asks(row: dict) -> list[dict]:
    """The blob arm asked for its shape and its drawn options, in the document's words.

    The same list, from the same tables, in the same wording as the router's arms - so a
    requirement is comparable across arms and the only thing that varies is which ones
    got picked. The spec's zones, paths and props are deliberately not here: they are
    recorded but no longer sent, so scoring the images against them would be marking an
    arm on text no image model ever read.
    """
    from layoutgen.model import rules as br

    spec = _blob_spec(row.get("scene", ""))
    if not spec:
        return []
    g = br.genre(spec.get("genre", ""))
    if g is None:
        return []
    out: list[dict] = []
    if (s := g.shape(spec.get("shape") or "")) is not None:
        out.append({"label": s.label, "text": s.what, "kind": "shape"})
    for o in spec.get("options") or []:
        opt = g.option(o.get("id", ""))
        if opt is not None and opt.drawn:
            out.append({"label": opt.label, "kind": opt.goes_to,
                        "text": br.visible_text(g.name, opt)})
    return out


def _author_asks(scene: str) -> list[dict]:
    """What the *author* asked for, according to nobody's arm.

    Every checklist in `results/eval` marks each feature as coming from the prompt or
    from the injection that was bolted onto it. Keeping only the prompt-origin features
    leaves a list written before any of these arms existed, each item carrying the
    author's own words as its evidence - which is the only checklist two arms can be
    held to without one of them having set the exam.
    """
    import json

    path = paths.EVAL / f"{scene}.json"
    if not path.is_file():
        return []
    out = []
    for f in json.loads(path.read_text(encoding="utf-8")).get("features", []):
        if f.get("origin") != "prompt":
            continue
        out.append({"label": f.get("name", "feature"),
                    "text": (f.get("notes") or f.get("name") or "").strip(),
                    "kind": "author", "quote": f.get("quote", "")})
    return out


def _needs_chips(row: dict) -> list[str]:
    return [x for x in [row.get("subgenre_id", "")] if x]


def _rules_chips(row: dict) -> list[str]:
    bits = [row.get("shape_label") or row.get("shape", "")]
    if (p := row.get("preset", "")) and p != "none":
        bits.insert(0, p)
    return [x for x in bits if x] + list(row.get("route", []))


def _skill_chips(row: dict) -> list[str]:
    """As the rules arm, plus a mark on the scenes it declined to call a game."""
    chips = _rules_chips(row)
    return (["no genre"] + chips) if row.get("genre") == "No Genre" else chips


def _blob_chips(row: dict) -> list[str]:
    """As the rules arm, plus which image this arm decided to draw first.

    Worth a chip of its own because it is the one pick no other arm makes deliberately:
    the others infer the order from whether some option happened to carry `P6`.
    """
    order = {"p6": "top-down first", "layout": "authored plan first",
             "std": "isometric first"}.get(row.get("order", ""), "")
    return _rules_chips(row) + [x for x in [order] if x]


ARMS: dict[str, Arm] = {
    "raw": Arm(
        id="raw", title="Raw prompt", short="raw", accent="#8b949e",
        blurb="The prompt as written, plus the shared style tail. Nothing added.",
        sub="no guidance at all",
    ),
    "needs": Arm(
        id="needs", title="Sub-genre Hard Needs", short="need", accent="#d29922",
        blurb="An older model: the prompt is classified into one of 44 sub-genres, "
              "and that sub-genre's Hard Needs are injected as demands.",
        sub="sub-genre Hard Needs",
        run="needs", asks=_needs_asks, chips=_needs_chips,
        sent=(("isometric", "guided_prompt"),),
        group=lambda row: row.get("subgenre_id") or row.get("genre", ""),
    ),
    "rules": Arm(
        id="rules", title="Build.md Part II", short="rule", accent="#58a6ff",
        blurb="One shape plus whichever options the router picked. Nothing is "
              "mandatory, so a short list is a legitimate answer.",
        sub="one shape plus its options",
        run="rules", asks=_rules_asks, chips=_rules_chips,
        sent=(("isometric", "iso_prompt"), ("top-down", "td_prompt")),
        group=lambda row: (row.get("preset", "") if row.get("preset", "none") != "none"
                           else row.get("genre", "")),
    ),
    "skill": Arm(
        id="skill", title="genre-choice skill", short="skil", accent="#3fb950",
        blurb="The same menu, chosen by an agent following the skill one scene at a "
              "time - which can also decline to name a genre, and rewrites every "
              "option for the scene in front of it.",
        sub="an agent following the skill",
        run="skill", asks=_skill_asks, chips=_skill_chips,
        sent=(("isometric", "iso_prompt"), ("top-down", "td_prompt")),
        group=lambda row: (row.get("preset", "") if row.get("preset", "none") != "none"
                           else row.get("genre", "")),
    ),
    "answered": Arm(
        id="answered", title="router plus intake answers", short="ansr", accent="#a371f7",
        blurb="The upstream genre classification, with the router's intake questions "
              "answered per scene by an agent that had read the prompt.",
        sub="the router, told the answers",
        run="answered", asks=_skill_asks, chips=_skill_chips,
        sent=(("isometric", "iso_prompt"), ("top-down", "td_prompt")),
        group=lambda row: (row.get("preset", "") if row.get("preset", "none") != "none"
                           else row.get("genre", "")),
    ),
    "blob": Arm(
        id="blob", title="skills, blob, spec", short="blob", accent="#f78166",
        blurb="Four stages: an agent uprezzes the prompt into a scene, a second writes "
              "a prose blob about its shape, the gateway decouples that into a spec, and "
              "the image prompts are composed from the spec in code. The author's words "
              "are never sent.",
        sub="a spec, composed in code",
        run="blob", asks=_blob_asks, chips=_blob_chips,
        sent=(("isometric", "iso_prompt"), ("top-down", "td_prompt")),
        group=lambda row: (row.get("preset", "") if row.get("preset", "none") != "none"
                           else row.get("genre", "")),
    ),
}


@dataclass(frozen=True)
class Comparison:
    """One set of arms, judged together on one shared list of requirements."""

    id: str
    title: str
    blurb: str
    arms: tuple[str, ...]
    page: str
    #: Where the checklist comes from, if not from the arms themselves. Given a scene,
    #: returns the requirements to judge it on. See `requirements` for why.
    basis: Callable[[str], list[dict]] | None = None

    def __iter__(self):
        return (ARMS[a] for a in self.arms)

    @property
    def asking(self) -> tuple[Arm, ...]:
        """The arms that asked for something, in order. These define the checklist."""
        return tuple(ARMS[a] for a in self.arms if ARMS[a].guided)

    @property
    def runs(self) -> tuple[Arm, ...]:
        return tuple(ARMS[a] for a in self.arms if ARMS[a].run)

    def scores(self, stage: str):
        return paths.SCORES / f"{self.id}_{stage}.jsonl"

    def requirements(self, rows: dict[str, dict], scene: str = "") -> list[dict]:
        """What to judge this comparison's images on, for one scene.

        Two arms can be compared on the union of what they each demanded, which is the
        default below, or on a checklist neither of them wrote, which is `basis`. The
        difference matters when the arms are not asking for comparable amounts. The
        union rewards volume: an arm that demands twenty features and delivers fifteen
        outscores one that demands five and delivers all five, on a list three quarters
        of which it wrote itself. That is fine for arms picking from the same menu and
        useless for an arm that composes its own scene, so such a comparison supplies a
        `basis` instead and both sides answer to the same outside list.

        A live prompt from the playground has no scene id and so no stored checklist;
        it falls back to the union, which is the only thing available in that case.
        """
        if self.basis is not None and scene:
            return [{**item, "source": "author"} for item in self.basis(scene)]

        out: list[dict] = []
        seen: set[str] = set()
        for arm in self.asking:
            for item in arm.asks(rows.get(arm.id, {})):
                key = " ".join(item["text"].split()).lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                out.append({**item, "text": item["text"].strip(), "source": arm.id})
        return out


COMPARISONS: dict[str, Comparison] = {
    c.id: c for c in (
        Comparison(
            id="all_arms", page="all_arms.html",
            title="Every arm on the same scene",
            blurb="Each arm on the union of what all the guided arms asked for, so a "
                  "row read across shows whether an arm delivered a feature it never "
                  "requested. The union is not evenly owned - an arm that asks for "
                  "more of it will lead on the total while losing on someone else's "
                  "requirements - so the split by who asked is the honest column.",
            arms=("raw", "needs", "rules", "skill"),
        ),
        Comparison(
            id="rules_vs_raw", page="rules_compare.html",
            title="Build.md Part II vs the raw prompt",
            blurb="Today's arm against the unguided baseline, on the features today's "
                  "arm asked for. Identical wrapper and style tail on both sides.",
            arms=("raw", "rules"),
        ),
        Comparison(
            id="skill_vs_rules", page="skill_compare.html",
            title="Who chose: an agent following the skill, or the router",
            blurb="The same menu and the same generator on both sides, so the only "
                  "difference is who read the prompt. Judged on the union of what "
                  "each asked for, which is where they part company: the skill asks "
                  "for more, words it for the scene, and on fifteen prompts declines "
                  "to call the thing a game at all.",
            arms=("rules", "skill"),
        ),
        Comparison(
            id="blob_vs_answered", page="blob_compare.html",
            title="The four-stage pipeline vs the router it replaces",
            blurb="Judged on the features the *author* asked for, taken from the eval "
                  "checklists and filtered to the ones traceable to the prompt itself. "
                  "Neither arm wrote this list, which is the point: the new pipeline "
                  "asks for several times more than the router does, so any checklist "
                  "built from the arms' own demands would be won by whoever demanded "
                  "most. It is also the harder test for the new arm, which never sends "
                  "the author's words at all - anything its spec dropped cannot appear.",
            arms=("answered", "blob"), basis=_author_asks,
        ),
        Comparison(
            id="blob_own_asks", page="blob_asks.html",
            title="Did each arm deliver what it asked for",
            blurb="The diagnostic beside the headline, on the union of both arms' own "
                  "demands. Not a fair race - the new arm names every zone, route and "
                  "prop and so writes most of the list - but it answers a different "
                  "question: when this pipeline specifies a space in detail, does the "
                  "image model build it, or does the detail get ignored?",
            arms=("answered", "blob"),
        ),
    )
}


def load_runs() -> dict[str, dict[str, dict]]:
    """Every arm's run file, keyed by arm and then by scene."""
    import json

    out: dict[str, dict[str, dict]] = {}
    for arm in ARMS.values():
        if not arm.run:
            continue
        path = paths.RUNS / f"{arm.run}.jsonl"
        out[arm.id] = ({json.loads(x)["scene"]: json.loads(x)
                        for x in path.open() if x.strip()} if path.is_file() else {})
    return out


def rows_for(scene: str, runs: dict[str, dict[str, dict]]) -> dict[str, dict]:
    """Each arm's row for one scene, as `requirements` and the pages want it."""
    return {arm: by_scene.get(scene, {}) for arm, by_scene in runs.items()}
