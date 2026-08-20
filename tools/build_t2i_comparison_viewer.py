"""Build a shareable side-by-side viewer for a ``t2i_batch.py`` result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from layoutgen.pipeline import prompts as pipeline_prompts

REPO = Path(__file__).resolve().parent.parent
GEMINI_GEPA = REPO / "run" / "gepa" / "gemini_gepa_all75_v1_260816"
GEMINI_ORIGINAL_RUN = (
    "agent_gateway_gpt55_golden75_direct_enriched_gemini31_260814"
)
GEMINI_ORIGINAL_PROMPTS = (
    REPO / "results" / "runs" / f"{GEMINI_ORIGINAL_RUN}_prompts.jsonl"
)
GEMINI_JUDGE_GEPA = (
    REPO / "run" / "gepa" / "gemini_gepa_vlm_gpt55_all75_eval_v1_260817"
)
GEMINI_CAMERA_GEPA = (
    REPO / "run" / "gepa" / "gemini_gepa_vlm_similarity_iso_all75_eval_v2_260818"
)
GEMINI_600_GEPA_ROOT = (
    REPO
    / "results"
    / "gepa"
    / "gemini_gepa_upstream600_golden75_full_v1_260819"
)
GEMINI_600_GEPA_CANDIDATE = (
    REPO
    / "run"
    / "gepa"
    / "gemini_gepa_upstream600_golden75_full_v1_260819"
    / "best_candidate.json"
)
GEMINI_600_NO_RECAPTION_GEPA_CANDIDATE = (
    REPO
    / "run"
    / "gepa"
    / "gemini_gepa_upstream600_golden75_no_recaption_full_v1_260819"
    / "best_candidate.json"
)
GEMINI_CAPTION_ROOT = (
    REPO / "results" / "t2i" / "golden75_gemini_caption_summary_260818"
)
GEMINI_CAPTION_GEPA_ROOT = (
    REPO / "results" / "gepa" / "gemini_caption_gepa_all75_v1_260818"
)
GEMINI_RECAPTION_ROOT = (
    REPO / "results" / "t2i" / "gemini_recaption_pilot10_260818"
)
GEMINI_GPTPROMPT_RECAPTION_GEPA_ROOT = (
    REPO
    / "results"
    / "gepa"
    / "gemini_gptprompt_recaption_gepa_std45_v1_260818"
)
GEMINI_CONTRACT_REPAIR_ROOT = (
    REPO / "results" / "t2i" / "gemini_contract_repair_pilot9_260818"
)
FLUX_SIM_GEPA = REPO / "run" / "gepa" / "flux_gepa_iso_all75_v1_260817"
FLUX_JUDGE_GEPA = (
    REPO / "run" / "gepa" / "flux_gepa_vlm_gpt55_all75_eval_v1_260817"
)
ZIMAGE_SIM_GEPA = REPO / "run" / "gepa" / "zimage_gepa_iso_std45_v1_260817"
ZIMAGE_JUDGE_GEPA = (
    REPO / "run" / "gepa" / "zimage_gepa_vlm_gpt55_std45_v1_260817"
)
QWEN_SIM_GEPA = REPO / "run" / "gepa" / "qwen_pipeline_gepa_iso_all75_v1_260817"
QWEN_JUDGE_GEPA = (
    REPO / "run" / "gepa" / "qwen_pipeline_gepa_vlm_gpt55_all75_eval_v1_260817"
)
DEFAULT_RUN = "golden75_initial_gpt_prompts_all3_260817"
DEFAULT_ROOT = REPO / "results" / "t2i" / DEFAULT_RUN
DEFAULT_SOURCE_MANIFEST = (
    REPO
    / "results"
    / "runs"
    / "agent_gpt52_upstream_cf94b18_gptimage2_260815_manifest.json"
)
DEFAULT_FLUX_SECOND_RUN = "golden75_second_stage_iso_flux_260817"
DEFAULT_FLUX_SECOND_ROOT = REPO / "results" / "t2i" / DEFAULT_FLUX_SECOND_RUN
DEFAULT_QWEN_SECOND_RUN = "golden75_second_stage_iso_qwen_pipeline_260817"
DEFAULT_QWEN_SECOND_ROOT = REPO / "results" / "t2i" / DEFAULT_QWEN_SECOND_RUN
DEFAULT_OUTPUT = REPO / "results" / "t2i_comparison_viewer.html"

MODELS = (
    (
        "gpt-image-2",
        "Original",
        "golden render",
        "baseline",
        "raw",
        "GPT Image 2",
        "Reference target; no GEPA policy.",
    ),
    (
        "gemini-3.1-flash-image",
        "Original",
        "initial untuned policy",
        "gemini-original",
        "gemini-original",
        "Gemini 3.1 Flash Image",
        "Initial policy; no optimization.",
    ),
    (
        "gemini-3.1-flash-image",
        "Caption Distillation",
        "blind GPT-target caption",
        "gemini-caption",
        "caption",
        "Gemini 3.1 Flash Image",
        "Target-derived caption used as the complete prompt; diagnostic, not a fair benchmark.",
    ),
    (
        "gemini-3.1-flash-image",
        "Caption GEPA",
        "held-out global template",
        "gemini-caption-gepa",
        "caption-gepa",
        "Gemini 3.1 Flash Image",
        "GEPA-optimized global template around each immutable target-derived caption.",
    ),
    (
        "gemini-3.1-flash-image",
        "Iterative Recaption",
        "three-step · 10-scene pilot",
        "gemini-recaption",
        "recaption",
        "Gemini 3.1 Flash Image",
        "Per-scene caption hill climb using target/candidate visual feedback.",
    ),
    (
        "gemini-3.1-flash-image",
        "GPT Prompt + Recaption GEPA",
        "held-out global adapter · 45 scenes",
        "gemini-gptprompt-recaption-gepa",
        "gptprompt-recaption-gepa",
        "Gemini 3.1 Flash Image",
        "Exact GPT prompt plus a global adapter learned from candidate recaptions.",
    ),
    (
        "gemini-3.1-flash-image",
        "Contract Repair",
        "two retries · 9-scene pilot",
        "gemini-contract-repair",
        "contract-repair",
        "Gemini 3.1 Flash Image",
        "Recaption-to-contract repair selected without target similarity.",
    ),
    (
        "gemini-3.1-flash-image",
        "Similarity GEPA",
        "Gemini 3.1 Flash Image · all-75 winner",
        "gepa",
        "gepa",
        "Gemini 3.1 Flash Image",
        "45° camera, richer detail, perimeter and fuller canvas.",
    ),
    (
        "gemini-3.1-flash-image",
        "Prompt/Layout GEPA (75)",
        "golden-75 pilot · GPT-5.5 judged",
        "gemini-judge-gepa",
        "gemini-judge-gepa",
        "Gemini 3.1 Flash Image",
        "Countable structures, strict placement and visibility-first framing.",
    ),
    (
        "gemini-3.1-flash-image",
        "Prompt/Layout + Recaption (600)",
        "completed · 600 train · golden-75 validation",
        "gemini-600-gepa",
        "gemini-600-gepa",
        "Gemini 3.1 Flash Image",
        "Candidate recaptions guided reflection but were not part of the score.",
    ),
    (
        "gemini-3.1-flash-image",
        "Prompt/Layout GEPA (600, No Recaption)",
        "completed · 600 train · golden-75 validation",
        "gemini-600-no-recaption-gepa",
        "gemini-600-no-recaption-gepa",
        "Gemini 3.1 Flash Image",
        "Clean ablation with candidate recaptioning completely disabled.",
    ),
    (
        "gemini-3.1-flash-image",
        "Balanced Camera GEPA",
        "VLM + GPT Image 2 + camera gate",
        "gemini-camera-gepa",
        "gemini-camera-gepa",
        "Gemini 3.1 Flash Image",
        "True isometric angle, prompt/layout fidelity and GPT Image 2 similarity.",
    ),
    (
        "qwen-image",
        "Original",
        "raw prompt · GEPA running",
        "qwen",
        "raw",
        "Qwen Pipeline",
        "Raw policy; no optimization.",
    ),
    (
        "qwen-image",
        "Similarity GEPA",
        "GPT Image 2 similarity objective",
        "qwen-sim-gepa",
        "gepa",
        "Qwen Pipeline",
        "45° orthographic camera, structural fidelity and reduced filler.",
    ),
    (
        "qwen-image",
        "Prompt/Layout GEPA",
        "GPT-5.5 judged objective",
        "qwen-judge-gepa",
        "gepa",
        "Qwen Pipeline",
        "No policy change; the seed remained best under the GPT-5.5 judge.",
    ),
    (
        "flux2-klein-4b",
        "Original",
        "raw prompt · 4B · 4 steps",
        "flux-raw",
        "raw",
        "FLUX.2 Klein 4B",
        "Raw policy; no optimization.",
    ),
    (
        "flux2-klein-4b",
        "Similarity GEPA",
        "GPT Image 2 similarity objective",
        "flux-sim-gepa",
        "gepa",
        "FLUX.2 Klein 4B",
        "No policy change; the seed remained best.",
    ),
    (
        "flux2-klein-4b",
        "Prompt/Layout GEPA",
        "GPT-5.5 judged objective",
        "flux-judge-gepa",
        "gepa",
        "FLUX.2 Klein 4B",
        "Clear routes, exact singular landmarks and visible obstacle placement.",
    ),
    (
        "z-image-turbo",
        "Original",
        "raw prompt · 6B · 9 steps",
        "zimage-raw",
        "raw",
        "Z-Image Turbo",
        "Raw policy; no optimization.",
    ),
    (
        "z-image-turbo",
        "Similarity GEPA",
        "GPT Image 2 similarity objective",
        "zimage-sim-gepa",
        "gepa",
        "Z-Image Turbo",
        "Strict orthographic framing, full footprint and geometry-first detail.",
    ),
    (
        "z-image-turbo",
        "Prompt/Layout GEPA",
        "GPT-5.5 judged winner · unchanged policy",
        "zimage-judge-gepa",
        "gepa",
        "Z-Image Turbo",
        "No policy change; the seed remained best.",
    ),
)

CSS = """
:root{color-scheme:dark;--bg:#0d1018;--panel:#151a25;--line:#2b3446;
--text:#edf0f6;--muted:#9ba6b8;--accent:#7aa2ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:14px/1.5 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:2;background:rgba(13,16,24,.96);
border-bottom:1px solid var(--line);padding:8px 14px}
.head{max-width:1800px;margin:auto;display:flex;gap:18px;align-items:center}
h1{font-size:20px;margin:0}.sub{color:var(--muted);font-size:12px}
.nav{display:flex;gap:7px;margin-top:5px}.nav a{color:var(--muted);
text-decoration:none;border:1px solid var(--line);border-radius:7px;padding:3px 8px;
font-size:11px}.nav a.active{color:var(--accent);border-color:var(--accent)}
select{background:var(--panel);color:var(--text);border:1px solid var(--line);
border-radius:8px;padding:9px 11px;min-width:150px}
.filters{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}
#picker{min-width:230px}
main{max-width:1900px;margin:auto;padding:6px 10px 20px}
.meta{display:flex;gap:6px;margin-bottom:6px}.chip{border:1px solid var(--line);
border-radius:999px;padding:4px 10px;color:var(--muted)}.chip strong{color:var(--text)}
.displayControls{margin:0 0 6px;background:var(--panel);border:1px solid var(--line);
border-radius:8px;padding:5px 8px}.displayControls summary{font-size:11px;color:var(--muted)}
.displayRows{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px;margin-top:5px}
.displayRow{display:flex;gap:5px;align-items:center;min-width:0}
.displayRow strong{width:150px;font-size:11px;white-space:nowrap;overflow:hidden;
text-overflow:ellipsis}.displayRow button{background:#10141d;color:var(--muted);
border:1px solid var(--line);
border-radius:999px;padding:4px 9px;cursor:pointer;font-size:11px}
.displayRow button.active{color:var(--text);border-color:var(--accent);
background:#17223a}
.displayRow button.modelToggle{font-weight:700}.displayRow.modelOff{opacity:.45}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}
.modelRow{display:block;background:var(--panel);border:1px solid var(--line);
border-radius:9px;padding:6px}.modelName{padding:1px 3px 5px;font-size:13px;font-weight:700}
.versions{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:5px}
.pane{display:flex;flex-direction:column;gap:4px;background:#111620;border:1px solid var(--line);
border-radius:7px;padding:5px;min-width:0}
.pane h3{font-size:10px;margin:0;display:flex;gap:4px;justify-content:space-between;
white-space:nowrap;overflow:hidden}.pane h3 span{font-size:9px;color:var(--muted);
font-weight:400;overflow:hidden;text-overflow:ellipsis}
.changes{height:23px;font-size:9px;line-height:11px;color:var(--accent);overflow:hidden;
display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.pane img{display:block;width:clamp(82px,9.5vw,120px);height:clamp(82px,9.5vw,120px);
margin:auto;
object-fit:contain;background:#080a10;
border:1px solid var(--line);border-radius:7px;cursor:zoom-in}
.unsupported{display:grid;place-items:center;width:clamp(82px,9.5vw,120px);
height:clamp(82px,9.5vw,120px);
margin:auto;background:#10131a;
border:1px dashed var(--line);border-radius:7px;color:var(--muted);text-align:center;
padding:6px;font-size:9px}
.grid.filtered .pane img,.grid.filtered .unsupported{
width:clamp(170px,18vw,280px);height:clamp(170px,18vw,280px)}
.grid.singleGroup{grid-template-columns:1fr}
.grid.singleGroup .versions{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
.grid.singleCard .pane img,.grid.singleCard .unsupported{
width:min(520px,72vw);height:min(520px,72vw)}
.topPrompt{display:grid;grid-template-columns:130px 1fr;gap:6px;align-items:stretch;
margin-bottom:6px;background:var(--panel);border:1px solid var(--line);border-radius:8px;
padding:5px}.topPrompt strong{display:flex;align-items:center;padding:4px;font-size:11px}
.topPrompt pre{height:38px;max-height:38px;margin:0;padding:5px;background:#0b0e15;
border:1px solid var(--line);border-radius:6px}
details{margin-top:15px;background:var(--panel);border:1px solid var(--line);
border-radius:9px;padding:10px}summary{cursor:pointer;color:var(--muted)}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font:11px/1.5 ui-monospace,monospace;
max-height:260px;overflow:auto}.note{margin-top:12px;color:var(--muted);font-size:12px}
.lightbox{display:none;position:fixed;inset:0;z-index:5;background:rgba(0,0,0,.94);
align-items:center;justify-content:center;padding:18px}.lightbox.open{display:flex}
.lightbox img{max-width:97vw;max-height:97vh;object-fit:contain}
.promptTip{display:none;position:fixed;z-index:8;width:min(560px,70vw);max-height:55vh;
overflow:auto;pointer-events:none;background:#090c12;border:1px solid var(--accent);
border-radius:8px;padding:9px;box-shadow:0 10px 35px rgba(0,0,0,.6)}
.promptTip.open{display:block}.promptTip strong{display:block;margin-bottom:5px}
.promptTip pre{margin:0;white-space:pre-wrap;font:10px/1.4 ui-monospace,monospace}
@media(max-width:780px){.grid{grid-template-columns:1fr}
.head{align-items:flex-start;flex-direction:column}.filters{margin:0;width:100%}
select{margin:0;width:100%}.displayRows{grid-template-columns:1fr}}
"""

BODY = """
<header><div class="head"><div><h1>Golden prompt image-model comparison</h1>
<div class="sub">Isometric outputs only. Top-down-first scenes are converted from each
model's own first-stage image where the model supports references.</div>
<nav class="nav"><a href="/features">Original viewer</a><a href="/pipeline">Pipeline</a>
<a class="active" href="/comparison">GPT Image 2 vs Gemini</a></nav>
</div><div class="filters"><select id="genre" aria-label="Genre"></select>
<select id="picker" aria-label="Scene"></select></div>
</div></header>
<main><div class="meta" id="meta"></div>
<details class="displayControls" open><summary>Models and variants</summary>
<div class="displayRows" id="displayRows"></div></details>
<section class="topPrompt"><strong>Initial user prompt</strong><pre id="userPrompt"></pre></section>
<div class="grid" id="grid"></div>
<div class="note">75 golden scenes · 1024×1024. Z-Image is unavailable for the 30
top-down-first scenes because it has no reference-image or edit capability.</div></main>
<div class="lightbox" id="lightbox"><img></div>
<div class="promptTip" id="promptTip"><strong></strong><pre></pre></div>
"""

JS = r"""
const ROWS=__ROWS__,MODELS=__MODELS__,ROOT="__ROOT__",
FLUXSECOND="__FLUXSECOND__",QWENSECOND="__QWENSECOND__",
GEMINICAPTION="__GEMINICAPTION__",GEMINICAPTIONGEPA="__GEMINICAPTIONGEPA__",
GEMINIRECAPTION="__GEMINIRECAPTION__",
GEMINIGPTRECAPTIONGEPA="__GEMINIGPTRECAPTIONGEPA__",
GEMINICONTRACTREPAIR="__GEMINICONTRACTREPAIR__";
const $=id=>document.getElementById(id),picker=$("picker"),genre=$("genre"),
displayRows=$("displayRows");
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",
'"':"&quot;","'":"&#39;"}[c]));
const genres=[...new Set(ROWS.map(r=>r.genre))].sort((a,b)=>a.localeCompare(b));
genre.innerHTML=`<option value="">All genres</option>`+genres.map(g=>
`<option value="${esc(g)}">${esc(g)}</option>`).join("");
const modelNames=[...new Set(MODELS.map(m=>m.group))],
activeGroups=new Set(modelNames),activeKinds=new Set(MODELS.map(m=>m.kind));
function drawDisplayControls(){displayRows.innerHTML=modelNames.map(group=>{
 const enabled=activeGroups.has(group),variants=MODELS.filter(m=>m.group===group);
 return `<div class="displayRow ${enabled?"":"modelOff"}">
 <button type="button" class="modelToggle ${enabled?"active":""}" data-group="${esc(group)}"
 aria-pressed="${enabled}">${enabled?"Hide":"Show"}</button><strong>${esc(group)}</strong>
 ${variants.map(m=>`<button type="button" class="${activeKinds.has(m.kind)?"active":""}"
 data-kind="${esc(m.kind)}" aria-pressed="${activeKinds.has(m.kind)}">${esc(m.label)}</button>`
 ).join("")}</div>`}).join("")}
