"""Build a page pairing every sent prompt with the images it produced.

The other viewers answer "how was this scene decided": they walk the stages, and the
prompt is one panel among seven. This one answers the question you ask when scanning a
few hundred renders - what exactly did we send, and what came back - by putting the two
side by side and nothing else between them.

Every arm is in the one page, since the interesting comparison is usually across arms
on the same scene. The prompt is coloured by where each span came from, using the same
`prompts.decompose` the pipeline's own composer is defined next to.

Usage:
    python tools/build_prompt_gallery.py            # every arm that has runs
    python tools/build_prompt_gallery.py --arms e2e,answered
    python tools/build_prompt_gallery.py --out foo.html
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen.paths import RESULTS, RUNS, SCENES
from layoutgen.pipeline.prompts import decompose

#: Arm order in the picker: the two built from a real front half first, then the
#: smaller comparison arms. An arm with no run file is skipped rather than shown empty.
ARMS = ["e2e", "answered", "skill", "rules", "needs"]

#: What each arm is, in the few words the picker has room for.
ABOUT = {
    "e2e": "questions generated and answered by the agent, from the raw message alone",
    "answered": "the 614 upstream scenes, config chosen by the router from the Q&A",
    "skill": "an agent following the layout skill chose the config",
    "rules": "the router chose the config from Build.md Part II",
    "needs": "the unguided baseline, prompt sent as written",
}


def parts(text: str, addendum: str, body: str = "") -> list[dict]:
    return [{"k": k, "t": t} for k, t in decompose(text, addendum, body)]


def bodies(arm: str) -> dict[str, str]:
    """The scene prompt per scene, for arms whose body is not the author's message.

    The blob-descended arms send an uprezzed rewrite rather than the message, and it is
    not on the run row. Locating it exactly beats inferring it, which is all
    `decompose` can do without it.
    """
    out: dict[str, str] = {}
    d = RESULTS / "routing" / arm
    if not d.is_dir():
        return out
    for p in d.glob("*.json"):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if sp := (rec.get("scene_prompt") or "").strip():
            out[rec.get("scene", p.stem)] = sp
    return out


def collect(arm: str) -> list[dict]:
    path = RUNS / f"{arm}.jsonl"
    if not path.is_file():
        return []
    body = bodies(arm)
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        scene = r["scene"]
        shots = {}
        for stage in ("plan", "td", "iso"):
            # The baseline arm predates the run row carrying its image names, and
            # writes them under the scene id, which is what the field would have said.
            name = r.get(stage) or f"{scene}.png"
            if (SCENES / arm / stage / name).is_file():
                shots[stage] = f"/results/scenes/{arm}/{stage}/{name}"
        add = r.get("addendum") or ""
        b = body.get(scene, "")
        # Same arm, same reason: its isometric prompt is under a name of its own, and
        # it never recorded a top-down prompt, so that view is simply absent for it.
        iso_text = r.get("iso_prompt") or r.get("guided_prompt") or ""
        td_text = r.get("td_prompt") or ""
        rows.append({
            "id": scene,
            "title": r.get("title", ""),
            "source": r.get("prompt", ""),
            "genre": r.get("genre", ""),
            "shape": r.get("shape_label") or r.get("shape") or "",
            "order": r.get("order", ""),
            "status": r.get("status", ""),
            "error": (r.get("error") or "").splitlines()[:1],
            "iso": parts(iso_text, add, b),
            "td": parts(td_text, add, b),
            "n_iso": len(iso_text),
            "n_td": len(td_text),
            "shots": shots,
        })
    rows.sort(key=lambda x: x["id"])
    return rows


CSS = """
:root{--bg:#0f1220;--panel:#171b2e;--panel-2:#1e2340;--line:#2b3153;--text:#e7e9f3;
  --muted:#9aa0c0;--accent:#6c8cff;--green:#35c88b;--orange:#f2a54c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
  font:13px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header{padding:14px 22px;border-bottom:1px solid var(--line);position:sticky;top:0;
  background:var(--bg);z-index:5}
h1{margin:0 0 9px;font-size:17px}
.bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.tab{padding:5px 12px;border-radius:8px;border:1px solid var(--line);background:var(--panel);
  cursor:pointer;font-size:12.5px;color:var(--muted)}
.tab:hover{border-color:var(--accent)}
.tab.on{background:var(--accent);border-color:var(--accent);color:#0b0d18;font-weight:600}
input[type=search]{flex:1;min-width:220px;max-width:420px;padding:6px 11px;border-radius:8px;
  border:1px solid var(--line);background:var(--panel);color:var(--text);font-size:12.5px;
  outline:none}
input[type=search]:focus{border-color:var(--accent)}
.note{color:var(--muted);font-size:12px;margin-top:8px}
.key{display:flex;gap:16px;flex-wrap:wrap;font-size:11.5px;color:var(--muted);margin-top:8px}
.key i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px}
main{padding:16px 22px 80px}
.scene{border:1px solid var(--line);border-radius:11px;background:var(--panel);
  margin-bottom:14px;overflow:hidden}
.head{display:flex;align-items:center;gap:10px;padding:8px 13px;background:var(--panel-2);
  border-bottom:1px solid var(--line);flex-wrap:wrap}
.head b{font-size:13px}
.tag{font-size:11px;color:var(--muted);border:1px solid var(--line);border-radius:6px;
  padding:1px 7px}
.src{color:var(--muted);font-size:12px;flex:1;min-width:200px;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.05fr);gap:14px;padding:13px}
@media(max-width:1150px){.grid{grid-template-columns:1fr}}
pre{margin:0;white-space:pre-wrap;word-break:break-word;
  font:11.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;max-height:330px;overflow:auto}
