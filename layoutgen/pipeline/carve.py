"""Author a layout outright, and check afterwards whether the render kept it.

Some shapes are the game: a maze is its topology, a circuit is its route. Asking an
image model for one and hoping is not the same as generating one and making the model
draw it, so those shapes are carved here first and handed to the image model as a
reference.

The masks the carve produces are kept, which is what makes the check possible: tint
the intended walls or route over the render and it is immediately obvious whether the
model followed the plan or drew something that merely resembles it.
"""

from __future__ import annotations

import pathlib
from concurrent.futures import ThreadPoolExecutor

from layoutgen.layouts import maze as bp
from layoutgen.layouts import track as tg
from layoutgen.paths import OUT

#: Where a maze can be authored outright instead of drawn. Build.md routes these
#: P6 - the topology is the game, so it is generated procedurally first and dressed
#: after. Only the maze generator exists today; the track, lane, course and chunk
#: generators the other P6 routes call for are unbuilt.
#: Scoped by genre, because the generator carves a *perfect* maze - one route from a
#: start to an end - and a shared ID does not mean the same thing everywhere.
#: `obstacle-maze` is a routed maze in Obby ("a maze the player has to route through"),
#: but in Party it is "a warren of rooms and corridors to hide and be hunted in", which
#: has no start and no end and wants loops rather than a single solution.
MAZE_SHAPES = {("Puzzle", "puzzle-maze")}
MAZE_OPTIONS = {("Obby & Platformer", "obstacle-maze")}

#: Racing shapes whose route can be authored as a closed loop instead of drawn.
#: Build.md routes all of Racing P6 for exactly this reason - the track has to read as
#: one connected route with no ambiguous self-crossings, which a free image cannot
#: promise. `route-multitier` is the same loop with a crossing that a bridge resolves.
TRACK_SHAPES = {
    ("Racing", "route-circuit"): {"closed": True, "crossings": 0},
    ("Racing", "route-multitier"): {"closed": True, "crossings": 1},
    ("Racing", "route-point-to-point"): {"closed": False, "crossings": 0},
}

ROUTE_TINT = (40, 230, 120)

_jobs: dict[str, dict] = {}
#: What each job was asked for, kept aside from the job itself so it is not sent
#: back on every poll. A card built from a run needs the picks the run used.
_specs: dict[str, dict] = {}
_cards: dict[str, dict] = {}
_pool = ThreadPoolExecutor(max_workers=3)


# ---------------------------------------------------------------- prompt assembly

def carve_layout(cells: int, seed: int) -> dict:
    """Author a guaranteed-solvable maze and draw it as a blueprint.

    Perfect maze via recursive backtracker: exactly one path between any two cells,
    so it is solvable by construction and the shortest route is known exactly rather
    than re-derived from pixels later.
    """
    cells = max(4, min(28, int(cells)))
    open_dirs = bp.carve(cells, int(seed))
    start, end = (0, 0), (cells - 1, cells - 1)
    occ = bp.occupancy(open_dirs, start, end)
    img, geom = bp.render(open_dirs, occ, start, end)
    path = bp.solve_cells(open_dirs, start, end)
    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"maze_{cells}_{seed}"
    plan, sol = OUT / f"{stem}.png", OUT / f"{stem}_solved.png"
    img.save(plan)
    bp.draw_solution(img, geom, path).save(sol)
    return {"layout": plan.name, "solution": sol.name, "cells": cells, "seed": int(seed),
            "steps": len(path), "kind": "maze",
            "masks": {"plan": _wall_mask(img), "solution": _path_mask(img, geom, path)}}


def _wall_mask(img):
    """Where the walls stand, at the blueprint's own resolution.

    Built from the drawn blueprint rather than from the occupancy grid: the grid gives
    every index the same width, but the blueprint draws walls thin and corridors wide,
    so a grid-sized mask stretched over a render drifts out of step with it.
    """
    import numpy as np
    from PIL import Image
    return Image.fromarray(
        ((np.array(img.convert("L")) < 110) * 255).astype("uint8"), "L")