drawDisplayControls();
function refreshPicker(){const previous=picker.value;
 const visible=ROWS.filter(r=>!genre.value||r.genre===genre.value);
 picker.innerHTML=visible.map(r=>`<option value="${esc(r.scene)}">Scene ${esc(r.scene)} · ${
 esc(r.initial_stage)} first</option>`).join("");
 if(visible.some(r=>r.scene===previous))picker.value=previous;
 render()}
function render(){const r=ROWS.find(x=>x.scene===picker.value)||ROWS[0];
 const scene=r.scene,topdownFirst=r.initial_stage==="topdown";
 $("meta").innerHTML=`<span class="chip"><strong>Scene:</strong> ${esc(scene)}</span>
 <span class="chip"><strong>Genre:</strong> ${esc(r.genre)}</span>
 <span class="chip"><strong>View:</strong> isometric</span>
 <span class="chip"><strong>Pipeline:</strong> ${esc(r.initial_stage)} first</span>`;
 const card=m=>{let src="",unsupported="";
 const hasScene=m.available&&(!m.scenes||m.scenes.includes(scene));
 if(m.kind==="baseline")src=
 `/results/scenes/agent_gpt52_upstream_cf94b18_gptimage2_260815/iso/${scene}.png`;
 else if(m.kind==="gemini-original")
 src=`/results/scenes/__GEMINIORIGINAL__/iso/${scene}.png`;
 else if(m.kind==="gemini-caption"&&hasScene)
 src=`/results/t2i/${GEMINICAPTION}/images/${scene}_iso.png`;
 else if(m.kind==="gemini-caption-gepa"&&hasScene)
 src=`/results/gepa/${GEMINICAPTIONGEPA}/images/isometric/${scene}.png`;
 else if(m.kind==="gemini-recaption"&&hasScene)
 src=`/results/t2i/${GEMINIRECAPTION}/images/${scene}_iso.png`;
 else if(m.kind==="gemini-gptprompt-recaption-gepa"&&hasScene)
 src=`/results/gepa/${GEMINIGPTRECAPTIONGEPA}/images/isometric/${scene}.png`;
 else if(m.kind==="gemini-contract-repair"&&hasScene)
 src=`/results/t2i/${GEMINICONTRACTREPAIR}/images/${scene}_iso.png`;
 else if(m.kind==="gepa")src=
 `/results/gepa/gemini_gepa_all75_v1_260816/images/isometric/${scene}.jpg`;
 else if(m.kind==="gemini-judge-gepa"&&hasScene)
 src=`/results/gepa/gemini_gepa_vlm_gpt55_all75_eval_v1_260817/images/isometric/${scene}.jpg`;
 else if(m.kind==="gemini-600-gepa"&&hasScene)
 src=`/results/gepa/gemini_gepa_upstream600_golden75_full_v1_260819/assets/gemini/${scene}.jpg`;
 else if(m.kind==="gemini-600-no-recaption-gepa"&&hasScene)
 src=`/results/gepa/gemini_gepa_upstream600_golden75_no_recaption_full_v1_260819/assets/gemini/${scene}.jpg`;
 else if(m.kind==="gemini-camera-gepa"&&hasScene)
 src=`/results/gepa/gemini_gepa_vlm_similarity_iso_all75_eval_v2_260818/images/isometric/${scene}.jpg`;
 else if(m.kind==="qwen")src=topdownFirst
 ?`/results/t2i/${QWENSECOND}/qwen-image-edit/${scene}-isometric.png`
 :`/results/t2i/${ROOT}/qwen-image/${scene}-isometric.png`;
 else if(m.kind==="qwen-sim-gepa")
 src=`/results/gepa/qwen_pipeline_gepa_iso_all75_v1_260817/images/isometric/${scene}.jpg`;
 else if(m.kind==="qwen-judge-gepa"&&hasScene)
 src=`/results/gepa/qwen_pipeline_gepa_vlm_gpt55_all75_eval_v1_260817/images/isometric/${scene}.jpg`;
 else if(m.kind==="flux-raw")src=topdownFirst
 ?`/results/t2i/${FLUXSECOND}/flux2-klein-4b/${scene}-isometric.png`
 :`/results/t2i/${ROOT}/flux2-klein-4b/${scene}-isometric.png`;
 else if(m.kind==="flux-sim-gepa")
 src=`/results/gepa/flux_gepa_iso_all75_v1_260817/images/isometric/${scene}.jpg`;
 else if(m.kind==="flux-judge-gepa"&&m.available)
 src=`/results/gepa/flux_gepa_vlm_gpt55_all75_eval_v1_260817/images/isometric/${scene}.jpg`;
 else if(m.kind==="zimage-raw"&&!topdownFirst)
 src=`/results/t2i/${ROOT}/z-image-turbo/${scene}-isometric.png`;
 else if(m.kind==="zimage-sim-gepa"&&!topdownFirst)
 src=`/results/gepa/zimage_gepa_iso_std45_v1_260817/images/isometric/${scene}.jpg`;
 else if(m.kind==="zimage-judge-gepa"&&!topdownFirst)
 src=`/results/gepa/zimage_gepa_vlm_gpt55_std45_v1_260817/images/isometric/${scene}.jpg`;
 else if(!m.available)unsupported=`${m.label} results are unavailable.`;
 else if(m.scenes&&!m.scenes.includes(scene))
 unsupported=`${m.label} was not evaluated for this scene.`;
 else unsupported="No geometry-preserving isometric: this model cannot accept its top-down output.";
 const fullPrompt=m.promptKind==="raw"?r.isometric_prompt:(r.gepa_prompts[m.kind]||"");
 return `<article class="pane"><h3>${esc(m.label)}<span>${esc(m.detail)}</span></h3>
 <div class="changes">${esc(m.changes)}</div>
 ${unsupported?`<div class="unsupported">${esc(unsupported)}</div>`:
 `<img src="${esc(src)}" data-full="${esc(src)}" data-model="${esc(m.group+" · "+m.label)}"
 data-prompt="${esc(fullPrompt)}" alt="${esc(m.label)} output">`}
 </article>`};
 const visibleModels=MODELS.filter(m=>activeGroups.has(m.group)&&activeKinds.has(m.kind));
 const groups=[...visibleModels.reduce((map,m)=>{if(!map.has(m.group))map.set(m.group,[]);
 map.get(m.group).push(m);return map},new Map())];
 const grid=$("grid");
 grid.className=`grid${visibleModels.length!==MODELS.length?" filtered":""}${
 groups.length===1?" singleGroup":""}${visibleModels.length===1?" singleCard":""}`;
 grid.innerHTML=groups.map(([name,versions])=>
 `<section class="modelRow"><div class="modelName">${esc(name)}</div>
 <div class="versions">${versions.map(card).join("")}</div></section>`).join("");
 $("userPrompt").textContent=r.author_prompt}
