"""Parse `docs/LayoutGen - Build.md` Part II into the routing model the repo uses.

This is the model the pipeline runs on today, and it replaced a sub-genre model in
which every sub-genre carried mandatory Hard Needs. Part II is a *menu*:

    Shape      exactly one per game, mutually exclusive, and almost always the
               pipeline-routing decision (a flat arena is P0, a multi-level one P2)
    Options    additive on top of the shape, combined freely, nothing mandatory
    Presets    one shape plus a few option IDs, modelled on a real game - this is
               what stands in for what earlier drafts called sub-genres

Shapes live in **one shared catalogue of 45**, and every one is reachable from every
genre; `SHAPES` holds it and is the only place a shape's route is read from. A genre owns
two things about a shape and not the shape itself: a `typical` shortlist naming a default,
which is presentation rather than restriction, and its own wording for rows it words
differently - `range-directed` is a firing line in Shooter and a bowling lane in Sports.
`Genre.shapes` is therefore the whole catalogue wearing that genre's words.

When nothing in the catalogue fits, a build may carry no shape at all and answer the five
routing axes directly - the document's *described shape*. That is the same mechanism
`No Genre` uses, which is why `Genre.axis` falls back to the axis table No Genre holds.

Options use the same shared-catalogue rule as shapes: a genre's table is its shortlist
and its wording, not a fence. `OPTION_CATALOG` holds one structural row per ID so an
option requested outside its usual genre still survives normalization and routing. The
genre's own row always wins when present. Six options live in a universal table and are
merged into every genre; they carry `universal` and are never `core`.

A sixteenth destination has no genre at all. A prompt describing a place rather than a
game - a lobby, a swamp, a farm scene - routes to `No Genre`, which the document calls
"a legitimate outcome, not a failure". It has options and presets like any genre, but no
shape: with no genre prior to infer from, the five routing axes are asked directly, each
with a default that costs nothing. `NO_GENRE` carries it, and `route_of` takes those axes
where it would otherwise take a shape.

The single most important field for us is `Goes to`. Pipeline step 4 recovers
geometry from the isometric render, so anything invisible - a trigger volume, a
spawn marker, a pickup - cannot be recovered and must never reach the image model.
Only `image`, and the visible half of `both`, is injectable.

    from layoutgen.model.rules import GENRES, render
    g = GENRES["Racing"]
    print(render(g.name, g.shape("route-circuit"), ["spawn-grid", "barrier-guardrail"]))
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace

from layoutgen.paths import BUILD_DOC as DOC
from layoutgen.paths import SHAPE_MIGRATION as MIGRATION_DOC

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
    s = _ITAL.sub(r"\1", s)
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
    #: From the Universal Options table rather than this genre's own. Never `core`,
    #: so it stays out of the tune menu - the document is explicit that these are a
    #: landing place for something the user asked for, never a default.
    universal: bool = False

    @property
    def label(self) -> str:
        return self.flavor or self.name

    @property
    def drawn(self) -> bool:
        """Whether any part of this reaches the image model."""
        return self.goes_to in ("image", "both")


@dataclass
class Axis:
    """One of the five routing questions asked when there is no genre to infer from.

    An axis is not a shape. A shape is chosen once from a table and usually decides the
    route on its own; an axis is a question with a default answer, and *only the
    non-default answer costs anything*. So a build that leaves all five alone is a
    complete answer that routes `P0`, which the document says is right for most place
    prompts.
    """

    id: str
    name: str
    what: str
    pipeline: str
    default: str
    #: Every value the document offers, mapped to its own wording. The default's
    #: wording is empty - the document gives it no clause, because it is the absence
    #: of a choice rather than one.
    clauses: dict[str, str] = field(default_factory=dict)
    #: Value -> the pipeline code it forces. Defaults never appear here.
    routes: dict[str, str] = field(default_factory=dict)

    @property
    def key(self) -> str:
        """``axis-enclosure`` -> ``enclosure``, which is how a block names it."""
        return self.id[5:] if self.id.startswith("axis-") else self.id


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
    #: Every shape in the catalogue, reworded where this genre words one its own way.
    #: All 45 are here because the document says every one is reachable from every
    #: genre; what a genre owns is the wording and the shortlist, not the set.
    shapes: list[Shape] = field(default_factory=list)
    #: The handful the genre publishes, in the document's order, first one the default.
    #: Presentation rather than restriction - "a shared catalogue nobody reaches past
    #: the first five closes nothing" - so nothing may reject a shape for being absent.
    typical: list[str] = field(default_factory=list)
    options: list[Option] = field(default_factory=list)
    presets: list[Preset] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    #: Only `No Genre` has these, and it has them instead of shapes.
    axes: list[Axis] = field(default_factory=list)
    #: Catalogue id -> this genre's own (name, type, flavor, what). Filled while
    #: parsing and spent building `shapes`; kept afterwards so the difference between
    #: an inherited wording and an owned one stays visible.
    wording: dict[str, tuple[str, str, str, str]] = field(default_factory=dict)

    @property
    def default_shape(self) -> str:
        """The shape the genre marks `(default)`, or its first typical one."""
        return self.typical[0] if self.typical else ""

    def shape(self, sid: str) -> Shape | None:
        return next((s for s in self.shapes if s.id == sid), None)

    def axis(self, key: str) -> Axis | None:
        """By either spelling: the document's ``axis-enclosure`` or a block's
        ``enclosure``.

        The five axes are not genre-specific - "every 3D game has a value on all five" -
        and only `No Genre` carries the table, because that is where the document keeps
        "the copy these are checked against". Any genre may still need them: a described
        shape answers the axes directly when nothing in the catalogue fits, and without
        this fallback such a build would lose both its route and its addendum wording.
        """
        here = next((a for a in self.axes if key in (a.id, a.key)), None)
        if here is not None or self.name == NO_GENRE_NAME:
            return here
        return next((a for a in NO_GENRE.axes if key in (a.id, a.key)), None)

    def option(self, oid: str) -> Option | None:
        own = next((o for o in self.options if o.id == oid), None)
        if own is not None:
            return own
        # Build.md now gives options the same reachability rule as shapes. The module
        # catalogue is populated after parsing; method lookup happens only afterwards.
        return OPTION_CATALOG.get(oid)

    def preset(self, name: str) -> Preset | None:
        return next((p for p in self.presets if p.name == name), None)


def _catalog(lines: list[str]) -> dict[str, Shape]:
    """The Shape Catalog - every shape in the system, and the only place a route lives.

    Shapes used to be filed per genre, and a genre could only pick from its own five or
    six. They are now one shared table that every genre reaches into, which is a change
    of kind and not of degree: `interior-single` was previously unreachable from any
    genre whose shapes all assumed outdoors, so a prompt wanting one large interior got
    the nearest wrong answer instead. What a genre still owns is the wording and a
    shortlist, both handled in `_fill`.

    The route is deliberately read here and nowhere else. A genre's own wording table
    has no Pipeline column, so there is no second copy to disagree with this one.
    """
    try:
        i = next(n for n, x in enumerate(lines)
                 if x.strip() == "## **Shape Catalog**")
    except StopIteration:
        return {}
    rows, _ = _table(lines, i + 1)
    out: dict[str, Shape] = {}
    for r in rows:
        if len(r) < 4 or not (sid := _clean(r[0])):
            continue
        full, typ, flav = _split_name(r[1])
        out[sid] = Shape(id=sid, name=full, type=typ, flavor=flav,
                         what=_clean(r[2]), pipeline=_clean(r[3]))
    return out


def _universal(lines: list[str]) -> list[Option]:
    """The Universal Options table, which sits outside the numbered genres.

    Six features that belong to no genre in particular because they belong to all of
    them - who inhabits the space, water, terrain relief. They are a separate table
    because filing them per genre would restate the same row seventy-eight times.
    """
    try:
        i = next(n for n, x in enumerate(lines)
                 if x.strip() == "## **Universal Options**")
    except StopIteration:
        return []
    rows, _ = _table(lines, i + 1)
    out = []
    for r in rows:
        if len(r) < 6:
            continue
        full, typ, flav = _split_name(r[1])
        out.append(Option(id=_clean(r[0]), name=full, type=typ, flavor=flav,
                          what=_clean(r[2]), core="●" in r[3], goes_to=_clean(r[4]),
                          pipeline=_clean(r[5]), universal=True))
    return out


#: ``exterior`` (default), or ``interior-only, play happens entirely inside...``.
_AXIS_VALUE = re.compile(r"^`([^`]+)`\s*(\(default\))?\s*(?:,\s*(.*))?$", re.S)
#: ``P3` for `transition` only`` - a code that applies to one named value.
_AXIS_FOR = re.compile(r"`([^`]+)`\s+for\s+`([^`]+)`")


def _axes(rows: list[list[str]]) -> list[Axis]:
    """The No Genre shape table, which asks five questions instead of offering shapes.

    Both halves have to be read off the raw cells rather than the cleaned ones, because
    the values are marked by their backticks and that is the only thing distinguishing
    them from the prose describing them.
    """
    out: list[Axis] = []
    for r in rows:
        if len(r) < 4 or not _clean(r[0]).startswith("axis-"):
            continue
        clauses: dict[str, str] = {}
        default = ""
        for part in r[2].split("·"):
            m = _AXIS_VALUE.match(part.strip().rstrip("."))
            if m is None:
                continue
            clauses[m.group(1)] = _clean(m.group(3) or "")
            if m.group(2):
                default = m.group(1)

        # A cost is either attached to a named value, or - where the axis has only one
        # non-default value - stated bare, with the value left implied.
        routes = {v: c for c, v in _AXIS_FOR.findall(r[3])}
        if not routes and (codes := _CODE.findall(r[3])):
            routes = {v: codes[0] for v in clauses if v != default}

        out.append(Axis(id=_clean(r[0]), name=_clean(r[1]), what=_clean(r[2]),
                        pipeline=_clean(r[3]), default=default,
                        clauses=clauses, routes=routes))
    return out


def _fill(g: Genre, body: list[str]) -> None:
    """Read one genre's tables and notes out of its section of the document."""
    i = 1
    while i < len(body):
        line = body[i].strip()
        if not g.tagline and line.startswith("*") and not line.startswith("**"):
            g.tagline = _clean(line).rstrip(".")
        if line.startswith("**Genre route:"):
            g.route = _clean(line)
        # The shortlist the genre publishes. It is a line rather than a table, and the
        # first entry carries `(default)`. Reading it is not the same as reading a shape
        # table: the shapes themselves come from the catalogue, and this only says which
        # of them this genre puts on screen first.
        if line.startswith("**Typical shapes"):
            g.typical = _CODE.findall(line)
            if (m := re.search(r"`([\w-]+)`\s*\*?\(default\)", line)) and g.typical:
                g.typical.remove(m.group(1))
                g.typical.insert(0, m.group(1))
            i += 1
            continue
        # Ten genres reword some catalogue rows for themselves - `range-directed` is a
        # firing line in Shooter and a bowling lane in Sports. Three columns, and no
        # Pipeline column on purpose: the route lives in the catalogue and only there.
        if line.startswith("This genre words these"):
            rows, i = _table(body, i + 1)
            for r in rows:
                if len(r) < 3:
                    continue
                full, typ, flav = _split_name(r[1])
                g.wording[_clean(r[0])] = (full, typ, flav, _clean(r[2]))
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


