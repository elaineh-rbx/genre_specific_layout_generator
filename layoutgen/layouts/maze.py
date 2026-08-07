"""Generate a guaranteed-solvable maze BLUEPRINT to use as a reference image.

This is the robust answer to "is the maze solvable?": don't try to perceive it
from a render, *author* it. We carve a perfect maze (recursive backtracker -
exactly one path between any two cells, so solvable by construction), keep the
occupancy grid as the source of truth, compute the exact solution from that grid,
and draw a clean high-contrast blueprint. The blueprint then conditions the 3D
image generation (see render_from_blueprint.py); because we still hold the
authored grid, verification later is a drift check, not a fragile re-segmentation.

Outputs (in --out):
  blueprint.png   clean top-down maze (dark walls, light floor, green/red tiles)
  solution.png    blueprint with the guaranteed shortest path drawn
  grid.npy        occupancy grid, shape (2N+1, 2N+1): True = wall  (ground truth)
  grid.txt        same grid as ASCII ('#' wall, ' ' floor, 'S' start, 'E' end)
  meta.json       cells, seed, start/end cells + pixels, path length, pitch

    python -m layoutgen.layouts.maze --cells 20 --seed 7 --out /tmp/bp20
"""

from __future__ import annotations

import argparse
import json
import random
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

# palette (kept distinct by *fill* colour, not just outline, so a render/segmenter
# can tell wall from floor without relying on thin edges)
FLOOR = (210, 210, 210)
WALL = (60, 64, 70)
START = (46, 184, 74)
END = (222, 46, 46)
PATH = (255, 202, 40)

N, S, E, W = 1, 2, 4, 8
_DX = {E: 1, W: -1, N: 0, S: 0}
_DY = {E: 0, W: 0, N: -1, S: 1}
_OPP = {N: S, S: N, E: W, W: E}


def carve(n: int, seed: int) -> list[list[int]]:
    """Recursive-backtracker perfect maze; per-cell OPEN-direction bit flags."""
    rng = random.Random(seed)
    open_dirs = [[0] * n for _ in range(n)]
    visited = [[False] * n for _ in range(n)]
    stack = [(0, 0)]
    visited[0][0] = True
    while stack:
        x, y = stack[-1]
        nbrs = [
            (d, x + _DX[d], y + _DY[d])
            for d in (N, S, E, W)
            if 0 <= x + _DX[d] < n and 0 <= y + _DY[d] < n and not visited[y + _DY[d]][x + _DX[d]]
        ]
        if not nbrs:
            stack.pop()
            continue
        d, nx, ny = rng.choice(nbrs)
        open_dirs[y][x] |= d
        open_dirs[ny][nx] |= _OPP[d]
        visited[ny][nx] = True
        stack.append((nx, ny))
    return open_dirs


def occupancy(open_dirs, start_cell, end_cell) -> np.ndarray:
    """(2N+1, 2N+1) bool wall grid. Cells at odd indices; walls between/around.

    The two edge openings for start/end are carved into the outer border.
    """
    n = len(open_dirs)
    g = np.ones((2 * n + 1, 2 * n + 1), dtype=bool)  # all wall
    for r in range(n):
        for c in range(n):
            g[2 * r + 1, 2 * c + 1] = False           # cell centre = floor
            if open_dirs[r][c] & E:
                g[2 * r + 1, 2 * c + 2] = False       # open passage east
            if open_dirs[r][c] & S:
                g[2 * r + 2, 2 * c + 1] = False       # open passage south
    # edge openings so start/end touch the outside border
    (sc, sr), (ec, er) = start_cell, end_cell
    for (col, row) in ((sc, sr), (ec, er)):
        gr, gc = 2 * row + 1, 2 * col + 1
        if row == 0:
            g[0, gc] = False
        elif row == n - 1:
            g[-1, gc] = False
        if col == 0:
            g[gr, 0] = False
        elif col == n - 1:
            g[gr, -1] = False
    return g


def solve_cells(open_dirs, start_cell, end_cell) -> list[tuple[int, int]]:
    """Shortest path (list of (col,row) cells) on the maze graph. Always exists."""
    sc, ec = start_cell, end_cell
    prev = {sc: None}
    q = deque([sc])
    while q:
        cur = q.popleft()
        if cur == ec:
            break
        col, row = cur
        for d in (N, S, E, W):
            if open_dirs[row][col] & d:
                nc = (col + _DX[d], row + _DY[d])
                if nc not in prev:
                    prev[nc] = cur
                    q.append(nc)
    path = []
    cur = ec
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    return path[::-1]