picker.addEventListener("change",render);
genre.addEventListener("change",refreshPicker);
displayRows.addEventListener("click",event=>{const button=event.target.closest("button");
 if(!button)return;
 if(button.dataset.group){const group=button.dataset.group;
  if(activeGroups.has(group))activeGroups.delete(group);else activeGroups.add(group)}
 else if(button.dataset.kind){const kind=button.dataset.kind;
  if(activeKinds.has(kind))activeKinds.delete(kind);else activeKinds.add(kind)}
 drawDisplayControls();render()});
document.addEventListener("keydown",e=>{if(!["ArrowLeft","ArrowRight"].includes(e.key))return;
 const n=picker.selectedIndex+(e.key==="ArrowRight"?1:-1);
 if(n>=0&&n<picker.options.length){picker.selectedIndex=n;render()}});
const lb=$("lightbox"),li=lb.querySelector("img");
const tip=$("promptTip"),tipTitle=tip.querySelector("strong"),tipText=tip.querySelector("pre");
document.addEventListener("mouseover",e=>{if(!e.target.matches(".pane img"))return;
 tipTitle.textContent=e.target.dataset.model;tipText.textContent=e.target.dataset.prompt;
 tip.classList.add("open")});
document.addEventListener("mousemove",e=>{if(!tip.classList.contains("open"))return;
 tip.style.left=`${Math.min(e.clientX+14,innerWidth-tip.offsetWidth-8)}px`;
 tip.style.top=`${Math.min(e.clientY+14,innerHeight-tip.offsetHeight-8)}px`});
