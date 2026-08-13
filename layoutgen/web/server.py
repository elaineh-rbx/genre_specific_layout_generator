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
    python -m layoutgen.web.server --port 8887
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

from layoutgen import arms, assets, paths
from layoutgen.backends import images
from layoutgen.evaluate import card as pc
from layoutgen.model import rules as br
from layoutgen.paths import OUT
from layoutgen.pipeline import run as pipeline
from layoutgen.pipeline.carve import carve
from layoutgen.pipeline.spec import build, catalog

_jobs: dict[str, dict] = {}
#: What each job was asked for, kept aside from the job itself so it is not sent
#: back on every poll. A card built from a run needs the picks the run used.
_specs: dict[str, dict] = {}
_cards: dict[str, dict] = {}
_pool = ThreadPoolExecutor(max_workers=3)

#: Precomputed router picks, so a golden prompt opens already configured. Written by
#: `python -m layoutgen.model.router --golden`; missing or stale entries fall back to empty.
CLASSIFIED = paths.ROUTING / "rules.jsonl"

# ---------------------------------------------------------------- cards

def yesterdays_guidance(source: str):
    """The sub-genre yesterday's system would have picked, and what it demanded.

    Classifying costs an LLM call; resolving the Hard Needs from the sub-genre does
    not. A card cannot fall back to an empty addendum when this fails, because an
    empty one silently turns yesterday's arm into a second copy of the raw arm.
    """
    from layoutgen.model.hardneeds import classify as sc
    from layoutgen.model.hardneeds import guidance as gd
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
            cmp = arms.COMPARISONS[pc.DEFAULT]
            # The playground already ran one arm - this one - so the card only has to
            # generate the others before the whole set can go to the judge.
            here = "rules"
            card["step"] = "1/4 resolving what the other arms would have been given"
            guide = yesterdays_guidance(source)
            row = rules_row_from(spec)
            rows = pc.rows_for_live(row, guide)
            addenda = {a.id: rows.get(a.id, {}).get("addendum", "")
                       for a in cmp if a.id != here}
            card["step"] = (f"2/4 generating the other {len(addenda)} arms "
                            f"({2 * len(addenda)} images)")
            shots = pc.build_arms(source, addenda, images.generate, OUT,
                                  f"card_{cid}")
            for stage, key in (("iso", "isometric"), ("td", "topdown")):
                name = job["images"].get(key)
                shots[(here, stage)] = OUT / name if name else None
            card["step"] = (f"3/4 judging all {len(cmp.arms)} against one checklist")
            items = pc.requirements_for(row, guide, cmp)
            judged = pc.judge_live(items, shots, int(cid[:6], 16),
                                   OUT / f"card_{cid}_thumbs", cmp)
            card["step"] = "4/4 drawing the card"
            dest = OUT / f"card_{cid}.png"
            pc.write(pc.live(source, row, shots, guide, judged, cmp), dest)
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
        # Ports that share out one analysis rewrite / to that page rather than
        # to the viewer index, so the URL people paste around is the analysis.
        # The page lives under results/ so the same server serves it from
        # either place; this route just makes / redirect there.
        if path == "/" and HOME == "shifts":
            shifts_path = paths.RESULTS / "config_shifts.html"
            if shifts_path.is_file():
                return self._send(200, shifts_path.read_bytes(),
                                  "text/html; charset=utf-8")
            return self._send(404,
                b"config_shifts.html not built yet - run "
                b"tools/build_shifts_viewer.py",
                "text/plain")
        # `/pipeline` is the per-scene pipeline flowchart, populated with the
        # answered configs and the actual images each scene produced. Built
        # by `tools/build_pipeline_viewer.py`; served here at a stable URL
        # rather than through /results/ so the link is short enough to paste.
        if path in ("/pipeline", "/pipeline/"):
            pv_path = paths.RESULTS / "pipeline_viewer.html"
            if pv_path.is_file():
                return self._send(200, pv_path.read_bytes(),
                                  "text/html; charset=utf-8")
            return self._send(404,
                b"pipeline_viewer.html not built yet - run "
                b"tools/build_pipeline_viewer.py",
                "text/plain")
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
            return self._json({"ok": True, "genres": len(br.GENRES),
                               "images": assets.status()})
        return self._static(path)

    def _static(self, path: str):
        """The built pages, and the results they point at, from one origin.

        Two roots rather than one because they have different lifetimes: `site/` is
        rebuilt whenever the data changes, while `results/` is the evidence itself.
        Serving them together means a page can reference an image with an ordinary
        relative URL and the browser needs no second port.

        An image the clone does not carry is fetched from the bucket and cached. That
        is why the pages ask this server for images rather than addressing storage
        directly: the bucket blocks public access, so the credentials have to live on
        this side of the request.
        """
        import mimetypes
        rel = path.lstrip("/") or "index.html"
        if rel.startswith("results/"):
            f = assets.fetch(rel[len("results/"):])
            if f is None:
                return self._send(404, b"not found", "text/plain")
            ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
            return self._send(200, f.read_bytes(), ctype)
        root, rel = paths.SITE, rel
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
                from layoutgen.model import router
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
            _pool.submit(pipeline.run, _jobs[jid], jid, spec)
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


#: The playground page. It is an HTML file rather than a string in here because it
#: is 800 lines of markup, script and stylesheet, and burying that in a module makes
#: the server look like a page and the page uneditable by anything that understands
#: HTML. Read once at import: it ships with the package and does not change under a
#: running process.
PAGE = (pathlib.Path(__file__).parent / "playground.html").read_text(encoding="utf-8")


#: What "/" serves. The same process answers both the playground and the built viewer
#: pages, so a port dedicated to the playground opens straight into it, while a port
#: shared with the viewers opens on their landing page. Every other path is identical
#: either way, so the two can run side by side against the same files.
HOME = "viewers"


def main() -> None:
    global HOME
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8887)
    ap.add_argument("--home", choices=("playground", "viewers", "shifts"),
                    default="playground",
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
