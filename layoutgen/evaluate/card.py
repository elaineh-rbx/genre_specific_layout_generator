"""One downloadable card per prompt: every arm's images, and what each was asked for.

A card answers a single question at a glance - what did this prompt look like under
each arm - and then shows the checklist they were judged against, so the pictures and
the requirements sit on the same sheet instead of on two different pages.

It is drawn from a comparison, so its width is however many arms that comparison has.
The tiles shrink to fit and the checklist gets one column per asking arm; nothing here
counts to three.

Two sources, one layout:

  stored    any of the 75 golden scenes, assembled from the runs and the blinded
            scores already on disk, so a card costs nothing to make.
  live      a prompt typed into the playground, which has only today's arm. The
            other two are generated the way the golden set generated them, and the
            trio then goes through the same blinded judge, so a live card's ticks
            mean what a stored card's ticks mean.

Usage:
    python -m layoutgen.evaluate.card --scene 0025
    python -m layoutgen.evaluate.card --all --comparison rules_vs_raw
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib

from PIL import Image, ImageDraw, ImageFont

from layoutgen import arms as A
from layoutgen import paths
from layoutgen.evaluate import judge as J
from layoutgen.evaluate import score as sc
from layoutgen.model import rules as br
from layoutgen.paths import PROMPTS as MANIFEST
from layoutgen.pipeline import prompts

CARDS = paths.RUN / "cards"

#: Which arms a card shows, unless one is passed in. The widest comparison, because a
#: card is a thing you hand someone, and the more arms it holds the more it settles.
DEFAULT = "all_arms"
STAGES = paths.STAGES
STAGE_LABEL = {"iso": "isometric", "td": "top-down"}

BG = (13, 17, 23)
PANEL = (20, 27, 38)
LINE = (37, 48, 63)
FG = (230, 237, 243)
DIM = (159, 176, 195)
DIM2 = (111, 130, 150)
OK = (63, 185, 80)
MISS = (60, 72, 88)


def rgb(hex_colour: str) -> tuple[int, int, int]:
    """An arm's accent, as Pillow wants it. The pages state it once, in hex."""
    h = hex_colour.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

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


def merge_stages(iso_items: list[dict], td_items: list[dict], arms) -> list[dict]:
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
                    "iso": {a: bool(it["present"].get(a)) for a in arms},
                    "td": {a: bool(td.get("present", {}).get(a)) for a in arms}})
    return out


