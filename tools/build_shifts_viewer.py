"""Build a single-page side-by-side viewer for the config shifts.

One card per scene, showing the author's prompt and the intake Q&A, then the same five
picks - genre, shape, preset, route, options - as three arms made them:

    upstream   the Cursor agents' tags that came with the corpus, used as ground truth
    router     three narrow model calls on the prompt plus the answers
    agent      subagents reading the skill files, one shard of scenes each

The renders shown are the agent arm's, because they are the only ones that still match
the configs beside them: the router's images were drawn before its configs were
re-decided against the shared shape catalogue, so pairing them would show a picture of
a decision the page is no longer displaying.

Client-side filters narrow by which pair of arms to compare, by axis, and by genre.

The page is self-contained so it works when opened as a file:// URL, but is
also placed under `results/` so the running web server can serve it at
`/results/config_shifts.html`.

Usage:
    python tools/build_shifts_viewer.py            # writes results/config_shifts.html
    python tools/build_shifts_viewer.py --out foo.html
"""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen.model import rules as br
from layoutgen.model.handoff import GENRE_BY_SLUG
from layoutgen.paths import ROUTING, RESULTS

ANSWERED = ROUTING / "answered"
SKILL = ROUTING / "skill"
AGENT = ROUTING / "agent_spec_gateway"
AGENT_RUN = RESULTS / "runs" / "agent_gateway.jsonl"

#: The picks each arm makes, in the order the panels list them.
AXES = ("genre", "shape", "preset", "route", "options")


def enriched_prompt(source: str, answers: list[dict]) -> str:
    """Build the exact string the router sees: the source prompt with each Q&A
    appended in the author's voice. Kept in sync with the same-named function
    in `tools/reclassify_with_answers.py` - that one produced the answered
    configs, this one shows them back for auditing."""
    if not answers:
        return source
    lines = [source.rstrip(), "", "--- clarifications from the author ---"]
    for a in answers:
        ans = (a.get("answer") or "").strip()
        if not ans:
            continue
        lines.append(f"- [{a.get('field','?')}] "
                     f"{a.get('ask','').rstrip('?')}? {ans}")
    return "\n".join(lines)


def canon_genre(name: str) -> str:
    """An upstream genre slug as the arms spell it.

    An empty tag is the upstream way of writing No Genre, which is a real answer worth
    7% of the corpus rather than a missing one, so it resolves to the name the arms use
    for it. Reading it as "(none)" instead made 18 scenes where every arm correctly said
    No Genre show up as disagreements, and cost the agent arm about three points.
    """
    if not name:
        return br.NO_GENRE_NAME
    return GENRE_BY_SLUG.get(name.lower(), name)


def shape_now(name: str) -> str:
    """A shape id in today's vocabulary.

    The upstream tags were written when shapes were per-genre, and the shared catalogue
    absorbed twelve of them under new names - `arena-flat` is now `space-bounded`. Every
    side goes through this before anything is compared, or the page reports a rename as a
    disagreement on almost every scene and both model-driven arms look far worse than
    they are.
    """
    return br.SHAPE_MIGRATION.get(name or "", name or "")


