"""The full checklist a comparison was judged against, one column per asking arm.

A comparison scores every arm on the union of what the asking arms wanted. This page
is that union laid out in full, so the vocabularies can be read against each other
rather than inferred from a percentage.

Each requirement carries the scene it came from and a tick per arm, and each column
carries its own hit rate, which is what makes the asymmetry legible: an arm that only
scores in its own column followed instructions, while one that also scores in someone
else's produced a layout that happens to be right.

It was written for two columns and had the two arms' names in its headings. It now
takes them from the comparison, so a third asking arm is a third column.

Writes `site/requirements.html`.

Usage:
    python -m layoutgen.web.pages.requirements
    python -m layoutgen.web.pages.requirements rules_vs_raw
"""

from __future__ import annotations

import json
import pathlib
from collections import defaultdict

from layoutgen import arms as A
from layoutgen import paths
from layoutgen.web.pages import shared

OUT = paths.SITE / "requirements.html"


def widest() -> A.Comparison:
    """The comparison with the most asking arms - the one with the most to show."""
    return max(A.COMPARISONS.values(), key=lambda c: (len(c.asking), len(c.arms)))


def collect(cmp: A.Comparison) -> tuple[dict, int]:
    runs = A.load_runs()
    scores = {}
    for stage in paths.STAGES:
        path = cmp.scores(stage)
        scores[stage] = ({json.loads(x)["scene"]: json.loads(x)
                          for x in path.open() if x.strip()}
                         if path.is_file() else {})

    items = []
    for scene, r in sorted(scores["iso"].items()):
        t = scores["td"].get(scene)
        rows = A.rows_for(scene, runs)
        for i, it in enumerate(r["items"]):
            tt = t["items"][i] if t and i < len(t["items"]) else {}
            asker = A.ARMS.get(it["source"])
            items.append({
                "scene": scene, "label": it["label"], "text": it["text"],
                "kind": it["kind"], "source": it["source"],
                "group": asker.group(rows.get(asker.id, {})) if asker else "",
                "iso": it["present"],
                "td": tt.get("present", {a: None for a in cmp.arms}),
            })

    columns = {}
    for asker in cmp.asking:
        mine = [x for x in items if x["source"] == asker.id]
        by = defaultdict(list)
        for x in mine:
            by[x["group"] or "ungrouped"].append(x)
        columns[asker.id] = {
            "n": len(mine),
            "rate": {a: (100 * sum(1 for x in mine if x["iso"].get(a)) / len(mine)
                         if mine else 0) for a in cmp.arms},
            "groups": [{"name": k, "items": v}
                       for k, v in sorted(by.items(), key=lambda kv: -len(kv[1]))],
        }
    return columns, len(items)


def build(cmp: A.Comparison | None = None) -> pathlib.Path:
    cmp = cmp or widest()
    columns, total = collect(cmp)

    def bar(arm_id: str) -> str:
        col = columns[arm_id]
        cells = "".join(
            f"""<tr><td>{a.title}</td>
                <td style="width:58%"><div style="background:#1d2733;border-radius:4px">
                  <div style="width:{col['rate'][a.id]:.0f}%;background:{a.accent};
                    height:14px;border-radius:4px"></div></div></td>
                <td class="c" style="width:64px">{col['rate'][a.id]:.0f}%</td></tr>"""
            for a in cmp)
        return f"<table>{cells}</table>"

    order = "".join(f"<b>{a.title}</b>" + (" &middot; " if a is not list(cmp)[-1] else "")
                    for a in cmp)
    sides = "".join(f"""
    <div class="sect">
      <h2>{asker.title}</h2>
      <p class="note">{asker.blurb}</p>
      <p class="note"><b>{columns[asker.id]["n"]}</b> requirements across the scenes,
        grouped by what produced them.</p>
      <h3 style="margin-top:12px">Hit rate on this column (isometric)</h3>
      {bar(asker.id)}
      <div id="col_{asker.id}"></div>
    </div>""" for asker in cmp.asking)

    html = f"""<!doctype html><meta charset="utf-8">
<title>Requirements used &mdash; {cmp.title}</title>
<style>{shared.CSS}
.cols{{display:grid;grid-template-columns:repeat({len(cmp.asking)},1fr);gap:14px;
  align-items:start}}
.req{{border-bottom:1px solid var(--ln);padding:7px 0}}
.req:last-child{{border-bottom:none}}
.req .t{{display:flex;gap:8px;align-items:baseline}}
.req .t b{{font-size:12px}}
.marks{{margin-left:auto;white-space:nowrap;font-size:12px}}
.marks span{{margin-left:7px}}
.gname{{color:var(--acc);font-size:12px;font-weight:600;margin:12px 0 2px}}
</style>
<header><h1>Requirements used</h1>{shared.nav("requirements.html")}
  <span class="sub">the full union {cmp.title.lower()} was judged against
    &mdash; {total} requirements</span></header>
<div class="main" style="height:calc(100vh - 49px);overflow:auto">
  <div class="sect">
    <h3>How to read this</h3>
    <p class="note">Each requirement below was marked present or absent in every image
      independently, by a judge that saw them shuffled and unlabelled. The ticks on a
      row are, in order, {order}, for the isometric. A requirement appears in the
      column of the arm that asked for it &mdash; so another arm's score in that
      column is what it produced without being told to.</p>
  </div>
  <div class="cols">{sides}</div>
</div>
<script>
const COLS={json.dumps({k: v["groups"] for k, v in columns.items()})};
const ARMS={json.dumps([{"id": a.id, "title": a.title} for a in cmp])};
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>(
  {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]));
const mark=(v,t)=>`<span title="${{t}}">`+
  (v==null?'<span style="color:#6f8296">&ndash;</span>'
   :v?'<span class="y">&#10003;</span>':'<span class="n">&#10007;</span>')+`</span>`;

for(const [src,groups] of Object.entries(COLS)){{
  document.getElementById("col_"+src).innerHTML=groups.map(g=>`
    <div class="gname">${{esc(g.name)}}
      <span class="chip">${{g.items.length}}</span></div>
    ${{g.items.map(x=>`
      <div class="req">
        <div class="t"><b>${{esc(x.label)}}</b>
          <span class="chip">${{esc(x.scene)}}</span>
          <span class="chip">${{esc(x.kind)}}</span>
          <span class="marks">${{ARMS.map(a=>mark(x.iso[a.id],a.title)).join("")}}</span>
        </div>
        <div class="note">${{esc(x.text)}}</div>
      </div>`).join("")}}`).join("");
}}
</script>"""
    OUT.write_text(html, encoding="utf-8")
    return OUT


if __name__ == "__main__":
    import sys

    p = build(A.COMPARISONS[sys.argv[1]] if len(sys.argv) > 1 else None)
    print(f"wrote {p}  ({p.stat().st_size // 1024} KB)")
