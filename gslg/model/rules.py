"""Parse `docs/build.md` Part II into the routing model the rest of the repo uses.

This is the model the pipeline runs on today, and it replaced a sub-genre model in
which every sub-genre carried mandatory Hard Needs. Part II is a *menu*:

    Shape      exactly one per game, mutually exclusive, and almost always the
               pipeline-routing decision (a flat arena is P0, a multi-level one P2)
    Options    additive on top of the shape, combined freely, nothing mandatory
    Presets    one shape plus a few option IDs, modelled on a real game - this is
               what stands in for what earlier drafts called sub-genres

The single most important field for us is `Goes to`. Pipeline step 4 recovers
geometry from the isometric render, so anything invisible - a trigger volume, a
spawn marker, a pickup - cannot be recovered and must never reach the image model.
Only `image`, and the visible half of `both`, is injectable.

    from gslg.model.rules import GENRES, render
    g = GENRES["Racing"]
    print(render(g.name, g.shape("route-circuit"), ["spawn-grid", "barrier-guardrail"]))
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from gslg.paths import BUILD_DOC as DOC

_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITAL = re.compile(r"\*(.+?)\*")
_CODE = re.compile(r"`([^`]*)`")
_TYPED = re.compile(r"^(?P<type>[A-Za-z]+)\s*\((?P<flavor>.+)\)$")


def _clean(s: str) -> str:
    """Markdown cell to plain text, keeping the words and dropping the syntax."""
    s = _LINK.sub(r"\1", s)
    s = s.replace("\\", "").strip()
    s = _BOLD.sub(r"\1", s)
    s = _CODE.sub(r"\1", s)
    return s.strip()


def _row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _table(lines: list[str], i: int) -> tuple[list[list[str]], int]:
    """Read the markdown table starting at or after ``i``; return rows and next index."""
    while i < len(lines) and not lines[i].lstrip().startswith("|"):
        if lines[i].startswith("#"):
            return [], i
        i += 1
    rows = []
    header = True
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        cells = _row(lines[i])
        if set("".join(cells)) <= set(": -"):
            i += 1
            continue
        if header:
            header = False
        else:
            rows.append(cells)
        i += 1
    return rows, i


def _split_name(raw: str) -> tuple[str, str, str]:
    """``Cover (Line-of-Sight Pillars)`` -> (full, type, flavor)."""
    full = _clean(raw)
    m = _TYPED.match(full)
    return (full, m.group("type"), m.group("flavor")) if m else (full, "", full)


@dataclass
class Shape:
    id: str
    name: str
    type: str
    flavor: str
    what: str
    pipeline: str

    @property
    def label(self) -> str:
        return self.flavor or self.name


@dataclass
class Option:
    id: str
    name: str
    type: str
    flavor: str
    what: str
    core: bool
    goes_to: str
    pipeline: str

    @property
    def label(self) -> str:
        return self.flavor or self.name

    @property
    def drawn(self) -> bool:
        """Whether any part of this reaches the image model."""
        return self.goes_to in ("image", "both")


@dataclass
class Preset:
    name: str
    modelled_on: str
    shape: str
    options: list[str]


@dataclass
class Genre:
    num: int
    name: str
    tagline: str
    route: str
    shapes: list[Shape] = field(default_factory=list)
    options: list[Option] = field(default_factory=list)
    presets: list[Preset] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def shape(self, sid: str) -> Shape | None:
        return next((s for s in self.shapes if s.id == sid), None)

    def option(self, oid: str) -> Option | None:
        return next((o for o in self.options if o.id == oid), None)

    def preset(self, name: str) -> Preset | None:
        return next((p for p in self.presets if p.name == name), None)


def _parse() -> tuple[dict[str, Genre], list[tuple[str, str]]]:
    lines = DOC.read_text().splitlines()

    # The Genre List gives the one-line description for each of the fifteen.
    descs: list[tuple[str, str]] = []
    try:
        gl = next(i for i, x in enumerate(lines) if x.strip() == "## **Genre List**")
        for text in lines[gl + 1: gl + 40]:
            m = re.match(r"^\d+\.\s+\*\*(.+?)\*\*\s*[—-]\s*(.+?)\s*$", text.strip())
            if m:
                descs.append((_clean(m.group(1)), _clean(m.group(2)).rstrip(".")))
    except StopIteration:
        pass

    heads = [(i, m) for i, x in enumerate(lines)
             if (m := re.match(r"^## \*\*(\d+)\\?\.\s+(.+?)\*\*\s*$", x))]
    genres: dict[str, Genre] = {}
    for n, (start, m) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        body = lines[start:end]
        name = _clean(m.group(2))
        g = Genre(num=int(m.group(1)), name=name, tagline="", route="")

        i = 1
        while i < len(body):
            line = body[i].strip()
            if not g.tagline and line.startswith("*") and not line.startswith("**"):
                g.tagline = _clean(line).rstrip(".")
            if line.startswith("**Genre route:"):
                g.route = _clean(line)
            if line.startswith("**Shape"):
                rows, i = _table(body, i + 1)
                for r in rows:
                    if len(r) < 4:
                        continue
                    full, typ, flav = _split_name(r[1])
                    g.shapes.append(Shape(id=_clean(r[0]), name=full, type=typ,
                                          flavor=flav, what=_clean(r[2]),
                                          pipeline=_clean(r[3])))
                continue
            if line.startswith("**Options**"):
                rows, i = _table(body, i + 1)
                for r in rows:
                    if len(r) < 6:
                        continue
                    full, typ, flav = _split_name(r[1])
                    g.options.append(Option(id=_clean(r[0]), name=full, type=typ,
                                            flavor=flav, what=_clean(r[2]),
                                            core="●" in r[3], goes_to=_clean(r[4]),
                                            pipeline=_clean(r[5])))
                continue
            if line.startswith("**Presets**"):
                rows, i = _table(body, i + 1)
                for r in rows:
                    if len(r) < 4:
                        continue
                    g.presets.append(Preset(
                        name=_clean(r[0]), modelled_on=_clean(r[1]),
                        shape=_clean(r[2]),
                        options=[x for x in (_clean(o) for o in r[3].split(",")) if x]))
                continue
            if line.startswith("**Genre notes**"):
                for nl in body[i + 1:]:
                    # The last genre is followed by Themes and the Appendix; stop at
                    # the section break rather than absorbing them.
                    if nl.startswith("#") or nl.strip() == "---":
                        break
                    if nl.strip().startswith("* "):
                        g.notes.append(_clean(nl.strip()[2:]))
                break
            i += 1
        genres[name] = g

    return genres, descs


GENRES, GENRE_DESCS = _parse()

#: Every option ID that appears in more than one genre, per the shared registry.
SHARED_IDS: dict[str, list[str]] = {}
for _g in GENRES.values():
    for _o in _g.options:
        SHARED_IDS.setdefault(_o.id, []).append(_g.name)
SHARED_IDS = {k: v for k, v in SHARED_IDS.items() if len(v) > 1}


# ------------------------------------------------------------------ injection

#: The visible half of each `both` option, keyed by (genre, option id).
#:
#: Build.md marks an option `both` when it has a visible part and an invisible part,
#: and says only the visible part is injected. It marks *which* options are `both`
#: but not where the split falls, so these clauses are ours: the document's own
#: visible nouns kept, and the detection/trigger/scoring language dropped, because
#: asking an image model for "an invisible cylinder" or "a detection perimeter"
#: produces nothing a segmenter can recover. The invisible half is placed against the
#: layout afterwards, exactly as the `layout` options are.
#:
#: Keyed by genre because a shared ID is worded per genre - `teleporter-link` appears
#: in six genres and means something different in each.
VISIBLE_PART: dict[tuple[str, str], str] = {
    ("Action", "spawn-protected"):
        "Start areas set back, screened by walls or terrain, or raised above the "
        "arena floor.",
    ("Adventure", "tracker-quest"):
        "A physical notice board or standing pillar, sited where players pass it.",
    ("Adventure", "teleporter-link"):
        "Paired matching markers or platforms at known locations, each clearly "
        "identifiable as a travel point.",
    ("Obby & Platformer", "checkpoint-respawn"):
        "Flat enclosed pads set at intervals along the course, wide enough to stand "
        "on safely.",
    ("Obby & Platformer", "winner-zone"):
        "A distinct reward area at the end of the course holding the payoff items.",
    ("Obby & Platformer", "teleporter-link"):
        "Marked pads that link the stages to each other and back to the hub.",
    ("Party & Casual", "tracker-leaderboard"):
        "A prominent flat structural wall in the lobby, sized and framed to host a "
        "large display.",
    ("Party & Casual", "teleporter-link"):
        "Clearly marked pads or gateways at the lobby edge leading to the match area.",
    ("Puzzle", "trigger-solve"):
        "A physical receptacle for a key item - a shaped indentation, a pedestal, or "
        "a socket in a wall or table.",
    ("Puzzle", "button-solve"):
        "Levers, keypads, and pressure plates mounted where players can reach them.",
    ("RPG", "collectible-nodes"):
        "Repeating alcoves and clearings reserved for mining seams, woodcutting "
        "stands, and herb patches.",
    ("RPG", "teleporter-link"):
        "Standardized stone platforms outside the major landmarks.",
    ("Roleplay & Avatar Sim", "teleporter-link"):
        "Marked transport points at the edges of the distant districts.",
    ("Shooter", "spawn-teambase"):
        "Balanced bases at opposite ends of the map, each enclosed so it is not "
        "overlooked from open ground.",
    ("Shooter", "spawn-protected"):
        "Geometry directly around a spawn that blocks the sightlines into it.",
    ("Shooter", "capture-zone"):
        "A marked stand or platform at the objective, distinct from the ground "
        "around it.",
    ("Shooter", "control-zone"):
        "A marked raised area - the King-of-the-Hill hill - visibly distinct from "
        "its surroundings.",
    ("Simulation", "trigger-task"):
        "A built station in the job loop - a pickup bay, a delivery dock, a patient "
        "bed, a planting plot.",
    ("Strategy", "tracker-core"):
        "A large structure at the end of the track, built as the visual focus of "
        "the defence.",
    ("Survival", "gate-escape"):
        "Large structural doors or escape hatches set into the outer boundary.",
    ("Sports", "trigger-bounds"):
        "Painted or built boundary lines marking the edge of the active playing "
        "area - touchlines, foul lines, baselines.",
    ("Sports", "startpoint-play"):
        "Marked static positions where play begins - pitcher's mound and home plate, "
        "centre circle, serve box.",
    ("Sports", "trigger-scoring"):
        "The built scoring targets themselves - the goal mouth, the hoop and "
        "backboard, home plate.",
    ("Racing", "startpoint-line"):
        "The marked start position - a painted line or a lane slot on the track.",
    ("Racing", "trigger-finish"):
        "The built finish at the exact end of the course - a touch-pad wall, a "
        "finish line across the track, or a finish gate.",
    ("Racing", "spawn-grid"):
        "A wide launch front of evenly spaced slots - blocks in a pool, lanes on a "
        "track, grid spots on a circuit - laid out side by side.",
    ("Entertainment (Showcase & Hub)", "spawn-first-reveal"):
        "The spawn area placed and oriented to face a composed view, never backstage "
        "geometry, seams, or the underside of the build.",
    ("Entertainment (Showcase & Hub)", "teleporter-link"):
        "Physical, clearly identifiable portal structures at logical endpoints of "
        "the layout.",
}


def visible_text(genre_name: str, option: Option) -> str:
    """What actually gets injected for an option: the visible part only."""
    return VISIBLE_PART.get((genre_name, option.id), option.what)


HEADER = (
    "LAYOUT FEATURES for this {genre} map. Build these as the actual structure of "
    "the space rather than as set dressing, keep them visually distinct from one "
    "another, and keep the whole layout legible in one view."
)
SHAPE_LINE = "SHAPE OF THE SPACE - {label}: {what}"


def render(genre_name: str, shape: Shape | None,
           bullets: list[tuple[str, str]]) -> str:
    """Assemble the addendum from an explicit shape and feature list.

    Picking nothing is a legitimate outcome and returns an empty string - the user
    gets a simple map, which Build.md is explicit is not a failure.
    """
    if shape is None and not bullets:
        return ""
    parts = [HEADER.format(genre=genre_name)]
    if shape is not None:
        parts.append(SHAPE_LINE.format(label=shape.label, what=shape.what))
    if bullets:
        parts.append("INCLUDE:\n" + "\n".join(
            f"- {lab}: {txt}" if lab else f"- {txt}" for lab, txt in bullets))
    return "\n\n".join(parts)


def injection(genre: Genre, shape: Shape | None, option_ids: list[str]) -> str:
    """The Stage A addendum for one shape and a set of picked options.

    Only what a segmenter could recover from a render is injected: options marked
    ``layout`` are dropped, and ``both`` contributes its visible part.
    """
    picks = [o for oid in option_ids if (o := genre.option(oid)) and o.drawn]
    return render(genre.name, shape,
                  [(o.label, visible_text(genre.name, o)) for o in picks])


def dropped(genre: Genre, option_ids: list[str]) -> list[Option]:
    """Picked options that never reach the image model, so the UI can say so."""
    return [o for oid in option_ids if (o := genre.option(oid)) and not o.drawn]


def genre_list_text() -> str:
    """The Genre List, for a router that has to choose among all fifteen."""
    return "\n".join(f"{g.num:2d}. {g.name} - {dict(GENRE_DESCS).get(g.name, g.tagline)}"
                     for g in GENRES.values())


def menu_text(g: Genre) -> str:
    """One genre's full menu as compact text, for prompting a model.

    Presets carry their `Modelled on` games, which Build.md states are internal
    reference for the LLM - they ground a preset in something concrete - and are
    never shown to a user.
    """
    out = [f"GENRE: {g.name} - {g.tagline}"]
    if g.route:
        out.append(g.route)
    out.append("\nSHAPES (pick exactly one)")
    for s in g.shapes:
        out.append(f"  {s.id} | {s.label} | {s.what}"
                   + (f" | pipeline {s.pipeline}" if s.pipeline else ""))
    out.append("\nOPTIONS (pick any number, or none)")
    for o in g.options:
        out.append(f"  {o.id} | {o.label} | {o.what} | {o.goes_to}"
                   + (" | core" if o.core else "")
                   + (f" | pipeline {o.pipeline}" if o.pipeline else ""))
    out.append("\nPRESETS (a shape plus a few options; 'modelled on' is your internal "
               "reference and is never shown to the user)")
    for p in g.presets:
        out.append(f"  {p.name} | modelled on {p.modelled_on} | shape {p.shape} | "
                   f"options {', '.join(p.options)}")
    return "\n".join(out)


def preset_menu_text(g: Genre) -> str:
    """The presets spelled out, for a model choosing one of them outright.

    Each preset is written as the configuration it actually is - the shape's own
    wording, then every option's - so the choice is made on the structure rather than
    on how evocative the preset's name happens to be.
    """
    out = [f"GENRE: {g.name} - {g.tagline}"]
    if g.route:
        out.append(g.route)
    out.append("\nPRESETS ('modelled on' is your internal reference, never shown to "
               "the user)")
    for p in g.presets:
        s = g.shape(p.shape)
        out.append(f"\n  {p.name} | modelled on {p.modelled_on}")
        if s is not None:
            out.append(f"      shape: {s.label} - {s.what}"
                       + (f" [pipeline {s.pipeline}]" if s.pipeline else ""))
        for oid in p.options:
            if (o := g.option(oid)) is not None:
                out.append(f"      option {o.id}: {o.label} - {o.what}"
                           + (f" [pipeline {o.pipeline}]" if o.pipeline else ""))
        if not p.options:
            out.append("      options: none")
    out.append("\n  none | no preset fits; the configuration is built option by option")
    return "\n".join(out)


def route_of(genre: Genre, shape: Shape | None, option_ids: list[str]) -> list[str]:
    """The pipeline modifiers this combination forces, in document order."""
    tags: list[str] = []
    for text in ([genre.route, shape.pipeline if shape else ""]
                 + [o.pipeline for oid in option_ids if (o := genre.option(oid))]):
        for tag in re.findall(r"\bP\d\b|\btiered\b|\bCHECK\b", text or ""):
            if tag not in tags:
                tags.append(tag)
    return tags or ["P0"]


if __name__ == "__main__":
    print(f"{len(GENRES)} genres, {len(GENRE_DESCS)} descriptions")
    for g in GENRES.values():
        drawn = sum(1 for o in g.options if o.drawn)
        print(f"  {g.num:2d}. {g.name:<26} {len(g.shapes)} shapes  "
              f"{len(g.options):2d} options ({drawn} drawn)  "
              f"{len(g.presets)} presets  {len(g.notes)} notes"
              + (f"  route={g.route.split(':')[1].strip().rstrip('.')}" if g.route else ""))
    print(f"\nshared option ids: {len(SHARED_IDS)}")