def stored(scene: str, cmp: A.Comparison | None = None) -> dict:
    """A card's worth of data for one golden scene, entirely from disk."""
    cmp = cmp or A.COMPARISONS[DEFAULT]

    def rows(path: pathlib.Path) -> dict:
        if not path.is_file():
            return {}
        return {json.loads(x)["scene"]: json.loads(x)
                for x in path.open() if x.strip()}

    run_rows = {a.id: rows(paths.RUNS / f"{a.run}.jsonl").get(scene) for a in cmp.runs}
    if any(r is None for r in run_rows.values()):
        raise KeyError(f"scene {scene} has no stored run")
    iso = rows(cmp.scores("iso")).get(scene, {})
    td = rows(cmp.scores("td")).get(scene, {})
    items = merge_stages(iso.get("items", []), td.get("items", []), cmp.arms)
    if not items:
        # Unjudged, so show what was asked for without pretending to a verdict.
        items = [{**r, "iso": {}, "td": {}}
                 for r in cmp.requirements(run_rows, scene)]

    rules = run_rows.get("rules", {})
    needs = run_rows.get("needs", {})
    prompt = next((r.get("prompt") for r in run_rows.values() if r.get("prompt")), "")
    if not prompt and MANIFEST.is_file():
        for x in MANIFEST.open():
            if x.strip() and (m := json.loads(x))["scene"] == scene:
                prompt = m["source_prompt"]
                break

    images = {}
    for arm in cmp.arms:
        for stage in STAGES:
            p = paths.scene(arm, stage, scene)
            images[(arm, stage)] = p if p.is_file() else None
    return {"comparison": cmp.id, "title": f"Golden scene {scene}", "prompt": prompt,
            "subgenre": needs.get("subgenre_id", ""),
            "rules_label": _rules_label(rules), "order": rules.get("order", "std"),
            "notes": {a.id: A.ARMS[a.id].group(run_rows.get(a.id, {})) for a in cmp.asking},
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


def rows_for_live(spec: dict, guidance) -> dict[str, dict]:
    """A run row per arm for a prompt that has never been through a batch run.

    The pages and the judge both work from run rows, so the playground fabricates the
    rows the golden set would have written. Anything an arm's `asks` reads has to be
    here; anything else is decoration.
    """
    needs_row = {
        "needs": [{"primitive": n.primitive, "role": n.role, "visual": n.visual}
                  for n in (guidance.needs if guidance else [])],
        "fragments": (guidance.fragments if guidance else []),
        "subgenre_id": f"{guidance.genre} :: {guidance.variation}" if guidance else "",
        "addendum": guidance.addendum if guidance else "",
    }
    rules_row = {"genre": spec.get("genre", ""), "shape": spec.get("shape") or "",
                 "options": spec.get("options") or [],
                 "extras": spec.get("extras") or [],
                 "preset": spec.get("preset") or "none"}
    return {"needs": needs_row, "rules": rules_row}


def live(prompt: str, spec: dict, images: dict, guidance, judged: dict,
         cmp: A.Comparison | None = None) -> dict:
    """A card's worth of data for a prompt that was run in the playground."""
    cmp = cmp or A.COMPARISONS[DEFAULT]
    rows = rows_for_live(spec, guidance)
    items = merge_stages(judged.get("iso", []), judged.get("td", []), cmp.arms)
    if not items:
        items = [{**r, "iso": {}, "td": {}} for r in cmp.requirements(rows)]
    return {"comparison": cmp.id, "title": "Playground prompt", "prompt": prompt,
            "subgenre": rows["needs"]["subgenre_id"],
            "rules_label": _rules_label(rows["rules"]),
            "notes": {a.id: a.group(rows.get(a.id, {})) for a in cmp.asking},
            "order": spec.get("mode", "std"), "images": images, "items": items}


def requirements_for(spec: dict, guidance,
                     cmp: A.Comparison | None = None) -> list[dict]:
    """The union checklist for a live prompt, before anything has been judged."""
    cmp = cmp or A.COMPARISONS[DEFAULT]
    return cmp.requirements(rows_for_live(spec, guidance))


# ---------------------------------------------------------------- drawing

#: The largest a tile gets. Fewer arms do not make bigger pictures - a card should
#: look like the same artefact whichever comparison drew it.
TILE_MAX = 452
GUTTER = 22
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


#: One tick: the box, the space to the next box, and the space between arms.
BOX, GAP, GRP = 17, 4, 15


def tick_width(n_arms: int) -> int:
    return n_arms * (2 * BOX + GAP + GRP) - GRP


def _ticks(d: ImageDraw.ImageDraw, item: dict, x: int, y: int, arms) -> int:
    """Two marks per arm per requirement: its isometric and its top-down.

    Both stages are on the card because they disagree often enough to matter - a
    feature can survive the isometric and be lost in the conversion - and a single
    tick would have to pick one silently.
    """
    box, gap, grp = BOX, GAP, GRP
    for i, arm in enumerate(arms):
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
    return tick_width(len(arms))


def _tick_header(d: ImageDraw.ImageDraw, x: int, y: int, arms) -> None:
    box, gap, grp = BOX, GAP, GRP
    small, tiny = _font(13, True), _font(11)
    for i, arm in enumerate(arms):
        x0 = x + i * (2 * box + gap + grp)
        d.text((x0, y), arm.short, font=small, fill=rgb(arm.accent))
        d.text((x0 + 1, y + 15), "iso", font=tiny, fill=DIM2)
        d.text((x0 + box + gap + 1, y + 15), "top", font=tiny, fill=DIM2)


def render(data: dict, cmp: A.Comparison | None = None) -> Image.Image:
    """The card: header, prompt, one tile column per arm, then the checklist.

    Everything below is measured before anything is drawn, because the height depends
    on how long the prompt wrapped and how many requirements the longest column holds,
    and a card that guessed would either clip its last row or trail blank space.
    """
    cmp = cmp or A.COMPARISONS[data.get("comparison") or DEFAULT]
    arms = list(cmp)
    items = data["items"]
    columns = [(a, [it for it in items if it["source"] == a.id]) for a in cmp.asking]

    f_title, f_meta = _font(34, True), _font(20)
    f_h4 = _font(15, True)
    f_prompt = _font(21)
    f_arm, f_armsub = _font(25, True), _font(17)
    f_lab, f_txt = _font(18, True), _font(17)

    tile = min(TILE_MAX, (W - 2 * PAD - (len(arms) - 1) * GUTTER) // len(arms))
    n_col = max(len(columns), 1)
    col_w = (W - (n_col + 1) * PAD) // n_col
    text_w = col_w - tick_width(len(arms)) - 30

    prompt_lines = _wrap(data["prompt"], f_prompt, W - 2 * PAD, cap=6)

    def lines_of(it: dict) -> list[str]:
        # Measured against the bold face the first line is drawn in, since that is
        # the widest of the two and the ticks sit immediately to the right.
        return _wrap(f"{it['label']} \u2014 {it['text']}", f_lab, text_w, cap=4)

    def block(rows: list[dict]) -> int:
        return sum(max(len(lines_of(it)) * 23 + 16, 46) for it in rows)

    head_h = 96
    prompt_h = 42 + len(prompt_lines) * 29 + 24
    arms_h = 46 + 2 * (tile + 8) + 30
    list_h = 74 + max([block(rows) for _, rows in columns] or [0]) + 30
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

    # one column of tiles per arm
    span = len(arms) * tile + (len(arms) - 1) * GUTTER
    x0 = (W - span) // 2
    judged = any(it.get("iso") for it in items)
    for i, arm in enumerate(arms):
        x = x0 + i * (tile + GUTTER)
        title = arm.title.upper()
        d.text((x, y), title, font=f_arm, fill=rgb(arm.accent))
        d.text((x, y + 27), arm.sub, font=f_armsub, fill=DIM2)
        met = {st: sum(1 for it in items if it.get(st, {}).get(arm.id))
               for st in STAGES}
        if judged:
            tally = (f"met  iso {met['iso']}/{len(items)}  \u00b7  "
                     f"top {met['td']}/{len(items)}")
            # Beside the title if it fits, on the subtitle line if not. More arms mean
            # narrower tiles, and a tally printed over the arm's own name is worse
            # than one printed a line lower.
            room = tile - f_armsub.getlength(tally) - 12
            row = (y + 6 if f_arm.getlength(title) < room
                   else y + 29 if f_armsub.getlength(arm.sub) < room else None)
            if row is not None:
                d.text((x + tile, row), tally, font=f_armsub, fill=DIM, anchor="ra")
        for j, stage in enumerate(STAGES):
            ty = y + 46 + j * (tile + 8)
            _tile(card, data["images"].get((arm.id, stage)), x, ty, tile)
            # A caption band, because a pale scene swallows plain white text.
            d.rectangle([x, ty + tile - 28, x + tile, ty + tile], fill=(10, 13, 18))
            d.text((x + 9, ty + tile - 24), STAGE_LABEL[stage], font=f_h4, fill=FG)
    y += 46 + 2 * (tile + 8) + 22

    # the checklist, one column per arm that asked for something
    d.line([(PAD, y), (W - PAD, y)], fill=LINE)
    y += 18
    for c, (arm, rows) in enumerate(columns):
        cx = PAD + c * (col_w + PAD)
        d.text((cx, y), arm.title, font=_font(21, True), fill=rgb(arm.accent))
        d.text((cx, y + 27), data.get("notes", {}).get(arm.id) or "nothing picked",
               font=f_armsub, fill=DIM2)
        _tick_header(d, cx + text_w + 30, y + 4, arms)
        ry = y + 56
        if not rows:
            d.text((cx, ry), "nothing was required", font=f_txt, fill=DIM2)
        for it in rows:
            lines = lines_of(it)
            _ticks(d, it, cx + text_w + 30, ry + 2, arms)
            for k, ln in enumerate(lines):
                d.text((cx, ry + k * 23), ln, font=f_lab if k == 0 else f_txt,
                       fill=FG if k == 0 else DIM)
            ry += max(len(lines) * 23 + 16, 46)
    return card


def write(data: dict, dest: pathlib.Path,
          cmp: A.Comparison | None = None) -> pathlib.Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    render(data, cmp).save(dest, format="PNG")
    return dest


# ---------------------------------------------------------------- live arms

def build_arms(source: str, addenda: dict[str, str], gen, dest: pathlib.Path,
               stem: str) -> dict:
    """Generate the arms the playground has not already produced.

    `addenda` maps arm to the text that arm injects - empty for a control. Every arm
    uses the golden set's own wrappers, and the top-down prompt is identical across
    arms because only the isometric it converts differs, so the arms differ by exactly
    the thing being compared and nothing else.

    They run side by side. Each is a chain of two calls that has to stay in order, but
    the arms have nothing to say to each other, so serialising them would only
    multiply the wait.
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
    with ThreadPoolExecutor(max_workers=max(len(addenda), 1)) as pool:
        for name, iso, td in pool.map(lambda kv: arm(*kv), list(addenda.items())):
            out[(name, "iso")], out[(name, "td")] = iso, td
    return out


def judge_live(items: list[dict], images: dict, key: int, thumbs: pathlib.Path,
               cmp: A.Comparison | None = None) -> dict:
    """Run the blinded judge over a live set, one call per stage.

    The same judge the golden set went through, so a card built from a prompt someone
    typed a minute ago carries ticks that mean what a stored card's ticks mean.
    """
    cmp = cmp or A.COMPARISONS[DEFAULT]
    marked = {}
    for stage in STAGES:
        shots = {}
        for arm in cmp.arms:
            src = images.get((arm, stage))
            dest = thumbs / f"{stage}_{arm}.jpg"
            if src is None or not sc.thumb(pathlib.Path(src), dest):
                shots = {}
                break
            shots[arm] = dest
        if not shots:
            continue
        got = J.judge(items, shots, key)
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
    ap.add_argument("--comparison", default=DEFAULT, choices=list(A.COMPARISONS),
                    help="which arms the card holds")
    args = ap.parse_args()
    cmp = A.COMPARISONS[args.comparison]

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
            path = write(stored(s, cmp), out / f"card_{s}.png")
        except KeyError as exc:
            print(f"  {s}: {exc}")
            continue
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
