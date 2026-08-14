"""Build and upload a manifest for the agent_gateway i2l segmentation corpus."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import boto3

REPO = Path(__file__).resolve().parent.parent
BUCKET = "3dfm-data"
SOURCE_PREFIX = os.getenv(
    "LAYOUTGEN_I2L_SOURCE_PREFIX",
    "users/elaineh/layoutgen/results/scenes/agent_gateway_260813",
).strip("/")
PREFIX = f"{SOURCE_PREFIX}/i2l"
RUN_NAME = os.getenv("LAYOUTGEN_I2L_RUN_NAME", "agent_gateway")
RUN = REPO / "results" / "runs" / f"{RUN_NAME}.jsonl"
SPECS = REPO / "results" / "routing" / "agent_spec_gateway"
OUT = REPO / "results" / "runs" / f"{RUN_NAME}_segmentation_manifest.jsonl"
SUMMARY = REPO / "results" / "runs" / f"{RUN_NAME}_segmentation_summary.json"


def uri(key: str) -> str:
    return f"s3://{BUCKET}/{key}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="3dfm")
    args = parser.parse_args()
    s3 = boto3.Session(profile_name=args.profile).client("s3")

    objects: dict[str, int] = {}
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=f"{PREFIX}/"):
        for obj in page.get("Contents", []):
            objects[obj["Key"]] = obj["Size"]

    runs = {
        row["scene"]: row
        for line in RUN.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }
    rows = []
    for scene, run in sorted(runs.items()):
        base = f"{PREFIX}/{scene}"
        required = {
            "mask": f"{base}/seg_mask.png",
            "plan": f"{base}/plan/response.json",
            "palette": f"{base}/generation/palette.json",
            "stage": f"{base}/generation/stage_c.json",
            "timings": f"{base}/timings.json",
        }
        complete = all(key in objects and objects[key] > 0 for key in required.values())
        stage = {}
        if required["stage"] in objects:
            stage = json.loads(
                s3.get_object(Bucket=BUCKET, Key=required["stage"])["Body"].read()
            )
        spec_path = SPECS / f"{scene}.json"
        spec_doc = json.loads(spec_path.read_text(encoding="utf-8"))
        spec = spec_doc.get("spec") or {}
        scene_keys = {
            key: size for key, size in objects.items() if key.startswith(f"{base}/")
        }
        quality = stage.get("mask_quality") or {}
        rows.append(
            {
                "scene": scene,
                "status": "complete" if complete else "incomplete",
                "genre": spec.get("genre", ""),
                "shape": spec.get("shape", ""),
                "preset": spec.get("preset", ""),
                "render_order": run.get("order", ""),
                "source": {
                    "isometric": uri(f"{SOURCE_PREFIX}/iso/{scene}.png"),
                    "topdown": uri(f"{SOURCE_PREFIX}/td/{scene}.png"),
                    **(
                        {"plan": uri(f"{SOURCE_PREFIX}/plan/{scene}.png")}
                        if run.get("plan")
                        else {}
                    ),
                },
                "segmentation": {
                    name: uri(key) for name, key in required.items()
                },
                "mask_gallery": uri(f"{SOURCE_PREFIX}/seg/{scene}.png"),
                "output_prefix": uri(base),
                "backend": stage.get("backend", ""),
                "model": stage.get("model", ""),
                "attempts": stage.get("attempts"),
                "quality_gate_passed": quality.get("meets_gate"),
                "near_palette_fraction": quality.get("near_palette_fraction"),
                "palette_classes": len(quality.get("coverage") or {}),
                "output_sha256": stage.get("output_sha256", ""),
                "artifact_count": len(scene_keys),
                "artifact_bytes": sum(scene_keys.values()),
            }
        )

    OUT.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    complete = sum(row["status"] == "complete" for row in rows)
    passed = sum(row["quality_gate_passed"] is True for row in rows)
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "bucket": BUCKET,
        "prefix": uri(PREFIX),
        "scenes": len(rows),
        "complete": complete,
        "incomplete": len(rows) - complete,
        "quality_gate_passed": passed,
        "quality_gate_not_passed": complete - passed,
        "artifact_count": sum(row["artifact_count"] for row in rows),
        "artifact_bytes": sum(row["artifact_bytes"] for row in rows),
        "manifest": uri(f"{SOURCE_PREFIX}/segmentation_manifest.jsonl"),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    s3.upload_file(str(OUT), BUCKET, f"{SOURCE_PREFIX}/segmentation_manifest.jsonl")
    s3.upload_file(
        str(SUMMARY), BUCKET, f"{SOURCE_PREFIX}/segmentation_manifest_summary.json"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
