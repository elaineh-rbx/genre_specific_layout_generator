"""A closed loop that folds back on itself, grown by repelling a curve from itself.

Ported from rschmidt/trackgen @ `69dfd36` (`racetrack-py/`), which is itself a port
of that repo's JavaScript web app. The method is repulsive curves: a blobby seed is
contoured out of three metaballs, boxes are packed around it, and then tangent-point
energy is minimised under a Sobolev-Slobodeckij preconditioner with barycenter and
length constraints, so the curve lengthens while pushing away from itself and from
the boxes. What comes out is a single closed circuit that weaves through the plane in
long parallel corridors and hairpins.

Why it is here at all: `layoutgen.layouts.track` used to place control points at
strictly increasing angles around a centre, which makes a simple polygon by
construction - and also makes a radial blob by construction, because a curve whose
points are angle-sorted can never double back. Every circuit came out an oval with
dents. This produces the folded, maze-like loop instead, and still guarantees the
one property Build.md's P6 route actually asks of a racing layout: one continuous
connected route with no broken or ambiguously self-crossing segments.

What is used from upstream, and what is not: `rng`, `shapes`, `blob`, `boundaries`,
`kernels` and `optimizer` are theirs, copied with only their imports made relative so
they can be diffed against upstream later. `finalize` keeps the geometry half of
their `finalize_render` and drops the renderer, because this repo draws the band
itself - it has a start line to place and a bridge to break. Their `generate.py`
driver is replaced by `centreline()` below, which returns points rather than a PNG.

    python -m layoutgen.layouts.repulsive --seed 23 --steps 200
"""

from __future__ import annotations

import numpy as np

from .boundaries import generate_boundaries
from .finalize import _overlap, finalize, offset_curves, relax_offsets
from .optimizer import EnergyCurve

__all__ = ["EnergyCurve", "centreline", "finalize", "fits_road",
           "generate_boundaries", "offset_curves", "relax_offsets", "span"]

#: Upstream's automatic mode, and the units everything here is expressed in. The seed
#: curve is grown to `target_length_scale` times its own length, so the world span
#: stays roughly fixed however long the road gets - which is what makes a fixed step
#: count mean the same thing from one seed to the next.
RADIUS = 10.0
NUM_POINTS = 100


def span(pts) -> float:
    """The longer side of the loop's bounding box - what a canvas fit scales to."""
    P = np.asarray(pts, dtype=float)
    return float(max(np.ptp(P[:, 0]), np.ptp(P[:, 1]))) or 1.0


def fits_road(pts, half_width: float) -> bool:
    """Whether a road of this half-width can be drawn on this loop without touching.

    The offsets are the honest test. A centreline that does not cross itself says
    nothing about the road hung on it: two corridors passing a road's width apart
    merge into one piece of tarmac, and the plan stops reading as a route. Sampling
    down to a few hundred points first keeps the pairwise test cheap enough to run on
    every step of the evolution, which is the point of having it.
    """
    P = np.asarray(pts, dtype=float)
    P = np.ascontiguousarray(P[::max(1, len(P) // 400)])
    return not _overlap(*offset_curves(P, half_width))


def centreline(seed: int, steps: int, spacing: float = 0.2,
               road_half: float = 0.0):
    """Evolve one loop and return it as an (m, 2) array of points, unrendered.

    `road_half` is the useful dial: half the width of the road that will be drawn on
    this loop, as a fraction of the loop's own bounding span. The loop folds tighter
    the longer it runs, and left alone it folds tighter than a road of any fixed width
    can survive; keeping the last shape the road still fits grows the most folded
    circuit that stays legible, which a fixed step count cannot do - the same number
    is too few for one seed and far too many for the next.

    The keep-the-last-good rule matters more than it looks. Room for the road does not
    fall away steadily: a step that pulls two corridors together is often followed by
    one that pushes them apart again, so stopping at the first step that does not fit
    abandons the run around a tenth of the way in, and hands back a curve barely more
    folded than the blob it started as.

    Stops early on two conditions upstream also stops on: the optimizer settling, and
    the curve reaching a box it did not start on. The second is what keeps a long run
    from pressing the loop flat against its own boundary once there is nowhere left
    to grow.
    """
    _, boxes = generate_boundaries(seed, RADIUS, NUM_POINTS)
    ec = EnergyCurve(seed, RADIUS, NUM_POINTS, boxes)
    watched = ec.watched_boxes()
    kept = finalize(ec.polyline, spacing)
    for _ in range(max(1, int(steps))):
        ec.step()
        cur = finalize(ec.polyline, spacing)
        if not road_half or fits_road(cur, road_half * span(cur)):
            kept = cur
        if ec.done or ec.intruded(watched):
            break
    return kept


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=23)
    ap.add_argument("--steps", type=int, default=200)
    a = ap.parse_args()
    pts = centreline(a.seed, a.steps)
    span = pts.max(axis=0) - pts.min(axis=0)
    print(f"seed {a.seed}  {a.steps} steps  {len(pts)} points  "
          f"span {span[0]:.1f} x {span[1]:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
