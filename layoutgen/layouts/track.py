"""Author a race track the way the maze generator authors a maze: topology first.

Build.md routes every Racing shape P6 - "the track must read as one continuous
connected route, legible from plan view, with no broken or ambiguously self-crossing
segments. A free image can't guarantee that." So the loop is generated here and the
image model is handed a finished plan to dress, rather than asked to invent one.

A closed circuit's shape comes from `layoutgen.layouts.repulsive`, which grows a loop
by pushing it away from itself until it folds back into corridors and hairpins. The
angle-sorted generator it replaced could not fold at all - points at strictly
increasing angles about a centre cannot double back - so every circuit was an oval
with dents. It is still here, and still used for the two cases the folded curve
cannot serve: an open point-to-point course, and a circuit asked for a crossing.

Guaranteed by construction:
  - one continuous closed loop, from either generator
  - a road that does not touch itself: the folded curve is relaxed against the width
    it is about to be drawn at, so a hairpin cannot close up into a blob
  - no dead ends, no forks, no unreachable spurs
  - a start/finish placed on the loop
  - self-crossings only when asked for, and then drawn with a real gap so the plan
    reads as a bridge rather than as an ambiguous flat X

The blueprint is deliberately plain - one grey band on a dark field - because it
encodes position only. The render prompt tells the model to take its materials and
mood from the scene description instead of from these colours.

Usage:
    python -m layoutgen.layouts.track --seed 7 --complexity 11 --out /tmp/track.png
"""

from __future__ import annotations

import argparse
import math
import random

from PIL import Image, ImageDraw

from layoutgen.layouts.track_geometry import chaikin, find_crossings

BG = (13, 17, 23)
ROAD = (154, 160, 166)
EDGE = (96, 104, 112)
START = (63, 185, 80)
FINISH = (248, 81, 73)


def _control_points(rng: random.Random, n: int, cx: float, cy: float,
                    r: float) -> list[tuple[float, float]]:
    """Control points at strictly increasing angles, so the polygon cannot self-cross.

    Radii come from a near ring and a far ring rather than jittering around one mean,
    because a single mean averages out as the count rises and gives a rounded blob.
    Which ring a point takes is random, capped at two in a row, so the loop gets deep
    inward cuts without settling into the regular star that strict alternation makes.
    Angular steps vary too, which is what produces long sweeps in some places and
    tight switchbacks in others.
    """
    weights = [rng.uniform(0.55, 1.75) for _ in range(n)]
    scale = 2 * math.pi / sum(weights)

    pts, ang, run, far = [], rng.uniform(0, 2 * math.pi), 0, True
    for i in range(n):
        if run >= 2:
            far = not far
            run = 1
        else:
            nxt = rng.random() < 0.5
            run = run + 1 if nxt == far else 1
            far = nxt
        rad = r * (rng.uniform(0.88, 1.10) if far else rng.uniform(0.40, 0.66))
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        ang += weights[i] * scale
    return pts


def _fit(pts: list[tuple[float, float]], size: int, margin: int
         ) -> list[tuple[float, float]]:
    """Scale and centre the loop so it fills the canvas without clipping."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    span = max(w, h) or 1
    k = (size - 2 * margin) / span
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    return [(size / 2 + (x - cx) * k, size / 2 + (y - cy) * k) for x, y in pts]


def _band(d: ImageDraw.ImageDraw, pts, width: int, fill, closed: bool = True) -> None:
    """A polyline with round joins - Pillow's joint= only covers open lines."""
    n = len(pts)
    for i in range(n if closed else n - 1):
        d.line([pts[i], pts[(i + 1) % n]], fill=fill, width=width)
    r = width / 2
    for x, y in pts:
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def _sub(pts, edge: int, reach: float):
    """The stretch of the loop around one edge, used to redraw a bridge on top."""
    n = len(pts)
    out, i, dist = [pts[edge]], edge, 0.0
    while dist < reach and len(out) < n:
        nxt = (i + 1) % n
        dist += math.dist(pts[i], pts[nxt])
        out.append(pts[nxt])
        i = nxt
    i, dist = edge, 0.0
    while dist < reach and len(out) < n:
        prv = (i - 1) % n
        dist += math.dist(pts[i], pts[prv])
        out.insert(0, pts[prv])
        i = prv
    return out


