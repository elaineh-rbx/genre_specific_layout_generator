"""Score every decider against the upstream agents' tags, on one shared set of scenes.

`genre_truth.py` compares two arms. There are now three, and they do not all decide the
same way: the router asks the gateway three narrow questions, the blob arm asks it one wide
one, and the agent arm is a Cursor subagent per scene reading `genre-choice` with tool
access. Only the last of those is an agent in the sense the upstream tags were produced by,
which is the comparison this script exists to make.

One correction matters more than the arithmetic. The upstream tags were written against the
*previous* document, whose shapes were per-genre, and the shared catalogue absorbed twelve
of those ids under new names - `arena-flat` became `space-bounded`, `world-single` became
`world-open`. Comparing the raw strings scores a rename as a disagreement and quietly
penalises every arm running on the new document, which is all of them. Both sides go
through `SHAPE_MIGRATION` first, so what is left is a genuine difference of opinion about
the shape rather than a difference of vocabulary.

Genre is scored twice, as it always has been: against the first tag, and against any tag.
A scene the upstream agent gave two tags is one it did not consider unambiguous, so
insisting on the first would score a defensible answer as wrong.

Usage:
    python tools/score_arms.py
"""

from __future__ import annotations

import json
import math
import pathlib
import re
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from layoutgen import paths                                       # noqa: E402
from layoutgen.model import rules as br                           # noqa: E402

ANSWERED = paths.ROUTING / "answered"


def slug_to_genre() -> dict[str, str]:
    """Upstream tag -> our genre name. Parentheticals are dropped before slugging."""
    out = {}
    for name in br.GENRES:
        bare = re.sub(r"\s*\(.*?\)", "", name)
        out[bare.lower().replace(" & ", "-").replace(" ", "-")] = name
    return out


def shape(s: str) -> str:
    """A shape id in the shared catalogue's vocabulary, whichever era wrote it."""
    return br.SHAPE_MIGRATION.get(s or "", s or "")


def load() -> tuple[dict, dict, dict, dict]:
    """Upstream tags plus the three arms, each keyed by scene."""
    truth, router = {}, {}
    m = slug_to_genre()
    for p in sorted(ANSWERED.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        up = d.get("upstream_skill") or {}
        if named := [m[t] for t in (up.get("genres") or []) if t in m]:
            truth[d["scene"]] = {"genres": named, "shape": shape(up.get("shape", "")),
                                 "preset": up.get("preset") or "",
                                 "route": ",".join(sorted(up.get("pipeline") or []))}
        if c := d.get("config"):
            router[d["scene"]] = {"genre": c.get("genre", ""),
                                  "shape": shape(c.get("shape", "")),
                                  "preset": c.get("preset") or "",
                                  "route": ",".join(sorted(c.get("route") or []))}
    arms = {}
    for name, sub in (("blob", "blob"), ("agent", "agent_spec_gateway")):
        out = {}
        for p in sorted((paths.ROUTING / sub).glob("*.json")):
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("status") != "ok" or not d.get("spec"):
                continue
            s = d["spec"]
            out[d["scene"]] = {"genre": s.get("genre", ""),
                               "shape": shape(s.get("shape", "")),
                               "preset": (s.get("preset") or "").replace("none", ""),
                               "route": ",".join(sorted(s.get("route") or []))}
        arms[name] = out
    return truth, router, arms["blob"], arms["agent"]


def pct(n: int, d: int) -> str:
    return f"{n:4d}/{d:<4d} {100 * n / d:5.1f}%" if d else "        n/a"


def sign_p(a: int, b: int) -> float:
    """Two-sided sign test over the scenes where exactly one arm is right."""
    n = a + b
    if not n:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(max(a, b), n + 1))
    return min(2 * tail / 2 ** n, 1.0)


def main() -> None:
    truth, router, blob, agent = load()
    arms = {"router (3 calls)": router, "blob (1 wide call)": blob,
            "agent (subagents)": agent}
    shared = sorted(set(truth) & set(router) & set(blob) & set(agent))
    print(f"upstream tags on {len(truth)} scenes; all three arms cover {len(shared)}")
    print(f"{sum(1 for s in shared if len(truth[s]['genres']) > 1)} of those carry "
          f"more than one tag")

    print("\nGENRE")
    print(f"  {'arm':<20}{'first tag':<18}{'any tag':<18}")
    hit: dict[str, set[str]] = {}
    for name, arm in arms.items():
        first = {s for s in shared if arm[s]["genre"] == truth[s]["genres"][0]}
        among = {s for s in shared if arm[s]["genre"] in truth[s]["genres"]}
        hit[name] = among
        print(f"  {name:<20}{pct(len(first), len(shared)):<18}"
              f"{pct(len(among), len(shared)):<18}")

    print("\n  head to head on genre (any tag), disagreements only")
    names = list(arms)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            only_a, only_b = len(hit[a] - hit[b]), len(hit[b] - hit[a])
            print(f"    {a:<20} vs {b:<20} {only_a:3d}:{only_b:<3d} "
                  f"p={sign_p(only_a, only_b):.4f}")

    # Shape and preset only mean anything inside a genre, so each is scored twice: over
    # every scene, and over the scenes where that arm already agreed on the genre. Without
    # the second column an arm is charged twice for one wrong genre.
    for fld in ("shape", "preset", "route"):
        have = [s for s in shared if truth[s][fld]]
        print(f"\n{fld.upper()}  ({len(have)} scenes where upstream stated one)")
        print(f"  {'arm':<20}{'all scenes':<18}{'genre also agrees':<18}")
        for name, arm in arms.items():
            ok = {s for s in have if arm[s][fld] == truth[s][fld]}
            sub = [s for s in have if arm[s]["genre"] in truth[s]["genres"]]
            oks = {s for s in sub if arm[s][fld] == truth[s][fld]}
            print(f"  {name:<20}{pct(len(ok), len(have)):<18}"
                  f"{pct(len(oks), len(sub)):<18}")

    print("\nWHERE THE ARMS AGREE WITH EACH OTHER (not with upstream)")
    for fld in ("genre", "shape", "preset"):
        rb = sum(1 for s in shared if router[s][fld] == blob[s][fld])
        ra = sum(1 for s in shared if router[s][fld] == agent[s][fld])
        ba = sum(1 for s in shared if blob[s][fld] == agent[s][fld])
        print(f"  {fld:<8} router~blob {pct(rb, len(shared))}   "
              f"router~agent {pct(ra, len(shared))}   "
              f"blob~agent {pct(ba, len(shared))}")

    print("\nagent arm's most common departures from upstream (upstream -> agent)")
    miss = Counter((truth[s]["genres"][0], agent[s]["genre"])
                   for s in shared if agent[s]["genre"] not in truth[s]["genres"])
    for (t, p), n in miss.most_common(8):
        print(f"  {n:3d}  {t:<32} -> {p}")

    print("\nreach past the genre's typical shapes (the new document's whole point)")
    for name, arm in arms.items():
        out = 0
        for s in shared:
            g = br.genre(arm[s]["genre"])
            if g is not None and arm[s]["shape"] and arm[s]["shape"] not in g.typical:
                out += 1
        print(f"  {name:<20}{pct(out, len(shared))}")

    print("\nno shape at all (No Genre, or a described shape)")
    for name, arm in arms.items():
        n = sum(1 for s in shared if not arm[s]["shape"])
        ng = sum(1 for s in shared if arm[s]["genre"] == br.NO_GENRE_NAME)
        print(f"  {name:<20}{pct(n, len(shared))}   of which No Genre: {ng}")


if __name__ == "__main__":
    main()
