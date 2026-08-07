"""Side-by-side viewer: the 75 golden prompts raw, against the same prompts routed
through Build.md Part II.

Baseline  the raw prompt plus the golden set's style tail. Nothing injected.
Rules     the same wrapper with a LAYOUT FEATURES block inserted before that tail -
          one shape, plus the visible half of whatever options the router picked.

Both arms then produce a top-down. In the baseline that is always converted from the
isometric; in the rules arm a P6 or layout route generates it first instead, which is
the point of those routes rather than an accident.

Every feature carries a blinded judge's verdict per arm, from `gslg.judges.rules`, so
the page shows its own evidence instead of asking you to eyeball it.

Writes `site/rules_compare.html`, which the server serves alongside `results/`.

Usage:
    python -m gslg.viewers.compare
"""

from __future__ import annotations

import json
import pathlib
from concurrent.futures import ThreadPoolExecutor

from gslg import paths
from gslg import rules as br
from gslg.judges import rules as rsc

OUT = paths.SITE / "rules_compare.html"


def thumbs() -> int:
    """Every arm and stage at one size, including the plans.

    The judges make thumbnails only for the pairs they actually look at, so a page
    that shows a plan, or an arm a judge skipped, would otherwise have nothing to
    display. Making them all here keeps the pages buildable from images alone.
    """
    jobs = []
    for scene in sorted(p.stem for p in (paths.SCENES / "rules" / "iso").glob("*.png")):
        for arm in paths.ARMS:
            for stage in paths.STAGES:
                jobs.append((paths.scene(arm, stage, scene),
                             paths.thumb(arm, stage, scene)))
        jobs.append((paths.plan(scene), paths.thumb("rules", "plan", scene)))
    with ThreadPoolExecutor(max_workers=8) as pool:
        return sum(pool.map(lambda j: rsc.thumb(*j), jobs))


def _load() -> list[dict]:
    rows = {json.loads(x)["scene"]: json.loads(x)
            for x in (paths.RUNS / "rules.jsonl").open() if x.strip()}
    iso = {json.loads(x)["scene"]: json.loads(x)
           for x in (paths.SCORES / "rules_iso.jsonl").open() if x.strip()}
    td = {json.loads(x)["scene"]: json.loads(x)
          for x in (paths.SCORES / "rules_td.jsonl").open() if x.strip()}

    out = []
    for scene, r in sorted(rows.items()):
        g = br.GENRES.get(r["genre"])
        held = r.get("held") or []
        si, st = iso.get(scene), td.get(scene)
        feats = []
        for i, q in enumerate(rsc.requirements(r)):
            a = si["items"][i] if si and i < len(si["items"]) else None
            b = st["items"][i] if st and i < len(st["items"]) else None
            feats.append({
                "label": q["label"], "text": q["text"], "kind": q["kind"],
                "isoB": a["base"] if a else None, "isoR": a["rules"] if a else None,
                "tdB": b["base"] if b else None, "tdR": b["rules"] if b else None,
                "note": (a or b or {}).get("note", ""),
            })
        out.append({
            "scene": scene, "title": r.get("title", ""), "prompt": r["prompt"],
            "genre": r["genre"], "preset": r["preset"], "shape": r["shape"],
            "shapeLabel": r.get("shape_label", ""),
            "options": [
                {"id": o.id, "label": o.label, "goes": o.goes_to}
                for oid in r["options"] if g and (o := g.option(oid)) and o.drawn],
            "held": held, "route": r.get("route", []), "order": r["order"],
            "confidence": r.get("confidence", ""), "evidence": r.get("evidence", ""),
            "addendum": r["addendum"], "isoPrompt": r.get("iso_prompt", ""),
            "tdPrompt": r.get("td_prompt", ""), "plan": r.get("plan"),
            "features": feats,
            "isoB": si["base_met"] if si else 0, "isoR": si["rules_met"] if si else 0,
            "tdB": st["base_met"] if st else 0, "tdR": st["rules_met"] if st else 0,
            "total": si["total"] if si else len(feats),
        })
    return out


