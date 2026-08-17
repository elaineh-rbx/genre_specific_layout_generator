"""Build a side-by-side Azure GPT Image 2 versus Gateway Gemini viewer."""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from layoutgen.paths import RESULTS  # noqa: E402
from layoutgen.optimize.gepa_images import _candidate_id, load_cases  # noqa: E402
from build_pipeline_viewer import collect  # noqa: E402


CSS = """
:root{--bg:#0d1018;--panel:#151a25;--panel2:#1b2230;--line:#2b3446;
--text:#edf0f6;--muted:#9ba6b8;--azure:#7aa2ff;--gemini:#52c995}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:14px/1.5 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:5;background:rgba(13,16,24,.96);
border-bottom:1px solid var(--line);padding:14px 24px}.head{max-width:1700px;margin:auto;
display:flex;gap:18px;align-items:center}h1{font-size:20px;margin:0}.sub{font-size:12px;
color:var(--muted)}.nav{display:flex;gap:7px;margin-top:7px}.nav a{color:var(--muted);
text-decoration:none;border:1px solid var(--line);border-radius:7px;padding:3px 8px;
font-size:11px}.nav a.active{color:var(--gemini);border-color:var(--gemini)}
.controls{margin-left:auto;display:flex;gap:9px}select,input{background:var(--panel2);
color:var(--text);border:1px solid var(--line);border-radius:8px;padding:9px 11px;
min-width:220px}main{max-width:1700px;margin:auto;padding:20px 24px 60px}.meta{
display:flex;gap:7px;flex-wrap:wrap;margin-bottom:12px}.chip{border:1px solid var(--line);
background:var(--panel);border-radius:999px;padding:4px 10px;color:var(--muted);
font-size:12px}.chip strong{color:var(--text)}.prompt{background:var(--panel);
border:1px solid var(--line);border-radius:11px;padding:13px;white-space:pre-wrap;
margin-bottom:16px}.view{margin-bottom:17px}.view>h2{font-size:14px;margin:0 0 8px;
text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}.pair{display:grid;
grid-template-columns:1fr 1fr;gap:14px}.pane{background:var(--panel);
border:1px solid var(--line);border-radius:12px;padding:12px}.pane h3{font-size:14px;
margin:0 0 8px;display:flex;justify-content:space-between}.pane h3 span{font-size:10px;
font-weight:400;color:var(--muted)}.azure h3{color:var(--azure)}.gemini h3{color:var(--gemini)}
.pane img{display:block;width:100%;aspect-ratio:1;object-fit:contain;background:#080a10;
border:1px solid var(--line);border-radius:8px;cursor:zoom-in}.prompts{display:grid;
grid-template-columns:1fr 1fr;gap:12px;margin-top:10px}.prompts details{background:var(--panel);
border:1px solid var(--line);border-radius:9px;padding:9px}.prompts summary{cursor:pointer;
color:var(--muted);font-size:11px}.prompts pre{white-space:pre-wrap;overflow-wrap:anywhere;
font:10px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace;max-height:300px;
overflow:auto}.lightbox{display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);
z-index:20;align-items:center;justify-content:center;padding:20px}.lightbox.open{display:flex}
.lightbox img{max-width:96vw;max-height:96vh;object-fit:contain}
@media(max-width:900px){.head{flex-direction:column;align-items:flex-start}.controls{
margin:0;width:100%;flex-wrap:wrap}.controls>*{min-width:0;flex:1}.pair,.prompts{
grid-template-columns:1fr}}
"""


