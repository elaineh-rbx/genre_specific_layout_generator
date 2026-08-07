"""Write the landing page for the viewer set.

It states what each of the other pages is for, so the set can be opened cold by
someone who has never seen it.

    python -m gslg.web.pages.index
"""

from __future__ import annotations

import json
import pathlib
from collections import Counter

from gslg import arms as A
from gslg import paths
from gslg.web.pages.shared import CSS, PLAYGROUND_PATH, nav

OUT = paths.SITE / "index.html"

#: The comparison tiles describe themselves from the registry, so a new comparison is
#: on the landing page as soon as it exists.
CARDS = [
    (c.page, f"{len(c.arms)} arms &mdash; " + ", ".join(a.short for a in c),
     c.blurb + " Any scene, or any set of them, downloads as a card.")
    for c in A.COMPARISONS.values()
] + [
    ("roadmap.html", "Injection roadmap",
     "Every scene's injected block in one place, with 16:9 sheets rendered for slides."),
    ("requirements.html", "Requirements used",
     "Every arm's catalogue of requirements side by side, with how often each was "
     "met - by the arm that asked, and by the arms that did not."),
    ("rules_viewer/index.html", "Genre menu",
     "The Build.md model itself - each genre's shapes, options and presets."),
]


def stats() -> list[tuple[str, str]]:
    run = paths.RUNS / "rules.jsonl"
    if not run.is_file():
        return []
    rows = [json.loads(x) for x in run.open() if x.strip()]
    order = Counter(r["order"] for r in rows)
    return [
        (str(len(rows)), "scenes generated"),
        (str(len({r["genre"] for r in rows})), "genres represented"),
        (str(order["layout"]), "authored layout first"),
        (str(order["p6"]), "plan first"),
    ]


def build() -> pathlib.Path:
    cards = "".join(
        f'<a class="tile" href="{href}"><h4>{label}</h4>'
        f'<p class="note">{blurb}</p></a>' for href, label, blurb in CARDS)
    sums = "".join(f'<div class="card"><b>{n}</b><span>{what}</span></div>'
                   for n, what in stats())
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Layout rules - viewers</title><style>{CSS}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}}
.tile{{background:var(--pan);border:1px solid var(--ln);border-radius:10px;
  padding:13px 15px;text-decoration:none;color:var(--fg);display:block}}
.tile:hover{{border-color:var(--acc)}}
.tile h4{{margin:0 0 5px;font-size:13px;color:var(--acc)}}
.main.solo{{padding:20px 22px 60px}}
</style></head><body>
<header><h1>Layout rules</h1>
  <span class="sub">75 golden scenes, generated from Build.md Part II</span>
  {nav("index.html")}</header>
<div class="main solo">
  <div class="sum">{sums}</div>
  <div class="tiles">{cards}</div>
  <p class="note" style="margin-top:14px">The <a href="{PLAYGROUND_PATH}"
    style="color:var(--acc)">playground</a> is served from here too: pick a genre, a
    shape and any options, and generate from any prompt. Where a layout can be authored
    outright - a maze, a racing circuit or a point-to-point course - it is carved
    locally first and the images are built from it.</p>
</div></body></html>"""
    OUT.write_text(html, encoding="utf-8")
    return OUT


if __name__ == "__main__":
    p = build()
    print(f"wrote {p}  ({p.stat().st_size // 1024} KB)")
