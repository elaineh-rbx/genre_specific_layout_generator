"""Authored descriptions for the 44 attribute sub-genres in pipeline-viewer.html.

The source file carries a `brk` field per variation, but that explains why the
variation *routes* the way it does, not what the sub-genre *is*. These describe
the shape of the game so the funnel can be navigated by someone who does not
already know the routing rules.

Keyed by (genre, variation) exactly as they appear in VARIATIONS[].
"""

from __future__ import annotations

DESCRIPTIONS: dict[tuple[str, str], str] = {
    ("Action", "Flat arena"):
        "A single enclosed combat floor where all fighting happens in one open space.",
    ("Action", "Tiered stadium arena (relief, no overhang)"):
        "Combat floor ringed by stepped seating or terraces that rise away from play. "
        "Elevation is real, but nothing hangs over anything else.",
    ("Action", "Multi-tier arena (floors overhang)"):
        "Fighting spreads across stacked platforms and walkways that pass above one another.",

    ("Adventure", "Single-level linear trail (surface only)"):
        "One continuous outdoor route from start to end, with no interiors and no "
        "branching zones.",
    ("Adventure", "Cave-only exploration (interior only)"):
        "The entire journey happens underground; there is no surface world to build.",
    ("Adventure", "Overworld → enter caves (outside→inside)"):
        "A surface world whose chapters are gated behind cave or ruin entrances the "
        "player physically walks into.",
    ("Adventure", "Underwater exploration over a seafloor (open volume)"):
        "Free swimming through a water column above a seafloor that carries the actual "
        "layout.",

    ("Obby & Platformer", "Flat difficulty-chart obby"):
        "A course of numbered stages laid end to end on one plane, escalating in difficulty.",
    ("Obby & Platformer", "Flat vehicle obby"):
        "A single-surface course driven rather than jumped, with spacing sized to a vehicle "
        "instead of an avatar's jump.",
    ("Obby & Platformer", "Terraced / amphitheater obby (relief, no overhang)"):
        "The course climbs a hillside or bowl in stepped tiers, without any platform "
        "passing over another.",
    ("Obby & Platformer", "Tower / spiral obby (surfaces overhang)"):
        "The course winds upward around a central tower, so higher sections sit directly "
        "above lower ones.",

    ("Party & Casual", "Single flat minigame arena"):
        "One open stage where the whole round plays out, with players spawning straight "
        "into it.",
    ("Party & Casual", "Lobby + separate stage"):
        "A waiting area kept physically distinct from the match arena, with players moved "
        "between them between rounds.",
    ("Party & Casual", "Hide-and-seek maze"):
        "A warren of corridors and props sized for breaking line of sight, where every "
        "route has to actually connect.",

    ("Puzzle", "Open flat puzzle plaza"):
        "Puzzles arranged around one open outdoor space, with no sealed rooms.",
    ("Puzzle", "Escape room (interior only)"):
        "A sequence of sealed indoor chambers, each holding the player until its logic "
        "is solved.",
    ("Puzzle", "Maze"):
        "A layout whose solution path is itself the puzzle; it must be provably "
        "traversable from entrance to exit.",

    ("RPG", "Single-map RPG (no dungeons/interiors)"):
        "One exterior world with NPCs, shops and combat all on the surface.",
    ("RPG", "Dungeon-crawler (interior only)"):
        "The whole run happens inside a dungeon; there is no overworld to build.",
    ("RPG", "Hub + enter dungeons (outside→inside)"):
        "A safe town the player returns to between physically entered dungeon instances.",

    ("Roleplay & Avatar Sim", "Static town (exteriors only)"):
        "Streets, shops and facades to socialise around, with no building the player can "
        "walk into.",
    ("Roleplay & Avatar Sim", "Enter houses (Brookhaven, outside→inside)"):
        "A town whose buildings open into furnished interiors the player occupies.",

    ("Shooter", "Arcade lanes / arena (flat)"):
        "Three-lane competitive map on a single level, built for constant respawning "
        "engagement.",
    ("Shooter", "Indoor-only room-clearing (single building)"):
        "The entire match happens inside one structure, cleared room by room.",
    ("Shooter", "Multi-floor arena"):
        "Combat stacks vertically across floors connected by stairs and drop-downs.",
    ("Shooter", "Compound raid (approach outside → breach)"):
        "An outdoor approach to a defended structure that the attackers then enter.",
    ("Shooter", "Space dogfight — dense asteroid field (self-occluding)"):
        "Free flight through a debris field where the obstacles themselves hide what is "
        "behind them.",

    ("Simulation", "Flat tycoon plots"):
        "Equal, non-overlapping per-player plots laid out on one level around shared shops.",
    ("Simulation", "Vehicle sim (single open map)"):
        "One large shared surface built for driving between work sites.",
    ("Simulation", "Mining tycoon (surface → underground)"):
        "A surface base sitting above an excavated underground the player descends into.",

    ("Strategy", "RTS (open terrain)"):
        "Open battlefield with bases distributed around it and units pathing freely, with "
        "no fixed route.",
    ("Strategy", "Tower Defense (Actor Track)"):
        "A fixed enemy lane flanked by build pads, running from the spawn opening to the "
        "defended core.",

    ("Survival", "Flat map w/ hiding props"):
        "One exterior map dense with props sized to break line of sight.",
    ("Survival", "Indoor mascot-horror (interior only)"):
        "Trapped inside a building for the whole round with a pursuing threat.",
    ("Survival", 'Looping "zero dead-end" map'):
        "Corridors built entirely as interconnected loops, so a fleeing player is never "
        "cornered by pathfinding AI.",
    ("Survival", "Flee outside → hide in buildings (outside→inside)"):
        "Open ground for running, with enterable buildings to break line of sight in.",

    ("Sports", "Regulation field"):
        "A single field or court at regulation proportions, with marked boundaries and "
        "scoring targets.",

    ("Racing", "Simple flat circuit"):
        "A closed loop on one surface, raced for a set number of laps.",
    ("Racing", "Multi-tier track w/ tunnels"):
        "A circuit that crosses over itself on bridges and passes under itself through "
        "tunnels.",
    ("Racing", "Flight circuit over terrain (open volume)"):
        "A course flown through the air above terrain that anchors the route below.",

    ("Infinite Runner", "Procedural auto-runner"):
        "An endless lane-based track assembled from modular chunks as the player runs.",

    ("Entertainment", "Showcase (single scene)"):
        "One curated environment built to be looked at, with a route that sequences the "
        "key views.",
    ("Entertainment", "Interior walkthrough (building, interior only)"):
        "A museum or building tour that stays entirely indoors.",
    ("Entertainment", "Hub (portals out)"):
        "A lobby whose job is routing players onward to other experiences through portals.",
}


