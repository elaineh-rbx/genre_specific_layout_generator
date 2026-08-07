"""One page per comparison, drawn from however many arms it has.

There used to be two of these, one written for a pair of arms and one for three, with
the counts wired into their CSS grids, their column headers and their summary cards.
They showed the same thing: the scenes down the side, the images across the top, and a
checklist underneath saying which arm actually produced each requested feature.

So there is one now, and the number of arms is whatever the comparison says it is.
Adding a fourth arm changes the width of a row, not the file.

Usage:
    python -m gslg.web.pages.comparison            # every comparison
    python -m gslg.web.pages.comparison three_way
"""

from __future__ import annotations

import json
import pathlib

from gslg import arms as A
from gslg import paths
from gslg.web.pages import shared


def _scores(cmp: A.Comparison) -> dict[str, dict[str, dict]]:
    out = {}
    for stage in paths.STAGES:
        path = cmp.scores(stage)
        out[stage] = ({json.loads(x)["scene"]: json.loads(x)
                       for x in path.open() if x.strip()} if path.is_file() else {})
    return out


def collect(cmp: A.Comparison) -> list[dict]:
    """Everything one page needs, per scene, with the arms already lined up.

    The checklist is rebuilt from the run files rather than read out of a score file
    so that a scene which failed to judge still lists what was asked of it - a blank
    row is more useful than a missing scene.
    """
    runs = A.load_runs()
    scores = _scores(cmp)
    scenes = sorted(set.intersection(*(set(runs[a.id]) for a in cmp.runs)))

    out = []
    for scene in scenes:
        rows = A.rows_for(scene, runs)
        reqs = cmp.requirements(rows)
        judged = {st: scores[st].get(scene) for st in paths.STAGES}

        feats = []
        for i, q in enumerate(reqs):
            marks = {}
            for st in paths.STAGES:
                s = judged[st]
                item = s["items"][i] if s and i < len(s["items"]) else None
                marks[st] = item["present"] if item else None
            note = next((s["items"][i].get("note", "") for st in paths.STAGES
                         if (s := judged[st]) and i < len(s["items"])), "")
            feats.append({**q, "marks": marks, "note": note})

        anchor = next((r for r in rows.values() if r), {})
        out.append({
            "scene": scene,
            "title": anchor.get("title", ""),
            "prompt": anchor.get("prompt", ""),
            "genre": anchor.get("genre", ""),
            "order": rows.get("rules", {}).get("order", "std"),
            "preset": rows.get("rules", {}).get("preset", "none"),
            "plan": rows.get("rules", {}).get("plan"),
            "total": len(feats),
            "met": {st: (judged[st]["met"] if judged[st]
                         else {a: 0 for a in cmp.arms}) for st in paths.STAGES},
            "features": feats,
            "given": {
                a.id: {"chips": a.chips(rows.get(a.id, {})),
                       "addendum": a.addendum(rows.get(a.id, {})),
                       "sent": [[label, rows.get(a.id, {}).get(key, "")]
                                for label, key in a.sent
                                if rows.get(a.id, {}).get(key)]}
                for a in cmp},
        })
    return out


def summary(cmp: A.Comparison, scenes: list[dict]) -> str:
    """The headline: every arm's hit rate, and who asked for what."""
    tot = sum(s["total"] for s in scenes) or 1
    cards = []
    for arm in cmp:
        pct = {st: 100 * sum(s["met"][st].get(arm.id, 0) for s in scenes) / tot
               for st in paths.STAGES}
        cards.append(
            f'<div class="card"><b style="color:{arm.accent}">{pct["iso"]:.0f}%'
            f' <span style="color:var(--dim2);font-size:13px">/ {pct["td"]:.0f}%</span></b>'
            f'<span>{arm.title} &mdash; isometric / top-down</span></div>')
    cards.append(
        f'<div class="card"><b>{tot}</b><span>requirement checks across '
        f'{len(scenes)} scenes, judged blind, per arm</span></div>')
    head = f'<div class="sum">{"".join(cards)}</div>'

    if len(cmp.asking) > 1:
        rows = []
        for asker in cmp.asking:
            its = [(f, s) for s in scenes for f in s["features"]
                   if f["source"] == asker.id]
            if not its:
                continue
            cells = ""
            for arm in cmp:
                hits = sum(1 for f, _ in its
                           for st in paths.STAGES
                           if f["marks"][st] and f["marks"][st].get(arm.id))
                cells += (f'<td class="c" style="color:{arm.accent}">'
                          f'{100 * hits / (2 * len(its)):.0f}%</td>')
            rows.append(f'<tr><td>{asker.title}</td>'
                        f'<td class="c">{len(its)}</td>{cells}</tr>')
        heads = "".join(f'<th class="c">{a.short}</th>' for a in cmp)
        head += (
            '<div class="sect"><h3>Split by which arm asked</h3>'
            '<p class="note">Every arm is judged on the union, so a row read across '
            'shows whether an arm happened to deliver a feature it never asked for.'
            '</p><table><tr><th>asked by</th><th class="c">checks</th>'
            f'{heads}</tr>{"".join(rows)}</table></div>')
    return head