CSS = """
:root{--bg:#0d1117;--pan:#141b23;--ln:#253040;--fg:#e6edf3;--dim:#9fb0c3;
  --dim2:#6f8296;--ok:#3fb950;--acc:#58a6ff;--bad:#f85149;--warn:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:13px/1.55 ui-sans-serif,-apple-system,Segoe UI,Roboto,sans-serif}
header{padding:12px 18px;border-bottom:1px solid var(--ln);position:sticky;top:0;
  background:var(--bg);z-index:9}
header h1{margin:0;font-size:14px;display:inline}
header .sub{color:var(--dim);font-size:12px;margin-left:10px}
.wrap{display:flex;height:calc(100vh - 49px)}
.nav{width:216px;flex:0 0 216px;overflow:auto;border-right:1px solid var(--ln);
  padding:8px}
.nav .f{display:flex;gap:5px;margin-bottom:8px}
.nav select{flex:1;background:var(--pan);color:var(--fg);border:1px solid var(--ln);
  border-radius:6px;padding:4px;font-size:11px}
.nav a{display:block;padding:5px 7px;border-radius:6px;color:var(--fg);
  text-decoration:none;font-size:12px;border:1px solid transparent}
.nav a:hover{background:var(--pan)}
.nav a.on{background:var(--pan);border-color:var(--acc)}
.nav a i{display:block;color:var(--dim2);font-style:normal;font-size:10.5px}
.main{flex:1;overflow:auto;padding:16px 20px 60px}
.sect{background:var(--pan);border:1px solid var(--ln);border-radius:10px;
  padding:12px 14px;margin-bottom:14px}
h2{font-size:15px;margin:0 0 4px}
h3{font-size:12px;margin:0 0 6px;color:var(--dim);font-weight:600;
  text-transform:uppercase;letter-spacing:.05em}
h4{font-size:12px;margin:0 0 8px}
.chip{display:inline-block;border:1px solid var(--ln);border-radius:999px;
  padding:1px 8px;font-size:11px;color:var(--dim);margin-right:5px}
.chip.acc{color:var(--acc);border-color:#2f4a7a}
.chip.ok{color:var(--ok);border-color:#1f5c2b}
.chip.warn{color:var(--warn);border-color:#5c4a12}
.chip.bad{color:var(--bad);border-color:#6e2b28}
pre{white-space:pre-wrap;background:#0b0f14;border:1px solid var(--ln);
  border-radius:8px;padding:10px;margin:0;font-size:12px;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.fig h5{margin:0 0 5px;font-size:11.5px;color:var(--dim);font-weight:600}
.fig img{width:100%;border:1px solid var(--ln);border-radius:8px;cursor:zoom-in;
  display:block;background:#0b0f14}
.fig.b h5{color:var(--acc)}
.miss{height:200px;display:flex;align-items:center;justify-content:center;
  color:var(--dim2);border:1px dashed var(--ln);border-radius:8px}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{text-align:left;padding:5px 7px;border-bottom:1px solid var(--ln);
  vertical-align:top}
th{color:var(--dim);font-weight:600;font-size:11px}
td.c{text-align:center;width:52px}
.y{color:var(--ok)}.n{color:var(--bad)}
.note{color:var(--dim);font-size:11.5px;margin:3px 0 0}
.sum{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px}
.card{background:var(--pan);border:1px solid var(--ln);border-radius:10px;padding:10px}
.card b{display:block;font-size:20px;line-height:1.2}
.card span{color:var(--dim);font-size:11px}
dialog{border:none;background:transparent;max-width:96vw;max-height:96vh}
dialog::backdrop{background:rgba(0,0,0,.86)}
dialog img{max-width:94vw;max-height:94vh;border-radius:8px}
.del{font-weight:600}
.up{color:var(--ok)}.dn{color:var(--bad)}
.tabs{display:inline-flex;gap:4px;margin-left:14px;vertical-align:middle}
.tabs a{color:var(--dim);text-decoration:none;font-size:11.5px;padding:3px 9px;
  border:1px solid var(--ln);border-radius:999px}
.tabs a:hover{color:var(--fg)}
.tabs a.on{color:var(--acc);border-color:#2f4a7a;background:#101a2a}
"""

#: Where a scene's images live, as the browser addresses them. Every page builds the
#: same URLs, and they all go through here so the layout under `results/` is stated
#: once rather than spelled out inside six template literals.
URL_JS = """
const shot=(arm,stage,scene)=>`/results/scenes/${arm}/${stage}/${scene}.png`;
const thumb=(arm,stage,scene)=>`/results/thumbs/${stage}_${arm}_${scene}.jpg`;
"""