BODY = """
<header><div class="head">
  <div><h1>Golden image-model comparison</h1>
    <div class="sub">Same 75 scene specs and render orders; each backend uses its production prompt profile.</div>
    <nav class="nav"><a href="/features">Original viewer</a><a href="/pipeline">Pipeline</a>
      <a class="active" href="/comparison">GPT Image 2 vs Gemini</a></nav>
  </div>
  <div class="controls"><select id="genre"><option value="">All genres</option></select>
    <input id="search" placeholder="Filter scene, genre, shape…"><select id="picker"></select></div>
</div></header>
<main>
  <div class="meta" id="meta"></div>
  <div class="prompt" id="prompt"></div>
  <section class="view"><h2>Isometric</h2><div class="pair">
    <div class="pane azure"><h3>Azure GPT Image 2 <span>gpt-image-2</span></h3><img id="azureIso"></div>
    <div class="pane gemini"><h3>__GEMINI_LABEL__ <span>__GEMINI_SUB__</span></h3><img id="geminiIso"></div>
  </div></section>
  <section class="view"><h2>Top-down</h2><div class="pair">
    <div class="pane azure"><h3>Azure GPT Image 2 <span>gpt-image-2</span></h3><img id="azureTd"></div>
    <div class="pane gemini"><h3>__GEMINI_LABEL__ <span>__GEMINI_SUB__</span></h3><img id="geminiTd"></div>
  </div></section>
  <div class="prompts">
    <details><summary>Azure · exact isometric prompt</summary><pre id="azureIsoPrompt"></pre></details>
    <details><summary>Gemini · exact isometric prompt</summary><pre id="geminiIsoPrompt"></pre></details>
    <details><summary>Azure · exact top-down prompt</summary><pre id="azureTdPrompt"></pre></details>
    <details><summary>Gemini · exact top-down prompt</summary><pre id="geminiTdPrompt"></pre></details>
  </div>
</main>
<div class="lightbox" id="lightbox"><img></div>
"""


