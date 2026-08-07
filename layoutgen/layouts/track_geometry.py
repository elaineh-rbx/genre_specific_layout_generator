"""Generate a guaranteed single-closed-loop RACE TRACK blueprint.

Mirrors the maze generator: author the topology, then hand a clean 2D
reference to the image model so the render inherits a real racing loop instead
of one the model invents.

Guarantees by construction:
  - single continuous closed loop (radially-sorted control points => simple
    polygon; Chaikin smoothing preserves simplicity)
  - no dead ends, no forks, no unfinished segments
  - a marked start/finish
  - optional self-crossings that are explicitly labelled as BRIDGE / TUNNEL so
    the render draws grade-separation, not ambiguous 2D X-junctions

Outputs (in --out):
  blueprint.png   clean top-down track (green grass, gray asphalt ring,
                  dashed white centerline, checkered start/finish, bridge/
                  tunnel glyphs on any self-crossings)
  track.json      polyline coords, length, start point, crossings (ground truth)

    python -m layoutgen.layouts.track_geometry --seed 7 --complexity 12 \\
        --crossings 1 --out /tmp/tb01
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

GRASS = (68, 152, 78)
ASPHALT = (56, 58, 62)
CURB = (230, 40, 40)
DASH = (245, 245, 245)
BRIDGE_FILL = (48, 108, 216)
TUNNEL_FILL = (204, 60, 60)
GLYPH_TEXT = (245, 245, 245)
GLYPH_OUTLINE = (0, 0, 0)


def _font(size: int) -> ImageFont.FreeTypeFont:
    for base in ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/TTF"):
        p = Path(base) / "DejaVuSans-Bold.ttf"
        if p.is_file():
            return ImageFont.truetype(str(p), size=size)
    return ImageFont.load_default()


def radial_polygon(rng: random.Random, n: int, cx: float, cy: float,
                   r_mean: float, r_var: float, angle_jitter: float) -> list[tuple[float, float]]:
    """N vertices arranged by strictly-increasing angle => simple polygon."""
    verts: list[tuple[float, float]] = []
    step = 2 * math.pi / n
    for i in range(n):
        angle = i * step + rng.uniform(-step * angle_jitter, step * angle_jitter)
        r = r_mean * rng.uniform(1 - r_var, 1 + r_var)
        verts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return verts


def chaikin(pts: list[tuple[float, float]], rounds: int) -> list[tuple[float, float]]:
    for _ in range(rounds):
        new: list[tuple[float, float]] = []
        m = len(pts)
        for i in range(m):
            p, q = pts[i], pts[(i + 1) % m]
            new.append((0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]))
            new.append((0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1]))
        pts = new
    return pts


def _seg_intersect(a, b, c, d) -> tuple[float, float] | None:
    """Return intersection point of segments ab and cd if they cross strictly."""
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = a, b, c, d
    rx, ry = bx - ax, by - ay
    sx, sy = dx - cx, dy - cy
    denom = rx * sy - ry * sx
    if abs(denom) < 1e-9:
        return None
    t = ((cx - ax) * sy - (cy - ay) * sx) / denom
    u = ((cx - ax) * ry - (cy - ay) * rx) / denom
    if 0 < t < 1 and 0 < u < 1:
        return (ax + t * rx, ay + t * ry)
    return None


def introduce_crossing(pts: list[tuple[float, float]], rng: random.Random,
                       min_edge_gap: int = 4) -> bool:
    """In-place: pick a chord across the polygon and swap two vertices to force
    exactly one new self-crossing.

    Strategy: pick a middle vertex, mirror it (roughly) across the centroid so
    the walk 'darts inward and back out', creating a bowtie-style crossing.
    Retries a few times on the current geometry until at least one strict
    intersection appears. Returns True if a crossing was successfully added.
    """
    before = len(find_crossings(pts))
    for _ in range(80):
        i = rng.randrange(min_edge_gap, len(pts) - min_edge_gap)
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        dx, dy = pts[i][0] - cx, pts[i][1] - cy
        scale = rng.uniform(-0.95, -0.55)
        new = (cx + dx * scale, cy + dy * scale)
        old = pts[i]
        pts[i] = new
        if len(find_crossings(pts)) > before:
            return True
        pts[i] = old
    return False


def _has_crossing(pts: list[tuple[float, float]]) -> bool:
    return len(find_crossings(pts)) > 0


def find_crossings(pts: list[tuple[float, float]]) -> list[tuple[float, float, int, int]]:
    """Return every strict self-intersection (x, y, edge_i, edge_j)."""
    hits: list[tuple[float, float, int, int]] = []
    m = len(pts)
    for i in range(m):
        a, b = pts[i], pts[(i + 1) % m]
        for j in range(i + 2, m):
            if i == 0 and j == m - 1:
                continue
            c, d = pts[j], pts[(j + 1) % m]
            p = _seg_intersect(a, b, c, d)
            if p is not None:
                hits.append((p[0], p[1], i, j))
    return hits


def _polygon_area(pts: list[tuple[float, float]]) -> float:
    a = 0.0
    m = len(pts)
    for i in range(m):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % m]
        a += x0 * y1 - x1 * y0
    return a / 2


def _polyline_length(pts: list[tuple[float, float]]) -> float:
    length = 0.0
    m = len(pts)
    for i in range(m):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % m]
        length += math.hypot(x1 - x0, y1 - y0)
    return length


def draw_dashed_polyline(draw: ImageDraw.ImageDraw, pts: list[tuple[float, float]],
                        *, dash_len: float, gap_len: float, width: int, fill: tuple[int, int, int]) -> None:
    m = len(pts)
    remaining = 0.0
    drawing = True
    prev = pts[0]
    for i in range(1, m + 1):
        p = pts[i % m]
        seg_dx, seg_dy = p[0] - prev[0], p[1] - prev[1]
        seg_len = math.hypot(seg_dx, seg_dy)
        if seg_len < 1e-6:
            prev = p
            continue
        ux, uy = seg_dx / seg_len, seg_dy / seg_len
        travelled = 0.0
        cursor = prev
        while travelled < seg_len:
            if remaining <= 0:
                remaining = dash_len if drawing else gap_len
            step = min(remaining, seg_len - travelled)
            nxt = (cursor[0] + ux * step, cursor[1] + uy * step)
            if drawing:
                draw.line([cursor, nxt], fill=fill, width=width)
            cursor = nxt
            travelled += step
            remaining -= step
            if remaining <= 1e-6:
                drawing = not drawing
        prev = p


def _draw_start_finish(d: ImageDraw.ImageDraw, xy: list[tuple[int, int]],
                       start_index: int, track_width: int) -> None:
    p0 = xy[start_index]
    p1 = xy[(start_index + 1) % len(xy)]
    tx, ty = p1[0] - p0[0], p1[1] - p0[1]
    tl = math.hypot(tx, ty) or 1
    ux, uy = tx / tl, ty / tl
    nx, ny = -uy, ux
    half = track_width / 2 + 2
    depth = max(28, track_width / 3)
    cell = 10
    rows = 2
    cols = max(4, int((2 * half) / cell))
    base_along = -depth / 2
    for r in range(rows):
        for c in range(cols):
            along = base_along + (r + 0.5) * (depth / rows)
            across = -half + (c + 0.5) * (2 * half / cols)
            cxp = p0[0] + ux * along + nx * across
            cyp = p0[1] + uy * along + ny * across
            colour = (240, 240, 240) if (r + c) % 2 == 0 else (30, 30, 30)
            corners = [
                (cxp + ux * (-cell / 2) + nx * (-cell / 2), cyp + uy * (-cell / 2) + ny * (-cell / 2)),
                (cxp + ux * (cell / 2) + nx * (-cell / 2), cyp + uy * (cell / 2) + ny * (-cell / 2)),
                (cxp + ux * (cell / 2) + nx * (cell / 2), cyp + uy * (cell / 2) + ny * (cell / 2)),
                (cxp + ux * (-cell / 2) + nx * (cell / 2), cyp + uy * (-cell / 2) + ny * (cell / 2)),
            ]
            d.polygon(corners, fill=colour)
    outline_corners = [
        (p0[0] + ux * (-depth / 2) + nx * half, p0[1] + uy * (-depth / 2) + ny * half),
        (p0[0] + ux * (depth / 2) + nx * half, p0[1] + uy * (depth / 2) + ny * half),
        (p0[0] + ux * (depth / 2) - nx * half, p0[1] + uy * (depth / 2) - ny * half),
        (p0[0] + ux * (-depth / 2) - nx * half, p0[1] + uy * (-depth / 2) - ny * half),
    ]
    d.polygon(outline_corners, outline=(0, 0, 0), fill=None)


def render_blueprint(pts: list[tuple[float, float]], *, size: int, track_width: int,
                     start_index: int, crossings: list[tuple[float, float, int, int]]) -> Image.Image:
    img = Image.new("RGB", (size, size), GRASS)
    d = ImageDraw.Draw(img)

    xy = [(round(x), round(y)) for x, y in pts]
    xy_closed = xy + [xy[0]]

    d.line(xy_closed, fill=CURB, width=track_width + 12, joint="curve")
    d.line(xy_closed, fill=ASPHALT, width=track_width, joint="curve")

    draw_dashed_polyline(d, xy, dash_len=max(14, track_width * 0.9),
                         gap_len=max(14, track_width * 0.9),
                         width=max(3, track_width // 14), fill=DASH)

    _draw_start_finish(d, xy, start_index, track_width)

    for k, (cxp, cyp, _, _) in enumerate(crossings):
        kind = "BRIDGE" if k % 2 == 0 else "TUNNEL"
        fill = BRIDGE_FILL if kind == "BRIDGE" else TUNNEL_FILL
        r = max(24, track_width // 2 + 6)
        d.ellipse([cxp - r, cyp - r, cxp + r, cyp + r], fill=fill, outline=(0, 0, 0), width=3)
        f = _font(max(14, r - 6))
        tw = f.getlength(kind)
        d.text((cxp - tw / 2, cyp - r // 2 - 4), kind, fill=GLYPH_TEXT, font=f,
               stroke_width=2, stroke_fill=GLYPH_OUTLINE)
    return img


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--complexity", type=int, default=10, help="Number of control points before smoothing (7-16 is a good range)")
    ap.add_argument("--r-mean", type=float, default=0.38, help="Mean track radius as fraction of canvas")
    ap.add_argument("--r-var", type=float, default=0.28, help="Radial jitter as fraction of r-mean")
    ap.add_argument("--angle-jitter", type=float, default=0.35, help="Angular jitter as fraction of angular step")
    ap.add_argument("--smoothing", type=int, default=3, help="Chaikin subdivision rounds")
    ap.add_argument("--track-width", type=int, default=64, help="Road width in px")
    ap.add_argument("--crossings", type=int, default=0, help="Number of intentional self-crossings (bridge/tunnel)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    cx = cy = args.size / 2
    r_mean = args.r_mean * args.size

    control = radial_polygon(rng, args.complexity, cx, cy, r_mean, args.r_var, args.angle_jitter)
    pts = chaikin(control, args.smoothing)

    added = 0
    for _ in range(args.crossings):
        if introduce_crossing(pts, rng):
            added += 1
    crossings = find_crossings(pts)
    if added < args.crossings:
        print(f"  note: only {added}/{args.crossings} crossings could be added on this geometry", flush=True)

    start_index = rng.randrange(len(pts))

    img = render_blueprint(pts, size=args.size, track_width=args.track_width,
                           start_index=start_index, crossings=crossings)
    bp = args.out / "blueprint.png"
    img.save(bp, format="PNG")

    meta = {
        "seed": args.seed,
        "size": args.size,
        "complexity": args.complexity,
        "smoothing": args.smoothing,
        "track_width": args.track_width,
        "polyline_points": len(pts),
        "polyline_length_px": round(_polyline_length(pts), 1),
        "polygon_area_px2": round(_polygon_area(pts), 1),
        "start_px": [round(pts[start_index][0], 1), round(pts[start_index][1], 1)],
        "crossings": [{"x": round(c[0], 1), "y": round(c[1], 1),
                       "kind": "BRIDGE" if i % 2 == 0 else "TUNNEL"}
                      for i, c in enumerate(crossings)],
        "polyline": [[round(x, 1), round(y, 1)] for x, y in pts],
    }
    (args.out / "track.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"wrote {bp}")
    print(f"  polyline: {len(pts)} pts, length {meta['polyline_length_px']:.0f}px, "
          f"crossings: {len(crossings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
