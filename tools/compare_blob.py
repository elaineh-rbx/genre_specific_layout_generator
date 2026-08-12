"""What the blob pipeline decided, and where it disagrees with the router.

The two arms answer the same question from the same prompts, so the interesting number
is never either arm's distribution on its own - it is the disagreement, and specifically
the disagreement about **order**, because that is the decision the redesign moved.

The router never decided an order. It derived one: a shape or option happened to carry
`P6`, so the plan was drawn first. Nothing recorded whether that was right for the scene,
and nothing could, because no stage was ever asked. The blob states an order and gives a
reason, so a wrong order is now a sentence somebody can read and disagree with.

Usage:
    python tools/compare_blob.py
    python tools/compare_blob.py --against rules
    python tools/compare_blob.py --show-order-flips 12
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from layoutgen import paths                                       # noqa: E402
from layoutgen.pipeline import golden                             # noqa: E402

ORDER_LABEL = {"std": "isometric-first", "p6": "plan-first",
               "layout": "authored-first"}


def load(arm: str) -> dict[str, object]:
    return {r.scene: r for r in golden.SOURCES[arm]()}


def pct(n: int, total: int) -> str:
    return f"{n:4d}  {n / total * 100:5.1f}%" if total else "   0    0.0%"


def section(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--against", default="answered", choices=["rules", "skill",
                                                             "answered"])
    ap.add_argument("--show-order-flips", type=int, default=8)
    args = ap.parse_args()

    print("loading blob arm...", flush=True)
    new = load("blob")
    print(f"loading {args.against} arm...", flush=True)
    old = load(args.against)

    shared = sorted(set(new) & set(old))
    print(f"\n{len(new)} blob specs, {len(old)} {args.against} rows, "
          f"{len(shared)} in both")

    section("Render order, blob arm")
    orders = Counter(new[s].order for s in new)
    for o, label in ORDER_LABEL.items():
        print(f"  {label:18} {pct(orders.get(o, 0), len(new))}")

    section(f"Render order, {args.against} arm (derived from P6, never stated)")
    old_orders = Counter(old[s].order for s in old)
    for o, label in ORDER_LABEL.items():
        print(f"  {label:18} {pct(old_orders.get(o, 0), len(old))}")

    section("Order disagreement")
    flips = [s for s in shared if new[s].order != old[s].order]
    print(f"  {len(flips)}/{len(shared)} scenes ordered differently "
          f"({len(flips) / max(len(shared), 1) * 100:.1f}%)")
    pairs = Counter(f"{ORDER_LABEL[old[s].order]} -> {ORDER_LABEL[new[s].order]}"
                    for s in flips)
    for pair, n in pairs.most_common():
        print(f"    {pair:42} {n:4d}")

    if args.show_order_flips and flips:
        section(f"Why the blob moved the order (first {args.show_order_flips})")
        for s in flips[: args.show_order_flips]:
            print(f"  {s}  {ORDER_LABEL[old[s].order]} -> "
                  f"{ORDER_LABEL[new[s].order]}  [{new[s].genre}/{new[s].shape}]")
            print(f"      {new[s].why or '(no reason given)'}")

    section("Genre agreement")
    same_g = sum(1 for s in shared if new[s].genre == old[s].genre)
    print(f"  same genre         {pct(same_g, len(shared))}")
    print(f"  different genre    {pct(len(shared) - same_g, len(shared))}")
    moved = Counter(f"{old[s].genre} -> {new[s].genre}"
                    for s in shared if new[s].genre != old[s].genre)
    for pair, n in moved.most_common(8):
        print(f"    {pair:52} {n:4d}")

    section("Shape agreement (where the genre matched)")
    both_g = [s for s in shared if new[s].genre == old[s].genre]
    same_s = sum(1 for s in both_g if new[s].shape == old[s].shape)
    print(f"  same shape         {pct(same_s, len(both_g))}")
    print(f"  different shape    {pct(len(both_g) - same_s, len(both_g))}")

    section("What reaches the image model")
    nb = [len(new[s].addendum) for s in shared]
    ob = [len(old[s].prompt) + len(old[s].addendum) for s in shared]
    print(f"  blob      composed body      mean {sum(nb) // max(len(nb), 1):5d} chars")
    print(f"  {args.against:9} prompt + addendum  mean "
          f"{sum(ob) // max(len(ob), 1):5d} chars")
    held_new = sum(len(new[s].held) for s in shared)
    held_old = sum(len(old[s].held) for s in shared)
    print(f"  invisible picks withheld: blob {held_new}, {args.against} {held_old}")

    section("Structure the blob arm carries that the router had nowhere to put")
    specs = [json.loads(p.read_text(encoding="utf-8"))
             for p in sorted((paths.ROUTING / "blob").glob("*.json"))]
    ok = [d["spec"] for d in specs if d.get("status") == "ok" and d.get("spec")]
    z = [len(s["layout"]["zones"]) for s in ok]
    pa = [len(s["layout"]["paths"]) for s in ok]
    pr = [len(s["layout"]["props"]) for s in ok]
    counted = sum(1 for s in ok for p in s["layout"]["props"] if p.get("count", -1) > 0)
    print(f"  zones      mean {sum(z) / max(len(z), 1):4.1f}  max {max(z, default=0)}")
    print(f"  paths      mean {sum(pa) / max(len(pa), 1):4.1f}  max {max(pa, default=0)}")
    print(f"  props      mean {sum(pr) / max(len(pr), 1):4.1f}  max {max(pr, default=0)}")
    print(f"  props carrying a stated count: {counted}")
    print(f"  set pieces: {sum(1 for s in ok if s['render']['set_piece'])}")
    bad = [d for d in specs if d.get("status") != "ok"]
    if bad:
        print(f"\n  {len(bad)} scenes without a spec: "
              + ", ".join(f"{d['scene']}({d['status']})" for d in bad[:10]))
    fixed = [d for d in specs if d.get("mapper_notes")]
    if fixed:
        print(f"  {len(fixed)} specs the mapper corrected:")
        for d in fixed[:5]:
            print(f"    {d['scene']}: {d['mapper_notes'][0][:96]}")


if __name__ == "__main__":
    main()