#: The card controls, shared by every page that lists scenes: styling, the block that
#: sits above the scene list, and the client that talks to the card endpoint. They
#: live here rather than in one page because the card is the same artefact whichever
#: results page you are reading when you decide you want it.
CARD_CSS = """
.cardbar{display:block;border:1px solid var(--ln);border-radius:8px;padding:7px 8px;
  margin-bottom:8px}
.cardbar button{width:100%;background:#16324f;color:#cfe6ff;border:1px solid #2f4a7a;
  border-radius:6px;padding:5px;font-size:11.5px;cursor:pointer}
.cardbar button:disabled{background:var(--pan);color:var(--dim2);
  border-color:var(--ln);cursor:default}
.cardbar a{color:var(--acc);font-size:11px;text-decoration:none}
.cardbar .note{font-size:10.5px;color:var(--dim2);margin-top:4px}
.nav .row{display:flex;align-items:flex-start;gap:6px}
.nav .row input{margin:7px 0 0;accent-color:var(--acc)}
.nav .row a{flex:1;min-width:0}
.dl{background:#16324f;color:#cfe6ff;border:1px solid #2f4a7a;border-radius:6px;
  padding:3px 10px;font-size:11.5px;cursor:pointer;margin-left:8px}
.dl:disabled{color:var(--dim2);background:var(--pan);border-color:var(--ln);
  cursor:default}
"""

CARD_BAR = """<div class="f cardbar">
      <button id="dlpick" disabled>download cards</button>
      <a href="#" id="pickall">all shown</a> &middot;
      <a href="#" id="picknone">none</a>
      <div class="note" id="picknote">tick scenes to take their cards as a zip</div>
    </div>"""

#: Expects the page to define `shown()`, returning the scenes the filters allow, and
#: `list()`, redrawing the scene list.
CARD_JS = """
// A card is one sheet holding a scene's prompt, the same prompt run three ways, and
// the checklist all three were judged against - this page's own content in a single
// file that can be dropped into a deck. The playground process serves these pages
// too, so an ordinary same-origin request reaches the endpoint that draws them.
function download(name,as){
  const a=document.createElement("a");
  a.href="/out/"+name; a.download=as;
  document.body.appendChild(a); a.click(); a.remove();
}
async function card(body,as,btn,note){
  btn.disabled=true; note.textContent=" building\\u2026";
  const r=await (await fetch("/api/card",{method:"POST",
    headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})).json();
  if(r.error){ note.textContent=" "+r.error; btn.disabled=false; return; }
  const t=setInterval(async()=>{
    const c=await (await fetch("/api/card?id="+r.card)).json();
    if(c.status==="running"){ note.textContent=" "+c.step; return; }
    clearInterval(t); btn.disabled=false;
    if(c.status==="done"){ download(c.file,as); note.textContent=` saved ${as}`; }
    else note.textContent=" "+(c.error||"failed");
  },1200);
}
const picked=new Set();
const pickBox=scene=>`<input type="checkbox" data-s="${scene}" ${
  picked.has(scene)?"checked":""}>`;
function bindPicks(){
  document.querySelectorAll(".nav input[data-s]").forEach(c=>c.onchange=()=>{
    c.checked?picked.add(c.dataset.s):picked.delete(c.dataset.s); updatePick(); });
  updatePick();
}
function updatePick(){
  $("dlpick").disabled=!picked.size;
  $("dlpick").textContent=picked.size>1?`download ${picked.size} cards as a zip`
    :picked.size?"download 1 card":"download cards";
}
$("pickall").onclick=e=>{ e.preventDefault();
  shown().forEach(x=>picked.add(x.s.scene)); list(); };
$("picknone").onclick=e=>{ e.preventDefault(); picked.clear(); list(); };
$("dlpick").onclick=()=>card({scenes:[...picked].sort()},
  picked.size>1?"cards.zip":`card_${[...picked][0]}.png`,
  $("dlpick"),$("picknote"));
"""

#: Every page in this set, so each one can link to the others. The playground is a
#: live server on another port rather than a file here, so it is linked by port and
#: resolved against whatever host the viewer is being read from.
PAGES = [
    ("index.html", "Start"),
    ("three_way.html", "Three arms"),
    ("rules_compare.html", "Rules vs baseline"),
    ("roadmap.html", "Injection roadmap"),
    ("requirements.html", "Requirements used"),
    ("rules_viewer/index.html", "Genre menu"),
]
#: The playground is served by the same process as these pages, at this path. It used
#: to run on its own port, which meant every page had to rewrite the host to link to
#: it; same origin means an ordinary relative link works.
PLAYGROUND_PATH = "/playground"


def nav(active: str) -> str:
    tabs = "".join(
        f'<a class="{"on" if href == active else ""}" href="{href}">{label}</a>'
        for href, label in PAGES)
    tabs += (f'<a href="{PLAYGROUND_PATH}" title="generate from any prompt">'
             f'Playground</a>')
    return f'<span class="tabs">{tabs}</span>'


