"""Every prompt injection the rules run produced, on one page, plus slide sheets.

The page groups all 75 scenes by genre and shows each one's LAYOUT FEATURES block in
full, so the whole surface of what Build.md Part II actually emitted can be read in
one pass rather than one scene at a time. Above it is the shape of the injection
itself - the fixed header, the shape line, the bullet list - since every block is the
same three parts with different contents.

It also renders 1920x1080 sheets to roadmap_slides/, which Google Slides takes at its
native 16:9: one overview of the whole run, then one sheet per genre carrying that
genre's injections verbatim.

Usage (repo root):
    python -m layoutgen.web.pages.roadmap
"""

from __future__ import annotations

import json
import pathlib
from collections import Counter, defaultdict

from PIL import Image, ImageDraw, ImageFont

from layoutgen import paths
from layoutgen.model import rules as br
from layoutgen.web.pages import shared as brc

OUT = paths.SITE / "roadmap.html"
SLIDES = paths.SITE / "roadmap_slides"

W, H = 1920, 1080
BG, PANEL, LINE = (13, 17, 23), (20, 27, 38), (37, 48, 63)
FG, DIM, DIM2 = (230, 237, 243), (159, 176, 195), (111, 130, 150)
OK, ACC, WARN = (63, 185, 80), (88, 166, 255), (210, 153, 34)


def _font_dir() -> pathlib.Path | None:
    """No system fonts in this image; matplotlib ships DejaVu, which has the arrow
    and bullet glyphs these sheets use. Without it Pillow silently falls back to a
    bitmap font and those render as tofu."""
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


