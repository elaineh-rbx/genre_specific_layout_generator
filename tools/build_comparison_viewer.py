"""Build the August 6 versus August 13 golden-render comparison page."""

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
--text:#edf0f6;--muted:#9ba6b8;--accent:#7aa2ff;--old:#e5a65b;--new:#52c995}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:14px/1.5 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:5;background:rgba(13,16,24,.96);
border-bottom:1px solid var(--line);padding:15px 24px}.head{max-width:1600px;margin:auto;
display:flex;gap:20px;align-items:center}h1{font-size:20px;margin:0}.sub{font-size:12px;color:var(--muted)}
.nav{display:flex;gap:7px;margin-top:7px}.nav a{color:var(--muted);text-decoration:none;
border:1px solid var(--line);border-radius:7px;padding:3px 8px;font-size:11px}
.nav a.active{color:var(--accent);border-color:var(--accent)}
.controls{margin-left:auto;display:flex;gap:9px}select,input{background:var(--panel2);
color:var(--text);border:1px solid var(--line);border-radius:8px;padding:9px 11px;min-width:230px}
main{max-width:1600px;margin:auto;padding:20px 24px 60px}.meta{display:flex;gap:7px;
flex-wrap:wrap;margin-bottom:14px}.chip{border:1px solid var(--line);background:var(--panel);
border-radius:999px;padding:4px 10px;color:var(--muted);font-size:12px}.chip strong{color:var(--text)}
.prompt{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:14px;
white-space:pre-wrap;margin-bottom:16px;line-height:1.6}.grid{display:grid;
grid-template-columns:1fr 1fr;gap:14px}.group{background:var(--panel);border:1px solid var(--line);
border-radius:12px;padding:13px}.group h2{font-size:14px;margin:0 0 10px;display:flex;
justify-content:space-between}.old h2{color:var(--old)}.new h2{color:var(--new)}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:11px}.pane h3{font-size:11px;color:var(--muted);
margin:0 0 6px;text-transform:uppercase;letter-spacing:.06em}.pane img{display:block;width:100%;
aspect-ratio:1;object-fit:contain;background:#080a10;border:1px solid var(--line);
border-radius:8px;cursor:zoom-in}.config-card{margin-top:13px;background:#10151f;
border:1px solid var(--line);border-radius:10px;padding:12px}.config-card h3{font-size:13px;
margin:0}.config-card .config-sub{color:var(--muted);font-size:11px;margin:2px 0 9px}
.model-prompt{margin-top:7px}.model-prompt details{background:#10151f;border:1px solid var(--line);
border-radius:7px;padding:7px 9px}.model-prompt summary{cursor:pointer;color:var(--accent);
font-size:11px}.model-prompt pre{white-space:pre-wrap;overflow-wrap:anywhere;color:var(--muted);
font:10px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;margin:8px 0 2px;
max-height:360px;overflow:auto}.missing-prompt{color:var(--muted);font-size:10px;margin-top:7px}
.feature-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px}
.feature{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:9px}
.feature strong{display:block}.feature .origin{float:right;color:var(--accent);font-size:9px;
text-transform:uppercase;letter-spacing:.05em}.feature span,.feature .quote{
color:var(--muted);font-size:11px}.feature .quote{font-style:italic;margin-top:4px;
border-left:2px solid var(--line);padding-left:7px}
.lightbox{display:none;position:fixed;inset:0;background:rgba(0,0,0,.9);z-index:20;
align-items:center;justify-content:center;padding:20px}.lightbox.open{display:flex}
.lightbox img{max-width:96vw;max-height:96vh;object-fit:contain}
@media(max-width:900px){.head{flex-direction:column;align-items:flex-start}.controls{margin:0;width:100%}
.controls>*{min-width:0;flex:1}.grid,.pair{grid-template-columns:1fr}}
"""

BODY = """
<header><div class="head">
  <div><h1>Golden image comparison</h1>
    <div class="sub">August 6 baseline versus August 13 baseline</div>
    <nav class="nav"><a href="/features">Features + renders</a><a href="/pipeline">Pipeline</a>
      <a class="active" href="/comparison">Golden comparison</a>
      <a href="/playground">Playground</a></nav>
  </div>
  <div class="controls"><select id="genreFilter"><option value="">All August 13 genres</option></select>
    <input id="search" placeholder="Filter scene, genre, shape…">
    <select id="picker"></select></div>
