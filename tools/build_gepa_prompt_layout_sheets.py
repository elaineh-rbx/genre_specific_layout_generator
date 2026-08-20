"""Build printable prompt/reference/GEPA comparison sheets for the golden 75."""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import shutil

from layoutgen import assets, paths
from PIL import Image, ImageDraw, ImageOps
from layoutgen.optimize.gepa_600 import (
    DEFAULT_MANIFEST,
    TARGET_ARM,
    load_exact_cases,
)
from layoutgen.optimize.gepa_images import TargetStore, _candidate_id, _write_json
from layoutgen.pipeline import golden


DEFAULT_RUN = (
    paths.RUN / "gepa" / "gemini_gepa_upstream600_golden75_full_v1_260819"
)
DEFAULT_OUTPUT = (
    paths.RESULTS
    / "gepa"
    / "gemini_gepa_upstream600_golden75_full_v1_260819"
)
MODEL_RUNS = {
    "qwen": (
        "Qwen Prompt/Layout GEPA",
        "qwen_pipeline_gepa_vlm_gpt55_all75_eval_v1_260817",
    ),
    "flux": (
        "FLUX Prompt/Layout GEPA",
        "flux_gepa_vlm_gpt55_all75_eval_v1_260817",
    ),
    "zimage": (
        "Z-Image Prompt/Layout GEPA",
        "zimage_gepa_vlm_gpt55_std45_v1_260817",
    ),
}


