"""One downloadable card per prompt: three arms of images, and what each was asked for.

A card answers a single question at a glance - what did this prompt look like before
any guidance, under yesterday's sub-genre Hard Needs, and under today's Build.md
shape-and-options - and then shows the checklist both guided arms were judged against,
so the pictures and the requirements sit on the same sheet instead of in two viewers.

Two sources, one layout:

  stored    any of the 75 golden scenes, assembled from the runs and the blinded
            scores already on disk, so a card costs nothing to make.
  live      a prompt typed into the playground, which has only today's arm. The
            other two are generated the way the golden set generated them, and the
            trio then goes through the same blinded judge, so a live card's ticks
            mean what a stored card's ticks mean.

Usage:
    python -m gslg.cards --scene 0025
    python -m gslg.cards --all
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib

from PIL import Image, ImageDraw, ImageFont

from gslg import paths, prompts
from gslg import rules as br
from gslg.judges import rules as rsc
from gslg.judges import three_way as tws
from gslg.paths import PROMPTS as MANIFEST

CARDS = paths.RUN / "cards"

ARMS = paths.ARMS
ARM_TITLE = {"raw": "RAW PROMPT", "needs": "YESTERDAY", "rules": "TODAY"}
ARM_SUB = {"raw": "no guidance at all",
           "needs": "sub-genre Hard Needs",
           "rules": "Build.md Part II"}
ARM_TICK = {"raw": "raw", "needs": "yest", "rules": "today"}
STAGES = ("iso", "td")
STAGE_LABEL = {"iso": "isometric", "td": "top-down"}

BG = (13, 17, 23)
PANEL = (20, 27, 38)
LINE = (37, 48, 63)
FG = (230, 237, 243)
DIM = (159, 176, 195)
DIM2 = (111, 130, 150)
OK = (63, 185, 80)
MISS = (60, 72, 88)
ACCENT = {"raw": (139, 148, 158), "needs": (210, 153, 34), "rules": (88, 166, 255)}

W = 1920
PAD = 40


def _font_dir() -> pathlib.Path | None:
    """This image has no system fonts; matplotlib ships DejaVu, which has the tick
    and arrow glyphs the card uses. Without this the truetype lookup fails silently
    and Pillow falls back to a bitmap font that renders them tofu."""
    try:
        import matplotlib
        d = pathlib.Path(matplotlib.get_data_path()) / "fonts" / "ttf"
        return d if (d / "DejaVuSans.ttf").is_file() else None
    except Exception:
        return None


_FONTS = _font_dir()


def _font(size: int, bold: bool = False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for candidate in ([_FONTS / name] if _FONTS else []) + [name]:
        try:
            return ImageFont.truetype(str(candidate), size)
        except OSError:
            continue
    return ImageFont.load_default()


# ---------------------------------------------------------------- assembly

def _wrap(text: str, font, width: int, cap: int = 0) -> list[str]:
    """Wrap to a pixel width, measuring the font rather than counting characters.

    `cap` limits the number of lines and marks the cut, so a long prompt reads as
    trimmed rather than as if it simply ended there.
    """
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if font.getlength(trial) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    if cap and len(lines) > cap:
        lines = lines[:cap]
        while lines[-1] and font.getlength(lines[-1] + " \u2026") > width:
            lines[-1] = lines[-1].rsplit(" ", 1)[0]
        lines[-1] += " \u2026"
    return lines


def _key(text: str) -> str:
    return " ".join(text.split()).lower()


def merge_stages(iso_items: list[dict], td_items: list[dict]) -> list[dict]:
    """One checklist, with each requirement carrying both stages' verdicts.

    Keyed on the requirement text rather than position: the two stages are judged in
    separate calls, and a judge that drops or reorders an item would otherwise shift
    every tick below it onto the wrong requirement.
    """
    by_text = {_key(it["text"]): it for it in td_items}
    out = []
    for it in iso_items:
        td = by_text.get(_key(it["text"]), {})
        out.append({"label": it["label"], "text": it["text"],
                    "source": it["source"], "kind": it["kind"],
                    "iso": {a: bool(it.get(a)) for a in ARMS},
                    "td": {a: bool(td.get(a)) for a in ARMS}})
    return out


def stored(scene: str) -> dict:
    """A card's worth of data for one golden scene, entirely from disk."""
    def rows(path: pathlib.Path) -> dict:
        if not path.is_file():
            return {}
        return {json.loads(x)["scene"]: json.loads(x)
                for x in path.open() if x.strip()}

    rules = rows(paths.RUNS / "rules.jsonl").get(scene)
    needs = rows(paths.RUNS / "needs.jsonl").get(scene)
    if rules is None or needs is None:
        raise KeyError(f"scene {scene} has no stored run")
    iso = rows(paths.SCORES / "three_way_iso.jsonl").get(scene, {})
    td = rows(paths.SCORES / "three_way_td.jsonl").get(scene, {})
    items = merge_stages(iso.get("items", []), td.get("items", []))
    if not items:
        # Unjudged, so show what was asked for without pretending to a verdict.
        items = [{**r, "iso": {}, "td": {}}
                 for r in tws.requirements(needs, rules)]

    prompt = rules.get("prompt") or ""
    if not prompt and MANIFEST.is_file():
        for x in MANIFEST.open():
            if x.strip() and (m := json.loads(x))["scene"] == scene:
                prompt = m["source_prompt"]
                break

    images = {}
    for arm in ARMS:
        for stage in STAGES:
            p = paths.scene(arm, stage, scene)
            images[(arm, stage)] = p if p.is_file() else None
    return {"title": f"Golden scene {scene}", "prompt": prompt,
            "subgenre": needs.get("subgenre_id", ""),
            "rules_label": _rules_label(rules), "order": rules.get("order", "std"),
            "images": images, "items": items}


