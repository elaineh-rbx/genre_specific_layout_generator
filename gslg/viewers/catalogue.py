"""Build the per-genre viewer for the Build.md Part II layout model.

Shows, for each of the fifteen genres, the shape choices, the full option menu, and
every preset with the exact prompt injection it produces - so the variation between
genres, and between presets inside a genre, is readable side by side.

The `Goes to` column is given the same weight it has in the document: an option
marked `layout` is invisible, cannot survive segmentation, and is shown struck out
of the injection rather than silently dropped.

    python -m gslg.viewers.catalogue
"""

from __future__ import annotations

import json
import pathlib

from gslg import paths
from gslg import rules as br

ROOT = paths.SITE / "rules_viewer"
OUT = ROOT / "index.html"


def payload() -> dict:
    descs = dict(br.GENRE_DESCS)
    genres = []
    for g in br.GENRES.values():
        presets = []
        for p in g.presets:
            shape = g.shape(p.shape)
            picks = [g.option(o) for o in p.options]
            presets.append({
                "name": p.name, "ref": p.modelled_on,
                "shape": p.shape, "shapeLabel": shape.label if shape else "",
                "options": p.options,
                "drawn": [o.label for o in picks if o and o.drawn],
                "held": [o.label for o in picks if o and not o.drawn],
                "route": br.route_of(g, shape, p.options),
                "injection": br.injection(g, shape, p.options),
            })
        genres.append({
            "name": g.name, "num": g.num,
            "desc": descs.get(g.name, g.tagline), "tagline": g.tagline,
            "route": g.route, "notes": g.notes,
            "shapes": [{"id": s.id, "label": s.label, "type": s.type, "what": s.what,
                        "pipeline": s.pipeline} for s in g.shapes],
            "options": [{"id": o.id, "label": o.label, "type": o.type, "what": o.what,
                         "inject": br.visible_text(g.name, o),
                         "core": o.core, "goes": o.goes_to, "pipeline": o.pipeline,
                         "shared": br.SHARED_IDS.get(o.id, [])} for o in g.options],
            "presets": presets,
        })
    return {"genres": genres, "shared": br.SHARED_IDS,
            "header": br.HEADER, "shapeLine": br.SHAPE_LINE}


