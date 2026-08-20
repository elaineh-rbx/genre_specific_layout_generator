"""Delete local T2I PNGs only after verifying identical objects exist in S3."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import boto3

REPO = Path(__file__).resolve().parent.parent
DEFAULT_RUN = "golden75_initial_gpt_prompts_all3_260817"
DEFAULT_ROOT = REPO / "results" / "t2i" / DEFAULT_RUN
DEFAULT_PREFIX = f"users/elaineh/layoutgen/results/t2i/{DEFAULT_RUN}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--bucket", default="3dfm-data")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--profile", default="3dfm")
    args = parser.parse_args()

    manifest = json.loads((args.root / "manifest.json").read_text(encoding="utf-8"))
    expected = {
        str(
            Path(result["file"]).relative_to(
                Path("results/t2i") / args.root.name
            )
        )
        for result in manifest["results"]
        if result["status"] == "ok"
    }

    s3 = boto3.Session(profile_name=args.profile).client("s3")
    remote = {
        obj["Key"].removeprefix(args.prefix.rstrip("/") + "/"): obj["ETag"].strip('"')
        for page in s3.get_paginator("list_objects_v2").paginate(
            Bucket=args.bucket,
            Prefix=args.prefix.rstrip("/") + "/",
        )
        for obj in page.get("Contents", [])
        if obj["Key"].endswith(".png")
    }
    if set(remote) != expected:
        raise RuntimeError(
            f"S3 set mismatch: expected {len(expected)} PNGs, found {len(remote)}"
        )

    removed = 0
    freed = 0
    for relative in sorted(expected):
        local = args.root / relative
        if not local.is_file():
            continue
        digest = hashlib.md5(local.read_bytes()).hexdigest()
        if digest != remote[relative]:
            raise RuntimeError(f"checksum mismatch; refusing to delete {local}")
        freed += local.stat().st_size
        local.unlink()
        removed += 1
    print(f"deleted {removed} verified local PNGs ({freed / 1024 / 1024:.1f} MiB)")


if __name__ == "__main__":
    main()
