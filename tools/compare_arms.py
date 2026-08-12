"""Decide whether one arm is actually better than another, and by how much.

`layoutgen.evaluate.score` prints the two rates and the per-scene winner. That is enough
to see a difference and not enough to believe one, for two reasons this tool exists to
handle.

**The checks are not independent.** A scene contributes several requirements, judged from
the same pair of images, and they succeed and fail together - a render that missed the
brief misses most of its checklist. Treating 2,900 checks as 2,900 independent trials
makes any gap look decisive. The confidence interval here is a cluster bootstrap over
*scenes*, which is the unit that was actually sampled.

**The arms saw the same prompts.** So the comparison is paired, and the informative
quantity is not two rates but the requirements where the arms disagreed. A gap of two
points built from ten disagreements is noise; the same gap built from four hundred is a
finding. That is what the discordance table shows.

Usage:
    python -m tools.compare_arms blob_vs_answered
    python -m tools.compare_arms blob_vs_answered --stage iso --by order
"""

from __future__ import annotations

import argparse
import json
import random
import statistics as st
from collections import Counter, defaultdict

from layoutgen import arms as A
from layoutgen import paths

BOOT = 4000


def load(cmp: A.Comparison, stage: str) -> list[dict]:
    path = cmp.scores(stage)
    if not path.is_file():
        return []
    return [json.loads(x) for x in path.open() if x.strip()]


def pooled(rows: list[dict], arm: str) -> tuple[int, int]:
    met = sum(sum(bool(it["present"].get(arm)) for it in r["items"]) for r in rows)
    tot = sum(len(r["items"]) for r in rows)
    return met, tot


def bootstrap(rows: list[dict], a: str, b: str, seed: int = 7) -> tuple[float, float]:
    """A 95% interval for the pooled difference b - a, resampling whole scenes.

    Whole scenes rather than checks: the checks inside a scene are judged from one pair
    of images and are correlated, so resampling them individually would understate the
    spread by pretending each is fresh evidence.
    """
    rng = random.Random(seed)
    per = [(sum(bool(it["present"].get(a)) for it in r["items"]),
            sum(bool(it["present"].get(b)) for it in r["items"]),
            len(r["items"])) for r in rows]
    if not per:
        return 0.0, 0.0
    diffs = []
    n = len(per)
    for _ in range(BOOT):
        pick = [per[rng.randrange(n)] for _ in range(n)]
        tot = sum(x[2] for x in pick) or 1
        diffs.append(100 * (sum(x[1] for x in pick) - sum(x[0] for x in pick)) / tot)
    diffs.sort()
    return diffs[int(0.025 * BOOT)], diffs[int(0.975 * BOOT)]


def discordance(rows: list[dict], a: str, b: str) -> tuple[int, int, float]:
    """Checks where exactly one arm delivered, and whether the split is lopsided."""
    only_a = only_b = 0
    for r in rows:
        for it in r["items"]:
            x, y = bool(it["present"].get(a)), bool(it["present"].get(b))
            if x and not y:
                only_a += 1
            elif y and not x:
                only_b += 1
    p = 1.0
    if only_a + only_b:
        try:
            from scipy.stats import binomtest
            p = binomtest(min(only_a, only_b), only_a + only_b, 0.5).pvalue
        except ImportError:
            pass
    return only_a, only_b, p


def label(cmp: A.Comparison, rows: list[dict], runs, mode: str) -> dict[str, list[dict]]:
    """Split the scenes into groups, so a headline can be checked for where it came from."""
    out: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        scene = r["scene"]
        by_arm = A.rows_for(scene, runs)
        if mode == "order":
            orders = {a: (by_arm.get(a) or {}).get("order", "?") for a in cmp.arms}
            key = ("same order: " + list(orders.values())[0]
                   if len(set(orders.values())) == 1
                   else " vs ".join(f"{a}={o}" for a, o in orders.items()))
        elif mode == "genre":
            key = next((by_arm[a].get("genre", "") for a in cmp.arms
                        if by_arm.get(a, {}).get("genre")), "?")
        elif mode == "size":
            n = len(r["items"])
            key = "1-2 checks" if n <= 2 else "3-5 checks" if n <= 5 else "6+ checks"
        else:
            key = "all"
        out[key].append(r)
    return out