document.addEventListener("mouseout",e=>{if(e.target.matches(".pane img"))
 tip.classList.remove("open")});
document.addEventListener("click",e=>{if(e.target.matches(".pane img")){
 li.src=e.target.dataset.full;lb.classList.add("open")}else if(e.target===lb||e.target===li){
 lb.classList.remove("open");li.src=""}});refreshPicker();
"""


def build(
    root: Path,
    source_manifest: Path,
    flux_second_root: Path,
    qwen_second_root: Path,
    gemini_caption_root: Path,
    gemini_caption_gepa_root: Path,
    gemini_recaption_root: Path,
    gemini_gptprompt_recaption_gepa_root: Path,
    gemini_contract_repair_root: Path,
) -> str:
    source_rows = json.loads(source_manifest.read_text(encoding="utf-8"))["scenes"]
    rows = [
            {
                "scene": row["scene"],
                "initial_stage": (
                    "isometric" if row["render_order"] == "std" else "topdown"
                ),
                "genre": row["genre"],
                "author_prompt": row["author_prompt"],
                "isometric_prompt": row["isometric"]["prompt"],
            }
            for row in source_rows
            if row["scene"].isdigit() and 1 <= int(row["scene"]) <= 75
    ]
    if len(rows) != 75:
        raise ValueError(f"expected 75 golden scenes, found {len(rows)}")

    def completed(result_root: Path) -> set[str]:
        manifest = json.loads(
            (result_root / "manifest.json").read_text(encoding="utf-8")
        )
        return {
            result["prompt_id"]
            for result in manifest["results"]
            if result["status"] == "ok"
        }

    initial = completed(root)
    flux_second = completed(flux_second_root)
    qwen_second = completed(qwen_second_root)
    for row in rows:
        prompt_id = f"{row['scene']}-isometric"
        available = initial if row["initial_stage"] == "isometric" else flux_second
        if prompt_id not in available:
            raise ValueError(f"missing FLUX isometric output: {prompt_id}")
        available = initial if row["initial_stage"] == "isometric" else qwen_second
        if prompt_id not in available:
            raise ValueError(f"missing Qwen isometric output: {prompt_id}")
    models = [
        {
            "id": model_id,
            "label": label,
            "detail": detail,
            "kind": kind,
            "promptKind": prompt_kind,
            "group": group,
            "changes": changes,
        }
        for model_id, label, detail, kind, prompt_kind, group, changes in MODELS
    ]
    prompt_manifests = {
        "gepa": GEMINI_GEPA / "s3_manifest.json",
        "gemini-judge-gepa": GEMINI_JUDGE_GEPA / "s3_manifest.json",
        "gemini-camera-gepa": GEMINI_CAMERA_GEPA / "s3_manifest.json",
        "gemini-caption-gepa": gemini_caption_gepa_root / "s3_manifest.json",
        "gemini-gptprompt-recaption-gepa": (
            gemini_gptprompt_recaption_gepa_root / "s3_manifest.json"
        ),
        "qwen-sim-gepa": QWEN_SIM_GEPA / "s3_manifest.json",
        "qwen-judge-gepa": QWEN_JUDGE_GEPA / "s3_manifest.json",
        "flux-sim-gepa": FLUX_SIM_GEPA / "s3_manifest.json",
        "flux-judge-gepa": FLUX_JUDGE_GEPA / "s3_manifest.json",
        "zimage-sim-gepa": ZIMAGE_SIM_GEPA / "s3_manifest.json",
        "zimage-judge-gepa": ZIMAGE_JUDGE_GEPA / "s3_manifest.json",
    }
    prompt_manifests = {
        kind: path for kind, path in prompt_manifests.items() if path.is_file()
    }
    prompts_by_kind = {
        kind: {
            scene["scene"]: scene["prompts"]["isometric"]["text"]
            for scene in json.loads(path.read_text(encoding="utf-8"))["scenes"]
        }
        for kind, path in prompt_manifests.items()
    }
    candidate_paths = {
        "gemini-600-gepa": GEMINI_600_GEPA_CANDIDATE,
        "gemini-600-no-recaption-gepa": (
            GEMINI_600_NO_RECAPTION_GEPA_CANDIDATE
        ),
    }
    for kind, candidate_path in candidate_paths.items():
        if not candidate_path.is_file():
            continue
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        prompts_by_kind[kind] = {
            row["scene"]: pipeline_prompts.with_instruction(
                row["isometric_prompt"],
                "iso",
                candidate["iso"],
            )
            for row in rows
        }
    prompts_by_kind["gemini-original"] = {
        row["scene"]: row["isometric"]["prompt"]
        for line in GEMINI_ORIGINAL_PROMPTS.read_text(encoding="utf-8").splitlines()
        if (row := json.loads(line))
    }
    caption_scores = gemini_caption_root / "scores.jsonl"
    if caption_scores.is_file():
        prompts_by_kind["gemini-caption"] = {
            row["scene"]: row["caption"]
            for line in caption_scores.read_text(encoding="utf-8").splitlines()
            if (row := json.loads(line)) and row["stage"] == "iso"
        }
    recaption_scores = gemini_recaption_root / "scores.jsonl"
    if recaption_scores.is_file():
        prompts_by_kind["gemini-recaption"] = {
            row["scene"]: row["best_caption"]
            for line in recaption_scores.read_text(encoding="utf-8").splitlines()
            if (row := json.loads(line))
        }
    contract_repair_scores = gemini_contract_repair_root / "scores.jsonl"
    if contract_repair_scores.is_file():
        contract_rows = [
            json.loads(line)
            for line in contract_repair_scores.read_text(encoding="utf-8").splitlines()
            if line
        ]
        prompts_by_kind["gemini-contract-repair"] = {
            row["scene"]: (
                next(
                    item["generation_prompt"]
                    for item in row["history"]
                    if item["iteration"] == row["best_iteration"]
                )
                if row["best_iteration"]
                else row["base_generation_prompt"]
            )
            for row in contract_rows
        }
    for row in rows:
        row["gepa_prompts"] = {
            kind: prompts.get(row["scene"], "")
            for kind, prompts in prompts_by_kind.items()
        }
    for model in models:
        model["available"] = model["kind"] not in {
            "gemini-original", "gemini-caption", "gemini-caption-gepa",
            "gemini-recaption", "gemini-gptprompt-recaption-gepa",
            "gemini-contract-repair", "gemini-judge-gepa",
            "gemini-camera-gepa", "gemini-600-gepa",
            "gemini-600-no-recaption-gepa", "qwen-judge-gepa"
        } or model["kind"] in prompts_by_kind
        if model["kind"] in prompts_by_kind:
            model["scenes"] = sorted(prompts_by_kind[model["kind"]])
    script = (
        JS.replace("__ROWS__", json.dumps(rows, ensure_ascii=False).replace("</", "<\\/"))
        .replace("__MODELS__", json.dumps(models))
        .replace("__ROOT__", root.name)
        .replace("__GEMINIORIGINAL__", GEMINI_ORIGINAL_RUN)
        .replace("__GEMINICAPTION__", gemini_caption_root.name)
        .replace("__GEMINICAPTIONGEPA__", gemini_caption_gepa_root.name)
        .replace("__GEMINIRECAPTION__", gemini_recaption_root.name)
        .replace(
            "__GEMINIGPTRECAPTIONGEPA__",
            gemini_gptprompt_recaption_gepa_root.name,
        )
        .replace("__GEMINICONTRACTREPAIR__", gemini_contract_repair_root.name)
        .replace("__FLUXSECOND__", flux_second_root.name)
        .replace("__QWENSECOND__", qwen_second_root.name)
    )
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>Golden T2I comparison</title><style>{CSS}</style></head>"
        f"<body>{BODY}<script>{script}</script></body></html>\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--source-manifest",
        type=Path,
        default=DEFAULT_SOURCE_MANIFEST,
    )
    parser.add_argument(
        "--flux-second-root",
        type=Path,
        default=DEFAULT_FLUX_SECOND_ROOT,
    )
    parser.add_argument(
        "--qwen-second-root",
        type=Path,
        default=DEFAULT_QWEN_SECOND_ROOT,
    )
    parser.add_argument(
        "--gemini-caption-root",
        type=Path,
        default=GEMINI_CAPTION_ROOT,
    )
    parser.add_argument(
        "--gemini-caption-gepa-root",
        type=Path,
        default=GEMINI_CAPTION_GEPA_ROOT,
    )
    parser.add_argument(
        "--gemini-recaption-root",
        type=Path,
        default=GEMINI_RECAPTION_ROOT,
    )
    parser.add_argument(
        "--gemini-gptprompt-recaption-gepa-root",
        type=Path,
        default=GEMINI_GPTPROMPT_RECAPTION_GEPA_ROOT,
    )
    parser.add_argument(
        "--gemini-contract-repair-root",
        type=Path,
        default=GEMINI_CONTRACT_REPAIR_ROOT,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    page = build(
        args.root,
        args.source_manifest,
        args.flux_second_root,
        args.qwen_second_root,
        args.gemini_caption_root,
        args.gemini_caption_gepa_root,
        args.gemini_recaption_root,
        args.gemini_gptprompt_recaption_gepa_root,
        args.gemini_contract_repair_root,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".part")
    temporary.write_text(page, encoding="utf-8")
    temporary.replace(args.output)
    print(f"wrote {args.output} ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