def build() -> pathlib.Path:
    thumbs()
    scenes = _load()

    tot = sum(s["total"] for s in scenes)
    ib = sum(s["isoB"] for s in scenes)
    ir = sum(s["isoR"] for s in scenes)
    tb = sum(s["tdB"] for s in scenes)
    tr = sum(s["tdR"] for s in scenes)
    genres = sorted({s["genre"] for s in scenes})

    head = f"""<div class="sum">
  <div class="card"><b>{100*ib/tot:.0f}% &rarr; <span class="up">{100*ir/tot:.0f}%</span></b>
    <span>isometric &mdash; features visible, baseline to rules</span></div>
  <div class="card"><b>{100*tb/tot:.0f}% &rarr; <span class="up">{100*tr/tot:.0f}%</span></b>
    <span>top-down &mdash; same measure on stage B</span></div>
  <div class="card"><b>{tot}</b><span>feature checks across {len(scenes)} scenes,
    judged blind, per arm</span></div>
  <div class="card"><b>{sum(1 for s in scenes if s['preset']!='none')}/{len(scenes)}</b>
    <span>landed on a preset; the rest were built option by option</span></div>
</div>"""

    html = f"""<!doctype html><meta charset="utf-8">
<title>Build.md rules vs baseline &mdash; 75 golden prompts</title>
<style>{CSS}{CARD_CSS}</style>
<header><h1>Build.md Part II vs the raw prompt</h1>{nav("rules_compare.html")}
  <span class="sub">75 golden prompts &middot; identical wrapper, identical style tail
    &middot; the only difference is the injected LAYOUT FEATURES block</span></header>
<div class="wrap">
  <div class="nav">
    <div class="f">
      <select id="fg"><option value="">all genres</option>
        {"".join(f'<option>{g}</option>' for g in genres)}</select>
      <select id="fo"><option value="">any order</option><option>std</option>
        <option>p6</option><option>layout</option></select>
    </div>
    {CARD_BAR}
    <div id="list"></div>
  </div>
  <div class="main" id="main"></div>
</div>
<dialog id="zoom"><img id="zimg"></dialog>
<script>
const S={json.dumps(scenes)};
const HEAD={json.dumps(head)};
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>(
  {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]));
const $=id=>document.getElementById(id);
let cur=0;

function mark(v){{ return v===null?'<span style="color:#6f8296">&ndash;</span>'
  :v?'<span class="y">&#10003;</span>':'<span class="n">&#10007;</span>'; }}

function fig(label,src,full,cls){{
  return `<div class="fig ${{cls||""}}"><h5>${{esc(label)}}</h5>`+
    (src?`<img src="${{src}}" data-full="${{full}}">`:`<div class="miss">not generated</div>`)+
    `</div>`;
}}

function render(i){{
  cur=i; const s=S[i];
  const dIso=s.isoR-s.isoB, dTd=s.tdR-s.tdB;
  const stageB = s.order==="std"
    ? "converted from each arm's own isometric &mdash; same Stage B prompt on both sides"
    : "the rules arm generated this first and built its isometric from it; the baseline still converted its own";
  $("main").innerHTML = HEAD + `
  <div class="sect">
    <h2>${{esc(s.scene)}} &mdash; ${{esc(s.genre)}}
      ${{s.preset!=="none"?`<span class="chip acc">${{esc(s.preset)}}</span>`
        :`<span class="chip">no preset fitted</span>`}}
      <button class="dl" id="dlone">download this card</button>
      <span class="note" id="dlnote"></span></h2>
    <p class="note">${{esc(s.prompt)}}</p>
  </div>

  <div class="sect">
    <h3>How it routed</h3>
    <div>
      <span class="chip">shape: ${{esc(s.shapeLabel||s.shape)}}</span>
      ${{s.options.map(o=>`<span class="chip">${{esc(o.label)}}</span>`).join("")}}
      ${{s.route.map(r=>`<span class="chip warn">${{esc(r)}}</span>`).join("")}}
      <span class="chip ${{s.order==="std"?"":"acc"}}">${{
        s.order==="std"?"isometric first":s.order==="p6"?"plan first":"authored layout first"}}</span>
      <span class="chip ${{s.confidence==="low"?"bad":s.confidence==="high"?"ok":""}}">${{
        esc(s.confidence)}} confidence</span>
    </div>
    <p class="note">${{esc(s.evidence)}}</p>
    ${{s.held.length?`<p class="note" style="color:var(--warn)">held back, never drawn:
      ${{s.held.map(esc).join(", ")}}</p>`:""}}
  </div>

  <div class="sect">
    <h3>What was injected</h3>
    <pre>${{esc(s.addendum)||"<em>nothing</em>"}}</pre>
  </div>

  <div class="sect">
    <h3>Stage A &mdash; isometric
      <span class="del ${{dIso>0?"up":dIso<0?"dn":""}}">${{s.isoB}} &rarr; ${{s.isoR}}
      of ${{s.total}}</span></h3>
    <div class="pair">
      ${{fig("Baseline \\u2014 raw prompt",thumb("raw","iso",s.scene),
             shot("raw","iso",s.scene))}}
      ${{fig("Rules \\u2014 + layout features",thumb("rules","iso",s.scene),
             shot("rules","iso",s.scene),"b")}}
    </div>
  </div>

  <div class="sect">
    <h3>Stage B &mdash; top-down
      <span class="del ${{dTd>0?"up":dTd<0?"dn":""}}">${{s.tdB}} &rarr; ${{s.tdR}}
      of ${{s.total}}</span></h3>
    <p class="note" style="margin-bottom:8px">${{stageB}}</p>
    <div class="pair">
      ${{fig("Baseline top-down",thumb("raw","td",s.scene),
             shot("raw","td",s.scene))}}
      ${{fig("Rules top-down",thumb("rules","td",s.scene),
             shot("rules","td",s.scene),"b")}}
    </div>
    ${{s.plan?`<div style="margin-top:12px;max-width:50%">${{
      fig("Authored layout \\u2014 carved before any image was generated",
          thumb("rules","plan",s.scene),
          "/results/scenes/rules/plan/"+s.scene+".png")}}</div>`:""}}
  </div>

  <div class="sect">
    <h3>Feature audit &mdash; judged blind, each arm marked independently</h3>
    <table>
      <tr><th>Feature</th><th class="c">iso base</th><th class="c">iso rules</th>
        <th class="c">td base</th><th class="c">td rules</th></tr>
      ${{s.features.map(f=>`<tr>
        <td><b>${{esc(f.label)}}</b>
          <span class="chip">${{esc(f.kind)}}</span>
          <div class="note">${{esc(f.text)}}</div>
          ${{f.note?`<div class="note" style="color:var(--dim2)">${{esc(f.note)}}</div>`:""}}</td>
        <td class="c">${{mark(f.isoB)}}</td><td class="c">${{mark(f.isoR)}}</td>
        <td class="c">${{mark(f.tdB)}}</td><td class="c">${{mark(f.tdR)}}</td>
      </tr>`).join("")}}
    </table>
  </div>

  <div class="sect">
    <h3>Prompts actually sent</h3>
    <h4>Stage A</h4><pre>${{esc(s.isoPrompt)}}</pre>
    <h4 style="margin-top:10px">Stage B</h4><pre>${{esc(s.tdPrompt)}}</pre>
  </div>`;

  document.querySelectorAll(".fig img").forEach(el=>el.onclick=()=>{{
    $("zimg").src=el.dataset.full; $("zoom").showModal(); }});
  document.querySelectorAll(".nav a[data-i]").forEach(a=>
    a.classList.toggle("on", +a.dataset.i===i));
  $("dlone").onclick=()=>card({{scenes:[s.scene]}},`card_${{s.scene}}.png`,
    $("dlone"),$("dlnote"));
  $("main").scrollTop=0;
}}

function shown(){{
  const fg=$("fg").value, fo=$("fo").value;
  return S.map((s,i)=>({{s,i}}))
    .filter(({{s}})=>(!fg||s.genre===fg)&&(!fo||s.order===fo));
}}
function list(){{
  $("list").innerHTML=shown().map(({{s,i}})=>{{
      const d=s.isoR-s.isoB;
      return `<div class="row">${{pickBox(s.scene)}}
        <a href="#" data-i="${{i}}"><b>${{esc(s.scene)}}</b>
        <span class="del ${{d>0?"up":d<0?"dn":""}}">${{d>0?"+":""}}${{d}}</span>
        <i>${{esc(s.genre)}} &middot; ${{esc(s.preset==="none"?"no preset":s.preset)}}</i>
        </a></div>`;
    }}).join("");
  document.querySelectorAll(".nav a[data-i]").forEach(a=>a.onclick=e=>{{
    e.preventDefault(); render(+a.dataset.i); }});
  bindPicks();
}}
{URL_JS}
{CARD_JS}
$("fg").onchange=list; $("fo").onchange=list;
$("zoom").onclick=()=>$("zoom").close();
document.onkeydown=e=>{{
  if(e.key==="ArrowDown"&&cur<S.length-1) render(cur+1);
  if(e.key==="ArrowUp"&&cur>0) render(cur-1);
}};
list(); render(0);
</script>"""

    OUT.write_text(html, encoding="utf-8")
    return OUT


if __name__ == "__main__":
    p = build()
    print(f"wrote {p}  ({p.stat().st_size//1024} KB)")