def _no_genre(lines: list[str]) -> Genre:
    """The `No Genre` section, which has the shape of a genre and no shapes.

    Its shape table is really the five routing axes, so it is re-read as those and the
    shape list left empty - there is no shape to pick, and code that asks for one
    should get nothing rather than an axis wearing a shape's name.
    """
    g = Genre(num=0, name=NO_GENRE_NAME, tagline="", route="")
    try:
        start = next(i for i, x in enumerate(lines)
                     if re.match(r"^## \*\*No Genre\*\*\s*$", x))
    except StopIteration:
        return g
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith("## ")), len(lines))
    body = lines[start:end]

    _fill(g, body)
    j = next((n for n, x in enumerate(body) if x.strip().startswith("**Shape")), -1)
    if j >= 0:
        rows, _ = _table(body, j + 1)
        g.axes = _axes(rows)
    g.shapes = []
    return g


def _parse() -> tuple[dict[str, Genre], list[tuple[str, str]], list[Option], Genre,
                      dict[str, Shape]]:
    lines = DOC.read_text().splitlines()
    catalog = _catalog(lines)

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
        _fill(g, body)
        # Every catalogue row, in catalogue order, wearing this genre's words where it
        # has any. Materialised per genre rather than shared so that `g.shape(id).what`
        # is the sentence that reaches the image model for *this* genre without any
        # caller having to know a wording table exists.
        g.shapes = [
            Shape(id=s.id, name=w[0], type=w[1], flavor=w[2], what=w[3],
                  pipeline=s.pipeline) if (w := g.wording.get(s.id)) else
            Shape(**vars(s))
            for s in catalog.values()]
        genres[name] = g

    # Every genre inherits the universal table on top of its own, and its own row wins
    # on a collision - four genres word `building-interior` their own way, and those
    # definitions are the ones that hold for them. No Genre inherits it too, and the
    # document says it matters more there than anywhere: a prompt with no genre is
    # usually describing a place, and these are what a place is made of.
    universal = _universal(lines)
    no_genre = _no_genre(lines)
    for g in list(genres.values()) + [no_genre]:
        own = {o.id for o in g.options}
        g.options.extend(o for o in universal if o.id not in own)

    return genres, descs, universal, no_genre, catalog