def _rules_label(rules: dict) -> str:
    g = br.GENRES.get(rules.get("genre", ""))
    shape = g.shape(rules.get("shape") or "") if g else None
    bits = [rules.get("genre", "")]
    if rules.get("preset") and rules["preset"] != "none":
        bits.append(rules["preset"])
    elif shape is not None:
        bits.append(shape.label)
    return " \u203a ".join(b for b in bits if b)


def live(prompt: str, spec: dict, images: dict, guidance, judged: dict) -> dict:
    """A card's worth of data for a prompt that was run in the playground."""
    needs_row = {
        "needs": [{"primitive": n.primitive, "role": n.role, "visual": n.visual}
                  for n in (guidance.needs if guidance else [])],
        "fragments": (guidance.fragments if guidance else []),
        "subgenre_id": f"{guidance.genre} :: {guidance.variation}" if guidance else "",
    }
    rules_row = {"genre": spec.get("genre", ""), "shape": spec.get("shape") or "",
                 "options": spec.get("options") or [],
                 "extras": spec.get("extras") or [],
                 "preset": spec.get("preset") or "none"}
    items = merge_stages(judged.get("iso", []), judged.get("td", []))
    if not items:
        items = [{**r, "iso": {}, "td": {}}
                 for r in tws.requirements(needs_row, rules_row)]
    return {"title": "Playground prompt", "prompt": prompt,
            "subgenre": needs_row["subgenre_id"],
            "rules_label": _rules_label(rules_row),
            "order": spec.get("mode", "std"), "images": images, "items": items}


def requirements_for(spec: dict, guidance) -> list[dict]:
    """The union checklist for a live prompt, before anything has been judged."""
    return tws.requirements(
        {"needs": [{"visual": n.visual} for n in (guidance.needs if guidance else [])],
         "fragments": (guidance.fragments if guidance else [])},
        {"genre": spec.get("genre", ""), "shape": spec.get("shape") or "",
         "options": spec.get("options") or [], "extras": spec.get("extras") or []})


# ---------------------------------------------------------------- drawing

TILE = 452
ORDER_NOTE = {"std": "isometric first, then converted to top-down",
              "p6": "plan first, then dressed into isometric",
              "layout": "authored layout, then top-down, then isometric"}


def _tile(card: Image.Image, path, x: int, y: int, size: int) -> None:
    box = (x, y, x + size, y + size)
    if path is None or not pathlib.Path(path).is_file():
        d = ImageDraw.Draw(card)
        d.rectangle(box, fill=PANEL, outline=LINE)
        f = _font(20)
        d.text((x + size / 2, y + size / 2), "not generated", font=f, fill=DIM2,
               anchor="mm")
        return
    with Image.open(path) as im:
        im = im.convert("RGB")
        im = im.resize((size, size), Image.LANCZOS)
        card.paste(im, (x, y))
    ImageDraw.Draw(card).rectangle(box, outline=LINE)


