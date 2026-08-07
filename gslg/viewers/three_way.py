"""Three-arm viewer: the raw prompt, yesterday's Hard Needs run, today's Build.md run.

Each scene shows all three isometrics and all three top-downs side by side, then the
requirement table underneath. The requirements are the union of what the two guided
arms asked for, every row tagged with which arm asked, and each arm marked present or
absent independently by a judge that saw the three images shuffled and unlabelled.

Reading a row across tells you whether an arm delivered a feature it never requested.
That is the comparison worth having: scoring an arm only on its own asks tells you it
followed instructions, not whether the instructions were the right ones.

Writes `site/three_way.html`, which the server serves alongside `results/`.

Usage:
    python -m gslg.viewers.three_way
"""

from __future__ import annotations

import json
import pathlib

from gslg import paths
from gslg.judges import three_way as tws
from gslg.viewers import compare as brc

OUT = paths.SITE / "three_way.html"

ARM_LABEL = {
    "raw": "Raw prompt",
    "needs": "Yesterday &mdash; sub-genre Hard Needs",
    "rules": "Today &mdash; Build.md Part II",
}
def _load() -> tuple[list[dict], dict]:
    iso = {json.loads(x)["scene"]: json.loads(x)
           for x in (paths.SCORES / "three_way_iso.jsonl").open() if x.strip()}
    td = {json.loads(x)["scene"]: json.loads(x)
          for x in (paths.SCORES / "three_way_td.jsonl").open() if x.strip()}
    runs = {json.loads(x)["scene"]: json.loads(x)
            for x in (paths.RUNS / "rules.jsonl").open() if x.strip()}
    needs = {json.loads(x)["scene"]: json.loads(x)
             for x in (paths.RUNS / "needs.jsonl").open() if x.strip()}

    scenes = []
    for scene in sorted(iso):
        a, b = iso[scene], td.get(scene)
        r, n = runs[scene], needs[scene]
        feats = []
        for i, it in enumerate(a["items"]):
            t = b["items"][i] if b and i < len(b["items"]) else {}
            feats.append({
                "label": it["label"], "text": it["text"], "source": it["source"],
                "kind": it["kind"], "note": it.get("note", ""),
                "iso": {k: it.get(k) for k in tws.ARMS},
                "td": {k: t.get(k) for k in tws.ARMS},
            })
        scenes.append({
            "scene": scene, "prompt": r["prompt"], "genre": r["genre"],
            "preset": r["preset"], "subgenre": n.get("subgenre_id", ""),
            "order": r["order"], "route": r.get("route", []),
            "rulesAdd": r["addendum"], "needsAdd": n.get("addendum", ""),
            "total": a["total"], "features": feats,
            "iso": {k: a[f"{k}_met"] for k in tws.ARMS},
            "td": {k: (b[f"{k}_met"] if b else 0) for k in tws.ARMS},
        })

    tot = sum(s["total"] for s in scenes)
    agg = {"total": tot, "scenes": len(scenes)}
    for stage in ("iso", "td"):
        agg[stage] = {k: sum(s[stage][k] for s in scenes) for k in tws.ARMS}
    for src in ("needs", "rules"):
        its = [f for s in scenes for f in s["features"] if f["source"] == src]
        agg[f"own_{src}"] = {"n": len(its),
                             **{k: sum(1 for f in its if f["iso"][k]) for k in tws.ARMS}}
    return scenes, agg