def _cross(pts, rng: random.Random, want: int):
    """Add crossings by reversing a stretch of the loop - a 2-opt move.

    `track_geometry.introduce_crossing` mirrors one vertex to make a bowtie, and
    that bowtie is too narrow to survive Chaikin: it lasted 1 seed in 24 after a single
    smoothing round. Reversing a run of points instead swaps which ends join up, so the
    two new edges cross at a wide angle, and the result is still exactly one closed
    loop because a reversal cannot split a tour.
    """
    n = len(pts)
    best = list(pts)
    for _ in range(400):
        if len(find_crossings(best)) >= want:
            break
        i = rng.randrange(n)
        j = (i + rng.randrange(n // 5, max(n // 5 + 1, n // 2))) % n
        if i == j:
            continue
        cand = list(best)
        if i < j:
            cand[i + 1:j + 1] = reversed(cand[i + 1:j + 1])
        else:
            cand = cand[j:i + 1] + list(reversed(cand[:j])) + list(
                reversed(cand[i + 1:]))
        got, have = len(find_crossings(cand)), len(find_crossings(best))
        if have < got <= want:
            best = cand
    return best


def _chaikin_open(pts, rounds: int):
    """Chaikin that keeps the two endpoints.

    The shared `chaikin` treats its input as a closed polygon, so smoothing an open
    course with it joins the finish back to the start and the course stops being a
    course.
    """
    for _ in range(rounds):
        out = [pts[0]]
        for i in range(len(pts) - 1):
            p, q = pts[i], pts[i + 1]
            out.append((0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]))
            out.append((0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1]))
        out.append(pts[-1])
        pts = out
    return pts


