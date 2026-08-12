"""Build a page setting one run's prompts against another's, scene by scene.

The gallery shows what a run sent; this shows what changed between two of them. The
pairing that matters right now is the live 614-scene run against the end-to-end arm,
because they differ in one place only - where the body of the prompt comes from. The
live run sends the author's message as written; the e2e arm sends a rewrite of it
produced from the intake answers. Everything downstream of that is the same code.

Scenes the second run did not cover are left out rather than shown half empty.

Usage:
    python tools/build_run_compare.py                    # answered vs e2e
    python tools/build_run_compare.py --left rules --right skill
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen.paths import RESULTS, ROUTING, RUNS, SCENES
from layoutgen.pipeline.prompts import decompose

#: How each arm decides the body of its prompt - the one thing this page is comparing.
BODY_IS = {
    "answered": "the author's message, sent as written",
    "e2e": "a rewrite of the message, from the agent's own questions and answers",
    "blob": "a rewrite of the message, from the curated questions and answers",
    "skill": "the author's message, sent as written",
    "rules": "the author's message, sent as written",
}


def runs(arm: str) -> dict[str, dict]:
    path = RUNS / f"{arm}.jsonl"
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["scene"]] = r
    return out


def bodies(arm: str) -> dict[str, str]:
    """The rewritten body per scene, for the arms that have one."""
    out: dict[str, str] = {}
    d = ROUTING / arm
    if d.is_dir():
        for p in d.glob("*.json"):
            rec = json.loads(p.read_text(encoding="utf-8"))
            if sp := (rec.get("scene_prompt") or "").strip():
                out[rec.get("scene", p.stem)] = sp
    return out


def side(arm: str, r: dict, body: str) -> dict:
    parts = decompose(r.get("iso_prompt") or "", r.get("addendum") or "", body)
    by: dict[str, int] = {}
    for kind, text in parts:
        by[kind] = by.get(kind, 0) + len(text)
    shots = {}
    for stage in ("plan", "td", "iso"):
        name = r.get(stage) or ""
        if name and (SCENES / arm / stage / name).is_file():
            shots[stage] = f"/results/scenes/{arm}/{stage}/{name}"
    return {
        "genre": r.get("genre", ""),
        "shape": r.get("shape_label") or r.get("shape") or "",
        "order": r.get("order", ""),
        "parts": [{"k": k, "t": t} for k, t in parts],
        "chars": sum(by.values()),
        "body": by.get("body", 0),
        "addendum": by.get("addendum", 0),
        "frame": by.get("frame", 0),
        "shots": shots,
    }


def collect(left: str, right: str) -> tuple[list[dict], list[str]]:
    lr, rr = runs(left), runs(right)
    lb, rb = bodies(left), bodies(right)
    rows, missing = [], sorted(set(rr) - set(lr))
    for scene in sorted(set(lr) & set(rr)):
        rows.append({
            "id": scene,
            "source": rr[scene].get("prompt", "") or lr[scene].get("prompt", ""),
            "left": side(left, lr[scene], lb.get(scene, "")),
            "right": side(right, rr[scene], rb.get(scene, "")),
        })
    return rows, missing


CSS = """
:root{--bg:#0f1220;--panel:#171b2e;--panel-2:#1e2340;--line:#2b3153;--text:#e7e9f3;
  --muted:#9aa0c0;--accent:#6c8cff;--green:#35c88b;--orange:#f2a54c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
  font:13px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header{padding:16px 22px;border-bottom:1px solid var(--line)}
h1{margin:0 0 4px;font-size:18px}
h2{font-size:13px;margin:0}
.lede{color:var(--muted);font-size:12.5px;max-width:900px;margin:0}
.totals{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:16px 0 4px;max-width:1000px}
.tot{border:1px solid var(--line);border-radius:10px;background:var(--panel);padding:12px 14px}
.tot h3{margin:0 0 2px;font-size:12.5px}
.tot .who{color:var(--muted);font-size:11.5px;margin-bottom:9px}
.bar{display:flex;height:16px;border-radius:5px;overflow:hidden;margin-bottom:7px}
.bar span{display:block}
.b-body{background:rgba(53,200,139,.75)}
.b-addendum{background:rgba(108,140,255,.75)}
.b-frame{background:#4d5470}
.tot dl{display:grid;grid-template-columns:auto 1fr;gap:1px 10px;margin:0;font-size:11.5px}
.tot dt{color:var(--muted)}
.tot dd{margin:0}
.delta{color:var(--orange)}
.up{color:var(--green)}
main{padding:16px 22px 80px}
.scene{border:1px solid var(--line);border-radius:11px;background:var(--panel);
  margin-bottom:14px;overflow:hidden}
.head{display:flex;gap:10px;align-items:baseline;padding:9px 13px;background:var(--panel-2);
  border-bottom:1px solid var(--line)}
.head b{font-size:13.5px}
.head .src{color:var(--muted);font-size:12px;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:0}
.pair>div{padding:12px 14px}
.pair>div:first-child{border-right:1px solid var(--line)}
.who{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;margin-bottom:8px}
.who b{font-size:12px}
.tag{font-size:11px;color:var(--muted);border:1px solid var(--line);border-radius:6px;
  padding:1px 7px}
.tag.diff{color:var(--orange);border-color:var(--orange)}
pre{margin:0 0 10px;white-space:pre-wrap;word-break:break-word;
  font:11.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;max-height:300px;overflow:auto}
.k-frame{color:#767c9d}
.k-body{color:#8ff0c2;background:rgba(53,200,139,.09)}
.k-addendum{color:#b9c6ff;background:rgba(108,140,255,.11)}
.shots{display:grid;grid-template-columns:1fr 1fr;gap:9px}
.shots img{width:100%;border-radius:8px;border:1px solid var(--line);display:block;
  background:#0b0d18}
.key{display:flex;gap:16px;flex-wrap:wrap;font-size:11.5px;color:var(--muted);margin-top:10px}
.key i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px}
.miss{color:var(--muted);font-size:12px;margin-top:10px}
"""

JS = """
const D = DATA;
const esc = s => (s==null?'':String(s)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const paint = ps => ps.map(p=>`<span class="k-${p.k}">${esc(p.t)}</span>`).join('');

function col(s, other, label){
  const shots = ['plan','td','iso'].filter(k=>s.shots[k]).map(k=>
    `<a href="${s.shots[k]}" target="_blank"><img src="${s.shots[k]}" loading="lazy"></a>`
    ).join('');
  const tag = (v, o, t) => v ? `<span class="tag${v!==o?' diff':''}">${esc(t||v)}</span>` : '';
  return `<div>
    <div class="who"><b>${label}</b>
      ${tag(s.genre, other.genre)} ${tag(s.shape, other.shape)}
      ${tag(s.order, other.order, s.order + '-first')}
      <span class="tag" style="margin-left:auto">${s.chars} chars ·
        ${Math.round(100*s.body/s.chars)}% body</span></div>
    <pre>${paint(s.parts)}</pre>
    <div class="shots">${shots}</div></div>`;
}
document.getElementById('out').innerHTML = D.rows.map(r=>`
  <section class="scene">
    <div class="head"><b>${r.id}</b><span class="src">${esc(r.source.slice(0,170))}</span></div>
    <div class="pair">${col(r.left, r.right, D.left)}${col(r.right, r.left, D.right)}</div>
  </section>`).join('');
"""


def totals(rows: list[dict], key: str) -> dict:
    out = {k: sum(r[key][k] for r in rows) for k in ("body", "addendum", "frame")}
    out["chars"] = sum(out.values())
    return out


def panel(name: str, t: dict, other: dict | None) -> str:
    def line(k: str, label: str) -> str:
        d = ""
        if other:
            diff = t[k] - other[k]
            cls = "up" if diff > 0 else "delta"
            if diff:
                d = (f' <span class="{cls}">{diff:+,} '
                     f'({diff / other[k]:+.0%})</span>' if other[k] else "")
        return (f"<dt>{label}</dt><dd>{t[k]:,} chars · "
                f"{t[k] / t['chars']:.0%}{d}</dd>")

    bar = "".join(f'<span class="b-{k}" style="width:{t[k] / t["chars"]:.1%}"></span>'
                  for k in ("body", "addendum", "frame"))
    return f"""<div class="tot"><h3>{name}</h3>
      <div class="who">{BODY_IS.get(name, "")}</div>
      <div class="bar">{bar}</div>
      <dl>{line("body", "scene description")}{line("addendum", "generated features")}
      {line("frame", "fixed wording")}
      <dt>total</dt><dd>{t["chars"]:,} chars</dd></dl></div>"""


def build(rows: list[dict], left: str, right: str, missing: list[str]) -> str:
    lt, rt = totals(rows, "left"), totals(rows, "right")
    payload = {"rows": rows, "left": left, "right": right}
    gone = (f'<p class="miss">{", ".join(missing)} '
            f"{'is' if len(missing) == 1 else 'are'} in the {right} run but not in "
            f"{left}, so {'it has' if len(missing) == 1 else 'they have'} no pair "
            "here.</p>") if missing else ""
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{left} vs {right}</title>
<style>{CSS}</style></head><body>
<header>
  <h1>{left} vs {right} — the same {len(rows)} scenes, two runs</h1>
  <p class="lede">Both runs compose the prompt the same way and end on the same style
  wording. They differ in where the body comes from, and in the config that generates
  the feature list under it. Totals below are over the {len(rows)} scenes both ran;
  percentages on the right-hand panel are its change from {left}.</p>
  <div class="totals">{panel(left, lt, None)}{panel(right, rt, lt)}</div>
  <div class="key">
    <span><i style="background:rgba(53,200,139,.75)"></i>scene description</span>
    <span><i style="background:rgba(108,140,255,.75)"></i>features generated from
      the config</span>
    <span><i style="background:#4d5470"></i>camera and style wording, fixed</span>
    <span>an orange tag marks a value the two runs disagree on</span>
  </div>
  {gone}
</header>
<main id="out"></main>
<script>const DATA = {json.dumps(payload, ensure_ascii=False)};</script>
<script>{JS}</script>
</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--left", default="answered", help="the run to compare against")
    ap.add_argument("--right", default="e2e", help="the newer run")
    ap.add_argument("--out", type=pathlib.Path, default=RESULTS / "run_compare.html")
    args = ap.parse_args()

    rows, missing = collect(args.left, args.right)
    if not rows:
        print(f"no scenes in both {args.left} and {args.right}")
        return
    args.out.write_text(build(rows, args.left, args.right, missing), encoding="utf-8")
    lt, rt = totals(rows, "left"), totals(rows, "right")
    print(f"{len(rows)} scenes in both -> {args.out}")
    for name, t in ((args.left, lt), (args.right, rt)):
        print(f"  {name:9} {t['chars']:6} chars   body {t['body'] / t['chars']:4.0%}"
              f"   addendum {t['addendum'] / t['chars']:4.0%}")
    if missing:
        print(f"  only in {args.right}: {', '.join(missing)}")
    print("open /compare")


if __name__ == "__main__":
    main()
