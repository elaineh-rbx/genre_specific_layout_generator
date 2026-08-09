"""Golden-set evaluation harness for the layout-intake skill network.

Three subcommands:

    batch   split the golden-set CSV into blind batch files for lanes
    check   validate lane output records against the schema
    merge   fold records back into an annotated CSV plus aggregate tables

Blindness is enforced here: batch files carry only an opaque item id, the
user's prompt, and the enriched prompt. The CSV's own genre columns never
reach a lane, and batches are shuffled so batch composition cannot leak a
label either.

The agree/defensible/disagree verdict is computed in `merge`, not by a lane.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import random
import sys
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent.parent
ROOT = EVAL_ROOT.parent
EVAL_DIR = EVAL_ROOT / "data"
CSV_PATH = EVAL_DIR / "layout gen prompt golden set  - build 600 (prod subgenre balanced).csv"
BATCH_DIR = EVAL_DIR / "batches"
RECORD_DIR = EVAL_DIR / "records"

# Our 15 genre slugs, plus the two outcomes the CSV's taxonomy cannot express.
OUR_GENRES = {
    "action", "adventure", "obby-platformer", "party-casual", "puzzle", "rpg",
    "roleplay-avatar-sim", "shooter", "simulation", "strategy", "survival",
    "sports", "racing", "infinite-runner", "entertainment",
}
OUR_NON_GENRE = {"none", "p5"}

# CSV label -> the set of our slugs that count as agreement.
#
# Several CSV labels are coarser than ours by design. `sports_and_racing` is one
# Roblox genre that we split on finish condition; Roblox files Runner under
# Obby & Platformer where we treat it separately. Both of ours are correct
# against the one label, so both count as agreement and the split is recorded
# separately in `taxonomy_note`.
GENRE_MAP: dict[str, set[str]] = {
    "simulation": {"simulation"},
    "roleplay_and_avatar_sim": {"roleplay-avatar-sim"},
    "obby_and_platformer": {"obby-platformer", "infinite-runner"},
    "adventure": {"adventure"},
    "shooter": {"shooter"},
    "survival": {"survival"},
    "rpg": {"rpg"},
    "action": {"action"},
    "sports_and_racing": {"sports", "racing"},
    "party_and_casual": {"party-casual"},
    "strategy": {"strategy"},
    "puzzle": {"puzzle"},
    "other_entertainment": {"entertainment"},
    # No clean equivalent in our taxonomy: a shopping/social space is a place,
    # so several of ours are defensible and none is canonical.
    "avatar_shopping": set(),
    "social": set(),
    "shopping": set(),
    # The CSV has no opinion, so there is nothing to agree or disagree with.
    "unknown": set(),
    "unspecified": set(),
}

# CSV labels that are coarser than our taxonomy: a mismatch here is a known
# split, not an error.
COARSE_LABELS = {"obby_and_platformer", "sports_and_racing"}
# CSV labels with no equivalent on our side at all.
NO_EQUIVALENT = {"avatar_shopping", "social", "shopping"}
# CSV labels carrying no opinion.
NO_OPINION = {"unknown", "unspecified", ""}

# Subgenres that land on the "usually no space" list in genre-choice Stage B.
# Every one of these is labelled with a real genre and a full_game_map scope in
# the CSV, so a P5 route here is signal rather than disagreement.
P5_CANDIDATE_SUBGENRES = {
    "idle", "incremental_simulator", "music_audio", "match_merge", "word",
    "board_card_games",
}


def load_rows() -> list[dict]:
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for i, r in enumerate(rows):
        r["_row"] = i + 2  # 1-based with header
    return rows


def is_usable(r: dict) -> tuple[bool, str]:
    """Rows we refuse to send to a lane, with the reason."""
    if r["remove"].strip():
        return False, "flagged remove in source"
    p = r["initial_prompt"].strip()
    if p == "#ERROR!":
        return False, "source cell is a spreadsheet error"
    if not p:
        return False, "empty prompt"
    return True, ""


def item_id(r: dict) -> str:
    return f"P{r['_row']:04d}"


def cmd_batch(args: argparse.Namespace) -> int:
    rows = load_rows()
    usable, skipped = [], []
    for r in rows:
        ok, why = is_usable(r)
        (usable if ok else skipped).append((r, why))

    pool = [r for r, _ in usable]
    rng = random.Random(args.seed)
    rng.shuffle(pool)

    if args.only:
        wanted = set(args.only.split(","))
        pool = [r for r in pool if item_id(r) in wanted]
    elif args.exclude_batches:
        done = set()
        for f in BATCH_DIR.glob("*.json"):
            for item in json.loads(f.read_text(encoding="utf-8")):
                done.add(item["item_id"])
        pool = [r for r in pool if item_id(r) not in done]

    if args.limit:
        pool = pool[: args.limit]

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    RECORD_DIR.mkdir(parents=True, exist_ok=True)

    size = args.size
    batches = [pool[i : i + size] for i in range(0, len(pool), size)]
    contents: list[list[dict]] = [
        [
            {
                "item_id": item_id(r),
                "prompt": r["initial_prompt"],
                "enriched": r["initial_scene_subprompt_enriched"],
            }
            for r in batch
        ]
        for batch in batches
    ]

    # Calibration: re-issue a few prompts to a *different* lane under a "b"
    # suffix. Two lanes given the same prompt should produce the same record;
    # with 60+ lanes sharing one canonical vocabulary, that is the only cheap
    # way to find out whether they actually do. The copies are excluded from
    # the merged CSV and compared by the `calibrate` subcommand.
    calibration_pairs = []
    if args.calibration and len(contents) > 1:
        picks = rng.sample(range(len(contents)), min(args.calibration, len(contents)))
        for src in picks:
            item = rng.choice(contents[src])
            dst = rng.choice([i for i in range(len(contents)) if i != src])
            contents[dst].append({**item, "item_id": item["item_id"] + "b"})
            calibration_pairs.append((item["item_id"], src + args.start_index,
                                      dst + args.start_index))

    written = []
    for n, items in enumerate(contents, start=args.start_index):
        path = BATCH_DIR / f"{args.prefix}-{n:02d}.json"
        path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        chars = sum(len(i["prompt"]) + len(i["enriched"]) for i in items)
        written.append((path.name, len(items), chars))

    print(f"{len(rows)} source rows, {len(pool)} selected, {len(skipped)} unusable")
    for r, why in skipped:
        print(f"  skipped {item_id(r)}: {why}")
    total_chars = sum(c for _, _, c in written)
    total_items = sum(n for _, n, _ in written)
    print(f"\n{len(written)} batches, {total_items} items, "
          f"{total_chars:,} chars (~{total_chars // 4:,} tokens)")
    biggest = max(written, key=lambda w: w[2])
    print(f"largest batch: {biggest[0]} at {biggest[2]:,} chars")
    if calibration_pairs:
        print(f"\n{len(calibration_pairs)} calibration duplicates:")
        for iid, src, dst in calibration_pairs:
            print(f"  {iid} in batch {src:02d} re-issued as {iid}b in batch {dst:02d}")
    return 0


REQUIRED_TOP = {"item_id", "handoff", "coverage", "gaps"}
REQUIRED_HANDOFF = {"genre_choice", "theme", "scale", "open_questions"}
REQUIRED_GC = {"genres", "shape", "preset", "pipeline", "image_prompt", "layout_placement", "notes"}
REQUIRED_COVERAGE = {
    "verdict", "captured", "missing", "enriched_invented",
    "preset_derived", "preset_rejected",
}
COVERAGE_VERDICTS = {"complete", "partial", "insufficient"}

# Where an ask actually has to be satisfied. The layout pipeline owns `image`
# and `layout`; everything else is real but belongs to a different consumer,
# and separating the two is what turns the unmatched pile into an actionable
# list of missing options.
DESTINATIONS = {
    "image", "layout", "ui", "audio", "sky", "progression",
    "mechanics", "constraint", "metadata", "unclear",
}
LAYOUT_PIPELINE_DESTINATIONS = {"image", "layout"}

# Only prompt records. The adjudication lanes also write into the records
# directory and key their verdicts by the same item_ids, so a bare "*.jsonl"
# would let a one-line verdict object collide with — and potentially replace —
# the full record for that prompt.
RECORD_GLOB = "batch-*.jsonl"


def load_records(paths: list[Path]) -> list[dict]:
    """Parse JSONL, tolerating what agents writing files on Windows produce.

    PowerShell's redirection writes a UTF-8 BOM, which makes the first line of
    an otherwise perfect file unparseable; a lane occasionally wraps output in
    a markdown fence out of habit. Both are recoverable without asking anyone
    to redo work, so recover them rather than dropping records.
    """
    out = []
    for p in paths:
        # utf-8-sig strips a leading BOM; the per-line strip catches a BOM that
        # landed mid-file from an append rather than at the start.
        for ln, raw in enumerate(p.read_text(encoding="utf-8-sig").splitlines(), 1):
            line = raw.lstrip("\ufeff").strip()
            if not line or line.startswith("```"):
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                rec = repair_truncated(line)
                if rec is None:
                    print(f"  {p.name}:{ln} unrecoverable JSON", file=sys.stderr)
                    continue
                print(f"  {p.name}:{ln} repaired a truncated line", file=sys.stderr)
                rec["_repaired"] = True
            rec["_src"] = p.name
            out.append(rec)
    return out


def repair_truncated(line: str) -> dict | None:
    """Close a record that lost its trailing brackets to a short write.

    Several lanes appended lines a character or two shy of complete. The
    content is intact and re-running the prompt to recover a `}` would be
    absurd, so close the open containers and re-parse. Anything that still
    fails is left to the caller to report rather than guessed at.
    """
    depth = []
    in_string = False
    escaped = False
    for ch in line:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            depth.append(ch)
        elif ch in "}]" and depth:
            depth.pop()
    if not depth and not in_string:
        return None

    candidate = line
    if in_string:
        candidate += '"'
    candidate += "".join("}" if c == "{" else "]" for c in reversed(depth))
    try:
        rec = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return rec if isinstance(rec, dict) else None


def validate(rec: dict) -> list[str]:
    errs = []
    missing = REQUIRED_TOP - rec.keys()
    if missing:
        errs.append(f"missing top-level keys: {sorted(missing)}")
        return errs
    h = rec["handoff"]
    if not isinstance(h, dict):
        return ["handoff is not an object"]
    hm = REQUIRED_HANDOFF - h.keys()
    if hm:
        errs.append(f"handoff missing: {sorted(hm)}")
    gc = h.get("genre_choice")
    if not isinstance(gc, dict):
        errs.append("handoff.genre_choice is not an object")
    else:
        gm = REQUIRED_GC - gc.keys()
        if gm:
            errs.append(f"genre_choice missing: {sorted(gm)}")
        for g in gc.get("genres", []):
            if g not in OUR_GENRES:
                errs.append(f"unknown genre slug {g!r}")
        if not gc.get("pipeline"):
            errs.append("pipeline is empty")
    cov = rec["coverage"]
    if not isinstance(cov, dict):
        errs.append("coverage is not an object")
    else:
        cm = REQUIRED_COVERAGE - cov.keys()
        if cm:
            errs.append(f"coverage missing: {sorted(cm)}")
        if cov.get("verdict") not in COVERAGE_VERDICTS:
            errs.append(f"coverage.verdict {cov.get('verdict')!r} not in {sorted(COVERAGE_VERDICTS)}")

    gaps = rec.get("gaps")
    if not isinstance(gaps, dict):
        errs.append("gaps is not an object")
        return errs
    for i, u in enumerate(gaps.get("unmatched_options") or []):
        if not isinstance(u, dict):
            errs.append(f"unmatched_options[{i}] is not an object")
            continue
        if not (u.get("canonical") or "").strip():
            errs.append(f"unmatched_options[{i}] has no canonical phrase")
        if u.get("destination") not in DESTINATIONS:
            errs.append(
                f"unmatched_options[{i}] destination {u.get('destination')!r} "
                f"not in {sorted(DESTINATIONS)}"
            )
    for key in ("genre_gap", "skill_gap"):
        g = gaps.get(key)
        if g is None:
            continue
        if not isinstance(g, dict):
            errs.append(f"{key} must be null or an object with name and why")
        elif not (g.get("name") or "").strip():
            errs.append(f"{key} has no name, so it cannot be grouped")
    return errs


def cmd_check(args: argparse.Namespace) -> int:
    paths = sorted(RECORD_DIR.glob(args.glob))
    if not paths:
        print(f"no record files matching {args.glob} in {RECORD_DIR}")
        return 1
    recs = load_records(paths)
    expected = set()
    for f in BATCH_DIR.glob("*.json"):
        for item in json.loads(f.read_text(encoding="utf-8")):
            expected.add(item["item_id"])

    bad = 0
    seen = collections.Counter()
    for rec in recs:
        seen[rec.get("item_id")] += 1
        errs = validate(rec)
        if errs:
            bad += 1
            print(f"{rec['_src']} {rec.get('item_id')}:")
            for e in errs:
                print(f"    {e}")
    dupes = [k for k, v in seen.items() if v > 1]
    print(f"\n{len(recs)} records, {bad} with schema errors")
    if dupes:
        print(f"duplicate item_ids: {sorted(dupes)}")

    # A repaired record parsed only because we closed its brackets for it, so
    # whatever the lane had not written yet is simply absent. While lanes are
    # running this mostly catches files caught mid-write and is harmless, but a
    # repair surviving to the final check is silent data loss and the prompt
    # must be re-run. Name them so that is a decision rather than an accident.
    repaired = sorted(r.get("item_id") for r in recs if r.get("_repaired"))
    if repaired:
        print(f"{len(repaired)} records needed bracket repair and may be missing "
              f"fields: {repaired}")
        print("  re-run these if any lane has finished; mid-write files are fine")

    gap = expected - seen.keys()
    if gap and args.glob == RECORD_GLOB:
        print(f"{len(gap)} batched prompts have no record: {sorted(gap)[:20]}")
    return 1 if bad or dupes else 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    """Compare each calibration duplicate against its original.

    Agreement on genre is the headline; agreement on the canonical vocabulary
    matters more for the aggregation, since the whole common-versus-one-off
    split depends on two lanes naming the same concept the same way.
    """
    recs = {r["item_id"]: r for r in load_records(sorted(RECORD_DIR.glob(RECORD_GLOB)))}
    pairs = [(k[:-1], k) for k in recs if k.endswith("b") and k[:-1] in recs]
    if not pairs:
        print("no calibration pairs found")
        return 0

    genre_same = shape_same = 0
    vocab_overlap = []
    for a, b in sorted(pairs):
        ra, rb = recs[a], recs[b]
        ga = (ra["handoff"]["genre_choice"].get("genres") or [None])[0]
        gb = (rb["handoff"]["genre_choice"].get("genres") or [None])[0]
        sa = (ra["handoff"]["genre_choice"].get("shape") or {}).get("id")
        sb = (rb["handoff"]["genre_choice"].get("shape") or {}).get("id")
        ca = {(u.get("canonical") or "").lower() for u in ra["gaps"].get("unmatched_options") or []}
        cb = {(u.get("canonical") or "").lower() for u in rb["gaps"].get("unmatched_options") or []}
        both = len(ca & cb)
        either = len(ca | cb)
        jaccard = both / either if either else 1.0
        vocab_overlap.append(jaccard)
        genre_same += ga == gb
        shape_same += sa == sb
        flag = "" if ga == gb else "   <-- genre differs"
        print(f"{a}: genre {ga} vs {gb}{flag}")
        print(f"    shape {sa} vs {sb}")
        print(f"    canonical overlap {both}/{either} = {jaccard:.2f}")
        if ca ^ cb:
            print(f"    only one lane said: {sorted(ca ^ cb)}")

    n = len(pairs)
    print(f"\n{n} pairs: genre agrees {genre_same}/{n}, shape agrees {shape_same}/{n}, "
          f"mean canonical overlap {sum(vocab_overlap) / n:.2f}")
    return 0


def grade(csv_label: str, our_genres: list[str], pipeline: list[str]) -> tuple[str, str]:
    """Three-way verdict plus a note naming why it is not a plain agreement.

    A binary good/bad would report ~40 rows as failures that are artifacts of
    two different taxonomies, so the middle value carries its reason.
    """
    label = (csv_label or "").strip()
    ours = [g for g in our_genres if g in OUR_GENRES]
    accept = GENRE_MAP.get(label, set())

    if "P5" in pipeline:
        return "defensible", "routed P5 (no traversable space); the CSV taxonomy has no P5 outcome"
    if label in NO_OPINION:
        return "defensible", "CSV has no genre opinion on this row"
    if not ours:
        return "defensible", "classified no-genre; the CSV taxonomy has no no-genre outcome"

    dominant = ours[0]
    if dominant in accept:
        if label in COARSE_LABELS and len(accept) > 1:
            return "agree", f"agrees within the coarse {label!r} bucket; we resolve it to {dominant!r}"
        return "agree", ""
    if any(g in accept for g in ours[1:]):
        return "defensible", f"{label!r} is present as a secondary genre; dominance call differs"
    if label in NO_EQUIVALENT:
        return "defensible", f"{label!r} has no equivalent in our 15 genres"
    if not accept:
        return "defensible", f"{label!r} is unmapped in our taxonomy"
    return "disagree", f"CSV {label!r} vs ours {dominant!r}"


NEW_COLUMNS = [
    "eval_our_genre",
    "eval_our_genres_all",
    "eval_genre_verdict",
    "eval_verdict_note",
    "eval_shape",
    "eval_preset",
    "eval_pipeline",
    "eval_theme",
    "eval_scale_band",
    "eval_p5_routed",
    "eval_p5_candidate",
    "eval_coverage_verdict",
    "eval_preset_derived",
    "eval_preset_rejected",
    "eval_question_count",
    "eval_questions",
    "eval_unmatched_count",
    "eval_unmatched_options",
    "eval_off_pipeline_asks",
    "eval_genre_gap",
    "eval_skill_gap",
    "eval_adjudication",
    "eval_adjudication_why",
    "eval_status",
]

# A disagreement does not say who is wrong, and the pilot found the CSV label to
# be the weaker of the two on both disagreeing rows. Adjudication is a second,
# deliberately *sighted* pass over disagreements only: it sees the prompt and
# both labels and says which is better. Blindness matters for classification;
# for adjudication it would just be a handicap.
ADJUDICATION_PATH = EVAL_DIR / "adjudication.json"

# An ask seen this many times or more is a gap in the option set worth closing.
# Below it, it is a one-off that the free-text channel should carry instead.
# The line is a starting point, not a law — `aggregate.json` keeps the full
# distribution so it can be moved once the shape of the data is visible.
COMMON_ASK_THRESHOLD = 5


def gap_parts(g) -> tuple[str, str]:
    """Accept either the current {name, why} shape or a legacy bare sentence."""
    if not g:
        return "", ""
    if isinstance(g, str):
        return "", g
    return (g.get("name") or "").strip(), (g.get("why") or "").strip()


def pick_richer(a: dict, b: dict) -> dict:
    """Choose between two records for the same prompt.

    Only reachable when a lane is re-run to rescue prompts an earlier one never
    finished, so the realistic case is a full record against a stalled or
    bracket-repaired one. Prefer the intact record, then the one that found more
    to say; never let filename order decide it silently.
    """
    for rec in (a, b):
        other = b if rec is a else a
        if rec.get("_repaired") and not other.get("_repaired"):
            return other
    weigh = lambda r: len((r.get("gaps") or {}).get("unmatched_options") or [])
    return a if weigh(a) >= weigh(b) else b


def load_adjudication() -> dict[str, dict]:
    """Collect the sighted verdicts on genre disagreements.

    The adjudication lanes append JSONL as they go, so read those directly
    rather than making someone convert them by hand between every merge. A
    hand-written `adjudication.json` still wins, which leaves a way to correct
    an individual verdict without editing a lane's output.
    """
    adj: dict[str, dict] = {}
    for p in sorted(RECORD_DIR.glob("adjudication-*.jsonl")):
        for line in p.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip().lstrip("\ufeff")
            if not line or line.startswith("```"):
                continue
            try:
                v = json.loads(line)
            except json.JSONDecodeError:
                print(f"  {p.name}: unparseable verdict line", file=sys.stderr)
                continue
            if v.get("item_id") and v.get("better"):
                adj[v["item_id"]] = {"better": v["better"], "why": v.get("why", "")}
    if ADJUDICATION_PATH.exists():
        adj.update(json.loads(ADJUDICATION_PATH.read_text(encoding="utf-8")))
    return adj


def cmd_merge(args: argparse.Namespace) -> int:
    rows = load_rows()
    recs: dict[str, dict] = {}
    for rec in load_records(sorted(RECORD_DIR.glob(RECORD_GLOB))):
        iid = rec.get("item_id")
        if iid in recs:
            keep = pick_richer(recs[iid], rec)
            print(f"  {iid} appears in {recs[iid]['_src']} and {rec['_src']}; "
                  f"keeping {keep['_src']}", file=sys.stderr)
            recs[iid] = keep
        else:
            recs[iid] = rec
    adj = load_adjudication()

    out_rows = []
    stats = collections.Counter()
    verdict_by_label = collections.defaultdict(collections.Counter)
    unmatched = []
    questions = collections.Counter()
    genre_gaps, skill_gaps = [], []
    canonical = collections.Counter()
    destinations = collections.Counter()
    genre_gap_names = collections.Counter()
    skill_gap_names = collections.Counter()
    quantities = []

    for r in rows:
        iid = item_id(r)
        rec = recs.get(iid)
        blank = {c: "" for c in NEW_COLUMNS}
        ok, why = is_usable(r)
        if not ok:
            blank["eval_status"] = f"excluded: {why}"
            stats["excluded"] += 1
            out_rows.append({**r, **blank})
            continue
        if rec is None:
            blank["eval_status"] = "not evaluated"
            stats["not evaluated"] += 1
            out_rows.append({**r, **blank})
            continue

        gc = rec["handoff"]["genre_choice"]
        cov = rec["coverage"]
        gaps = rec.get("gaps", {})
        ours = gc.get("genres") or []
        pipeline = gc.get("pipeline") or []
        verdict, note = grade(r["aligned_game_genre"], ours, pipeline)
        shape = gc.get("shape") or {}
        scale = rec["handoff"].get("scale") or {}
        qs = cov.get("missing") or []
        um = gaps.get("unmatched_options") or []

        stats[verdict] += 1
        stats[f"coverage:{cov.get('verdict')}"] += 1
        verdict_by_label[r["aligned_game_genre"]][verdict] += 1
        for q in qs:
            questions[q.get("field", "?")] += 1
        for u in um:
            unmatched.append({"item_id": iid, "genre": ours[0] if ours else "none", **u})
            canonical[(u.get("canonical") or "?").strip().lower()] += 1
            destinations[u.get("destination") or "?"] += 1
            if u.get("quantity"):
                quantities.append({"item_id": iid, "quantity": u["quantity"],
                                   "canonical": u.get("canonical", "")})
        gg, sg = gap_parts(gaps.get("genre_gap")), gap_parts(gaps.get("skill_gap"))
        if gg[0] or gg[1]:
            genre_gaps.append({"item_id": iid, "name": gg[0], "why": gg[1],
                               "our_genre": ours[0] if ours else "none"})
            genre_gap_names[gg[0].lower() or "(unnamed)"] += 1
        if sg[0] or sg[1]:
            skill_gaps.append({"item_id": iid, "name": sg[0], "why": sg[1]})
            skill_gap_names[sg[0].lower() or "(unnamed)"] += 1

        p5 = "P5" in pipeline
        cand = r["inferred_game_subgenre"] in P5_CANDIDATE_SUBGENRES
        if p5:
            stats["p5_routed"] += 1
        if cand:
            stats["p5_candidate"] += 1
        if p5 and cand:
            stats["p5_hit"] += 1

        out_rows.append({
            **r,
            "eval_our_genre": ours[0] if ours else ("p5" if p5 else "none"),
            "eval_our_genres_all": "|".join(ours),
            "eval_genre_verdict": verdict,
            "eval_verdict_note": note,
            "eval_shape": shape.get("id") or "",
            "eval_preset": gc.get("preset") or "",
            "eval_pipeline": "|".join(pipeline),
            "eval_theme": rec["handoff"].get("theme") or "",
            "eval_scale_band": scale.get("band") or "",
            "eval_p5_routed": "yes" if p5 else "",
            "eval_p5_candidate": "yes" if cand else "",
            "eval_coverage_verdict": cov.get("verdict", ""),
            "eval_preset_derived": "|".join(cov.get("preset_derived") or []),
            "eval_preset_rejected": " | ".join(
                f"{x.get('id', '?')}: {x.get('why', '')}"
                for x in (cov.get("preset_rejected") or [])
            ),
            "eval_question_count": len(qs),
            "eval_questions": " | ".join(f"[{q.get('field','?')}] {q.get('ask','')}" for q in qs),
            "eval_unmatched_count": len(um),
            "eval_unmatched_options": " | ".join(u.get("text", "") for u in um),
            "eval_genre_gap": ": ".join(p for p in gg if p),
            "eval_skill_gap": ": ".join(p for p in sg if p),
            "eval_off_pipeline_asks": " | ".join(
                f"[{u.get('destination')}] {u.get('canonical')}"
                for u in um
                if u.get("destination") not in LAYOUT_PIPELINE_DESTINATIONS
            ),
            "eval_adjudication": (adj.get(iid) or {}).get("better", ""),
            "eval_adjudication_why": (adj.get(iid) or {}).get("why", ""),
            "eval_status": "evaluated",
        })
        if verdict == "disagree":
            stats[f"disagree_better:{(adj.get(iid) or {}).get('better', 'unadjudicated')}"] += 1
        if cov.get("preset_derived"):
            stats["rows_with_preset_derived_picks"] += 1
        if cov.get("preset_rejected"):
            stats["rows_where_a_preset_option_conflicts"] += 1

    fieldnames = [c for c in out_rows[0] if not c.startswith("_")]
    written_rows = out_rows
    if args.evaluated_only:
        written_rows = [r for r in out_rows if r["eval_status"] == "evaluated"]
    out_path = EVAL_DIR / args.out
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in written_rows:
            w.writerow(r)

    common = {k: v for k, v in canonical.most_common() if v >= COMMON_ASK_THRESHOLD}
    one_offs = [k for k, v in canonical.items() if v == 1]
    in_pipeline = sum(v for k, v in destinations.items() if k in LAYOUT_PIPELINE_DESTINATIONS)
    agg = {
        "stats": dict(sorted(stats.items())),
        "verdict_by_csv_label": {k: dict(v) for k, v in sorted(verdict_by_label.items())},
        "question_fields": dict(questions.most_common()),
        "asks": {
            "total": len(unmatched),
            "distinct_canonical": len(canonical),
            "common_threshold": COMMON_ASK_THRESHOLD,
            "common": common,
            "one_off_count": len(one_offs),
            "by_destination": dict(destinations.most_common()),
            "in_layout_pipeline": in_pipeline,
            "off_pipeline": len(unmatched) - in_pipeline,
            "all_canonical": dict(canonical.most_common()),
        },
        "quantities": quantities,
        "genre_gap_names": dict(genre_gap_names.most_common()),
        "skill_gap_names": dict(skill_gap_names.most_common()),
        "unmatched_options": unmatched,
        "genre_gaps": genre_gaps,
        "skill_gaps": skill_gaps,
    }
    (EVAL_DIR / "aggregate.json").write_text(
        json.dumps(agg, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"wrote {out_path.name} ({len(written_rows)} rows, +{len(NEW_COLUMNS)} columns)")
    print(f"wrote aggregate.json")
    print()
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    if unmatched:
        print(f"\n  asks: {len(unmatched)} total, {len(canonical)} distinct, "
              f"{len(one_offs)} seen once, {len(common)} seen {COMMON_ASK_THRESHOLD}+ times")
        print(f"  destinations: {in_pipeline} in the layout pipeline, "
              f"{len(unmatched) - in_pipeline} off it")
        for k, v in destinations.most_common():
            print(f"    {k}: {v}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("batch", help="write blind batch files")
    b.add_argument("--size", type=int, default=22)
    b.add_argument("--limit", type=int, default=0, help="0 = all")
    b.add_argument("--seed", type=int, default=20260807)
    b.add_argument("--prefix", default="batch")
    b.add_argument("--start-index", type=int, default=1)
    b.add_argument("--only", default="", help="comma-separated item_ids")
    b.add_argument("--exclude-batches", action="store_true",
                   help="skip item_ids already present in an existing batch file")
    b.add_argument("--calibration", type=int, default=0,
                   help="re-issue N prompts to a second lane to measure inter-lane agreement")
    b.set_defaults(func=cmd_batch)

    c = sub.add_parser("check", help="validate lane records")
    c.add_argument("--glob", default=RECORD_GLOB)
    c.set_defaults(func=cmd_check)

    cal = sub.add_parser("calibrate", help="compare duplicate prompts across lanes")
    cal.set_defaults(func=cmd_calibrate)

    m = sub.add_parser("merge", help="fold records into an annotated CSV")
    m.add_argument("--out", default="golden set 600 - genre and coverage eval.csv")
    m.add_argument("--evaluated-only", action="store_true",
                   help="drop rows with no record, for reviewing a partial run in a spreadsheet")
    m.set_defaults(func=cmd_merge)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