</div></header>
<main>
  <div class="meta" id="meta"></div>
  <div class="prompt" id="prompt"></div>
  <div class="grid">
    <section class="group old"><h2>August 6 baseline <span>layoutgen_genre_images_260806</span></h2>
      <div class="pair"><div class="pane"><h3>Isometric</h3><img id="oldIso">
        <div class="model-prompt" id="oldIsoPrompt"></div></div>
      <div class="pane"><h3>Top-down</h3><img id="oldTd">
        <div class="model-prompt" id="oldTdPrompt"></div></div></div>
      <div class="config-card"><h3>August 6 prompt configuration</h3>
        <div class="config-sub">Older subgenre + playable-requirements system; it did not use Build.md shapes or presets.</div>
        <div class="feature-list" id="oldBuildSelections"></div></div></section>
    <section class="group new"><h2>August 13 baseline <span>current pipeline</span></h2>
      <div class="pair"><div class="pane"><h3>Isometric</h3><img id="newIso">
        <div class="model-prompt" id="newIsoPrompt"></div></div>
      <div class="pane"><h3>Top-down</h3><img id="newTd">
        <div class="model-prompt" id="newTdPrompt"></div></div></div>
      <div class="config-card"><h3>August 13 prompt configuration</h3>
        <div class="config-sub">Current Build.md selections, what each one controls, and whether its requirement reached the isometric prompt, top-down prompt, both, or neither.</div>
        <div class="feature-list" id="newBuildSelections"></div></div></section>
  </div>
</main>
<div class="lightbox" id="lightbox"><img></div>
"""

JS = r"""
const SCENES=__SCENES__, $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",
'"':"&quot;","'":"&#39;"}[c]));
function showPrompt(id,text,label="Exact image-model prompt"){const el=$(id);
 el.innerHTML=text?`<details><summary>${esc(label)}</summary><pre>${esc(text)}</pre></details>`:
 `<div class="missing-prompt">Exact per-image prompt was not retained in this baseline's artifacts.</div>`}
function promptTargets(text,s){const needle=String(text||"").trim().replace(/\.$/,"");
 if(!needle)return"neither image prompt";
 const iso=(s.iso_prompt||"").includes(needle),td=(s.td_prompt||"").includes(needle);
 return iso&&td?"isometric and top-down":iso?"isometric only":td?"top-down only":
  "neither image prompt"}
const picker=$("picker"),search=$("search"),genreFilter=$("genreFilter");
const genres=[...new Set(SCENES.map(s=>s.genre||"No Genre"))].sort((a,b)=>a.localeCompare(b));
genreFilter.innerHTML+=genres.map(g=>`<option value="${esc(g)}">${esc(g)}</option>`).join("");
function choices(){const q=search.value.trim().toLowerCase();
 const wanted=genreFilter.value;
 const rows=SCENES.filter(s=>(!wanted||(s.genre||"No Genre")===wanted)&&
 (!q||[s.id,s.genre,s.shape,s.preset,s.prompt,s.august_6?.genre,
 s.august_6?.variation,s.august_6?.implied].some(v=>
 String(v||"").toLowerCase().includes(q))));const cur=picker.value;
 picker.innerHTML=rows.map(s=>`<option value="${s.id}">${s.id} · ${esc(s.genre||"No Genre")} · ${esc(s.shape||"described")}</option>`).join("");
 if(rows.length){picker.value=rows.some(s=>s.id===cur)?cur:rows[0].id;render(picker.value)}}
