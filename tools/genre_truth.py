"""How close each router gets to the upstream classification, and how close the
blob arm's prompts are to the arm the viewer shows.

The upstream handoffs carry a genre chosen by an agent reading the author's message
against the same document we use. Its tags are our genre names in slug form, so they
can be compared directly once un-slugged. A scene may carry more than one tag; we
score a pick as right if it is the first tag, and separately if it is any tag, because
a two-tag scene is one the upstream agent itself would not call unambiguous.

Forty-three scenes carry no tag at all. Those are dropped rather than counted wrong:
absence is a gap in the ground truth, not a wrong answer by anything downstream.
"""

from __future__ import annotations

import json
import math
import pathlib
import random
import re
from collections import Counter

from layoutgen import paths
from layoutgen.model import rules as br

STOP = set("""a an the and or of to in on at for with by from as is are be it its this that
these those into over under out up down off no not you your we our they their he she his
her i me my if then than so such very more most also just only can may will would should
there here what which who whom when where how all any both each few other some own same
too s t don now d ll m o re ve y ain aren couldn didn doesn hadn hasn haven isn ma mightn
mustn needn shan shouldn wasn weren won wouldn make makes made add adds added create
creates created use uses used include includes included player players game games map maps
build builds built""".split())

WORD = re.compile(r"[a-z][a-z'-]{2,}")


def slug_to_genre() -> dict[str, str]:
    """Upstream tag -> our genre name. Parentheticals are dropped before slugging."""
    out = {}
    for name in br.GENRES:
        bare = re.sub(r"\s*\(.*?\)", "", name)
        out[bare.lower().replace(" & ", "-").replace(" ", "-")] = name
    return out


def bag(text: str) -> set[str]:
    return {w for w in WORD.findall((text or "").lower()) if w not in STOP}