JS = r"""
const SCENES=__SCENES__, $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",
'"':"&quot;","'":"&#39;"}[c]));
const picker=$("picker"),search=$("search"),genre=$("genre");
const genres=[...new Set(SCENES.map(s=>s.genre||"No Genre"))].sort((a,b)=>a.localeCompare(b));
genre.innerHTML+=genres.map(g=>`<option value="${esc(g)}">${esc(g)}</option>`).join("");
function choices(){const q=search.value.trim().toLowerCase(),wanted=genre.value,cur=picker.value;
 const rows=SCENES.filter(s=>(!wanted||(s.genre||"No Genre")===wanted)&&
 (!q||[s.id,s.genre,s.shape,s.preset,s.prompt].some(v=>String(v||"").toLowerCase().includes(q))));
 picker.innerHTML=rows.map(s=>`<option value="${s.id}">${s.id} · ${esc(s.genre||"No Genre")} · ${esc(s.shape||"described")}</option>`).join("");
 if(rows.length){picker.value=rows.some(s=>s.id===cur)?cur:rows[0].id;render(picker.value)}}
function image(id,src){const el=$(id);el.src=src;el.dataset.full=src}
function render(id){const s=SCENES.find(x=>x.id===id);if(!s)return;
 $("meta").innerHTML=[["Scene",s.id],["Genre",s.genre||"No Genre"],["Shape",s.shape||"described"],
 ["Preset",s.preset||"none"],["Order",s.order||"—"]].map(([k,v])=>
 `<span class="chip"><strong>${esc(k)}:</strong> ${esc(v)}</span>`).join("");
 $("prompt").textContent=s.prompt||"";
 image("azureIso",s.azure.iso);image("azureTd",s.azure.td);
 image("geminiIso",s.gemini.iso);image("geminiTd",s.gemini.td);
 $("azureIsoPrompt").textContent=s.prompts.azure.iso||"";
 $("geminiIsoPrompt").textContent=s.prompts.gemini.iso||"";
 $("azureTdPrompt").textContent=s.prompts.azure.td||"";
 $("geminiTdPrompt").textContent=s.prompts.gemini.td||""}
search.addEventListener("input",choices);genre.addEventListener("change",choices);
picker.addEventListener("change",()=>render(picker.value));
document.addEventListener("keydown",e=>{if(!["ArrowLeft","ArrowRight"].includes(e.key))return;
 const n=picker.selectedIndex+(e.key==="ArrowRight"?1:-1);
 if(n>=0&&n<picker.options.length){picker.selectedIndex=n;render(picker.value)}});
const lb=$("lightbox"),li=lb.querySelector("img");document.addEventListener("click",e=>{
 if(e.target.matches(".pane img")){li.src=e.target.dataset.full;lb.classList.add("open")}
 else if(e.target===lb||e.target===li){lb.classList.remove("open");li.src=""}});choices();
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--azure-run",
        default="agent_gateway_gpt55_golden75_direct_enriched_260814",
    )
    parser.add_argument(
        "--azure-arm",
        default="agent_gateway_gpt55_golden75_direct_enriched_260814",
    )
    parser.add_argument(
        "--gemini-run",
        default=(
            "agent_gateway_gpt55_golden75_direct_enriched_"
            "gemini31_promptfix3_260814"
        ),
    )
    parser.add_argument(
        "--gemini-arm",
        default=(
            "agent_gateway_gpt55_golden75_direct_enriched_"
            "gemini31_promptfix3_260814"
        ),
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=RESULTS / "comparison_viewer_gpt55_golden75.html",
    )
    parser.add_argument(
        "--gepa-root",
        type=pathlib.Path,
        help="completed GEPA run root; uses its best candidate instead of --gemini-run",
    )
    parser.add_argument(
        "--gepa-arm",
        default="agent_gpt52_upstream_cf94b18_gemini31_gepa_260816",
        help="results/scenes arm populated from --gepa-root",
    )
    args = parser.parse_args()

    azure = {r["id"]: r for r in collect(args.azure_run, args.azure_arm, only_sent=True)}
    gemini = (
        _gepa_rows(args.gepa_root, args.gepa_arm, azure)
        if args.gepa_root
        else {r["id"]: r for r in collect(
            args.gemini_run, args.gemini_arm, only_sent=True
        )}
    )
    if set(azure) != set(gemini):
        raise ValueError(
            f"run scene mismatch: Azure={len(azure)}, Gemini={len(gemini)}"
        )
    rows = []
    for scene in sorted(azure):
        row = dict(gemini[scene])
        azure_row = azure[scene]
        row["azure"] = azure_row["images"]
        row["gemini"] = row["images"]
        row["prompts"] = {
            "azure": {
                "iso": azure_row.get("iso_prompt", ""),
                "td": azure_row.get("td_prompt", ""),
            },
            "gemini": {
                "iso": row.get("iso_prompt", ""),
                "td": row.get("td_prompt", ""),
            },
        }
        row.pop("images", None)
        row.pop("iso_prompt", None)
        row.pop("td_prompt", None)
        row.pop("checklist", None)
        rows.append(row)

    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    page = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>Azure vs Gemini golden comparison</title><style>{CSS}</style></head>"
        f"<body>{BODY.replace(
            '__GEMINI_LABEL__',
            'GEPA-optimized Gemini' if args.gepa_root else 'LLM Gateway Gemini',
        ).replace(
            '__GEMINI_SUB__',
            'gemini-3.1-flash-image · GEPA best' if args.gepa_root
            else 'gemini-3.1-flash-image',
        )}<script>{JS.replace('__SCENES__', data)}</script></body></html>\n"
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".part")
    temporary.write_text(page, encoding="utf-8")
    temporary.replace(args.out)
    print(f"wrote {args.out} ({len(rows)} scenes, {len(page)//1024} KB)")


def _gepa_rows(
    root: pathlib.Path,
    arm: str,
    azure: dict[str, dict],
) -> dict[str, dict]:
    candidate_path = root / "best_candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    cases = load_cases()
    destination = RESULTS / "scenes" / arm
    rows: dict[str, dict] = {}
    for scene, azure_row in azure.items():
        case = cases[scene]
        source = root / "renders" / _candidate_id(candidate, case) / scene
        prompt_record = json.loads(
            (source / "prompts.json").read_text(encoding="utf-8")
        )
        images = {}
        for stage, filename in (("iso", "iso.jpg"), ("td", "td.jpg")):
            source_image = source / filename
            if not source_image.is_file():
                raise FileNotFoundError(f"missing GEPA image {source_image}")
            target = destination / stage / f"{scene}.jpg"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_image, target)
            images[stage] = f"/results/scenes/{arm}/{stage}/{scene}.jpg"
        row = dict(azure_row)
        row["images"] = images
        row["iso_prompt"] = prompt_record.get("iso_prompt", "")
        row["td_prompt"] = prompt_record.get("first_prompt", "")
        rows[scene] = row
    return rows


if __name__ == "__main__":
    main()
