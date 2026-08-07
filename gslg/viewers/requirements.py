"""Side by side: every requirement each arm asked for, and how all three arms scored.

The three-arm comparison judges each image against the union of what both guided arms
requested. This page is that union laid out in full - yesterday's sub-genre Hard Needs
on the left, today's Build.md features on the right - so the two vocabularies can be
read against each other rather than inferred from a score.

Each requirement carries the scene it came from and a tick per arm, and each side
carries its own hit rate, which is what makes the asymmetry legible: an arm that only
scores on its own column followed instructions, while one that also scores on the
other column produced a layout that happens to be right.

Writes `site/requirements.html`.

Usage:
    python -m gslg.viewers.requirements
"""

from __future__ import annotations

import json
import pathlib
from collections import defaultdict

from gslg import paths
from gslg.judges import three_way as tws
from gslg.viewers import compare as brc

OUT = paths.SITE / "requirements.html"

SIDE = {
    "needs": dict(title="Yesterday &mdash; sub-genre Hard Needs",
                  blurb="Authored per sub-genre, 44 of them, and injected as a "
                        "demand: every listed item had to be clearly present. The "
                        "list was fixed once the classifier chose a sub-genre."),
    "rules": dict(title="Today &mdash; Build.md Part II",
                  blurb="A shape plus whichever options the router picked, taken "
                        "from the document at run time. Nothing is mandatory, so a "
                        "short list - or none at all - is a legitimate answer."),
}


def _load() -> tuple[dict, dict, list[dict]]:
    iso = {json.loads(x)["scene"]: json.loads(x)
           for x in (paths.SCORES / "three_way_iso.jsonl").open() if x.strip()}
    td = {json.loads(x)["scene"]: json.loads(x)
          for x in (paths.SCORES / "three_way_td.jsonl").open() if x.strip()}

    items = []
    for scene, r in sorted(iso.items()):
        t = td.get(scene)
        for i, it in enumerate(r["items"]):
            tt = t["items"][i] if t and i < len(t["items"]) else {}
            items.append({
                "scene": scene, "genre": r["genre"],
                "group": r["subgenre"] if it["source"] == "needs" else
                         (r["preset"] if r["preset"] != "none" else r["genre"]),
                "label": it["label"], "text": it["text"], "kind": it["kind"],
                "source": it["source"], "note": it.get("note", ""),
                "iso": {a: it.get(a) for a in tws.ARMS},
                "td": {a: tt.get(a) for a in tws.ARMS},
            })

    sides = {}
    for src in ("needs", "rules"):
        mine = [x for x in items if x["source"] == src]
        by = defaultdict(list)
        for x in mine:
            by[x["group"]].append(x)
        sides[src] = {
            "n": len(mine),
            "rate": {a: (100 * sum(1 for x in mine if x["iso"][a]) / len(mine)
                         if mine else 0) for a in tws.ARMS},
            "rateTd": {a: (100 * sum(1 for x in mine if x["td"][a]) / len(mine)
                           if mine else 0) for a in tws.ARMS},
            "groups": [{"name": k, "items": v}
                       for k, v in sorted(by.items(), key=lambda kv: -len(kv[1]))],
        }
    return sides, {}, items


def build() -> pathlib.Path:
    sides, _, items = _load()

    def bar(src: str) -> str:
        s = sides[src]
        cells = "".join(
            f"""<tr><td>{brc.PAGES and ''}{lbl}</td>
                <td style="width:60%"><div style="background:#1d2733;border-radius:4px">
                  <div style="width:{s['rate'][a]:.0f}%;background:{col};height:14px;
                    border-radius:4px"></div></div></td>
                <td class="c" style="width:64px">{s['rate'][a]:.0f}%</td></tr>"""
            for a, lbl, col in (
                ("raw", "raw prompt", "#3d4a5c"),
                ("needs", "Hard Needs arm", "#58a6ff"),
                ("rules", "Build.md arm", "#3fb950")))
        return f"<table>{cells}</table>"

    html = f"""<!doctype html><meta charset="utf-8">
<title>Requirements used &mdash; both arms</title>
<style>{brc.CSS}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:start}}
.req{{border-bottom:1px solid var(--ln);padding:7px 0}}
.req:last-child{{border-bottom:none}}
.req .t{{display:flex;gap:8px;align-items:baseline}}
.req .t b{{font-size:12px}}
.marks{{margin-left:auto;white-space:nowrap;font-size:12px}}
.marks span{{margin-left:7px}}
.gname{{color:var(--acc);font-size:12px;font-weight:600;margin:12px 0 2px}}
.legend{{color:var(--dim2);font-size:11px}}
</style>
<header><h1>Requirements used</h1>{brc.nav("requirements.html")}
  <span class="sub">the full union the three-arm comparison was judged against
    &mdash; {len(items)} requirements</span></header>
<div class="main" style="height:calc(100vh - 49px);overflow:auto">
  <div class="sect">
    <h3>How to read this</h3>
    <p class="note">Each requirement below was marked present or absent in all three
      images independently, by a judge that saw them shuffled and unlabelled. The
      three ticks on a row are, in order,
      <b>raw prompt</b> &middot; <b>Hard Needs arm</b> &middot; <b>Build.md arm</b>,
      for the isometric. A requirement appears on the side of the arm that asked for
      it &mdash; so the other arm's score on that side is what it produced without
      being told to.</p>
  </div>
  <div class="two">
    {"".join(f'''
    <div class="sect">
      <h2>{SIDE[src]["title"]}</h2>
      <p class="note">{SIDE[src]["blurb"]}</p>
      <p class="note"><b>{sides[src]["n"]}</b> requirements across the 75 scenes,
        grouped by the label that produced them.</p>
      <h3 style="margin-top:12px">Hit rate on this side (isometric)</h3>
      {bar(src)}
      <div id="side_{src}"></div>
    </div>''' for src in ("needs", "rules"))}
  </div>
</div>
<script>
const SIDES={json.dumps({k: v["groups"] for k, v in sides.items()})};
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>(
  {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]));
const mark=(v,t)=>`<span title="${{t}}">`+(v==null?'<span style="color:#6f8296">&ndash;</span>'
  :v?'<span class="y">&#10003;</span>':'<span class="n">&#10007;</span>')+`</span>`;

for(const [src,groups] of Object.entries(SIDES)){{
  document.getElementById("side_"+src).innerHTML=groups.map(g=>`
    <div class="gname">${{esc(g.name)}}
      <span class="chip">${{g.items.length}}</span></div>
    ${{g.items.map(x=>`
      <div class="req">
        <div class="t"><b>${{esc(x.label)}}</b>
          <span class="chip">${{esc(x.scene)}}</span>
          <span class="chip">${{esc(x.kind)}}</span>
          <span class="marks">
            ${{mark(x.iso.raw,"raw")}}${{mark(x.iso.needs,"Hard Needs")}}${{
              mark(x.iso.rules,"Build.md")}}</span></div>
        <div class="note">${{esc(x.text)}}</div>
      </div>`).join("")}}`).join("");
}}
</script>"""
    OUT.write_text(html, encoding="utf-8")
    return OUT


if __name__ == "__main__":
    p = build()
    print(f"wrote {p}  ({p.stat().st_size // 1024} KB)")