def build() -> pathlib.Path:
    scenes, agg = _load()
    tot = agg["total"]

    def pct(stage: str, arm: str) -> str:
        return f"{100 * agg[stage][arm] / tot:.0f}%"

    cards = "".join(
        f"""<div class="card"><b>{pct('iso', a)} <span style="font-size:13px;
          color:var(--dim)">/ {pct('td', a)}</span></b>
          <span>{ARM_LABEL[a]}<br>isometric / top-down</span></div>"""
        for a in tws.ARMS)

    own = ""
    for src, who in (("needs", "yesterday asked for"), ("rules", "today asked for")):
        d = agg[f"own_{src}"]
        row = "  ".join(
            f"""<span class="chip {'acc' if a == src else ''}">{ARM_LABEL[a].split('&mdash;')[0].strip()}
              {100 * d[a] / d['n']:.0f}%</span>""" for a in tws.ARMS)
        own += f"""<tr><td>{who} <span class="chip">{d['n']} checks</span></td>
                   <td>{row}</td></tr>"""

    head = f"""<div class="sum" style="grid-template-columns:repeat(3,1fr)">{cards}</div>
    <div class="sect">
      <h3>Each arm on its own asks, and on the other's</h3>
      <table>{own}</table>
      <p class="note">Requirements are the union of what both guided arms asked for,
        {tot} checks over {agg['scenes']} scenes. An arm scoring well only on its own
        row means it followed its instructions; scoring well on the other row means it
        produced a playable layout regardless of who asked.</p>
    </div>"""

    html = f"""<!doctype html><meta charset="utf-8">
<title>Three arms &mdash; raw, Hard Needs, Build.md</title>
<style>{brc.CSS}
.tri{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
td.c{{width:64px}}
.src{{font-size:10px;text-transform:uppercase;letter-spacing:.05em}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:start}}
.col{{background:var(--pan);border:1px solid var(--ln);border-radius:10px;
  padding:12px 14px}}
.col.b{{border-color:#2f4a7a}}
.col h4{{font-size:13px;margin:0 0 2px}}
.req{{border-top:1px solid var(--ln);padding:9px 0}}
.req b{{font-size:12.5px}}
.mini{{width:auto;margin-top:6px;font-size:11px}}
.mini th,.mini td{{padding:1px 9px 1px 0;border:none;text-align:center}}
.mini th:first-child,.mini td:first-child{{text-align:left;color:var(--dim2);
  width:34px}}
.mini th{{color:var(--dim2);font-size:10px;text-transform:uppercase;
  letter-spacing:.04em}}
.none{{color:var(--dim2);font-size:12px;padding:10px 0}}
{brc.CARD_CSS}
</style>
<header><h1>Raw vs Hard Needs vs Build.md Part II</h1>{brc.nav("three_way.html")}
  <span class="sub">75 golden prompts &middot; same wrapper and style tail in all three
    &middot; judged blind on the union of both guided arms' requirements</span></header>
<div class="wrap">
  <div class="nav">
    <div class="f">
      <select id="fg"><option value="">all genres</option>
        {"".join(f'<option>{g}</option>' for g in sorted({s["genre"] for s in scenes}))}
      </select>
    </div>
    {brc.CARD_BAR}
    <div id="list"></div>
  </div>
  <div class="main" id="main"></div>
</div>
<dialog id="zoom"><img id="zimg"></dialog>
<script>
const S={json.dumps(scenes)};
const HEAD={json.dumps(head)};
const ARMS={json.dumps(list(tws.ARMS))};
const LABEL={json.dumps(ARM_LABEL)};
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>(
  {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]));
const $=id=>document.getElementById(id);
let cur=0;

const mark=v=>v==null?'<span style="color:#6f8296">&ndash;</span>'
  :v?'<span class="y">&#10003;</span>':'<span class="n">&#10007;</span>';

function strip(stage,s){{
  return `<div class="tri">`+ARMS.map(a=>{{
    return `<div class="fig ${{a==="rules"?"b":""}}">
      <h5>${{LABEL[a]}} &mdash; ${{s[stage][a]}}/${{s.total}}</h5>
      <img src="${{thumb(a,stage,s.scene)}}"
           data-full="${{shot(a,stage,s.scene)}}"></div>`;
  }}).join("")+`</div>`;
}}

const COL={{
  needs:{{title:"Yesterday &mdash; sub-genre Hard Needs",
    blurb:"Authored per sub-genre and injected as a demand: every item had to be "+
          "clearly present."}},
  rules:{{title:"Today &mdash; Build.md Part II",
    blurb:"A shape plus whatever options the router picked. Nothing is mandatory, "+
          "so a short list is a legitimate answer."}},
}};

function reqCol(s,src){{
  const fs=s.features.filter(f=>f.source===src);
  const met=a=>fs.filter(f=>f.iso[a]).length;
  return `<div class="col ${{src==="rules"?"b":""}}">
    <h4>${{COL[src].title}}</h4>
    <p class="note">${{COL[src].blurb}}</p>
    <div style="margin:8px 0 2px">
      <span class="chip">${{fs.length}} required</span>
      ${{fs.length?ARMS.map(a=>`<span class="chip ${{a===src?"acc":""}}">${{a}}
        ${{met(a)}}/${{fs.length}}</span>`).join(""):""}}
    </div>
    ${{fs.length?fs.map(f=>`
      <div class="req">
        <b>${{esc(f.label)}}</b> <span class="chip">${{esc(f.kind)}}</span>
        <div class="note">${{esc(f.text)}}</div>
        <table class="mini">
          <tr><th></th>${{ARMS.map(a=>`<th>${{a}}</th>`).join("")}}</tr>
          <tr><td>iso</td>${{ARMS.map(a=>`<td>${{mark(f.iso[a])}}</td>`).join("")}}</tr>
          <tr><td>td</td>${{ARMS.map(a=>`<td>${{mark(f.td[a])}}</td>`).join("")}}</tr>
        </table>
        ${{f.note?`<div class="note" style="color:var(--dim2);margin-top:5px">${{
          esc(f.note)}}</div>`:""}}
      </div>`).join(""):`<div class="none">This arm asked for nothing on this
        scene.</div>`}}
  </div>`;
}}

function render(i){{
  cur=i; const s=S[i];
  $("main").innerHTML=HEAD+`
  <div class="sect">
    <h2>${{esc(s.scene)}} &mdash; ${{esc(s.genre)}}
      <button class="dl" id="dlone">download this card</button>
      <span class="note" id="dlnote"></span></h2>
    <p class="note">${{esc(s.prompt)}}</p>
    <div style="margin-top:8px">
      <span class="chip">yesterday: ${{esc(s.subgenre||"unclassified")}}</span>
      <span class="chip acc">today: ${{esc(s.preset==="none"?"no preset":s.preset)}}</span>
      ${{s.route.map(r=>`<span class="chip warn">${{esc(r)}}</span>`).join("")}}
    </div>
  </div>

  <div class="sect"><h3>Stage A &mdash; isometric</h3>${{strip("iso",s)}}</div>
  <div class="sect"><h3>Stage B &mdash; top-down</h3>${{strip("td",s)}}</div>

  <div class="sect">
    <h3>What each arm required of this scene</h3>
    <p class="note" style="margin-bottom:10px">Each column is one arm's own hard
      requirements. The ticks beside a requirement are all three arms, so the two
      columns on the right of a row show what an arm produced <em>without</em> being
      asked for it.</p>
    <div class="two">${{reqCol(s,"needs")}}${{reqCol(s,"rules")}}</div>
  </div>

  <div class="sect">
    <h3>What each arm injected</h3>
    <div class="pair">
      <div><h4>Yesterday &mdash; Hard Needs</h4>
        <pre>${{esc(s.needsAdd)||"<em>nothing</em>"}}</pre></div>
      <div><h4>Today &mdash; Build.md Part II</h4>
        <pre>${{esc(s.rulesAdd)||"<em>nothing</em>"}}</pre></div>
    </div>
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
  const fg=$("fg").value;
  return S.map((s,i)=>({{s,i}})).filter(({{s}})=>!fg||s.genre===fg);
}}
function list(){{
  $("list").innerHTML=shown().map(({{s,i}})=>`<div class="row">${{pickBox(s.scene)}}
      <a href="#" data-i="${{i}}"><b>${{esc(s.scene)}}</b>
      <span class="note">${{s.iso.raw}}/${{s.iso.needs}}/${{s.iso.rules}}</span>
      <i>${{esc(s.genre)}}</i></a></div>`).join("");
  document.querySelectorAll(".nav a[data-i]").forEach(a=>a.onclick=e=>{{
    e.preventDefault(); render(+a.dataset.i); }});
  bindPicks();
}}
{brc.URL_JS}
{brc.CARD_JS}
$("fg").onchange=list;
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
    print(f"wrote {p}  ({p.stat().st_size // 1024} KB)")