def render(open_dirs, occ, start_cell, end_cell, *, cell=26, wall=10):
    """Draw the blueprint from the occupancy grid; return (img, geom)."""
    n = len(open_dirs)
    unit_c, unit_w = cell, wall
    # pixel span of grid index i: walls are the even indices, cells the odd.
    spans = []  # (start_px, size) per grid index
    pos = 0
    for i in range(2 * n + 1):
        sz = unit_w if i % 2 == 0 else unit_c
        spans.append((pos, sz))
        pos += sz
    total = pos
    img = Image.new("RGB", (total, total), FLOOR)
    draw = ImageDraw.Draw(img)
    for gi in range(2 * n + 1):
        y0, hh = spans[gi]
        for gj in range(2 * n + 1):
            if occ[gi, gj]:
                x0, ww = spans[gj]
                draw.rectangle([x0, y0, x0 + ww - 1, y0 + hh - 1], fill=WALL)

    def cell_px(col, row):
        x0, ww = spans[2 * col + 1]
        y0, hh = spans[2 * row + 1]
        return x0, y0, ww, hh

    def tile(cellrc, color):
        col, row = cellrc
        x0, y0, ww, hh = cell_px(col, row)
        pad = 2
        draw.rectangle([x0 + pad, y0 + pad, x0 + ww - 1 - pad, y0 + hh - 1 - pad], fill=color)
        return int(x0 + ww / 2), int(y0 + hh / 2)

    start_px = tile(start_cell, START)
    end_px = tile(end_cell, END)
    geom = {"total": total, "cell": unit_c, "wall": unit_w, "spans": spans,
            "start_px": start_px, "end_px": end_px, "cell_px": cell_px}
    return img, geom


def draw_solution(img, geom, path):
    out = img.copy()
    draw = ImageDraw.Draw(out)
    pts = []
    for (col, row) in path:
        x0, y0, ww, hh = geom["cell_px"](col, row)
        pts.append((int(x0 + ww / 2), int(y0 + hh / 2)))
    if len(pts) >= 2:
        draw.line(pts, fill=(0, 0, 0), width=6, joint="curve")
        draw.line(pts, fill=PATH, width=3, joint="curve")
    return out


def grid_to_ascii(occ, start_cell, end_cell) -> str:
    chars = np.where(occ, "#", " ").astype("<U1")
    (sc, sr), (ec, er) = start_cell, end_cell
    chars[2 * sr + 1, 2 * sc + 1] = "S"
    chars[2 * er + 1, 2 * ec + 1] = "E"
    return "\n".join("".join(row) for row in chars)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cells", type=int, default=20, help="Maze cells per side.")
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--cell", type=int, default=26, help="Floor cell size (px).")
    ap.add_argument("--wall", type=int, default=10, help="Wall thickness (px).")
    ap.add_argument("--start", type=int, nargs=2, metavar=("COL", "ROW"), default=None)
    ap.add_argument("--end", type=int, nargs=2, metavar=("COL", "ROW"), default=None)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "blueprint")
    args = ap.parse_args()
    n = args.cells
    args.out.mkdir(parents=True, exist_ok=True)

    start_cell = tuple(args.start) if args.start else (n // 2, 0)
    end_cell = tuple(args.end) if args.end else (n // 2, n - 1)

    open_dirs = carve(n, args.seed)
    occ = occupancy(open_dirs, start_cell, end_cell)
    path = solve_cells(open_dirs, start_cell, end_cell)
    img, geom = render(open_dirs, occ, start_cell, end_cell, cell=args.cell, wall=args.wall)
    sol = draw_solution(img, geom, path)

    bp = args.out / "blueprint.png"
    img.save(bp, format="PNG")
    sol.save(args.out / "solution.png", format="PNG")
    np.save(args.out / "grid.npy", occ)
    (args.out / "grid.txt").write_text(grid_to_ascii(occ, start_cell, end_cell), encoding="utf-8")
    meta = {
        "cells": n, "seed": args.seed, "size_px": geom["total"],
        "cell_px": args.cell, "wall_px": args.wall,
        "start_cell": list(start_cell), "end_cell": list(end_cell),
        "start_px": list(geom["start_px"]), "end_px": list(geom["end_px"]),
        "path_len_cells": len(path), "grid_shape": list(occ.shape),
        "wall_fraction": round(float(occ.mean()), 3),
    }
    (args.out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"cells={n} seed={args.seed}  image={geom['total']}x{geom['total']}px  "
          f"grid={occ.shape[0]}x{occ.shape[1]}")
    print(f"solvable by construction: path length = {len(path)} cells")
    print(f"start(green) cell={start_cell} px={geom['start_px']}  "
          f"end(red) cell={end_cell} px={geom['end_px']}")
    print(f"wrote: {bp}")
    print(f"       {args.out/'solution.png'}")
    print(f"       {args.out/'grid.npy'}  {args.out/'grid.txt'}  {args.out/'meta.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