.k-frame{color:#767c9d}
.k-body{color:#8ff0c2;background:rgba(53,200,139,.09)}
.k-addendum{color:#b9c6ff;background:rgba(108,140,255,.11)}
.shots{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;
  align-content:start}
.shots img{width:100%;border-radius:8px;border:1px solid var(--line);display:block;
  background:#0b0d18}
.shots figure{margin:0}
.shots figcaption{color:var(--muted);font-size:11px;text-align:center;margin-top:4px}
.which{display:flex;gap:6px;margin-bottom:8px}
.which button{font-size:11.5px;padding:3px 10px;border-radius:7px;border:1px solid var(--line);
  background:var(--panel-2);color:var(--muted);cursor:pointer}
.which button.on{color:var(--text);border-color:var(--accent)}
.fail{color:var(--orange);font-size:12px;padding:0 13px 12px}
.more{display:block;margin:18px auto;padding:8px 20px;border-radius:9px;
  border:1px solid var(--line);background:var(--panel);color:var(--text);cursor:pointer}
.more:hover{border-color:var(--accent)}
"""

JS = """
const DATA = PAYLOAD, ABOUT = ABOUTS;
const PAGE = 25;
let arm = Object.keys(DATA)[0], shown = PAGE, q = "", view = {};
const esc = s => (s==null?'':String(s)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const paint = ps => ps.map(p=>`<span class="k-${p.k}">${esc(p.t)}</span>`).join('');

function matching(){
  const rows = DATA[arm] || [];
  if (!q) return rows;
  const n = q.toLowerCase();
  return rows.filter(r => (r.id + ' ' + r.genre + ' ' + r.shape + ' ' + r.source)
    .toLowerCase().includes(n));
}
function scene(r){
  const has = ['iso','td'].filter(v => r['n_' + v] > 0);
  const which = has.includes(view[r.id]) ? view[r.id] : has[0];
  const ps = which === 'iso' ? r.iso : r.td;
  const chars = which === 'iso' ? r.n_iso : r.n_td;
  const by = {};
  ps.forEach(p => by[p.k] = (by[p.k]||0) + p.t.length);
  const label = {iso:'isometric', td:'top-down', plan:'authored plan'};
  const shots = ['plan','td','iso'].filter(k=>r.shots[k]).map(k=>
    `<figure><a href="${r.shots[k]}" target="_blank">
      <img src="${r.shots[k]}" loading="lazy"></a>
      <figcaption>${label[k]}</figcaption></figure>`).join('')
    || '<span class="fail">no images for this scene</span>';
  return `<section class="scene" data-id="${r.id}">
    <div class="head"><b>${r.id}</b>
      ${r.genre?`<span class="tag">${esc(r.genre)}</span>`:''}
      ${r.shape?`<span class="tag">${esc(r.shape)}</span>`:''}
      ${r.order?`<span class="tag">${esc(r.order)}-first</span>`:''}
      <span class="src">${esc(r.source.slice(0,150))}</span></div>
    ${r.status && r.status!=='ok'
      ? `<div class="fail">${esc(r.status)}: ${esc(r.error[0]||'')}</div>` : ''}
    <div class="grid">
      <div>
        <div class="which">
          ${has.map(v=>`<button data-v="${v}" class="${which===v?'on':''}">
            ${v==='iso'?'isometric':'top-down'} prompt</button>`).join('')}
          <span class="tag" style="margin-left:auto">${chars} chars
            ${by.body?`· ${Math.round(100*by.body/chars)}% from the author`:''}</span>
        </div>
        <pre>${paint(ps)}</pre>
      </div>
      <div class="shots">${shots}</div>
    </div></section>`;
}
function render(){
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('on', t.dataset.arm===arm));
  document.getElementById('about').textContent =
    `${(DATA[arm]||[]).length} scenes — ${ABOUT[arm]||''}`;
  const rows = matching();
  document.getElementById('out').innerHTML =
    rows.slice(0, shown).map(scene).join('')
    + (rows.length > shown
        ? `<button class="more" id="more">show ${Math.min(PAGE, rows.length-shown)} more
           of ${rows.length}</button>` : '');
  const more = document.getElementById('more');
  if (more) more.onclick = () => { shown += PAGE; render(); };
}
document.getElementById('tabs').addEventListener('click', e=>{
  const t = e.target.closest('.tab'); if(!t) return;
  arm = t.dataset.arm; shown = PAGE; render();
});
// Delegated, so the buttons keep working on rows appended later.
document.getElementById('out').addEventListener('click', e=>{
  const b = e.target.closest('.which button'); if(!b) return;
  view[b.closest('.scene').dataset.id] = b.dataset.v; render();
});
let timer;
document.getElementById('q').addEventListener('input', e=>{
  clearTimeout(timer);
  timer = setTimeout(()=>{ q = e.target.value.trim(); shown = PAGE; render(); }, 150);
});
render();
"""


def build(data: dict[str, list[dict]]) -> str:
    tabs = "".join(
        f'<button class="tab" data-arm="{a}">{a} <span style="opacity:.7">'
        f"{len(rows)}</span></button>"
        for a, rows in data.items())
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Prompts and what they drew</title>
<style>{CSS}</style></head><body>
<header>
  <h1>Prompts, and what they drew</h1>
  <div class="bar" id="tabs">{tabs}
    <input type="search" id="q" placeholder="filter by scene, genre, shape or prompt text">
  </div>
  <div class="note" id="about"></div>
  <div class="key">
    <span><i style="background:rgba(53,200,139,.5)"></i>the scene description,
      from the author</span>
    <span><i style="background:rgba(108,140,255,.55)"></i>feature list generated
      from the config</span>
    <span><i style="background:#767c9d"></i>camera and style wording, fixed</span>
  </div>
</header>
<main id="out"></main>
<script>const PAYLOAD = {json.dumps(data, ensure_ascii=False)};
const ABOUTS = {json.dumps(ABOUT)};</script>
<script>{JS}</script>
</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--out", type=pathlib.Path, default=RESULTS / "prompt_gallery.html")
    args = ap.parse_args()

    data = {}
    for arm in [a.strip() for a in args.arms.split(",") if a.strip()]:
        rows = collect(arm)
        if rows:
            data[arm] = rows
            shots = sum(len(r["shots"]) for r in rows)
            print(f"  {arm:9} {len(rows):4} scenes, {shots:5} images")
    if not data:
        print("no runs found under", RUNS)
        return
    args.out.write_text(build(data), encoding="utf-8")
    print(f"{sum(len(v) for v in data.values())} scenes -> {args.out} "
          f"({args.out.stat().st_size / 1e6:.1f} MB)")
    print("open /prompts")


if __name__ == "__main__":
    main()
