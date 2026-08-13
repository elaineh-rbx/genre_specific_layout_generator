"""Build a page showing what each end-to-end scene did at every stage.

`tools/run_e2e_pipeline.py` keeps all six intermediates per scene precisely so a bad
render can be traced to the stage that lost it, and reading them means opening six
fields of a JSON file per scene. This lays them out in the order they happened, with
the images the chain ended at, so the question "where did this go wrong" is answered
by scrolling rather than by grepping.

Usage:
    python tools/build_e2e_viewer.py          # writes results/e2e_viewer.html
    python tools/build_e2e_viewer.py --out foo.html
"""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen.paths import EVAL, RESULTS, ROUTING, SCENES
from layoutgen.pipeline.prompts import decompose

E2E = ROUTING / "e2e"
IMAGES = SCENES / "e2e"


def checklist(scene: str) -> dict:
    """The eval checklist, which this arm did not write.

    Shown last because it is the only section on the page that is not this chain's own
    account of itself: everything above is what the pipeline decided, and this is the
    list the render will be marked against. It is keyed by scene rather than by arm, so
    on most of these it was extracted from a different arm's prompt - `addendum_from`
    says which, and it is worth reading before treating a mismatch as a failure.
    """
    p = EVAL / f"{scene}.json"
    if not p.is_file():
        return {"features": [], "excluded": [], "from": ""}
    d = json.loads(p.read_text(encoding="utf-8"))
    return {"features": d.get("features") or [], "excluded": d.get("excluded") or [],
            "from": d.get("addendum_from") or ""}


def segments(text: str, body: str, addendum: str) -> list[dict]:
    """The composed prompt as spans, ready to colour.

    A sent prompt is several times the length of the message that started it, and the
    obvious reading - that the pipeline embroidered the author's words - is wrong. Most
    of it is a feature list generated from the spec, wrapped in camera and style wording
    byte-identical on every scene. Showing which span is which answers that at a glance,
    and it is also how a body that never reached the prompt at all becomes visible
    rather than merely short.
    """
    return [{"kind": k, "text": t} for k, t in decompose(text, addendum, body)]


