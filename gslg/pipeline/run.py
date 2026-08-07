"""Run one spec all the way to images, reporting progress as it goes.

The three orders differ in what is generated first, and that is the whole point of
having them, so each is spelled out rather than folded into one path with flags:

    std     isometric, then a top-down converted from it
    p6      a top-down plan, then an isometric dressed from the plan
    layout  an authored layout, then a top-down locked to it, then an isometric

`job` is a plain dict the caller owns and can read while this runs; the server hands
it straight to the browser as progress.
"""

from __future__ import annotations

import time
import traceback

from gslg.backends import images
from gslg.paths import OUT
from gslg.pipeline.carve import ROUTE_TINT, carve, overlay
from gslg.pipeline.spec import build

# ---------------------------------------------------------------- generation

def run(job: dict, jid: str, spec: dict) -> None:
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