def _score_map(path: pathlib.Path) -> dict[str, dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {str(row["scene"]): row for row in rows}


def _metrics(row: dict) -> dict[str, float]:
    feedback = row.get("feedback") or {}
    scores = feedback.get("scores") or {}
    return {
        "objective": float(row.get("score", scores.get("combined_objective", 0.0))),
        "prompt": float(scores.get("prompt_adherence", 0.0)),
        "layout": float(scores.get("layout_following", 0.0)),
        "camera": float(scores.get("isometric_camera", 0.0)),
        "image": float(
            scores.get(
                "perceptual_similarity",
                scores.get("isometric_similarity", 0.0),
            )
        ),
    }


def _manifest_rows(path: pathlib.Path) -> dict[str, dict]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return {str(row["scene"]): row for row in manifest.get("scenes", [])}


def _figure(
    scene: str,
    asset: str,
    label: str,
    objective: float | None = None,
    available: bool = True,
) -> str:
    score = (
        f'<span class="score">Objective {objective:.3f}</span>'
        if objective is not None
        else ""
    )
    content = (
        f'<img loading="lazy" src="{html.escape(asset, quote=True)}" '
        f'alt="{html.escape(label)} for scene {scene}">'
        if available
        else (
            '<div class="missing">Not evaluated for this reference-conditioned '
            "scene</div>"
        )
    )
    return f"""
    <figure class="{'available' if available else 'unavailable'}">
      {content}
      <figcaption><span>{html.escape(label)}</span>{score}</figcaption>
    </figure>"""


def _sheet(scene: str, order: str, figures: list[str]) -> str:
    searchable = html.escape(f"{scene} {order}".lower(), quote=True)
    return f"""
<article class="sheet" id="scene-{scene}" data-search="{searchable}">
  <header>
    <div>
      <div class="eyebrow">Golden scene {scene} · {html.escape(order)}</div>
      <h2>GPT reference vs Prompt/Layout GEPA models</h2>
    </div>
    <a href="#scene-{scene}">#{scene}</a>
  </header>
  <div class="images">{''.join(figures)}</div>
</article>
"""


def _grid_image(
    entries: list[tuple[str, pathlib.Path | None, float | None]],
    destination: pathlib.Path,
) -> pathlib.Path:
    tile, caption = 512, 58
    canvas = Image.new("RGB", (tile * len(entries), tile + caption), "#090b10")
    draw = ImageDraw.Draw(canvas)
    for index, (label, source, objective) in enumerate(entries):
        left = index * tile
        if source is not None:
            with Image.open(source) as opened:
                image = ImageOps.contain(
                    opened.convert("RGB"),
                    (tile, tile),
                    Image.Resampling.LANCZOS,
                )
            x = left + (tile - image.width) // 2
            y = (tile - image.height) // 2
            canvas.paste(image, (x, y))
        else:
            draw.rectangle(
                (left, 0, left + tile - 1, tile - 1),
                fill="#111722",
                outline="#293142",
                width=2,
            )
            draw.text(
                (left + tile // 2, tile // 2),
                "Not evaluated",
                fill="#9ba7bb",
                anchor="mm",
            )
        score = f" · {objective:.3f}" if objective is not None else ""
        draw.text(
            (left + 12, tile + 18),
            f"{label}{score}",
            fill="#eef3fb",
        )
        if index:
            draw.line((left, 0, left, tile + caption), fill="#293142", width=2)
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="JPEG", quality=91, optimize=True)
    return destination


def _page(sheets: list[str], run_name: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GPT Reference vs Prompt/Layout GEPA Models</title>
<style>
:root {{ color-scheme: dark; --bg:#090b10; --card:#11151d; --line:#293142;
  --muted:#9ba7bb; --accent:#86b7ff; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:#eef3fb;
  font:14px/1.45 Inter,ui-sans-serif,system-ui,sans-serif; }}
.toolbar {{ position:sticky; top:0; z-index:5; display:flex; gap:16px;
  align-items:center; padding:14px 22px; background:#090b10ee;
  border-bottom:1px solid var(--line); backdrop-filter:blur(10px); }}
.toolbar h1 {{ margin:0; font-size:18px; white-space:nowrap; }}
.toolbar input {{ width:min(520px,55vw); border:1px solid var(--line);
  background:#121722; color:white; border-radius:8px; padding:9px 12px; }}
.toolbar .meta {{ color:var(--muted); margin-left:auto; }}
main {{ max-width:1520px; margin:auto; padding:22px; }}
.sheet {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
  padding:20px; margin:0 0 24px; box-shadow:0 8px 30px #0005; }}
.sheet header {{ display:flex; justify-content:space-between; gap:20px;
  align-items:start; }}
.sheet header a {{ color:var(--accent); text-decoration:none; font-weight:700; }}
.eyebrow {{ color:var(--accent); font-size:12px; font-weight:700;
  letter-spacing:.06em; text-transform:uppercase; }}
h2 {{ margin:4px 0 12px; font-size:19px; }}
.images {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; }}
figure {{ margin:0; border:1px solid var(--line); border-radius:10px;
  overflow:hidden; background:#080a0f; }}
figure img {{ display:block; width:100%; aspect-ratio:1; object-fit:contain; }}
figcaption {{ display:flex; justify-content:space-between; gap:10px; padding:9px 12px;
  border-top:1px solid var(--line); color:#d8e2f1; font-weight:700; }}
.score {{ color:var(--muted); font-size:12px; white-space:nowrap; }}
.missing {{ display:grid; place-items:center; width:100%; aspect-ratio:1;
  padding:24px; text-align:center; color:var(--muted);
  background:repeating-linear-gradient(135deg,#0c1017,#0c1017 12px,#101620 12px,#101620 24px); }}
.hidden {{ display:none; }}
@media(max-width:760px) {{
  .toolbar {{ flex-wrap:wrap; }}
  .toolbar input {{ width:100%; order:3; }}
  .images {{ grid-template-columns:1fr; }}
  main {{ padding:12px; }}
}}
@media print {{
  :root {{ color-scheme:light; }}
  body {{ background:white; color:black; }}
  .toolbar {{ display:none; }}
  main {{ max-width:none; padding:0; }}
  .sheet {{ break-after:page; box-shadow:none; border:0; margin:0; padding:12mm; }}
  .images {{ gap:8mm; }}
  figure {{ border-color:#bbb; }}
}}
</style>
</head>
<body>
<div class="toolbar">
  <h1>Prompt/Layout GEPA model sheets</h1>
  <input id="search" type="search" placeholder="Filter by scene or render order…">
  <div class="meta">75 scenes · {html.escape(run_name)}</div>
</div>
<main>{''.join(sheets)}</main>
<script>
const input=document.querySelector('#search');
input.addEventListener('input',()=>{{
  const q=input.value.trim().toLowerCase();
  document.querySelectorAll('.sheet').forEach(sheet=>{{
    sheet.classList.toggle('hidden',q&&!sheet.dataset.search.includes(q));
  }});
}});
</script>
</body>
</html>
"""


def build(
    run_root: pathlib.Path,
    output: pathlib.Path,
    specs: pathlib.Path,
    source_manifest: pathlib.Path,
    target_arm: str,
) -> pathlib.Path:
    candidate_path = run_root / "best_candidate.json"
    scores_path = run_root / "golden75_scores.json"
    if not candidate_path.is_file() or not scores_path.is_file():
        raise FileNotFoundError(
            "run is incomplete; expected best_candidate.json and golden75_scores.json"
        )
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    score_rows = _score_map(scores_path)
    cases = load_exact_cases(specs, source_manifest)
    scenes = [f"{index:04d}" for index in range(1, 76)]
    missing = [scene for scene in scenes if scene not in score_rows or scene not in cases]
    if missing:
        raise ValueError(f"missing golden scenes: {', '.join(missing)}")

    gpt_assets = output / "assets" / "gpt"
    gemini_assets = output / "assets" / "gemini"
    model_assets = {
        slug: output / "assets" / slug
        for slug in MODEL_RUNS
    }
    grid_assets = output / "grids"
    gpt_assets.mkdir(parents=True, exist_ok=True)
    gemini_assets.mkdir(parents=True, exist_ok=True)
    for directory in model_assets.values():
        directory.mkdir(parents=True, exist_ok=True)
    model_rows = {
        slug: _manifest_rows(paths.RUN / "gepa" / run_name / "s3_manifest.json")
        for slug, (_, run_name) in MODEL_RUNS.items()
    }
    targets = TargetStore(target_arm)
    sheets = []
    manifest_rows = []
    for scene in scenes:
        case = cases[scene]
        candidate_id = _candidate_id(candidate, case)
        gemini_source = run_root / "renders" / candidate_id / scene / "iso.jpg"
        if not gemini_source.is_file():
            raise FileNotFoundError(f"missing Gemini winner render: {gemini_source}")
        gpt_source = targets.get(scene, "iso")
        gpt_destination = gpt_assets / f"{scene}.png"
        gemini_destination = gemini_assets / f"{scene}.jpg"
        shutil.copy2(gpt_source, gpt_destination)
        shutil.copy2(gemini_source, gemini_destination)
        metrics = _metrics(score_rows[scene])
        figures = [
            _figure(
                scene,
                f"assets/gpt/{scene}.png",
                "GPT Image 2 reference",
            ),
            _figure(
                scene,
                f"assets/gemini/{scene}.jpg",
                "Gemini Prompt/Layout GEPA",
                metrics["objective"],
            ),
        ]
        grid_entries: list[tuple[str, pathlib.Path | None, float | None]] = [
            ("GPT Image 2", gpt_destination, None),
            ("Gemini", gemini_destination, metrics["objective"]),
        ]
        model_manifest_rows = {}
        for slug, (label, run_name) in MODEL_RUNS.items():
            model_row = model_rows[slug].get(scene)
            source = assets.fetch(
                f"gepa/{run_name}/images/isometric/{scene}.jpg"
            )
            available = model_row is not None and source is not None
            objective = (
                float((model_row.get("scores") or {}).get("combined_objective", 0.0))
                if model_row
                else None
            )
            destination = model_assets[slug] / f"{scene}.jpg"
            if available:
                assert source is not None
                shutil.copy2(source, destination)
            figures.append(
                _figure(
                    scene,
                    f"assets/{slug}/{scene}.jpg",
                    label,
                    objective,
                    available,
                )
            )
            grid_entries.append(
                (
                    label.removesuffix(" Prompt/Layout GEPA"),
                    destination if available else None,
                    objective,
                )
            )
            model_manifest_rows[slug] = {
                "available": available,
                "image": (
                    str(destination.relative_to(output))
                    if available
                    else None
                ),
                "objective": objective,
                "source_run": run_name,
            }
        sheets.append(
            _sheet(scene, case.order, figures)
        )
        grid_destination = _grid_image(
            grid_entries,
            grid_assets / f"{scene}.jpg",
        )
        manifest_rows.append(
            {
                "scene": scene,
                "order": case.order,
                "gpt_reference": str(gpt_destination.relative_to(output)),
                "gemini_gepa": str(gemini_destination.relative_to(output)),
                "grid": str(grid_destination.relative_to(output)),
                "gemini_metrics": metrics,
                "other_models": model_manifest_rows,
            }
        )

    output.mkdir(parents=True, exist_ok=True)
    destination = output / "comparison_sheets.html"
    destination.write_text(
        _page(sheets, run_root.name),
        encoding="utf-8",
    )
    _write_json(
        output / "manifest.json",
        {
            "source_run": str(run_root),
            "target_arm": target_arm,
            "candidate": candidate,
            "scenes": manifest_rows,
        },
    )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=pathlib.Path, default=DEFAULT_RUN)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--specs", type=pathlib.Path, default=golden.AGENT_GATEWAY)
    parser.add_argument(
        "--source-manifest",
        type=pathlib.Path,
        default=DEFAULT_MANIFEST,
    )
    parser.add_argument("--target-arm", default=TARGET_ARM)
    args = parser.parse_args()
    destination = build(
        args.run_root,
        args.output,
        args.specs,
        args.source_manifest,
        args.target_arm,
    )
    print(f"wrote {destination}")


if __name__ == "__main__":
    main()
