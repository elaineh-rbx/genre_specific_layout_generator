"""Score the Build.md rules arm against the untouched baseline, feature by feature.

For each scene the judge sees both images and the list of layout features the rules
arm actually asked for - the shape of the space, then each option's visible wording -
and marks every one present or absent in each image independently. Scoring presence
rather than preference keeps "which looks nicer" out of the result.

The judge is never told which arm is which, and the images swap sides on odd scenes,
so position cannot correlate with arm.

One caveat on the top-down stage: in the baseline the top-down is always converted
from the isometric, while the rules arm generates it first on a P6 or layout route.
That is the point of those routes rather than a confound, but it does mean the two
top-downs were not made the same way.

Usage:
    python -m gslg.judges.rules --stage iso
    python -m gslg.judges.rules --stage td --workers 8
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from gslg import llm, paths
from gslg import rules as br

THUMB_PX = 420

STAGES = {
    "iso": dict(what="isometric", out="rules_iso.jsonl"),
    "td": dict(what="top-down", out="rules_td.jsonl"),
}

SYSTEM = """You audit game-layout concept images against explicit layout requirements.

You see two images of the same game scene, labelled LEFT and RIGHT, and a numbered
list of layout requirements. For each requirement, decide independently whether it is
clearly visible in LEFT and whether it is clearly visible in RIGHT.

Judge only what is actually depicted. "Clearly visible" means a person reading the
image could point at the thing. Do not credit a requirement because the scene is the
right genre, because the thing is implied, or because it would be easy to add. If you
cannot point at it, it is absent.

Ignore art quality, lighting, colour and appeal entirely. You are checking presence
and arrangement, nothing else."""


def requirements(row: dict) -> list[dict]:
    """The features this scene's prompt actually asked for, in injected order."""
    g = br.GENRES.get(row["genre"])
    if g is None:
        return []
    out = []
    if (s := g.shape(row["shape"])) is not None:
        out.append({"label": s.label, "text": s.what, "kind": "shape"})
    for oid in row["options"]:
        if (o := g.option(oid)) is not None and o.drawn:
            out.append({"label": o.label, "text": br.visible_text(g.name, o),
                        "kind": o.goes_to})
    for e in row.get("extras", []):
        if e.get("goes_to") == "image":
            out.append({"label": "unlisted request", "text": e["text"],
                        "kind": "extra"})
    return out


def thumb(src: pathlib.Path, dest: pathlib.Path) -> bool:
    """A judge-sized copy, made once and reused.

    The judge is shown thumbnails rather than full renders: a 1024px pair costs
    several times as many image tokens and the features being marked - a circuit, a
    row of lanes, a central hub - survive the downscale intact.
    """
    from PIL import Image
    if not src.is_file():
        return False
    if dest.is_file() and dest.stat().st_mtime >= src.stat().st_mtime:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert("RGB")
        im.thumbnail((THUMB_PX, THUMB_PX), Image.LANCZOS)
        im.save(dest, format="JPEG", quality=82)
    return True


def _schema(n: int) -> dict:
    return {
        "name": "audit", "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "requirements": {
                    "type": "array", "minItems": n, "maxItems": n,
                    "items": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "integer"},
                            "in_left": {"type": "boolean"},
                            "in_right": {"type": "boolean"},
                            "note": {"type": "string"},
                        },
                        "required": ["index", "in_left", "in_right", "note"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["requirements"],
            "additionalProperties": False,
        },
    }


def judge(job: tuple[dict, str], retries: int = 3) -> dict | None:
    row, stage = job
    scene = row["scene"]
    reqs = requirements(row)
    if not reqs:
        return None

    base = paths.thumb("raw", stage, scene)
    arm = paths.thumb("rules", stage, scene)
    if not thumb(paths.scene("raw", stage, scene), base):
        return None
    if not thumb(paths.scene("rules", stage, scene), arm):
        return None

    swap = int(scene) % 2 == 1
    left, right = (arm, base) if swap else (base, arm)
    listing = "\n".join(f"{i + 1}. {r['label']} - {r['text']}"
                        for i, r in enumerate(reqs))
    content = [
        llm.text_part(f"REQUIREMENTS\n{listing}\n\nLEFT image:"),
        llm.image_part(left),
        llm.text_part("RIGHT image:"),
        llm.image_part(right),
        llm.text_part("For every requirement, mark presence in each image."),
    ]
    try:
        out = llm.ask(SYSTEM, content, _schema(len(reqs)), retries=retries, timeout=240)
    except llm.LLMError:
        print(f"  {scene}: judging failed", flush=True)
        return None
    items = []
    for i, r in enumerate(out["requirements"]):
        if i >= len(reqs):
            break
        items.append({**reqs[i],
                      "base": r["in_right"] if swap else r["in_left"],
                      "rules": r["in_left"] if swap else r["in_right"],
                      "note": r["note"]})
    return {"scene": scene, "genre": row["genre"], "preset": row["preset"],
            "shape": row["shape"], "order": row["order"],
            "route": row.get("route", []), "swapped": swap, "items": items,
            "base_met": sum(x["base"] for x in items),
            "rules_met": sum(x["rules"] for x in items),
            "total": len(items)}


