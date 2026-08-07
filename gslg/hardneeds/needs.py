"""Genre Hard Needs from LayoutGen - Build.md, Part II, as prompt-injectable text.

Build.md states Hard Needs as engineering requirements using Shared Vocabulary
terms (``TriggerZone``, ``SpawnZone``, ``Chunk``). An image model has no idea what
a ``TriggerZone`` is, so each need carries two strings:

``primitive``/``role``  the machine-readable handle, verbatim from Build.md. This
                        is what a validator and the Stage B taxonomy key off.
``visual``              the same requirement restated as visible content, which is
                        the only form a text-to-image model can act on.

Only Hard Needs are encoded here. Suggested Layout Features are deliberately
excluded so the A/B measures the minimum that makes a layout playable.

Sub-genre resolution matters for two genres and is why the corpus tag columns are
worth plumbing through: ``sports_racing`` splits into two genres with completely
different Hard Needs, and ``strategy`` splits into Tower Defense (which has an
Actor Track) and RTS (which explicitly has no path at all).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HardNeed:
    primitive: str
    role: str
    visual: str


@dataclass(frozen=True)
class Delta:
    """One line of a Build.md Sub-Genre Override block."""

    kind: str  # ADD | REPLACE | REMOVE | PROMOTE | RETUNE
    primitive: str
    role: str
    note: str
    # Role name in the parent genre's Hard Needs this acts on. Required for
    # REPLACE/REMOVE/RETUNE, unused for ADD/PROMOTE.
    target: str | None = None
    # Replacement visual text. Required for everything except REMOVE.
    visual: str = ""


@dataclass(frozen=True)
class OverrideSpec:
    name: str
    genre: str
    example: str
    summary: str
    deltas: tuple[Delta, ...]
    # (game_genre, game_subgenre) pairs in the corpus taxonomy that reach this
    # override. Empty means no corpus tag can currently trigger it.
    corpus_tags: tuple[tuple[str, str], ...] = ()


HARD_NEEDS: dict[str, list[HardNeed]] = {
    "Action": [
        HardNeed("CombatZone", "Central Clash Arena",
                 "one wide, completely flat central fighting floor kept clear of small "
                 "tripping clutter"),
        HardNeed("SpawnZone", "Spawn Buffer",
                 "team spawn areas set at the edges, each walled off or raised above the "
                 "arena floor so they read as protected"),
    ],
    "Adventure": [
        HardNeed("Gate", "Linear/Branched Thresholds",
                 "clear physical bottlenecks between areas - canyon narrows, gateways or "
                 "structural doors - that read as chapter transitions"),
        HardNeed("Landmark", "Reveal Openings (Cinematic Viewports)",
                 "at least one opening where a tight space gives way to a wide view, "
                 "positioned so a distant landmark is visible through it"),
        HardNeed("Collectible", "Objective Pedestals",
                 "explicit focal points such as altars or ruin platforms built to hold "
                 "quest objects"),
    ],
    "Obby & Platformer": [
        HardNeed("Path", "Sequential Grid Track",
                 "one continuous chain of separate jumping platforms running start to "
                 "finish, with visible gaps between them, in a clearly traceable order "
                 "and no ambiguous branches"),
        HardNeed("Checkpoint", "Safe Landing Pads",
                 "flat, wider resting pads spaced along that chain that clearly read as "
                 "safe standing places distinct from the jump platforms"),
        HardNeed("HazardZone", "Hazard Volumes",
                 "an obvious fall-through void or clearly marked lethal surface beneath "
                 "and around the platform chain"),
    ],
    "Party & Casual": [
        HardNeed("SocialZone", "Social Lobby & Leaderboard",
                 "a separate waiting lobby with one prominent flat feature wall sized to "
                 "hold a leaderboard display"),
        HardNeed("SpectatorZone", "Isolated Stage",
                 "the minigame stage as a physically separate area with a visible gap or "
                 "barrier between it and the lobby"),
    ],
    "Puzzle": [
        HardNeed("SpectatorZone", "Hermetic Compartments",
                 "fully sealed rooms or enclosed containment areas with walls on all "
                 "sides, readable as separate chambers"),
        HardNeed("TriggerZone", "Interaction Slots",
                 "rigid receiving slots built into walls, tables or pedestals - visible "
                 "indentations shaped to accept a missing puzzle piece"),
    ],
    "RPG": [
        HardNeed("SafeZone", "Sanctuary Hub & Economy Ring",
                 "a compact town core with shop, quest-giver and blacksmith buildings "
                 "clustered tightly together in a ring"),
        HardNeed("HazardZone", "Aggro Bowls",
                 "open monster-nest clearings set well back from the main roads"),
        HardNeed("Gate", "Level-Gated Throats",
                 "highly visible blockades - a guarded bridge, massive castle gate or "
                 "mountain crack - sealing the route into the higher-threat area"),
    ],
    "Roleplay & Avatar Sim": [
        HardNeed("SocialZone", "Town Square Core",
                 "one large central social plaza with room for a dense crowd and no "
                 "pinch points at its entrances"),
        HardNeed("Path", "Unified Road Network",
                 "wide, flat, grid-aligned streets forming a connected road network "
                 "between residential and commercial blocks, wide enough for two lanes "
                 "of vehicles to pass"),
    ],
    "Shooter": [
        HardNeed("SpawnZone", "Opposing Team Bases",
                 "two mirrored team bases at opposite ends of the map, each visually "
                 "shielded from the other's sightlines"),
        HardNeed("Lane", "Three-Lane Architecture",
                 "three distinct parallel routes - left, centre and right - running "
                 "between the two bases, with rooms connecting sideways between them so "
                 "there are no dead ends"),
        HardNeed("Cover", "Tactical Cover Arrays",
                 "waist-high and full-height cover blocks distributed evenly along all "
                 "three routes"),
    ],
    "Simulation": [
        HardNeed("BuildZone", "Isolated Tycoon Footprints",
                 "several large, equally sized, evenly spaced individual plots that do "
                 "not overlap or touch each other"),
        HardNeed("SocialZone", "The Upgrades Bazaar",
                 "one central shop or upgrade storefront reachable from every plot"),
    ],
    "Strategy": [
        HardNeed("Path", "The Actor Track",
                 "one single clearly defined winding enemy track running unbroken across "
                 "the map from the monster spawn opening to the defended structure, easy "
                 "to trace end to end with no forks or gaps"),
        HardNeed("BuildZone", "Tower Placement Grid",
                 "flat open tower-placement pads framing both sides of that track along "
                 "its whole length"),
        HardNeed("Tracker", "ObjectivePoint (The Core Base)",
                 "one prominent structure at the far end of the track that clearly reads "
                 "as the thing being defended"),
    ],
    "Survival": [
        HardNeed("Path", "Looping Escape Routes",
                 "corridors and routes built entirely as interconnected loops with zero "
                 "dead ends, so every route rejoins another and a fleeing player can "
                 "always keep moving"),
        HardNeed("Gate", "Gate Exit Layouts",
                 "large escape doors or hatches set into the outer boundary wall as the "
                 "visible way out"),
    ],
    "Sports": [
        HardNeed("TriggerZone", "Play/Foul Boundaries",
                 "a precise, rigid painted or marked perimeter defining the exact active "
                 "field of play, in correct regulation proportions"),
        HardNeed("StartPoint", "Point-of-Origin / Play-Start",
                 "the fixed play-start positions marked on the surface, such as a centre "
                 "circle, pitch mound and home plate, or serve boxes"),
        HardNeed("TriggerZone", "Scoring Targets",
                 "the scoring targets built as distinct structures at their regulation "
                 "positions, such as goal mouths, hoops or wickets"),
        HardNeed("SpectatorZone", "Team Sector Enclosures",
                 "team benches or dugouts placed just outside the boundary line"),
    ],
    "Racing": [
        HardNeed("SpawnZone", "Multi-Lane Starting Grid",
                 "a wide starting grid at the start line divided into evenly spaced "
                 "side-by-side lane slots"),
        HardNeed("Barrier", "Lateral Path Boundaries",
                 "continuous barriers, guardrails or painted edge lines running down both "
                 "sides of the entire route so the drivable corridor is unambiguous"),
        HardNeed("TriggerZone", "Lap Verification",
                 "marked checkpoint gates spaced at intervals along the route"),
        HardNeed("TriggerZone", "Terminal Finish",
                 "one distinct finish line structure at the exact end of the course"),
    ],
    "Infinite Runner": [
        HardNeed("Lane", "Multi-Lane Grid Alignment",
                 "the track split into three rigid parallel lanes of equal width running "
                 "straight down the direction of travel"),
        HardNeed("Chunk", "Deterministic Alignment",
                 "the track built from repeating modular segments whose ends line up flush "
                 "on a single axis, so the road reads as tileable"),
        HardNeed("TriggerZone", "Object-Pooling Despawn",
                 "a clear open run-off region behind the start where old track segments "
                 "would be cleaned up"),
    ],
    "Entertainment": [
        HardNeed("Path", "Guided Reveal Route",
                 "one clear walking route threading through the space that sequences the "
                 "key views in order"),
        HardNeed("Landmark", "Hero Focal Builds",
                 "one or more large, deliberately composed centrepiece structures framed "
                 "from along that route"),
        HardNeed("SpawnZone", "Curated First Reveal",
                 "an arrival point positioned so the first thing seen is a composed view "
                 "of the centrepiece, never backstage geometry"),
    ],
}


# The "Sub-Genre Overrides" / "Variant Overrides" prose blocks of Build.md Part II,
# encoded as deltas against the parent genre's Hard Needs. Build.md is explicit that
# these REPLACE rather than add, so applying them as a union would inject exactly the
# requirements the rules forbid.
#
# corpus_tags records which (game_genre, game_subgenre) pairs in the corpus taxonomy
# can actually reach each block. Most are empty: the corpus labels games by content,
# not by the structural distinctions these overrides turn on.
OVERRIDES: tuple[OverrideSpec, ...] = (
    OverrideSpec(
        name="Open World & Survival RPG",
        genre="RPG",
        example="Booga Booga",
        summary="Persistent player-driven survival/crafting rather than hub-and-dungeon. "
                "Progression is gear tier and a rebirth loop, not physical level gates.",
        corpus_tags=(("rpg", "open_world_survival_rpg"),),
        deltas=(
            Delta("REPLACE", "BuildZone", "Unclaimed Territory",
                  target="Sanctuary Hub & Economy Ring",
                  note="No fixed NPC shop/quest-giver/blacksmith hub; tribes build anywhere.",
                  visual="broad open buildable terrain across the map where players raise "
                         "their own bases, rather than one clustered NPC town"),
            Delta("REPLACE", "HazardZone", "Biome-Tiered Danger",
                  target="Aggro Bowls",
                  note="Danger is a gradient over the whole map, not fenced-off nests.",
                  visual="danger escalating as a gradient across biomes, with the harshest "
                         "terrain furthest out, rather than fenced-off monster clearings"),
            Delta("REMOVE", "Gate", "Level-Gated Throats",
                  target="Level-Gated Throats",
                  note="Build.md: don't force a guarded bridge onto this style - no zone "
                       "is unconditionally off-limits by level alone."),
            Delta("PROMOTE", "Collectible", "Resource Node Veins",
                  note="Suggested -> Hard Need: gatherable nodes are the whole progression loop.",
                  visual="gatherable resource nodes - wood, stone, ore - scattered visibly "
                         "across the open world"),
        ),
    ),
    OverrideSpec(
        name="Vehicle Sim (Shared Open Environment, No BuildZone)",
        genre="Simulation",
        example="Mega Miners",
        summary="Players cooperatively operate large vehicles in one shared persistent "
                "environment, hauling to shared processing structures. Not Racing - no lap "
                "or finish condition.",
        corpus_tags=(("simulation", "vehicle_sim"),),
        deltas=(
            Delta("REMOVE", "BuildZone", "Isolated Tycoon Footprints",
                  target="Isolated Tycoon Footprints",
                  note="Build.md: no BuildZone at all."),
            Delta("ADD", "HazardZone", "Dynamic Environmental Hazard",
                  note="May include a rising-lava style evacuation event over the shared space.",
                  visual="a dynamic environmental hazard region layered over the shared "
                         "working area"),
        ),
    ),
    OverrideSpec(
        name="Real-Time Strategy",
        genre="Strategy",
        example="MEDIEVAL REAL TIME STRATEGY",
        summary="Units path dynamically across open terrain. No fixed route, no hard-coded "
                "AI track. This is why RTS routes P0 while Tower Defense routes P6.",
        deltas=(
            Delta("REMOVE", "Path", "The Actor Track", target="The Actor Track",
                  note="No winding enemy lane exists to build."),
            Delta("REPLACE", "BuildZone", "Territorial Free Placement",
                  target="Tower Placement Grid",
                  note="Buildable land radiates from each base, gated by proximity rules.",
                  visual="broad buildable territory radiating outward from each player's "
                         "base rather than a narrow strip flanking a lane"),
            Delta("RETUNE", "Tracker", "Core Base (all-approach)",
                  target="ObjectivePoint (The Core Base)",
                  note="Fixed heart of own territory, defensible from every direction.",
                  visual="each player's core structure sited at the heart of their own "
                         "territory so it is approachable, and defensible, from all sides"),
        ),
    ),
    OverrideSpec(
        name="MilSim / Tactical Shooter",
        genre="Shooter",
        example="BODYCAM: SWAT Simulator",
        summary="Slow, deliberate, high-punishment pacing. Squad-vs-objective or "
                "squad-vs-squad-with-one-life rather than two symmetric respawning bases.",
        deltas=(
            Delta("REPLACE", "Path", "Terminating Room-Clearing Sequence",
                  target="Three-Lane Architecture",
                  note="A raid site of rooms dead-ending into breach points, not a lane network.",
                  visual="a raid structure of connected rooms that dead-end into breach "
                         "points, cleared in a defined sequence rather than parallel lanes"),
            Delta("RETUNE", "Cover", "Exposed Chokepoints",
                  target="Tactical Cover Arrays",
                  note="Doorways and breach points are deliberately exposed - that IS the tension.",
                  visual="cover through the rooms, with doorways and breach points left "
                         "deliberately exposed as the points of tension"),
            Delta("REMOVE", "SpawnZone", "Opposing Team Bases",
                  target="Opposing Team Bases",
                  note="One staging SpawnZone per squad, not two mirrored bases."),
        ),
    ),
    OverrideSpec(
        name="Input Variant Overrides (Non-Spatial Answers)",
        genre="Puzzle",
        example="The Logo Quiz!",
        summary="The answer is verified through chat or a UI text box, so there is no "
                "spatial slot to build. The layout shrinks to housing the clue.",
        corpus_tags=(("puzzle", "word"),),
        deltas=(
            Delta("REMOVE", "TriggerZone", "Interaction Slots", target="Interaction Slots",
                  note="No physical object is ever placed into a slot."),
            Delta("ADD", "Barrier", "Clue Facade",
                  note="The clue display becomes the layout's whole purpose.",
                  visual="a prominent feature wall or framed display placed directly in the "
                         "player's natural line of sight to host the clue"),
            Delta("ADD", "Gate", "Answer Gate",
                  note="Gates forward progress once a correct chat/UI answer registers.",
                  visual="a clear physical gate along the route that reads as the barrier "
                         "opened by answering correctly"),
        ),
    ),
    OverrideSpec(
        name="Role Simulation (Task-Loop, No BuildZone)",
        genre="Simulation",
        example="pilot, doctor, trucker, medieval farmer",
        summary="Imitates the day-to-day tasks of a job rather than building a base. A "
                "defined, repeatable task loop, frequently cooperative.",
        deltas=(
            Delta("REMOVE", "BuildZone", "Isolated Tycoon Footprints",
                  target="Isolated Tycoon Footprints", note="No BuildZone at all."),
            Delta("ADD", "TriggerZone", "Task Stations",
                  note="Pickup, delivery, patient bed, planting plot - the actual content.",
                  visual="distinct task stations - pickup, delivery, treatment or planting "
                         "points - spread through a themed work environment"),
            Delta("ADD", "Path", "Task Loop Route",
                  note="Chains the task stations into a repeatable circuit.",
                  visual="a connecting route that chains those task stations into a loop"),
        ),
    ),
    OverrideSpec(
        name="Shared / Co-op Tycoon",
        genre="Simulation",
        example="2 Player Secret Hideout Tycoon",
        summary="Two or more players intentionally share one BuildZone; upgrades are spread "
                "across the single shared structure and benefit the team jointly.",
        deltas=(
            Delta("RETUNE", "BuildZone", "Shared Team Footprint",
                  target="Isolated Tycoon Footprints",
                  note="One right-sized BuildZone per team, not one per player.",
                  visual="one large shared plot per team with upgrade stations spread "
                         "across it, rather than one isolated plot per player"),
        ),
    ),
    OverrideSpec(
        name="Resource-Extraction Tycoon Hybrid",
        genre="Simulation",
        example="Ultimate Mining Tycoon",
        summary="Pairs isolated per-player factory plots with a separate large shared "
                "open-world resource zone that everyone extracts from.",
        deltas=(
            Delta("ADD", "BuildZone", "Shared Extraction Zone",
                  note="Not part of anyone's personal plot and must not be built as one.",
                  visual="a separate large shared extraction site, distinct from the "
                         "personal plots and clearly not owned by any one of them"),
            Delta("ADD", "Path", "Haul Route",
                  note="Vehicle route between the shared resource zone and the plots.",
                  visual="a vehicle haul route linking that shared site back to the plots"),
        ),
    ),
    OverrideSpec(
        name="Vehicle Obby",
        genre="Obby & Platformer",
        example="car / boat / plane obbies",
        summary="Traversal is in a vehicle, so Part I's WalkSpeed / JumpHeight / step-height "
                "metrics do not apply at all.",
        deltas=(
            Delta("RETUNE", "Path", "Vehicle-Spaced Track",
                  target="Sequential Grid Track",
                  note="Spacing from turning radius, top speed and ramp tolerance.",
                  visual="a continuous drivable course whose gaps, ramps and corner radii "
                         "are sized for a vehicle rather than for jumping on foot"),
            Delta("RETUNE", "Checkpoint", "Vehicle Reset Pads",
                  target="Safe Landing Pads",
                  note="Must restore vehicle position, orientation and zeroed velocity.",
                  visual="wide flat reset pads along the course sized to receive a vehicle "
                         "squarely, with clear approach and exit orientation"),
        ),
    ),
    OverrideSpec(
        name="Glitch Obby",
        genre="Obby & Platformer",
        example=None or "wallhop / ladder-flick courses",
        summary="Deliberately inverts the Path need: spacing is set BEYOND normal jump and "
                "step limits to require engine-state techniques. Spacing cannot be derived "
                "from Part I at all and must be empirically tuned.",
        deltas=(
            Delta("RETUNE", "Path", "Beyond-Limit Spacing", target="Sequential Grid Track",
                  note="The one style where the documented physics baseline is inapplicable, "
                       "not merely overridden.",
                  visual="a climbing route of wall corners, trusses and ledges spaced too "
                         "far apart for an ordinary jump"),
        ),
    ),
    OverrideSpec(
        name="Cooperative / Asymmetric (2-Player) Obby",
        genre="Obby & Platformer",
        example="balloon-and-holder, frog-and-tongue",
        summary="Two players with complementary movement abilities share the course, which "
                "breaks the genre's baseline 'own pace' assumption.",
        deltas=(
            Delta("RETUNE", "Path", "Paired-Reach Track", target="Sequential Grid Track",
                  note="Spacing accounts for the pair's combined reach.",
                  visual="a course whose gaps are crossable only by two players combining "
                         "their abilities, not by either one alone"),
            Delta("RETUNE", "Checkpoint", "Paired Checkpoints", target="Safe Landing Pads",
                  note="Save both players together so neither is stranded.",
                  visual="checkpoint pads wide enough to hold both players together"),
        ),
    ),
    OverrideSpec(
        name="Static Map (No Personal Housing)",
        genre="Roleplay & Avatar Sim",
        example="Adventure Time: Land of Ooo Showcase",
        summary="The map is fixed, pre-built content. Personalization happens only through "
                "the avatar, never property. The most common of the three housing models.",
        deltas=(),
    ),
    OverrideSpec(
        name="Claimable House (Static Inventory, Minimal Customization)",
        genre="Roleplay & Avatar Sim",
        example="Welcome to The Town of Robloxia",
        summary="A fixed set of pre-built houses players claim rather than construct.",
        deltas=(
            Delta("ADD", "BuildZone", "Claimable House Models",
                  note="Replaces the per-player grid of empty lots.",
                  visual="a set of individually distinct pre-built houses distributed "
                         "through the town, ready to be claimed, rather than empty lots"),
        ),
    ),
    OverrideSpec(
        name="Personalized Building (Full Player-Constructed Plots)",
        genre="Roleplay & Avatar Sim",
        example="Bloxburg, Brookhaven",
        summary="The style the BuildZone (Modular Property Plots) Suggested feature "
                "describes in full. Build.md notes it is the LEAST common of the three.",
        deltas=(
            Delta("PROMOTE", "BuildZone", "Modular Property Plots",
                  note="Suggested -> Hard Need under this housing model only.",
                  visual="uniform flat square lots on a strict grid where players spawn "
                         "their own houses"),
        ),
    ),
)


def overrides_for(genre: str) -> list[OverrideSpec]:
    return [o for o in OVERRIDES if o.genre == genre]


# Corpus game_genre label -> Build.md genre. Two labels are ambiguous and need the
# game_subgenre column to resolve, which is exactly the argument for plumbing the
# corpus tags through the pipeline.
_GENRE_ALIASES = {
    "action": "Action",
    "adventure": "Adventure",
    "obby_platformer": "Obby & Platformer",
    "obby_and_platformer": "Obby & Platformer",
    "party_casual": "Party & Casual",
    "party_and_casual": "Party & Casual",
    "puzzle": "Puzzle",
    "rpg": "RPG",
    "roleplay_avatar_sim": "Roleplay & Avatar Sim",
    "roleplay_and_avatar_sim": "Roleplay & Avatar Sim",
    "shooter": "Shooter",
    "simulation": "Simulation",
    "strategy": "Strategy",
    "survival": "Survival",
    "sports": "Sports",
    "racing": "Racing",
    "infinite_runner": "Infinite Runner",
    "entertainment": "Entertainment",
    "other_entertainment": "Entertainment",
    "showcase_and_hub": "Entertainment",
}

_SUBGENRE_SPLITS = {
    # sports_racing collapses two Build.md genres whose Hard Needs share nothing.
    ("sports_racing", "racing"): "Racing",
    ("sports_racing", "sports"): "Sports",
    ("sports_and_racing", "racing"): "Racing",
    ("sports_and_racing", "sports"): "Sports",
    # An Obby tagged 'runner' is really Infinite Runner: forward motion is automatic.
    ("obby_platformer", "runner"): "Infinite Runner",
    ("obby_and_platformer", "runner"): "Infinite Runner",
}


def resolve_genre(game_genre: str, game_subgenre: str = "") -> str | None:
    """Map a corpus (game_genre, game_subgenre) pair onto a Build.md genre."""
    key = (game_genre or "").strip().lower()
    sub = (game_subgenre or "").strip().lower()
    if (key, sub) in _SUBGENRE_SPLITS:
        return _SUBGENRE_SPLITS[(key, sub)]
    if key == "sports_racing" or key == "sports_and_racing":
        return "Racing"  # corpus default: the racing subgenres dominate this label
    return _GENRE_ALIASES.get(key)


# Corpus subgenres that carry a Layout Attribute rather than a rule change. These
# steer the pipeline ROUTE and leave the Hard Needs alone. Sourced from the matching
# entry in VARIATIONS[] in pipeline-viewer.html.
_ATTRIBUTE_TAGS: dict[tuple[str, str], tuple[tuple[str, ...], str, str]] = {
    ("obby_platformer", "tower_obby"): (
        ("P2",), "verticality: stacked",
        "Tower / spiral obby - levels overhang each other, so a single top-down occludes."),
    ("obby_and_platformer", "tower_obby"): (
        ("P2",), "verticality: stacked",
        "Tower / spiral obby - levels overhang each other, so a single top-down occludes."),
    ("puzzle", "escape_room"): (
        (), "enclosure: interior-only",
        "Escape room - the whole game is inside, so it generates roofless as one top-down."),
    ("survival", "escape"): (
        (), "enclosure: exterior",
        "Threat-evasion map; enclosure depends on the scene, default exterior."),
    ("strategy", "tower_defense"): (
        ("P6",), "structure: must-be-valid",
        "The enemy lane must be one continuous valid path - procedural-first."),
    ("sports_racing", "racing"): (
        ("P6",), "structure: must-be-valid",
        "Even a simple circuit must be a connected loop - procedural-first."),
    ("sports_and_racing", "racing"): (
        ("P6",), "structure: must-be-valid",
        "Even a simple circuit must be a connected loop - procedural-first."),
    ("obby_platformer", "runner"): (
        ("P6",), "structure: must-be-valid",
        "Layout is procedural chunk rules - P6 by nature."),
    ("obby_and_platformer", "runner"): (
        ("P6",), "structure: must-be-valid",
        "Layout is procedural chunk rules - P6 by nature."),
}

# Corpus subgenres with no Build.md rules of any kind.
_UNCOVERED = {
    ("simulation", "sandbox"): "Build.md's Simulation section covers Tycoon plus four "
                               "overrides; sandbox is none of them.",
    ("simulation", "idle"): "No Hard Needs written for idle/incremental layouts.",
    ("simulation", "incremental_simulator"): "No Hard Needs written for incremental layouts.",
    ("simulation", "physics_sim"): "No Hard Needs written for physics sandboxes.",
    ("strategy", "board_card_games"): "Named in the Strategy genre description but given "
                                      "no Hard Needs.",
    ("action", "open_world_action"): "No override written; base Action Hard Needs assume "
                                     "a bounded arena.",
    ("entertainment", "music_audio"): "Build.md marks Music & Audio out of scope.",
    ("action", "music_rhythm"): "Rhythm layouts have no rules in Build.md.",
}

# Corpus subgenres that are too coarse to pick an override on their own.
_AMBIGUOUS = {
    ("roleplay_avatar_sim", "life"): (
        "Housing Model", "Build.md defines three housing models with different BuildZone "
        "treatment - Static Map, Claimable House, Personalized Building - and 'life' does "
        "not say which."),
    ("entertainment", "showcase_hub"): (
        "Showcase vs Hub", "Teleporter (Hub Portal Gates) is a Hard Need for Hub layouts "
        "only, and this label merges Showcase with Hub."),
    ("puzzle", "match_merge"): (
        "Spatial vs non-spatial", "Match-and-merge may be a UI grid with no spatial slot, "
        "which would trigger the Non-Spatial Answers override."),
    ("shooter", "pve_shooter"): (
        "Arcade vs MilSim", "PvE squad-vs-objective leans MilSim, but Build.md records four "
        "further shooter styles it does not yet cover."),
}


@dataclass
class Resolution:
    corpus_genre: str
    corpus_subgenre: str
    genre: str | None = None
    override: OverrideSpec | None = None
    needs: list[HardNeed] = field(default_factory=list)
    applied: list[Delta] = field(default_factory=list)
    route: list[str] = field(default_factory=list)
    attribute: str | None = None
    trace: list[tuple[str, str]] = field(default_factory=list)
    question: tuple[str, str] | None = None
    uncovered: str | None = None

    @property
    def ok(self) -> bool:
        return self.genre is not None and bool(self.needs)


def _apply(needs: list[HardNeed], spec: OverrideSpec) -> tuple[list[HardNeed], list[Delta]]:
    out = list(needs)
    applied: list[Delta] = []
    for d in spec.deltas:
        if d.kind in ("REPLACE", "RETUNE", "REMOVE"):
            idx = next((i for i, n in enumerate(out) if n.role == d.target), None)
            if idx is None:
                continue
            if d.kind == "REMOVE":
                out.pop(idx)
            else:
                out[idx] = HardNeed(d.primitive, d.role, d.visual)
        else:  # ADD / PROMOTE
            out.append(HardNeed(d.primitive, d.role, d.visual))
        applied.append(d)
    return out, applied


def resolve(game_genre: str, game_subgenre: str = "") -> Resolution:
    """Full corpus-tag -> injected-requirements resolution, with a decision trace."""
    key = (game_genre or "").strip().lower()
    sub = (game_subgenre or "").strip().lower()
    r = Resolution(corpus_genre=key, corpus_subgenre=sub)

    if (key, sub) in _UNCOVERED:
        r.uncovered = _UNCOVERED[(key, sub)]
        r.trace.append(("No rules", r.uncovered))
        return r

    # 1. genre
    if (key, sub) in _SUBGENRE_SPLITS:
        r.genre = _SUBGENRE_SPLITS[(key, sub)]
        r.trace.append(("Genre split on subgenre",
                        f"'{key}' collapses several Build.md genres; subgenre '{sub}' "
                        f"selects {r.genre}."))
    elif key in ("sports_racing", "sports_and_racing"):
        r.genre = "Racing"
        r.trace.append(("Genre default",
                        f"'{key}' is ambiguous and subgenre '{sub or 'unspecified'}' does "
                        "not resolve it; defaulting to Racing."))
    else:
        r.genre = _GENRE_ALIASES.get(key)
        if r.genre is None:
            r.trace.append(("Unmapped", f"No Build.md genre for corpus label '{key}'."))
            return r
        r.trace.append(("Genre", f"'{key}' maps directly to Build.md genre {r.genre}."))

    r.needs = list(HARD_NEEDS.get(r.genre, []))
    r.trace.append((f"{r.genre} Hard Needs",
                    f"{len(r.needs)} baseline requirements from Build.md Part II."))

    # 2. override
    spec = next((o for o in OVERRIDES if (key, sub) in o.corpus_tags), None)
    if spec is not None:
        r.override = spec
        r.needs, r.applied = _apply(r.needs, spec)
        r.trace.append((f"Override: {spec.name}",
                        f"Subgenre '{sub}' names a Build.md override block. Build.md states "
                        f"these REPLACE rather than add, so {len(r.applied)} deltas are "
                        "applied to the baseline."))
    elif (key, sub) in _AMBIGUOUS:
        r.question = _AMBIGUOUS[(key, sub)]
        r.trace.append((f"Needs a ruling: {r.question[0]}", r.question[1]))

    # 3. attribute / route
    if (key, sub) in _ATTRIBUTE_TAGS:
        mods, attr, why = _ATTRIBUTE_TAGS[(key, sub)]
        r.route, r.attribute = list(mods), attr
        r.trace.append((f"Route {' + '.join(mods) if mods else 'P0'}", f"{attr} - {why}"))
    else:
        r.trace.append(("Route P0", "No non-default layout attribute implied by this tag."))
    return r


def render_addendum(needs: list[HardNeed], genre: str) -> str:
    bullets = "".join(f"\n- {n.visual}." for n in needs)
    return (
        f"\n\nPLAYABLE LAYOUT REQUIREMENTS for this {genre} map. Every one of the "
        f"following must be clearly present and readable from above, laid out so "
        f"they stay visually distinct from one another:{bullets}\n"
        "Compose these as the actual structure of the space rather than as set "
        "dressing, and keep the whole layout legible in one view."
    )


def addendum(genre: str) -> str:
    """The baseline Hard Needs of ``genre`` as a Stage-A prompt addendum."""
    needs = HARD_NEEDS.get(genre)
    if not needs:
        raise KeyError(f"no Hard Needs recorded for genre {genre!r}")
    return render_addendum(needs, genre)


def primitives(genre: str) -> list[str]:
    """The Shared Vocabulary handles a validator would look for."""
    return [f"{n.primitive} ({n.role})" for n in HARD_NEEDS.get(genre, [])]