def _ticks(d: ImageDraw.ImageDraw, item: dict, x: int, y: int) -> int:
    """Six marks per requirement: three arms, each with its isometric and top-down.

    Both stages are on the card because they disagree often enough to matter - a
    feature can survive the isometric and be lost in the conversion - and a single
    tick would have to pick one silently.
    """
    box, gap, grp = 17, 4, 15
    for i, arm in enumerate(ARMS):
        for j, stage in enumerate(STAGES):
            verdict = item.get(stage, {}).get(arm)
            x0 = x + i * (2 * box + gap + grp) + j * (box + gap)
            r = (x0, y, x0 + box, y + box)
            if verdict is None:
                d.rectangle(r, outline=MISS)
                d.line([(x0 + 5, y + box / 2), (x0 + box - 5, y + box / 2)], fill=MISS)
            elif verdict:
                d.rectangle(r, fill=OK)
                d.line([(x0 + 4, y + 9), (x0 + 7, y + box - 5)], fill=BG, width=2)
                d.line([(x0 + 7, y + box - 5), (x0 + box - 3, y + 4)], fill=BG, width=2)
            else:
                d.rectangle(r, outline=MISS)
    return 3 * (2 * box + gap + grp) - grp


def _tick_header(d: ImageDraw.ImageDraw, x: int, y: int) -> None:
    box, gap, grp = 17, 4, 15
    small, tiny = _font(13, True), _font(11)
    for i, arm in enumerate(ARMS):
        x0 = x + i * (2 * box + gap + grp)
        d.text((x0, y), ARM_TICK[arm], font=small, fill=ACCENT[arm])
        d.text((x0 + 1, y + 15), "iso", font=tiny, fill=DIM2)
        d.text((x0 + box + gap + 1, y + 15), "top", font=tiny, fill=DIM2)


def render(data: dict) -> Image.Image:
    """The card: header, prompt, the three arms, then the checklist in two columns."""
    items = data["items"]
    left = [it for it in items if it["source"] == "needs"]
    right = [it for it in items if it["source"] == "rules"]

    f_title, f_meta = _font(34, True), _font(20)
    f_h4 = _font(15, True)
    f_prompt = _font(21)
    f_arm, f_armsub = _font(25, True), _font(17)
    f_lab, f_txt = _font(18, True), _font(17)

    col_w = (W - 3 * PAD) // 2
    tick_w = 3 * (2 * 17 + 4 + 15) - 15
    text_w = col_w - tick_w - 30

    prompt_lines = _wrap(data["prompt"], f_prompt, W - 2 * PAD, cap=6)

    def lines_of(it: dict) -> list[str]:
        # Measured against the bold face the first line is drawn in, since that is
        # the widest of the two and the ticks sit immediately to the right.
        return _wrap(f"{it['label']} \u2014 {it['text']}", f_lab, text_w, cap=4)

    def block(rows: list[dict]) -> int:
        return sum(max(len(lines_of(it)) * 23 + 16, 46) for it in rows)

    head_h = 96
    prompt_h = 42 + len(prompt_lines) * 29 + 24
    arms_h = 46 + 2 * (TILE + 8) + 30
    list_h = 74 + max(block(left), block(right)) + 30
    H = head_h + prompt_h + arms_h + list_h

    card = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(card)

    # header
    d.rectangle([0, 0, W, head_h], fill=PANEL)
    d.line([(0, head_h), (W, head_h)], fill=LINE)
    d.text((PAD, 26), data["title"], font=f_title, fill=FG)
    sub = " \u00b7 ".join(x for x in [data["rules_label"],
                                     ORDER_NOTE.get(data["order"], "")] if x)
    d.text((PAD, 64), sub, font=f_meta, fill=DIM)
    stamp = datetime.date.today().strftime("%d %b %Y")
    d.text((W - PAD, 34), "PROMPT CARD", font=f_h4, fill=DIM2, anchor="ra")
    d.text((W - PAD, 58), stamp, font=f_meta, fill=DIM2, anchor="ra")

    y = head_h + 24
    d.text((PAD, y), "THE PROMPT", font=f_h4, fill=DIM2)
    y += 26
    for ln in prompt_lines:
        d.text((PAD, y), ln, font=f_prompt, fill=FG)
        y += 29
    y += 24

    # the three arms
    span = 3 * TILE + 2 * 22
    x0 = (W - span) // 2
    for i, arm in enumerate(ARMS):
        x = x0 + i * (TILE + 22)
        d.text((x, y), ARM_TITLE[arm], font=f_arm, fill=ACCENT[arm])
        d.text((x, y + 27), ARM_SUB[arm], font=f_armsub, fill=DIM2)
        met = {st: sum(1 for it in items if it.get(st, {}).get(arm)) for st in STAGES}
        if any(it.get("iso") for it in items):
            d.text((x + TILE, y + 6),
                   f"met  iso {met['iso']}/{len(items)}  \u00b7  "
                   f"top {met['td']}/{len(items)}",
                   font=f_armsub, fill=DIM, anchor="ra")
        for j, stage in enumerate(STAGES):
            ty = y + 46 + j * (TILE + 8)
            _tile(card, data["images"].get((arm, stage)), x, ty, TILE)
            # A caption band, because a pale scene swallows plain white text.
            d.rectangle([x, ty + TILE - 28, x + TILE, ty + TILE], fill=(10, 13, 18))
            d.text((x + 9, ty + TILE - 24), STAGE_LABEL[stage], font=f_h4, fill=FG)
    y += 46 + 2 * (TILE + 8) + 22

    # the checklist
    d.line([(PAD, y), (W - PAD, y)], fill=LINE)
    y += 18
    heads = [("Yesterday \u2014 sub-genre Hard Needs",
              data["subgenre"] or "no sub-genre resolved", left),
             ("Today \u2014 Build.md Part II",
              data["rules_label"] or "nothing picked", right)]
    for c, (title, note, rows) in enumerate(heads):
        cx = PAD + c * (col_w + PAD)
        d.text((cx, y), title, font=_font(21, True), fill=FG)
        d.text((cx, y + 27), note, font=f_armsub, fill=DIM2)
        _tick_header(d, cx + text_w + 30, y + 4)
        ry = y + 56
        if not rows:
            d.text((cx, ry), "nothing was required", font=f_txt, fill=DIM2)
        for it in rows:
            lines = lines_of(it)
            _ticks(d, it, cx + text_w + 30, ry + 2)
            for k, ln in enumerate(lines):
                d.text((cx, ry + k * 23), ln, font=f_lab if k == 0 else f_txt,
                       fill=FG if k == 0 else DIM)
            ry += max(len(lines) * 23 + 16, 46)
    return card