def report(results: list[dict], what: str) -> None:
    tot = sum(r["total"] for r in results)
    b = sum(r["base_met"] for r in results)
    g = sum(r["rules_met"] for r in results)
    print(f"\n{len(results)} scenes, {tot} feature checks ({what})")
    print(f"  {'baseline (raw prompt)':34s} {b:4d}/{tot}  {100*b/tot:.1f}%")
    print(f"  {'rules (Build.md injection)':34s} {g:4d}/{tot}  {100*g/tot:.1f}%")
    print(f"  {'delta':34s} {g-b:+4d}       {100*(g-b)/tot:+.1f} pts")

    verdict = Counter()
    for r in results:
        verdict["rules better" if r["rules_met"] > r["base_met"]
                else "baseline better" if r["base_met"] > r["rules_met"]
                else "tie"] += 1
    print("\nper scene:", dict(verdict))

    print("\nby route order:")
    for order in ("std", "p6", "layout"):
        rs = [r for r in results if r["order"] == order]
        if not rs:
            continue
        t = sum(x["total"] for x in rs)
        bb = sum(x["base_met"] for x in rs)
        gg = sum(x["rules_met"] for x in rs)
        print(f"  {order:8s} n={len(rs):2d}  baseline {100*bb/t:5.1f}%  "
              f"rules {100*gg/t:5.1f}%  delta {100*(gg-bb)/t:+5.1f}")

    print("\nby feature kind:")
    kinds: dict[str, list] = {}
    for r in results:
        for it in r["items"]:
            kinds.setdefault(it["kind"], []).append(it)
    for k, its in sorted(kinds.items()):
        bb = sum(x["base"] for x in its)
        gg = sum(x["rules"] for x in its)
        print(f"  {k:8s} n={len(its):3d}  baseline {100*bb/len(its):5.1f}%  "
              f"rules {100*gg/len(its):5.1f}%  delta {100*(gg-bb)/len(its):+5.1f}")

    worst = sorted(results, key=lambda x: x["rules_met"] - x["base_met"])[:5]
    print("\nscenes where the rules arm scored worse:")
    for r in worst:
        d = r["rules_met"] - r["base_met"]
        if d < 0:
            print(f"  {r['scene']}  {r['genre']} :: {r['preset']}  {d:+d}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--stage", choices=tuple(STAGES) + ("both",), default="both")
    ap.add_argument("--only", default="", help="rescore just these scenes, e.g. "
                    "0053,0054 - the rest keep the scores already on disk")
    args = ap.parse_args()

    rows = [json.loads(x) for x in (paths.RUNS / "rules.jsonl").open() if x.strip()]
    rows = [r for r in rows if r["status"] == "ok"]
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    if only:
        rows = [r for r in rows if r["scene"] in only]
    stages = tuple(STAGES) if args.stage == "both" else (args.stage,)

    for stage in stages:
        st = STAGES[stage]
        print(f"\njudging {len(rows)} {st['what']} pairs with {llm.DEPLOYMENT}",
              flush=True)
        results = []
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for i, res in enumerate(pool.map(judge, [(r, stage) for r in rows]), 1):
                if res:
                    results.append(res)
                if i % 15 == 0:
                    print(f"  {i}/{len(rows)}", flush=True)
        out = paths.SCORES / st["out"]
        if only and out.is_file():
            # Merge, so rescoring a few regenerated scenes keeps the scores for the
            # scenes this run never looked at.
            kept = {r["scene"]: r for x in out.open() if x.strip()
                    for r in [json.loads(x)]}
            kept.update({r["scene"]: r for r in results})
            results = list(kept.values())
        results.sort(key=lambda r: r["scene"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("".join(json.dumps(r) + "\n" for r in results), encoding="utf-8")
        report(results, st["what"])
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
