"""Build a focused prompt, essential-features, and render comparison viewer.

Usage:
    python tools/build_feature_viewer.py \
      --run-name agent_gateway_gpt55_golden75_260813 \
      --image-arm agent_gateway_gpt55_golden75_260813 \
      --out results/feature_viewer_gpt55_golden75.html
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from layoutgen.paths import RESULTS  # noqa: E402
from build_pipeline_viewer import collect  # noqa: E402


CSS = """
:root{--bg:#0d1018;--panel:#151a25;--panel2:#1b2230;--line:#2b3446;
--text:#edf0f6;--muted:#9ba6b8;--accent:#7aa2ff;--green:#52c995;--orange:#e5a65b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:14px/1.5 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:5;background:rgba(13,16,24,.96);
border-bottom:1px solid var(--line);padding:16px 24px}
.head{max-width:1500px;margin:auto;display:flex;gap:20px;align-items:center}
h1{font-size:20px;margin:0;white-space:nowrap}.sub{color:var(--muted);font-size:12px}
.nav{display:flex;gap:7px;margin-top:7px}.nav a{color:var(--muted);text-decoration:none;
border:1px solid var(--line);border-radius:7px;padding:3px 8px;font-size:11px}
.nav a.active{color:var(--accent);border-color:var(--accent)}
.controls{margin-left:auto;display:flex;gap:10px;flex:1;justify-content:flex-end}
select,input{background:var(--panel2);color:var(--text);border:1px solid var(--line);
border-radius:8px;padding:9px 11px;min-width:220px}input{max-width:260px}
main{max-width:1500px;margin:auto;padding:22px 24px 60px}
.meta{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:16px}.chip{border:1px solid var(--line);
background:var(--panel);border-radius:999px;padding:4px 10px;color:var(--muted);font-size:12px}
.chip strong{color:var(--text)}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
.card h2{font-size:14px;margin:0 0 11px}.wide{grid-column:1/-1}
.prompt{white-space:pre-wrap;color:#d8deea;line-height:1.65}
.images{display:grid;grid-template-columns:1fr 1fr;gap:14px}.image-panel{min-width:0}
.image-panel h3{font-size:12px;color:var(--muted);margin:0 0 8px;text-transform:uppercase;
letter-spacing:.06em}.image-panel img{display:block;width:100%;aspect-ratio:1;object-fit:contain;
background:#080a10;border:1px solid var(--line);border-radius:9px;cursor:zoom-in}
.features{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:9px}
.feature{background:var(--panel2);border:1px solid var(--line);border-radius:9px;padding:11px}
.feature .name{font-weight:650}.origin{float:right;font-size:10px;text-transform:uppercase;
letter-spacing:.05em;color:var(--accent)}.feature .notes,.feature .quote,.where{
color:var(--muted);font-size:12px;margin-top:4px}.feature .quote{font-style:italic;
border-left:2px solid var(--line);padding-left:8px}.layout .origin{color:var(--green)}
.empty{color:var(--muted);font-style:italic}.list{margin:0;padding-left:20px}
.list li{margin:5px 0}.section-label{font-size:11px;color:var(--muted);
text-transform:uppercase;letter-spacing:.06em;margin:13px 0 5px}
.lightbox{display:none;position:fixed;inset:0;background:rgba(0,0,0,.88);z-index:20;
align-items:center;justify-content:center;padding:24px}.lightbox.open{display:flex}
.lightbox img{max-width:95vw;max-height:95vh;object-fit:contain}
@media(max-width:850px){.head{align-items:flex-start;flex-direction:column}.controls{margin:0;
width:100%;justify-content:stretch}.controls>*{min-width:0;flex:1}.grid,.images{grid-template-columns:1fr}}
"""


BODY = """
<header><div class="head">
  <div><h1>Essential features + renders</h1>
  <div class="sub">Input brief, flagged requirements, and generated views</div>
  <nav class="nav"><a class="active" href="/features">Original viewer</a>
    <a href="/pipeline">Pipeline</a>
    <a href="/comparison">GPT Image 2 vs Gemini</a></nav></div>
  <div class="controls">
    <input id="search" placeholder="Filter scene, genre, shape…">
    <select id="picker"></select>
  </div>
</div></header>
<main>
  <div class="meta" id="meta"></div>
  <div class="grid">
    <section class="card wide"><h2>Input prompt</h2><div class="prompt" id="prompt"></div></section>
    <section class="card wide"><h2>Generated images</h2><div class="images">
      <div class="image-panel"><h3>Isometric</h3><img id="iso"></div>
      <div class="image-panel"><h3>Top-down</h3><img id="td"></div>
    </div></section>
    <section class="card wide"><h2>Build.md selections — genre, shape, and config</h2>
      <div class="features" id="buildSelections"></div></section>
    <section class="card wide"><h2>Essential visible features flagged for evaluation</h2>
      <div class="features" id="features"></div></section>
    <section class="card"><h2>Chosen image features</h2><div class="features" id="imageFeatures"></div></section>
    <section class="card layout"><h2>Chosen layout requirements</h2>
      <div class="features" id="placements"></div></section>
    <section class="card wide"><h2>Structured layout summary</h2><div id="layout"></div></section>
    <section class="card wide"><h2>Non-visual asks excluded from image evaluation</h2>
      <div id="excluded"></div></section>
  </div>
</main>
<div class="lightbox" id="lightbox"><img></div>
"""


JS = r"""
const SCENES=__SCENES__;
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",
'"':"&quot;","'":"&#39;"}[c]));
const picker=$("picker"), search=$("search");

