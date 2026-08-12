"""How close the blob arm's prompts are to the arm the pipeline viewer shows.

Both arms now assemble a prompt the same way - a body, then the document's own wording
for the chosen shape and options, then the shared style tail - so every remaining
difference is one of three things, and it is worth keeping them apart:

  body    the viewer's arm sends the author's message verbatim; the blob arm sends the
          uprezzed rewrite of it. Containment, not overlap, is the number that matters:
          how much of what the author said survives into the body that was actually sent.
  config  a different genre, shape or option set produces a different addendum. Byte
          identity is the strict test; sharing the shape is the loose one.
  order   which image is drawn first, which changes the wrapper and the top-down text.

A single similarity score would blend all three and hide which one is doing the work.

Usage:
    python tools/prompt_similarity.py
    python tools/prompt_similarity.py --show 3
"""

from __future__ import annotations

import argparse
import pathlib
import statistics as st
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from layoutgen.pipeline import golden                     # noqa: E402
from tools.genre_truth import bag                         # noqa: E402

ORDER = {"std": "isometric-first", "p6": "plan-first", "layout": "authored-first"}


def share(part: set[str], whole: set[str]) -> float:
    """How much of `part` appears in `whole`. Asymmetric on purpose."""
    return len(part & whole) / len(part) if part else 1.0


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if (a or b) else 1.0


def med(xs: list[float]) -> str:
    return f"{st.median(xs) * 100:5.1f}%" if xs else "  n/a"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--show", type=int, default=0, help="print N side-by-side bodies")
    args = ap.parse_args()

    new = {r.scene: r for r in golden.blob_rows() if r.scene.startswith("P")}
    old = {r.scene: r for r in golden.answered_rows()}
    shared = sorted(set(new) & set(old))
    print(f"{len(shared)} scenes rendered by both arms\n")

    # `Row.prompt` is the author's message on every arm, kept for display. It is the
    # body the viewer's arm actually sends; the blob arm sends `scene_prompt` instead.
    body = {"viewer": {s: old[s].prompt for s in shared},
            "blob": {s: new[s].scene_prompt for s in shared}}
    author = {s: bag(body["viewer"][s]) for s in shared}
    b_body = {s: bag(body["blob"][s]) for s in shared}

    print("BODY  (viewer arm sends the author verbatim; blob sends the uprez)")
    print(f"  author words kept by the blob body   "
          f"{med([share(author[s], b_body[s]) for s in shared])}   (was 34%)")
    print(f"  blob body words the author wrote     "
          f"{med([share(b_body[s], author[s]) for s in shared])}   (was 14%)")
    print(f"  chars: author median "
          f"{st.median([len(body['viewer'][s]) for s in shared]):5.0f}"
          f"   blob median {st.median([len(body['blob'][s]) for s in shared]):5.0f}"
          f"   (blob was ~900)")

    same_shape = sum(1 for s in shared if new[s].shape == old[s].shape)
    ident = sum(1 for s in shared if new[s].addendum.strip() == old[s].addendum.strip())
    print("\nCONFIG  (the addendum is generated from genre + shape + options)")
    print(f"  same genre                {100 * sum(1 for s in shared if new[s].genre == old[s].genre) / len(shared):5.1f}%")
    print(f"  same shape                {100 * same_shape / len(shared):5.1f}%")
    print(f"  byte-identical addendum   {100 * ident / len(shared):5.1f}%   (was 4%)")
    print(f"  addendum wording overlap  "
          f"{med([jaccard(bag(new[s].addendum), bag(old[s].addendum)) for s in shared])}")

    same_o = sum(1 for s in shared if new[s].order == old[s].order)
    print("\nORDER  (which image is drawn first)")
    print(f"  same order                {100 * same_o / len(shared):5.1f}%   (was 64%)")
    for key, label in ORDER.items():
        n_new = sum(1 for s in shared if new[s].order == key)
        n_old = sum(1 for s in shared if old[s].order == key)
        print(f"    {label:18} viewer {n_old:4d}   blob {n_new:4d}")

    full_new = {s: bag(new[s].iso_prompt) for s in shared}
    full_old = {s: bag(old[s].iso_prompt) for s in shared}
    print("\nWHAT ACTUALLY REACHED THE IMAGE MODEL (isometric prompt)")
    print(f"  vocabulary overlap        "
          f"{med([jaccard(full_new[s], full_old[s]) for s in shared])}   (was 35%)")
    print(f"  byte-identical            "
          f"{sum(1 for s in shared if new[s].iso_prompt.strip() == old[s].iso_prompt.strip())}"
          f" scenes   (was 0)")
    print(f"  chars: viewer median {st.median([len(old[s].iso_prompt) for s in shared]):5.0f}"
          f"   blob median {st.median([len(new[s].iso_prompt) for s in shared]):5.0f}")

    twins = [s for s in shared if new[s].genre == old[s].genre
             and new[s].shape == old[s].shape and new[s].order == old[s].order]
    print(f"\n  on the {len(twins)} scenes where genre, shape and order all agree, the "
          f"prompts still\n  differ only by the body: overlap "
          f"{med([jaccard(full_new[s], full_old[s]) for s in twins])}")

    for s in shared[: args.show]:
        print(f"\n--- {s} "
              f"[{old[s].genre}/{old[s].shape} -> {new[s].genre}/{new[s].shape}]")
        print(f"  viewer body: {body['viewer'][s][:300]}")
        print(f"  blob body:   {body['blob'][s][:300]}")


if __name__ == "__main__":
    main()
