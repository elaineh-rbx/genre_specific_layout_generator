"""Audit A - do the questions intake asks give a clear path to proceed?

Not a quality score. Three closed-form checks over the 620 golden-set records,
each with an answer you can point at.

1. LANDING   If the user answered, is there somewhere in the handoff to put it?
             The handoff carries genres, shape, preset, pipeline, image_prompt,
             layout_placement, theme, scale, and notes. `notes` is prose the
             pipeline cannot act on, so it is not a home. Geometry and volumes
             always have a home because `image_prompt` / `layout_placement`
             accept free text with `id: null`.

2. CLOSURE   Gaps recorded in the record that no question addresses - and,
             separately, gaps that no question *could* address because the
             schema has no field for the answer. The second is not a question
             defect and is counted apart from the first.

3. FORM      Does the question offer alternatives to choose between, or is it
             open-ended? Does it smuggle two asks into one?

`coverage.missing` and `handoff.open_questions` are gap+question pairs by
construction, so check 2 deliberately looks at gaps recorded *elsewhere*:
`skill_gap`, `genre_gap`, and a null `theme` that raised no theme question.

    python evaluation/tools/eval_ask_audit.py                # the three checks
    python evaluation/tools/eval_ask_audit.py --show goal    # one field, in full
    python evaluation/tools/eval_ask_audit.py --landing none # questions by landing
    python evaluation/tools/eval_ask_audit.py --residual     # what did not classify
    python evaluation/tools/eval_ask_audit.py --dump         # ask-audit.json
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CSV_PATH = DATA / "golden set 600 - genre and coverage eval.csv"
RECORDS = DATA / "records"
OUT = DATA / "ask-audit.json"

# --------------------------------------------------------------------------
# Where an answer lands.
#
#   field    a dedicated key in the handoff
#   option   an image_prompt / layout_placement entry, possibly `id: null`
#   partial  the spatial half lands; the rest of the answer has no home
#   none     nowhere - the answer could only become prose in `notes`
#
# Destination names follow the taxonomy the lane brief already used for
# `unmatched_options`, so this audit and the missing-channel analysis in the
# main report are counting on the same axis.
LANDING = {
    "theme": ("field", "theme"),
    "scale": ("field", "scale.band"),
    "shape": ("field", "shape"),
    "genre": ("field", "genres"),
    "spatial": ("option", "image_prompt / layout_placement"),
    "count": ("partial", "count, only if the thing counted is an option"),
    "goal": ("partial", "a WinnerZone can be placed; the condition itself cannot"),
    "player count": ("none", None),
    "progression": ("none", None),
    "ui": ("none", None),
    "audio": ("none", None),
    "sky": ("none", None),
    "multi-map": ("none", None),
    "mechanics": ("none", None),
    "metadata": ("none", None),
    "movement": ("none", None),
    "player identity": ("none", None),
    "difficulty": ("none", None),
    "platform": ("none", None),
    "constraint": ("none", None),
    "repair": ("none", None),
    "unclear": ("none", None),
}

# Field normalisation. The records hold 464 distinct `skill_gap` names and a
# long tail of ad-hoc `field` values, because inter-worker naming overlap on
# free text was 0.30 - so raw strings cannot be counted directly. First match
# wins, so specific patterns precede general ones.
FIELD_RULES = [
    ("multi-map", r"multi[- ]?map|several maps|map switching|separate maps|number of maps|map list|lobby and map|map count"),
    ("player count", r"player count|player capacity|lobby size|team size|how many players|player load|concurrent"),
    ("goal", r"\bgoals?\b|win(?:ning)? condition|lose condition|objective|end condition|victory|what ends|round end"),
    ("metadata", r"\btitle\b|game name|game description"),
    ("ui", r"\bui\b|\bhud\b|\bgui\b|menu|screen[- ]space|on[- ]screen|button|overlay"),
    ("audio", r"\baudio\b|music|\bsound|voice"),
    ("sky", r"\bsky\b|skybox|weather|time of day|lighting|day.?night"),
    ("progression", r"progress|econom|currenc|\bshop\b|upgrade|reward|unlock|\bstats?\b|inventory|loot|rebirth|quest reward"),
    ("theme", r"theme|aesthetic|art style|\bmood\b|palette|visual style|colour scheme|color scheme"),
    ("scale", r"\bscale\b|\bsize\b|how large|how big|how long.*cross|extent|\bstuds\b|dimension|footprint|how tall|how wide"),
    ("shape", r"shape|enclosure|vertical|topology|layout form|one continuous|same space|separate.*(?:zone|arena)"),
    ("genre", r"\bgenre\b|what kind of game|game type|what sort of game"),
    ("player identity", r"player identity|what you play as|character (?:type|species)|non[- ]default avatar|play as a"),
    ("movement", r"movement|traversal|locomotion|walk speed|jump height|\bfly\b|swim|climb ability|abilit"),
    ("difficulty", r"difficult|challenge level|how hard"),
    ("platform", r"platform|mobile|console|\bdevice\b|touch control"),
    ("mechanics", r"mechanic|script|behaviour|behavior|combat system|damage|animation"),
    ("count", r"\bcounts?\b|how many"),
    ("constraint", r"forbids|prohibit|must not|no clarifying"),
    # Not a missing field - the prompt itself is incoherent, unbounded, or
    # asks us to invent scope. A different problem with a different fix.
    ("repair", r"what is ['\"]|what do you mean|unbounded|'and more'|\band more\b|"
               r"propose additions|features specifically|as written|which features"),
]

# A question whose answer is geometry or a placed volume. These land in the
# handoff even with no matching option ID, per genre-choice's `id: null` rule,
# so they are checked before the non-spatial buckets can claim them.
SPATIAL = re.compile(
    r"\b(?:room|rooms|arena|zone|zones|area|areas|stable|station|stations|building|"
    r"buildings|interior|interiors|enterable|floor|wall|track|lane|path|course|"
    r"island|map|maps|terrain|platform|platforms|spawn|base|bases|hub|lobby|"
    r"storefront|street|corridor|tower|field|court|stage|runway|booth|booths|"
    r"alcove|alcoves|hoop|hoops|audience|house|houses|home|homes|placed|somewhere|"
    r"pickup|pickups|prop|props|structure|landmark|checkpoint|barrier|gate|door|"
    r"doors|cover|obstacle|bridge|entrance|capture point|territory|chas(?:e|ing)|"
    r"entity|hostile|set dressing|in the (?:world|map|space|level))\b",
    re.I,
)


def normalise_field(raw, ask=""):
    raw = re.sub(r"^free:\s*", "", (raw or "").strip().lower())
    if raw in LANDING and raw != "unclear":
        return raw
    uninformative = raw in ("", "free", "other", "unknown", "n/a", "clarification", "prompt completeness")
    hay = f"{raw} {ask}" if uninformative else raw
    for key, pattern in FIELD_RULES:
        if re.search(pattern, hay, re.I):
            return key
    # Nothing named it, so fall back on what the answer would be: a thing in
    # the map, or something with no spatial footprint at all.
    if SPATIAL.search(ask):
        return "spatial"
    return "unclear"


# ---------------------------------------------------------------- question form
STEM = r"(?:what|which|how|where|who|when|do(?:es)?|is|are|should|would|will|can|any)"


def question_form(ask):
    body = ask.strip().rstrip("?")
    tail = re.split(r"\s[-\u2013\u2014:]\s", body, maxsplit=1)
    segment = tail[1] if len(tail) > 1 else body
    alternatives = 0
    if re.search(r"\bor\b", segment, re.I):
        parts = [s for s in re.split(r",\s*|\bor\b", segment, flags=re.I) if s.strip()]
        alternatives = len(parts)
    compound = (
        ask.count("?") > 1
        or bool(re.search(r",\s*(?:and\s+)?" + STEM + r"\b", body, re.I))
        or bool(re.search(r"\band\s+(?:how|what|which|where)\b", body, re.I))
    )
    return ("closed" if alternatives >= 2 else "open"), compound, alternatives


# ------------------------------------------------------- skill_gap: ask or build?
# A gap fixed by *asking* is an information gap. A gap fixed by adding a field,
# channel, option, or genre is a schema gap - asking would not help, because the
# user already told us and we had nowhere to put it. The distinction matters:
# only the first is a question defect.
SCHEMA_GAP = re.compile(
    r"\bno\b[^.]{0,50}?\b(?:field|channel|concern|home|slot|key|carrier|handoff|"
    r"vocabulary|expression|baseline|pairing|route|option|representation|"
    r"destination|stream|column|tag)\b"
    r"|nowhere|no home|cannot (?:express|carry|record)|can'?t (?:express|carry|record)"
    r"|not expressible|unable to record|has no way",
    re.I,
)
RULE_GAP = re.compile(
    r"preset|\brule\b|ambiguous|contradict|cannot be separated|forbids|"
    r"precedence|instruction|guidance|wrong answer|misroute|conflict",
    re.I,
)


def gap_kind(name, why=""):
    text = f"{name} {why}"
    if SCHEMA_GAP.search(text):
        return "schema"
    if RULE_GAP.search(text):
        return "rule"
    # "no X option" / "no X for Y" phrasings that the schema pattern missed are
    # still overwhelmingly about a missing container rather than missing info.
    if re.match(r"\s*(?:no|missing|lacks?)\b", name, re.I):
        return "schema"
    return "information"


# ---------------------------------------------------------------- loading
def csv_rows():
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            row["item_id"] = f"P{i:04d}"
            yield row


def load_records():
    out = {}
    for path in sorted(RECORDS.glob("batch-*.jsonl")):
        for line in open(path, encoding="utf-8-sig"):
            line = line.strip().lstrip("\ufeff")
            if not line or line.startswith("```"):
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            iid = rec.get("item_id")
            if iid and not str(iid).endswith("b"):
                out[iid] = rec
    return out


def clean(text, cap=240):
    return re.sub(r"\s+", " ", (text or "").replace("\\n", " ")).strip()[:cap]


STOP = set("a an the is are do does should would will can any of to in on for be "
           "it this that or and how what which where who when much many big large "
           "long each one we you your our there they need needs".split())


def content_words(ask):
    return {w for w in re.findall(r"[a-z0-9']+", ask.lower()) if w not in STOP and len(w) > 2}


def collapse(asks):
    """The same question is frequently recorded twice - a terse version in
    `open_questions` and a fuller one in `coverage.missing`. Exact-text dedupe
    misses those, so near-duplicates within a row are collapsed too, keeping
    the more informative wording (closed beats open, then longer beats shorter).
    Returns the kept asks and how many were folded away."""
    kept = []
    for ask in sorted(asks, key=lambda a: (a["form"] != "closed", -len(a["ask"]))):
        words = content_words(ask["ask"])
        dup = False
        for other in kept:
            ow = content_words(other["ask"])
            union = words | ow
            if not union:
                continue
            overlap = len(words & ow) / len(union)
            # same field and mostly the same words, or one is a subset of the other
            if ask["field"] == other["field"] and (overlap >= 0.5 or words <= ow or ow <= words):
                dup = True
                other["also_asked"] = other.get("also_asked", 0) + 1
                break
        if not dup:
            kept.append(ask)
    return kept, len(asks) - len(kept)


def build(pre_only=False):
    recs = load_records()
    prompts = {r["item_id"]: r for r in csv_rows()}
    rows = []
    folded = 0

    for iid, rec in sorted(recs.items()):
        handoff = rec.get("handoff") or {}
        cov = rec.get("coverage") or {}
        gaps = rec.get("gaps") or {}

        sources = [("pre", handoff.get("open_questions") or [])]
        if not pre_only:
            sources.append(("blocked", cov.get("missing") or []))

        asked, seen = [], set()
        for source, items in sources:
            for q in items:
                if not isinstance(q, dict):
                    continue
                ask = clean(q.get("ask"))
                if not ask or ask.lower() in seen:
                    continue
                seen.add(ask.lower())
                field = normalise_field(q.get("field"), ask)
                form, compound, alts = question_form(ask)
                landing, where = LANDING[field]
                asked.append({
                    "field": field, "raw_field": (q.get("field") or "").lower(),
                    "ask": ask, "source": source, "form": form,
                    "compound": compound, "alternatives": alts,
                    "landing": landing, "where": where,
                })

        asked, n_folded = collapse(asked)
        folded += n_folded
        asked_fields = {a["field"] for a in asked}

        unasked, schema_gaps = [], []
        sg = gaps.get("skill_gap")
        if isinstance(sg, dict) and sg.get("name"):
            kind = gap_kind(sg["name"], sg.get("why") or "")
            field = normalise_field(sg["name"], sg.get("why") or "")
            entry = {"kind": kind, "field": field, "detail": clean(sg["name"], 80)}
            if kind == "schema":
                schema_gaps.append(entry)
            elif field not in asked_fields:
                unasked.append(entry)
        gg = gaps.get("genre_gap")
        if isinstance(gg, dict) and gg.get("name"):
            # No genre fitting is a catalogue gap, not something a question fixes.
            schema_gaps.append({"kind": "catalogue", "field": "genre",
                                "detail": clean(gg["name"], 80)})
        if handoff.get("theme") in (None, "", "null") and "theme" not in asked_fields:
            unasked.append({"kind": "information", "field": "theme",
                            "detail": "theme null and no theme question raised"})

        blocked = [a for a in asked if a["landing"] == "none"]
        partial = [a for a in asked if a["landing"] == "partial"]

        if not asked and not unasked:
            verdict = "nothing needed"
        elif blocked:
            verdict = "asked, answer has no home"
        elif unasked:
            verdict = "gap left unasked"
        elif partial:
            verdict = "answer lands only partly"
        else:
            verdict = "clear path"

        rows.append({
            "id": iid,
            "prompt": clean((prompts.get(iid) or {}).get("initial_prompt"), 300),
            "coverage_verdict": cov.get("verdict"),
            "asked": asked, "unasked": unasked, "schema_gaps": schema_gaps,
            "verdict": verdict,
        })
    return rows, folded


def bar(count, total, width=26):
    return "#" * int(round(width * count / total)) + "." * (width - int(round(width * count / total))) if total else ""


def main():
    pre_only = "--pre" in sys.argv
    rows, folded = build(pre_only)
    total = len(rows)
    asks = [a for r in rows for a in r["asked"]]
    n = len(asks)

    if "--show" in sys.argv:
        want = sys.argv[sys.argv.index("--show") + 1].lower()
        hits = [(r, a) for r in rows for a in r["asked"] if a["field"] == want]
        land, where = LANDING.get(want, ("?", None))
        print(f"{want}: {len(hits)} question(s)   landing={land}   where={where}\n")
        for r, a in hits[:50]:
            print(f"{r['id']}  [{a['form']}{'/compound' if a['compound'] else ''}]  raw={a['raw_field']!r}")
            print(f"   ASK  {a['ask']}\n")
        return

    if "--landing" in sys.argv:
        want = sys.argv[sys.argv.index("--landing") + 1].lower()
        hits = [(r, a) for r in rows for a in r["asked"] if a["landing"] == want]
        print(f"{len(hits)} question(s) with landing={want}\n")
        for r, a in hits[:80]:
            print(f"{r['id']}  [{a['field']}]  {a['ask']}")
        return

    if "--residual" in sys.argv:
        print("Questions that did not classify to a field:\n")
        for r in rows:
            for a in r["asked"]:
                if a["field"] == "unclear":
                    print(f"{r['id']}  raw={a['raw_field']!r}  {a['ask']}")
        print("\nskill_gaps classified as information (not schema, not rule):\n")
        for r in rows:
            for u in r["unasked"]:
                if u["kind"] == "information" and u["field"] != "theme":
                    print(f"{r['id']}  [{u['field']}]  {u['detail']}")
        return

    scope = "open_questions only" if pre_only else "open_questions + coverage.missing"
    print(f"rows: {total}   questions: {n}   mean per row: {n/total:.1f}   [{scope}]")
    print(f"near-duplicates folded away: {folded}")
    print("(the eval forbade asking, so this is what was uncertain - not what")
    print(" the skill would say out loud, where the budget is about one)\n")

    print("=" * 68)
    print("CHECK 1 - LANDING: if the user answered, where does it go?")
    print("=" * 68)
    by_landing = Counter(a["landing"] for a in asks)
    for key, label in (("field", "a dedicated field"), ("option", "an option entry"),
                       ("partial", "only partly"), ("none", "NOWHERE")):
        c = by_landing[key]
        print(f"  {label:<20} {c:>5}  ({c/n:5.1%})  {bar(c, n)}")
    print("\n  by field:")
    per = Counter(a["field"] for a in asks)
    for field, c in per.most_common():
        land, where = LANDING[field]
        mark = {"field": "ok", "option": "ok", "partial": "PARTIAL", "none": "NO HOME"}[land]
        print(f"    {c:>5}  {field:<16} {mark:<8} {where or ''}")

    print("\n" + "=" * 68)
    print("CHECK 2 - CLOSURE: what stays open after every question is answered")
    print("=" * 68)
    unasked = [u for r in rows for u in r["unasked"]]
    schema = [s for r in rows for s in r["schema_gaps"]]
    r_un = sum(1 for r in rows if r["unasked"])
    r_sc = sum(1 for r in rows if r["schema_gaps"])
    print(f"  gaps a question would fix, but none was asked   {len(unasked):>4}"
          f"  in {r_un} rows ({r_un/total:.0%})")
    print(f"  gaps no question could fix - the schema has no")
    print(f"  field, option, or genre for the answer          {len(schema):>4}"
          f"  in {r_sc} rows ({r_sc/total:.0%})\n")
    print("  the unasked ones, by field:")
    for field, c in Counter(u["field"] for u in unasked).most_common(8):
        print(f"    {c:>5}  {field}")
    print("\n  the schema ones, by field:")
    for field, c in Counter(s["field"] for s in schema).most_common(8):
        print(f"    {c:>5}  {field}")

    print("\n" + "=" * 68)
    print("CHECK 3 - FORM: closed (pick one) vs open-ended")
    print("=" * 68)
    forms = Counter(a["form"] for a in asks)
    for form in ("closed", "open"):
        print(f"  {form:<8} {forms[form]:>5}  ({forms[form]/n:5.1%})  {bar(forms[form], n)}")
    comp = sum(1 for a in asks if a["compound"])
    print(f"\n  two asks in one question  {comp:>5}  ({comp/n:5.1%})")
    print("\n  open-ended rate, fields with >=25 questions:")
    tally = defaultdict(lambda: [0, 0])
    for a in asks:
        tally[a["field"]][0] += 1
        tally[a["field"]][1] += a["form"] == "open"
    for field, (cnt, op) in sorted(tally.items(), key=lambda kv: -kv[1][1] / max(kv[1][0], 1)):
        if cnt >= 25:
            print(f"    {field:<16} {op:>4}/{cnt:<4}  {op/cnt:4.0%} open  {bar(op, cnt, 18)}")

    print("\n" + "=" * 68)
    print("PER-ROW: is there a clear path to proceed?")
    print("=" * 68)
    for verdict, c in Counter(r["verdict"] for r in rows).most_common():
        print(f"  {verdict:<26} {c:>4}  ({c/total:5.1%})  {bar(c, total)}")

    ins = [r for r in rows if r["coverage_verdict"] == "insufficient"]
    clear = sum(1 for r in ins if r["verdict"] in ("clear path", "answer lands only partly"))
    print(f"\n  of the {len(ins)} rows called 'insufficient' - a real build would have")
    print(f"  to ask before starting - {clear} would be unblocked by the questions asked.")

    if "--dump" in sys.argv:
        OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nwrote {OUT.relative_to(ROOT.parent)}  ({total} rows, {OUT.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
