#!/usr/bin/env python3
"""Batch text-to-image generation against a SceneGen serving endpoint.

Standalone: Python 3.9+ standard library only, no install and no dependency on
the rest of this repository. Copy this one file to wherever the batch runs.

    python tools/t2i_batch.py \
      --prompts prompts.jsonl \
      --models qwen-image,flux2-klein-4b,z-image-turbo

Writes out/<model>/<prompt_id>.png plus out/manifest.json.

Prompt files may be either:
  * JSONL, one object per line, with "prompt_id" and "prompt" keys. An optional
    "image" string or list attaches local paths, HTTP URLs, or data URLs; or
  * plain text, one prompt per line, auto-numbered p0001, p0002, ...

Behaviour worth knowing before a long run:

  * Already-written PNGs are skipped, so an interrupted run resumes by simply
    being restarted. Pass --overwrite to force a re-render.
  * Models are worked in parallel and prompts serially within each model. The
    server keeps one model resident per GPU and serializes requests that share a
    GPU, so this is the shape that actually uses the hardware.
  * A fixed --seed makes every model render the same prompt from the same seed,
    which is what makes the outputs comparable side by side.
  * A single prompt failing does not stop the run. Failures are recorded in the
    manifest and reported at the end.

Exit status: 0 all requested images present, 1 at least one failed, 2 the run
could not start (unreachable server, unknown model, unreadable prompts).
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import json
import mimetypes
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DEFAULT_BASE_URL = "https://8080--standard--h200-training--akashgarg.devspaces.rbx.com/"

# Retried with backoff: the server returns 503 when a model's queue is full and
# 504 when a generation outran its timeout. A 4xx means the request itself is
# wrong, so retrying it would just fail the same way.
RETRY_STATUSES = frozenset({503, 504})

print_lock = threading.Lock()


def log(message: str) -> None:
    with print_lock:
        print(message, file=sys.stderr, flush=True)


class ApiError(RuntimeError):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def request_json(url: str, token: str | None, payload: dict | None = None, timeout: float = 900.0) -> dict:
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = "Bearer " + token
    body = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, body, headers, method="GET" if payload is None else "POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        with contextlib.suppress(ValueError, KeyError, TypeError):
            detail = json.loads(detail)["error"]["message"]
        raise ApiError(f"HTTP {exc.code}: {detail}", status=exc.code) from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"cannot reach {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ApiError(f"timed out after {timeout:.0f}s waiting for {url}") from exc


def load_prompts(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    prompts: list[dict] = []
    seen: set[str] = set()
    for number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("{"):
            try:
                record = json.loads(line)
            except ValueError as exc:
                raise ApiError(f"{path}:{number}: invalid JSON: {exc}") from exc
            prompt_id = str(record.get("prompt_id") or record.get("id") or f"p{len(prompts) + 1:04d}")
            prompt = record.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ApiError(f"{path}:{number}: missing a non-empty `prompt`")
            references = record.get("image") or []
            if isinstance(references, str):
                references = [references]
            if not isinstance(references, list) or not all(
                isinstance(item, str) and item.strip() for item in references
            ):
                raise ApiError(f"{path}:{number}: `image` must be a string or list")
            references = [
                item
                if item.startswith(("data:", "http://", "https://"))
                else str((path.parent / item).resolve())
                for item in references
            ]
        else:
            prompt_id = f"p{len(prompts) + 1:04d}"
            prompt = line
            references = []
        # The ID becomes a filename, so keep it to safe characters.
        prompt_id = re.sub(r"[^A-Za-z0-9._-]+", "-", prompt_id).strip("-._") or f"p{len(prompts) + 1:04d}"
        if prompt_id in seen:
            raise ApiError(f"{path}:{number}: duplicate prompt_id `{prompt_id}`")
        seen.add(prompt_id)
        prompts.append(
            {"prompt_id": prompt_id, "prompt": prompt, "image": references}
        )
    if not prompts:
        raise ApiError(f"{path} contains no prompts")
    return prompts


def image_data_url(source: str) -> str:
    if source.startswith("data:"):
        return source
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=60.0) as response:
            data = response.read()
            mime = response.headers.get_content_type()
    else:
        path = Path(source)
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise ApiError(f"cannot read reference image {path}: {exc}") from exc
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def generate_one(args, model: str, info: dict, prompt: dict, destination: Path) -> dict:
    payload = {"model": model, "prompt": prompt["prompt"], "size": args.size, "n": 1}
    references = prompt.get("image") or []
    capacity = int(info.get("max_reference_images", 0) or 0)
    if references and not capacity:
        return {
            "status": "failed",
            "model": model,
            "prompt_id": prompt["prompt_id"],
            "error": f"{model} does not accept reference images",
            "attempts": 0,
        }
    if len(references) > capacity:
        return {
            "status": "failed",
            "model": model,
            "prompt_id": prompt["prompt_id"],
            "error": f"{model} accepts at most {capacity} reference images",
            "attempts": 0,
        }
    if references:
        payload["image"] = [image_data_url(source) for source in references]
    if args.seed is not None:
        payload["seed"] = args.seed
    if args.steps is not None:
        payload["num_inference_steps"] = args.steps
    if args.guidance is not None:
        payload["guidance"] = args.guidance
    # Guidance-distilled checkpoints run no classifier-free guidance and reject a
    # negative prompt outright, so only send it where it does something.
    if args.negative_prompt and info.get("supports_negative_prompt"):
        payload["negative_prompt"] = args.negative_prompt

    last_error = ""
    for attempt in range(1, args.retries + 2):
        try:
            response = request_json(
                args.base_url.rstrip("/") + "/v1/images/generations",
                args.token,
                payload,
                timeout=args.timeout,
            )
        except ApiError as exc:
            last_error = str(exc)
            retryable = exc.status is None or exc.status in RETRY_STATUSES
            if not retryable or attempt > args.retries:
                break
            delay = min(2 ** (attempt - 1) * args.retry_delay, 60.0)
            log(f"  ! {model}/{prompt['prompt_id']}: {last_error} - retry {attempt}/{args.retries} in {delay:.0f}s")
            time.sleep(delay)
            continue

        image = response["data"][0]
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".png.part")
        temporary.write_bytes(base64.b64decode(image["b64_json"]))
        temporary.replace(destination)
        facts = response["scenegen"]
        return {
            "status": "ok",
            "model": model,
            "prompt_id": prompt["prompt_id"],
            "file": str(destination),
            "seed": image["seed"],
            "size": facts["size"],
            "num_inference_steps": facts["num_inference_steps"],
            "guidance": facts["guidance"],
            "repo_id": facts["repo_id"],
            "generation_seconds": facts["generation_seconds"],
            "queued_seconds": facts["queued_seconds"],
            "attempts": attempt,
        }

    return {
        "status": "failed",
        "model": model,
        "prompt_id": prompt["prompt_id"],
        "error": last_error,
        "attempts": args.retries + 1,
    }


def run_model(args, model: str, info: dict, prompts: list[dict], results: list[dict]) -> None:
    output_dir = args.output_dir / model
    done = 0
    spent = 0.0
    for position, prompt in enumerate(prompts, start=1):
        destination = output_dir / (prompt["prompt_id"] + ".png")
        if destination.exists() and not args.overwrite:
            with print_lock:
                results.append({"status": "skipped", "model": model, "prompt_id": prompt["prompt_id"],
                                "file": str(destination)})
            continue

        outcome = generate_one(args, model, info, prompt, destination)
        with print_lock:
            results.append(outcome)
        if outcome["status"] == "ok":
            done += 1
            spent += outcome["generation_seconds"]
            remaining = len(prompts) - position
            eta = f", eta {remaining * spent / done / 60:.0f}m" if remaining and done else ""
            log(f"  + {model}/{prompt['prompt_id']} {outcome['generation_seconds']:.1f}s "
                f"[{position}/{len(prompts)}{eta}]")
        else:
            log(f"  x {model}/{prompt['prompt_id']} FAILED: {outcome['error']}")
    log(f"= {model}: finished, {done} rendered in {spent / 60:.1f}m")


def preflight(args) -> dict:
    listing = request_json(args.base_url.rstrip("/") + "/v1/models", args.token, timeout=30.0)
    available = {entry["id"]: entry.get("scenegen", {}) for entry in listing["data"]}
    if not args.models:
        return available
    requested = [name.strip() for name in args.models.split(",") if name.strip()]
    unknown = [name for name in requested if name not in available]
    if unknown:
        raise ApiError(
            f"unknown model(s): {', '.join(unknown)}. Served: {', '.join(available)}"
        )
    return {name: available[name] for name in requested}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch text-to-image generation against a SceneGen serving endpoint.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--prompts", required=True, type=Path, help="JSONL or plain-text prompt file.")
    parser.add_argument("--output-dir", type=Path, default=Path("out"))
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--token", default=None, help="Bearer token, if the endpoint requires one.")
    parser.add_argument("--models", default=None, help="Comma-separated model names. Default: every served model.")
    parser.add_argument("--size", default="1024x1024", help="WIDTHxHEIGHT, each divisible by 16.")
    parser.add_argument("--seed", type=int, default=1234, help="Fixed base seed; use -1 for a random seed per image.")
    parser.add_argument("--steps", type=int, default=None, help="Override the per-model default step count.")
    parser.add_argument("--guidance", type=float, default=None, help="Override the per-model default guidance.")
    parser.add_argument("--negative-prompt", default=None, help="Sent only to models that run real CFG.")
    parser.add_argument("--limit", type=int, default=None, help="Use only the first N prompts.")
    parser.add_argument("--overwrite", action="store_true", help="Re-render prompts whose PNG already exists.")
    parser.add_argument("--retries", type=int, default=3, help="Retries per image for 503/504 and network errors.")
    parser.add_argument("--retry-delay", type=float, default=5.0, help="Base seconds for exponential backoff.")
    parser.add_argument("--timeout", type=float, default=900.0, help="Per-request timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan and exit without generating.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.seed is not None and args.seed < 0:
        args.seed = None

    try:
        prompts = load_prompts(args.prompts)
        models = preflight(args)
    except ApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.limit:
        prompts = prompts[: args.limit]

    def is_pending(model: str, prompt: dict) -> bool:
        return args.overwrite or not (args.output_dir / model / (prompt["prompt_id"] + ".png")).exists()

    pending = {model: [p for p in prompts if is_pending(model, p)] for model in models}
    total = sum(len(items) for items in pending.values())

    log(f"endpoint : {args.base_url}")
    log(f"prompts  : {len(prompts)} from {args.prompts}")
    log(f"output   : {args.output_dir}/<model>/<prompt_id>.png")
    log(f"seed     : {'random per image' if args.seed is None else args.seed}")
    log(f"size     : {args.size}")
    for model, items in pending.items():
        info = models[model]
        steps = args.steps if args.steps is not None else info.get("defaults", {}).get("num_inference_steps")
        skipped = len(prompts) - len(items)
        log(f"  {model:18s} {len(items):4d} to render, {skipped:4d} already present "
            f"({info.get('parameters', '?')}, {steps} steps, {info.get('device', '?')})")
    log(f"total    : {total} image(s)")

    if args.dry_run:
        log("dry run, nothing generated")
        return 0
    if total == 0:
        log("nothing to do; every requested image already exists")
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    started = time.time()
    # One worker per model: the server renders different models concurrently.
    with ThreadPoolExecutor(max_workers=len(models)) as pool:
        futures = [
            pool.submit(run_model, args, model, models[model], prompts, results)
            for model in models
        ]
        for future in futures:
            future.result()
    elapsed = time.time() - started

    ok = [r for r in results if r["status"] == "ok"]
    failed = [r for r in results if r["status"] == "failed"]
    skipped = [r for r in results if r["status"] == "skipped"]

    manifest = {
        "endpoint": args.base_url,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "elapsed_seconds": round(elapsed, 1),
        "settings": {
            "prompts_file": str(args.prompts),
            "size": args.size,
            "seed": args.seed,
            "steps": args.steps,
            "guidance": args.guidance,
            "negative_prompt": args.negative_prompt,
        },
        "models": {name: models[name].get("repo_id") for name in models},
        "counts": {"generated": len(ok), "skipped": len(skipped), "failed": len(failed)},
        "results": sorted(results, key=lambda r: (r["model"], r["prompt_id"])),
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    log("")
    log(f"generated {len(ok)}, skipped {len(skipped)}, failed {len(failed)} in {elapsed / 60:.1f}m")
    log(f"manifest: {manifest_path}")
    if failed:
        log("failed images (rerun the same command to retry only these):")
        for result in sorted(failed, key=lambda r: (r["model"], r["prompt_id"])):
            log(f"  {result['model']}/{result['prompt_id']}: {result['error']}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
