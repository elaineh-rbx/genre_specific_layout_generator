"""Publish a final all-scene GEPA winner and its complete prompts to S3."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import boto3

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen.optimize.gepa_images import _candidate_id, load_cases  # noqa: E402

DEFAULT_RUN = REPO / "run" / "gepa" / "gemini_gepa_all75_v1_260816"
DEFAULT_DESTINATION = (
    "s3://3dfm-data/users/elaineh/layoutgen/results/gepa/"
    "gemini_gepa_all75_v1_260816"
)


def _split_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"destination must start with s3://, got {uri!r}")
    bucket, separator, prefix = uri.removeprefix("s3://").partition("/")
    if not bucket or not separator or not prefix.strip("/"):
        raise ValueError("destination must include both a bucket and a non-empty prefix")
    return bucket, prefix.strip("/")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _image_record(path: Path, uri: str) -> dict[str, str | int]:
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(f"missing winner image: {path}")
    return {
        "uri": uri,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def build_manifest(
    run_root: Path,
    destination: str,
    *,
    candidate_file: Path | None = None,
    allow_partial: bool = False,
    minimum_camera_score: float | None = None,
) -> tuple[dict, list[tuple[Path, str]]]:
    """Build a complete prompt/image manifest and an S3 upload plan."""
    bucket, prefix = _split_s3_uri(destination)
    candidate_path = candidate_file or run_root / "best_candidate.json"
    candidate = json.loads(candidate_path.read_text())
    run_manifest = json.loads((run_root / "manifest.json").read_text())
    specs = Path(run_manifest["specs"])
    cases = load_cases(specs)
    expected_scenes = run_manifest.get("all_scenes") or (
        run_manifest["train_scenes"] + run_manifest["val_scenes"]
    )
    iso_only = bool(run_manifest.get("iso_only"))
    score_path = run_root / "final_all75_scores.json"
    if score_path.is_file():
        score_rows = json.loads(score_path.read_text())
    elif allow_partial:
        score_rows = []
        for scene in expected_scenes:
            case = cases[scene]
            render_root = run_root / "renders" / _candidate_id(candidate, case) / scene
            if (render_root / "prompts.json").is_file() and (
                render_root / "iso.jpg"
            ).is_file():
                score_rows.append({"scene": scene, "scores": {}})
    else:
        raise FileNotFoundError(f"missing final scores: {score_path}")
    if minimum_camera_score is not None:
        score_rows = [
            row
            for row in score_rows
            if row.get("scores", {}).get("isometric_camera", 0.0)
            >= minimum_camera_score
        ]

    if not allow_partial and len(score_rows) != len(expected_scenes):
        raise ValueError(
            f"expected {len(expected_scenes)} final score rows, found {len(score_rows)}"
        )

    scenes = []
    uploads: list[tuple[Path, str]] = []
    seen: set[str] = set()
    for score_row in score_rows:
        scene = str(score_row["scene"])
        if scene in seen:
            raise ValueError(f"duplicate final scene: {scene}")
        seen.add(scene)
        case = cases[scene]
        candidate_id = _candidate_id(candidate, case)
        render_root = run_root / "renders" / candidate_id / scene
        prompt_record = json.loads((render_root / "prompts.json").read_text())
        if prompt_record["candidate_id"] != candidate_id:
            raise ValueError(f"candidate mismatch for scene {scene}")

        iso_path = render_root / "iso.jpg"
        iso_key = f"{prefix}/images/isometric/{scene}.jpg"
        uploads.append((iso_path, iso_key))
        image_records = {
            "isometric": _image_record(iso_path, f"s3://{bucket}/{iso_key}")
        }
        prompt_records = {
            "isometric": {
                "stage": "iso",
                "text": prompt_record["iso_prompt"],
            }
        }
        if not iso_only:
            topdown_path = render_root / "td.jpg"
            topdown_key = f"{prefix}/images/topdown/{scene}.jpg"
            uploads.append((topdown_path, topdown_key))
            image_records["topdown"] = _image_record(
                topdown_path, f"s3://{bucket}/{topdown_key}"
            )
            prompt_records["topdown"] = {
                "stage": prompt_record["first_stage"],
                "text": prompt_record["first_prompt"],
            }
        scenes.append(
            {
                "scene": scene,
                "render_order": case.order,
                "candidate_id": candidate_id,
                "images": image_records,
                "prompts": prompt_records,
                "scores": score_row["scores"],
            }
        )

    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "run_name": run_manifest["run_name"],
        "image_model": run_manifest["image_model"],
        "destination": destination.rstrip("/"),
        "scene_count": len(scenes),
        "image_count": len(uploads),
        "prompt_count": sum(len(scene["prompts"]) for scene in scenes),
        "winning_execution_policies": candidate,
        "target": {
            "arm": run_manifest["target_arm"],
            "role": run_manifest["target_role"],
            "uploaded": False,
        },
        "scenes": scenes,
    }
    return manifest, uploads


def _upload_one(s3, bucket: str, item: tuple[Path, str]) -> None:
    path, key = item
    s3.upload_file(
        str(path),
        bucket,
        key,
        ExtraArgs={"ContentType": "image/jpeg"},
    )


def write_csv_manifest(manifest: dict, path: Path) -> None:
    """Write one flattened row per scene, retaining both complete prompts."""
    fieldnames = [
        "run_name",
        "image_model",
        "scene",
        "render_order",
        "candidate_id",
        "isometric_image_uri",
        "isometric_image_bytes",
        "isometric_image_sha256",
        "isometric_prompt",
        "topdown_image_uri",
        "topdown_image_bytes",
        "topdown_image_sha256",
        "topdown_prompt_stage",
        "topdown_prompt",
        "isometric_similarity",
        "topdown_similarity",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for scene in manifest["scenes"]:
            iso = scene["images"]["isometric"]
            topdown = scene["images"].get("topdown", {})
            topdown_prompt = scene["prompts"].get("topdown", {})
            writer.writerow(
                {
                    "run_name": manifest["run_name"],
                    "image_model": manifest["image_model"],
                    "scene": scene["scene"],
                    "render_order": scene["render_order"],
                    "candidate_id": scene["candidate_id"],
                    "isometric_image_uri": iso["uri"],
                    "isometric_image_bytes": iso["bytes"],
                    "isometric_image_sha256": iso["sha256"],
                    "isometric_prompt": scene["prompts"]["isometric"]["text"],
                    "topdown_image_uri": topdown.get("uri", ""),
                    "topdown_image_bytes": topdown.get("bytes", ""),
                    "topdown_image_sha256": topdown.get("sha256", ""),
                    "topdown_prompt_stage": topdown_prompt.get("stage", ""),
                    "topdown_prompt": topdown_prompt.get("text", ""),
                    "isometric_similarity": scene["scores"].get(
                        "isometric_similarity",
                        scene["scores"].get("perceptual_similarity", ""),
                    ),
                    "topdown_similarity": scene["scores"].get(
                        "topdown_similarity", ""
                    ),
                }
            )


def write_local_manifests(run_root: Path, manifest: dict) -> tuple[Path, Path]:
    """Write the nested JSON and flattened CSV representations."""
    json_path = run_root / "s3_manifest.json"
    csv_path = run_root / "s3_manifest.csv"
    json_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_csv_manifest(manifest, csv_path)
    return json_path, csv_path


def publish(
    run_root: Path,
    destination: str,
    profile: str,
    workers: int,
    overwrite: bool,
    *,
    candidate_file: Path | None = None,
    allow_partial: bool = False,
    minimum_camera_score: float | None = None,
) -> dict:
    """Validate and upload all images, publishing the manifest last."""
    manifest, uploads = build_manifest(
        run_root,
        destination,
        candidate_file=candidate_file,
        allow_partial=allow_partial,
        minimum_camera_score=minimum_camera_score,
    )
    bucket, prefix = _split_s3_uri(destination)
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    s3 = session.client("s3")

    existing = s3.list_objects_v2(Bucket=bucket, Prefix=f"{prefix}/", MaxKeys=1)
    if existing.get("KeyCount", 0) and not overwrite:
        raise FileExistsError(
            f"{destination.rstrip('/')} already contains objects; "
            "pass --overwrite to replace them"
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(lambda item: _upload_one(s3, bucket, item), uploads))

    manifest_path, csv_path = write_local_manifests(run_root, manifest)
    s3.upload_file(
        str(manifest_path),
        bucket,
        f"{prefix}/manifest.json",
        ExtraArgs={"ContentType": "application/json"},
    )
    s3.upload_file(
        str(csv_path),
        bucket,
        f"{prefix}/manifest.csv",
        ExtraArgs={"ContentType": "text/csv"},
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--destination", default=DEFAULT_DESTINATION)
    parser.add_argument("--profile", default="3dfm")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--candidate-file", type=Path)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--minimum-camera-score", type=float)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and write the local manifest without uploading",
    )
    args = parser.parse_args()

    if args.dry_run:
        manifest, _uploads = build_manifest(
            args.run_root,
            args.destination,
            candidate_file=args.candidate_file,
            allow_partial=args.allow_partial,
            minimum_camera_score=args.minimum_camera_score,
        )
        write_local_manifests(args.run_root, manifest)
    else:
        manifest = publish(
            args.run_root,
            args.destination,
            args.profile,
            args.workers,
            args.overwrite,
            candidate_file=args.candidate_file,
            allow_partial=args.allow_partial,
            minimum_camera_score=args.minimum_camera_score,
        )
    print(
        json.dumps(
            {
                "destination": manifest["destination"],
                "manifest": f"{manifest['destination']}/manifest.json",
                "csv_manifest": f"{manifest['destination']}/manifest.csv",
                "scenes": manifest["scene_count"],
                "images": manifest["image_count"],
                "prompts": manifest["prompt_count"],
                "uploaded": not args.dry_run,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
