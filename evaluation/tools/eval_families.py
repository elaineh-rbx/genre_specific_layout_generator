"""Find game families the classifier splits across genres.

The "+1 Speed" family was found by hand: six prompts for one recognisable kind
of Roblox game, sent to four genres and five presets. No evaluation lane could
have found it, because each lane saw ten prompts and every one of those six
looked locally reasonable. It is only visible across the whole set.

This generalises that search. Group prompts by a distinctive shared phrase,
then report the groups whose genre assignment is most scattered. A family that
lands in one genre is working as intended; a family sprayed across four is
either a missing genre or a recogniser that fires on wording rather than on
what the game is.

    python tools/eval_families.py                 # most scattered first
    python tools/eval_families.py --min-rows 6
    python tools/eval_families.py --term "tower defense"
"""

from __future__ import annotations

import argparse
import collections
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_golden_set as E  # noqa: E402

# Words too common in a Roblox prompt to identify a family. "game", "make" and
# "roblox" appear almost everywhere; grouping on them just re-reports the whole
# corpus and its genre spread.
STOP = {
    "a", "an", "the", "and", "or", "of", "for", "with", "to", "in", "on", "at",
    "is", "are", "be", "it", "its", "that", "this", "you", "your", "i", "me",
    "my", "we", "can", "will", "would", "should", "make", "makes", "making",
    "create", "creates", "creating", "build", "building", "want", "wants",
    "need", "needs", "like", "please", "game", "games", "roblox", "map", "maps",
    "player", "players", "add", "adding", "new", "get", "gets", "have", "has",
    "there", "where", "when", "then", "some", "all", "more", "very", "just",
    "also", "but", "so", "if", "as", "by", "from", "up", "out", "into", "one",
    "two", "each", "them", "they", "their", "he", "she", "his", "her",
}


def phrases(text: str) -> set[str]:
    """Bigrams that could plausibly name a game family.

    Unigrams are excluded deliberately. A first version included them and the
    results were "red", "smooth" and "seconds" — ordinary words that appear in
    dozens of prompts across every genre, which is expected rather than
    informative. Families are named with two words: "tower defense", "hide and
    seek", "+1 speed", "escape room".
    """
    words = re.findall(r"[a-z0-9+]+", text.lower())
    out: set[str] = set()
    for a, b in zip(words, words[1:]):
        if a in STOP or b in STOP or len(a) < 2 or len(b) < 2:
            continue
        out.add(f"{a} {b}")
    return out


def fragmentation(genres: list[str]) -> float:
    """How badly one family is split, as distinct genres per prompt.

    Deliberately not entropy. Entropy rewards a phrase for appearing everywhere,
    which is how the first version surfaced only common words. This asks the
    narrower question that matters: of the prompts naming this one thing, how
    many different genres did they land in? Six prompts in four genres (0.67)
    beats thirty-six prompts in fifteen (0.42), which is the right ordering.
    """
    return len(set(genres)) / len(genres) if genres else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-rows", type=int, default=4,
                    help="a family needs at least this many prompts")
    ap.add_argument("--max-rows", type=int, default=12,
                    help="a family is a handful of prompts; above this it is a common word")
    ap.add_argument("--min-genres", type=int, default=3,
                    help="only report families split across at least this many genres")
    ap.add_argument("--term", default="", help="inspect one phrase instead of searching")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()

    rows = {E.item_id(r): r for r in E.load_rows()}
    recs = {r["item_id"]: r
            for r in E.load_records(sorted(E.RECORD_DIR.glob(E.RECORD_GLOB)))}

    # Calibration duplicates would double-count a family member and make a
    # perfectly consistent pair look like corroboration, so drop the copies.
    info = {}
    for iid, rec in recs.items():
        if iid.endswith("b"):
            continue
        row = rows.get(iid)
        if not row:
            continue
        gc = rec["handoff"]["genre_choice"]
        genres = gc.get("genres") or ["(no genre)"]
        info[iid] = {
            "prompt": row.get("initial_prompt", ""),
            "genre": genres[0],
            "preset": gc.get("preset") or "(none)",
        }

    index: dict[str, list[str]] = collections.defaultdict(list)
    for iid, d in info.items():
        for ph in phrases(d["prompt"]):
            index[ph].append(iid)

    families = []
    for ph, ids in index.items():
        if not (args.min_rows <= len(ids) <= args.max_rows):
            continue
        genres = [info[i]["genre"] for i in ids]
        presets = {info[i]["preset"] for i in ids}
        distinct = len(set(genres))
        if distinct < args.min_genres:
            continue
        families.append({
            "phrase": ph, "ids": ids, "genres": genres,
            "distinct": distinct, "presets": presets,
            "score": (fragmentation(genres), distinct),
        })

    if args.term:
        ids = index.get(args.term.lower(), [])
        print(f"'{args.term}': {len(ids)} prompts")
        for i in sorted(ids):
            d = info[i]
            print(f"  {i}  {d['genre']:22} {d['preset'][:26]:28} "
                  f"{' '.join(d['prompt'].split())[:80]}")
        return 0

    families.sort(key=lambda f: f["score"], reverse=True)
    print(f"{len(info)} prompts, {len(families)} two-word phrases in "
          f"{args.min_rows}-{args.max_rows} prompts split across "
          f"{args.min_genres}+ genres\n")
    for f in families[:args.limit]:
        spread = collections.Counter(f["genres"])
        pretty = ", ".join(f"{g} x{n}" if n > 1 else g
                           for g, n in spread.most_common())
        print(f"\"{f['phrase']}\"  {f['distinct']} genres / {len(f['ids'])} prompts "
              f"/ {len(f['presets'])} presets")
        print(f"      {pretty}")
        print(f"      {', '.join(sorted(f['ids']))}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