def _marker(d: ImageDraw.ImageDraw, p0, p1, width: int, fill) -> None:
    """A line drawn across the road, marking a start or a finish."""
    tx, ty = p1[0] - p0[0], p1[1] - p0[1]
    tl = math.hypot(tx, ty) or 1
    nx, ny = -ty / tl, tx / tl
    half = width / 2
    d.line([(p0[0] - nx * half, p0[1] - ny * half),
            (p0[0] + nx * half, p0[1] + ny * half)],
           fill=fill, width=max(6, width // 7))


#: What `complexity` buys on the repulsive path: simulation steps, and so length, and
#: so how far the loop folds back into itself. Below about 40 it is still a blob; much
#: above 220 it stops gaining shape and only costs seconds.
STEPS = (40, 220)


def _steps_for(complexity: int) -> int:
    return round(STEPS[0] + (complexity - 6) / 14 * (STEPS[1] - STEPS[0]))


#: How wide the road is drawn, against the canvas. A folded circuit needs a far
#: slimmer one than an oval does: the corridors have to pass each other, so the road
#: plus its gap is the pitch the loop can be packed at, and at the old 0.085 only
#: about seven corridors fit across a canvas - too few for the loop to fold at all.
WIDTH_FRAC = {"radial": 0.085, "repulsive": 0.022}

#: The dark gap left between two corridors that pass each other, against the road.
#: Without it the loop is still legible as a curve but not as a *route* - two roads
#: meeting with no seam read as one wide piece of tarmac.
GAP_FRAC = 0.6


def _repulsive_loop(seed: int, complexity: int, size: int, pitch: float,
                    margin: int) -> tuple[list[tuple[float, float]], int]:
    """A folded circuit from `layoutgen.layouts.repulsive`, fitted to the canvas.

    How much room the road needs is worked out here rather than in that package
    because it is a fact about this canvas, not about the curve: the optimizer
    promises a centreline that does not cross itself, and only the renderer knows how
    wide a carriageway is about to be hung on it. `_fit` scales the loop's longer side
    to `size - 2 * margin`, so `pitch` - the road, its edging and the dark gap either
    side of it - converts straight into the fraction of its own span the loop has to
    keep clear.
    """
    from layoutgen.layouts import repulsive as rc

    curve = rc.centreline(seed, _steps_for(complexity),
                          road_half=pitch / 2 / (size - 2 * margin))
    pts = _fit([(float(x), float(y)) for x, y in curve], size, margin)
    # Belt and braces: the spline through the evolved vertices can bow slightly closer
    # than they did, so the offsets get a chance to push the last of it apart.
    relaxed, rounds = rc.relax_offsets(pts, pitch / 2)
    return _fit([(float(x), float(y)) for x, y in relaxed], size, margin), rounds


def _route_points(rng: random.Random, n: int, size: float) -> list[tuple[float, float]]:
    """An open course from one corner to another, for a point-to-point race.

    A closed loop cut open is no use here: its two ends sit next to each other, and a
    point-to-point race starts in one place and finishes somewhere else. This lays a
    serpentine spine instead - across, down, back across - and keeps each traverse
    inside its own horizontal band, so the route cannot cross itself however much the
    waypoints are jittered.
    """
    lanes = max(3, min(6, rng.randint(n // 5, n // 3)))
    band = size / lanes
    pts: list[tuple[float, float]] = []
    for lane in range(lanes):
        y = band * (lane + 0.5)
        # Waypoints per traverse vary, so one leg sweeps and another wriggles instead
        # of every course coming out the same serpentine.
        per = rng.randint(3, 6)
        xs = [size * (i / (per - 1)) for i in range(per)]
        if lane % 2:
            xs.reverse()
        for i, x in enumerate(xs):
            # The turnaround at each end keeps its x, or the smoothed corner would
            # bulge out past the canvas and get clipped by the fit.
            edge = i in (0, len(xs) - 1)
            jx = 0 if edge else rng.uniform(-0.30, 0.30) * band
            jy = rng.uniform(-0.12, 0.12) if edge else rng.uniform(-0.34, 0.34)
            pts.append((x + jx, y + jy * band))
    return pts


def generate(seed: int = 7, complexity: int = 11, size: int = 1024,
             crossings: int = 0, width_frac: float | None = None,
             closed: bool = True) -> dict:
    """One track - a closed circuit, or an open point-to-point course.

    Returns the facts about it as well as the picture, so a caller can assert on the
    route rather than re-deriving it from pixels.
    """
    complexity = max(6, min(20, int(complexity)))
    want = 0 if not closed else max(0, int(crossings))
    method = "repulsive" if closed and not want else "radial"
    if width_frac is None:
        width_frac = WIDTH_FRAC[method]
    rng = random.Random(int(seed))
    track_w = max(14, int(size * width_frac))
    edge_w = max(3, round(track_w * 0.115))
    margin = max(int(size * width_frac * 1.4), track_w)
    relaxed = 0
    if not closed:
        raw = _route_points(rng, complexity, size)
        pts = _chaikin_open(raw, 4)
    elif method == "radial":
        # A crossing is made by reversing a run of the loop, which needs a coarse
        # polyline to search over and undoes the spacing a folded curve was relaxed
        # for. The angle-sorted generator is the one that can take one.
        raw = _control_points(rng, complexity, size / 2, size / 2, size * 0.40)
        pts = chaikin(raw, 4)
    else:
        pts, relaxed = _repulsive_loop(
            int(seed), complexity, size,
            track_w + edge_w + max(8, round(track_w * GAP_FRAC)), margin)
    if want:
        # Cross after smoothing, then round the two new corners without undoing them.
        pts = _cross(pts, rng, want)
        smoothed = chaikin(pts, 1)
        if len(find_crossings(smoothed)) >= want:
            pts = smoothed
    pts = _fit(pts, size, margin)

    # The repulsive loop is crossing-free by construction and carries a few thousand
    # points, so asking would cost an O(n^2) search to confirm what relaxing the
    # offsets already guaranteed.
    hits = find_crossings(pts) if closed and method == "radial" else []

    img = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(img)
    _band(d, pts, track_w + edge_w, EDGE, closed)
    _band(d, pts, track_w, ROAD, closed)

    # Break the lower-numbered edge at each crossing so one road clearly passes over.
    for x, y, i, j in hits:
        r = track_w * 0.95
        d.ellipse([x - r, y - r, x + r, y + r], fill=BG)
        over = _sub(pts, j, track_w * 2.4)
        d.line(over, fill=EDGE, width=track_w + edge_w, joint="curve")
        d.line(over, fill=ROAD, width=track_w, joint="curve")

    # Across the edging as well as the road, or on a folded circuit's slim
    # carriageway the start is a tick too short to find.
    _marker(d, pts[0], pts[1], track_w + 2 * edge_w, START)
    if not closed:
        _marker(d, pts[-1], pts[-2], track_w + 2 * edge_w, FINISH)

    n = len(pts)
    length = sum(math.dist(pts[i], pts[(i + 1) % n])
                 for i in range(n if closed else n - 1))
    return {"image": img, "points": pts, "seed": int(seed), "closed": closed,
            "complexity": complexity, "crossings": len(hits), "method": method,
            "relaxed": relaxed,
            "length": round(length / track_w, 1), "width": track_w}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--complexity", type=int, default=11)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--crossings", type=int, default=0)
    ap.add_argument("--open", action="store_true",
                    help="an open point-to-point course instead of a closed circuit")
    ap.add_argument("--out", default="track.png")
    a = ap.parse_args()
    t = generate(a.seed, a.complexity, a.size, a.crossings, closed=not a.open)
    t["image"].save(a.out)
    print(f"{a.out}  seed {t['seed']}  {'circuit' if t['closed'] else 'course'}  "
          f"{t['method']}  complexity {t['complexity']}  "
          f"{t['crossings']} crossing(s)  {t['relaxed']} relax round(s)  "
          f"{t['length']} track-widths long")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
