"""Port of the automatic-mode boundary generator in racetrack-js/web/main.js
(`regenerateBoundaries`).

Lays a GRID x GRID grid over a box twice the blob-seed bounds, reserves the
cells the curve passes through (plus their 8 neighbours), then randomly packs
axis-aligned rectangles (>=2x2 cells, clamped to not overlap) until ~80% of the
grid is allocated. Each rectangle becomes a rounded-rect obstacle. RNG call
order matches the JS so a seed reproduces the same boxes.
"""

import math
import numpy as np

from .rng import Rng
from .blob import generate_blob_seed

GRID = 25
FILL_TARGET = 0.8
MAX_BOX_CELLS = 10
BOX_INSET = 0.12


def generate_boundaries(seed, radius=10.0, num_points=100):
    """Return (blob_pts (N,2), boxes) where each box is a dict
    {type:'roundrect', x, y, w, h, r} in world coordinates."""
    pts = generate_blob_seed(seed, radius, num_points)
    minX = pts[:, 0].min(); maxX = pts[:, 0].max()
    minY = pts[:, 1].min(); maxY = pts[:, 1].max()
    W = maxX - minX; H = maxY - minY
    cx = (minX + maxX) / 2.0; cy = (minY + maxY) / 2.0

    csx = (2 * W) / GRID
    csy = (2 * H) / GRID
    originX = cx - W
    originY = cy - H

    rng = Rng(((seed & 0xFFFFFFFF) * 2654435761 & 0xFFFFFFFF) ^ 0x5F3759DF)
    alloc = np.zeros((GRID, GRID), dtype=bool)  # alloc[y][x]

    # Reserve the corridor around the curve (cell + 8 neighbours).
    filled = 0
    for px, py in pts:
        gx = int(math.floor((px - originX) / csx))
        gy = int(math.floor((py - originY) / csy))
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                x = gx + dx; y = gy + dy
                if x < 0 or x >= GRID or y < 0 or y >= GRID:
                    continue
                if not alloc[y, x]:
                    alloc[y, x] = True
                    filled += 1

    def try_place(gx, gy, dw, dh):
        w = 0
        while w < dw and gx + w < GRID and not alloc[gy, gx + w]:
            w += 1
        if w < 2:
            return None
        h = 0
        while h < dh and gy + h < GRID:
            row_blocked = False
            for c in range(gx, gx + w):
                if alloc[gy + h, c]:
                    row_blocked = True
                    break
            if row_blocked:
                break
            h += 1
        if h < 2:
            return None
        alloc[gy:gy + h, gx:gx + w] = True
        return (gx, gy, w, h)

    boxes_cells = []
    target = int(math.floor(GRID * GRID * FILL_TARGET))
    attempts = 0
    while filled < target and attempts < 8000:
        attempts += 1
        gx = int(math.floor(rng.next() * GRID))
        gy = int(math.floor(rng.next() * GRID))
        if alloc[gy, gx]:
            continue
        dw = 2 + int(math.floor(rng.next() * (MAX_BOX_CELLS - 1)))
        dh = 2 + int(math.floor(rng.next() * (MAX_BOX_CELLS - 1)))
        b = try_place(gx, gy, dw, dh)
        if b:
            boxes_cells.append(b)
            filled += b[2] * b[3]

    inset = BOX_INSET * min(csx, csy)
    boxes = []
    for (gx, gy, w, h) in boxes_cells:
        bw = w * csx - 2 * inset
        bh = h * csy - 2 * inset
        boxes.append({
            'type': 'roundrect',
            'x': originX + (gx + w / 2.0) * csx,
            'y': originY + (gy + h / 2.0) * csy,
            'w': bw, 'h': bh, 'r': min(bw, bh) * 0.2,
        })
    return pts, boxes