def build(cmp: A.Comparison) -> pathlib.Path:
    scenes = collect(cmp)
    arms = [{"id": a.id, "title": a.title, "short": a.short, "accent": a.accent,
             "blurb": a.blurb} for a in cmp]
    genres = sorted({s["genre"] for s in scenes if s["genre"]})

    html = f"""<!doctype html><meta charset="utf-8">
<title>{cmp.title}</title>
<style>{shared.CSS}{shared.CARD_CSS}
.strip{{display:grid;gap:12px;margin-bottom:10px}}
.strip h5 span{{color:var(--dim2);font-weight:400}}
.given{{display:grid;gap:12px;margin-top:4px}}
.given .box{{border:1px solid var(--ln);border-radius:8px;padding:9px 11px}}
.given .box h4{{margin:0 0 6px}}
</style>
<header><h1>{cmp.title}</h1>{shared.nav(cmp.page)}
  <span class="sub">{len(scenes)} golden prompts &middot; identical wrapper and style
    tail &middot; the only difference is what each arm was told</span></header>
<div class="wrap">
  <div class="nav">
    <div class="f">
      <select id="fg"><option value="">all genres</option>
        {"".join(f'<option>{g}</option>' for g in genres)}</select>
      <select id="fo"><option value="">any order</option><option>std</option>
        <option>p6</option><option>layout</option></select>
    </div>
    {shared.CARD_BAR}
    <div id="list"></div>
  </div>
  <div class="main" id="main"></div>
</div>
<dialog id="zoom"><img id="zimg"></dialog>
<script>
const S={json.dumps(scenes)};
const ARMS={json.dumps(arms)};
const HEAD={json.dumps(summary(cmp, scenes))};
const STAGES=[["iso","isometric"],["td","top-down"]];
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>(
  {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]));
const $=id=>document.getElementById(id);
let cur=0;

function mark(v){{ return v===null||v===undefined
  ?'<span style="color:#6f8296">&ndash;</span>'
  :v?'<span class="y">&#10003;</span>':'<span class="n">&#10007;</span>'; }}

function strip(s,stage){{
  const cells=ARMS.map(a=>`<div class="fig">
    <h5 style="color:${{a.accent}}">${{esc(a.title)}}
      <span>&mdash; ${{s.met[stage][a.id]}}/${{s.total}}</span></h5>
    <img src="${{thumb(a.id,stage,s.scene)}}" data-full="${{shot(a.id,stage,s.scene)}}">
  </div>`).join("");
  return `<div class="strip" style="grid-template-columns:repeat(${{ARMS.length}},1fr)">
    ${{cells}}</div>`;
}}

function table(s){{
  const top=ARMS.map(a=>`<th class="c" colspan="2" style="color:${{a.accent}}">`+
    `${{esc(a.short)}}</th>`).join("");
  const sub=ARMS.map(()=>`<th class="c">iso</th><th class="c">top</th>`).join("");
  const rows=s.features.map(f=>{{
    const src=ARMS.find(a=>a.id===f.source);
    const cells=ARMS.map(a=>STAGES.map(([st])=>
      `<td class="c">${{mark(f.marks[st]?f.marks[st][a.id]:null)}}</td>`).join("")).join("");
    return `<tr><td><b>${{esc(f.label)}}</b>
      <span class="chip" ${{src?`style="color:${{src.accent}}"`:""}}>${{
        src?esc(src.short):esc(f.kind)}}</span>
      <div class="note">${{esc(f.text)}}</div>
      ${{f.note?`<div class="note" style="color:var(--dim2)">${{esc(f.note)}}</div>`:""}}
      </td>${{cells}}</tr>`;
  }}).join("");
  return `<table><tr><th rowspan="2">Requirement</th>${{top}}</tr><tr>${{sub}}</tr>
    ${{rows}}</table>`;
}}

function given(s){{
  const box=ARMS.map(a=>{{
    const g=s.given[a.id]||{{}};
    const chips=(g.chips||[]).map(c=>`<span class="chip acc">${{esc(c)}}</span>`).join("");
    const sent=(g.sent||[]).map(([l,p])=>
      `<h3 style="margin-top:8px">prompt sent &mdash; ${{esc(l)}}</h3>
       <pre>${{esc(p)}}</pre>`).join("");
    return `<div class="box"><h4 style="color:${{a.accent}}">${{esc(a.title)}}</h4>
      <p class="note">${{esc(a.blurb)}}</p>${{chips}}
      ${{g.addendum?`<pre style="margin-top:7px">${{esc(g.addendum)}}</pre>`
        :`<p class="note">nothing injected</p>`}}${{sent}}</div>`;
  }}).join("");
  return `<div class="given" style="grid-template-columns:repeat(${{
    Math.min(ARMS.length,3)}},1fr)">${{box}}</div>`;
}}

function render(i){{
  cur=i; const s=S[i];
  $("main").innerHTML = HEAD + `
  <div class="sect">
    <h2>${{esc(s.scene)}} &mdash; ${{esc(s.genre)}}
      ${{s.preset!=="none"?`<span class="chip acc">${{esc(s.preset)}}</span>`
        :`<span class="chip">no preset fitted</span>`}}
      <span class="chip">${{esc(s.order)}}</span></h2>
    <p class="note">${{esc(s.prompt)}}</p>
  </div>
  ${{STAGES.map(([st,label])=>`<div class="sect"><h3>${{label}}</h3>
    ${{strip(s,st)}}</div>`).join("")}}
  ${{s.plan?`<div class="sect"><h3>plan the rules arm drew first</h3>
    <div class="fig" style="max-width:420px"><img src="${{thumb("rules","plan",s.scene)}}"
      data-full="${{shot("rules","plan",s.scene)}}"></div></div>`:""}}
  <div class="sect"><h3>Requirements &mdash; ${{s.total}} checked in each image</h3>
    ${{table(s)}}</div>
  <div class="sect"><h3>What each arm was given</h3>${{given(s)}}</div>`;
  document.querySelectorAll(".nav a").forEach((a,j)=>
    a.classList.toggle("on",j===i));
  $("main").scrollTop=0;
}}

function shown(){{
  const g=$("fg").value,o=$("fo").value;
  return S.map((s,i)=>({{s,i}})).filter(({{s}})=>
    (!g||s.genre===g)&&(!o||s.order===o));
}}

function list(){{
  $("list").innerHTML=shown().map(({{s,i}})=>{{
    const tally=ARMS.map(a=>s.met.iso[a.id]).join("/");
    return `<div class="row">${{pickBox(s.scene)}}
      <a href="#" data-i="${{i}}">${{s.scene}} &mdash; ${{esc(s.genre)}}
        <i>${{tally}} of ${{s.total}} visible</i></a></div>`;
  }}).join("");
  $("list").querySelectorAll("a").forEach(a=>a.onclick=e=>{{
    e.preventDefault(); render(+a.dataset.i);}});
  bindPicks();
}}

$("fg").onchange=$("fo").onchange=()=>{{list();
  const f=shown(); if(f.length) render(f[0].i);}};
document.addEventListener("click",e=>{{
  if(e.target.tagName==="IMG"&&e.target.dataset.full){{
    $("zimg").src=e.target.dataset.full; $("zoom").showModal();}}
  else if(e.target.id==="zoom"||e.target.id==="zimg") $("zoom").close();
}});
{shared.URL_JS}
{shared.CARD_JS}
list(); render(0);
</script>"""

    out = paths.SITE / cmp.page
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


def build_all() -> list[pathlib.Path]:
    return [build(c) for c in A.COMPARISONS.values()]


if __name__ == "__main__":
    import sys

    names = sys.argv[1:] or list(A.COMPARISONS)
    for name in names:
        print(build(A.COMPARISONS[name]))
