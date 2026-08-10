"""Smooth the evolved polyline, and keep a road of a given width from touching itself.

Taken from racetrack-py's `finalize_render.py`, minus its renderer: this repo draws
the band with `layoutgen.layouts.track`, which also has to place a start line and
break a road at a bridge, so only the geometry half is wanted here.

`relax_offsets` is the part that earns its place. The optimizer guarantees a curve
that does not cross itself, which is not the same as a *road* that does not touch
itself: give a tight hairpin a wide enough carriageway and the two sides merge into a
blob, and the plan stops reading as a route. Relaxing until the offset rails come
apart is what keeps the corridor legible at whatever width the caller draws.
"""

from __future__ import annotations

import numpy as np
from numba import njit
from scipy.interpolate import splev, splprep


def finalize(polyline, spacing=0.2):
    """Smooth the closed polyline with a periodic cubic spline and resample it to an
    even arc-length spacing. Returns (m, 2) points."""
    P = np.asarray(polyline, dtype=float)
    tck, _ = splprep([P[:, 0], P[:, 1]], s=0, per=1, k=3)
    dense = np.array(splev(np.linspace(0, 1, 4000, endpoint=False), tck)).T
    return _resample_even(dense, spacing)


def _resample_even(dense, spacing):
    d = np.roll(dense, -1, axis=0) - dense
    seg = np.hypot(d[:, 0], d[:, 1])
    total = seg.sum()
    n = max(8, round(total / spacing))
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    targets = np.linspace(0, total, n, endpoint=False)
    idx = np.clip(np.searchsorted(cum, targets, side="right") - 1, 0, len(dense) - 1)
    t = (targets - cum[idx]) / np.where(seg[idx] > 1e-12, seg[idx], 1.0)
    nxt = (idx + 1) % len(dense)
    return dense[idx] + (dense[nxt] - dense[idx]) * t[:, None]


def offset_curves(pts, dist):
    """The two rails a road of half-width `dist` would have."""
    pts = np.asarray(pts, dtype=float)
    t = np.roll(pts, -1, axis=0) - np.roll(pts, 1, axis=0)
    m = np.hypot(t[:, 0], t[:, 1])
    m[m == 0] = 1.0
    normal = np.column_stack([-t[:, 1] / m, t[:, 0] / m])
    return pts + normal * dist, pts - normal * dist


@njit(cache=True, inline="always")
def _ccw(px, py, qx, qy, rx, ry):
    return (ry - py) * (qx - px) > (qy - py) * (rx - px)


@njit(cache=True)
def _seg_cross(ax, ay, bx, by, cx, cy, dx, dy):
    return (_ccw(ax, ay, cx, cy, dx, dy) != _ccw(bx, by, cx, cy, dx, dy) and
            _ccw(ax, ay, bx, by, cx, cy) != _ccw(ax, ay, bx, by, dx, dy))


@njit(cache=True)
def _self_intersects(pts):
    n = pts.shape[0]
    for i in range(n):
        ax = pts[i, 0]; ay = pts[i, 1]
        i1 = (i + 1) % n
        bx = pts[i1, 0]; by = pts[i1, 1]
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            j1 = (j + 1) % n
            if _seg_cross(ax, ay, bx, by, pts[j, 0], pts[j, 1], pts[j1, 0], pts[j1, 1]):
                return True
    return False


@njit(cache=True)
def _polys_cross(A, B):
    na = A.shape[0]; nb = B.shape[0]
    for i in range(na):
        ax = A[i, 0]; ay = A[i, 1]
        i1 = (i + 1) % na
        bx = A[i1, 0]; by = A[i1, 1]
        for j in range(nb):
            j1 = (j + 1) % nb
            if _seg_cross(ax, ay, bx, by, B[j, 0], B[j, 1], B[j1, 0], B[j1, 1]):
                return True
    return False


def _overlap(left, right):
    return (_self_intersects(np.ascontiguousarray(left))
            or _self_intersects(np.ascontiguousarray(right))
            or _polys_cross(np.ascontiguousarray(left), np.ascontiguousarray(right)))


def _laplacian_smooth_closed(pts, alpha, iterations):
    cur = pts.copy()
    for _ in range(iterations):
        target = (np.roll(cur, 2, axis=0) + np.roll(cur, 1, axis=0)
                  + np.roll(cur, -1, axis=0) + np.roll(cur, -2, axis=0)) / 4.0
        cur = cur + alpha * (target - cur)
    return cur


def relax_offsets(resampled, dist, rounds_max=20):
    """Smooth the centreline until a road of half-width `dist` stops touching itself.

    Returns (curve, rounds). Rounds is worth having back: it says how much of the
    shape the width cost, and a caller asking for a road too wide for its own
    hairpins will see it climb to the limit.
    """
    curve = np.asarray(resampled, dtype=float)
    if not _overlap(*offset_curves(curve, dist)):
        return curve, 0
    curve = curve[::2]
    rounds = 0
    while rounds < rounds_max:
        if not _overlap(*offset_curves(curve, dist)):
            break
        curve = _laplacian_smooth_closed(curve, 1.0, 5)
        rounds += 1
    return curve, rounds
