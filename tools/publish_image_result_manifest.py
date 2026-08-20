"""Publish JSON and CSV manifests for a completed image-generation run."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import boto3

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "results" / "runs"
DEFAULT_RUN_NAME = "agent_gpt52_upstream_cf94b18_gptimage2_260815"
DEFAULT_DESTINATION = (
    "s3://3dfm-data/users/elaineh/layoutgen/results/scenes/"
    f"{DEFAULT_RUN_NAME}"
)


def _split_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"destination must start with s3://, got {uri!r}")
    bucket, separator, prefix = uri.removeprefix("s3://").partition("/")
    if not bucket or not separator or not prefix.strip("/"):
        raise ValueError("destination must include both a bucket and a non-empty prefix")
    return bucket, prefix.strip("/")


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_manifest(run_name: str, destination: str) -> dict:
    """Combine the prompt manifest with stable image URIs."""
    prompt_rows = _jsonl(RUNS / f"{run_name}_prompts.jsonl")
    run_rows = {
        str(row["scene"]): row for row in _jsonl(RUNS / f"{run_name}.jsonl")
    }
    if not prompt_rows:
        raise ValueError("prompt manifest is empty")

    scenes = []
    seen: set[str] = set()
    image_count = 0
    for prompt_row in prompt_rows:
        scene = str(prompt_row["scene"])
        if scene in seen:
            raise ValueError(f"duplicate scene in prompt manifest: {scene}")
        seen.add(scene)
        run_row = run_rows.get(scene)
        if run_row is None:
            raise ValueError(f"scene {scene} is absent from the source run")

        images = {
            "isometric": f"{destination.rstrip('/')}/iso/{run_row['iso']}",
            "topdown": f"{destination.rstrip('/')}/td/{run_row['td']}",
        }
        if run_row.get("plan"):
            images["plan"] = (
                f"{destination.rstrip('/')}/plan/{run_row['plan']}"
            )
        image_count += len(images)
        scenes.append({**prompt_row, "images": images})

    return {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "run_name": run_name,
        "destination": destination.rstrip("/"),
        "scene_count": len(scenes),
        "prompt_count": len(scenes) * 2,
        "image_count": image_count,
        "scenes": scenes,
    }


def write_json_manifest(manifest: dict, path: Path) -> None:
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv_manifest(manifest: dict, path: Path) -> None:
    """Flatten nested prompt records into one CSV row per scene."""
    fieldnames = [
        "manifest_version",
        "scene",
        "title",
        "genre",
        "preset",
        "shape",
        "render_order",
        "image_backend",
        "image_model",
        "image_prompt_profile",
        "image_size",
        "text_model",
        "pipeline_version",
        "schema_degraded",
        "prompt_source",
        "author_prompt",
        "clarifications_json",
        "initial_scene_subprompt_enriched",
        "layout_addendum",
        "isometric_prompt",
        "isometric_prompt_sha256",
        "isometric_reference",
        "isometric_image_uri",
        "topdown_prompt",
        "topdown_prompt_sha256",
        "topdown_reference",
        "topdown_image_uri",
        "plan_image_uri",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in manifest["scenes"]:
            writer.writerow(
                {
                    "manifest_version": row["manifest_version"],
                    "scene": row["scene"],
                    "title": row["title"],
                    "genre": row["genre"],
                    "preset": row["preset"],
                    "shape": row["shape"],
                    "render_order": row["render_order"],
                    "image_backend": row["image_backend"],
                    "image_model": row["image_model"],
                    "image_prompt_profile": row["image_prompt_profile"],
                    "image_size": row["image_size"],
                    "text_model": row["text_model"],
                    "pipeline_version": row["pipeline_version"],
                    "schema_degraded": row["schema_degraded"],
                    "prompt_source": row["prompt_source"],
                    "author_prompt": row["author_prompt"],
                    "clarifications_json": json.dumps(
                        row["clarifications"], ensure_ascii=False
                    ),
                    "initial_scene_subprompt_enriched": row[
                        "initial_scene_subprompt_enriched"
                    ],
                    "layout_addendum": row["layout_addendum"],
                    "isometric_prompt": row["isometric"]["prompt"],
                    "isometric_prompt_sha256": row["isometric"]["sha256"],
                    "isometric_reference": row["isometric"]["reference"] or "",
                    "isometric_image_uri": row["images"]["isometric"],
                    "topdown_prompt": row["topdown"]["prompt"],
                    "topdown_prompt_sha256": row["topdown"]["sha256"],
                    "topdown_reference": row["topdown"]["reference"] or "",
                    "topdown_image_uri": row["images"]["topdown"],
                    "plan_image_uri": row["images"].get("plan", ""),
                }
            )


def _expected_keys(manifest: dict, prefix: str) -> set[str]:
    folders = {"isometric": "iso", "topdown": "td", "plan": "plan"}
    return {
        f"{prefix}/{folders[kind]}/{Path(uri).name}"
        for row in manifest["scenes"]
        for kind, uri in row["images"].items()
    }


def publish(
    manifest: dict,
    json_path: Path,
    csv_path: Path,
    profile: str,
    overwrite: bool,
) -> None:
    bucket, prefix = _split_s3_uri(manifest["destination"])
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    s3 = session.client("s3")

    existing = {
        obj["Key"]
        for page in s3.get_paginator("list_objects_v2").paginate(
            Bucket=bucket, Prefix=f"{prefix}/"
        )
        for obj in page.get("Contents", [])
    }
    missing = sorted(_expected_keys(manifest, prefix) - existing)
    if missing:
        preview = ", ".join(missing[:3])
        raise FileNotFoundError(
            f"{len(missing)} manifest image objects are missing from S3: {preview}"
        )

    manifest_keys = (f"{prefix}/manifest.json", f"{prefix}/manifest.csv")
    collisions = [key for key in manifest_keys if key in existing]
    if collisions and not overwrite:
        raise FileExistsError(
            f"manifest objects already exist: {', '.join(collisions)}; "
            "pass --overwrite to replace them"
        )

    s3.upload_file(
        str(json_path),
        bucket,
        manifest_keys[0],
        ExtraArgs={"ContentType": "application/json"},
    )
    s3.upload_file(
        str(csv_path),
        bucket,
        manifest_keys[1],
        ExtraArgs={"ContentType": "text/csv"},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--destination", default=DEFAULT_DESTINATION)
    parser.add_argument("--profile", default="3dfm")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest = build_manifest(args.run_name, args.destination)
    json_path = RUNS / f"{args.run_name}_manifest.json"
    csv_path = RUNS / f"{args.run_name}_manifest.csv"
    write_json_manifest(manifest, json_path)
    write_csv_manifest(manifest, csv_path)
    if not args.dry_run:
        publish(manifest, json_path, csv_path, args.profile, args.overwrite)

    print(
        json.dumps(
            {
                "json": f"{manifest['destination']}/manifest.json",
                "csv": f"{manifest['destination']}/manifest.csv",
                "scenes": manifest["scene_count"],
                "prompts": manifest["prompt_count"],
                "images": manifest["image_count"],
                "uploaded": not args.dry_run,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
