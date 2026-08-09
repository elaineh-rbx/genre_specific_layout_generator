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
}


@dataclass(frozen=True)
class Comparison:
    """One set of arms, judged together on one shared list of requirements."""

    id: str
    title: str
    blurb: str
    arms: tuple[str, ...]
    page: str

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

    def requirements(self, rows: dict[str, dict]) -> list[dict]:
        """The union of what every asking arm wanted, each item tagged with who asked.

        The union rather than each arm's own list, because scoring an arm only on its
        own asks tells you it followed instructions, not whether the instructions were
        worth following. Deduplicated on the text, so two arms wording the same demand
        differently do not double-count - the first to ask keeps it.
        """
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
            id="three_way", page="three_way.html",
            title="Raw vs Hard Needs vs Build.md Part II",
            blurb="Every arm on the union of what both guided arms asked for, so a "
                  "row read across shows whether an arm delivered a feature it never "
                  "requested.",
            arms=("raw", "needs", "rules"),
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
