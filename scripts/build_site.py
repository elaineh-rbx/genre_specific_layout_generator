"""Rebuild every page from what is currently in `results/`.

The pages are static and are generated from the runs and the scores, so this is the
step that makes new results visible. Order matters only in that the thumbnails are
made first; after that each page is independent.

One comparison page is written per entry in the registry, so a new comparison appears
here without this script learning its name.

Usage:
    python scripts/build_site.py
"""

from __future__ import annotations

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from layoutgen import paths  # noqa: E402
from layoutgen.web.pages import (  # noqa: E402
    catalogue, comparison, index, requirements, roadmap, shared,
)

#: Pages that stand alone. The comparison pages come from the registry instead.
PAGES = (requirements, roadmap, catalogue, index)


def main() -> None:
    paths.SITE.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    print(f"{shared.thumbs()} thumbnails", flush=True)
    outs = comparison.build_all()
    for module in PAGES:
        outs.append(module.build())
    for out in outs:
        print(f"  {out.relative_to(paths.ROOT)}  {out.stat().st_size // 1024} KB",
              flush=True)
    print(f"done in {time.monotonic() - t0:.1f}s")


if __name__ == "__main__":
    main()
