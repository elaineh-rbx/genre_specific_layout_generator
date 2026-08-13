"""Run image-to-layout's image stages over the agent_gateway render corpus.

Each scene is downloaded from S3, processed in an isolated bounded-size work
directory, uploaded with all provenance, verified by object size, and removed
locally. A scene whose accepted ``seg_mask.png`` is already in S3 is skipped.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import boto3

BUCKET = "3dfm-data"
SOURCE_PREFIX = "users/elaineh/layoutgen/results/scenes/agent_gateway_260813"
OUTPUT_PREFIX = f"{SOURCE_PREFIX}/i2l"
I2L_REPO = Path("/home/builder/workspace/image-to-layout")
MANIFEST = (
    Path(__file__).resolve().parent.parent / "results" / "runs" / "agent_gateway.jsonl"
)

_local = threading.local()
_lock = threading.Lock()
_done = 0


def client(profile: str):
    if not hasattr(_local, "s3"):
        _local.s3 = boto3.Session(profile_name=profile).client("s3")
    return _local.s3


def completed(profile: str) -> set[str]:
    s3 = client(profile)
    paginator = s3.get_paginator("list_objects_v2")
    keys = {
        obj["Key"]
        for page in paginator.paginate(Bucket=BUCKET, Prefix=f"{OUTPUT_PREFIX}/")
        for obj in page.get("Contents", [])
        if obj["Size"] > 0
    }
    candidates = {
        key.removesuffix("/seg_mask.png").rsplit("/", 1)[-1]
        for key in keys
        if key.endswith("/seg_mask.png")
    }
    return {
        scene
        for scene in candidates
        if f"{OUTPUT_PREFIX}/{scene}/generation/stage_c.json" in keys
        and f"{OUTPUT_PREFIX}/{scene}/timings.json" in keys
    }


def scenes() -> list[str]:
    rows = [
        json.loads(line)
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return sorted(r["scene"] for r in rows if r.get("status") == "ok")


def upload_tree(s3, root: Path, prefix: str) -> None:
    uploaded: list[tuple[str, int]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        key = f"{prefix}/{path.relative_to(root).as_posix()}"
        size = path.stat().st_size
        s3.upload_file(str(path), BUCKET, key)
        uploaded.append((key, size))
    for key, size in uploaded:
        actual = s3.head_object(Bucket=BUCKET, Key=key)["ContentLength"]
        if actual != size:
            raise RuntimeError(f"S3 size mismatch for {key}: local={size}, remote={actual}")


def run_one(scene: str, profile: str, work_root: Path, total: int) -> tuple[str, str]:
    global _done
    started = time.monotonic()
    run = work_root / scene
    s3 = client(profile)
    state = "ok"
    try:
        # A previous orchestrator may have been stopped while its i2l child was
        # finishing. Preserve that paid generation instead of clearing it.
        if (
            (run / "seg_mask.png").is_file()
            and (run / "generation" / "stage_c.json").is_file()
            and (run / "timings.json").is_file()
        ):
            upload_tree(s3, run, f"{OUTPUT_PREFIX}/{scene}")
        else:
            shutil.rmtree(run, ignore_errors=True)
            run.mkdir(parents=True)
            for source, target in (("iso", "isometric.png"), ("td", "topdown.png")):
                s3.download_file(
                    BUCKET,
                    f"{SOURCE_PREFIX}/{source}/{scene}.png",
                    str(run / target),
                )
            env = os.environ.copy()
            env["I2L_LLM_GATEWAY_TOKEN_CACHE"] = str(
                Path("~/.cache/llm-gateway-token").expanduser()
            )
            answer = subprocess.run(
                [
                    str(I2L_REPO / ".venv" / "bin" / "i2l"),
                    "pipeline",
                    "run",
                    str(run),
                    "--images-only",
                    "--backend",
                    "gpt-image-2",
                    "--image-size",
                    "1024",
                ],
                cwd=I2L_REPO,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=1800,
            )
            (run / "_pipeline.log").write_text(answer.stdout, encoding="utf-8")
            if answer.returncode or not (run / "seg_mask.png").is_file():
                state = "failed"
                (run / "_failed.json").write_text(
                    json.dumps(
                        {"scene": scene, "returncode": answer.returncode}, indent=2
                    )
                    + "\n",
                    encoding="utf-8",
                )
            upload_tree(s3, run, f"{OUTPUT_PREFIX}/{scene}")
    except Exception as exc:
        state = f"failed: {type(exc).__name__}: {exc}"
        try:
            (run / "_failed.json").write_text(
                json.dumps({"scene": scene, "error": state}, indent=2) + "\n",
                encoding="utf-8",
            )
            upload_tree(s3, run, f"{OUTPUT_PREFIX}/{scene}")
        except Exception as upload_exc:
            state += f"; failure upload also failed: {upload_exc}"
    finally:
        shutil.rmtree(run, ignore_errors=True)
    with _lock:
        _done += 1
        print(
            f"[{_done}/{total}] {scene} {state} ({time.monotonic() - started:.1f}s)",
            flush=True,
        )
    return scene, state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--profile", default="3dfm")
    parser.add_argument(
        "--work-root",
        type=Path,
        default=I2L_REPO / "inference_runs" / "layoutgen_agent_gateway",
    )
    parser.add_argument("--only", default="", help="comma-separated scene IDs")
    args = parser.parse_args()

    wanted = scenes()
    if args.only:
        selected = {x.strip() for x in args.only.split(",") if x.strip()}
        wanted = [scene for scene in wanted if scene in selected]
    already = completed(args.profile)
    todo = [scene for scene in wanted if scene not in already]
    args.work_root.mkdir(parents=True, exist_ok=True)
    print(
        f"{len(wanted)} selected; {len(already & set(wanted))} already complete; "
        f"{len(todo)} to run with {args.workers} workers",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        outcomes = list(
            pool.map(
                lambda scene: run_one(
                    scene, args.profile, args.work_root, len(todo)
                ),
                todo,
            )
        )
    failed = [(scene, state) for scene, state in outcomes if state != "ok"]
    if failed:
        print(f"{len(failed)} failed:", flush=True)
        for scene, state in failed:
            print(f"  {scene}: {state}", flush=True)
        raise SystemExit(1)
    print(f"SEGMENTATION_BATCH_COMPLETE scenes={len(wanted)}", flush=True)


if __name__ == "__main__":
    main()
