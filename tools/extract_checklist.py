"""Extract the per-scene evaluation checklist from the prompt that was sent.

For each scene the image model was sent `source + addendum`, where the addendum lists
the shape and options the arm picked. What a downstream eval wants is a *checklist of
concrete features the rendered image should visibly contain*, so a judge can verify each
item against the iso/top-down render and produce a coverage score.

The extraction itself lives in `layoutgen.evaluate.checklist`, because `pipeline.golden`
now runs it at the end of every render - a scene should not be generable without one.
This is the CLI over it, for backfilling scenes rendered before that was true.

One file per scene, shared by every arm; see that module for why. `--arm` chooses whose
addendum is read for a scene that has no checklist yet, which is the only thing about it
that is arm-specific.

Usage:
    python tools/extract_checklist.py --limit 5              # small pilot
    python tools/extract_checklist.py --only P0002,P0075     # named scenes
    python tools/extract_checklist.py --arm e2e              # backfill one arm
    python tools/extract_checklist.py --all-arms             # every rendered scene
    python tools/extract_checklist.py --force --workers 12
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen.evaluate import checklist
from layoutgen.pipeline.golden import SOURCES

#: Preferred order when `--all-arms` finds the same scene in several. Arms that actually
#: rendered the scene come first: the addendum recorded should be one some image was
#: really made from, and `blob` has specs for 692 scenes and images for none of them.
PREFERENCE = ("answered", "e2e", "skill", "rules", "blob")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arm", default="answered", choices=sorted(SOURCES),
                    help="which arm's rows to read")
    ap.add_argument("--all-arms", action="store_true",
                    help="every arm, so no rendered scene is left without a checklist")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="",
                    help="comma-separated scene ids, ignoring the rest")
    ap.add_argument("--force", action="store_true",
                    help="redo scenes that already have a checklist")
    args = ap.parse_args()

    arms = [a for a in PREFERENCE if a in SOURCES] if args.all_arms else [args.arm]
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    t0 = time.monotonic()
    ok = err = 0
    for arm in arms:
        try:
            rows = SOURCES[arm]()
        except Exception as exc:
            print(f"{arm}: no rows ({type(exc).__name__}: {exc})")
            continue
        if only:
            rows = [r for r in rows if r.scene in only]
        if args.limit:
            rows = rows[: args.limit]
        if not rows:
            continue
        print(f"--- {arm}: {len(rows)} scenes")
        a, b = checklist.ensure(rows, arm=arm, workers=args.workers, force=args.force)
        ok += a
        err += b

    dt = time.monotonic() - t0
    print(f"\n{ok} written, {err} error in {dt:.1f}s "
          f"({(ok / dt if dt else 0):.1f} scenes/sec)")


if __name__ == "__main__":
    main()