def truth() -> dict[str, list[str]]:
    """Scene -> upstream genre names, in the order the upstream agent listed them."""
    m = slug_to_genre()
    out: dict[str, list[str]] = {}
    for p in sorted((paths.ROUTING / "answered").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        tags = ((d.get("upstream_skill") or {}).get("genres")) or []
        named = [m[t] for t in tags if t in m]
        if named:
            out[d["scene"]] = named
    return out


def answered() -> dict[str, dict]:
    out = {}
    for p in sorted((paths.ROUTING / "answered").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("config"):
            out[d["scene"]] = d
    return out


def blob() -> dict[str, dict]:
    out = {}
    for p in sorted((paths.ROUTING / "blob").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("status") == "ok" and d.get("spec"):
            out[d["scene"]] = d
    return out


def score(picks: dict[str, str], gt: dict[str, list[str]]) -> tuple[int, int, int]:
    shared = [s for s in picks if s in gt]
    first = sum(1 for s in shared if picks[s] == gt[s][0])
    among = sum(1 for s in shared if picks[s] in gt[s])
    return first, among, len(shared)


def pct(n: int, d: int) -> str:
    return f"{n:4d}/{d:<4d} {100 * n / d:5.1f}%" if d else "   n/a"


def _boot(scenes: list[str], ok_a: set[str], ok_b: set[str],
          draws: int = 4000) -> tuple[float, float]:
    """Paired bootstrap over scenes for the accuracy gap, in points."""
    diffs = []
    n = len(scenes)
    for _ in range(draws):
        pick = random.choices(scenes, k=n)
        diffs.append(100 * sum((s in ok_b) - (s in ok_a) for s in pick) / n)
    diffs.sort()
    return diffs[int(0.025 * draws)], diffs[int(0.975 * draws)]


def sign_p(win_b: int, win_a: int) -> float:
    """Two-sided sign test. Only the disagreements carry information about which arm
    is better: if the two were equally good, each would fall either way at even odds."""
    n = win_b + win_a
    if not n:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(max(win_a, win_b), n + 1))
    return min(2 * tail / 2 ** n, 1.0)


def head_to_head(label: str, scenes: list[str], ok_a: set[str], ok_b: set[str]) -> None:
    n = len(scenes)
    win_b, win_a = len(ok_b - ok_a), len(ok_a - ok_b)
    lo, hi = _boot(scenes, ok_a, ok_b)
    gap = 100 * (len(ok_b) - len(ok_a)) / n
    print(f"  {label:<12}{pct(len(ok_a), n)}  {pct(len(ok_b), n)}   "
          f"{gap:+5.1f}  [{lo:+5.1f},{hi:+5.1f}]  "
          f"{win_b:3d}:{win_a:<3d} p={sign_p(win_b, win_a):.4f}")


def field(name: str, up: dict, arm: dict) -> tuple[dict[str, str], dict[str, str]]:
    """Scene -> upstream value and arm value, over scenes where upstream stated one."""
    return ({s: v for s, v in up.items() if v}, arm)


def main() -> None:
    gt, ans, blb = truth(), answered(), blob()
    print(f"ground truth: {len(gt)} scenes carry an upstream genre "
          f"({sum(1 for v in gt.values() if len(v) > 1)} carry more than one)")

    a_pick = {s: d["config"].get("genre", "") for s, d in ans.items()}
    b_pick = {s: d["spec"].get("genre", "") for s, d in blb.items()}

    print("\nGENRE, against the upstream agent's tags")
    print(f"{'arm':<26}{'exact (first tag)':<22}{'in the tag set':<22}")
    for label, picks in (("answered (router+answers)", a_pick),
                         ("blob (new pipeline)", b_pick)):
        f, am, n = score(picks, gt)
        print(f"  {label:<24}{pct(f, n):<22}{pct(am, n):<22}")

    both = [s for s in gt if s in a_pick and s in b_pick]
    ok_a = {s for s in both if a_pick[s] in gt[s]}
    ok_b = {s for s in both if b_pick[s] in gt[s]}
    print(f"\npaired on {len(both)} scenes:")
    print(f"  both match upstream      {pct(len(ok_a & ok_b), len(both))}")
    print(f"  only answered matches    {pct(len(ok_a - ok_b), len(both))}")
    print(f"  only blob matches        {pct(len(ok_b - ok_a), len(both))}")
    print(f"  neither matches          {pct(len(both) - len(ok_a | ok_b), len(both))}")

    # The rest of the config the upstream agent chose. Shape and preset are only
    # meaningful inside a genre, so they are also scored on the genre-agreeing subset:
    # a shape that disagrees only because the genre disagreed is already counted once.
    upstream: dict[str, dict] = {}
    for p in sorted((paths.ROUTING / "answered").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        upstream[d["scene"]] = (d.get("upstream_skill") or {})

    print("\nTHE WHOLE CONFIG, same scenes, upstream as truth")
    print(f"  {'field':<12}{'answered':<15}{'blob':<15}   {'gap':>5}  "
          f"{'95% CI':>15}  {'disagreements':>16}")
    rows = [
        ("genre", lambda s: upstream[s].get("genres") and
         slug_to_genre().get(upstream[s]["genres"][0]),
         lambda s: a_pick[s], lambda s: b_pick[s]),
        ("shape", lambda s: upstream[s].get("shape"),
         lambda s: ans[s]["config"].get("shape") or "",
         lambda s: blb[s]["spec"].get("shape") or ""),
        ("preset", lambda s: upstream[s].get("preset"),
         lambda s: ans[s]["config"].get("preset") or "",
         lambda s: blb[s]["spec"].get("preset") or ""),
        ("route", lambda s: ",".join(sorted(upstream[s].get("pipeline") or [])) or None,
         lambda s: ",".join(sorted(ans[s]["config"].get("route") or [])),
         lambda s: ",".join(sorted(blb[s].get("spec", {}).get("route") or []))),
    ]
    for name, tf, af, bf in rows:
        scenes = [s for s in both if tf(s)]
        head_to_head(name, scenes, {s for s in scenes if af(s) == tf(s)},
                     {s for s in scenes if bf(s) == tf(s)})

    agree_g = [s for s in both if a_pick[s] == b_pick[s] == (gt[s][0])]
    for name, tf, af, bf in rows[1:3]:
        scenes = [s for s in agree_g if tf(s)]
        head_to_head(f"{name} |genre", scenes,
                     {s for s in scenes if af(s) == tf(s)},
                     {s for s in scenes if bf(s) == tf(s)})

    miss = Counter((gt[s][0], b_pick[s]) for s in both if b_pick[s] not in gt[s])
    print("\nwhere blob departs from upstream most often (upstream -> blob):")
    for (t, p), n in miss.most_common(8):
        print(f"  {n:3d}  {t:<32} -> {p}")

    conf = Counter()
    for s in both:
        conf[(len(gt[s]) > 1, b_pick[s] in gt[s])] += 1
    print()
    for multi in (False, True):
        hit, tot = conf[(multi, True)], conf[(multi, True)] + conf[(multi, False)]
        lab = "upstream gave 2+ tags" if multi else "upstream gave one tag"
        print(f"  blob, {lab:<24}{pct(hit, tot)}")


if __name__ == "__main__":
    main()
