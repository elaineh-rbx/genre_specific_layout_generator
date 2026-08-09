"""Every wrapper the image model is given, in one file.

A scene description on its own is not a prompt. Around it sits wording that fixes the
camera, states what the reference image means, and says what may and may not change -
and that wording is what makes two runs comparable. When it lived beside whichever
script first needed it, the same clause existed in three slightly different forms and
a difference between two arms could be the wrapper rather than the guidance.

The wrappers come in pairs, one per stage, because the pipeline always draws twice:

    text -> isometric -> top-down          the default, `std`
    text -> plan -> isometric              plan first, `p6`
    blueprint -> top-down -> isometric     an authored layout, `layout`

The layout order is the only one where the geometry is decided before the model sees
anything: the maze or the circuit is carved by this repo, handed over as a reference
image, and the model's job is to dress it without moving it.
"""

from __future__ import annotations

# ---------------------------------------------------------------- text -> isometric

PREFIX = "Generate directly from this text prompt only, with no reference image: "
TAIL = (" Polished square Roblox-like 3D environment concept, isometric three-quarter "
        "view, no captions or watermark.")

#: A `SET` route says there is real geometry that no avatar ever crosses - a rhythm
#: stage with a crowd, a board on a table, a shooting gallery on rails. The image is
#: still drawn and still segmented; what changes here is only the framing, because
#: there is no spawn point to sit the camera over. The saving is downstream, where
#: traversal segmentation and jump-gap validation have nothing to check.
SET_FRAMING = (
    " Frame the whole set at once, composed as something looked at rather than walked "
    "into: there is no entrance to arrive through and no route across it."
)


def isometric(source: str, addendum: str = "", set_piece: bool = False) -> str:
    """Stage A: the scene, with any guidance inserted before the style tail.

    The guidance goes inside the wrapper rather than after it so that every arm ends
    on the same sentence about style and framing - the arms differ by their guidance
    and by nothing else.
    """
    body = source.strip()
    if addendum.strip():
        body = f"{body}\n\n{addendum.strip()}"
    return f"{PREFIX}{body}{SET_FRAMING if set_piece else ''}{TAIL}"


# ------------------------------------------------------------ isometric -> top-down

#: The constant half of the Stage B wrapper; the scene text is appended.
TOPDOWN = (
    "Convert the referenced scene into a TRUE overhead nadir minimap layout. Camera is "
    "straight down (90\u00b0 top-down), ZERO perspective and ZERO isometric tilt. Show "
    "ONLY the tops of objects. NO building walls, NO doorways, NO awnings, NO side "
    "faces, NO vertical surfaces of any kind. Flat game-minimap / floor-plan style with "
    "clean flat color zones. Preserve the EXACT position, shape, size and orientation "
    "of every object from the reference image. Tightly crop to the occupied layout "
    "footprint; everything outside the footprint must be pure black (#000000). Square "
    "output. Scene details: "
)


def topdown(source: str) -> str:
    """Stage B, identical for every arm: only the isometric it converts differs."""
    return f"{TOPDOWN}{source.strip()}"


# --------------------------------------------------------------------- plan first

#: Nadir framing lifted from the Stage B wrapper, so a plan drawn first is directly
#: comparable with the top-downs the other orders produce.
PLAN_PREFIX = "Generate directly from this text prompt only, with no reference image: "
PLAN_TAIL = (
    " Draw this as a TRUE overhead nadir plan of the layout. Camera straight down "
    "(90 degrees), ZERO perspective and ZERO isometric tilt. Show only the tops of "
    "things - no side faces, no walls in elevation, no vertical surfaces of any kind. "
    "Flat game-minimap / floor-plan style with clean flat colour zones and strong "
    "contrast between walkable surface and blocked surface, so the connectivity of the "
    "layout is unmistakable. Square output, no captions or watermark."
)

ISO_FROM_PLAN_PREFIX = "Build this scene from the attached top-down plan: "
ISO_FROM_PLAN_TAIL = TAIL


def plan(source: str, addendum: str = "") -> str:
    body = source.strip()
    if addendum.strip():
        body = f"{body}\n\n{addendum.strip()}"
    return f"{PLAN_PREFIX}{body}{PLAN_TAIL}"


def isometric_from_plan(source: str, addendum: str = "",
                        set_piece: bool = False) -> str:
    body = source.strip()
    if addendum.strip():
        body = f"{body}\n\n{addendum.strip()}"
    return f"{ISO_FROM_PLAN_PREFIX}{body}{SET_FRAMING if set_piece else ''}"\
           f"{ISO_FROM_PLAN_TAIL}"


# ------------------------------------------------------------- authored maze layout