TEMPLATE = r"""<!doctype html>
<meta charset="utf-8"><title>Genre layout options &amp; prompt injections</title>
<style>
 :root{--bg:#0d1117;--panel:#141b26;--panel2:#1b2433;--line:#25303f;--fg:#e6edf3;
  --dim:#9fb0c3;--dim2:#6f8296;--ok:#3fb950;--warn:#d29922;--bad:#f85149;--accent:#58a6ff}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--fg);
  font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
 header{padding:13px 22px;border-bottom:1px solid var(--line);background:var(--panel)}
 h1{margin:0;font-size:15px} header p{margin:3px 0 0;color:var(--dim2);font-size:12px}
 .wrap{display:grid;grid-template-columns:250px 1fr;height:calc(100vh - 60px)}
 .nav{overflow-y:auto;border-right:1px solid var(--line);background:var(--panel)}
 .main{overflow-y:auto;padding:20px 26px}
 .g{padding:8px 14px;border-bottom:1px solid var(--line);cursor:pointer;font-size:12.5px}
 .g:hover{background:var(--panel2)}
 .g.on{background:var(--panel2);border-left:3px solid var(--accent);padding-left:11px}
 .g .n{color:var(--dim2);font-size:11px;margin-right:5px}
 .g .c{color:var(--dim2);font-size:10.5px;float:right}
 h2{margin:0 0 3px;font-size:19px} h3{margin:26px 0 9px;font-size:12px;
  letter-spacing:.06em;text-transform:uppercase;color:var(--dim2)}
 .lead{color:var(--dim);margin:0 0 4px}
 .route{color:var(--warn);font-size:12.5px;margin:8px 0 0;border-left:2px solid #4a3d24;
  padding-left:10px}
 table{border-collapse:collapse;width:100%;font-size:12.5px}
 th{text-align:left;font-size:10px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--dim2);font-weight:600;padding:5px 9px;border-bottom:1px solid var(--line)}
 td{padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}
 tr:hover td{background:var(--panel)}
 td.w{color:var(--dim)}
 code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.5px;
  color:var(--dim2)}
 .badge{font-size:9.5px;letter-spacing:.05em;text-transform:uppercase;padding:1px 6px;
  border-radius:9px;border:1px solid var(--line);color:var(--dim2);white-space:nowrap}
 .badge.image{color:var(--ok);border-color:#265340}
 .badge.both{color:var(--accent);border-color:#2f4a7a}
 .badge.layout{color:var(--warn);border-color:#4a3d24}
 .chip{font-size:10.5px;padding:1px 8px;border-radius:11px;border:1px solid var(--line);
  color:var(--dim);white-space:nowrap}
 .chip.warn{color:var(--warn);border-color:#4a3d24}
 .chip.acc{color:var(--accent);border-color:#2f4a7a}
 .core{color:var(--ok)}
 .p{background:var(--panel);border:1px solid var(--line);border-radius:8px;
  margin-bottom:10px;overflow:hidden}
 .p .h{padding:9px 13px;cursor:pointer;display:flex;align-items:center;gap:9px;
  flex-wrap:wrap}
 .p .h:hover{background:var(--panel2)}
 .p .h b{font-size:13px} .p .h .r{color:var(--dim2);font-size:11px;flex:1}
 .p .body{border-top:1px solid var(--line);padding:12px 13px;display:none}
 .p.open .body{display:block}
 pre{background:var(--bg);border:1px solid var(--line);border-radius:7px;
  padding:12px 14px;font-size:12px;line-height:1.55;white-space:pre-wrap;margin:0;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--dim)}
 pre b{color:var(--ok);font-weight:600}
 .vis{margin-top:4px;padding-left:8px;border-left:2px solid #265340;color:var(--ok);
  font-size:11.5px}
 .vis b{color:var(--dim2);font-weight:600}
 .held{color:var(--warn);font-size:11.5px;margin-top:9px}
 .held s{color:var(--dim2)}
 ul.notes{margin:0;padding-left:18px;color:var(--dim);font-size:12.5px}
 ul.notes li{margin-bottom:5px}
 .sum{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
</style>
<header>
  <h1>Genre layout options &amp; prompt injections</h1>
  <p>Build.md Part II. Each genre is a menu: one <b>shape</b>, any <b>options</b> on
  top, and a <b>preset</b> is a shape plus a few option IDs. Nothing is mandatory
  &mdash; picking nothing injects nothing.</p>
</header>
<div class="wrap">
  <div class="nav" id="nav"></div>
  <div class="main" id="main"></div>
</div>
<script>
const DATA=__DATA__;
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
let gi=0;

function nav(){
  $("nav").innerHTML=DATA.genres.map((g,i)=>`<div class="g ${i===gi?"on":""}" data-g="${i}">
    <span class="n">${g.num}</span>${esc(g.name)}
    <span class="c">${g.presets.length}p</span></div>`).join("");
  $("nav").querySelectorAll("[data-g]").forEach(el=>
    el.onclick=()=>{ gi=+el.dataset.g; nav(); main(); $("main").scrollTop=0; });
}
function main(){
  const g=DATA.genres[gi];
  const drawn=g.options.filter(o=>o.goes!=="layout").length;
  $("main").innerHTML=`
    <h2>${esc(g.name)}</h2>
    <p class="lead">${esc(g.desc)}</p>
    <div class="sum">
      <span class="chip">${g.shapes.length} shapes</span>
      <span class="chip">${g.options.length} options</span>
      <span class="chip ok">${drawn} reach the image</span>
      <span class="chip warn">${g.options.length-drawn} never drawn</span>
      <span class="chip">${g.presets.length} presets</span></div>
    ${g.route?`<p class="route">${esc(g.route)}</p>`:""}

    <h3>Shape &mdash; pick exactly one</h3>
    <table><tr><th>Shape</th><th>What it is</th><th>Pipeline</th></tr>
    ${g.shapes.map(s=>`<tr><td><b>${esc(s.label)}</b>${s.type?`<br><code>${esc(s.type)}</code>`:""}
      <br><code>${esc(s.id)}</code></td>
      <td class="w">${esc(s.what)}</td>
      <td>${s.pipeline?`<span class="chip warn">${esc(s.pipeline)}</span>`:
        `<span class="chip">P0</span>`}</td></tr>`).join("")}</table>

    <h3>Options &mdash; combine freely</h3>
    <table><tr><th>Option</th><th>What it is</th><th>Goes to</th><th>Pipeline</th></tr>
    ${g.options.map(o=>`<tr><td><b>${esc(o.label)}</b>
      ${o.core?'<span class="core"> \u25cf</span>':""}
      <br><code>${esc(o.id)}</code>
      ${o.shared.length>1?`<br><span class="chip">shared \u00d7${o.shared.length}</span>`:""}</td>
      <td class="w">${esc(o.what)}
        ${o.inject!==o.what?`<div class="vis"><b>injected:</b> ${esc(o.inject)}</div>`:""}</td>
      <td><span class="badge ${esc(o.goes)}">${esc(o.goes)}</span></td>
      <td>${o.pipeline?`<span class="chip warn">${esc(o.pipeline)}</span>`:""}</td></tr>`
      ).join("")}</table>

    <h3>Presets &mdash; and the injection each produces</h3>
    ${g.presets.map((p,i)=>`<div class="p" data-p="${i}">
      <div class="h"><b>${esc(p.name)}</b>
        <span class="chip acc">${esc(p.shapeLabel)}</span>
        ${p.route.map(r=>`<span class="chip warn">${esc(r)}</span>`).join("")}
        <span class="r">modelled on ${esc(p.ref)}</span>
        <span class="chip">${p.drawn.length} drawn${p.held.length?
          " \u00b7 "+p.held.length+" held":""}</span></div>
      <div class="body">
        <pre>${esc(p.injection)||"<i>nothing injected</i>"}</pre>
        ${p.held.length?`<p class="held">Withheld from the image, invisible to a
          segmenter: ${p.held.map(x=>`<s>${esc(x)}</s>`).join(", ")} &mdash; placed
          against the layout after segmentation.</p>`:""}
      </div></div>`).join("")}

    <h3>Genre notes</h3>
    <ul class="notes">${g.notes.map(n=>`<li>${esc(n)}</li>`).join("")}</ul>`;
  $("main").querySelectorAll("[data-p]").forEach(el=>
    el.querySelector(".h").onclick=()=>el.classList.toggle("open"));
  const first=$("main").querySelector("[data-p]");
  if(first) first.classList.add("open");
}
nav(); main();
</script>
"""


def build() -> pathlib.Path:
    ROOT.mkdir(parents=True, exist_ok=True)
    html = TEMPLATE.replace("__DATA__", json.dumps(payload()))
    OUT.write_text(html)
    return OUT


if __name__ == "__main__":
    p = build()
    d = payload()
    print(f"{p}  {p.stat().st_size/1024:.0f} KB")
    print(f"  {len(d['genres'])} genres, "
          f"{sum(len(g['shapes']) for g in d['genres'])} shapes, "
          f"{sum(len(g['options']) for g in d['genres'])} options, "
          f"{sum(len(g['presets']) for g in d['genres'])} presets")
