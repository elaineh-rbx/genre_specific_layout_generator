"""Rebuild every viewer page from what is currently in `results/`.

The pages are static and are generated from the runs and the scores, so this is the
step that makes new results visible. Order matters only in that the thumbnails are
made first; after that each page is independent.

Usage:
    python scripts/build_site.py
"""

from __future__ import annotations

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from gslg import paths  # noqa: E402
from gslg.viewers import catalogue, compare, index, requirements, roadmap, three_way  # noqa: E402

PAGES = (three_way, compare, requirements, roadmap, catalogue, index)


def main() -> None:
    paths.SITE.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    print(f"{compare.thumbs()} thumbnails", flush=True)
    for module in PAGES:
        out = module.build()
        print(f"  {out.relative_to(paths.ROOT)}  {out.stat().st_size // 1024} KB",
              flush=True)
    print(f"done in {time.monotonic() - t0:.1f}s")


if __name__ == "__main__":
    main()