# What each non-default attribute value does to the prompt. This is what makes one
# attribute sub-genre generate differently from another within the same genre.
#
#   kind="prompt"     changes the words sent for a single image
#   kind="structure"  changes how many images are generated and what each covers,
#                     so it cannot be expressed as prompt text at all
ATTRIBUTE_EFFECT: dict[tuple[str, str], dict] = {
    ("enclosure", "interior-only"): dict(
        kind="prompt",
        text="Render this as an interior with the ceiling removed so the entire floor plan "
             "reads from above, rather than as an exterior view of a building.",
        why="the Stage A prompt already contains a cutaway branch, but nothing triggers "
            "it - the model has to guess from the scene text. This tag fires it explicitly."),
    ("enclosure", "transition"): dict(
        kind="structure",
        text="Two linked maps are generated - one exterior, one interior - each with its "
             "own Stage A and Stage B pass, joined at the doorway.",
        why="A single top-down cannot hold both an outdoor approach and the inside of the "
            "building it leads into."),
    ("verticality", "tiered"): dict(
        kind="prompt",
        text="Build the height change as visible stepped terraces or graded relief that "
             "reads clearly from directly above, and keep every surface exposed to the sky "
             "so nothing overhangs anything below it.",
        why="Relief with no overhang is still one surface, so it stays on the happy path - "
            "but it has to be stated or the model flattens it."),
    ("verticality", "stacked"): dict(
        kind="structure",
        text="The scene is split into elevation layers, and each layer gets its own "
             "top-down and mask before being stacked back together.",
        why="Overhanging surfaces occlude each other in a single top-down, so the "
            "information needed to extract them is simply not in one image."),
    ("zones", "multi-zone"): dict(
        kind="structure",
        text="The whole image-to-extract chain runs once per zone, and the zones are "
             "linked afterwards.",
        why="Separate maps cannot share one image and cannot share one scale."),
    ("structure", "must-be-valid"): dict(
        kind="prompt",
        text="Reproduce the attached blueprint's layout EXACTLY - every corner, junction "
             "and crossing in the same place and the same order. Restyle its appearance to "
             "match the scene description, but do not alter, simplify or re-route it.",
        # Used when no procedural blueprint is supplied. The A/B run showed injection
        # delivers presence and arrangement but not topology invariants, so this states
        # the invariant in words and is expected to be the weaker of the two.
        text_noref="The route must form one continuous, fully connected circuit with no "
                   "dead ends, no gaps and no segment that leads nowhere - every branch "
                   "rejoins the main route, and the path can be traced from start back to "
                   "start without lifting off it.",
        why="The topology is authored procedurally first so it is valid by construction; "
            "Stage A's job drops to dressing a layout it must not change."),
    ("playspace", "volumetric (open)"): dict(
        kind="prompt",
        text="Frame the entire play area within the single view. The space above the "
             "surface is a play-height envelope, so keep the ground layout complete and "
             "readable rather than cropping it.",
        why="Fine over a framed surface, but the whole area has to fit one image or the "
            "extraction loses the edges."),
    ("playspace", "volumetric (self-occluding)"): dict(
        kind="structure",
        text="Treated as an occlusion problem and routed through the elevation-layer path.",
        why="A volume whose own contents hide each other collapses to the same problem as "
            "overhanging floors."),
}