def agent_configs() -> dict[str, dict]:
    """What the subagents picked, keyed by scene.

    `agent_spec` carries the whole record - the body, the provenance hash, the prompts
    built from it - but a card only shows the picks.
    """
    out: dict[str, dict] = {}
    for p in sorted(AGENT.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("status") != "ok" or not d.get("spec"):
            continue
        s = d["spec"]
        out[d.get("scene") or p.stem] = {
            "genre": s.get("genre", ""),
            "shape": shape_now(s.get("shape") or ""),
            "preset": s.get("preset") or "none",
            "route": " + ".join(s.get("route") or []) or "",
            "options": [o["id"] for o in (s.get("options") or []) if o.get("id")],
            "evidence": d.get("agent_notes", ""),
        }
    return out


def agent_images() -> dict[str, dict[str, str]]:
    """Which stages each scene has, taken from the run record rather than the disk.

    The renders live in the bucket and reach a page through the server, which downloads
    what it does not have locally. A local `is_file` check would therefore find nothing
    and the page would claim every scene failed to render.
    """
    out: dict[str, dict[str, str]] = {}
    if not AGENT_RUN.is_file():
        return out
    for line in AGENT_RUN.open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("status") != "ok":
            continue
        out[r["scene"]] = {k: f"/results/scenes/agent_gateway/{k}/{r['scene']}.png"
                           for k in ("iso", "td", "plan") if r.get(k)}
    return out


def differs(a: dict, b: dict) -> dict:
    """Which of the five picks two arms disagree on.

    An arm that has no config for a scene disagrees about nothing rather than about
    everything: the card says it is absent, and counting an absence as five differences
    would put it at the top of every filter.

    Genre is judged by membership when the other side published more than one tag, which
    upstream does for 86 scenes. A prompt can be honestly read as two genres, and an arm
    that named the second one has not made a mistake to be shown in warning colour.
    """
    if not a or not b:
        return {k: False for k in AXES}
    tags = [t.lower() for t in (b.get("genres") or []) if t]
    mine = (a.get("genre") or "").lower()
    out = {"genre": mine not in tags if tags
           else mine != (b.get("genre") or "").lower()}
    for k in ("shape", "preset", "route"):
        out[k] = (a.get(k) or "").lower() != (b.get(k) or "").lower()
    out["options"] = sorted(a.get("options") or []) != sorted(b.get("options") or [])
    return out


def unescape_nl(s: str) -> str:
    """The eval CSV stored prompts with literal `\\n` sequences rather than real
    newlines, and the routing JSONs preserved them that way. That is fine for
    the router (it saw the same string both times), but shown to a reader the
    prompts run together as a wall of text. Turn the escaped sequences into
    actual newlines for the viewer only."""
    return s.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "    ")