function choices(){
  const q=search.value.trim().toLowerCase();
  const keep=SCENES.filter(s=>!q||[s.id,s.genre,s.shape,s.preset,s.prompt]
    .some(v=>String(v||"").toLowerCase().includes(q)));
  const current=picker.value;
  picker.innerHTML=keep.map(s=>`<option value="${esc(s.id)}">${esc(s.id)} · ${esc(s.genre||"No Genre")} · ${esc(s.shape||"described")}</option>`).join("");
  if(keep.length){picker.value=keep.some(s=>s.id===current)?current:keep[0].id;render(picker.value)}
}
function cards(items,kind){
  if(!items?.length)return `<div class="empty">None selected.</div>`;
  return items.map(x=>`<div class="feature ${kind||""}">
    <span class="origin">${esc(x.origin||x.id||kind||"feature")}</span>
    <div class="name">${esc(x.name||x.label||x.id)}</div>
    ${x.text?`<div class="notes">${esc(x.text)}</div>`:""}
    ${x.notes?`<div class="notes">${esc(x.notes)}</div>`:""}
    ${x.where?`<div class="where"><strong>Where:</strong> ${esc(x.where)}</div>`:""}
    ${Number.isInteger(x.count)&&x.count>=0?`<div class="notes"><strong>Count:</strong> ${x.count}</div>`:""}
    ${x.quote?`<div class="quote">${esc(x.quote)}</div>`:""}
  </div>`).join("");
}
function render(id){
  const s=SCENES.find(x=>x.id===id);if(!s)return;
  $("meta").innerHTML=[
    ["Scene",s.id],["Genre",s.genre||"No Genre"],["Shape",s.shape||"described"],
    ["Preset",s.preset||"none"],["Order",s.order||"—"],["Route",(s.route||[]).join(" + ")||"P0"]
  ].map(([k,v])=>`<span class="chip"><strong>${esc(k)}:</strong> ${esc(v)}</span>`).join("");
  $("prompt").textContent=s.prompt||"";
  for(const [id,key] of [["iso","iso"],["td","td"]]){
    const img=$(id),src=s.images?.[key]||"";img.src=src;img.dataset.full=src;
    img.style.display=src?"block":"none";
  }
  $("features").innerHTML=cards(s.checklist?.features||[],"essential");
  const shape=s.shape_selection||{}, axes=s.axes_selection||[];
  const build=[
    {name:"Genre",id:s.genre||"No Genre",text:s.genre_route||"No genre-wide route"},
    ...(shape.id?[{name:"Shape · "+shape.label,id:shape.id,text:shape.what,
      where:shape.pipeline?`Pipeline: ${shape.pipeline}`:"Pipeline: P0"}]:
      axes.map(a=>({name:"Axis · "+a.label,id:a.id,text:a.value,
        where:`Default: ${a.default}${a.pipeline?` · Pipeline: ${a.pipeline}`:""}`}))),
    {name:"Preset",id:s.preset||"none",text:s.preset&&s.preset!=="none"?
      "Named bundle used as the starting selection.":"No preset selected."},
    ...(s.options_all||[]).map(o=>({name:`Option · ${o.label}`,id:o.id,text:o.what,
      count:o.count,where:`Goes to: ${o.goes||"unknown"} · Pipeline: ${o.pipeline||"P0"}`}))
  ];
  $("buildSelections").innerHTML=cards(build,"build");
  $("imageFeatures").innerHTML=cards(s.options_img||[],"image");
  $("placements").innerHTML=cards(s.layout_placement||[],"layout");
  const l=s.layout||{};
  const zones=(l.zones||[]).map(z=>`<li><strong>${esc(z.name)}</strong> — ${esc(z.role)} <span class="where">${esc(z.where)}</span></li>`).join("");
  const paths=(l.paths||[]).map(p=>`<li>${esc(p.from)} → ${esc(p.to)} <span class="where">${esc(p.kind)}</span></li>`).join("");
  $("layout").innerHTML=`
    <div>${esc(l.composition||"No composition recorded.")}</div>
    ${zones?`<div class="section-label">Zones</div><ul class="list">${zones}</ul>`:""}
    ${paths?`<div class="section-label">Paths</div><ul class="list">${paths}</ul>`:""}
    ${l.terrain?`<div class="section-label">Terrain</div><div>${esc(l.terrain)}</div>`:""}
    ${l.boundary?`<div class="section-label">Boundary</div><div>${esc(l.boundary)}</div>`:""}`;
  const ex=s.checklist?.excluded||[];
  $("excluded").innerHTML=ex.length?`<ul class="list">${ex.map(x=>`<li><strong>${esc(x.name)}</strong> — ${esc(x.why||"")}</li>`).join("")}</ul>`:
    `<div class="empty">Nothing excluded.</div>`;
}
search.addEventListener("input",choices);picker.addEventListener("change",()=>render(picker.value));
const lb=$("lightbox"),lbImg=lb.querySelector("img");
document.addEventListener("click",e=>{if(e.target.matches(".image-panel img")&&e.target.dataset.full){
  lbImg.src=e.target.dataset.full;lb.classList.add("open")}else if(e.target===lb||e.target===lbImg){
  lb.classList.remove("open");lbImg.src=""}});
choices();
"""


def build_page(rows: list[dict]) -> str:
    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    script = JS.replace("__SCENES__", data)
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>Essential features + renders</title><style>{CSS}</style></head>"
        f"<body>{BODY}<script>{script}</script></body></html>\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", default="agent_gateway")
    parser.add_argument("--image-arm", default="agent_gateway_260813")
    parser.add_argument(
        "--checklist-dir",
        type=pathlib.Path,
        default=RESULTS / "eval",
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=RESULTS / "feature_viewer.html",
    )
    args = parser.parse_args()
    rows = collect(
        args.run_name,
        args.image_arm,
        only_sent=True,
        checklist_dir=args.checklist_dir,
    )
    page = build_page(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page, encoding="utf-8")
    print(f"wrote {args.out} ({len(rows)} scenes, {len(page)//1024} KB)")


if __name__ == "__main__":
    main()