# The P6 validity condition, per sub-genre.
#
# Pipeline.md names four distinct ones - "solvable maze, connected circuit, single
# continuous TD lane, physics-legal obby spacing" - and they are not interchangeable.
# ATTRIBUTE_EFFECT's text_noref states the circuit condition for all seven, which is
# actively wrong for a maze: it forbids the dead ends a maze is made of. Stated here
# per sub-genre so the plan pass asks for the invariant that sub-genre actually has.
P6_INVARIANT: dict[tuple[str, str], str] = {
    ("Party & Casual", "Hide-and-seek maze"): (
        "The maze must be solvable: every open cell reachable from every entrance by at "
        "least one unbroken corridor, with no walled-off pocket. Dead-end nooks are wanted "
        "here as hiding places, but each must branch off a corridor that itself connects "
        "back to the main network."),
    ("Puzzle", "Maze"): (
        "The maze must be solvable: exactly one entrance and one exit, both on the outer "
        "wall and clearly marked, joined by at least one unbroken open corridor. No open "
        "area may be sealed off from that corridor, and no wall may cut a corridor in two."),
    ("Strategy", "Tower Defense (Actor Track)"): (
        "The enemy lane must be one single continuous path from the spawn to the defended "
        "goal - unbroken along its whole length, never splitting into a branch that stops "
        "short, and never passing through a wall. Buildable ground must border it on both "
        "sides for its whole length."),
    ("Survival", 'Looping "zero dead-end" map'): (
        "Every corridor must rejoin the network: no dead ends anywhere, and every part of "
        "the map reachable from every other by at least two different routes, so a player "
        "being chased is never cornered."),
    ("Racing", "Simple flat circuit"): (
        "The track must be one closed loop that returns to its own start line - continuous "
        "for its whole length, never breaking, never narrowing to nothing, and never "
        "leaving a stub that leads nowhere. The start/finish line sits on the loop."),
    ("Racing", "Multi-tier track w/ tunnels"): (
        "The track must be one closed loop that returns to its own start line, continuous "
        "across every change of height. Each ramp, bridge and tunnel must physically join "
        "the two pieces of track it sits between, so the loop can be driven without a gap."),
    ("Infinite Runner", "Procedural auto-runner"): (
        "The runnable lane must be one continuous forward path of consistent width, "
        "unbroken from one end of the tile to the other, with its exit aligned to its "
        "entrance so copies of the tile join seamlessly end to end."),
}