#: The blueprint encodes LAYOUT ONLY. Its positions are kept exactly so the maze stays
#: solvable, but the look has to come from the scene text - otherwise the model just
#: recolours the flat grey plan and the prompt's theme is lost.
MAZE_LAYOUT = (
    "USE THE REFERENCE IMAGE ONLY AS A LAYOUT MAP: it is a top-down floor-plan where "
    "the dark cells mark WHERE walls stand, the light cells mark the open floor and "
    "corridors, the GREEN cell is the start tile and the RED cell is the end tile. "
    "Reproduce that floor-plan EXACTLY - every wall, corridor, opening, junction and "
    "dead-end in the SAME position and proportion, walls kept THIN and corridors kept "
    "WIDE and uniformly wide, and the green start and red end tiles exactly where they "
    "are, so the maze stays solvable. Do NOT add, remove, merge, move, narrow, pinch or "
    "close any wall or corridor."
)

MAZE_STYLE = (
    "But do NOT copy the flat gray colours of the reference - it encodes only positions. "
    "Fully apply the look from the scene description above: its materials, surface "
    "colours, textures, lighting and mood on the walls and floor, and its named props. "
    "Decorative props (crates, pillars, plants, light fixtures, debris, etc.) may sit "
    "AGAINST or ON TOP OF the walls, in alcoves and in the corners, but must NEVER block, "
    "narrow or cover a corridor, a doorway, or the green and red tiles - every passage "
    "must stay clearly open and walkable end to end."
)

MAZE_ISO_FROM_TOPDOWN = (
    "The reference image is a true overhead top-down plan of this scene and it is the "
    "GROUND TRUTH for the layout. Rebuild the SAME scene as a polished isometric "
    "three-quarter aerial view. Keep every wall, corridor, opening, junction and "
    "dead-end in the SAME position and proportion, corridors uniformly WIDE and walls "
    "THIN, and the green start tile and the red end tile exactly where they are, so the "
    "maze stays solvable. Do NOT add, remove, merge, move, narrow, pinch or close any "
    "wall or corridor. Keep the SAME materials, surface colours, textures, props and "
    "lighting as the reference. Keep the walls LOW and use a STEEP, high three-quarter "
    "angle so the wide corridors and the whole route from the green tile to the red "
    "tile stay visible rather than hidden behind wall height. No characters, labels, "
    "UI, borders or watermark."
)


def maze_topdown(scene: str) -> str:
    """The top-down drawn straight from the carved blueprint."""
    return ("Build a clean straight-overhead TOP-DOWN (nadir) low-poly Roblox 3D scene, "
            "richly themed from this description:\n"
            f"{scene}\n" + MAZE_LAYOUT + " " + MAZE_STYLE +
            " True overhead view, no perspective, no labels or watermark.")


def maze_isometric(scene: str) -> str:
    """The isometric drawn straight from the carved blueprint, walls low and thin."""
    return ("Build a polished ISOMETRIC (three-quarter aerial) low-poly Roblox 3D scene, "
            "richly themed from this description:\n"
            f"{scene}\n" + MAZE_LAYOUT + " " + MAZE_STYLE +
            " Keep the walls LOW and THIN (height about one third of a corridor's width, "
            "footprint much thinner than the corridors) and use a STEEP, high, "
            "near-top-down three-quarter angle, so the WIDE corridors and the whole path "
            "from the green tile to the red tile stay fully visible and generously "
            "walkable, NOT hidden behind wall height or pinched narrow by perspective. "
            "No characters, labels, UI, borders, or watermark.")


# ------------------------------------------------------------ authored track layout

#: The track plan is one grey band on a dark field, so the wording has to say plainly
#: that the band is the drivable surface and the colours mean nothing - otherwise the
#: model renders a grey road on a black plain instead of taking its look from the
#: prompt.
def track_layout_text(closed: bool) -> str:
    shape = ("ONE continuous closed loop" if closed else
             "ONE continuous course that runs from one end to the other and does NOT "
             "close into a loop")
    marks = ("the GREEN line across the band marks WHERE the start/finish sits - build "
             "a real start/finish there" if closed else
             "the GREEN line across the band marks WHERE the race starts and the RED "
             "line marks WHERE it finishes - build a real starting line and a real "
             "finish line at those two ends")
    route = "loop" if closed else "course"
    return (
        "The reference image is the AUTHORED TRACK PLAN for this scene, seen from "
        "directly overhead, and it is the GROUND TRUTH for the layout. The light band "
        f"is the drivable road surface and it forms {shape}; the dark field around it "
        f"is everything that is not road; {marks} in this scene's own style, a painted "
        "or checkered line across the full road width, rather than copying a coloured "
        f"stripe. Reproduce that route EXACTLY - the same {route}, the same corners in "
        "the same places and the same directions, the same straights, the same road "
        f"width throughout, and the markings where they are. The {route} must stay "
        "continuous with no break, no dead end and no fork.")