def collect() -> list[dict]:
    rows: list[dict] = []
    agents, images = agent_configs(), agent_images()
    for p in sorted(ANSWERED.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        cfg = d.get("config") or {}
        up = d.get("upstream_skill") or {}

        # Pull the upstream option ids and the Q&A from the sibling skill file.
        skill = {}
        skill_path = SKILL / f"{d['scene']}.json"
        if skill_path.exists():
            skill = json.loads(skill_path.read_text(encoding="utf-8"))
        block = skill.get("block") or {}
        up_opts: list[str] = []
        for e in (block.get("image_prompt") or []):
            oid = e.get("id")
            if oid and oid not in up_opts:
                up_opts.append(oid)
        for e in (block.get("layout_placement") or []):
            oid = e.get("id")
            if oid and oid not in up_opts:
                up_opts.append(oid)

        scene = d["scene"]
        up_tags = [canon_genre(g) for g in (up.get("genres") or [])] or [canon_genre("")]
        panels = {
            "up": {
                # Every tag is shown, and every tag counts as a correct answer.
                "genre": " / ".join(up_tags),
                "genres": up_tags,
                "shape": shape_now(up.get("shape") or ""),
                "preset": up.get("preset") or "none",
                "route": " + ".join(up.get("pipeline") or []) or "",
                "options": up_opts,
            },
            "ro": {
                "genre": cfg.get("genre", ""),
                "shape": shape_now(cfg.get("shape") or ""),
                "preset": cfg.get("preset") or "none",
                "route": " + ".join(cfg.get("route") or []) or "",
                "options": cfg.get("options") or [],
                "confidence": cfg.get("confidence", ""),
                "evidence": cfg.get("evidence", ""),
            },
            "ag": agents.get(scene) or {},
        }
        pairs = {"ru": differs(panels["ro"], panels["up"]),
                 "au": differs(panels["ag"], panels["up"]),
                 "ar": differs(panels["ag"], panels["ro"])}
        rows.append({
            "scene": scene,
            "prompt": d.get("source", ""),
            "theme_up": skill.get("theme") or "",
            "scale_up": (skill.get("scale") or {}).get("band") or "",
            "panels": panels,
            "answers": d.get("answers") or [],
            "pairs": pairs,
            # The badge counts the agent arm against upstream: it is the arm being
            # examined, and the filters default to the same comparison.
            "touched": sum(pairs["au"].values()),
            "images": images.get(scene, {}),
        })
    return rows


CSS = """
:root{--bg:#0d1117;--pan:#141b23;--pan2:#0b0f14;--ln:#253040;--fg:#e6edf3;
  --dim:#9fb0c3;--dim2:#6f8296;--ok:#3fb950;--acc:#58a6ff;--bad:#f85149;
  --warn:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:13px/1.55 ui-sans-serif,-apple-system,Segoe UI,Roboto,sans-serif}
header{padding:12px 18px;border-bottom:1px solid var(--ln);position:sticky;top:0;
  background:var(--bg);z-index:9}
header h1{margin:0;font-size:14px;display:inline}
header .sub{color:var(--dim);font-size:12px;margin-left:10px}
header .nav{display:inline-flex;gap:8px;margin-left:14px}
header .nav a{color:var(--acc);text-decoration:none;padding:2px 8px;border-radius:5px;
  border:1px solid var(--ln);background:var(--pan);font-size:11.5px}
header .nav a.active{border-color:var(--acc);background:var(--pan2)}
header .filters{margin-top:8px;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
header select,header input[type=text]{background:var(--pan);color:var(--fg);
  border:1px solid var(--ln);border-radius:6px;padding:4px 8px;font-size:11.5px}
header input[type=text]{width:220px}
header .count{color:var(--dim);font-size:11.5px;margin-left:auto}
.main{padding:12px 18px 40px;max-width:1440px}
.card{background:var(--pan);border:1px solid var(--ln);border-radius:10px;
  padding:12px 14px;margin-bottom:10px}
.card h2{margin:0 0 4px;font-size:14px;display:flex;gap:10px;align-items:baseline}
.card h2 .id{color:var(--acc);font-weight:600}
.card h2 .badge{font-size:11px;color:var(--dim);border:1px solid var(--ln);
  border-radius:999px;padding:0 8px}
.card h2 .badge.hot{color:var(--warn);border-color:#5c4a12}
.card h2 .badge.same{color:var(--ok);border-color:#1f5c2b}
.card .prompt{color:var(--dim);font-size:11.5px;margin:0 0 8px;
  white-space:pre-wrap;max-height:4.5em;overflow:hidden;text-overflow:ellipsis;
  cursor:pointer}
.card .prompt.open{max-height:none;overflow:visible}
.input-block{background:var(--pan2);border:1px solid var(--ln);
  border-left:3px solid var(--acc);border-radius:8px;padding:9px 11px;
  margin-bottom:10px}
.input-block h3{margin:0 0 6px;font-size:11px;letter-spacing:.05em;
  text-transform:uppercase;color:var(--acc);font-weight:600}
.input-block .lbl{color:var(--dim2);font-size:10.5px;text-transform:uppercase;
  letter-spacing:.05em;margin:6px 0 4px}
.input-block .src{color:var(--fg);font-size:11.5px;white-space:pre-wrap;
  max-height:4.5em;overflow:hidden;cursor:pointer}
.input-block .src.open{max-height:none;overflow:visible}
.input-block .noqa{color:var(--dim2);font-size:11px;font-style:italic}
.qa-list{margin:0}
.qa-list .qi{padding:6px 0;border-top:1px dashed var(--ln)}
.qa-list .qi:first-child{border-top:none;padding-top:2px}
.qa-list .qi .field{color:var(--acc);
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:10.5px;margin-right:6px;background:#101a2a;
  border:1px solid #2f4a7a;border-radius:4px;padding:1px 5px}
.qa-list .qi .q{color:var(--fg);font-size:11.5px}
.qa-list .qi .a{color:var(--dim);font-size:11.5px;margin-top:3px;
  padding-left:14px;border-left:2px solid #2f4a7a}
.qa-list .qi .a::before{content:"answer  ";color:var(--dim2);
  font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;margin-right:6px}
.router-input{margin-top:8px}
.router-input summary{cursor:pointer;color:var(--dim);font-size:11px;
  padding:2px 0;outline:none}
.router-input summary::marker{color:var(--dim2)}
.router-input pre{margin:6px 0 0;background:#080b10;border:1px solid var(--ln);
  border-radius:6px;padding:8px 10px;font-size:11px;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--fg);
  white-space:pre-wrap;max-height:340px;overflow:auto}
.trio{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
@media (max-width:1100px){.trio{grid-template-columns:1fr}}
.side{background:#0b0f14;border:1px solid var(--ln);border-radius:8px;padding:8px 10px}
.side h3{margin:0 0 6px;font-size:11px;letter-spacing:.05em;text-transform:uppercase;
  color:var(--dim);font-weight:600}
.row{display:grid;grid-template-columns:64px 1fr;gap:8px;font-size:12px;padding:2px 0}
.row .k{color:var(--dim2)}
.row .v{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.5px;
  word-break:break-word}
.row.diff .v{color:var(--warn)}
.row.diff .k{color:var(--warn)}
.opts{margin-top:6px;font-size:11.5px}
.opts .chip{display:inline-block;border:1px solid var(--ln);border-radius:4px;
  padding:1px 6px;margin:2px 3px 0 0;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10.5px;
  color:var(--dim)}
.opts .chip.add{color:var(--ok);border-color:#1f5c2b}
.opts .chip.rem{color:var(--bad);border-color:#6e2b28;text-decoration:line-through}
.qa{margin-top:10px;border-top:1px dashed var(--ln);padding-top:8px}
.qa .qi{margin-bottom:5px;font-size:11.5px}
.qa .qi .field{color:var(--acc);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:10.5px;margin-right:6px}
.qa .qi .q{color:var(--fg)}
.qa .qi .a{color:var(--dim);margin-top:2px;padding-left:14px}
.evidence{color:var(--dim);font-size:11px;margin-top:6px;font-style:italic}
.renders{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:8px;margin:0 0 10px}
.renders .tile{background:var(--pan2);border:1px solid var(--ln);border-radius:8px;
  padding:6px;text-align:center}
.renders .tile .cap{color:var(--dim2);font-size:10px;letter-spacing:.08em;
  text-transform:uppercase;margin-bottom:4px}
.renders .tile img{width:100%;height:auto;border-radius:4px;display:block;
  background:#000;cursor:zoom-in}
.renders.none{color:var(--dim2);font-size:11px;font-style:italic;
  border:1px dashed var(--ln);border-radius:8px;padding:8px;display:block;
  text-align:center}
.lightbox{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;
  align-items:center;justify-content:center;z-index:99;cursor:zoom-out;padding:20px}
.lightbox.open{display:flex}
.lightbox img{max-width:96vw;max-height:96vh;object-fit:contain}
"""


def field_row(label: str, value: str, diff: bool) -> str:
    """One row inside a config panel: just the label and the value on this side.
    `diff` marks the answered-side value that changed from the upstream side, so
    the eye can find where the reclassification moved."""
    cls = "row diff" if diff else "row"
    return (f'<div class="{cls}"><span class="k">{label}</span>'
            f'<span class="v">{html.escape(value or "(none)")}</span></div>')


def option_chips(picks: list[str], baseline: list[str], mark: bool) -> str:
    """Chips for one arm's option ids.

    `mark` compares them against the upstream picks, so an arm's panel shows in green
    what it added and struck through what it let go. The upstream panel passes False and
    lists its own picks plainly, having nothing to be compared against.
    """
    base, chosen = set(baseline), set(picks)
    chips = [f'<span class="chip{" add" if mark and o not in base else ""}">'
             f'{html.escape(o)}</span>' for o in picks]
    if mark:
        chips += [f'<span class="chip rem">{html.escape(o)}</span>'
                  for o in baseline if o not in chosen]
    return "".join(chips) or '<span class="chip">(none)</span>'


def panel(title: str, note: str, p: dict, marks: dict, baseline: list[str],
          mark_opts: bool) -> str:
    """One arm's column."""
    if not p:
        return (f'<div class="side"><h3>{html.escape(title)}</h3>'
                '<div class="evidence">this arm has no config for this scene</div></div>')
    rows = "".join(field_row(k, p.get(k, ""), marks.get(k, False))
                   for k in ("genre", "shape", "preset", "route"))
    opts = p.get("options") or []
    ev = ""
    if p.get("evidence"):
        conf = f' ({p["confidence"]})' if p.get("confidence") else ""
        ev = (f'<div class="evidence">{html.escape(note or "why")}{conf}: '
              f'{html.escape(p["evidence"][:400])}</div>')
    return (f'<div class="side"><h3>{html.escape(title)}</h3>{rows}'
            f'<div class="opts"><span class="k" style="color:var(--dim2)">'
            f'options ({len(opts)})</span><br>'
            f'{option_chips(opts, baseline, mark_opts)}</div>{ev}</div>')


def render_card(r: dict) -> str:
    scene = r["scene"]
    up, ro, ag = r["panels"]["up"], r["panels"]["ro"], r["panels"]["ag"]
    au, ru, ar = r["pairs"]["au"], r["pairs"]["ru"], r["pairs"]["ar"]
    n = r["touched"]
    badge_cls = "same" if n == 0 else ("hot" if n >= 3 else "")
    badge = ("agrees with upstream" if n == 0
             else f"{n} axes differ from upstream")
    prompt_txt = html.escape(unescape_nl(r["prompt"].strip()))

    qa_items_html = ""
    if r["answers"]:
        qs = []
        for a in r["answers"]:
            qs.append(
                f'<div class="qi">'
                f'<span class="field">[{html.escape(a.get("field","?"))}]</span>'
                f'<span class="q">{html.escape(a.get("ask",""))}</span>'
                f'<div class="a">{html.escape(a.get("answer","") or "(empty)")}</div>'
                f'</div>')
        qa_items_html = '<div class="qa-list">' + "".join(qs) + "</div>"
    else:
        qa_items_html = ('<div class="noqa">no open questions on this scene '
                         '&mdash; the router saw the prompt alone</div>')

    full_input = unescape_nl(enriched_prompt(r["prompt"], r["answers"]))
    router_input_html = (
        '<details class="router-input">'
        '<summary>full text sent to the router (prompt + clarifications)</summary>'
        f'<pre>{html.escape(full_input)}</pre>'
        '</details>')

    input_block = f"""
  <div class="input-block">
    <h3>Input that produced the answered config</h3>
    <div class="lbl">source prompt</div>
    <div class="src" onclick="this.classList.toggle('open')">{prompt_txt}</div>
    <div class="lbl">questions the intake asked, and the author's answers ({len(r['answers'])})</div>
    {qa_items_html}
    {router_input_html}
  </div>"""

    tiles = []
    for kind in ("iso", "td", "plan"):
        src = r["images"].get(kind)
        if not src:
            continue
        cap = {"iso": "isometric", "td": "top-down",
               "plan": "authored plan"}[kind]
        tiles.append(
            f'<div class="tile">'
            f'<div class="cap">{cap}</div>'
            f'<img loading="lazy" data-full="{src}" '
            f'src="{src}" alt="{scene} {kind}"></div>')
    if tiles:
        renders_html = f'<div class="renders">{"".join(tiles)}</div>'
    else:
        renders_html = ('<div class="renders none">the agent arm has no render for '
                        'this scene</div>')

    data = [f'data-scene="{scene}"',
            f'data-genre-ag="{html.escape(ag.get("genre", ""))}"',
            f'data-genre-ro="{html.escape(ro.get("genre", ""))}"',
            f'data-has-ag="{int(bool(ag))}"']
    for pref, marks in (("au", au), ("ru", ru), ("ar", ar)):
        data.append(f'data-touched-{pref}="{sum(marks.values())}"')
        data += [f'data-{pref}-{k}="{int(marks.get(k, False))}"' for k in AXES]

    return f"""
<div class="card" {' '.join(data)}>
  <h2>
    <span class="id">{scene}</span>
    <span class="badge {badge_cls}">{badge}</span>
    <span class="badge">{html.escape(ag.get('genre') or ro.get('genre', ''))}</span>
  </h2>
  {input_block}
  {renders_html}
  <div class="trio">
    {panel("Upstream tags (ground truth)", "", up, {}, up["options"], False)}
    {panel("Router (three narrow calls)", "evidence", ro, ru, up["options"], True)}
    {panel("Agent (subagents on the skills)", "notes", ag, au, up["options"], True)}
  </div>
</div>
"""


JS = """
const cards=[...document.querySelectorAll('.card')];
const filt=id=>document.getElementById(id);
const lb=document.getElementById('lightbox');
const lbImg=lb.querySelector('img');
document.addEventListener('click',e=>{
  const t=e.target;
  if(t && t.tagName==='IMG' && t.dataset.full){
    lbImg.src=t.dataset.full;
    lb.classList.add('open');
  } else if (t===lb || t.tagName==='IMG' && t.parentElement===lb){
    lb.classList.remove('open');
    lbImg.src='';
  }
});
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){lb.classList.remove('open');lbImg.src='';}
});
function apply(){
  const only=filt('only').value;
  const axis=filt('axis').value;
  const g=filt('genre').value;
  const vs=filt('vs').value;                       // au | ru | ar
  const q=(filt('q').value||'').toLowerCase().trim();
  // The pair being compared drives both the count and the axis test, so the two can
  // never disagree about which arms the reader is looking at.
  const key=s=>vs+s[0].toUpperCase()+s.slice(1);
  let shown=0;
  for(const c of cards){
    const t=+c.dataset['touched'+vs[0].toUpperCase()+vs[1]];
    let ok=true;
    if(only==='shifted' && t===0) ok=false;
    if(only==='unchanged' && t!==0) ok=false;
    if(only==='hot' && t<3) ok=false;
    if(axis!=='any' && c.dataset[key(axis)] !== '1') ok=false;
    if(g && c.dataset.genreAg !== g) ok=false;
    if(q){
      const s=c.dataset.scene.toLowerCase();
      const src=c.querySelector('.src');
      const pt=(src?src.textContent:'').toLowerCase();
      // Also match anywhere in the card so a search for an ask, answer, or
      // option id like 'safezone-town' finds the scenes that used it.
      const rest=c.textContent.toLowerCase();
      if(!s.includes(q) && !pt.includes(q) && !rest.includes(q)) ok=false;
    }
    c.style.display=ok?'':'none';
    if(ok) shown++;
  }
  filt('count').textContent=`${shown} of ${cards.length}`;
}
['only','axis','genre','vs'].forEach(id=>filt(id).addEventListener('change',apply));
filt('q').addEventListener('input',apply);
apply();
"""


def build_page(rows: list[dict]) -> str:
    genres = sorted({r["panels"]["ag"].get("genre") for r in rows
                     if r["panels"]["ag"].get("genre")})
    genre_opts = "\n".join(
        f'<option value="{html.escape(g)}">{html.escape(g)}</option>' for g in genres)
    cards = "\n".join(render_card(r) for r in rows)
    n = len(rows)
    have = sum(1 for r in rows if r["panels"]["ag"])
    agree = sum(1 for r in rows if r["panels"]["ag"] and r["touched"] == 0)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Config shifts</title>
<style>{CSS}</style></head>
<body>
<header>
  <h1>Config shifts</h1>
  <span class="sub">{n} scenes &middot; {have} decided by the agent arm &middot;
    {agree} of those agree with upstream on all five picks</span>
  <span class="nav">
    <a class="active" href="/">Config shifts</a>
    <a href="/pipeline">Pipeline (per-scene)</a>
    <a href="/pipeline/reference">Reference (upstream)</a>
  </span>
  <div class="filters">
    <label>compare
      <select id="vs">
        <option value="au" selected>agent vs upstream</option>
        <option value="ru">router vs upstream</option>
        <option value="ar">agent vs router</option>
      </select>
    </label>
    <label>show
      <select id="only">
        <option value="all">all</option>
        <option value="shifted" selected>differs on \u22651 axis</option>
        <option value="hot">differs on \u22653 axes</option>
        <option value="unchanged">agrees on all five</option>
      </select>
    </label>
    <label>axis
      <select id="axis">
        <option value="any">any</option>
        <option>genre</option>
        <option>shape</option>
        <option>preset</option>
        <option>route</option>
        <option>options</option>
      </select>
    </label>
    <label>agent genre
      <select id="genre"><option value="">any</option>{genre_opts}</select>
    </label>
    <input id="q" type="text" placeholder="scene id or prompt substring" />
    <span class="count" id="count"></span>
  </div>
</header>
<main class="main">
{cards}
</main>
<div id="lightbox" class="lightbox"><img alt="" /></div>
<script>{JS}</script>
</body></html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path,
                    default=RESULTS / "config_shifts.html")
    args = ap.parse_args()
    rows = collect()
    text = build_page(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    kb = len(text) // 1024
    print(f"wrote {args.out}  ({len(rows)} scenes, {kb} KB)")
    print(f"served at http://localhost:8887/results/{args.out.name} "
          f"or file://{args.out.resolve()}")


if __name__ == "__main__":
    main()
