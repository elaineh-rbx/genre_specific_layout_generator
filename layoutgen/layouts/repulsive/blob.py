"""Port of racetrack-js/src/blobSeed.js — the metaball-blend seed curve.

Three jittered metaballs (a random equilateral triangle), contoured with
marching squares; the largest loop, resampled to `num_points` and rescaled so
the mean vertex radius is 1.875x `radius` (matching the JS `targetR`).

The marching-squares cell scan order, edge-id stitching and loop-walk mirror the
JS exactly (Python dicts preserve insertion order like JS Map), so a given seed
reproduces the same blob as the web app's automatic mode.
"""

import math
import numpy as np

from .rng import Rng

ISO = 1.0
TARGET_SCALE = 1.875  # mean vertex radius = TARGET_SCALE * radius (JS blobSeed)


def _build_balls(rng, radius):
    circum = radius * 0.9
    side = circum * math.sqrt(3.0)
    rot = rng.range(0.0, 2 * math.pi)
    balls = []
    for i in range(3):
        a = rot + (i / 3.0) * 2 * math.pi
        cx = math.cos(a) * circum
        cy = math.sin(a) * circum
        off = rng.range(0.0, 0.5 * side)
        oa = rng.range(0.0, 2 * math.pi)
        cx += math.cos(oa) * off
        cy += math.sin(oa) * off
        r = rng.range(0.6, 0.95) * radius
        balls.append((cx, cy, r, r * r))
    return balls


def _field_minus_iso(px, py, balls):
    s = 0.0
    for cx, cy, _r, r2 in balls:
        dx = px - cx
        dy = py - cy
        s += r2 / (dx * dx + dy * dy + 1e-9)
    return s - ISO


def _lerp(ax, ay, bx, by, fa, fb):
    t = 0.5 if abs(fa - fb) < 1e-12 else fa / (fa - fb)
    return (ax + t * (bx - ax), ay + t * (by - ay))


def _contour(balls, x0, y0, dx, dy, nx, ny):
    # Field-minus-iso at every grid node.
    xs = x0 + np.arange(nx + 1) * dx
    ys = y0 + np.arange(ny + 1) * dy
    gx, gy = np.meshgrid(xs, ys)  # shape (ny+1, nx+1)
    V = np.zeros_like(gx)
    for cx, cy, _r, r2 in balls:
        V += r2 / ((gx - cx) ** 2 + (gy - cy) ** 2 + 1e-9)
    V -= ISO

    def at(i, j):
        return V[j, i]

    def pt(i, j):
        return (x0 + i * dx, y0 + j * dy)

    points = {}
    adj = {}

    def link(a, b):
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)

    for j in range(ny):
        for i in range(nx):
            f00 = at(i, j); f10 = at(i + 1, j)
            f11 = at(i + 1, j + 1); f01 = at(i, j + 1)
            in00 = f00 >= 0; in10 = f10 >= 0
            in11 = f11 >= 0; in01 = f01 >= 0

            crossed = []
            if in00 != in10:  # bottom
                idb = f"h{i}_{j}"
                p0 = pt(i, j); p1 = pt(i + 1, j)
                points[idb] = _lerp(p0[0], p0[1], p1[0], p1[1], f00, f10)
                crossed.append(idb)
            if in10 != in11:  # right
                idr = f"v{i + 1}_{j}"
                p0 = pt(i + 1, j); p1 = pt(i + 1, j + 1)
                points[idr] = _lerp(p0[0], p0[1], p1[0], p1[1], f10, f11)
                crossed.append(idr)
            if in11 != in01:  # top
                idt = f"h{i}_{j + 1}"
                p0 = pt(i, j + 1); p1 = pt(i + 1, j + 1)
                points[idt] = _lerp(p0[0], p0[1], p1[0], p1[1], f01, f11)
                crossed.append(idt)
            if in01 != in00:  # left
                idl = f"v{i}_{j}"
                p0 = pt(i, j); p1 = pt(i, j + 1)
                points[idl] = _lerp(p0[0], p0[1], p1[0], p1[1], f00, f01)
                crossed.append(idl)

            if len(crossed) == 2:
                link(crossed[0], crossed[1])
            elif len(crossed) == 4:
                B, R, T, L = crossed
                center = _field_minus_iso(x0 + (i + 0.5) * dx, y0 + (j + 0.5) * dy, balls) >= 0
                if center == in00:
                    link(B, R); link(T, L)
                else:
                    link(L, B); link(R, T)

    loops = []
    visited = set()
    for start in list(adj.keys()):
        if start in visited:
            continue
        loop = []
        prev = None
        cur = start
        while cur is not None and cur not in visited:
            visited.add(cur)
            loop.append(points[cur])
            nxt = None
            for nb in adj.get(cur, ()):
                if nb != prev and nb not in visited:
                    nxt = nb
                    break
            prev = cur
            cur = nxt
        if len(loop) >= 3:
            loops.append(loop)
    return loops


def _signed_area(loop):
    a = 0.0
    n = len(loop)
    for i in range(n):
        px, py = loop[i]
        qx, qy = loop[(i + 1) % n]
        a += px * qy - qx * py
    return a / 2.0


def _resample_closed(loop, n):
    m = len(loop)
    seg = [0.0] * m
    total = 0.0
    for i in range(m):
        px, py = loop[i]
        qx, qy = loop[(i + 1) % m]
        seg[i] = math.hypot(qx - px, qy - py)
        total += seg[i]
    out = []
    step = total / n
    i = 0
    acc = 0.0
    for k in range(n):
        target = k * step
        while i < m - 1 and acc + seg[i] < target:
            acc += seg[i]
            i += 1
        t = (target - acc) / seg[i] if seg[i] > 1e-12 else 0.0
        px, py = loop[i]
        qx, qy = loop[(i + 1) % m]
        out.append((px + t * (qx - px), py + t * (qy - py)))
    return out


def generate_blob_seed(seed=0, radius=10.0, num_points=100):
    """Return the blob seed curve as an (num_points, 2) float array (CCW)."""
    rng = Rng((seed & 0xFFFFFFFF) + 1)  # +1 so seed 0 still perturbs mulberry32
    balls = _build_balls(rng, radius)

    minX = min(cx - r * 1.6 for cx, cy, r, r2 in balls)
    maxX = max(cx + r * 1.6 for cx, cy, r, r2 in balls)
    minY = min(cy - r * 1.6 for cx, cy, r, r2 in balls)
    maxY = max(cy + r * 1.6 for cx, cy, r, r2 in balls)
    pad = radius * 0.3
    minX -= pad; minY -= pad; maxX += pad; maxY += pad

    res = 150
    span = max(maxX - minX, maxY - minY)
    h = span / res
    nx = max(2, math.ceil((maxX - minX) / h))
    ny = max(2, math.ceil((maxY - minY) / h))

    loops = _contour(balls, minX, minY, h, h, nx, ny)

    if not loops:
        ang = np.linspace(0, 2 * math.pi, num_points, endpoint=False)
        r = radius * TARGET_SCALE
        return np.column_stack([np.cos(ang) * r, np.sin(ang) * r])

    best = max(loops, key=lambda lp: abs(_signed_area(lp)))
    if _signed_area(best) < 0:
        best = best[::-1]

    pts = _resample_closed(best, num_points)
    arr = np.array(pts, dtype=float)

    c = arr.mean(axis=0)
    arr -= c
    mean_r = np.hypot(arr[:, 0], arr[:, 1]).mean()
    k = (radius * TARGET_SCALE) / mean_r if mean_r > 1e-6 else 1.0
    return arr * k
