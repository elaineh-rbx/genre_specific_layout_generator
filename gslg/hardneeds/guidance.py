"""Resolve a (genre, sub-genre) pair to the guidance injected at Stage A.

This is yesterday's model, kept because the comparison depends on it: the middle arm
of every three-way judgement is a scene generated under these per-sub-genre Hard
Needs, which were mandatory in a way nothing in Part II is.

Sub-genres are the 44 VARIATIONS[] in `docs/subgenre-catalogue.html`, parsed at import
so the list cannot drift. Each resolves to:

  needs        the genre's Build.md Hard Needs, with any override that names the
               same style applied as replacements
  fragments    prompt text contributed by non-default layout attribute tags
  structural   attribute deviations that change the run rather than the prompt
  addendum     the assembled text appended to the scene prompt at Stage A
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from gslg.hardneeds import needs as hn
from gslg.hardneeds import subgenres as sd
from gslg.paths import SUBGENRE_DOC as VIEWER

_VAR_RE = re.compile(
    r'\{\s*genre:"(?P<genre>[^"]+)",\s*variation:(?P<q>["\'])(?P<name>.*?)(?P=q),\s*'
    r'modifiers:\[(?P<mods>[^\]]*)\](?P<rest>[^}]*)\}'
)

DEFAULTS = {"enclosure": "exterior", "verticality": "single", "zones": "single",
            "structure": "dressed", "playspace": "grounded"}


def parse_variations() -> list[dict]:
    """Parse VARIATIONS[] out of pipeline-viewer.html."""
    text = VIEWER.read_text(encoding="utf-8")
    out = []
    for m in _VAR_RE.finditer(text):
        rest = m.group("rest")
        mods = [x.strip().strip("\"'") for x in m.group("mods").split(",") if x.strip()]
        brk = re.search(r'brk:(["\'])(.*?)\1', rest, re.S)
        ps = re.search(r'playspace:"(\w+)"', rest)
        out.append({
            "genre": m.group("genre"),
            "name": m.group("name"),
            "modifiers": mods,
            "roofless": "roofless:true" in rest.replace(" ", ""),
            "tiered": "tiered:true" in rest.replace(" ", ""),
            "playspace": ps.group(1) if ps else None,
            "brk": brk.group(2) if brk else "",
        })
    return out


def attrs_of(v: dict) -> dict[str, str]:
    """Mirrors attrsFromVariation() in pipeline-viewer.html."""
    return {
        "enclosure": "interior-only" if v["roofless"]
                     else "transition" if "P3" in v["modifiers"] else "exterior",
        "verticality": "tiered" if v["tiered"]
                       else "stacked" if ("P2" in v["modifiers"]
                                          and v["playspace"] != "occluding") else "single",
        "zones": "multi-zone" if "P4" in v["modifiers"] else "single",
        "structure": "must-be-valid" if "P6" in v["modifiers"] else "dressed",
        "playspace": "volumetric (open)" if v["playspace"] == "open"
                     else "volumetric (self-occluding)" if v["playspace"] == "occluding"
                     else "grounded",
    }


VARIATIONS: list[dict] = parse_variations()
BY_KEY: dict[tuple[str, str], dict] = {(v["genre"], v["name"]): v for v in VARIATIONS}

def _clean(s: str) -> str:
    """Double quotes are rejected inside strict structured-output enums, and one
    variation name ('zero dead-end') carries them."""
    return s.replace('"', "'")


#: Stable "Genre :: Variation" ids, usable directly as a JSON-schema enum.
IDS: list[str] = [_clean(f"{v['genre']} :: {v['name']}") for v in VARIATIONS]
_BY_ID: dict[str, tuple[str, str]] = {
    _clean(f"{v['genre']} :: {v['name']}"): (v["genre"], v["name"]) for v in VARIATIONS
}


def make_id(genre: str, variation: str) -> str:
    return _clean(f"{genre} :: {variation}")


def split_id(sid: str) -> tuple[str, str]:
    """The real (genre, variation) pair for an id the model returned."""
    if sid in _BY_ID:
        return _BY_ID[sid]
    raise KeyError(f"not one of the {len(IDS)} sub-genre ids: {sid!r}")


@dataclass
class Guidance:
    genre: str
    variation: str
    description: str
    brk: str
    route: list[str]
    attrs: dict[str, str]
    nondefault: list[str]
    needs: list[hn.HardNeed]
    deltas: list[hn.Delta] = field(default_factory=list)
    implied: str | None = None
    implied_why: str = ""
    fragments: list[dict] = field(default_factory=list)
    structural: list[dict] = field(default_factory=list)
    addendum: str = ""
    base_needs: list[hn.HardNeed] = field(default_factory=list)

    @property
    def changes_prompt(self) -> bool:
        return bool(self.implied or self.fragments)


def resolve(genre: str, variation: str, *, blueprint: bool = True) -> Guidance:
    """The guidance for one sub-genre. Raises KeyError if it is not one of the 44.

    `blueprint=False` swaps any fragment that points at a procedurally authored
    blueprint for wording that states the same invariant in text, for runs that
    generate Stage A straight from the prompt with nothing attached.
    """
    v = BY_KEY[(genre, variation)]
    a = attrs_of(v)
    base = list(hn.HARD_NEEDS.get(genre, []))

    frags, structs = [], []
    for k, val in a.items():
        if val == DEFAULTS[k]:
            continue
        eff = sd.ATTRIBUTE_EFFECT.get((k, val))
        if not eff:
            continue
        text = eff["text"] if blueprint else eff.get("text_noref", eff["text"])
        row = {"axis": sd.AXIS_LABELS[k], "value": sd.VALUE_LABELS[(k, val)],
               "text": text, "why": eff["why"]}
        (frags if eff["kind"] == "prompt" else structs).append(row)

    needs, deltas, implied, why = list(base), [], None, ""
    link = sd.IMPLIED_OVERRIDE.get((genre, variation))
    if link:
        implied, why = link
        spec = next(o for o in hn.overrides_for(genre) if o.name == implied)
        needs, deltas = hn._apply(list(base), spec)

    add = hn.render_addendum(needs, genre).strip() if needs else ""
    if frags and add:
        add += "\n" + "\n".join(f["text"] for f in frags)

    return Guidance(
        genre=genre, variation=variation,
        description=sd.DESCRIPTIONS.get((genre, variation), v["brk"]),
        brk=v["brk"],
        route=v["modifiers"] or (["P0 + tiered flag"] if v["tiered"] else ["P0"]),
        attrs=a,
        nondefault=[f"{k}: {val}" for k, val in a.items() if val != DEFAULTS[k]],
        needs=needs, deltas=deltas, implied=implied, implied_why=why,
        fragments=frags, structural=structs, addendum=add, base_needs=base,
    )


def catalog_text() -> str:
    """The 44 sub-genres as a prompt-ready catalog for the classifier."""
    lines: list[str] = []
    for gname, gdesc in GENRE_DESCS:
        subs = [v for v in VARIATIONS if v["genre"] == gname]
        if not subs:
            continue
        lines.append(f"\n## {gname} — {gdesc}")
        for v in subs:
            g = resolve(gname, v["name"])
            tags = f"  [tags: {', '.join(g.nondefault)}]" if g.nondefault else ""
            lines.append(f"  - {make_id(gname, v['name'])}{tags}\n      {g.description}")
    return "\n".join(lines)


# Genre one-liners, used only to orient the classifier.
GENRE_DESCS: list[tuple[str, str]] = [
    ("Action", "combat and battlegrounds, fast physical challenges"),
    ("Adventure", "exploration, scavenger hunts, narrative quests"),
    ("Entertainment", "showcases and hubs, built to be looked at or routed through"),
    ("Obby & Platformer", "obstacle courses and skill-based jumping"),
    ("Party & Casual", "round-based social minigames, trivia, tag, hide-and-seek"),
    ("Puzzle", "logic, match-and-merge, escape rooms"),
    ("RPG", "character progression, stats, combat loops, economy hubs"),
    ("Roleplay & Avatar Sim", "town-and-life sim, pets, avatar customisation"),
    ("Shooter", "team deathmatch, battle royale, PvE shooters"),
    ("Simulation", "tycoons, pet collection, vehicle driving, idle clickers"),
    ("Strategy", "tower defense, RTS, board and card games"),
    ("Survival", "1-vs-all, disaster survival, mascot horror"),
    ("Sports", "stadium sports — soccer, baseball, football, hockey"),
    ("Racing", "racing a finite track or lap count"),
    ("Infinite Runner", "procedural auto-runners, automatic forward motion"),
]