def report(cmp: A.Comparison, stage: str, rows: list[dict], runs, mode: str) -> None:
    a, b = cmp.arms[0], cmp.arms[-1]
    print(f"\n{'=' * 78}\n{cmp.id}  {stage}   {len(rows)} scenes, "
          f"{sum(len(r['items']) for r in rows)} checks")
    print(f"checklist: {'the author, via results/eval' if cmp.basis else 'the arms themselves'}")
    print("=" * 78)

    for arm in cmp:
        met, tot = pooled(rows, arm.id)
        print(f"  {arm.title:36s} {met:5d}/{tot:<5d} {100 * met / max(tot, 1):5.1f}%")

    lo, hi = bootstrap(rows, a, b)
    ma, ta = pooled(rows, a)
    mb, _ = pooled(rows, b)
    gap = 100 * (mb - ma) / max(ta, 1)
    verdict = ("no measurable difference" if lo <= 0 <= hi
               else f"{b} ahead" if lo > 0 else f"{a} ahead")
    print(f"\n  {b} - {a}: {gap:+.1f} points, 95% CI [{lo:+.1f}, {hi:+.1f}]  -> {verdict}")

    only_a, only_b, p = discordance(rows, a, b)
    print(f"  checks only {a} delivered: {only_a}    only {b}: {only_b}    "
          f"(sign test p={p:.2g})")
    agree = sum(len(r["items"]) for r in rows) - only_a - only_b
    print(f"  the arms agreed on {agree} of {agree + only_a + only_b} checks")

    win = Counter()
    for r in rows:
        sa = sum(bool(it["present"].get(a)) for it in r["items"])
        sb = sum(bool(it["present"].get(b)) for it in r["items"])
        win["tie" if sa == sb else (a if sa > sb else b)] += 1
    print(f"  per scene: {dict(win)}")

    if mode != "none":
        groups = label(cmp, rows, runs, mode)
        print(f"\n  split by {mode}:")
        rank = sorted(groups.items(), key=lambda kv: -len(kv[1]))
        for key, part in rank:
            if len(part) < 8:
                continue
            pa = pooled(part, a)
            pb = pooled(part, b)
            ra = 100 * pa[0] / max(pa[1], 1)
            rb = 100 * pb[0] / max(pb[1], 1)
            print(f"    {key[:44]:44s} n={len(part):3d}  {a[:8]} {ra:5.1f}%  "
                  f"{b[:8]} {rb:5.1f}%  {rb - ra:+5.1f}")


def extremes(cmp: A.Comparison, rows: list[dict], n: int) -> None:
    a, b = cmp.arms[0], cmp.arms[-1]
    scored = []
    for r in rows:
        sa = sum(bool(it["present"].get(a)) for it in r["items"])
        sb = sum(bool(it["present"].get(b)) for it in r["items"])
        scored.append((sb - sa, r["scene"], sa, sb, len(r["items"])))
    scored.sort()
    print(f"\n  worst {n} for {b}:")
    for d, s, sa, sb, t in scored[:n]:
        print(f"    {s}  {a} {sa}/{t}  {b} {sb}/{t}")
    print(f"  best {n} for {b}:")
    for d, s, sa, sb, t in reversed(scored[-n:]):
        print(f"    {s}  {a} {sa}/{t}  {b} {sb}/{t}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("comparison", choices=list(A.COMPARISONS))
    ap.add_argument("--stage", choices=paths.STAGES + ("both",), default="both")
    ap.add_argument("--by", choices=("order", "genre", "size", "none"), default="order")
    ap.add_argument("--show", type=int, default=0, help="list this many scenes each way")
    args = ap.parse_args()

    cmp = A.COMPARISONS[args.comparison]
    runs = A.load_runs()
    stages = paths.STAGES if args.stage == "both" else (args.stage,)
    for stage in stages:
        rows = load(cmp, stage)
        if not rows:
            print(f"\n{cmp.id} {stage}: nothing scored yet - run "
                  f"`python -m layoutgen.evaluate.score {cmp.id}`")
            continue
        report(cmp, stage, rows, runs, args.by)
        if args.show:
            extremes(cmp, rows, args.show)

    if len(stages) == 2:
        both = {st: {r["scene"]: r for r in load(cmp, st)} for st in paths.STAGES}
        shared = sorted(set(both["iso"]) & set(both["td"]))
        if shared:
            print(f"\n{'=' * 78}\nboth stages, {len(shared)} scenes in common")
            for arm in cmp:
                rates = []
                for st_ in paths.STAGES:
                    met, tot = pooled([both[st_][s] for s in shared], arm.id)
                    rates.append(100 * met / max(tot, 1))
                print(f"  {arm.title:36s} iso {rates[0]:5.1f}%   td {rates[1]:5.1f}%   "
                      f"mean {st.mean(rates):5.1f}%")


if __name__ == "__main__":
    main()
