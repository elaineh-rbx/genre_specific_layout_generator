"""Bring the 75-scene results across from the scratch tree this repo grew out of.

Kept because it documents where `results/` came from and what was renamed on the way,
and because it is idempotent: rerunning it after regenerating a few scenes copies only
what changed. It is not part of the pipeline and nothing imports it.

Three things are normalised:

  arms       `original`/`guided` become `raw`/`needs`, matching the names the judges
             and the viewers have always used in their data
  filenames  every arm uses `{scene}.png`, where one arm used to prefix `scene_`
  scores     every judged comparison sits together under `results/scores/`, and is
             then converted to the generic format by `scripts/migrate_scores.py`

Images are hard-linked rather than copied. They are identical bytes on the same
filesystem, and a second full copy of ~900 MB buys nothing.

Usage:
    python scripts/import_results.py --src ~/workspace/image-to-layout/.i2l_scratch
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from layoutgen import paths  # noqa: E402

#: (source directory, source filename pattern) -> where it lands.
SCENES = {
    ("original", "scene_{s}.png"): ("raw", "iso"),
    ("original_td", "scene_{s}.png"): ("raw", "td"),
    ("guided", "scene_{s}.png"): ("needs", "iso"),
    ("guided_td", "scene_{s}.png"): ("needs", "td"),
}
RULES_SCENES = {"iso": "iso", "td": "td", "plan": "plan"}

FILES = [
    ("prompt_corpus/golden_set_manifest.jsonl", "prompts/golden_set.jsonl"),
    ("golden_guided/preset_classification.jsonl", "routing/rules.jsonl"),
    ("golden_guided/classification.jsonl", "routing/subgenres.jsonl"),
    ("golden_guided/run.jsonl", "runs/needs.jsonl"),
    ("golden_rules/run.jsonl", "runs/rules.jsonl"),
    ("golden_rules/scores.jsonl", "scores/rules_iso.jsonl"),
    ("golden_rules/scores_td.jsonl", "scores/rules_td.jsonl"),
    ("three_way/scores.jsonl", "scores/three_way_iso.jsonl"),
    ("three_way/scores_td.jsonl", "scores/three_way_td.jsonl"),
]


def link(src: pathlib.Path, dest: pathlib.Path) -> bool:
    if not src.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if dest.stat().st_ino == src.stat().st_ino:
            return True
        dest.unlink()
    try:
        dest.hardlink_to(src)
    except OSError:               # a different filesystem, or a hard-link limit
        shutil.copy2(src, dest)
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=pathlib.Path, required=True,
                    help="the scratch directory holding golden_rules/ and golden_guided/")
    args = ap.parse_args()
    src = args.src.expanduser()

    scenes = sorted(p.stem for p in (src / "golden_rules" / "iso").glob("*.png"))
    print(f"{len(scenes)} scenes from {src}")

    n = 0
    for (d, pat), (arm, stage) in SCENES.items():
        for s in scenes:
            n += link(src / "golden_guided" / d / pat.format(s=s),
                      paths.scene(arm, stage, s))
    for d, stage in RULES_SCENES.items():
        for s in scenes:
            n += link(src / "golden_rules" / d / f"{s}.png",
                      paths.SCENES / "rules" / stage / f"{s}.png")
    print(f"  {n} images linked")

    for a, b in FILES:
        if link(src / a, paths.RESULTS / b):
            print(f"  {b}")
        else:
            print(f"  MISSING {a}")


if __name__ == "__main__":
    main()
