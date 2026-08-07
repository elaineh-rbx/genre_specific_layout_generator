"""The interactive server: build a prompt from the rules, then generate from it.

Part II is a menu, not a specification: a game picks exactly one **shape**, adds any
**options** it likes on top, and a **preset** is a shape plus a few option IDs
modelled on a real game. Nothing is mandatory - picking nothing is a legitimate
outcome that injects nothing.

This serves that model with every decision exposed, so a prompt can be pushed
through any genre, any shape, any combination of options, with the wording edited,
and the image regenerated from whatever that produces.

    prompt      one of the 75 golden scenes, or free text
    genre       any of the 15 in Build.md's Genre List
    preset      optional starting point - sets the shape and a few options at once
    shape       exactly one, and almost always the pipeline-routing decision
    options     any number, each editable, plus your own
    order       isometric first, P6 top-down first, or an authored layout first

Options marked `layout` never reach the image model. That is not a preference: step
4 recovers geometry from the render, and an invisible trigger volume or spawn marker
cannot be recovered, so it is placed against the segmented layout afterward. The
filter is applied server side, so the preview cannot drift from what is sent.

It also serves the built viewer pages and the results they read, so one process
answers everything: `/` is the playground or the viewer index depending on `--home`,
`/results/...` is the committed evidence, and `/out/...` is whatever this process has
generated since it started.

Usage:
    python -m gslg.server --port 8887
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from gslg import cards as pc
from gslg import images, paths, prompts
from gslg import rules as br
from gslg.layouts import maze as bp
from gslg.layouts import track as tg
from gslg.paths import OUT
from gslg.paths import PROMPTS as GOLDEN

#: Precomputed router picks, so a golden prompt opens already configured. Written by
#: `python -m gslg.router --golden`; missing or stale entries fall back to empty.
CLASSIFIED = paths.ROUTING / "rules.jsonl"

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

def addendum_from(spec: dict) -> tuple[str, list[str]]:
    """Assemble the addendum, and report which picks were withheld from the image.

    The ``Goes to`` filter is enforced here rather than in the browser, so an option
    that cannot survive segmentation can never reach the image model regardless of
    what the client sends.
    """
    g = br.GENRES.get(spec.get("genre", ""))
    if g is None:
        return "", []
    shape = g.shape(spec.get("shape") or "")
    edits = spec.get("edits") or {}
    bullets, withheld = [], []
    for oid in spec.get("options") or []:
        o = g.option(oid)
        if o is None:
            continue
        if o.drawn:
            # `both` contributes only its visible part; the rest is placed later.
            bullets.append((o.label,
                            (edits.get(oid) or br.visible_text(g.name, o)).strip()))
        else:
            withheld.append(f"{o.label} ({o.goes_to})")
    bullets += [("", c.strip()) for c in (spec.get("custom") or []) if c.strip()]
    return br.render(g.name, shape, bullets), withheld


def build(spec: dict) -> dict:
    add, withheld = addendum_from(spec)
    source = (spec.get("source") or "").strip()
    body = source + (f"\n\n{add}" if add else "")
    mode = spec.get("mode", "std")
    out = {"addendum": add, "withheld": withheld}
    if mode == "layout":
        kind = layout_kind(spec.get("genre", ""), spec.get("shape") or "",
                           spec.get("options"))
        if kind == "track":
            p = track_params(spec.get("genre", ""), spec.get("shape") or "")
            x = int(spec.get("crossings", p["crossings"]) or 0)
            cl = bool(spec.get("closed", p["closed"]))
            out.update(topdown=prompts.track_topdown(body, x, cl),
                       iso=f"{body}\n\n{prompts.track_isometric(x, cl)}",
                       plan=None, kind="track")
        else:
            out.update(topdown=prompts.maze_topdown(body),
                       iso=f"{body}\n\n{prompts.MAZE_ISO_FROM_TOPDOWN}",
                       plan=None, kind="maze")
    elif mode == "p6":
        out.update(plan=prompts.plan(body), iso=prompts.isometric_from_plan(body),
                   topdown=None)
    else:
        out.update(iso=prompts.isometric(body), topdown=prompts.topdown(source),
                   plan=None)
    return out


# ---------------------------------------------------------------- payloads

def catalog() -> dict:
    genres = []
    descs = dict(br.GENRE_DESCS)
    for g in br.GENRES.values():
        genres.append({
            "name": g.name, "desc": descs.get(g.name, g.tagline), "tagline": g.tagline,
            "route": g.route, "notes": g.notes,
            "shapes": [{"id": s.id, "label": s.label, "name": s.name, "what": s.what,
                        "pipeline": s.pipeline,
                        "maze": (g.name, s.id) in MAZE_SHAPES,
                        "track": (g.name, s.id) in TRACK_SHAPES,
                        **track_params(g.name, s.id)} for s in g.shapes],
            "options": [{"id": o.id, "label": o.label, "name": o.name, "what": o.what,
                         "inject": br.visible_text(g.name, o),
                         "core": o.core, "goes": o.goes_to, "pipeline": o.pipeline,
                         "drawn": o.drawn, "maze": (g.name, o.id) in MAZE_OPTIONS,
                         "shared": br.SHARED_IDS.get(o.id, [])} for o in g.options],
            "presets": [{"name": p.name, "ref": p.modelled_on, "shape": p.shape,
                         "options": p.options} for p in g.presets],
        })

    picks = {}
    if CLASSIFIED.is_file():
        for r in (json.loads(x) for x in CLASSIFIED.open() if x.strip()):
            g = br.GENRES.get(r["genre"])
            if g is None or not g.shape(r["shape"]):
                continue
            held = [o.label for oid in r.get("dropped_options", [])
                    if (o := g.option(oid))]
            picks[r["scene"]] = {
                "genre": r["genre"], "preset": r["preset"], "shape": r["shape"],
                "options": [o for o in r["options"] if g.option(o)],
                "extras": r.get("extras", []), "confidence": r["confidence"],
                "evidence": r["evidence"], "route": r.get("route", []),
                "secondary": r.get("secondary", []), "held": held}

    prompts = []
    if GOLDEN.is_file():
        for m in (json.loads(x) for x in GOLDEN.open() if x.strip()):
            genre = m.get("genre", "")
            prompts.append({"scene": m["scene"], "title": m.get("title", ""),
                            "source": m["source_prompt"],
                            "genre": genre if genre in br.GENRES else "",
                            "defaults": picks.get(m["scene"])})
    return {"genres": genres, "prompts": prompts}


# ---------------------------------------------------------------- layout

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


# ---------------------------------------------------------------- generation

def run_job(jid: str, spec: dict) -> None:
    job = _jobs[jid]
    started = time.monotonic()
    try:
        built = build(spec)
        job["prompts"] = built
        OUT.mkdir(parents=True, exist_ok=True)
        mode = spec.get("mode", "std")
        if mode == "layout":
            job["step"] = "1/3 carving the layout"
            lay = carve(spec)
            plan = OUT / lay["layout"]
            job["images"]["layout"] = lay["layout"]
            job["images"]["solution"] = lay["solution"]
            # The carve the run actually used, so the panel can show it even when the
            # layout was never carved by hand first.
            job["layout"] = {k: v for k, v in lay.items()
                             if k not in ("masks", "layout", "solution")}
            job["step"] = "2/3 top-down, locked to the layout"
            top = OUT / f"{jid}_topdown.png"
            images.generate(built["topdown"], top, [plan])
            job["images"]["topdown"] = top.name
            masks = lay.get("masks") or {}
            plan_m, route_m = masks.get("plan"), masks.get("solution")
            if plan_m is not None:
                ov = OUT / f"{jid}_overlay.png"
                overlay(top, plan_m, ov)
                job["images"]["overlay"] = ov.name
            if route_m is not None:
                sv = OUT / f"{jid}_route.png"
                overlay(top, route_m, sv, colour=ROUTE_TINT, alpha=0.62)
                job["images"]["route"] = sv.name
                if plan_m is not None:
                    # The two toggle independently, so the pair needs its own image
                    # rather than one being reachable only through the other.
                    bv = OUT / f"{jid}_both.png"
                    overlay(ov, route_m, bv, colour=ROUTE_TINT, alpha=0.62)
                    job["images"]["both"] = bv.name
            job["step"] = "3/3 isometric, dressed from the top-down"
            iso = OUT / f"{jid}_isometric.png"
            images.generate(built["iso"], iso, [top])
            job["images"]["isometric"] = iso.name
        elif mode == "p6":
            plan = OUT / f"{jid}_topdown.png"
            job["step"] = "1/2 generating the top-down plan"
            images.generate(built["plan"], plan)
            job["images"]["topdown"] = plan.name
            job["step"] = "2/2 dressing the isometric from the plan"
            iso = OUT / f"{jid}_isometric.png"
            images.generate(built["iso"], iso, [plan])
            job["images"]["isometric"] = iso.name
        else:
            job["step"] = "1/2 generating the isometric" if spec.get("stageB") \
                else "generating"
            iso = OUT / f"{jid}_isometric.png"
            images.generate(built["iso"], iso)
            job["images"]["isometric"] = iso.name
            if spec.get("stageB"):
                job["step"] = "2/2 converting to top-down"
                top = OUT / f"{jid}_topdown.png"
                images.generate(built["topdown"], top, [iso])
                job["images"]["topdown"] = top.name
        job["status"] = "done"
    except Exception as exc:
        job["status"] = "error"
        job["error"] = str(exc)
        traceback.print_exc()
    job["elapsed"] = round(time.monotonic() - started, 1)
    job["step"] = ""


# ---------------------------------------------------------------- cards

def yesterdays_guidance(source: str):
    """The sub-genre yesterday's system would have picked, and what it demanded.

    Classifying costs an LLM call; resolving the Hard Needs from the sub-genre does
    not. A card cannot fall back to an empty addendum when this fails, because an
    empty one silently turns yesterday's arm into a second copy of the raw arm.
    """
    from gslg.hardneeds import classify as sc
    from gslg.hardneeds import guidance as gd
    r = sc.classify(source)
    genre, variation = gd.split_id(r["subgenre_id"])
    # blueprint=False: this arm generates straight from text with nothing attached,
    # so any fragment that points at an authored blueprint has to state its
    # invariant in words instead.
    return gd.resolve(genre, variation, blueprint=False)


def rules_row_from(spec: dict) -> dict:
    """The spec as the scorer wants it: the shape, the options, the typed-in extras."""
    g = br.GENRES.get(spec.get("genre", ""))
    shape = g.shape(spec.get("shape") or "") if g else None
    return {"genre": spec.get("genre", ""), "shape": spec.get("shape") or "",
            "options": spec.get("options") or [],
            "extras": [{"text": c, "goes_to": "image"}
                       for c in (spec.get("custom") or []) if c.strip()],
            "preset": shape.label if shape is not None else "none",
            "mode": spec.get("mode", "std")}


def card_job(cid: str, scenes: list[str], jid: str) -> None:
    """Build cards: one or many from stored golden results, or one from a live run.

    More than one scene comes back as a zip. Downloading twenty cards one at a time
    means twenty save dialogs, and the browser blocks most of them anyway.
    """
    card = _cards[cid]
    started = time.monotonic()
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        if len(scenes) > 1:
            import zipfile
            dest = OUT / f"cards_{cid}.zip"
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
                for i, s in enumerate(scenes, 1):
                    card["step"] = f"drawing card {i} of {len(scenes)} \u2014 scene {s}"
                    one = OUT / f"card_{s}.png"
                    pc.write(pc.stored(s), one)
                    zf.write(one, one.name)
        elif scenes:
            card["step"] = "reading the stored run and scores"
            dest = OUT / f"card_{scenes[0]}.png"
            pc.write(pc.stored(scenes[0]), dest)
        else:
            job, spec = _jobs[jid], _specs[jid]
            source = (spec.get("source") or "").strip()
            card["step"] = "1/4 resolving the sub-genre yesterday would have used"
            guide = yesterdays_guidance(source)
            card["step"] = "2/4 generating the raw and yesterday arms (4 images)"
            shots = pc.build_arms(source, guide.addendum, images.generate, OUT,
                                  f"card_{cid}")
            for stage, key in (("iso", "isometric"), ("td", "topdown")):
                name = job["images"].get(key)
                shots[("rules", stage)] = OUT / name if name else None
            row = rules_row_from(spec)
            card["step"] = "3/4 judging all three against one checklist"
            items = pc.requirements_for(row, guide)
            judged = pc.judge_live(items, shots, int(cid[:6], 16),
                                   OUT / f"card_{cid}_thumbs")
            card["step"] = "4/4 drawing the card"
            dest = OUT / f"card_{cid}.png"
            pc.write(pc.live(source, row, shots, guide, judged), dest)
        card["file"] = dest.name
        card["status"] = "done"
    except Exception as exc:
        card["status"] = "error"
        card["error"] = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    card["elapsed"] = round(time.monotonic() - started, 1)
    card["step"] = ""


# ---------------------------------------------------------------- http

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode())

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/" and HOME == "playground":
            return self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        if path in ("/playground", "/playground/"):
            return self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        if path == "/api/init":
            return self._json(catalog())
        if path == "/api/job":
            jid = self.path.split("id=")[-1]
            job = _jobs.get(jid)
            return self._json(job or {"status": "unknown"}, 200 if job else 404)
        if path == "/api/card":
            card = _cards.get(self.path.split("id=")[-1])
            return self._json(card or {"status": "unknown"}, 200 if card else 404)
        if path.startswith("/out/"):
            f = OUT / pathlib.Path(path[5:]).name
            if f.is_file():
                kind = "application/zip" if f.suffix == ".zip" else "image/png"
                return self._send(200, f.read_bytes(), kind)
            return self._send(404, b"not found", "text/plain")
        if path == "/api/health":
            return self._json({"ok": True, "genres": len(br.GENRES)})
        return self._static(path)

    def _static(self, path: str):
        """The built pages, and the results they point at, from one origin.

        Two roots rather than one because they have different lifetimes: `site/` is
        rebuilt from the scripts whenever the data changes, while `results/` is the
        evidence itself. Serving them together means a page can reference an image
        with an ordinary relative URL and the browser needs no second port.
        """
        import mimetypes
        rel = path.lstrip("/") or "index.html"
        root, rel = ((paths.RESULTS, rel[len("results/"):])
                     if rel.startswith("results/") else (paths.SITE, rel))
        f = (root / rel).resolve()
        if f.is_dir():
            f = f / "index.html"
        if not (f.is_file() and root.resolve() in f.parents):
            return self._send(404, b"not found", "text/plain")
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype.endswith("javascript"):
            ctype += "; charset=utf-8"
        return self._send(200, f.read_bytes(), ctype)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            spec = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "bad json"}, 400)
        path = self.path.split("?")[0]

        if path == "/api/preview":
            try:
                return self._json(build(spec))
            except Exception as exc:
                return self._json({"error": str(exc)}, 400)

        if path == "/api/classify":
            src = (spec.get("source") or "").strip()
            if not src:
                return self._json({"error": "no prompt"}, 400)
            try:
                from gslg import router
                s = router.classify(src, genre=spec.get("genre") or "")
                return self._json({
                    "genre": s.genre, "secondary": s.secondary, "preset": s.preset,
                    "shape": s.shape, "options": s.options, "extras": s.extras,
                    "confidence": s.confidence, "evidence": s.evidence,
                    "genreEvidence": s.genre_evidence, "route": s.route,
                    "held": s.dropped_options})
            except Exception as exc:
                return self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

        if path == "/api/layout":
            try:
                lay = carve(spec)
                return self._json({k: v for k, v in lay.items() if k != "masks"})
            except Exception as exc:
                return self._json({"error": str(exc)}, 400)

        if path == "/api/generate":
            if not (spec.get("source") or "").strip():
                return self._json({"error": "no prompt"}, 400)
            jid = uuid.uuid4().hex[:12]
            _jobs[jid] = {"id": jid, "status": "running", "step": "queued",
                          "images": {}, "error": "", "elapsed": 0}
            _specs[jid] = spec
            _pool.submit(run_job, jid, spec)
            return self._json({"job": jid})

        if path == "/api/card":
            jid = spec.get("job") or ""
            scenes = [s for s in (spec.get("scenes")
                                  or ([spec["scene"]] if spec.get("scene") else []))
                      if str(s).strip()]
            if jid and jid not in _jobs:
                return self._json({"error": "unknown run"}, 400)
            if not scenes and not jid:
                return self._json({"error": "no scene or run"}, 400)
            cid = uuid.uuid4().hex[:12]
            _cards[cid] = {"id": cid, "status": "running", "step": "queued",
                           "file": "", "error": "", "elapsed": 0}
            _pool.submit(card_job, cid, scenes, jid)
            return self._json({"card": cid})

        return self._json({"error": "unknown endpoint"}, 404)


PAGE = r"""<!doctype html>
<meta charset="utf-8"><title>Layout options playground</title>
<style>
 :root{--bg:#0d1117;--panel:#141b26;--panel2:#1b2433;--line:#25303f;--fg:#e6edf3;
  --dim:#9fb0c3;--dim2:#6f8296;--ok:#3fb950;--warn:#d29922;--bad:#f85149;--accent:#58a6ff}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--fg);
  font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
 header{padding:12px 20px;border-bottom:1px solid var(--line);background:var(--panel);
  display:flex;align-items:baseline;gap:14px}
 h1{margin:0;font-size:15px} header p{margin:0;color:var(--dim2);font-size:12px}
 .wrap{display:grid;grid-template-columns:var(--wa,300px) 5px var(--wb,400px) 5px 1fr;
  height:calc(100vh - 47px)}
 .col{overflow-y:auto;padding:14px 16px;min-width:0}
 .col.a{background:var(--panel)}
 .gut{background:var(--line);cursor:col-resize;position:relative}
 .gut::after{content:"";position:absolute;top:0;bottom:0;left:-4px;right:-4px}
 .gut:hover,.gut.drag{background:var(--accent)}
 h4{margin:0 0 7px;font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--dim2)}
 .sect{margin-bottom:18px}
 select,textarea,input{width:100%;background:var(--bg);color:var(--fg);
  border:1px solid var(--line);border-radius:6px;padding:7px 9px;font-size:12.5px;
  font-family:inherit}
 textarea{resize:vertical;line-height:1.5}
 select:focus,textarea:focus,input:focus{outline:none;border-color:var(--accent)}
 .item{padding:7px 10px;border-bottom:1px solid var(--line);cursor:pointer;font-size:12px}
 .item:hover{background:var(--panel2)}
 .item.on{background:var(--panel2);border-left:3px solid var(--accent);padding-left:7px}
 .item .s{color:var(--dim2);font-size:11px}
 .item .t{display:block;margin-top:1px}
 .shape{display:block;background:var(--panel);border:1px solid var(--line);
  border-radius:6px;padding:7px 10px;margin-bottom:5px;cursor:pointer;font-size:12px}
 .shape:hover{border-color:var(--dim2)}
 .shape.on{border-color:var(--accent);background:var(--panel2)}
 .shape .w{display:block;color:var(--dim2);font-size:11.5px;margin-top:2px}
 .opt{background:var(--panel);border:1px solid var(--line);border-radius:6px;
  padding:7px 10px;margin-bottom:5px;font-size:12px}
 .opt.on{border-color:#2f4a7a}
 .opt.off{opacity:.55}
 .opt .top{display:flex;gap:7px;align-items:flex-start}
 .opt .nm{flex:1;cursor:pointer}
 .opt .w{display:block;color:var(--dim2);font-size:11.5px;margin-top:2px}
 .opt textarea{margin-top:6px;font-size:11.5px;min-height:54px}
 .badge{font-size:9.5px;letter-spacing:.05em;text-transform:uppercase;padding:1px 6px;
  border-radius:9px;border:1px solid var(--line);color:var(--dim2);white-space:nowrap}
 .badge.image{color:var(--ok);border-color:#265340}
 .badge.both{color:var(--accent);border-color:#2f4a7a}
 .badge.layout{color:var(--warn);border-color:#4a3d24}
 .core{color:var(--ok);font-size:13px;line-height:1}
 .chip{font-size:11px;padding:2px 9px;border-radius:11px;border:1px solid var(--line);
  color:var(--dim)}
 .chip.ok{color:var(--ok);border-color:#265340} .chip.acc{color:var(--accent);
  border-color:#2f4a7a} .chip.warn{color:var(--warn);border-color:#4a3d24}
 button.go{background:var(--accent);border:none;color:#04121f;font-weight:700;
  border-radius:6px;padding:9px 16px;cursor:pointer;font-size:13px}
 button.go:disabled{background:var(--line);color:var(--dim2);cursor:default}
 button.mini{background:var(--accent);border:none;color:#04121f;font-weight:700;
  border-radius:5px;padding:3px 10px;cursor:pointer;font-size:11px;white-space:nowrap}
 button.alt{background:none;border:1px solid var(--line);color:var(--dim);
  border-radius:6px;padding:6px 11px;cursor:pointer;font-size:12px}
 button.alt:hover{color:var(--fg);border-color:var(--accent)}
 .x{background:none;border:1px solid var(--line);color:var(--dim2);border-radius:4px;
  cursor:pointer;font-size:11px;padding:1px 7px}
 .x:hover{color:var(--bad);border-color:var(--bad)}
 /* Toggles, tinted to match the overlay each one draws. */
 .tg{background:none;border:1px solid var(--line);color:var(--dim2);border-radius:4px;
  cursor:pointer;font-size:11px;padding:1px 7px}
 .tg:hover{color:var(--fg);border-color:var(--accent)}
 #ovplan.on{color:#ff4fd8;border-color:#8a2f76;background:#25101f}
 #ovroute.on{color:#3fd77e;border-color:#1f5c3a;background:#0f2418}
 .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
 .sugg{display:flex;gap:9px;align-items:flex-start;margin-bottom:7px}
 .sugg button{flex:0 0 auto;min-width:132px;text-align:left}
 .sugg .note{flex:1;font-size:11px;line-height:1.4;margin:0}
 .hrow{display:flex;gap:7px;align-items:center}
 pre.prompt{background:var(--panel);border:1px solid var(--line);border-radius:7px;
  padding:12px 14px;font-size:12px;line-height:1.55;white-space:pre-wrap;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--dim);margin:0}
 pre.prompt b{color:var(--ok);font-weight:600}
 .pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;
  margin-top:12px}
 .fig{background:var(--panel);border:1px solid var(--line);border-radius:8px;
  overflow:hidden}
 .fig h5{margin:0;padding:6px 11px;font-size:10.5px;letter-spacing:.06em;
  text-transform:uppercase;color:var(--dim2);border-bottom:1px solid var(--line);
  display:flex;justify-content:space-between;align-items:center;gap:8px;min-height:29px}
 .fig img{width:100%;display:block;background:#000;cursor:zoom-in}
 .fig .ph{padding:70px 10px;text-align:center;color:var(--dim2);font-size:12px}
 .fig .ph.busy{color:var(--accent);animation:pulse 1.4s ease-in-out infinite}
 @keyframes pulse{0%,100%{opacity:.45}50%{opacity:1}}
 .figfoot{padding:7px 10px;border-top:1px solid var(--line);display:flex;gap:10px;
  align-items:center;flex-wrap:wrap;font-size:11.5px;color:var(--dim2)}
 .figfoot input{width:54px;padding:2px 6px;font-size:11.5px}
 .note{color:var(--dim2);font-size:11.5px;margin:6px 0 0}
 .hist{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
 .hist div{border:1px solid var(--line);border-radius:6px;overflow:hidden;cursor:pointer;
  width:104px}
 .hist div:hover{border-color:var(--accent)}
 .hist div.on{border-color:var(--ok);box-shadow:0 0 0 1px var(--ok)}
 .hist img{width:100%;display:block} .hist span{display:block;font-size:9.5px;
  color:var(--dim2);padding:3px 5px}
 #layhist{padding:0 10px 9px;margin-top:8px} #layhist div{width:66px}
 dialog{border:none;background:transparent;max-width:96vw;padding:0}
 dialog::backdrop{background:rgba(0,0,0,.85)} dialog img{max-width:94vw;max-height:92vh}
 .err{color:var(--bad);font-size:12px;margin-top:8px}
 .warnbox{border:1px solid #4a3d24;background:#1e1a10;color:var(--warn);
  border-radius:6px;padding:7px 10px;font-size:11.5px;margin-top:8px}
</style>
<header>
  <h1>Layout options playground</h1>
  <p>Build.md Part II &mdash; pick one shape, add any options, edit the wording,
  generate from exactly that. Nothing is mandatory.</p>
  <a href="/" style="margin-left:auto;color:var(--dim);text-decoration:none;
    font-size:12px;border:1px solid var(--line);border-radius:999px;padding:3px 10px"
    >&larr; the viewers</a>
</header>
<div class="wrap" id="wrap">
  <div class="col a">
    <div class="sect">
      <h4>Prompt</h4>
      <select id="pick"></select>
      <textarea id="src" rows="9" style="margin-top:8px"
        placeholder="or paste any prompt"></textarea>
    </div>
    <div class="sect"><h4>Golden set</h4><div id="list"></div></div>
  </div>
  <div class="gut" data-g="0" title="drag to resize \u00b7 double-click to reset"></div>

  <div class="col b">
    <div class="sect">
      <div style="margin-bottom:14px">
        <h4>Model suggestions</h4>
        <div class="sugg">
          <button class="mini" id="autog">Suggest for <b id="curgenre"></b></button>
          <span class="note">keeps the genre below and asks the model for the preset,
            shape and options</span></div>
        <div class="sugg">
          <button class="alt" id="auto">Suggest everything</button>
          <span class="note">lets the model pick the genre as well &mdash; use this for
            a prompt you typed yourself</span></div>
        <span class="note" id="autostat"></span>
      </div>
      <div id="autobox"></div>
      <h4>Genre</h4>
      <select id="genre"></select>
      <p class="note" id="gdesc"></p>
      <p class="note" id="groute" style="color:var(--warn)"></p>
    </div>
    <div class="sect">
      <h4>Preset <span class="note">&mdash; a shape plus a few options</span></h4>
      <select id="preset"></select>
      <p class="note" id="pref"></p>
    </div>
    <div class="sect">
      <h4>Shape <span class="note">&mdash; pick exactly one</span></h4>
      <div id="shapes"></div>
    </div>
    <div class="sect">
      <h4>Order</h4>
      <div class="row">
        <label class="chip"><input type="radio" name="mode" value="std" checked>
          isometric first</label>
        <label class="chip"><input type="radio" name="mode" value="p6">
          P6 &mdash; top-down first</label>
        <label class="chip ok" id="lmode" style="display:none">
          <input type="radio" name="mode" value="layout">
          <span id="lmodetxt">authored layout first</span></label>
      </div>
      <label class="note" id="stageBwrap" style="display:block;margin-top:7px">
        <input type="checkbox" id="stageB" checked> also convert to a top-down
        afterwards &mdash; uncheck for the isometric alone</label>
    </div>
    <div class="sect">
      <h4>Options <span class="chip" id="ocount"></span>
        <span class="note">&mdash; nothing here is required</span></h4>
      <p class="note"><span class="core">&#9679;</span> marks the options that are
        signature to this genre. It ranks the list rather than deciding it &mdash; an
        option without one is just as valid a pick.</p>
      <div class="row" style="margin-bottom:8px">
        <button class="alt" id="allcore">tick the <span class="core">&#9679;</span>
          ones</button>
        <button class="alt" id="all">select all</button>
        <button class="alt" id="none">clear all</button>
      </div>
      <p class="note" id="ohidden" style="margin-bottom:8px"></p>
      <div id="opts"></div>
      <div id="customs"></div>
      <button class="alt" id="add">+ add your own feature</button>
    </div>
  </div>
  <div class="gut" data-g="1" title="drag to resize \u00b7 double-click to reset"></div>

  <div class="col c">
    <div class="sect">
      <h4>Prompt that will be sent</h4>
      <pre class="prompt" id="preview">&hellip;</pre>
      <div id="withheld"></div>
      <div class="row" style="margin-top:12px">
        <button class="go" id="gen">Generate</button>
        <span id="clock" class="chip acc"></span>
        <span id="status" class="note"></span>
      </div>
      <div class="err" id="err"></div>
    </div>
    <p class="note" id="shown"></p>
    <div class="pair">
      <div class="fig" id="fig0" style="display:none">
        <h5><span>Layout &mdash; step 1, authored</span>
          <span class="hrow"><span class="chip ok" id="laymeta"></span>
            <button class="mini" id="newlay">new layout</button></span></h5>
        <div id="slot0" class="ph">&mdash;</div>
        <div class="figfoot">
          <label id="celllab">cells
            <input type="number" id="cells" min="4" max="28" value="12"></label>
          <label>seed <input type="number" id="seed" value="7"></label>
          <label id="xlab" style="display:none">bridges
            <input type="number" id="crossings" min="0" max="3" value="0"></label>
          <span id="laynote"></span>
        </div>
        <div class="hist" id="layhist"></div></div>
      <div class="fig" id="fig1"><h5 id="lab1">Isometric</h5><div id="slot1" class="ph">
        nothing generated yet</div></div>
      <div class="fig" id="fig2"><h5><span id="lab2">Top-down</span>
        <span class="hrow">
          <button class="tg" id="ovplan" style="display:none">the plan</button>
          <button class="tg" id="ovroute" style="display:none">the solution</button>
        </span></h5>
        <div id="slot2" class="ph">&mdash;</div></div>
    </div>
    <div class="sect" style="margin-top:16px">
      <h4>Card</h4>
      <p class="note">One sheet with the prompt, the same prompt run three ways
        &mdash; raw, yesterday's sub-genre Hard Needs, today's Build.md picks &mdash;
        and the checklist all three were judged against.</p>
      <div class="row">
        <button class="alt" id="cardrun" disabled
          title="generates the other two arms, then judges all three">card for this
          run</button>
        <button class="alt" id="cardscene" style="display:none"
          title="built from results already on disk">card for the stored run</button>
        <span class="note" id="cardnote"></span>
      </div>
    </div>
    <div class="sect" style="margin-top:16px">
      <h4>This session</h4><div class="hist" id="hist"></div>
    </div>
  </div>
</div>
<dialog id="zoom"><img id="zimg"></dialog>
<script>
let CAT={genres:[],prompts:[]}, gi=0, shape=null, picks={}, customs=[], hist=[], poll=null;
let wantP6=false, wantTop=false, wantLayout=false, tick=null, t0=0;
let curScene="custom", lastLabel="", lastJob=null, ovPlan=false, ovRoute=false;
let goldenSrc="", cardBusy=false;
let LAY=null, layHist=[];
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const G=()=>CAT.genres[gi];
const mode=()=>document.querySelector('input[name=mode]:checked').value;

const DEFCOLS=[300,400];
let COLS=DEFCOLS.slice();
try{ const s=JSON.parse(localStorage.getItem("pgcols2")||""); if(Array.isArray(s)&&s.length===2)
  COLS=s; }catch(e){}
function applyCols(){
  $("wrap").style.setProperty("--wa",COLS[0]+"px");
  $("wrap").style.setProperty("--wb",COLS[1]+"px");
  localStorage.setItem("pgcols2",JSON.stringify(COLS)); autosize();
}
document.querySelectorAll(".gut").forEach(g=>{
  g.onmousedown=e=>{
    e.preventDefault();
    const i=+g.dataset.g, x0=e.clientX, w0=COLS[i];
    g.classList.add("drag"); document.body.style.userSelect="none";
    const mv=ev=>{ COLS[i]=Math.max(200,Math.min(1000,w0+ev.clientX-x0)); applyCols(); };
    const up=()=>{ g.classList.remove("drag"); document.body.style.userSelect="";
      document.removeEventListener("mousemove",mv);
      document.removeEventListener("mouseup",up); };
    document.addEventListener("mousemove",mv); document.addEventListener("mouseup",up);
  };
  g.ondblclick=()=>{ COLS=DEFCOLS.slice(); applyCols(); };
});
function autosize(){
  const t=$("src"); t.style.height="auto";
  t.style.height=Math.min(t.scrollHeight+4, window.innerHeight*0.55)+"px";
}
window.addEventListener("resize",applyCols);

async function init(){
  $("seed").value=Math.floor(Math.random()*99999);
  CAT=await (await fetch("/api/init")).json();
  $("genre").innerHTML=CAT.genres.map((g,i)=>`<option value="${i}">${esc(g.name)}</option>`)
    .join("");
  $("pick").innerHTML=`<option value="-1">Custom prompt</option>`+
    CAT.prompts.map((p,i)=>`<option value="${i}">${esc(p.scene)} \u00b7 `+
      `${esc(p.title||p.source.slice(0,52))}</option>`).join("");
  $("list").innerHTML=CAT.prompts.map((p,i)=>`<div class="item" data-p="${i}">
      <span class="s">${esc(p.scene)}${p.genre?" \u00b7 "+esc(p.genre):""}</span>
      <span class="t">${esc((p.title||p.source).slice(0,64))}</span></div>`).join("");
  document.querySelectorAll("[data-p]").forEach(el=>
    el.onclick=()=>{ $("pick").value=el.dataset.p; usePrompt(+el.dataset.p); });
  renderGenre();
  if(CAT.prompts.length){ $("pick").value=0; usePrompt(0); }
}
function usePrompt(i){
  clearResults();
  document.querySelectorAll("[data-p]").forEach(el=>
    el.classList.toggle("on", +el.dataset.p===i));
  $("autobox").innerHTML="";
  if(i<0){ curScene="custom"; goldenSrc=""; $("src").value=""; autosize();
    updateCard(); preview(); return; }
  const p=CAT.prompts[i];
  curScene=p.scene; goldenSrc=p.source.trim();
  $("src").value=p.source; autosize(); updateCard();
  // Golden prompts open already configured from the precomputed router pass.
  if(p.defaults){ applySettings(p.defaults,"saved model suggestion"); return; }
  if(p.genre){
    const g=CAT.genres.findIndex(x=>x.name===p.genre);
    if(g>=0&&g!==gi){ gi=g; $("genre").value=g; renderGenre(); return; }
  }
  preview();
}
// Drop a set of router picks into the normal controls. Everything stays editable.
function applySettings(r,note){
  const g=CAT.genres.findIndex(x=>x.name===r.genre);
  if(g<0){ $("autostat").textContent="unknown genre "+r.genre; return false; }
  gi=g; $("genre").value=g; renderGenre();
  shape=r.shape; picks={};
  (r.options||[]).forEach(id=>{ if(G().options.some(o=>o.id===id)) picks[id]=true; });
  customs=(r.extras||[]).filter(e=>e.goes_to==="image").map(e=>e.text);
  const pi=G().presets.findIndex(p=>p.name===r.preset);
  $("preset").value=pi>=0?pi:-1;
  $("pref").textContent=pi>=0
    ? `modelled on ${G().presets[pi].ref} \u2014 internal reference, not shown to users`
    : "";
  $("shapes").querySelectorAll("input[name=shape]").forEach(el=>
    el.checked=el.value===shape);
  markShapes(); renderOpts();
  setOrder();
  const held=(r.held||[]).concat((r.extras||[])
    .filter(e=>e.goes_to==="layout").map(e=>e.text));
  $("autobox").innerHTML=`<div class="warnbox" style="border-color:#2f4a7a;
    background:#101a28;color:var(--dim)">
    <b style="color:var(--accent)">${esc(r.preset==="none"?"no preset fits":r.preset)}</b>
    <span class="chip ${r.confidence==="low"?"warn":"ok"}">${esc(r.confidence)}</span>
    ${(r.route||[]).map(x=>`<span class="chip warn">${esc(x)}</span>`).join("")}
    ${(r.secondary||[]).length?`<span class="chip">also ${
      r.secondary.map(esc).join(", ")}</span>`:""}
    <span class="chip">${esc(note)}</span>
    <div style="margin-top:5px">${esc(r.evidence)}</div>
    ${held.length?`<div style="margin-top:5px;color:var(--warn)">not drawn:
      ${held.map(esc).join("; ")}</div>`:""}
    <div style="margin-top:5px;color:var(--dim2)">everything below stays editable</div>
    </div>`;
  return true;
}
function renderGenre(){
  const g=G();
  shape=null; picks={}; customs=[];
  $("gdesc").textContent=g.desc;
  $("groute").textContent=g.route||"";
  $("curgenre").textContent=g.name;
  $("preset").innerHTML=`<option value="-1">\u2014 none, start empty \u2014</option>`+
    g.presets.map((p,i)=>`<option value="${i}">${esc(p.name)}</option>`).join("");
  $("pref").textContent="";
  $("shapes").innerHTML=g.shapes.map(s=>`<label class="shape" data-s="${esc(s.id)}">
      <input type="radio" name="shape" value="${esc(s.id)}"> <b>${esc(s.label)}</b>
      ${s.pipeline?`<span class="chip warn">${esc(s.pipeline)}</span>`:""}
      <span class="w">${esc(s.what)}</span></label>`).join("");
  $("shapes").querySelectorAll("input[name=shape]").forEach(el=>
    el.onchange=()=>{ shape=el.value; markShapes(); renderOpts(); });
  renderOpts();
}
// The order is part of the configuration, not a separate choice. A P6 route means the
// topology must be valid by construction, which a free image cannot guarantee, so it
// cannot be drawn isometric-first. Where a generator exists - only mazes today - the
// layout is authored outright instead.
function orderFromPicks(){
  const g=G(), sh=g.shapes.find(x=>x.id===shape);
  if(layoutKind()) return "layout";
  const txt=[g.route||"", sh?sh.pipeline:""]
    .concat(g.options.filter(o=>picks[o.id]).map(o=>o.pipeline||"")).join(" ");
  return /\bP6\b/.test(txt)?"p6":"std";
}
function setOrder(){
  const el=document.querySelector(`input[name=mode][value=${orderFromPicks()}]`);
  if(el&&!el.checked){ el.checked=true; modeChanged(); }
}
function markShapes(){
  $("shapes").querySelectorAll("[data-s]").forEach(el=>
    el.classList.toggle("on", el.dataset.s===shape));
  const k=layoutKind();
  $("lmode").style.display=k?"":"none";
  $("lmodetxt").textContent=k==="track"?"authored track first"
    :"authored layout first";
  if(!k&&mode()==="layout"){
    document.querySelector('input[name=mode][value=std]').checked=true;
  }
  modeChanged();
}
// Which authored layout, if any, this configuration can have. Mirrors the server's
// layout_kind() - the shape decides a track, the shape or an option decides a maze.
function layoutKind(){
  const s=G().shapes.find(x=>x.id===shape);
  if(s&&s.track) return "track";
  if((s&&s.maze)||G().options.some(o=>o.maze&&picks[o.id])) return "maze";
  return null;
}
// Only `image` and `both` options are listed: this tool builds an image, and a
// layout-only option can never reach it. Build.md forbids truncating a list
// silently, so the ones left out are named underneath rather than just dropped.
function drawnOpts(){ return G().options.filter(o=>o.drawn); }
function renderOpts(){
  const g=G(), shown=drawnOpts();
  const on=shown.filter(o=>picks[o.id]).length;
  $("ocount").textContent=`${on} of ${shown.length}`;
  const hid=g.options.filter(o=>!o.drawn);
  $("ohidden").innerHTML=hid.length
    ? `not listed \u2014 ${hid.map(o=>esc(o.label)).join(", ")}: placed against the
       layout after segmentation, never drawn, so they cannot change this image`
    : "";
  $("opts").innerHTML=shown.map(o=>{
    const p=!!picks[o.id];
    return `<div class="opt ${p?"on":"off"}">
      <div class="top"><input type="checkbox" data-o="${esc(o.id)}" ${p?"checked":""}>
        <span class="nm"><b>${esc(o.label)}</b>
          ${o.core?'<span class="core">\u25cf</span>':""}
          <span class="badge ${esc(o.goes)}">${esc(o.goes)}</span>
          ${o.pipeline?`<span class="chip warn">${esc(o.pipeline)}</span>`:""}
          ${!p?`<span class="w">${esc(o.what)}</span>`:""}</span></div>
      ${p&&o.drawn&&o.inject!==o.what?`<span class="w" style="color:var(--warn)">
        ${esc(o.what)} \u2014 only the visible part below is drawn; the rest is placed
        after segmentation.</span>`:""}
      ${p?`<textarea data-t="${esc(o.id)}" rows="3">${esc(
        picks[o.id]===true?o.inject:picks[o.id])}</textarea>`:""}</div>`;
  }).join("");
  $("opts").querySelectorAll("[data-o]").forEach(el=>el.onchange=()=>{
    const id=el.dataset.o;
    if(el.checked) picks[id]=true; else delete picks[id];
    markShapes(); renderOpts();
  });
  $("opts").querySelectorAll("[data-t]").forEach(el=>el.oninput=()=>{
    picks[el.dataset.t]=el.value; preview();
  });
  renderCustoms();
}
function renderCustoms(){
  $("customs").innerHTML=customs.map((c,i)=>`<div class="opt on">
    <div class="top"><span class="nm"><b>Your own</b>
      <span class="badge image">image</span></span>
      <button class="x" data-c="${i}">remove</button></div>
    <textarea data-ct="${i}" rows="3">${esc(c)}</textarea></div>`).join("");
  $("customs").querySelectorAll("[data-c]").forEach(el=>el.onclick=()=>{
    customs.splice(+el.dataset.c,1); renderCustoms(); preview(); });
  $("customs").querySelectorAll("[data-ct]").forEach(el=>el.oninput=()=>{
    customs[+el.dataset.ct]=el.value; preview(); });
  preview();
}
function applyPreset(i){
  const g=G();
  if(i<0){ $("pref").textContent=""; return; }
  const p=g.presets[i];
  shape=p.shape; picks={}; customs=[];
  p.options.forEach(id=>{ if(g.options.some(o=>o.id===id)) picks[id]=true; });
  $("pref").textContent=`modelled on ${p.ref} \u2014 internal reference, not shown to users`;
  $("shapes").querySelectorAll("input[name=shape]").forEach(el=>
    el.checked=el.value===shape);
  markShapes(); renderOpts(); setOrder();
}

function modeChanged(){
  const on=mode()==="layout", track=layoutKind()==="track";
  $("fig0").style.display=on?"":"none";
  if(on&&(!LAY||(LAY.kind==="track")!==track)) resetLayoutPanel();
  $("fig2").style.order=on?"2":"";
  $("fig1").style.order=on?"3":"";
  $("stageBwrap").style.display=on?"none":"";
  $("lab1").textContent=on?"Isometric \u2014 step 3, from the top-down":"Isometric";
  $("lab2").textContent=on?"Top-down \u2014 step 2, locked to the layout":"Top-down";
  $("celllab").firstChild.textContent=track?"corners ":"cells ";
  $("cells").min=track?6:4; $("cells").max=track?20:28;
  if(track&&+$("cells").value>20) $("cells").value=13;
  const s=G().shapes.find(x=>x.id===shape);
  // A bridge needs a loop to cross itself; an open course has nothing to pass over.
  $("xlab").style.display=track&&s&&s.closed?"":"none";
  if(track&&s) $("crossings").value=s.crossings;
  $("newlay").textContent=track?"new track":"new layout";
  updateGen(); preview();
}
function resetLayoutPanel(){
  LAY=null; $("laymeta").textContent="";
  $("laynote").textContent="carving is local and free \u2014 re-roll as often as you like."+
    " Generating without one carves it for you, from the numbers below.";
  const el=$("slot0");
  if(el) el.outerHTML=`<div id="slot0" class="ph">${
    layoutKind()==="track"?"press new track, or just generate"
                          :"press new layout, or just generate"}</div>`;
  drawLayHist(); updateGen();
}
// The numbers and the sentence under the layout. Split out from showLayout because a
// generated run has to update them without touching the image the poller is filling.
function describeLayout(l){
  $("cells").value=l.cells; $("seed").value=l.seed;
  if(l.kind==="track"){
    $("crossings").value=l.crossings;
    $("laymeta").textContent=`${l.cells} corners \u00b7 seed ${l.seed}`;
    $("laynote").textContent=(l.closed
      ? `one closed loop by construction \u00b7 ${l.steps} track-widths round`
      : `one course, start to finish, by construction \u00b7 ${l.steps} track-widths`)+
      (l.crossings?` \u00b7 ${l.crossings} bridge`+(l.crossings>1?"s":""):"");
  }else{
    $("laymeta").textContent=`${l.cells}\u00d7${l.cells} \u00b7 seed ${l.seed}`;
    $("laynote").textContent=
      `solvable by construction \u00b7 shortest route ${l.steps} cells`;
  }
}
function showLayout(l){
  LAY=l; describeLayout(l);
  const el=$("slot0");
  if(el) el.outerHTML=`<img id="slot0" src="/out/${l.layout}" data-full="/out/${l.solution}">`;
  $("slot0").onclick=e=>{ $("zimg").src=e.target.dataset.full; $("zoom").showModal(); };
  drawLayHist(); updateGen();
}
// Only carves of the kind now selected. A track thumbnail sitting under a maze
// configuration is not just clutter: clicking it would hand a racing loop to a maze.
function drawLayHist(){
  const k=layoutKind()||"maze";
  const shown=layHist.map((l,i)=>({l,i})).filter(x=>(x.l.kind||"maze")===k);
  $("layhist").innerHTML=shown.slice(0,12).map(({l,i})=>
    `<div data-l="${i}" class="${LAY&&l.seed===LAY.seed&&l.cells===LAY.cells?"on":""}"
      title="${l.kind==="track"?l.cells+" corners":l.cells+"\u00d7"+l.cells}, seed ${
        l.seed}"><img src="/out/${l.layout}"><span>seed ${l.seed}</span></div>`).join("");
  $("layhist").querySelectorAll("[data-l]").forEach(el=>
    el.onclick=()=>showLayout(layHist[+el.dataset.l]));
}
async function carveLayout(){
  const s=G().shapes.find(x=>x.id===shape);
  const body={kind:layoutKind()||"maze", genre:G().name, shape:shape,
    cells:+$("cells").value||12, seed:+$("seed").value||0,
    closed:!(s&&s.track&&!s.closed), crossings:+$("crossings").value||0};
  const r=await (await fetch("/api/layout",{method:"POST",
    headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})).json();
  if(r.error){ $("laynote").textContent=r.error; return; }
  if(!layHist.some(l=>l.seed===r.seed&&l.cells===r.cells)) layHist.unshift(r);
  showLayout(r);
}
// Generating without a carve is fine - the server carves from the same numbers this
// panel shows - so the button no longer waits for one, and the result is written back
// into the panel so the layout on screen is always the one that was used.
function updateGen(){
  $("gen").disabled=$("gen").dataset.busy==="1";
  $("gen").textContent=mode()!=="layout" ? "Generate"
    : LAY ? "Generate from this layout" : "Carve and generate";
}

let pT=null;
function preview(){ clearTimeout(pT); pT=setTimeout(doPreview,250); }
function payload(){
  const g=G(), edits={};
  Object.entries(picks).forEach(([k,v])=>{ if(v!==true) edits[k]=v; });
  return {mode:mode(), source:$("src").value, genre:g.name, shape:shape,
    options:Object.keys(picks), edits, custom:customs, kind:layoutKind()||"maze",
    stageB:$("stageB").checked, cells:+$("cells").value||12,
    seed:+$("seed").value||0, crossings:+$("crossings").value||0};
}
async function doPreview(){
  const body=payload();
  const r=await (await fetch("/api/preview",{method:"POST",
    headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})).json();
  if(r.error){ $("preview").textContent=r.error; return; }
  const add=r.addendum;
  const show=t=>{ if(!t) return ""; const i=add?t.indexOf(add):-1;
    return i<0?esc(t):esc(t.slice(0,i))+"<b>"+esc(add)+"</b>"+esc(t.slice(i+add.length)); };
  $("preview").innerHTML = body.mode==="p6"
    ? `<b style="color:var(--accent)">1. TOP-DOWN PLAN</b>\n`+show(r.plan)+
      `\n\n<b style="color:var(--accent)">2. ISOMETRIC, from that plan</b>\n`+show(r.iso)
    : body.mode==="layout"
    ? `<b style="color:var(--accent)">1. LAYOUT \u2014 carved here, no model call</b>\n`+
      (layoutKind()==="track"
        ? `A single racing route is generated locally and attached as the `+
          `reference image below.`
        : `A perfect maze is generated locally and attached as the reference image `+
          `below.`)+
      `\n\n<b style="color:var(--accent)">2. TOP-DOWN, locked to that layout</b>\n`+
      show(r.topdown)+
      `\n\n<b style="color:var(--accent)">3. ISOMETRIC, dressed from that top-down</b>\n`+
      show(r.iso)
    : show(r.iso)+($("stageB").checked
      ? `\n\n<b style="color:var(--accent)">then, from that isometric</b>\n`+esc(r.topdown)
      : "");
  $("withheld").innerHTML=(r.withheld&&r.withheld.length)
    ? `<div class="warnbox">Withheld from the image prompt, because a segmenter could
       not recover it: ${r.withheld.map(esc).join(", ")}. These are placed against the
       layout after segmentation.</div>` : "";
}

// The panels always show output for the current selection.
function clearResults(){
  clearInterval(poll); clearInterval(tick);
  $("clock").textContent=""; $("status").textContent=""; $("err").textContent="";
  $("shown").textContent=""; $("gen").dataset.busy="0";
  const lay=mode()==="layout";
  $("lab1").textContent=lay?"Isometric \u2014 step 3, from the top-down":"Isometric";
  $("lab2").textContent=lay?"Top-down \u2014 step 2, locked to the layout":"Top-down";
  $("slot1").outerHTML=`<div id="slot1" class="ph">nothing generated yet</div>`;
  $("slot2").outerHTML=`<div id="slot2" class="ph">\u2014</div>`;
  $("slot0").outerHTML=`<div id="slot0" class="ph">\u2014</div>`;
  lastJob=null; hideOverlayToggles(); $("cardnote").textContent=""; updateCard();
  if(!lay) updateGen(); else if(LAY) showLayout(LAY); else resetLayoutPanel();
}
function label(){
  const s=G().shapes.find(x=>x.id===shape);
  return `${curScene} \u00b7 ${G().name}${s?" \u203a "+s.label:""}`;
}
async function generate(){
  $("err").textContent=""; $("gen").dataset.busy="1"; updateGen();
  const r=await (await fetch("/api/generate",{method:"POST",
    headers:{"Content-Type":"application/json"},body:JSON.stringify(payload())})).json();
  if(r.error){ $("err").textContent=r.error; $("gen").dataset.busy="0"; updateGen();
    return; }
  wantP6=mode()==="p6"; wantLayout=mode()==="layout";
  wantTop=wantP6||wantLayout||$("stageB").checked; t0=Date.now();
  lastLabel=label(); hideOverlayToggles();
  $("shown").textContent=`showing: ${lastLabel} \u2014 `+
    (wantLayout?"authored layout, then top-down, then isometric"
     :wantP6?"top-down first, then dressed"
     :(wantTop?"isometric, then converted to top-down":"isometric only"));
  $("slot1").outerHTML=`<div id="slot1" class="ph">\u2026</div>`;
  $("slot2").outerHTML=`<div id="slot2" class="ph">\u2026</div>`;
  clearInterval(poll); clearInterval(tick);
  tick=setInterval(()=>{ $("clock").textContent=
    `${Math.round((Date.now()-t0)/1000)}s`; },1000);
  poll=setInterval(()=>check(r.job),1500); check(r.job);
}
function fill(slot,name,pending,busy){
  const el=$(slot); if(!el) return;
  if(name){
    if(el.tagName==="IMG") return;
    el.outerHTML=`<img id="${slot}" src="/out/${name}" data-full="/out/${name}">`;
    $(slot).onclick=e=>{ $("zimg").src=e.target.dataset.full; $("zoom").showModal(); };
    return;
  }
  if(el.tagName==="IMG") return;
  el.textContent=pending; el.className="ph"+(busy?" busy":"");
}
async function check(jid){
  const j=await (await fetch("/api/job?id="+jid)).json();
  const run=j.status==="running", iso=j.images.isometric, top=j.images.topdown;
  lastJob=j;
  $("status").textContent=j.step||(j.status==="done"?`done in ${j.elapsed}s`:j.status);
  if(j.images.overlay) $("ovplan").style.display="";
  if(j.images.route) $("ovroute").style.display="";
  if(wantLayout){
    // Adopt whatever the run carved, so the panel below the image always describes the
    // layout that was actually used - including when it was never carved by hand.
    if(j.layout&&(!LAY||LAY.seed!==j.layout.seed||LAY.cells!==j.layout.cells
                  ||LAY.kind!==j.layout.kind)){
      const l={...j.layout, layout:j.images.layout, solution:j.images.solution};
      if(!layHist.some(x=>x.layout===l.layout)) layHist.unshift(l);
      LAY=l; describeLayout(l); drawLayHist();
    }
    fill("slot0",j.images.layout,"carving\u2026",run);
    fill("slot2",top, run?(j.images.layout?"step 2 \u2014 top-down on the layout\u2026"
                                          :"step 2 \u2014 waiting for the layout"):"\u2014",
         run&&!!j.images.layout);
    fill("slot1",iso, run?(top?"step 3 \u2014 dressing from the top-down\u2026"
                              :"step 3 \u2014 waiting for the top-down"):"\u2014",
         run&&!!top);
  }else if(wantP6){
    fill("slot2",top, run?"step 1 \u2014 drawing the plan\u2026":"\u2014", run);
    fill("slot1",iso, run?(top?"step 2 \u2014 dressing from the plan\u2026"
                              :"step 2 \u2014 waiting for the plan"):"\u2014", run&&!!top);
  }else{
    fill("slot1",iso, run?"generating\u2026":"\u2014", run);
    fill("slot2",top, !wantTop?"not requested"
      :run?(iso?"step 2 \u2014 converting to top-down\u2026"
               :"step 2 \u2014 waiting for the isometric"):"\u2014", run&&!!iso);
  }
  if(j.status==="done"||j.status==="error"){
    clearInterval(poll); clearInterval(tick);
    $("gen").dataset.busy="0"; updateGen(); updateCard();
    $("clock").textContent="";
    if(j.status==="error") $("err").textContent=j.error;
    else{ hist.unshift({j,label:lastLabel}); drawHist(); }
  }
}
function drawHist(){
  $("hist").innerHTML=hist.slice(0,14).map((h,i)=>`<div data-h="${i}" title="${esc(h.label)}">
    <img src="/out/${h.j.images.isometric||h.j.images.topdown}">
    <span>${esc(h.label.slice(0,30))}</span></div>`).join("");
  $("hist").querySelectorAll("[data-h]").forEach(el=>el.onclick=()=>{
    const h=hist[+el.dataset.h];
    $("zimg").src="/out/"+(h.j.images.isometric||h.j.images.topdown);
    $("zoom").showModal();});
}
// Build.md's Presentation rule: offer the closest preset first, then let the user
// adjust. Everything the model picks lands in the normal controls and stays editable.
// Two scopes. Forcing the genre asks only the second question - the closest preset,
// the shape, the options - which is what you want once you have chosen the genre
// yourself. Leaving it free asks the genre question first as well.
async function autoPick(forceGenre){
  const src=$("src").value.trim();
  if(!src){ $("autostat").textContent="write a prompt first"; return; }
  $("auto").disabled=true; $("autog").disabled=true;
  $("autostat").textContent="thinking\u2026"; $("autobox").innerHTML="";
  try{
    const r=await (await fetch("/api/classify",{method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({source:src, genre:forceGenre?G().name:""})})).json();
    if(r.error){ $("autostat").textContent=r.error; return; }
    if(applySettings(r, forceGenre?`model suggestion for ${r.genre}`
                                  :"model suggestion, genre included"))
      $("autostat").textContent="";
  }catch(e){ $("autostat").textContent=String(e); }
  finally{ $("auto").disabled=false; $("autog").disabled=false; }
}
$("autog").onclick=()=>autoPick(true);
$("auto").onclick=()=>autoPick(false);
// Reselecting the prompt reapplies its saved suggestion, so there is no separate
// restore control.
$("genre").onchange=e=>{gi=+e.target.value; renderGenre(); clearResults();
  $("autobox").innerHTML="";};
$("preset").onchange=e=>applyPreset(+e.target.value);
$("pick").onchange=e=>usePrompt(+e.target.value);
$("src").oninput=()=>{autosize(); preview(); updateCard();};
$("allcore").onclick=()=>{ drawnOpts().forEach(o=>{ if(o.core) picks[o.id]=true; });
  markShapes(); renderOpts(); };
$("all").onclick=()=>{ drawnOpts().forEach(o=>{ picks[o.id]=true; });
  markShapes(); renderOpts(); };
$("none").onclick=()=>{ picks={}; customs=[]; markShapes(); renderOpts(); };
$("add").onclick=()=>{ customs.push(""); renderCustoms(); };
$("stageB").onchange=preview;
document.querySelectorAll('input[name=mode]').forEach(el=>el.onchange=modeChanged);
$("cells").onchange=carveLayout;
$("seed").onchange=carveLayout;
$("newlay").onclick=()=>{ $("seed").value=Math.floor(Math.random()*99999);
  carveLayout(); };
// Two things worth checking against the render, each on its own toggle: the authored
// plan, and - for a maze, which has one - the solved route through it, to see whether
// the way from start to end survived the dressing. Independent, so the solution can be
// looked at without the plan drawn over it first.
function hideOverlayToggles(){
  ovPlan=false; ovRoute=false;
  ["ovplan","ovroute"].forEach(id=>{
    $(id).style.display="none"; $(id).classList.remove("on"); });
}
function drawOverlays(){
  const el=$("slot2"); if(!lastJob||el.tagName!=="IMG") return;
  const im=lastJob.images;
  const name=(ovPlan&&ovRoute&&im.both) ? im.both
           : ovPlan&&im.overlay ? im.overlay
           : ovRoute&&im.route ? im.route
           : im.topdown;
  el.src=el.dataset.full="/out/"+name;
  $("ovplan").classList.toggle("on",ovPlan);
  $("ovroute").classList.toggle("on",ovRoute);
}
$("ovplan").onclick=()=>{ ovPlan=!ovPlan; drawOverlays(); };
$("ovroute").onclick=()=>{ ovRoute=!ovRoute; drawOverlays(); };

// A card for a golden scene is assembled from results already on disk, so it costs
// nothing. A card for a run has only today's arm and has to build the other two
// before anything can be judged, which is why the two are separate buttons rather
// than one that behaves differently depending on what is selected.
function updateCard(){
  const golden=curScene!=="custom", same=golden&&$("src").value.trim()===goldenSrc;
  $("cardrun").disabled=!(lastJob&&lastJob.status==="done")||cardBusy;
  $("cardscene").style.display=golden?"":"none";
  $("cardscene").disabled=cardBusy||!same;
  $("cardscene").textContent=same?`card for stored scene ${curScene}`
                                 :"prompt edited \u2014 no stored card";
}
function download(name,as){
  const a=document.createElement("a");
  a.href="/out/"+name; a.download=as; document.body.appendChild(a); a.click(); a.remove();
}
async function makeCard(body,as){
  cardBusy=true; updateCard(); $("cardnote").textContent="starting\u2026";
  const r=await (await fetch("/api/card",{method:"POST",
    headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})).json();
  if(r.error){ $("cardnote").textContent=r.error; cardBusy=false; updateCard(); return; }
  const t0=Date.now();
  const step=setInterval(async()=>{
    const c=await (await fetch("/api/card?id="+r.card)).json();
    const secs=Math.round((Date.now()-t0)/1000);
    if(c.status==="running"){ $("cardnote").textContent=`${c.step} \u2014 ${secs}s`; return; }
    clearInterval(step); cardBusy=false; updateCard();
    if(c.status==="done"){ download(c.file,as); $("cardnote").textContent=
      `downloaded ${as} \u2014 built in ${c.elapsed}s`; }
    else $("cardnote").textContent=c.error||"card failed";
  },1500);
}
$("cardscene").onclick=()=>makeCard({scene:curScene},`card_${curScene}.png`);
$("cardrun").onclick=()=>makeCard({job:lastJob.id},
  `card_${(curScene==="custom"?"prompt":curScene)}_${lastJob.id}.png`);
$("gen").onclick=generate;
$("zoom").onclick=()=>$("zoom").close();
applyCols();
init();
</script>
"""


#: What "/" serves. The same process answers both the playground and the built viewer
#: pages, so a port dedicated to the playground opens straight into it, while a port
#: shared with the viewers opens on their landing page. Every other path is identical
#: either way, so the two can run side by side against the same files.
HOME = "viewers"


def main() -> None:
    global HOME
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8887)
    ap.add_argument("--home", choices=("playground", "viewers"), default="playground",
                    help="what / serves; every other path is the same either way")
    args = ap.parse_args()
    HOME = args.home
    OUT.mkdir(parents=True, exist_ok=True)
    paths.LOGS.mkdir(parents=True, exist_ok=True)
    n_opt = sum(len(g.options) for g in br.GENRES.values())
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"serving :{args.port} ({args.home})  "
          f"{len(br.GENRES)} genres, {n_opt} options", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