#: The document's own name for the sixteenth destination, which is not a genre.
NO_GENRE_NAME = "No Genre"

GENRES, GENRE_DESCS, UNIVERSAL, NO_GENRE, SHAPES = _parse()

#: Every option ID in the system, independent of which section words it. No Genre is
#: included because its rows obey the same shared-catalogue rule as numbered genres.
#:
#: The current genre's own row still wins in ``Genre.option``. This fallback is for the
#: new cross-genre path: take the ID and structural metadata from the catalogue, while
#: the spec's contextual ``text`` supplies the prompt-specific realization.
OPTION_SOURCES: dict[str, list[tuple[str, Option]]] = {}
for _g in [*GENRES.values(), NO_GENRE]:
    for _o in _g.options:
        sources = OPTION_SOURCES.setdefault(_o.id, [])
        if not any(existing_genre == _g.name for existing_genre, _ in sources):
            sources.append((_g.name, _o))


def _catalog_option(sources: list[tuple[str, Option]]) -> Option:
    """One neutral fallback row without flattening genuine metadata differences."""
    base = sources[0][1]
    destinations = {option.goes_to for _, option in sources}
    pipelines = {option.pipeline for _, option in sources}
    return replace(
        base,
        goes_to=next(iter(destinations)) if len(destinations) == 1 else "varies",
        pipeline=next(iter(pipelines)) if len(pipelines) == 1 else "varies",
        core=False,
    )