function render(id){const s=SCENES.find(x=>x.id===id);if(!s)return;
 const old=s.august_6||{};
 $("meta").innerHTML=[["Scene",s.id],["August 6 genre",old.genre||"—"],
 ["August 13 genre",s.genre||"No Genre"]].map(([k,v])=>
 `<span class="chip"><strong>${esc(k)}:</strong> ${esc(v)}</span>`).join("");
 $("prompt").textContent=s.prompt||"";
 const oldSelections=[
  {name:"Genre",id:old.genre||"unknown",notes:old.variation||"No subgenre recorded",
    quote:old.implied?`Inferred template: ${old.implied}`:""},
  {name:"Routing",id:(old.route||[]).join(" + ")||"P0",
    notes:(old.nondefault||[]).length?`Non-default axes: ${old.nondefault.join(" · ")}`:
      "No non-default routing axes."},
  ...(old.needs||[]).map(n=>({name:"Requirement · "+n.role,id:n.primitive,notes:n.visual})),
  ...(old.fragments||[]).map(f=>({name:"Axis · "+f.axis,id:f.value,notes:f.text,quote:f.why})),
  ...(old.structural||[]).map(f=>({name:"Structural route · "+f.axis,id:f.value,
    notes:f.text,quote:f.why}))
 ];
 $("oldBuildSelections").innerHTML=oldSelections.map(x=>`<div class="feature">
  <span class="origin">${esc(x.id||"")}</span><strong>${esc(x.name)}</strong>
  <span>${esc(x.notes||"")}</span>${x.quote?`<div class="quote">${esc(x.quote)}</div>`:""}</div>`).join("");
 const shape=s.shape_selection||{}, axes=s.axes_selection||[];
 const axisSelections=axes.map(a=>{const isDefault=a.value===a.default;
  let detail=`Selected: ${a.value}${isDefault?" (default)":""}. `;
  if(isDefault)detail+="Requirement added: none; defaults do not inject text.";
  else if(a.routing_only)detail+="Routing only: changes generation strategy, not image text.";
  else if(a.clause)detail+=`Requirement added: ${a.clause} · Sent to: ${promptTargets(a.clause,s)}.`;
  else detail+="No standalone image requirement was recorded.";
  if(a.pipeline)detail+=` Pipeline: ${a.pipeline}.`;
  return{name:"Axis · "+a.label,id:a.id,
    notes:a.what||"A routing dimension used when no catalogue shape is selected.",
    quote:detail}});
 const newSelections=[
  {name:"Genre",id:s.genre||"No Genre",
    notes:"Classification used to choose the available shape, preset, and option catalogue.",
    quote:s.genre_route?`Genre-wide route: ${s.genre_route}`:
      "Requirement added: none; the genre label itself adds no geometry."},
  ...(shape.id?[{name:"Shape · "+shape.label,id:shape.id,
    notes:"Spatial requirement: "+shape.what,
    quote:`Sent to: ${promptTargets(shape.what,s)} · Pipeline: ${shape.pipeline||"P0"}`}]:
    axisSelections),
  {name:"Preset",id:s.preset||"none",notes:s.preset&&s.preset!=="none"?
    "Selection bundle only; its name is not sent to the image model. Its chosen shape and options appear separately.":
    "No preset selected; no requirement added."},
  ...(s.options_all||[]).map(o=>{const injected=o.injected_what||"";
    const target=injected?promptTargets(injected,s):"neither image prompt";
    const actual=injected?`Actual image requirement: ${injected} · Sent to: ${target}.`:
      "Requirement added to image prompts: none; this is post-segmentation only.";
    return{name:"Option · "+o.label,id:o.id,
      notes:`Agent interpretation: ${o.what||"—"}`,
      quote:`${actual} Goes to: ${o.goes||"unknown"} · Pipeline: ${o.pipeline||"P0"}${o.count>=0?` · Count: ${o.count}`:""}`}})
 ];
 $("newBuildSelections").innerHTML=newSelections.map(x=>`<div class="feature">
  <span class="origin">${esc(x.id||"")}</span><strong>${esc(x.name)}</strong>
  <span>${esc(x.notes||"")}</span>${x.quote?`<div class="quote">${esc(x.quote)}</div>`:""}</div>`).join("");
 const oldBase="/results/comparison/scene_"+s.id;
 const imgs={oldIso:oldBase+"_isometric.png",oldTd:oldBase+"_topdown.png",
 newIso:s.images?.iso||"",newTd:s.images?.td||""};
 Object.entries(imgs).forEach(([key,src])=>{const im=$(key);im.src=src;im.dataset.full=src});
 showPrompt("oldIsoPrompt",old.guided_prompt,"Archived image-model prompt");
 showPrompt("oldTdPrompt","");
 showPrompt("newIsoPrompt",s.iso_prompt);
 showPrompt("newTdPrompt",s.td_prompt)}
search.addEventListener("input",choices);genreFilter.addEventListener("change",choices);
picker.addEventListener("change",()=>render(picker.value));
const lb=$("lightbox"),li=lb.querySelector("img");document.addEventListener("click",e=>{
 if(e.target.matches(".pane img")){li.src=e.target.dataset.full;lb.classList.add("open")}
 else if(e.target===lb||e.target===li){lb.classList.remove("open");li.src=""}});choices();
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", default="agent_gateway_gpt55_golden75_260813")
    parser.add_argument("--image-arm", default="agent_gateway_gpt55_golden75_260813")
    parser.add_argument(
        "--august-6-run",
        type=pathlib.Path,
        default=RESULTS / "runs" / "needs.jsonl",
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=RESULTS / "comparison_viewer_gpt55_golden75.html",
    )
    args = parser.parse_args()
    rows = collect(
        args.run_name,
        args.image_arm,
        only_sent=True,
    )
    august_6 = {}
    for line in args.august_6_run.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record.get("status") != "ok":
            continue
        august_6[record["scene"]] = {
            key: record.get(key)
            for key in (
                "genre",
                "variation",
                "route",
                "implied",
                "needs",
                "nondefault",
                "fragments",
                "structural",
                "guided_prompt",
            )
        }
    for row in rows:
        row["august_6"] = august_6.get(row["id"], {})
        row.pop("checklist", None)
    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    page = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>Golden image comparison</title><style>{CSS}</style></head>"
        f"<body>{BODY}<script>{JS.replace('__SCENES__', data)}</script></body></html>\n"
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page, encoding="utf-8")
    print(f"wrote {args.out} ({len(rows)} scenes, {len(page)//1024} KB)")


if __name__ == "__main__":
    main()