def wrap(draw, text: str, font, width: int, max_lines: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
            if len(lines) == max_lines:
                break
    if line and len(lines) < max_lines:
        lines.append(line)
    if lines and len(lines) == max_lines and draw.textlength(line, font=font) > 0:
        pass
    return lines


def rows() -> list[dict]:
    return [json.loads(x) for x in (paths.RUNS / "rules.jsonl").open() if x.strip()]


# ---------------------------------------------------------------- slide sheets

def _panel(d, box, title=None, tf=None):
    x0, y0, x1, y1 = box
    d.rectangle([x0, y0, x1, y1], fill=PANEL, outline=LINE)
    if title:
        d.text((x0 + 14, y0 + 10), title, fill=DIM, font=tf)


def overview_sheet(data: list[dict]) -> pathlib.Path:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_h1, f_h2 = _font(40, True), _font(19, True)
    f_b, f_s, f_n = _font(17), _font(14), _font(26, True)

    d.text((60, 46), "Prompt injection roadmap", fill=FG, font=f_h1)
    d.text((60, 98), "Build.md Part II across the 75-scene golden set - one shape, "
                     "plus the options the router picked", fill=DIM, font=f_b)

    genres = Counter(r["genre"] for r in data)
    presets = sum(1 for r in data if r["preset"] != "none")
    orders = Counter(r["order"] for r in data)
    opts = sum(len(r["options"]) for r in data) / len(data)
    stats = [(f"{len(data)}", "scenes routed"),
             (f"{len(genres)}", "genres used, of 15"),
             (f"{presets}/{len(data)}", "landed on a preset"),
             (f"{opts:.1f}", "options per scene, mean")]
    for i, (big, small) in enumerate(stats):
        x = 60 + i * 456
        _panel(d, (x, 140, x + 428, 240))
        d.text((x + 18, 158), big, fill=ACC, font=f_n)
        d.text((x + 18, 198), small, fill=DIM, font=f_s)

    # The shape of every injection, which is identical across all 75.
    _panel(d, (60, 264, 900, 620), "THE BLOCK THAT GETS INJECTED", f_h2)
    y = 310
    for label, text in [
        ("1  header", "LAYOUT FEATURES for this <genre> map. Build these as the "
                      "actual structure of the space rather than as set dressing..."),
        ("2  shape", "SHAPE OF THE SPACE - <shape>: <the shape's own wording>"),
        ("3  options", "INCLUDE:  one bullet per picked option, using the visible "
                       "half of its wording"),
    ]:
        d.text((80, y), label, fill=ACC, font=f_h2)
        for ln in wrap(d, text, f_s, 640, 3):
            d.text((208, y + 1), ln, fill=FG, font=f_s)
            y += 21
        y += 16
    d.text((80, y + 4), "Options whose Goes to is `layout` are never injected; a "
                        "`both` option contributes only its visible part.",
           fill=DIM2, font=f_s)

    _panel(d, (930, 264, 1860, 620), "WHERE THE 75 WENT", f_h2)
    y = 310
    for name, n in genres.most_common(11):
        d.rectangle([950, y + 4, 950 + int(360 * n / max(genres.values())), y + 16],
                    fill=ACC if n > 5 else LINE)
        d.text((1330, y), f"{n:2d}  {name}", fill=FG if n > 5 else DIM, font=f_s)
        y += 26

    _panel(d, (60, 646, 1860, 942), "GENERATION ORDER, DECIDED BY THE PICKS", f_h2)
    y = 700
    for key, label, why in [
        ("std", "isometric first, then converted to a top-down",
         "no pipeline flag on the shape or on any picked option"),
        ("p6", "plan first, then the isometric built from it",
         "a P6 flag - the topology is the game, so a render cannot recover it"),
        ("layout", "layout carved outright, then top-down, then isometric",
         "a maze the player routes through, where a generator exists"),
    ]:
        n = orders.get(key, 0)
        bw = max(int(620 * n / len(data)), 44)
        d.rectangle([80, y, 80 + bw, y + 34],
                    fill=ACC if key == "std" else OK if key == "p6" else WARN)
        d.text((94, y + 8), f"{n}", fill=BG, font=f_h2)
        d.text((740, y - 1), label, fill=FG, font=f_h2)
        d.text((740, y + 19), why, fill=DIM2, font=f_s)
        y += 62

    d.text((60, 980), "Everything here is parsed from LayoutGen - Build.md Part II at "
                      "run time, so the tools follow the document rather than a "
                      "hand-copied list.", fill=DIM2, font=f_s)
    p = SLIDES / "00_overview.png"
    im.save(p, quality=95)
    return p


def genre_sheet(genre: str, data: list[dict], idx: int) -> pathlib.Path:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_h1, f_h2, f_s, f_t = _font(34, True), _font(16, True), _font(13), _font(15, True)

    g = br.GENRES.get(genre)
    d.text((60, 40), genre, fill=FG, font=f_h1)
    d.text((60, 86), (g.tagline.strip("*") if g else ""), fill=DIM, font=f_h2)
    d.text((60, 112), f"{len(data)} scene{'s' if len(data) != 1 else ''} in the golden "
                      f"set routed here", fill=DIM2, font=f_s)

    cols, per = 3, 9
    shown = data[: cols * per]
    cw, ch = 590, 292
    for i, r in enumerate(shown[:9]):
        c, rw = i % cols, i // cols
        x0, y0 = 60 + c * (cw + 15), 156 + rw * (ch + 14)
        _panel(d, (x0, y0, x0 + cw, y0 + ch))
        d.text((x0 + 14, y0 + 10), f"{r['scene']}", fill=ACC, font=f_t)
        d.text((x0 + 66, y0 + 11),
               r["preset"] if r["preset"] != "none" else "no preset fitted",
               fill=FG if r["preset"] != "none" else DIM2, font=f_s)
        chips = [r["order"]] + list(r.get("route", []))
        cx = x0 + 14
        for ch_txt in chips:
            wpx = int(d.textlength(ch_txt, font=f_s)) + 14
            d.rectangle([cx, y0 + 34, cx + wpx, y0 + 54], outline=LINE)
            d.text((cx + 7, y0 + 37), ch_txt, fill=DIM, font=f_s)
            cx += wpx + 6

        # Skip the header - it is identical on all 75 and shown once on the overview.
        y = y0 + 64
        for part in r["addendum"].split("\n\n")[1:]:
            for raw in part.split("\n"):
                bullet = raw.startswith("- ")
                colour = ACC if raw.startswith("SHAPE") else FG
                for j, ln in enumerate(wrap(d, raw.lstrip("- "), f_s,
                                            cw - (44 if bullet else 28), 4)):
                    if y > y0 + ch - 22:
                        break
                    if bullet and j == 0:
                        d.text((x0 + 16, y), "\u2022", fill=DIM2, font=f_s)
                    d.text((x0 + (30 if bullet else 14), y), ln, fill=colour, font=f_s)
                    y += 17
            y += 5
    if len(data) > 9:
        d.text((60, H - 40), f"+{len(data) - 9} more scene(s) in this genre",
               fill=DIM2, font=f_s)
    p = SLIDES / f"{idx:02d}_{genre.split(' ')[0].lower().strip('&')}.png"
    im.save(p, quality=95)
    return p


def sheets(data: list[dict]) -> list[pathlib.Path]:
    SLIDES.mkdir(parents=True, exist_ok=True)
    by = defaultdict(list)
    for r in data:
        by[r["genre"]].append(r)
    out = [overview_sheet(data)]
    for i, (genre, rs) in enumerate(
            sorted(by.items(), key=lambda kv: -len(kv[1])), start=1):
        out.append(genre_sheet(genre, sorted(rs, key=lambda r: r["scene"]), i))
    return out


# ---------------------------------------------------------------------- page

def build() -> pathlib.Path:
    data = rows()
    files = [p.name for p in sheets(data)]

    by = defaultdict(list)
    for r in data:
        by[r["genre"]].append(r)
    payload = [{
        "genre": genre,
        "tagline": (br.GENRES[genre].tagline.strip("*") if genre in br.GENRES else ""),
        "scenes": [{
            "scene": r["scene"], "preset": r["preset"], "order": r["order"],
            "route": r.get("route", []), "addendum": r["addendum"],
            "prompt": r["prompt"][:240],
            "held": r.get("held", []),
        } for r in sorted(rs, key=lambda r: r["scene"])],
    } for genre, rs in sorted(by.items(), key=lambda kv: -len(kv[1]))]

    orders = Counter(r["order"] for r in data)
    presets = sum(1 for r in data if r["preset"] != "none")
    head = f"""<div class="sum">
      <div class="card"><b>{len(data)}</b><span>injections, one per scene</span></div>
      <div class="card"><b>{len(by)}</b><span>genres used, of 15</span></div>
      <div class="card"><b>{presets}/{len(data)}</b>
        <span>landed on a preset</span></div>
      <div class="card"><b>{orders['std']} / {orders['p6']} / {orders['layout']}</b>
        <span>isometric-first / plan-first / authored layout</span></div>
    </div>"""

    html = f"""<!doctype html><meta charset="utf-8">
<title>Injection roadmap &mdash; all 75</title>
<style>{brc.CSS}
.slides{{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}}
.slides a{{color:var(--acc);text-decoration:none;font-size:11.5px;
  border:1px solid #2f4a7a;border-radius:6px;padding:3px 9px}}
.gsec{{margin-bottom:18px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:10px}}
.inj{{background:var(--pan);border:1px solid var(--ln);border-radius:9px;padding:10px}}
.inj pre{{font-size:11px;margin-top:6px}}
.inj .hd{{display:flex;gap:6px;align-items:baseline;flex-wrap:wrap}}
</style>
<header><h1>Injection roadmap</h1>{brc.nav("roadmap.html")}
  <span class="sub">every LAYOUT FEATURES block the run produced, grouped by
    genre</span></header>
<div class="main" style="height:calc(100vh - 49px);overflow:auto">
{head}
<div class="sect">
  <h3>The block that gets injected &mdash; identical structure on all 75</h3>
  <pre>LAYOUT FEATURES for this &lt;genre&gt; map. Build these as the actual structure of the
space rather than as set dressing, keep them visually distinct from one another, and
keep the whole layout legible in one view.

SHAPE OF THE SPACE - &lt;shape&gt;: &lt;the shape's own wording from Build.md&gt;

INCLUDE:
- &lt;option label&gt;: &lt;the option's wording, visible half only if it is a `both`&gt;</pre>
  <p class="note">Options whose <b>Goes to</b> is <code>layout</code> never appear here
    &mdash; they are placed against the segmented layout afterwards, and a render
    cannot recover something invisible.</p>
  <h3 style="margin-top:12px">Slide sheets &mdash; 1920&times;1080, native 16:9</h3>
  <div class="slides">{"".join(
      f'<a href="roadmap_slides/{f}" target="_blank">{f}</a>' for f in files)}</div>
</div>
<div id="body"></div>
</div>
<script>
const G={json.dumps(payload)};
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>(
  {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]));
document.getElementById("body").innerHTML=G.map(g=>`
  <div class="sect gsec">
    <h2>${{esc(g.genre)}} <span class="chip">${{g.scenes.length}} scenes</span></h2>
    <p class="note" style="margin-bottom:10px">${{esc(g.tagline)}}</p>
    <div class="grid">${{g.scenes.map(s=>`
      <div class="inj">
        <div class="hd"><b>${{esc(s.scene)}}</b>
          <span class="chip ${{s.preset==="none"?"":"acc"}}">${{
            esc(s.preset==="none"?"no preset":s.preset)}}</span>
          <span class="chip">${{esc(s.order)}}</span>
          ${{s.route.map(r=>`<span class="chip warn">${{esc(r)}}</span>`).join("")}}
        </div>
        <p class="note">${{esc(s.prompt)}}&hellip;</p>
        <pre>${{esc(s.addendum)}}</pre>
        ${{s.held.length?`<p class="note" style="color:var(--warn)">held back:
          ${{s.held.map(esc).join(", ")}}</p>`:""}}
      </div>`).join("")}}</div>
  </div>`).join("");
</script>"""
    OUT.write_text(html, encoding="utf-8")
    return OUT


if __name__ == "__main__":
    p = build()
    n = len(list(SLIDES.glob("*.png")))
    print(f"wrote {p}  ({p.stat().st_size // 1024} KB) and {n} slide sheets")