# A handful of VARIATIONS[] entries name a game *style* rather than a layout attribute
# combination, and that style is already specified as an override in Build.md. Left
# unlinked they inject the genre baseline, which for some is exactly what Build.md
# forbids (a vehicle sim would get a BuildZone). Mapping is explicit rather than matched
# on shared words, because token overlap links things like "Flat difficulty-chart obby"
# to "Vehicle Obby" purely on the word "obby".
#
#   (genre, variation) -> (override name, why the two denote the same style)
IMPLIED_OVERRIDE: dict[tuple[str, str], tuple[str, str]] = {
    ("Simulation", "Vehicle sim (single open map)"): (
        "Vehicle Sim (Shared Open Environment, No BuildZone)",
        "Build.md defines this exact style and states it has no BuildZone at all; without "
        "the link the card injects the Tycoon BuildZone the override removes."),
    ("Simulation", "Mining tycoon (surface \u2192 underground)"): (
        "Resource-Extraction Tycoon Hybrid",
        "A mining tycoon is the resource-extraction hybrid Build.md describes: isolated "
        "player plots plus a shared extraction zone joined by a haul route."),
    ("Roleplay & Avatar Sim", "Enter houses (Brookhaven, outside\u2192inside)"): (
        "Personalized Building (Full Player-Constructed Plots)",
        "Build.md cites Brookhaven by name as this housing model, so the variation and the "
        "override are the same game."),
    ("Roleplay & Avatar Sim", "Static town (exteriors only)"): (
        "Static Map (No Personal Housing)",
        "A town with no enterable housing is precisely this override. It carries no deltas, "
        "so the needs are unchanged - the link records which housing model was chosen."),
    ("Obby & Platformer", "Flat vehicle obby"): (
        "Vehicle Obby",
        "Same style; the override retunes Path and Checkpoint to vehicle spacing, which is "
        "the whole reason the variation is called out separately from the flat obby."),
    ("Strategy", "RTS (open terrain)"): (
        "Real-Time Strategy",
        "The variation and the override are the same name. Build.md's RTS has no Actor "
        "Track at all, so without the link this card injects a fixed enemy lane into a "
        "game whose units path dynamically."),
    ("Shooter", "Indoor-only room-clearing (single building)"): (
        "MilSim / Tactical Shooter",
        "Build.md's MilSim Path is literally 'Terminating Room-Clearing Sequence' - rooms "
        "dead-ending into breach points rather than a looping three-lane network."),
    ("Shooter", "Compound raid (approach outside \u2192 breach)"): (
        "MilSim / Tactical Shooter",
        "Build.md names the compound raid and its breach points as this override's example, "
        "including that it needs one staging spawn per squad, not two mirrored bases."),
}

# Deliberately NOT linked, recorded so the decision is visible rather than an oversight:
#   RPG / "Single-map RPG (no dungeons/interiors)" vs "Open World & Survival RPG"
#     A single-map themepark RPG is not necessarily open-world survival. Build.md's
#     override removes level Gates and promotes gathering, which would be wrong to force
#     onto every single-map RPG.

# Support status per attribute value, mirroring ATTR_DEFS in pipeline-viewer.html.
ATTRIBUTE_STATE: dict[tuple[str, str], str] = {
    ("enclosure", "exterior"): "ok",
    ("enclosure", "interior-only"): "ok",
    ("enclosure", "transition"): "break",
    ("verticality", "single"): "ok",
    ("verticality", "tiered"): "variant",
    ("verticality", "stacked"): "break",
    ("zones", "single"): "ok",
    ("zones", "multi-zone"): "break",
    ("structure", "dressed"): "ok",
    ("structure", "must-be-valid"): "variant",
    ("playspace", "grounded"): "ok",
    ("playspace", "volumetric (open)"): "check",
    ("playspace", "volumetric (self-occluding)"): "break",
}

AXIS_LABELS = {
    "enclosure": "Enclosure",
    "verticality": "Verticality",
    "zones": "Zone count",
    "structure": "Structure-criticality",
    "playspace": "Play-space",
}

VALUE_LABELS = {
    ("enclosure", "exterior"): "Exterior (outdoors)",
    ("enclosure", "interior-only"): "Interior-only (roofless)",
    ("enclosure", "transition"): "Outside \u2194 Inside",
    ("verticality", "single"): "Single surface (flat / rolling)",
    ("verticality", "tiered"): "Tiered / terraced (no overhang)",
    ("verticality", "stacked"): "Stacked / overhanging",
    ("zones", "single"): "Single map",
    ("zones", "multi-zone"): "Multiple zones / maps",
    ("structure", "dressed"): "Dressed (free-form)",
    ("structure", "must-be-valid"): "Must be valid (maze / track / lane)",
    ("playspace", "grounded"): "Grounded surface",
    ("playspace", "volumetric (open)"): "Volumetric \u2014 open over a surface",
    ("playspace", "volumetric (self-occluding)"): "Volumetric \u2014 self-occluding",
}
