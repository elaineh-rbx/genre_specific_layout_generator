"""The pieces every built page uses: one stylesheet, one set of URL rules, one nav.

These were spread across whichever page happened to need them first, which meant six
copies of the dark theme drifting apart and two different opinions about where a
scene's image lives. A page here should be about what it shows, not about how the site
looks or where the files are.

The card controls are here for the same reason: a card is the same artefact whichever
results page you are reading when you decide you want one.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from layoutgen import arms as A
from layoutgen import paths


def thumbs() -> int:
    """Every arm and stage at one size, including the plans.

    A judge only makes thumbnails for the sets it actually looks at, so a page showing
    a plan, or an arm no comparison happens to include, would otherwise have nothing
    to display. Making them all here keeps the pages buildable from images alone.
    """
    from layoutgen.evaluate.score import thumb

    jobs = []
    for scene in sorted(p.stem for p in (paths.SCENES / "rules" / "iso").glob("*.png")):
        for arm in A.ARMS:
            for stage in paths.STAGES:
                jobs.append((paths.scene(arm, stage, scene),
                             paths.thumb(arm, stage, scene)))
            # Only the arms that route a scene layout-first have one of these, and
            # they disagree about which scenes those are, so every arm is asked.
            jobs.append((paths.plan(scene, arm), paths.thumb(arm, "plan", scene)))
    with ThreadPoolExecutor(max_workers=8) as pool:
        return sum(pool.map(lambda j: thumb(*j), jobs))


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
.nav .row a{flex:1;min-width:0}
/* One per prompt, and quiet until the row is under the pointer: the list is read far
   more often than a card is taken, so the button should not compete with the scene. */
.nav .row .cardbtn{flex:0 0 auto;margin-top:4px;background:transparent;
  color:var(--dim2);border:1px solid var(--ln);border-radius:5px;padding:2px 6px;
  font-size:10px;cursor:pointer;opacity:0;transition:opacity .12s}
.nav .row:hover .cardbtn,.nav .row .cardbtn:focus{opacity:1}
.nav .row .cardbtn:hover{color:#cfe6ff;background:#16324f;border-color:#2f4a7a}
.nav .row .cardbtn:disabled{opacity:1;color:var(--dim2);background:var(--pan);
  cursor:default}
.dl{background:#16324f;color:#cfe6ff;border:1px solid #2f4a7a;border-radius:6px;
  padding:3px 10px;font-size:11.5px;cursor:pointer;margin-left:8px}
.dl:disabled{color:var(--dim2);background:var(--pan);border-color:var(--ln);
  cursor:default}
"""

CARD_BAR = """<div class="f cardbar">
      <button id="dlall">download every scene shown</button>
      <div class="note" id="cardnote">or take one from the card button on a
        prompt</div>
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
// Taking a card is nearly always about the one prompt being read, so the button that
// does it sits on the prompt. Progress goes to the bar rather than into the button's
// own label, which would resize the row it lives in while the sheet is drawn.
const cardBtn=scene=>`<button class="cardbtn" data-s="${scene}"`+
  ` title="download this scene's card">card</button>`;
function bindCards(){
  document.querySelectorAll(".nav button[data-s]").forEach(b=>b.onclick=e=>{
    e.preventDefault(); e.stopPropagation();
    const s=b.dataset.s;
    card({scenes:[s]},`card_${s}.png`,b,$("cardnote"));
  });
}
$("dlall").onclick=()=>{
  const scenes=shown().map(x=>x.s.scene);
  if(!scenes.length) return;
  card({scenes},scenes.length>1?"cards.zip":`card_${scenes[0]}.png`,
    $("dlall"),$("cardnote"));
};
"""

#: Every page in this set, so each one can link to the others. The comparison pages
#: are listed from the registry rather than written out, so a new comparison appears
#: in the nav of every page without anyone editing this list.
PAGES = ([("index.html", "Start")]
         + [(c.page, c.title.split(" vs ")[0] if len(c.arms) < 3
             else f"{len(c.arms)} arms") for c in A.COMPARISONS.values()]
         + [("roadmap.html", "Injection roadmap"),
            ("requirements.html", "Requirements used"),
            ("rules_viewer/index.html", "Genre menu")])

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