OPTION_CATALOG: dict[str, Option] = {
    option_id: _catalog_option(sources)
    for option_id, sources in OPTION_SOURCES.items()
}


def option_variants(genre: Genre, option_id: str) -> list[Option]:
    """Applicable structural rows for an option in ``genre``.

    A row owned by the current genre is authoritative. Otherwise all source rows
    remain candidates so callers can use the spec's explicit route and destination
    decision instead of silently borrowing the first genre's interpretation.
    """
    sources = OPTION_SOURCES.get(option_id, [])
    own = [option for source, option in sources if source == genre.name]
    return own or [option for _, option in sources]


def option_destinations(genre: Genre, option_id: str) -> set[str]:
    return {option.goes_to for option in option_variants(genre, option_id)}


def option_pipelines(genre: Genre, option_id: str) -> set[str]:
    return {option.pipeline for option in option_variants(genre, option_id)}

#: Retired shape id -> the catalogue row that absorbed it, vendored from the upstream
#: rules repo beside the documents it belongs to.
#:
#: Merging the fifteen per-genre shape tables into one catalogue collapsed rows that had
#: been separate only because they lived in different genres: `arena-flat`, `field-bounded`
#: and `space-continuous` were one bounded single-level space described three times, and
#: are now `space-bounded`. Specs written before the merge name ids the catalogue no longer
#: has, and dropping their shape would silently turn a decided build into an undecided one,
#: so they are rewritten instead. This is a rename, not a re-decision - anything that needs
#: the new document's *judgement* needs a new run, not this.
SHAPE_MIGRATION: dict[str, str] = json.loads(MIGRATION_DOC.read_text()) \
    if MIGRATION_DOC.is_file() else {}


