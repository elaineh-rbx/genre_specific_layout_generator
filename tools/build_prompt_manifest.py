"""Write an auditable manifest of the exact prompts sent to the image model.

The render ``run.jsonl`` also retains these prompts, but it mixes them with image
filenames, timings, and layout metadata. This projection gives each corpus a compact,
stable prompt record with the enriched JSON field, canonical addendum, exact final
payloads, reference-image provenance, and hashes.

Usage:
    python tools/build_prompt_manifest.py \
      --run-name agent_gateway_gpt55_enriched_260814
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen import paths  # noqa: E402
from layoutgen.backends import images  # noqa: E402


REFERENCES = {
    "std": {"isometric": None, "topdown": "isometric"},
    "p6": {"isometric": "topdown", "topdown": None},
    "layout": {"isometric": "topdown", "topdown": "authored_plan"},
}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build(run_name: str) -> list[dict]:
    run_path = paths.RUNS / f"{run_name}.jsonl"
    specs = paths.ROUTING / "agent_spec_gateway"
    records = []
    for line in run_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        scene = row["scene"]
        transcription = json.loads(
            (specs / f"{scene}.json").read_text(encoding="utf-8")
        )
        spec = transcription["spec"]
        enriched = (spec.get("initial_scene_subprompt_enriched") or "").strip()
        if not enriched:
            raise ValueError(
                f"{scene}: missing initial_scene_subprompt_enriched in strict spec"
            )
        iso_prompt = row.get("iso_prompt") or ""
        td_prompt = row.get("td_prompt") or ""
        order = row.get("order") or "std"
        references = REFERENCES[order]
        records.append(
            {
                "manifest_version": 1,
                "scene": scene,
                "title": row.get("title") or "",
                "genre": row.get("genre") or "",
                "preset": row.get("preset") or "none",
                "shape": row.get("shape") or "",
                "render_order": order,
                "image_backend": images.BACKEND,
                "image_model": images.model_name(),
                "image_prompt_profile": row.get("prompt_profile") or "default",
                "image_size": f"{images.SIZE}x{images.SIZE}",
                "text_model": transcription.get("served_by") or "",
                "pipeline_version": transcription.get("pipeline_version") or "",
                "schema_degraded": bool(transcription.get("schema_degraded")),
                "prompt_source": "agent_enriched_plus_catalogue",
                "author_prompt": row.get("prompt") or "",
                "clarifications": spec.get("clarifications") or [],
                "initial_scene_subprompt_enriched": enriched,
                "layout_addendum": row.get("addendum") or "",
                "isometric": {
                    "prompt": iso_prompt,
                    "sha256": digest(iso_prompt),
                    "reference": references["isometric"],
                },
                "topdown": {
                    "prompt": td_prompt,
                    "sha256": digest(td_prompt),
                    "reference": references["topdown"],
                },
            }
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--out", type=pathlib.Path)
    args = parser.parse_args()
    out = args.out or paths.RUNS / f"{args.run_name}_prompts.jsonl"
    records = build(args.run_name)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"wrote {out} ({len(records)} prompt records)")


if __name__ == "__main__":
    main()
