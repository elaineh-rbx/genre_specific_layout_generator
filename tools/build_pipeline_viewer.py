"""Build a per-scene pipeline flowchart viewer.

For each corrected prose-agent scene this emits one HTML page with a scene
picker at the top and, for the selected scene, the full LayoutGen pipeline
graph with THAT scene's actual data lit up on each node:

    prompt     the scene's source text
    classify   which genre the router picked
    ask        the intake questions the agent answered (count + list below)
    genre      the picked genre / shape / preset
    blob       the Cursor agent's prose layout decision and enriched scene body
    json       the strict structured JSON transcribed by the Gateway
    streams    options split by `Goes to`: image_prompt vs layout_placement
    route      P0/P2/P3/P4/P6/tiered - what routes the scene off the happy path
    iso/td     the actual images that landed for this scene
    plan       the authored plan, if the scene runs the layout-first path

An optional read-only comparison panel places a fresh skill-run prose decision beside
the production decision. It never presents untranscribed prose as a rendered result.

Node layout (positions, edges, boundary/edgePath math) is lifted from
`mpalleschi/3D-LayoutBuild-Rules/pipeline-viewer.html`, since that is the
canonical drawing of the pipeline. Here we swap its `VARIATIONS` picker for
one whose options are our real scenes, and every node's subtitle is drawn
from that scene rather than from a hypothetical variation.

Usage:
    python tools/build_pipeline_viewer.py            # writes results/pipeline_viewer.html
    python tools/build_pipeline_viewer.py --out foo.html
    python tools/build_pipeline_viewer.py \
        --scope-after-dir results/routing/agent_blob_scope_reduce_RUN \
        --scope-after-manifest run/scope_reduce_RUN/manifest.json \
        --scope-after-image-dir results/scenes/scope_reduce_RUN \
        --only-scope-compared
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen.model import rules as br  # noqa: E402
from layoutgen.paths import RESULTS, ROUTING  # noqa: E402

AGENT = ROUTING / "agent_spec_gateway"
EVAL = RESULTS / "eval"

#: Route modifiers the flowchart lights up. Anything else in `route` (P0, CHECK,
#: SET) is informational and does not push the scene off the happy path.
FLOWCHART_MODIFIERS = {"P2", "P3", "P4", "P6"}


def unescape_nl(s: str) -> str:
    """Turn the CSV-import's literal `\\n` sequences into real newlines for
    display - the router saw them as-is either way."""
    return s.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "    ")


def prose_section(text: str, heading: str) -> str:
    """Return one ``##`` prose section without interpreting its decision."""
    marker = f"## {heading}"
    if marker not in text:
        return ""
    body = text.split(marker, 1)[1]
    return body.split("\n## ", 1)[0].strip()