def _path_mask(img, geom, path):
    """The solved route, as a band down the middle of the corridors it runs through."""
    from PIL import Image, ImageDraw
    m = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(m)
    pts = []
    for col, row in path:
        x0, y0, w, h = geom["cell_px"](col, row)
        pts.append((int(x0 + w / 2), int(y0 + h / 2)))
    if len(pts) >= 2:
        d.line(pts, fill=255, width=max(4, int(pts and geom["cell_px"](0, 0)[2] * 0.5)),
               joint="curve")
    return m


def carve_track(complexity: int, seed: int, crossings: int = 0,
                closed: bool = True) -> dict:
    """Author a racing route and draw it as a blueprint.

    The maze equivalent guarantees solvability; this guarantees the property Racing's
    genre route actually asks for - one continuous connected route with no broken or
    ambiguous segments - because a circuit's control points are angle-sorted and a
    course's traverses each stay in their own band, and smoothing preserves both.
    """
    import numpy as np
    t = tg.generate(seed=int(seed), complexity=int(complexity), size=1024,
                    crossings=int(crossings), closed=closed)
    OUT.mkdir(parents=True, exist_ok=True)
    stem = (f"track_{'loop' if closed else 'route'}_{t['complexity']}_{t['seed']}"
            f"_{t['crossings']}")
    plan = OUT / f"{stem}.png"
    t["image"].save(plan)
    # The road mask, so `overlay` can tint the authored route over a render and show
    # whether it was kept. The maze's equivalent marks walls; here it marks tarmac.
    from PIL import Image
    road = Image.fromarray(
        ((np.array(t["image"].convert("L")) > 90) * 255).astype("uint8"), "L")
    return {"layout": plan.name, "solution": plan.name, "kind": "track",
            "cells": t["complexity"], "seed": t["seed"],
            "masks": {"plan": road, "solution": None},
            # Which generator drew it. Two are in play and they do not look alike, so
            # a caller comparing one carve against another wants to be told rather
            # than left to infer it from the picture.
            "method": t["method"],
            "closed": closed, "crossings": t["crossings"], "steps": t["length"]}


def track_params(genre_name: str, shape_id: str) -> dict:
    return TRACK_SHAPES.get((genre_name, shape_id), {"closed": True, "crossings": 0})


def carve(spec: dict) -> dict:
    """Whichever authored layout this configuration calls for."""
    if spec.get("kind") == "track":
        p = track_params(spec.get("genre", ""), spec.get("shape") or "")
        return carve_track(spec.get("cells", 13), spec.get("seed", 7),
                           spec.get("crossings", p["crossings"]),
                           closed=spec.get("closed", p["closed"]))
    lay = carve_layout(spec.get("cells", 12), spec.get("seed", 7))
    lay["kind"] = "maze"
    return lay


def layout_kind(genre_name: str, shape_id: str, option_ids) -> str | None:
    """`maze`, `track`, or None when nothing here can be authored outright."""
    if (genre_name, shape_id) in TRACK_SHAPES:
        return "track"
    if ((genre_name, shape_id) in MAZE_SHAPES
            or any((genre_name, o) in MAZE_OPTIONS for o in option_ids or ())):
        return "maze"
    return None


def overlay(base_png: pathlib.Path, mask, dest: pathlib.Path,
            colour=(255, 0, 190), alpha: float = 0.45) -> None:
    """Tint an authored mask over a render, to see whether it kept the plan."""
    from PIL import Image
    base = Image.open(base_png).convert("RGB")
    m = mask.resize(base.size, Image.BILINEAR).point(lambda v: 255 if v > 127 else 0)
    tint = Image.new("RGB", base.size, colour)
    Image.composite(Image.blend(base, tint, alpha), base, m).save(dest)
