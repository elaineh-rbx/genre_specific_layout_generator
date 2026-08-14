"""Extract versioned eval checklists from one run's exact prompt and addendum."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen.backends import llm  # noqa: E402
from layoutgen.evaluate import checklist  # noqa: E402
from layoutgen.paths import RESULTS  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    run_path = RESULTS / "runs" / f"{args.run_name}.jsonl"
    rows = [
        json.loads(line)
        for line in run_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [row for row in rows if row.get("status") == "ok"]
    out_dir = RESULTS / "eval" / args.run_name
    out_dir.mkdir(parents=True, exist_ok=True)
    todo = [
        row
        for row in rows
        if args.force or not (out_dir / f"{row['scene']}.json").is_file()
    ]
    print(
        f"extracting {len(todo)} of {len(rows)} run checklists into {out_dir}",
        flush=True,
    )

    lock = threading.Lock()
    done = failed = 0

    def worker(row: dict) -> None:
        nonlocal done, failed
        scene = row["scene"]
        try:
            response = checklist.extract_one(
                scene,
                row.get("prompt", ""),
                row.get("addendum", ""),
            )
            record = {
                "scene": scene,
                "addendum_from": args.run_name,
                "served_by": llm.served_by(),
                "genre": row.get("genre", ""),
                "shape": row.get("shape", ""),
                "preset": row.get("preset", ""),
                "route": row.get("route") or [],
                "iso_prompt_len": len(row.get("iso_prompt", "")),
                "features": response.get("features") or [],
                "excluded": response.get("excluded") or [],
            }
            path = out_dir / f"{scene}.json"
            tmp = path.with_suffix(f".part{threading.get_ident()}")
            tmp.write_text(
                json.dumps(record, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            tmp.replace(path)
        except Exception as exc:  # noqa: BLE001
            with lock:
                failed += 1
                done += 1
                print(
                    f"  [{done}/{len(todo)}] {scene} failed: "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )
            return
        with lock:
            done += 1
            print(
                f"  [{done}/{len(todo)}] {scene} "
                f"{len(record['features'])} essential features",
                flush=True,
            )

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(worker, todo))

    print(
        f"RUN_CHECKLISTS_COMPLETE ok={len(todo) - failed} failed={failed} "
        f"total={len(rows)}",
        flush=True,
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