def genre(name: str) -> Genre | None:
    """Any of the fifteen, or the No Genre fallback.

    Callers that route a spec should use this rather than indexing `GENRES`: No Genre
    is a real answer with real options, and it is deliberately kept out of that dict so
    that anything enumerating the genres - the catalogue, the router's fifteen-way
    choice - does not offer it as a sixteenth.
    """
    return NO_GENRE if name == NO_GENRE_NAME else GENRES.get(name)

#: Every option ID that appears in more than one genre, per the shared registry.
#: Universal options are excluded: they are in all fifteen by construction, so listing
#: them here would say nothing and drown the IDs that are genuinely shared.
SHARED_IDS: dict[str, list[str]] = {}
for _g in [*GENRES.values(), NO_GENRE]:
    for _o in _g.options:
        if not _o.universal:
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
#: No Genre names no game type, so there is none to name here either. The rest of the
#: instruction is unchanged - what the space is for does not change how it is built.
PLACE_HEADER = (
    "LAYOUT FEATURES for this map. Build these as the actual structure of "
    "the space rather than as set dressing, keep them visually distinct from one "
    "another, and keep the whole layout legible in one view."
)
SHAPE_LINE = "SHAPE OF THE SPACE - {label}: {what}"
AXIS_LINE = "SHAPE OF THE SPACE - {what}"

#: Axes whose non-default value decides how the layout is generated rather than what it
#: looks like. `must-be-valid` says the topology is the deliverable, which is what buys
#: `P6` and draws the plan before the picture; its wording - "a solvable maze, a
#: connected circuit, a physics-legal jump path" - defines the category for whoever is
#: answering the question, and describes no particular space. The order it forces
#: already carries it, so injecting the sentence as well would only spend the image
#: model's attention on a decision that has been made.
ROUTING_ONLY_AXES = {"axis-structure"}


def axis_lines(g: Genre, axes: dict[str, str]) -> list[str]:
    """The chosen axis values, worded as the document words them, as one line.

    Defaults are skipped. They are the absence of a choice rather than one, the
    document gives them no clause to inject, and saying "exterior, single surface" on
    every place prompt would spend the image model's attention on nothing.
    """
    said = []
    for key, value in (axes or {}).items():
        a = g.axis(key)
        if a is None or value == a.default or a.id in ROUTING_ONLY_AXES:
            continue
        if clause := a.clauses.get(value, ""):
            said.append(clause.rstrip("."))
    return [AXIS_LINE.format(what="; ".join(said) + ".")] if said else []