def write(data: dict, dest: pathlib.Path) -> pathlib.Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    render(data).save(dest, format="PNG")
    return dest


# ---------------------------------------------------------------- live arms

def build_arms(source: str, addendum: str, gen, dest: pathlib.Path,
               stem: str) -> dict:
    """Generate the raw and yesterday arms for a prompt the playground just ran.

    Both use the golden set's own wrappers, and the top-down prompt is the same for
    every arm - only the isometric it converts differs - so the three arms differ by
    exactly the thing being compared and nothing else.

    The two arms run side by side. Each is a chain of two calls that has to stay in
    order, but the arms have nothing to say to each other, so serialising them would
    only double the wait.
    """
    from concurrent.futures import ThreadPoolExecutor

    def arm(name: str, add: str) -> tuple[str, pathlib.Path, pathlib.Path]:
        iso, td = dest / f"{stem}_{name}_iso.png", dest / f"{stem}_{name}_td.png"
        if not iso.is_file():
            gen(prompts.isometric(source, add), iso)
        if not td.is_file():
            gen(prompts.topdown(source), td, [iso])
        return name, iso, td

    out = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for name, iso, td in pool.map(lambda kv: arm(*kv),
                                      [("raw", ""), ("needs", addendum)]):
            out[(name, "iso")], out[(name, "td")] = iso, td
    return out


def judge_live(items: list[dict], images: dict, key: int,
               thumbs: pathlib.Path) -> dict:
    """Run the blinded judge over a live trio, one call per stage."""
    marked = {}
    for stage in STAGES:
        shots = {}
        for arm in ARMS:
            src = images.get((arm, stage))
            dest = thumbs / f"{stage}_{arm}.jpg"
            if src is None or not rsc.thumb(pathlib.Path(src), dest):
                shots = {}
                break
            shots[arm] = dest
        if not shots:
            continue
        got = tws.judge_paths(items, shots, key)
        if got:
            marked[stage] = got[0]
    return marked


# ---------------------------------------------------------------- cli

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", default="", help="one golden scene, e.g. 0025")
    ap.add_argument("--all", action="store_true", help="every scored golden scene")
    ap.add_argument("--outdir", default=str(CARDS))
    args = ap.parse_args()

    out = pathlib.Path(args.outdir)
    scenes = []
    if args.scene:
        scenes = [args.scene]
    elif args.all:
        scenes = sorted({json.loads(x)["scene"]
                         for x in (paths.RUNS / "rules.jsonl").open()
                         if x.strip()})
    else:
        ap.error("pass --scene or --all")

    for s in scenes:
        try:
            path = write(stored(s), out / f"card_{s}.png")
        except KeyError as exc:
            print(f"  {s}: {exc}")
            continue
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