def track_only_road_text(closed: bool) -> str:
    """Where the description's own features are allowed to go.

    Listing them is not enough: told to include boost pads and tunnels, the model
    builds each as its own object - a slab of surface on the grass, a portal in a
    hillside with an approach ramp - and those read as extra lanes and dead-end spurs
    beside the track. Each feature needs to be pinned to the track explicitly.
    """
    r = "loop" if closed else "course"
    return (
        f"That {r} is the ONLY drivable surface anywhere in the image, and it has no "
        "stub, spur or dead end of surface attached to it, however short. Everything "
        "the description asks for is realised ON it: a boost pad, arrow chevron, "
        "speed strip, jump ramp, chicane or obstacle is painted or built flush INTO "
        f"the {r}'s own surface where the {r} runs, never as a separate slab, apron, "
        f"platform or approach laid on the ground beside it. A tunnel exists only "
        f"where the {r} itself passes through a hill and comes out the other side - do "
        "NOT build a tunnel mouth, cave entrance, gate or arch that the track does not "
        f"run through. A bridge is a stretch of the {r} crossing water. Do NOT lay any "
        "extra road, spur, shortcut, slip road, pit lane, service track, parallel "
        "carriageway or second track, and leave the ground on either side of the "
        f"{r} free of drivable surface entirely.")


TRACK_BRIDGE = (
    " The plan shows the road passing over itself, drawn as a break in the lower road: "
    "build exactly that as a real bridge or overpass with clear headroom, not as a "
    "flat crossroads."
)

#: A game map is exactly what this model likes to draw as a tilted diorama, and one
#: closing sentence asking for an overhead view loses to that prior: the render comes
#: back with tree trunks, cliff faces and a tunnel arch all visible, which is a shallow
#: isometric wearing a top-down label. The Stage B wrapper already had wording strong
#: enough to hold the camera down, so the track plan uses the same kind of language.
TRACK_NADIR = (
    "CAMERA: straight down at 90 degrees, a true nadir view, with ZERO perspective and "
    "ZERO isometric tilt. Show ONLY the tops of things - the road surface, tree "
    "canopies, roofs - and NO side faces of any kind: no building walls, no tree "
    "trunks, no cliff or rock faces, no visible tunnel arch, no vertical surface "
    "anywhere. Objects at the edges of the image are seen from directly above exactly "
    "as those in the middle are, with no lean or splay."
)

TRACK_STYLE = (
    "Do NOT copy the grey and dark colours of the reference - it encodes the route "
    "only. Take the materials, surface colours, textures, lighting and mood entirely "
    "from the scene description above, and dress the surroundings with its named props "
    "and scenery. Barriers, kerbs, stands, trees, buildings and scenery sit BESIDE the "
    "road and never on it: the full width of the track stays clear and drivable end to "
    "end."
)


def track_topdown(scene: str, crossings: int = 0, closed: bool = True) -> str:
    """The bridge clause only appears when the plan actually has a crossing.

    Mentioning bridges unconditionally invites one even on a plan with no crossing at
    all, and a bridge the plan does not have needs road the plan does not have either.
    """
    return ("Build a clean straight-overhead TOP-DOWN (nadir) low-poly Roblox 3D "
            "scene, richly themed from this description:\n"
            f"{scene}\n" + track_layout_text(closed)
            + (TRACK_BRIDGE if crossings else "") + " "
            + track_only_road_text(closed) + " " + TRACK_STYLE + " " + TRACK_NADIR +
            " No labels, UI, borders or watermark.")


def track_isometric(crossings: int = 0, closed: bool = True) -> str:
    r = "loop" if closed else "course"
    return (
        "The reference image is a true overhead top-down view of this scene and it is "
        "the GROUND TRUTH for the layout. Rebuild the SAME scene as a polished "
        f"isometric three-quarter aerial view. Keep the racing {r} EXACTLY as it is - "
        + ("the same closed circuit" if closed else
           "the same course from the same start to the same finish") +
        ", the same corners in the same places, the same straights, the same road "
        "width and the same start and finish positions"
        + (", and any bridge or overpass still crossing where it crosses"
           if crossings else "") +
        ". Do NOT add, remove, move, narrow or close any part of the track. The "
        f"{r} stays the only road in the image: no extra road, spur, shortcut or "
        "second track. Keep the SAME materials, surface colours, textures, props and "
        "lighting as the reference. CAMERA: this is the one thing that changes. The "
        "reference looks straight down; tilt to a true three-quarter aerial view of "
        "about 45 degrees and rotate it, so the scene reads as a 3D diorama rather "
        "than a flat plan. Side faces MUST now be visible - tree trunks under their "
        "canopies, the walls of buildings, the face of any tunnel mouth, the thickness "
        "of the ground - and the far side of the scene sits higher in the frame than "
        f"the near side. Keep the angle steep enough that the whole {r} stays visible "
        "end to end rather than hidden behind scenery. No characters, labels, UI, "
        "borders or watermark.")