def render(genre_name: str, shape: Shape | None, bullets: list[tuple[str, str]],
           axis_text: list[str] | None = None) -> str:
    """Assemble the addendum from an explicit shape and feature list.

    Picking nothing is a legitimate outcome and returns an empty string - the user
    gets a simple map, which Build.md is explicit is not a failure.
    """
    axis_text = axis_text or []
    if shape is None and not bullets and not axis_text:
        return ""
    parts = [PLACE_HEADER if genre_name == NO_GENRE_NAME
             else HEADER.format(genre=genre_name)]
    if shape is not None:
        parts.append(SHAPE_LINE.format(label=shape.label, what=shape.what))
    parts.extend(axis_text)
    if bullets:
        parts.append("INCLUDE:\n" + "\n".join(
            f"- {lab}: {txt}" if lab else f"- {txt}" for lab, txt in bullets))
    return "\n\n".join(parts)


def injection(genre: Genre, shape: Shape | None, option_ids: list[str],
              axes: dict[str, str] | None = None) -> str:
    """The Stage A addendum for one shape and a set of picked options.

    Only what a segmenter could recover from a render is injected: options marked
    ``layout`` are dropped, and ``both`` contributes its visible part.
    """
    picks = [o for oid in option_ids if (o := genre.option(oid)) and o.drawn]
    return render(genre.name, shape,
                  [(o.label, visible_text(genre.name, o)) for o in picks],
                  axis_lines(genre, axes or {}))


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


def route_of(genre: Genre, shape: Shape | None, option_ids: list[str],
             axes: dict[str, str] | None = None) -> list[str]:
    """The pipeline modifiers this combination forces, in document order.

    ``axes`` is how a No Genre build says what a shape would otherwise say. Only a
    non-default value carries anything, so an empty mapping and a mapping that names
    every default are the same answer, and both route `P0`.

    ``SET`` is included and is not like the others: it says there is a space but
    nobody walks through it, so it sits alongside whatever route applies rather than
    replacing it - `P0 + SET` and `P3 + SET` are both ordinary answers.

    A base pass is always present. `tiered`, `CHECK` and `SET` each modify a build
    rather than being one, so a combination that names only those is a P0 build with
    that modification - which is how the document writes it, `["P0", "SET"]`.
    """
    tags: list[str] = []
    axis_costs = [a.routes.get(v, "") for k, v in (axes or {}).items()
                  if (a := genre.axis(k)) is not None]
    for text in ([genre.route, shape.pipeline if shape else ""] + axis_costs
                 + [o.pipeline for oid in option_ids if (o := genre.option(oid))]):
        for tag in re.findall(r"\bP\d\b|\btiered\b|\bCHECK\b|\bSET\b", text or ""):
            if tag not in tags:
                tags.append(tag)
    if not any(re.fullmatch(r"P\d", t) for t in tags):
        tags.insert(0, "P0")
    return tags


if __name__ == "__main__":
    print(f"{len(GENRES)} genres, {len(GENRE_DESCS)} descriptions")
    for g in GENRES.values():
        drawn = sum(1 for o in g.options if o.drawn)
        print(f"  {g.num:2d}. {g.name:<26} {len(g.shapes)} shapes  "
              f"{len(g.options):2d} options ({drawn} drawn)  "
              f"{len(g.presets)} presets  {len(g.notes)} notes"
              + (f"  route={g.route.split(':')[1].strip().rstrip('.')}" if g.route else ""))
    print(f"\nshared option ids: {len(SHARED_IDS)}")
    ng = NO_GENRE
    print(f"\n{ng.name}: {len(ng.axes)} axes, {len(ng.options)} options, "
          f"{len(ng.presets)} presets, {len(ng.notes)} notes")
    for a in ng.axes:
        costs = ", ".join(f"{v} -> {c}" for v, c in a.routes.items()) or "free"
        print(f"  {a.id:<16} default {a.default:<16} {costs}")