def scope_comparisons(
    prose_dir: pathlib.Path | None,
    manifest_path: pathlib.Path | None,
    image_dir: pathlib.Path | None = None,
    image_status: str = "prompt-only",
) -> dict[str, dict]:
    """Load a skill-run comparison without promoting it to production.

    The prose artifacts have deliberately not passed through Gateway transcription.
    Optional images are direct prompt-only previews, so the viewer must keep them
    separate from the baseline structured production spec and images.
    """
    if prose_dir is None:
        return {}
    manifest = {}
    if manifest_path and manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = manifest.get("validation_failures") or {}
    rows = {}
    for path in sorted(prose_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        images = {}
        if image_dir is not None:
            for kind in ("iso", "td", "plan"):
                candidate = image_dir / kind / f"{path.stem}.png"
                if candidate.is_file():
                    try:
                        image_url = "/" + candidate.resolve().relative_to(
                            REPO.resolve()
                        ).as_posix()
                    except ValueError:
                        image_url = candidate.resolve().as_uri()
                    images[kind] = image_url
        scope_result = prose_section(text, "Scope reduction result")
        ledger = scope_result or prose_section(
            text, "Scale, theme, and pipeline cost"
        )
        final_prompt = prose_section(text, "Final scoped image prompt")
        rows[path.stem] = {
            "scope_after_blob": text,
            "scope_after_enriched": (
                final_prompt or prose_section(text, "Enriched image prompt")
            ),
            "scope_after_genre": prose_section(text, "Genre"),
            "scope_after_shape": (
                prose_section(text, "Shape and preset")
                or prose_section(text, "Shape, and the preset it came from")
            ),
            "scope_after_ledger": ledger,
            "scope_after_fired": (
                (
                    "scope reduction:" in ledger.lower()
                    or (
                        bool(scope_result)
                        and "active" in scope_result.lower()
                    )
                )
                and "does not fire" not in ledger.lower()
                and "did not fire" not in ledger.lower()
                and "does not need reduction" not in ledger.lower()
            ),
            "scope_after_failure": failures.get(path.stem, ""),
            "scope_after_images": images,
            "scope_after_image_status": image_status if images else "",
            "scope_after_run": manifest.get("run_name", prose_dir.name),
            "scope_after_version": manifest.get("instruction_version", ""),
            "scope_after_structurally_valid": (
                manifest.get("structurally_valid_outputs", 0)
            ),
            "scope_after_total": manifest.get("scene_count", len(rows) + 1),
        }
    return rows


def catalogue_option(genre, oid: str):
    """Resolve an option from the dominant genre or the shared catalogue."""
    if genre and (option := genre.option(oid)):
        return option
    for candidate in [*br.GENRES.values(), br.NO_GENRE]:
        if option := candidate.option(oid):
            return option
    return None


def option_split(cfg: dict) -> tuple[list[dict], list[dict]]:
    """Split picks into the two handoff streams. `image_prompt` is the visible
    geometry that ends up in the isometric render; `layout_placement` is the
    invisible stuff placed after segmentation (triggers, spawns, emitters).

    The document's rule is `Option.drawn` (goes_to ∈ {image, both}); we mirror
    it verbatim so both places agree on which stream a pick belongs to.
    """
    g = br.genre(cfg.get("genre", ""))
    img, lay = [], []
    placements = {o.get("id"): o for o in cfg.get("layout_placement") or []}
    seen_lay = set()
    for pick in cfg.get("options") or []:
        oid = pick.get("id", "")
        o = catalogue_option(g, oid)
        entry = {
            "id": oid,
            "label": o.label if o else oid,
            "what": pick.get("text") or (o.what if o else ""),
            "injected_what": (
                br.visible_text(g.name, o) if g and o and o.drawn else ""
            ),
            "goes": o.goes_to if o else ("image" if pick.get("visible") else "layout"),
            "type": o.type if o else "",
            "pipeline": o.pipeline if o else "",
            "core": bool(o.core) if o else False,
            "universal": bool(o.universal) if o else False,
            "count": pick.get("count", -1),
            "visible": bool(pick.get("visible", True)),
            "catalogue_what": o.what if o else "",
        }
        if pick.get("visible", True):
            img.append(entry)
        else:
            lay.append(entry)
            seen_lay.add(oid)
    for oid, pick in placements.items():
        if oid in seen_lay:
            continue
        o = catalogue_option(g, oid)
        lay.append({
            "id": oid,
            "label": o.label if o else oid,
            "what": pick.get("text") or pick.get("where") or (o.what if o else ""),
            "injected_what": (
                br.visible_text(g.name, o) if g and o and o.drawn else ""
            ),
            "goes": o.goes_to if o else "layout",
            "type": o.type if o else "",
            "pipeline": o.pipeline if o else "",
            "core": bool(o.core) if o else False,
            "universal": bool(o.universal) if o else False,
            "count": pick.get("count", -1),
            "visible": False,
            "catalogue_what": o.what if o else "",
        })
    return img, lay


def sent_prompts(run_name: str = "agent_gateway") -> dict[str, dict]:
    """The prompts each scene was actually rendered from, out of the arm's run file.

    A separate file from the routing because they are separate facts: the routing is
    what was decided, the run is what was sent. The viewer needs both, and only the
    second one is evidence about the image.
    """
    path = RESULTS / "runs" / f"{run_name}.jsonl"
    if not path.is_file():
        return {}
    return {r["scene"]: r for line in path.open()
            if line.strip() for r in [json.loads(line)]}


def collect(
    run_name: str = "agent_gateway",
    image_arm: str = "agent_gateway_260813",
    *,
    only_sent: bool = False,
    checklist_dir: pathlib.Path = EVAL,
    scope_after_dir: pathlib.Path | None = None,
    scope_after_manifest: pathlib.Path | None = None,
    scope_after_image_dir: pathlib.Path | None = None,
    scope_after_image_status: str = "prompt-only",
    only_scope_compared: bool = False,
) -> list[dict]:
    rows: list[dict] = []
    sent = sent_prompts(run_name)
    scope_after = scope_comparisons(
        scope_after_dir,
        scope_after_manifest,
        scope_after_image_dir,
        scope_after_image_status,
    )
    for p in sorted(AGENT.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        cfg = d.get("spec") or {}
        scene = d["scene"]
        if only_sent and scene not in sent:
            continue
        if only_scope_compared and scene not in scope_after:
            continue
        route = list(cfg.get("route") or [])
        mods = [m for m in route if m in FLOWCHART_MODIFIERS]
        tiered = "tiered" in route
        check = "CHECK" in route
        set_piece = "SET" in route

        img_opts, lay_opts = option_split(cfg)
        genre = br.genre(cfg.get("genre", ""))
        shape = genre.shape(cfg.get("shape") or "") if genre else None
        axes = []
        for key, value in (cfg.get("axes") or {}).items():
            axis = genre.axis(key) if genre else None
            axes.append({
                "id": axis.id if axis else key,
                "label": axis.name if axis else key,
                "value": value,
                "default": axis.default if axis else "",
                "pipeline": (axis.routes.get(value, "") if axis else ""),
                "what": axis.what if axis else "",
                "clause": (
                    axis.clauses.get(value, "")
                    if axis and value != axis.default
                    and axis.id not in br.ROUTING_ONLY_AXES
                    else ""
                ),
                "routing_only": bool(
                    axis and value != axis.default
                    and axis.id in br.ROUTING_ONLY_AXES
                ),
            })

        images = {}
        run = sent.get(scene, {})
        if run.get("status") == "ok":
            for kind in ("iso", "td", "plan"):
                if run.get(kind):
                    images[kind] = (
                        f"/results/scenes/{image_arm}/{kind}/{scene}.png"
                    )

        checklist = {"features": [], "excluded": []}
        ev = checklist_dir / f"{scene}.json"
        if ev.is_file():
            ec = json.loads(ev.read_text(encoding="utf-8"))
            checklist["features"] = ec.get("features") or []
            checklist["excluded"] = ec.get("excluded") or []

        answers = d.get("answers") or []
        row = {
            "id": scene,
            "prompt": unescape_nl(d.get("source", "")),
            # What actually reached the image model, assembled. The source prompt and
            # addendum are provenance; the enriched JSON field, wrapper, style tail, and
            # top-down transformation are represented by the exact final prompts here.
            "iso_prompt": run.get("iso_prompt", ""),
            "td_prompt": run.get("td_prompt", ""),
            "order": run.get("order", ""),
            "run_route": run.get("route") or [],
            "why": run.get("why", ""),
            "genre": cfg.get("genre", ""),
            "genre_route": genre.route if genre else "",
            "shape": cfg.get("shape") or "",
            "shape_label": shape.label if shape else "",
            "shape_selection": ({
                "id": shape.id,
                "label": shape.label,
                "type": shape.type,
                "what": shape.what,
                "pipeline": shape.pipeline,
            } if shape else {}),
            "axes_selection": axes,
            "preset": cfg.get("preset") or "none",
            "confidence": cfg.get("confidence", ""),
            "evidence": cfg.get("evidence", ""),
            "genre_evidence": cfg.get("genre_evidence", ""),
            "answers": answers,
            "clarifications": cfg.get("clarifications") or [],
            "enriched": cfg.get("initial_scene_subprompt_enriched", ""),
            "agent_blob": d.get("blob", ""),
            "before_ledger": prose_section(
                d.get("blob", ""), "Scale, theme, and pipeline cost"
            ),
            "structured_json": json.dumps(cfg, indent=2, ensure_ascii=False),
            "options_img": img_opts,
            "options_lay": lay_opts,
            "options_all": img_opts + [
                option for option in lay_opts
                if option["id"] not in {picked["id"] for picked in img_opts}
            ],
            "layout_placement": cfg.get("layout_placement") or [],
            "layout": cfg.get("layout") or {},
            "modifiers": mods,
            "tiered": tiered,
            "check": check,
            "set_piece": set_piece,
            "route": route,
            "addendum": run.get("addendum", ""),
            "images": images,
            "checklist": checklist,
        }
        row.update(scope_after.get(scene, {}))
        rows.append(row)
    return rows


CSS = """
:root{
  --bg:#0f1220;--panel:#171b2e;--panel-2:#1e2340;--line:#2b3153;
  --text:#e7e9f3;--muted:#9aa0c0;--accent:#6c8cff;
  --green:#35c88b;--green-bg:#123528;
  --orange:#f2a54c;--orange-bg:#3a2a12;
  --red:#ff5d6c;--red-bg:#3a1420;
  --dim:#39406b;--dim-bg:#161a2c;
}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  background:radial-gradient(1200px 700px at 20% -10%,#1a1f38 0%,var(--bg) 60%);
  color:var(--text);min-height:100vh;font-size:13px}
header{padding:18px 26px 12px;border-bottom:1px solid var(--line)}
header h1{margin:0 0 4px;font-size:19px}
header p{margin:0;color:var(--muted);font-size:12.5px;max-width:1100px;line-height:1.55}
header .nav{margin-top:8px;display:flex;gap:12px;font-size:12.5px}
header .nav a{color:var(--accent);text-decoration:none;padding:3px 9px;border-radius:6px;
  border:1px solid var(--line);background:var(--panel)}
header .nav a.active{border-color:var(--accent);background:var(--panel-2)}

.wrap{display:flex;align-items:stretch}
.sidebar{width:340px;flex:0 0 340px;padding:18px;border-right:1px solid var(--line)}
.sidebar label{font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted)}
.sidebar select{width:100%;margin-top:8px;padding:10px 11px;border-radius:9px;background:var(--panel-2);
  color:var(--text);border:1px solid var(--line);font-size:13px;cursor:pointer}
.sidebar .filt{width:100%;margin-top:8px;padding:8px 10px;border-radius:8px;background:var(--panel-2);
  color:var(--text);border:1px solid var(--line);font-size:12.5px}
.verdict{margin-top:14px;padding:12px;border-radius:11px;background:var(--panel);border:1px solid var(--line)}
.verdict .badge{display:inline-block;padding:4px 11px;border-radius:999px;font-size:11.5px;font-weight:700}
.b-green{background:var(--green-bg);color:var(--green);border:1px solid var(--green)}
.b-orange{background:var(--orange-bg);color:var(--orange);border:1px solid var(--orange)}
.b-red{background:var(--red-bg);color:var(--red);border:1px solid var(--red)}
.verdict h3{margin:10px 0 4px;font-size:13.5px}
.verdict .sub{color:var(--muted);font-size:12px;line-height:1.5}
.chips{margin-top:10px;display:flex;flex-wrap:wrap;gap:6px}
.chip{font-size:11px;padding:3px 8px;border-radius:7px;background:var(--panel-2);
  color:var(--muted);border:1px solid var(--line)}
.chip.green{color:var(--green);border-color:var(--green)}
.chip.orange{color:var(--orange);border-color:var(--orange)}
.chip.red{color:var(--red);border-color:var(--red)}

.sec{margin-top:16px}
.sec h4{margin:0 0 8px;font-size:11px;text-transform:uppercase;letter-spacing:.7px;color:var(--muted)}
.sec .box{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.qa{margin:0}
.qa .qi{padding:7px 0;border-top:1px dashed var(--line)}
.qa .qi:first-child{border-top:none;padding-top:0}
.qa .qi .field{color:var(--accent);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:10.5px;margin-right:6px;background:rgba(108,140,255,.1);
  border:1px solid rgba(108,140,255,.4);border-radius:4px;padding:1px 5px}
.qa .qi .q{color:var(--text);font-size:12px}
.qa .qi .a{color:var(--muted);font-size:12px;margin-top:3px;padding-left:11px;
  border-left:2px solid var(--accent)}
.qa .qi .a::before{content:"answer ";color:#556280;font-size:9.5px;
  letter-spacing:.06em;text-transform:uppercase;margin-right:4px}

.lane{border:1px solid var(--line);border-radius:10px;padding:8px 11px;margin:0 0 8px;background:var(--panel)}
.lane.img{border-color:var(--accent)}
.lane.lay{border-color:var(--green)}
.lane h5{margin:0 0 5px;font-size:11px;letter-spacing:.3px}
.lane.img h5{color:var(--accent)}
.lane.lay h5{color:var(--green)}
.lane ul{margin:0;padding-left:16px}
.lane li{font-size:11.5px;line-height:1.45;color:var(--text)}
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

.main{flex:1;padding:16px 22px 40px;overflow-x:auto}
.chart{position:relative;width:2500px;height:690px;
  background:linear-gradient(180deg,rgba(255,255,255,.02),transparent 60%);
  border-radius:14px}
.band{position:absolute;border:1px dashed var(--line);border-radius:14px;pointer-events:none}
.band>span{position:absolute;top:-8px;left:16px;padding:0 8px;background:var(--bg);
  font-size:10px;font-weight:700;letter-spacing:.9px;text-transform:uppercase;color:var(--muted)}
.edges{position:absolute;inset:0;width:100%;height:100%;overflow:visible;pointer-events:none}

.node{position:absolute;width:172px;transform:translate(-50%,-50%);
  border-radius:11px;padding:9px 11px;border:1.5px solid var(--dim);background:var(--dim-bg);
  display:flex;flex-direction:column;gap:3px;transition:all .2s ease}
.node .tag{font-size:9.5px;letter-spacing:.5px;text-transform:uppercase;color:var(--muted)}
.node .title{font-size:12.5px;font-weight:700;line-height:1.2}
.node .sub{font-size:10.5px;color:var(--muted);line-height:1.35}
.node .step{position:absolute;top:-10px;left:-10px;width:22px;height:22px;border-radius:50%;
  background:var(--accent);color:#0b0e1c;font-size:11px;font-weight:800;display:none;
  align-items:center;justify-content:center}
.node.on .step{display:flex}
.n-dim{opacity:.4}
.n-green{border-color:var(--green);background:var(--green-bg)}
.n-green .step{background:var(--green)}
.n-orange{border-color:var(--orange);background:var(--orange-bg)}
.n-orange .step{background:var(--orange);color:#241d05}
.n-red{border-color:var(--red);background:var(--red-bg);
  box-shadow:0 0 0 0 rgba(255,93,108,0);animation:pulse 1.5s ease-in-out infinite}
.n-red .step{background:var(--red)}
.n-stream{border-style:dashed}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(255,93,108,0);}50%{box-shadow:0 0 0 6px rgba(255,93,108,.18);}}

.node .thumb{margin-top:6px;border-radius:5px;overflow:hidden;background:#000;
  border:1px solid rgba(255,255,255,.08)}
.node .thumb img{display:block;width:100%;height:auto;cursor:zoom-in}
.node .brief{font-size:10.5px;color:var(--text);line-height:1.35;max-height:3.2em;overflow:hidden}
.node:hover,.node:focus{z-index:60;outline:none}
.node .hover-detail{display:none;position:absolute;left:50%;bottom:calc(100% + 11px);
  transform:translateX(-50%);width:560px;max-width:min(560px,80vw);
  max-height:min(560px,70vh);overflow:auto;z-index:80;padding:12px 14px;
  border:1px solid var(--accent);border-radius:10px;background:#090c15;
  box-shadow:0 12px 36px rgba(0,0,0,.65);color:var(--text);cursor:text}
.node:hover .hover-detail,.node:focus .hover-detail{display:block}
.hover-detail .hover-head{position:sticky;top:0;margin:0 0 9px;
  padding:9px 10px;background:#111728;border-bottom:1px solid var(--line);
  color:var(--accent);font-size:11px;font-weight:750;letter-spacing:.04em}
.hover-detail pre{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;
  font:11.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--text)}

.legend{max-width:1180px;margin:18px 0 4px;padding:12px 15px;border-radius:12px;
  background:var(--panel);border:1px solid var(--line);color:var(--muted);font-size:12px;line-height:1.55}
.legend b{color:var(--text)}
.legend code{background:var(--panel-2);padding:1px 5px;border-radius:5px;font-size:11.5px}

.scope-compare{max-width:2140px;margin:0 0 18px;border:1px solid var(--orange);
  border-radius:14px;padding:14px;background:linear-gradient(135deg,rgba(242,165,76,.09),rgba(108,140,255,.04))}
.scope-compare .compare-head{display:flex;gap:12px;align-items:flex-start;justify-content:space-between}
.scope-compare h2{margin:0;font-size:15px}
.scope-compare .compare-note{margin:5px 0 0;color:var(--muted);font-size:11.5px;line-height:1.5;max-width:980px}
.scope-status{flex:0 0 auto;padding:4px 9px;border-radius:999px;font-size:10.5px;font-weight:700;
  border:1px solid var(--orange);color:var(--orange);background:var(--orange-bg)}
.scope-status.fail{border-color:var(--red);color:var(--red);background:var(--red-bg)}
.scope-summary{display:grid;grid-template-columns:repeat(5,minmax(130px,1fr));gap:8px;margin:12px 0}
.scope-stat{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:9px 10px}
.scope-stat strong{display:block;font-size:17px;color:var(--text)}
.scope-stat span{display:block;margin-top:2px;color:var(--muted);font-size:10.5px}
.scope-flow{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin:12px 0}
.scope-flow span{padding:5px 9px;border:1px solid var(--line);border-radius:7px;background:var(--panel);
  font-size:10.5px;color:var(--text)}
.scope-flow span.added{border-color:var(--orange);color:var(--orange);font-weight:700}
.scope-flow i{font-style:normal;color:var(--muted)}
.compare-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.compare-card{min-width:0;background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:11px 12px}
.compare-card.after{border-color:rgba(242,165,76,.65)}
.compare-card h3{margin:0 0 7px;font-size:11px;text-transform:uppercase;letter-spacing:.65px}
.compare-card.before h3{color:var(--accent)}
.compare-card.after h3{color:var(--orange)}
.compare-card pre{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;max-height:250px;overflow:auto;
  font:11.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--text)}
.compare-card .empty{color:var(--muted);font-style:italic}
.compare-image{display:flex;align-items:center;justify-content:center;min-height:180px;
  border:1px solid var(--line);border-radius:8px;background:#0a0d16;overflow:hidden}
.compare-image img{display:block;width:100%;max-height:620px;object-fit:contain;cursor:zoom-in}
.compare-image .empty{padding:18px;text-align:center;font-size:11.5px;line-height:1.5}
.compare-detail{margin-top:10px}
.compare-detail summary{cursor:pointer;color:var(--muted);font-size:11px}
.compare-warning{margin:10px 0 0;padding:8px 10px;border-radius:8px;border:1px solid var(--red);
  background:var(--red-bg);color:var(--red);font-size:11.5px;line-height:1.45}
.render-boundary{margin:10px 0;padding:9px 11px;border-radius:8px;border:1px solid var(--orange);
  background:var(--orange-bg);color:var(--orange);font-size:11.5px;line-height:1.45;font-weight:600}
.contrast{margin:0 0 12px;background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:11px 12px}
.contrast h3{margin:0 0 8px;font-size:11px;text-transform:uppercase;letter-spacing:.65px;color:var(--green)}
.contrast-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.contrast-col{min-width:0;border-left:2px solid var(--green);padding-left:9px}
.contrast-col.changed{border-left-color:var(--orange)}
.contrast-col h4{margin:0 0 5px;font-size:10.5px;color:var(--green)}
.contrast-col.changed h4{color:var(--orange)}
.contrast-col ul{margin:0;padding-left:16px}
.contrast-col li{font-size:11.5px;line-height:1.45;color:var(--text);margin:2px 0}
.contrast-shapes{margin-top:9px;padding-top:9px;border-top:1px dashed var(--line);
  display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:start;font-size:11.5px}
.contrast-shapes .old{color:var(--accent)}.contrast-shapes .new{color:var(--orange)}
.contrast-shapes .arrow{color:var(--muted)}
@media(max-width:1000px){.compare-grid,.contrast-grid{grid-template-columns:1fr}.scope-summary{grid-template-columns:1fr 1fr}.scope-compare .compare-head{display:block}.scope-status{display:inline-block;margin-top:8px}.contrast-shapes{grid-template-columns:1fr}}

.tail{max-width:2140px;margin-top:20px;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:14px}
.tail .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.tail .card h5{margin:0 0 8px;font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted)}
.tail .card pre{margin:0;background:#0a0d16;border:1px solid var(--line);border-radius:8px;
  padding:9px 11px;font:11.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
  color:var(--text);white-space:pre-wrap;max-height:280px;overflow:auto}
.tail .card .prompt{max-height:220px;overflow:auto;font-size:12px;line-height:1.55;
  color:var(--text);white-space:pre-wrap}

.lightbox{position:fixed;inset:0;background:rgba(0,0,0,.94);display:none;
  align-items:center;justify-content:center;z-index:99;cursor:zoom-out;padding:24px}
.lightbox.open{display:flex}
.lightbox img{max-width:96vw;max-height:96vh;object-fit:contain}
"""


HEADER_HTML = """
<header>
  <h1>Pipeline viewer &mdash; per-scene attribution</h1>
  <p>Pick a scene: the graph lights up the actual path its prompt took through
  the pipeline. Each node shows what came in at that step, so you can attribute
  every input to its stage.
  <b style="color:var(--green)">Green</b> = fits the
  current pipeline. <b style="color:var(--orange)">Orange</b> = P6 variant
  (procedural first) or a tiered flag. <b style="color:var(--red)">Red</b> = a
  break (P2 elevation, P3 outside&#8594;inside, or P4 multi-zone) that pushes
  the scene onto a new path. Handoff streams are dashed; they run identically
  on every route, but the option lists change per scene.</p>
  <div class="nav">
    <a href="/features">Original viewer</a>
    <a href="/pipeline" class="active">Pipeline</a>
    <a href="/comparison">GPT Image 2 vs Gemini</a>
  </div>
</header>
"""

SCOPE_HEADER_HTML = HEADER_HTML.replace(
    "Pipeline viewer &mdash; per-scene attribution",
    "Pipeline viewer &mdash; scope-skill comparison",
).replace(
    "Pick a scene: the graph lights up the actual path its prompt took through\n"
    "  the pipeline. Each node shows what came in at that step, so you can attribute\n"
    "  every input to its stage.",
    "Pick a scene to compare the pre-skill production decision with the fresh\n"
    "  <code>scope-reduce-default</code> evaluation decision from the same input.\n"
    "  The graph below remains the production path and rendered evidence; the\n"
    "  comparison panel explicitly stops the after side before Gateway transcription\n"
    "  and images until validation passes.",
)


BODY_HTML = """
<div class="wrap">
  <aside class="sidebar">
    <label for="picker">Scene</label>
    <select id="picker" size="1"></select>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px">
      <select class="filt" id="genreFilt"></select>
      <input class="filt" id="filt" type="text" placeholder="id or prompt..." />
    </div>
    <div style="color:var(--muted);font-size:11px;margin-top:6px" id="pickerCount"></div>

    <div class="verdict">
      <span class="badge" id="verdictBadge"></span>
      <h3 id="sceneTitle"></h3>
      <div class="sub" id="sceneSub"></div>
      <div class="chips" id="chips"></div>
    </div>

    <div class="sec">
      <h4>Questions the intake asked, and the answers</h4>
      <div class="box"><div class="qa" id="qa"></div></div>
    </div>

    <div class="sec">
      <h4>Handoff streams (options split by "Goes to")</h4>
      <div class="lane img">
        <h5>image_prompt \u2014 visible geometry, injected into iso render</h5>
        <div id="optImg"></div>
      </div>
      <div class="lane lay">
        <h5>layout_placement \u2014 invisible, placed at phase 4.5</h5>
        <div id="optLay"></div>
      </div>
    </div>

    <div class="sec">
      <h4>Eval checklist \u2014 visible features to verify in the render</h4>
      <div class="box"><ul class="checklist" id="checklist"></ul></div>
      <details style="margin-top:6px" id="excludedDetails">
        <summary style="cursor:pointer;color:var(--muted);font-size:11px;padding:2px 0">
          non-visual asks excluded from the checklist
        </summary>
        <div class="box" style="margin-top:6px">
          <ul class="excluded" id="excluded"></ul>
        </div>
      </details>
    </div>
  </aside>

  <main class="main">
    <section class="scope-compare" id="scopeCompare">
      <div class="compare-head">
        <div>
          <h2>Before / after <code>scope-reduce-default</code></h2>
          <p class="compare-note">The left side is the pre-skill production decision.
          The right side starts from the unedited upstream-skill evaluation generated
          from the same original input. Each completed production pair appears as its
          Gateway transcription and image render finishes.</p>
        </div>
        <span class="scope-status" id="scopeStatus"></span>
      </div>
      <div class="scope-summary" aria-label="Dataset comparison summary">
        <div class="scope-stat"><strong id="sumCompared"></strong><span>matched scenes</span></div>
        <div class="scope-stat"><strong id="sumReduced"></strong><span>reduced to one active zone</span></div>
        <div class="scope-stat"><strong id="sumWhole"></strong><span>returned as one whole frame</span></div>
        <div class="scope-stat"><strong id="sumWords"></strong><span>median image-prompt word change</span></div>
        <div class="scope-stat"><strong id="sumAfterRendered"></strong><span>after-skill image pairs available</span></div>
      </div>
      <div class="scope-flow" aria-label="Updated Build Agent flow">
        <span>record full request</span><i>&rarr;</i>
        <span class="added">scope reduce at end</span><i>&rarr;</i>
        <span>final active-zone prompt</span><i>&rarr;</i>
        <span>Gateway</span><i>&rarr;</i>
        <span>same scoped body to both images</span>
      </div>
      <div class="contrast">
        <h3>Compare &amp; contrast this scene</h3>
        <div class="contrast-grid">
          <div class="contrast-col">
            <h4>What stayed the same</h4>
            <ul id="sameList"></ul>
          </div>
          <div class="contrast-col changed">
            <h4>What changed</h4>
            <ul id="changedList"></ul>
          </div>
        </div>
        <div class="contrast-shapes">
          <div class="old"><b>Before:</b> <span id="beforeShape"></span></div>
          <div class="arrow">&rarr;</div>
          <div class="new"><b>After:</b> <span id="afterShape"></span></div>
        </div>
      </div>
      <div class="render-boundary" id="renderBoundary"></div>
      <div class="compare-grid" id="scopeImageCompare">
        <article class="compare-card before">
          <h3>OLD / NO SKILL &mdash; production isometric</h3>
          <div class="compare-image" id="beforeIsoImage"></div>
        </article>
        <article class="compare-card after">
          <h3 id="afterIsoHeading">NEW / WITH SKILL &mdash; isometric</h3>
          <div class="compare-image" id="afterIsoImage"></div>
        </article>
        <article class="compare-card before">
          <h3>OLD / NO SKILL &mdash; production top-down</h3>
          <div class="compare-image" id="beforeTdImage"></div>
        </article>
        <article class="compare-card after">
          <h3 id="afterTdHeading">NEW / WITH SKILL &mdash; top-down</h3>
          <div class="compare-image" id="afterTdImage"></div>
        </article>
      </div>
      <div class="compare-grid">
        <article class="compare-card before">
          <h3>OLD / NO SKILL &mdash; rendered prompt</h3>
          <pre id="beforePrompt"></pre>
        </article>
        <article class="compare-card after">
          <h3>NEW / WITH SKILL &mdash; final scoped image prompt</h3>
          <pre id="afterPrompt"></pre>
        </article>
        <article class="compare-card before">
          <h3>Before &mdash; scale and pipeline decision</h3>
          <pre id="beforeLedger"></pre>
        </article>
        <article class="compare-card after">
          <h3>After &mdash; full-request scope ledger</h3>
          <pre id="afterLedger"></pre>
        </article>
      </div>
      <div class="compare-warning" id="scopeFailure" hidden></div>
      <details class="compare-detail">
        <summary>Compare complete prose decisions</summary>
        <div class="compare-grid" style="margin-top:10px">
          <article class="compare-card before"><h3>Before &mdash; full prose</h3>
            <pre id="beforeBlob"></pre></article>
          <article class="compare-card after"><h3>After &mdash; full prose</h3>
            <pre id="afterBlob"></pre></article>
        </div>
      </details>
    </section>
    <div class="chart" id="chart">
      <svg class="edges" id="edges" viewBox="0 0 2500 690" preserveAspectRatio="none"></svg>
    </div>
    <div class="legend">
      <p><b>Every arrow is drawn once.</b> The <b>gray</b> arrows are the master graph &mdash; every
      route the pipeline supports. The colored arrows and numbered nodes are <i>this scene's</i>
      actual path. Non-numbered green nodes are the two handoff streams: they carry every scene
      but they are not a step in its route.</p>
    </div>
    <div class="tail">
      <div class="card">
        <h5>Source prompt (as the router saw it, before clarifications)</h5>
        <div class="prompt" id="promptText"></div>
      </div>
      <div class="card">
        <h5>Cursor agent decision &mdash; prose blob</h5>
        <pre id="blobText"></pre>
      </div>
      <div class="card">
        <h5>Gateway output &mdash; strict structured JSON</h5>
        <pre id="specText"></pre>
      </div>
      <div class="card">
        <h5>Addendum injected into iso render</h5>
        <pre id="addendumText"></pre>
      </div>
      <div class="card">
        <h5 id="sentHead">Sent to the image model &mdash; isometric</h5>
        <pre id="isoSent"></pre>
      </div>
      <div class="card">
        <h5>Sent to the image model &mdash; top-down</h5>
        <pre id="tdSent"></pre>
      </div>
    </div>
  </main>
</div>
<div id="lightbox" class="lightbox"><img alt="" /></div>
"""


# Chart geometry lifted from mpalleschi/3D-LayoutBuild-Rules/pipeline-viewer.html.
# Kept as JS so the small placement/edge math stays identical to the source of
# truth for the pipeline drawing.
JS = r"""
const SCENES = __SCENES__;
const VIEWER_AFTER_IMAGE_COUNT = __AFTER_IMAGE_COUNT__;

const HALF_W = 86, HALF_H = 40;

const NODES = {
  prompt:   { x:95,   y:385, tag:"Input",             title:"Prompt",           sub:"user free-text" },
  classify: { x:275,  y:385, tag:"Skill \u00b7 router", title:"Classify",       sub:"genre \u00b7 shape \u00b7 options" },
  ask:      { x:275,  y:220, tag:"Round trip",        title:"Ask the user",     sub:"open questions" },
  genre:    { x:455,  y:385, tag:"Choice",            title:"Genre + shape",    sub:"selected picks" },
  blob:     { x:800,  y:385, tag:"Cursor agent",      title:"Prose decision",   sub:"layout blob \u00b7 never JSON" },
  json:     { x:980,  y:385, tag:"1 Gateway call",    title:"Structured JSON",  sub:"strict layout_spec schema" },
  img:      { x:1160, y:80,  tag:"Spec stream 1",     title:"image_prompt",     sub:"visible geometry" },
  lay:      { x:1370, y:80,  tag:"Spec stream 2",     title:"layout_placement", sub:"triggers, spawns" },
  route:    { x:1160, y:385, tag:"Deterministic",     title:"Route + order",    sub:"agent order · catalogue route" },
  p4:       { x:1330, y:385, tag:"P4 \u00b7 Multi-Zone", title:"Zone graph",    sub:"multi-zone" },
  iso:      { x:1500, y:235, tag:"Image call",        title:"Isometric image",  sub:"whole game" },
  top:      { x:1670, y:235, tag:"Image call",        title:"Top-down",         sub:"projection" },
  elev:     { x:1670, y:385, tag:"P2 \u00b7 Elevation", title:"Elevation layers", sub:"stacked / vertical" },
  params:   { x:1500, y:545, tag:"P6",                title:"Extract params",   sub:"size / laps / spacing" },
  proc:     { x:1670, y:545, tag:"P6",                title:"Procedural gen",   sub:"structural plan" },
  seg:      { x:1840, y:385, tag:"Downstream",        title:"Segmentation",     sub:"mask + JSON provenance" },
  p3:       { x:1840, y:545, tag:"P3 \u00b7 2nd top-down", title:"Interior top-down", sub:"exterior \u2192 interior" },
  p45:      { x:2020, y:235, tag:"Phase 4.5",         title:"Placement",        sub:"onto segmented geometry" },
  build:    { x:2200, y:385, tag:"Phase 5",           title:"3D build + assets", sub:"assemble layout" },
  out:      { x:2380, y:385, tag:"Output",            title:"Playable layout",  sub:"ready" }
};

const BANDS = [
  { x:15,   y:160, w:875, h:320, label:"Build Agent \u2014 intake and Cursor agent prose",
    holds:["prompt","classify","ask","genre","blob"] },
  { x:900,  y:160, w:850, h:455, label:"MapGen \u2014 one strict text call, deterministic assembly, two image calls",
    holds:["json","route","p4","iso","top","elev","params","proc"] },
  { x:1760, y:160, w:720, h:455, label:"Downstream \u2014 segmentation, placement & build",
    holds:["seg","p3","p45","build","out"] }
];

const MASTER_EDGES = [
  ["prompt","classify"],
  ["classify","ask"],["ask","classify"],
  ["ask","genre"],["genre","blob"],["blob","json"],
  ["json","img"],["json","lay"],["json","route"],
  ["img","iso"],["lay","p45"],
  ["route","p4"],["route","iso"],["route","params"],
  ["p4","iso"],["p4","params"],
  ["iso","top"],["iso","elev"],
  ["top","iso"],["elev","iso"],
  ["params","proc"],["proc","top"],["proc","elev"],
  ["top","seg"],["elev","seg"],["iso","seg"],
  ["seg","p3"],["seg","p45"],["p3","p45"],
  ["p45","build"],
  ["build","out"]
];
const STREAM_EDGES = ["json>img","img>iso","json>lay","lay>p45"];

const CAT = {
  prompt:"base", classify:"base", ask:"base", genre:"base",
  blob:"base", json:"base",
  img:"base", lay:"base", route:"base", iso:"base", top:"base",
  seg:"base", p45:"base", build:"base", out:"base",
  params:"variant", proc:"variant",
  p4:"break", elev:"break", p3:"break"
};
const CATCOLOR = { base:"green", variant:"orange", break:"red" };
const RANK = { base:0, variant:1, break:2 };
const RANKCOLOR = ["green","orange","red"];

const MODIFIER_NAMES = {
  P2:"P2 \u00b7 Elevation-Layer Decomposition (BREAKS)",
  P3:"P3 \u00b7 Interior transition \u2014 2 top-downs (BREAKS)",
  P4:"P4 \u00b7 Multi-Zone (BREAKS)",
  P6:"P6 \u00b7 Procedural-First (VARIANT)"
};

function pathFor(s) {
  const has = id => s.modifiers.includes(id);
  const p = ["prompt","classify","ask","genre","blob","json","route"];
  if (has("P4")) p.push("p4");
  const struct = has("P2") ? "elev" : "top";
  if (has("P6")) p.push("params","proc",struct,"iso","seg");
  else           p.push("iso",struct,"seg");
  if (has("P3")) p.push("p3");
  p.push("p45","build","out");
  return p;
}

function boundary(N, tx, ty){
  const dx = tx - N.x, dy = ty - N.y;
  if (Math.abs(dx) * HALF_H >= Math.abs(dy) * HALF_W){
    const sx = Math.sign(dx) || 1;
    return { x:N.x + sx*HALF_W, y:N.y + dy*(HALF_W/Math.abs(dx||1)) };
  } else {
    const sy = Math.sign(dy) || 1;
    return { x:N.x + dx*(HALF_H/Math.abs(dy||1)), y:N.y + sy*HALF_H };
  }
}
function edgePath(a, b){
  const A = NODES[a], B = NODES[b];
  const s = boundary(A, B.x, B.y), e = boundary(B, A.x, A.y);
  const mx = (s.x+e.x)/2, my = (s.y+e.y)/2;
  const dx = e.x-s.x, dy = e.y-s.y, len = Math.hypot(dx,dy) || 1;
  const nx = -dy/len, ny = dx/len;
  const sign = (A.x < B.x || (A.x === B.x && A.y < B.y)) ? 1 : -1;
  const bow = 24 * sign;
  return `M ${s.x} ${s.y} Q ${mx+nx*bow} ${my+ny*bow} ${e.x} ${e.y}`;
}
const ekey = (a,b) => a+">"+b;

const picker  = document.getElementById("picker");
const filt    = document.getElementById("filt");
const genreFilt = document.getElementById("genreFilt");
const pickerCount = document.getElementById("pickerCount");
const chart   = document.getElementById("chart");
const edgesEl = document.getElementById("edges");

// Genre dropdown: "any" plus the distinct answered genres, each with a count.
(function populateGenres(){
  const counts = {};
  SCENES.forEach(s => { counts[s.genre || "(none)"] = (counts[s.genre || "(none)"] || 0) + 1; });
  const names = Object.keys(counts).sort();
  genreFilt.innerHTML =
    `<option value="">any genre (${SCENES.length})</option>` +
    names.map(g => `<option value="${g}">${g} (${counts[g]})</option>`).join("");
})();

function populate(){
  picker.innerHTML = "";
  const q = (filt.value || "").toLowerCase().trim();
  const g = genreFilt.value || "";
  // Scenes are already in P-id order from the Python side; keep that ordering
  // so a flat list scrolls sensibly by scene number, not by genre grouping.
  let shown = 0;
  SCENES.forEach((s, i) => {
    if (g && (s.genre || "(none)") !== g) return;
    if (q){
      const hay = (s.id + " " + (s.genre || "") + " " + s.prompt).toLowerCase();
      if (!hay.includes(q)) return;
    }
    const o = document.createElement("option");
    o.value = i;
    const preview = (s.prompt || "").replace(/\s+/g, " ").slice(0, 70);
    o.textContent = `${s.id} \u00b7 ${s.genre || "(no genre)"} \u2014 ${preview}`;
    picker.appendChild(o);
    shown++;
  });
  pickerCount.textContent = `${shown} of ${SCENES.length} scenes`;
  if (picker.options.length){
    let remembered = "";
    try { remembered = localStorage.getItem("pipeline-viewer-scene") || ""; }
    catch (_) {}
    const rememberedOption = Array.from(picker.options).find(
      option => SCENES[+option.value].id === remembered
    );
    const preview = Array.from(picker.options).find(option => {
      const images = SCENES[+option.value].scope_after_images || {};
      return images.iso || images.td || images.plan;
    });
    picker.value = rememberedOption
      ? rememberedOption.value
      : (preview ? preview.value : picker.options[0].value);
  }
}

const MARKERS = { dim:"var(--dim)", green:"var(--green)", orange:"var(--orange)", red:"var(--red)" };
function defs(){
  return `<defs>${Object.entries(MARKERS).map(([k,col]) =>
    `<marker id="mk-${k}" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto">
       <path d="M0,0 L8,3.2 L0,6.4 Z" fill="${col}"/></marker>`).join("")}</defs>`;
}

function esc(x){ return String(x==null?"":x).replace(/[&<>"']/g,
  c => ({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[c])); }

function words(text){
  return String(text||"").trim().split(/\s+/).filter(Boolean).length;
}
function signedPercent(value){
  if (!Number.isFinite(value)) return "\u2014";
  const rounded = Math.round(value);
  return `${rounded > 0 ? "+" : ""}${rounded}%`;
}
function firstSentence(text, max=280){
  const clean = String(text||"").replace(/\s+/g," ").trim();
  if (!clean) return "(not recorded)";
  const match = clean.match(/^.*?[.!?](?:\s|$)/);
  const sentence = match ? match[0].trim() : clean;
  return sentence.length > max ? sentence.slice(0,max-1)+"\u2026" : sentence;
}
function renderScopeSummary(){
  const compared = SCENES.filter(s => s.scope_after_blob);
  if (!compared.length) return;
  const reduced = compared.filter(s => s.scope_after_fired).length;
  const deltas = compared.map(s => {
    const before = words(s.enriched), after = words(s.scope_after_enriched);
    return before ? 100 * (after-before) / before : NaN;
  }).filter(Number.isFinite).sort((a,b)=>a-b);
  const mid = Math.floor(deltas.length/2);
  const median = deltas.length
    ? (deltas.length%2 ? deltas[mid] : (deltas[mid-1]+deltas[mid])/2)
    : NaN;
  document.getElementById("sumCompared").textContent = compared.length;
  document.getElementById("sumReduced").textContent = reduced;
  document.getElementById("sumWhole").textContent = compared.length-reduced;
  document.getElementById("sumWords").textContent = signedPercent(median);
  document.getElementById("sumAfterRendered").textContent =
    compared.filter(s => {
      const images = s.scope_after_images || {};
      return images.iso && images.td;
    }).length;
}

function optionDetails(list){
  if (!list || !list.length) return "(none)";
  return list.map(o => {
    const meta = [o.id, o.type, o.goes, o.pipeline].filter(Boolean).join(" · ");
    const count = o.count >= 0 ? ` · count ${o.count}` : "";
    const contextual = o.what || "(no scene-specific wording)";
    const catalogue = o.catalogue_what && o.catalogue_what !== contextual
      ? `\n  Catalogue fallback: ${o.catalogue_what}` : "";
    return `${o.label || o.id} (${meta}${count})\n  ${contextual}${catalogue}`;
  }).join("\n\n");
}

function clarificationDetails(s){
  const rows=(s.clarifications&&s.clarifications.length)?s.clarifications:
    (s.answers||[]).map(a=>({...a,source:"author"}));
  if (!rows.length) return "No layout-changing clarification was needed.";
  return rows.map((a,i) =>
    `${i+1}. [${a.source||"author"} · ${a.field||"?"}]\nQ: ${a.ask||""}\nA: ${a.answer||"(empty)"}`
  ).join("\n\n");
}

function axisDetails(s){
  const axes=s.axes_selection||[];
  if (!axes.length) return "(canonical shape supplies the axes)";
  return axes.map(a => {
    const route = a.pipeline ? ` · route ${a.pipeline}` : "";
    const clause = a.clause ? `\n  Prompt clause: ${a.clause}` : "";
    return `${a.label||a.id}: ${a.value}${route}${clause}`;
  }).join("\n");
}

function nodeDetails(id,s){
  const shape=s.shape_selection||{};
  const layout=JSON.stringify(s.layout||{},null,2);
  const placements=JSON.stringify(s.layout_placement||[],null,2);
  const summary=[
    `Genre: ${s.genre||"(none)"}`,
    `Shape: ${shape.label||s.shape_label||s.shape||"described shape"}`,
    `Preset: ${s.preset||"none"}`,
    `Order: ${s.order||"(not recorded)"}`,
    `Route: ${(s.run_route&&s.run_route.length?s.run_route:s.route||[]).join(" + ")||"P0 default"}`
  ].join("\n");
  switch(id){
    case "prompt":
      return s.prompt||"(empty source prompt)";
    case "classify":
      return `${summary}\n\nVisible option picks:\n${optionDetails(s.options_img)}\n\nLayout-only picks:\n${optionDetails(s.options_lay)}`;
    case "ask":
      return clarificationDetails(s);
    case "genre":
      return `${summary}\n\nShape definition:\n${shape.what||"(described directly in the prose decision)"}\n\nAxes:\n${axisDetails(s)}`;
    case "blob":
      return `${s.agent_blob||"(no prose decision recorded)"}\n\nENRICHED IMAGE BODY\n${s.enriched||"(none)"}`;
    case "json":
      return s.structured_json||"(no structured spec recorded)";
    case "img":
      return `VISIBLE IMAGE-PROMPT OPTIONS\n${optionDetails(s.options_img)}\n\nEXACT INJECTED ADDENDUM\n${s.addendum||"(no addendum)"}`;
    case "lay":
      return `LAYOUT-PLACEMENT OPTIONS\n${optionDetails(s.options_lay)}\n\nEXACT PLACEMENT RECORDS\n${placements}`;
    case "route":
      return `${summary}\n\nWhy this order:\n${s.why||s.evidence||"(no rationale recorded)"}\n\nGenre default route: ${s.genre_route||"P0"}`;
    case "p4":
      return `P4 multi-zone layout graph for this scene:\n${layout}`;
    case "iso":
      return s.iso_prompt||"(no isometric prompt recorded)";
    case "top":
      return s.td_prompt||"(no top-down prompt recorded)";
    case "elev":
      return `Elevation-relevant axes:\n${axisDetails(s)}\n\nLayout structure:\n${layout}`;
    case "params":
      return `Parameters are derived deterministically from this selected structure:\n${summary}\n\nShape:\n${JSON.stringify(shape,null,2)}`;
    case "proc":
      return `Authored-plan input for the procedural-first path:\n${summary}\n\nLayout contract:\n${layout}`;
    case "seg":
      return `Segmentation receives the generated image plus this layout contract:\n${layout}`;
    case "p3":
      return `P3 interior-transition inputs:\n${axisDetails(s)}\n\nLayout contract:\n${layout}`;
    case "p45":
      return `Post-segmentation placements:\n${optionDetails(s.options_lay)}\n\nExact records:\n${placements}`;
    case "build":
      return `${summary}\n\nVisible geometry:\n${optionDetails(s.options_img)}\n\nPlaced after segmentation:\n${optionDetails(s.options_lay)}\n\nLayout:\n${layout}`;
    case "out":
      return `${summary}\n\nGenerated artifacts:\n${JSON.stringify(s.images||{},null,2)}`;
    default:
      return summary;
  }
}

function positionHoverDetail(node,detail){
  const margin=12, gap=11;
  detail.style.display="block";
  detail.scrollTop=0;
  detail.style.left="50%";
  detail.style.right="auto";
  detail.style.transform="translateX(-50%)";

  const nodeRect=node.getBoundingClientRect();
  const mainRect=node.closest(".main").getBoundingClientRect();
  const topEdge=Math.max(margin,mainRect.top+margin);
  const bottomEdge=Math.min(window.innerHeight-margin,mainRect.bottom-margin);
  const leftEdge=Math.max(margin,mainRect.left+margin);
  const rightEdge=Math.min(window.innerWidth-margin,mainRect.right-margin);
  const above=Math.max(0,nodeRect.top-topEdge-gap);
  const below=Math.max(0,bottomEdge-nodeRect.bottom-gap);
  const putBelow=below>above;
  detail.style.top=putBelow?`calc(100% + ${gap}px)`:"auto";
  detail.style.bottom=putBelow?"auto":`calc(100% + ${gap}px)`;
  detail.style.maxHeight=`${Math.max(120,putBelow?below:above)}px`;

  const rect=detail.getBoundingClientRect();
  let shift=0;
  if (rect.left<leftEdge) shift=leftEdge-rect.left;
  else if (rect.right>rightEdge) {
    shift=rightEdge-rect.right;
  }
  detail.style.transform=`translateX(calc(-50% + ${shift}px))`;
  detail.style.removeProperty("display");
}

function render(idx){
  const s = SCENES[idx];
  if (!s) return;
  const scopePanel = document.getElementById("scopeCompare");
  const hasScopeComparison = !!s.scope_after_blob;
  scopePanel.style.display = hasScopeComparison ? "block" : "none";
  if (hasScopeComparison){
    const put = (id, value, empty) => {
      const el = document.getElementById(id);
      el.textContent = value || empty;
      el.classList.toggle("empty", !value);
    };
    const putImage = (id, url, alt, empty) => {
      const el = document.getElementById(id);
      el.innerHTML = url
        ? `<img src="${esc(url)}" data-full="${esc(url)}" loading="lazy" alt="${esc(alt)}">`
        : `<span class="empty">${esc(empty)}</span>`;
    };
    const afterImages = s.scope_after_images || {};
    putImage("beforeIsoImage", (s.images||{}).iso, `${s.id} old production isometric`,
             "No pre-skill production isometric is available.");
    putImage("afterIsoImage", afterImages.iso, `${s.id} new scoped isometric preview`,
             "No after-skill isometric preview has been rendered for this scene.");
    putImage("beforeTdImage", (s.images||{}).td, `${s.id} old production top-down`,
             "No pre-skill production top-down is available.");
    putImage("afterTdImage", afterImages.td, `${s.id} new scoped top-down preview`,
             "No after-skill top-down preview has been rendered for this scene.");
    const hasAfterPreview = !!(afterImages.iso || afterImages.td || afterImages.plan);
    const isProductionAfter = s.scope_after_image_status === "production";
    document.getElementById("afterIsoHeading").textContent = isProductionAfter
      ? "NEW / WITH SKILL — Gateway-transcribed production isometric"
      : "NEW / WITH SKILL — prompt-only isometric preview";
    document.getElementById("afterTdHeading").textContent = isProductionAfter
      ? "NEW / WITH SKILL — Gateway-transcribed production top-down"
      : "NEW / WITH SKILL — prompt-only top-down preview";
    document.getElementById("renderBoundary").textContent = hasAfterPreview
      ? (isProductionAfter
          ? "The right-side images are production renders generated after Gateway transcription. Every “sent to image model” prompt below remains from the OLD production run until the after-run prompt evidence is added."
          : "The right-side images are direct prompt-only previews of the final scoped prompt. They are not Gateway-transcribed production output. Every “sent to image model” prompt below remains from the OLD production run.")
      : "No after-skill preview exists for this scene yet. Every rendered image and “sent to image model” prompt shown here belongs to the OLD, pre-skill production run.";
    put("beforePrompt", s.enriched,
        "No enriched image prompt was recorded in the pre-skill spec.");
    put("afterPrompt", s.scope_after_enriched,
        "No enriched image prompt was found in the after-skill prose.");
    put("beforeLedger", s.before_ledger,
        "No explicit scope ledger existed before the skill.");
    put("afterLedger", s.scope_after_ledger,
        "No scope ledger was found in the after-skill prose.");
    put("beforeBlob", s.agent_blob, "No pre-skill prose was recorded.");
    put("afterBlob", s.scope_after_blob, "No after-skill prose was recorded.");

    const status = document.getElementById("scopeStatus");
    const failure = document.getElementById("scopeFailure");
    if (s.scope_after_failure){
      status.className = "scope-status fail";
      status.textContent = "known semantic failure";
      failure.hidden = false;
      failure.textContent = `Blocked: ${s.scope_after_failure}`;
    } else {
      status.className = "scope-status";
      status.textContent = "structurally valid · semantic audit not exhaustive";
      failure.hidden = true;
      failure.textContent = "";
    }
    const runBits = [s.scope_after_run, s.scope_after_version].filter(Boolean);
    status.title = runBits.join(" · ");

    const beforeWords = words(s.enriched);
    const afterWords = words(s.scope_after_enriched);
    const delta = beforeWords ? 100 * (afterWords-beforeWords) / beforeWords : NaN;
    const same = [
      "Same original author prompt and intake answers.",
      s.scope_after_genre && s.genre
        && s.scope_after_genre.toLowerCase().includes(String(s.genre).toLowerCase())
        ? `Dominant genre remains ${s.genre}.`
        : "Full-request classification remains visible in the after decision.",
      "Same shape and option catalogue; only the scope stage is newly inserted."
    ];
    const changed = [
      s.scope_after_fired
        ? "The new skill split the full request and selected one active buildable zone."
        : "The new skill assessed the request and returned it as one whole frame.",
      `Image-ready prose changed from ${beforeWords} to ${afterWords} words (${signedPercent(delta)}).`,
      s.scope_after_fired
        ? "Deferred zones remain in the scope ledger instead of the active image prompt."
        : "Any wording differences come from the fresh decision run, not a scope cut.",
      hasAfterPreview
        ? (isProductionAfter
            ? "Both sides have production render evidence; the right side uses the final scoped prompt after Gateway transcription."
            : "Before is production evidence; after has prompt-only preview images, but no Gateway-transcribed production evidence.")
        : "Before has production spec/render evidence; after remains prose-only until transcription and rendering."
    ];
    document.getElementById("sameList").innerHTML =
      same.map(item=>`<li>${esc(item)}</li>`).join("");
    document.getElementById("changedList").innerHTML =
      changed.map(item=>`<li>${esc(item)}</li>`).join("");
    const oldShape = s.shape_label
      ? `${s.shape_label} (${s.shape})`
      : (s.shape || "(not recorded)");
    document.getElementById("beforeShape").textContent =
      `${oldShape}; route ${(s.route||[]).join(" + ") || "P0"}`;
    document.getElementById("afterShape").textContent =
      firstSentence(s.scope_after_shape);
  }
  const path = pathFor(s);
  const onPath = new Set(path);
  const isP6 = s.modifiers.includes("P6");
  const isTiered = !!s.tiered;
  const hasBreak = ["P2","P3","P4"].some(m => s.modifiers.includes(m));

  // sidebar verdict
  const badge = document.getElementById("verdictBadge");
  if (hasBreak){ badge.className="badge b-red"; badge.textContent="\u2717 Breaks current pipeline"; }
  else if (isP6){ badge.className="badge b-orange"; badge.textContent="\u25c6 P6 variant \u2014 procedural first"; }
  else if (isTiered){ badge.className="badge b-orange"; badge.textContent="\u25c6 Tiered flag \u2014 elevation capture"; }
  else { badge.className="badge b-green"; badge.textContent="\u2714 Fits current pipeline"; }
  const shape = s.shape_label || s.shape || "";
  document.getElementById("sceneTitle").textContent =
    `${s.id} \u00b7 ${s.genre}${shape ? " \u00b7 " + shape : ""}`;
  const bits = [];
  if (s.preset && s.preset !== "none") bits.push(`preset: ${s.preset}`);
  if (s.confidence) bits.push(`confidence: ${s.confidence}`);
  if (s.evidence) bits.push(`evidence: ${s.evidence}`);
  document.getElementById("sceneSub").innerHTML = bits.map(esc).join("<br>");

  // chips: modifiers + special flags
  const chipEl = document.getElementById("chips"); chipEl.innerHTML = "";
  const addChip = (label, cls, title) => {
    const c = document.createElement("span");
    c.className = "chip" + (cls ? " " + cls : "");
    c.textContent = label; if (title) c.title = title;
    chipEl.appendChild(c);
  };
  if (!s.modifiers.length && !isTiered) addChip("current path", "green", "no deviations \u2014 prompt \u2192 iso \u2192 top-down \u2192 layout");
  s.modifiers.forEach(m => {
    const catNode = m==="P2"?"elev":m==="P3"?"p3":m==="P4"?"p4":"proc";
    addChip(m, CATCOLOR[CAT[catNode]], MODIFIER_NAMES[m]);
  });
  if (isTiered) addChip("tiered", "orange", "relief captured, not overhang");
  if (s.check) addChip("CHECK", "", "volumetric play-space \u2014 verify framing");
  if (s.set_piece) addChip("SET", "", "space is looked at, not walked through");

  // Q&A
  const qaEl = document.getElementById("qa");
  qaEl.innerHTML = "";
  const resolved=(s.clarifications&&s.clarifications.length)?s.clarifications:
    (s.answers||[]).map(a=>({...a,source:"author"}));
  if (resolved.length){
    resolved.forEach(a => {
      const div = document.createElement("div");
      div.className = "qi";
      div.innerHTML = `<span class="field">[${esc(a.source||"author")} · ${esc(a.field||"?")}]</span>` +
                      `<span class="q">${esc(a.ask||"")}</span>` +
                      `<div class="a">${esc(a.answer||"(empty)")}</div>`;
      qaEl.appendChild(div);
    });
  } else {
    qaEl.innerHTML = '<div class="qi" style="color:var(--muted);font-style:italic">' +
                     'no layout-changing clarification was needed</div>';
  }

  // Handoff option lanes
  const renderLane = (list, kind) => {
    if (!list.length) return `<div class="none">no ${kind} options for this scene</div>`;
    return "<ul>" + list.map(o =>
      `<li><b>${esc(o.label)}</b> <i>\u2014 ${esc(o.what || "")}</i></li>`).join("") + "</ul>";
  };
  document.getElementById("optImg").innerHTML = renderLane(s.options_img, "image_prompt");
  document.getElementById("optLay").innerHTML = renderLane(s.options_lay, "layout_placement");

  // Eval checklist: each visible feature as a checkbox row with origin + notes + quote.
  const clEl = document.getElementById("checklist");
  const exEl = document.getElementById("excluded");
  const feats = (s.checklist && s.checklist.features) || [];
  const excl  = (s.checklist && s.checklist.excluded) || [];
  clEl.innerHTML = feats.length
    ? feats.map(f => {
        const oc = f.origin === "prompt" ? "p" : "a";
        const notes = f.notes ? `<div class="notes">${esc(f.notes)}</div>` : "";
        const quote = f.quote ? `<div class="quote">${esc(f.quote)}</div>` : "";
        return `<li>
          <span class="tick ${oc}" title="${f.origin}"></span>
          <div>
            <span class="name">${esc(f.name)}</span>
            <span class="origin ${oc}">${esc(f.origin || "?")}</span>
            ${notes}${quote}
          </div>
        </li>`;
      }).join("")
    : `<li style="color:var(--muted);font-style:italic;padding-top:4px">
         no checklist yet - run <code>tools/extract_checklist.py --only ${s.id}</code>
       </li>`;
  exEl.innerHTML = excl.length
    ? excl.map(x => `<li><span class="name">${esc(x.name)}</span>
        <span class="why">${esc(x.why || "")}</span></li>`).join("")
    : `<li style="font-style:italic;padding-top:4px">nothing excluded</li>`;

  // Tail cards: source -> agent prose -> strict JSON -> assembled image prompts.
  document.getElementById("promptText").textContent = s.prompt || "";
  document.getElementById("blobText").textContent =
    s.agent_blob || "(no prose decision recorded)";
  document.getElementById("specText").textContent =
    s.structured_json || "(no structured spec recorded)";
  document.getElementById("addendumText").textContent = s.addendum || "(no addendum \u2014 no options picked)";
  // Which image was drawn from text and which was converted from the other, since the
  // same two prompts mean different things depending on the order.
  const FIRST = {std:"isometric drawn from text first, top-down converted from it",
                 p6:"top-down drawn from text first, isometric dressed from it",
                 layout:"authored plan first, then top-down, then isometric"};
  document.getElementById("sentHead").textContent =
    "Sent to the image model \u2014 isometric" +
    (FIRST[s.order] ? "  (" + FIRST[s.order] + ")" : "");
  document.getElementById("isoSent").textContent =
    s.iso_prompt || "(nothing recorded \u2014 this scene has no run row)";
  document.getElementById("tdSent").textContent =
    s.td_prompt || "(nothing recorded \u2014 this scene has no run row)";

  // Chart: edges
  const activeEdge = {};
  for (let i=0; i<path.length-1; i++){
    const a=path[i], b=path[i+1];
    activeEdge[ekey(a,b)] = RANKCOLOR[Math.max(RANK[CAT[a]], RANK[CAT[b]])];
  }
  STREAM_EDGES.forEach(k => activeEdge[k] = "green");

  let svg = defs();
  svg += "<g>";
  MASTER_EDGES.forEach(([a,b]) => {
    svg += `<path d="${edgePath(a,b)}" fill="none" stroke="var(--dim)" stroke-width="1.5" opacity="0.4" marker-end="url(#mk-dim)"/>`;
  });
  svg += "</g><g>";
  Object.entries(activeEdge).forEach(([k,col]) => {
    const [a,b] = k.split(">");
    const dash = STREAM_EDGES.includes(k) ? ' stroke-dasharray="7 5"' : "";
    svg += `<path d="${edgePath(a,b)}" fill="none" stroke="var(--${col})" stroke-width="3"${dash} marker-end="url(#mk-${col})"/>`;
  });
  svg += "</g>";
  edgesEl.innerHTML = svg;

  // Bands
  chart.querySelectorAll(".band").forEach(b => b.remove());
  BANDS.forEach(B => {
    const d = document.createElement("div");
    d.className = "band";
    d.style.left = B.x+"px"; d.style.top = B.y+"px";
    d.style.width = B.w+"px"; d.style.height = B.h+"px";
    d.innerHTML = `<span>${B.label}</span>`;
    chart.appendChild(d);
  });

  // Nodes with per-scene content
  chart.querySelectorAll(".node").forEach(n => n.remove());
  const order = {}; path.forEach((id,i) => order[id] = i+1);
  Object.entries(NODES).forEach(([id,N]) => {
    const div = document.createElement("div");
    let col = CATCOLOR[CAT[id]];
    const isStream = id === "img" || id === "lay";
    div.className = "node " + (isStream ? "n-green n-stream"
                              : onPath.has(id) ? ("n-"+col+" on") : "n-dim");
    div.tabIndex = 0;
    div.style.left = N.x + "px"; div.style.top = N.y + "px";

    // Per-scene subtitle: for the nodes that carry this scene's actual input.
    let sub = N.sub;
    let extra = "";
    if (id === "prompt"){
      const preview = (s.prompt||"").replace(/\s+/g," ").slice(0,90);
      sub = `${s.id}`;
      extra = `<div class="brief">${esc(preview + ((s.prompt||"").length>90?"\u2026":""))}</div>`;
    } else if (id === "classify"){
      sub = `picked ${s.genre || "(none)"}`;
    } else if (id === "ask"){
      const n = (s.answers||[]).length;
      sub = n ? `${n} question${n===1?"":"s"} answered` : "nothing to ask";
    } else if (id === "genre"){
      const preset = (s.preset && s.preset !== "none") ? ` \u00b7 ${s.preset}` : "";
      sub = `${s.genre}${preset}`;
      if (s.shape_label) extra = `<div class="brief">shape: ${esc(s.shape_label)}</div>`;
    } else if (id === "blob"){
      const n = (s.agent_blob||"").length;
      sub = `${n.toLocaleString()} chars \u00b7 prose`;
      const preview = (s.agent_blob||"").replace(/\s+/g," ").slice(0,90);
      if (preview) extra = `<div class="brief">${esc(preview + ((s.agent_blob||"").length>90?"\u2026":""))}</div>`;
    } else if (id === "json"){
      const ni = (s.options_img||[]).length, nl = (s.options_lay||[]).length;
      sub = `strict schema \u00b7 ${ni} image \u00b7 ${nl} layout`;
    } else if (id === "img"){
      const ni = (s.options_img||[]).length;
      sub = ni ? `${ni} pick${ni===1?"":"s"} \u2192 iso addendum` : "no picks (scene has no visible options)";
    } else if (id === "lay"){
      const nl = (s.options_lay||[]).length;
      sub = nl ? `${nl} pick${nl===1?"":"s"} \u2192 phase 4.5` : "no invisible picks";
    } else if (id === "route"){
      const mods = s.modifiers.length ? s.modifiers.join(" + ") : "P0 default";
      sub = `route: ${mods}`;
    } else if (id === "iso" && s.images.iso){
      sub = "generated";
      extra = `<div class="thumb"><img src="${s.images.iso}" data-full="${s.images.iso}" loading="lazy" alt="iso"></div>`;
    } else if (id === "top" && s.images.td){
      sub = "generated";
      extra = `<div class="thumb"><img src="${s.images.td}" data-full="${s.images.td}" loading="lazy" alt="td"></div>`;
    } else if (id === "proc" && s.images.plan){
      sub = "authored plan";
      extra = `<div class="thumb"><img src="${s.images.plan}" data-full="${s.images.plan}" loading="lazy" alt="plan"></div>`;
    }

    div.innerHTML = `<span class="step">${order[id]||""}</span>` +
                    `<span class="tag">${N.tag}</span>` +
                    `<span class="title">${N.title}</span>` +
                    `<span class="sub">${sub}</span>` + extra;
    const detail = document.createElement("div");
    detail.className = "hover-detail";
    const head = document.createElement("div");
    head.className = "hover-head";
    head.textContent = `${onPath.has(id)||isStream?"Active":"Not used"} · ${N.title} · full relevant text`;
    const body = document.createElement("pre");
    body.textContent = nodeDetails(id,s);
    detail.appendChild(head);
    detail.appendChild(body);
    div.appendChild(detail);
    div.addEventListener("mouseenter",()=>positionHoverDetail(div,detail));
    div.addEventListener("focus",()=>positionHoverDetail(div,detail));
    chart.appendChild(div);
  });
}

picker.addEventListener("change", e => {
  const scene = SCENES[+e.target.value];
  try {
    if (scene) localStorage.setItem("pipeline-viewer-scene", scene.id);
  } catch (_) {}
  render(+e.target.value);
});
function refresh(){
  populate();
  if (picker.options.length) render(+picker.value);
}
filt.addEventListener("input", refresh);
genreFilt.addEventListener("change", refresh);

// Lightbox
const lb = document.getElementById("lightbox");
const lbImg = lb.querySelector("img");
document.addEventListener("click", e => {
  const t = e.target;
  if (t && t.tagName === "IMG" && t.dataset.full){
    lbImg.src = t.dataset.full; lb.classList.add("open");
  } else if (t === lb || (t.tagName === "IMG" && t.parentElement === lb)){
    lb.classList.remove("open"); lbImg.src = "";
  }
});
document.addEventListener("keydown", e => {
  if (e.key === "Escape"){ lb.classList.remove("open"); lbImg.src = ""; }
});

populate();
renderScopeSummary();
if (picker.options.length) render(+picker.value);

// The batch runner rewrites this page as image pairs finish. Reload only when a
// newer build exposes more images, retaining the selected scene through localStorage.
if (VIEWER_AFTER_IMAGE_COUNT < SCENES.filter(s => s.scope_after_blob).length){
  setInterval(async () => {
    try {
      const response = await fetch(location.href, {cache:"no-store"});
      const text = await response.text();
      const match = text.match(/const VIEWER_AFTER_IMAGE_COUNT = (\d+);/);
      if (match && Number(match[1]) > VIEWER_AFTER_IMAGE_COUNT) location.reload();
    } catch (_) {}
  }, 30000);
}
"""


def build_page(rows: list[dict]) -> str:
    after_image_count = sum(
        bool((row.get("scope_after_images") or {}).get("iso"))
        and bool((row.get("scope_after_images") or {}).get("td"))
        for row in rows
    )
    js = (
        JS.replace("__SCENES__", json.dumps(rows))
        .replace("__AFTER_IMAGE_COUNT__", str(after_image_count))
    )
    header = (
        SCOPE_HEADER_HTML
        if any(row.get("scope_after_blob") for row in rows)
        else HEADER_HTML
    )
    return (f"<!doctype html>\n<html><head><meta charset=\"utf-8\">"
            f"<title>Pipeline viewer</title>\n<style>{CSS}</style></head>\n"
            f"<body>{header}{BODY_HTML}\n<script>{js}</script></body></html>\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path,
                    default=RESULTS / "pipeline_viewer.html")
    ap.add_argument("--run-name", default="agent_gateway",
                    help="results/runs/<name>.jsonl to visualize")
    ap.add_argument("--image-arm", default="agent_gateway_260813",
                    help="results/scenes/<arm> containing rendered images")
    ap.add_argument("--only-sent", action="store_true",
                    help="show only scenes present in the selected run")
    ap.add_argument("--checklist-dir", type=pathlib.Path, default=EVAL,
                    help="directory containing per-scene eval checklists")
    ap.add_argument(
        "--scope-after-dir",
        type=pathlib.Path,
        help="fresh skill-run prose directory to compare with production",
    )
    ap.add_argument(
        "--scope-after-manifest",
        type=pathlib.Path,
        help="manifest carrying run provenance and known validation failures",
    )
    ap.add_argument(
        "--scope-after-image-dir",
        type=pathlib.Path,
        help=(
            "optional results/scenes directory containing prompt-only "
            "after-skill previews"
        ),
    )
    ap.add_argument(
        "--scope-after-image-status",
        choices=("prompt-only", "production"),
        default="prompt-only",
        help="provenance label for after-skill images",
    )
    ap.add_argument(
        "--only-scope-compared",
        action="store_true",
        help="show only scenes that have an after-skill prose artifact",
    )
    args = ap.parse_args()
    rows = collect(
        args.run_name,
        args.image_arm,
        only_sent=args.only_sent,
        checklist_dir=args.checklist_dir,
        scope_after_dir=args.scope_after_dir,
        scope_after_manifest=args.scope_after_manifest,
        scope_after_image_dir=args.scope_after_image_dir,
        scope_after_image_status=args.scope_after_image_status,
        only_scope_compared=args.only_scope_compared,
    )
    text = build_page(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    kb = len(text) // 1024
    print(f"wrote {args.out}  ({len(rows)} scenes, {kb} KB)")
    print(f"served at http://localhost:8889/pipeline "
          f"or file://{args.out.resolve()}")


if __name__ == "__main__":
    main()