def collect() -> list[dict]:
    rows = []
    for p in sorted(E2E.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        scene = d["scene"]
        spec = d.get("spec") or {}
        images = {k: f"/results/scenes/e2e/{k}/{scene}.png"
                  for k in ("td", "iso", "plan")
                  if (IMAGES / k / f"{scene}.png").is_file()}
        rows.append({
            "id": scene,
            "source": d.get("source", ""),
            "theme": d.get("theme", ""),
            "scale": d.get("scale") or {},
            "questions": d.get("questions") or [],
            "answers": d.get("answers") or [],
            "scene_prompt": d.get("scene_prompt", ""),
            "blob": d.get("blob", ""),
            "spec": spec,
            "genre": spec.get("genre", ""),
            "shape": spec.get("shape") or "",
            "preset": spec.get("preset") or "none",
            "route": spec.get("route") or [],
            "order": d.get("order", ""),
            "addendum": d.get("addendum", ""),
            "iso_prompt": d.get("iso_prompt", ""),
            "td_prompt": d.get("td_prompt", ""),
            "iso_parts": segments(d.get("iso_prompt", ""),
                                  d.get("scene_prompt", ""), d.get("addendum", "")),
            "td_parts": segments(d.get("td_prompt", ""),
                                 d.get("scene_prompt", ""), d.get("addendum", "")),
            "status": d.get("status", ""),
            "stage": d.get("stage", ""),
            "error": d.get("error", ""),
            "seconds": d.get("seconds", 0),
            "images": images,
            "placements": spec.get("layout_placement") or [],
            "checklist": checklist(scene),
        })
    return rows


CSS = """
:root{--bg:#0f1220;--panel:#171b2e;--panel-2:#1e2340;--line:#2b3153;--text:#e7e9f3;
  --muted:#9aa0c0;--accent:#6c8cff;--green:#35c88b;--orange:#f2a54c;--pink:#f78166}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(1200px 700px at 20% -10%,#1a1f38 0%,var(--bg) 60%);
  color:var(--text);font:13px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header{padding:16px 24px 12px;border-bottom:1px solid var(--line)}
header h1{margin:0 0 3px;font-size:18px}
header p{margin:0;color:var(--muted);font-size:12.5px;max-width:1000px}
.wrap{display:flex;align-items:flex-start}
.side{width:290px;flex:0 0 290px;padding:16px;border-right:1px solid var(--line);
  position:sticky;top:0;max-height:100vh;overflow:auto}
.side h4{margin:0 0 8px;font-size:11px;letter-spacing:.7px;text-transform:uppercase;color:var(--muted)}
.pick{padding:8px 10px;border-radius:8px;border:1px solid var(--line);background:var(--panel);
  margin-bottom:6px;cursor:pointer}
.pick:hover{border-color:var(--accent)}
.pick.on{border-color:var(--accent);background:var(--panel-2)}
.pick .id{font-weight:700}
.pick .sub{color:var(--muted);font-size:11.5px;margin-top:2px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
main{flex:1;padding:18px 24px 60px;min-width:0}
.stage{margin-bottom:16px;border:1px solid var(--line);border-radius:11px;background:var(--panel);overflow:hidden}
.stage>h3{margin:0;padding:9px 13px;font-size:11.5px;letter-spacing:.8px;text-transform:uppercase;
  color:var(--muted);background:var(--panel-2);border-bottom:1px solid var(--line);
  display:flex;justify-content:space-between;align-items:center}
.stage>h3 b{color:var(--accent);letter-spacing:0;text-transform:none;font-size:12px}
.body{padding:12px 14px}
pre{margin:0;white-space:pre-wrap;word-break:break-word;font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
  color:#cfd4ee;max-height:340px;overflow:auto}
.qa{margin:0 0 10px;padding-left:12px;border-left:2px solid var(--line)}
.qa:last-child{margin-bottom:0}
.qa .q{color:var(--text)}
.qa .f{color:var(--pink);font-size:11px;text-transform:uppercase;letter-spacing:.5px}
.qa .a{color:var(--green);margin-top:3px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font-size:11.5px;padding:3px 9px;border-radius:7px;background:var(--panel-2);
  color:var(--muted);border:1px solid var(--line)}
.chip b{color:var(--text);font-weight:600}
.shots{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
.shot figure{margin:0}
.shot img{width:100%;border-radius:9px;border:1px solid var(--line);display:block;background:#0b0d18}
.shot figcaption{color:var(--muted);font-size:11.5px;margin-top:5px;text-align:center}
.first{color:var(--green);font-weight:600}
.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:1100px){.two{grid-template-columns:1fr}}
details summary{cursor:pointer;color:var(--muted);font-size:12px;outline:none}
details[open] summary{margin-bottom:8px}
.miss{color:var(--orange)}
.seg-frame{color:#767c9d}
.seg-body{color:#8ff0c2;background:rgba(53,200,139,.09)}
.seg-addendum{color:#b9c6ff;background:rgba(108,140,255,.11)}
.key{display:flex;flex-wrap:wrap;gap:14px;margin-bottom:10px;font-size:11.5px;color:var(--muted)}
.key span b{font-weight:600}
.key i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px;
  vertical-align:baseline}

/* Lifted from the pipeline viewer so a checklist reads the same on both pages: the
   two are looked at side by side, and a second styling of the same object is a second
   thing to learn. */
.lane{border:1px solid var(--line);border-radius:10px;padding:8px 11px;margin:0;background:var(--panel-2)}
.lane.lay{border-color:var(--green)}
.lane h5{margin:0 0 5px;font-size:11px;letter-spacing:.3px;color:var(--green)}
.lane ul{margin:0;padding-left:16px}
.lane li{font-size:11.5px;line-height:1.5;color:var(--text)}
.lane li i{font-style:normal;color:var(--muted)}
.lane .none{color:var(--muted);font-size:11.5px;font-style:italic}
.checklist{margin:0;padding:0;list-style:none}
.checklist li{padding:7px 0;border-top:1px dashed var(--line);display:grid;
  grid-template-columns:auto 1fr;gap:8px;align-items:baseline}
.checklist li:first-child{border-top:none;padding-top:0}
.checklist .tick{display:inline-block;width:14px;height:14px;border-radius:4px;
  border:1.5px solid var(--muted);flex:0 0 14px;position:relative;top:2px}
.checklist .tick.p{border-color:var(--accent)}
.checklist .tick.a{border-color:var(--green)}
.checklist .name{font-size:12px;font-weight:600;color:var(--text)}
.checklist .origin{font-size:9.5px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--muted);margin-left:6px;padding:1px 6px;border-radius:4px;
  border:1px solid var(--line);background:var(--panel-2);vertical-align:middle}
.checklist .origin.p{color:var(--accent);border-color:rgba(108,140,255,.4)}
.checklist .origin.a{color:var(--green);border-color:rgba(53,200,139,.4)}
.checklist .notes{font-size:11px;color:var(--muted);margin-top:2px;line-height:1.4}
.checklist .quote{font-size:11px;color:var(--muted);margin-top:2px;line-height:1.4;
  font-style:italic;padding-left:8px;border-left:2px solid var(--line)}
.excluded{margin:0;padding:0;list-style:none;font-size:11px;color:var(--muted)}
.excluded li{padding:3px 0;border-top:1px dotted var(--line)}
.excluded li:first-child{border-top:none;padding-top:0}
.excluded .name{color:#8791a8;text-decoration:line-through;text-decoration-color:rgba(135,145,168,.4)}
.excluded .why{margin-left:6px;font-size:10.5px;color:#6f7690;font-style:italic}
"""

JS = """
const R = DATA;
let cur = R[0] && R[0].id;
const esc = s => (s==null?'':String(s)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

function chips(pairs){
  return '<div class="chips">' + pairs.filter(p=>p[1]!=='' && p[1]!=null)
    .map(p=>`<span class="chip">${esc(p[0])} <b>${esc(p[1])}</b></span>`).join('') + '</div>';
}
const LABEL = {body:'the scene prompt, written from the author\\'s message',
               addendum:'feature list generated from the spec',
               frame:'camera and style wording, the same on every scene'};
const TINT = {body:'rgba(53,200,139,.5)', addendum:'rgba(108,140,255,.55)',
              frame:'#767c9d'};

function painted(parts){
  return parts.map(p=>`<span class="seg-${p.kind}">${esc(p.text)}</span>`).join('');
}
// The point of the breakdown is the proportion, so the key carries the counts rather
// than making the reader estimate them from the colouring.
function key(parts, total){
  const by = {};
  parts.forEach(p => by[p.kind] = (by[p.kind]||0) + p.text.length);
  return '<div class="key">' + ['body','addendum','frame'].filter(k=>by[k]).map(k=>
    `<span><i style="background:${TINT[k]}"></i><b>${by[k]}</b> chars —
     ${LABEL[k]} (${Math.round(100*by[k]/total)}%)</span>`).join('') + '</div>';
}
// The pipeline viewer's markup as well as its styling, for the same reason.
function checklistHtml(cl){
  const feats = (cl && cl.features) || [], excl = (cl && cl.excluded) || [];
  if (!feats.length) return '<span class="miss">no checklist for this scene \\u2014 run '
    + '<code>tools/extract_checklist.py --arm e2e</code></span>';
  const rows = feats.map(f => {
    const oc = f.origin === 'prompt' ? 'p' : 'a';
    return `<li><span class="tick ${oc}"></span><div>
        <span class="name">${esc(f.name)}</span>
        <span class="origin ${oc}">${esc(f.origin||'?')}</span>
        ${f.notes ? `<div class="notes">${esc(f.notes)}</div>` : ''}
        ${f.quote ? `<div class="quote">${esc(f.quote)}</div>` : ''}
      </div></li>`;
  }).join('');
  const ex = excl.length
    ? excl.map(x=>`<li><span class="name">${esc(x.name)}</span>
        <span class="why">${esc(x.why||'')}</span></li>`).join('')
    : '<li style="font-style:italic">nothing excluded</li>';
  return `<ul class="checklist">${rows}</ul>
    <details style="margin-top:10px"><summary>non-visual asks excluded \\u2014 ${excl.length}</summary>
      <ul class="excluded">${ex}</ul></details>`;
}
function placements(ps){
  if(!ps || !ps.length) return `<div class="lane lay"><h5>layout_placement</h5>
    <div class="none">nothing to place after segmentation</div></div>`;
  return `<div class="lane lay"><h5>layout_placement \\u2014 never drawn, sited after
    segmentation</h5><ul>` + ps.map(p=>
    `<li><b>${esc(p.id)}</b>${p.count>0?` \\u00d7${p.count}`:''}
       <i>\\u2014 ${esc(p.where || 'no siting rule given')}</i></li>`).join('')
    + '</ul></div>';
}
function stage(n, title, note, inner){
  return `<section class="stage"><h3><span>${n}. ${title}</span>${note?`<b>${esc(note)}</b>`:''}</h3>
          <div class="body">${inner}</div></section>`;
}
function render(){
  const r = R.find(x=>x.id===cur); if(!r) return;
  document.querySelectorAll('.pick').forEach(e=>e.classList.toggle('on', e.dataset.id===cur));

  const qa = r.questions.length
    ? r.questions.map((q,i)=>`<div class="qa"><div class="f">${esc(q.field)}</div>
        <div class="q">${esc(q.ask)}</div>
        <div class="a">${esc((r.answers[i]||{}).answer || '(unanswered)')}</div></div>`).join('')
    : '<span class="miss">no questions — the intake judged the prompt complete</span>';

  // Which view came first is the whole meaning of the pair: the other is derived
  // from it, so showing them unlabelled invites reading the wrong one as
  // authoritative. On a layout scene neither was first - the carved plan was.
  const first = {std:'iso', p6:'td', layout:'plan'}[r.order];
  const label = {iso:'isometric', td:'top-down', plan:'authored plan'};
  const mark = k => k !== first ? ''
    : k === 'plan' ? ' <span class="first">— carved first, both views follow it</span>'
                   : ' <span class="first">— drawn first</span>';
  const shots = ['plan','td','iso'].filter(k=>r.images[k]).map(k=>
    `<div class="shot"><figure><a href="${r.images[k]}" target="_blank">
       <img src="${r.images[k]}" loading="lazy"></a>
       <figcaption>${label[k]}${mark(k)}</figcaption>
     </figure></div>`).join('');

  document.getElementById('out').innerHTML =
    stage(1,'The author\\'s message','the only input', `<pre>${esc(r.source)}</pre>`)
  + stage(2,'Intake — questions asked back', `${r.questions.length} asked`,
      chips([['theme', r.theme||'—'],['scale', (r.scale.band||'—') + (r.scale.assumed?' (assumed)':'')]])
      + '<div style="margin-top:10px">' + qa + '</div>')
  + stage(3,'Uprez — the scene prompt','space only, English',
      `<pre>${esc(r.scene_prompt)}</pre>`)
  + stage(4,'Blob — the reasoning','prose, IDs inline',
      `<details open><summary>word blob</summary><pre>${esc(r.blob)}</pre></details>`)
  + stage(5,'Decouple — the structured spec', `${r.genre} / ${r.shape||'no shape'}`,
      chips([['genre',r.genre],['shape',r.shape||'—'],['preset',r.preset],
             ['route',(r.route||[]).join(', ')||'P0'],['order',r.order]])
      + '<div style="margin-top:10px">' + placements(r.placements) + '</div>'
      + `<details style="margin-top:10px"><summary>full spec JSON</summary>
         <pre>${esc(JSON.stringify(r.spec,null,2))}</pre></details>`)
  + stage(6,'Compose — what was sent to the image model', `${r.order}-first`,
      key(r.iso_parts, r.iso_prompt.length)
      + `<div class="two">
        <details open><summary>isometric prompt — ${r.iso_prompt.length} chars</summary>
          <pre>${painted(r.iso_parts)}</pre></details>
        <details open><summary>top-down prompt — ${r.td_prompt.length} chars</summary>
          <pre>${painted(r.td_parts)}</pre></details>
       </div>`)
  + stage(7,'The images', `${Object.keys(r.images).length} rendered`,
      shots ? `<div class="shots">${shots}</div>`
            : '<span class="miss">nothing rendered for this scene</span>')
  + stage(8,'Eval checklist — what the render is marked against',
      `${(r.checklist.features||[]).length} features`
      + (r.checklist.from && r.checklist.from !== 'e2e'
         ? ` · read from the ${r.checklist.from} arm's prompt` : ''),
      checklistHtml(r.checklist));
  if (location.hash.slice(1) !== r.id) location.hash = r.id;
}
document.getElementById('list').innerHTML = R.map(r=>
  `<div class="pick" data-id="${r.id}">
     <div class="id">${r.id} <span style="color:var(--muted);font-weight:400">· ${esc(r.genre||r.status)}</span></div>
     <div class="sub">${esc(r.source.slice(0,70))}</div></div>`).join('');
document.getElementById('list').addEventListener('click', e=>{
  const p = e.target.closest('.pick'); if(!p) return; cur = p.dataset.id; render();
});
// The picker writes the hash, so the back button and a pasted #P0520 both have to
// come back through here or they change the address bar and nothing else.
addEventListener('hashchange', ()=>{
  const id = location.hash.slice(1);
  if (id && id !== cur && R.some(r=>r.id===id)) { cur = id; render(); }
});
if (location.hash && R.some(r=>r.id===location.hash.slice(1))) cur = location.hash.slice(1);
render();
"""


def build(rows: list[dict]) -> str:
    n_q = sum(len(r["questions"]) for r in rows)
    ok = sum(r["status"] == "ok" for r in rows)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>End-to-end from the raw prompt</title>
<style>{CSS}</style></head><body>
<header>
  <h1>End to end, from the raw prompt only</h1>
  <p>{len(rows)} scenes, {ok} complete. Nothing here was imported: the intake questions
  were generated from the author's message, answered, and carried through uprez, blob and
  decouple into the spec the images were composed from. {n_q} questions asked
  ({n_q / max(len(rows), 1):.1f} per scene). Every stage is shown in the order it ran,
  and last the eval checklist \u2014 the one section this chain did not write, which is
  what the render will be marked against.</p>
</header>
<div class="wrap">
  <aside class="side"><h4>{len(rows)} scenes</h4><div id="list"></div></aside>
  <main id="out"></main>
</div>
<script>const DATA = {json.dumps(rows, ensure_ascii=False)};</script>
<script>{JS}</script>
</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path, default=RESULTS / "e2e_viewer.html")
    args = ap.parse_args()
    rows = collect()
    if not rows:
        print(f"no records under {E2E} - run tools/run_e2e_pipeline.py first")
        return
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build(rows), encoding="utf-8")
    shots = sum(len(r["images"]) for r in rows)
    print(f"{len(rows)} scenes, {shots} images -> {args.out}")
    print("serve with scripts/serve.sh restart, then open /e2e")


if __name__ == "__main__":
    main()
