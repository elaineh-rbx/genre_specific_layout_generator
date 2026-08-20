"""Check the flowchart in pipeline-viewer.html is a well-formed graph.

The chart is hand-positioned data inside a 4,800-line HTML file, so the ways it
breaks are silent: an edge naming a node that no longer exists, a node with no
colour category, a route whose consecutive steps have no edge drawn between
them, or two nodes sitting on top of each other. None of those throw in the
browser - they just render wrong.

    python tools/check_viewer_chart.py
"""
import re
import sys
from pathlib import Path

VIEWER = Path(__file__).resolve().parent.parent / "pipeline-viewer.html"
HALF_W, HALF_H = 79, 34

text = VIEWER.read_text(encoding="utf-8")


def block(name: str) -> str:
    m = re.search(rf"const {name} = (\[|\{{)(.*?)^(\]|\}});", text, re.S | re.M)
    if not m:
        sys.exit(f"could not find {name}")
    return m.group(2)


nodes = {m.group(1): (int(m.group(2)), int(m.group(3)))
         for m in re.finditer(r"^\s*(\w+):\s*\{\s*x:\s*(\d+),\s*y:\s*(\d+)", block("NODES"), re.M)}
edges = [(a, b) for a, b in re.findall(r'\["(\w+)","(\w+)"\]', block("MASTER_EDGES"))]
cats = dict(re.findall(r'(\w+):"(\w+)"', block("CAT")))
streams = re.findall(r'"(\w+>\w+)"', block("STREAM_EDGES"))
bands = [(int(x), int(y), int(w), int(h), holds.split('","'))
         for x, y, w, h, holds in
         re.findall(r'x:(\d+),\s*y:(\d+),\s*w:(\d+),\s*h:(\d+),[^[]*\["([^\]]*)"\]',
                    block("BANDS").replace("\n", " "))]

# viewBox and the .chart box must both cover every node
vb = re.search(r'id="edges" viewBox="0 0 (\d+) (\d+)"', text)
css = re.search(r"\.chart \{[^}]*width:(\d+)px;\s*height:(\d+)px", text)

problems = []

for a, b in edges:
    for n in (a, b):
        if n not in nodes:
            problems.append(f"edge {a}>{b} names unknown node {n!r}")
for n in nodes:
    if n not in cats:
        problems.append(f"node {n!r} has no CAT entry, so it has no colour")
for n in cats:
    if n not in nodes:
        problems.append(f"CAT names unknown node {n!r}")
for s in streams:
    if tuple(s.split(">")) not in edges:
        problems.append(f"STREAM_EDGES {s!r} is not in MASTER_EDGES, so nothing is drawn")

# every route a variation can take must have its consecutive edges drawn
have = set(edges)


def path_for(mods, tiered):
    p = ["prompt", "classify", "ask", "genre", "handoff", "route"]
    if "P4" in mods:
        p.append("p4")
    struct = "elev" if "P2" in mods else "top"
    if "P6" in mods:
        p += ["params", "proc", struct, "iso", "seg"]
    else:
        p += ["iso", struct, "seg"]
    if "P3" in mods:
        p.append("p3")
    return p + ["p45", "build", "out"]


for mods in [[], ["P2"], ["P3"], ["P4"], ["P6"], ["P4", "P3"], ["P6", "P2"], ["P2", "P3"]]:
    p = path_for(mods, False)
    for a, b in zip(p, p[1:]):
        if (a, b) not in have:
            problems.append(f"route {mods or ['none']}: no edge {a}>{b}")

# geometry: nodes must not overlap, and must sit inside the drawing area
ids = list(nodes)
for i, a in enumerate(ids):
    for b in ids[i + 1:]:
        ax, ay = nodes[a]
        bx, by = nodes[b]
        if abs(ax - bx) < 2 * HALF_W and abs(ay - by) < 2 * HALF_H:
            problems.append(f"nodes {a} and {b} overlap ({ax},{ay}) vs ({bx},{by})")

w, h = (int(vb.group(1)), int(vb.group(2))) if vb else (0, 0)
if css and (int(css.group(1)), int(css.group(2))) != (w, h):
    problems.append(f"viewBox {w}x{h} != .chart {css.group(1)}x{css.group(2)}; edges will be offset from nodes")
for n, (x, y) in nodes.items():
    if not (HALF_W <= x <= w - HALF_W and HALF_H <= y <= h - HALF_H):
        problems.append(f"node {n} at ({x},{y}) falls outside the {w}x{h} chart")

# Bands are decoration, but a node poking out of the box that names it reads as
# a mislabel, and that is exactly the kind of thing nobody notices in review.
banded = set()
for bx, by, bw, bh, holds in bands:
    if bx + bw > w or by + bh > h:
        problems.append(f"band at ({bx},{by}) {bw}x{bh} overflows the {w}x{h} chart")
    for n in holds:
        banded.add(n)
        if n not in nodes:
            problems.append(f"band lists unknown node {n!r}")
            continue
        x, y = nodes[n]
        if not (bx <= x - HALF_W and x + HALF_W <= bx + bw
                and by <= y - HALF_H and y + HALF_H <= by + bh):
            problems.append(f"node {n} at ({x},{y}) pokes out of its band ({bx},{by},{bw},{bh})")

for i, (ax, ay, aw, ah, _) in enumerate(bands):
    for bx, by, bw, bh, _ in bands[i + 1:]:
        if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
            problems.append(f"bands ({ax},{ay}) and ({bx},{by}) overlap")

# Anything not in a band should be there on purpose - only the two streams are.
stray = set(nodes) - banded
if stray != {"img", "lay"}:
    problems.append(f"nodes outside every band should be exactly the streams, got {sorted(stray)}")
for n in ("img", "lay"):
    y = nodes[n][1]
    top_band = min(b[1] for b in bands)
    if y + HALF_H >= top_band:
        problems.append(f"stream node {n} at y={y} overlaps the bands starting at y={top_band}")

print(f"nodes {len(nodes)}   edges {len(edges)}   streams {len(streams)}   bands {len(bands)}")
print(f"chart {w}x{h}")
unreached = set(nodes) - {n for e in edges for n in e}
if unreached:
    print(f"nodes with no edge at all: {sorted(unreached)}")
for p in problems:
    print("  !", p)
print(f"\n{len(problems)} problem(s)")
sys.exit(1 if problems else 0)
