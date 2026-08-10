"""Obstacle interior samplers — port of racetrack-js/src/shapes.js.

Fills a shape's interior with point masses on a lattice (row-major scan order,
matching the JS), so a curve cutting through feels repulsion from nearby masses.
Only the roundrect (boundary boxes) and circle (bounding obstacle) are needed.
"""

import math
import numpy as np

MAX_POINTS = 350


def _js_round(x):
    # JS Math.round: round half up (toward +inf) for positive values.
    return int(math.floor(x + 0.5))


def _fill(inside, minX, minY, maxX, maxY, step):
    area = max(1e-6, (maxX - minX) * (maxY - minY))
    step = max(step, math.sqrt(area / MAX_POINTS))
    nx = max(1, _js_round((maxX - minX) / step))
    ny = max(1, _js_round((maxY - minY) / step))
    sx = (maxX - minX) / nx
    sy = (maxY - minY) / ny
    out = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = minX + i * sx
            y = minY + j * sy
            if inside(x, y):
                out.append((x, y))
    return out


def _ensure_loop(pts, cx, cy, r):
    if len(pts) >= 3:
        return pts
    out = []
    for i in range(8):
        a = (i / 8.0) * 2 * math.pi
        out.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return out


def sample_roundrect(cx, cy, w, h, r, step=1.5):
    hw = w / 2.0
    hh = h / 2.0
    r = min(r, hw, hh)

    def inside(x, y):
        dx = max(abs(x - cx) - (hw - r), 0.0)
        dy = max(abs(y - cy) - (hh - r), 0.0)
        return abs(x - cx) <= hw and abs(y - cy) <= hh and dx * dx + dy * dy <= r * r

    pts = _fill(inside, cx - hw, cy - hh, cx + hw, cy + hh, step)
    return _ensure_loop(pts, cx, cy, min(hw, hh))


def sample_circle_ring(cx, cy, r, num_points):
    # The bounding obstacle is built directly as a ring of `num_points` vertices.
    pts = []
    for i in range(num_points):
        a = (i / num_points) * 2 * math.pi
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


def point_in_shape(box, x, y):
    hw = box['w'] / 2.0
    hh = box['h'] / 2.0
    r = min(box['r'], hw, hh)
    dx = max(abs(x - box['x']) - (hw - r), 0.0)
    dy = max(abs(y - box['y']) - (hh - r), 0.0)
    return abs(x - box['x']) <= hw and abs(y - box['y']) <= hh and dx * dx + dy * dy <= r * r


def closed_polyline_masses(points):
    """avgLength (dual length) per vertex for a closed polyline — the obstacle
    'mass' each sampled point carries (matches Obstacle/CurveVertex.avgLength)."""
    P = np.asarray(points, dtype=float)
    m = len(P)
    nxt = np.roll(P, -1, axis=0)
    edge_len = np.hypot(nxt[:, 0] - P[:, 0], nxt[:, 1] - P[:, 1])  # edge e joins v e -> e+1
    prev_len = np.roll(edge_len, 1)  # edge (i-1) is prevEdge of vertex i
    return 0.5 * (prev_len + edge_len)
