"""One-shot migration: per-genre shape tables -> one shared Shape Catalog.

Run once, review the diff, then delete. It is kept in the tree only so the
restructure is reproducible and reviewable rather than appearing as a large
unexplained hand-edit.

What it does, in Build.md:

  1. Inserts a **Shape Catalog** section holding one canonical row per shape --
     type, wording, and the route, which now lives in exactly one place.
  2. Replaces each genre's "Shape -- pick one" table with a recommended list
     naming a default, plus an override table carrying only the wording that
     genre states differently. This is the Universal Options pattern (D14): a
     genre's own words win, the catalogue is the fallback.
  3. Collapses the four near-duplicate families onto one ID each and repoints
     every preset that named a retired ID.
  4. Writes tools/shape-migration.json so the 620 eval rows can be remapped.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_genre_skills import BUILD_MD, parse_all  # noqa: E402

MIGRATION = Path(__file__).resolve().parent / "shape-migration.json"

# Four families, each internally route-consistent -- every member is plain P0,
# which is why they merge cleanly: they differ in wording, never in structure.
MERGE = {
    "world-single": "world-open", "world-shared": "world-open",
    "showcase-freeroam": "world-open",
    "arena-flat": "space-bounded", "arena-contained": "space-bounded",
    "field-bounded": "space-bounded", "space-continuous": "space-bounded",
    "arena-chain": "rooms-sequence", "breach-sequence": "rooms-sequence",
    "puzzle-rooms": "rooms-sequence",
    "world-corridor": "route-guided", "showcase-route": "route-guided",
}

# Canonical wording for the merged IDs. Deliberately genre-neutral: every
# member genre keeps its own sentence as an override, and this is what a genre
# with no opinion inherits.
CANON = {
    "world-open": ("", "Open World",
                   "One contiguous explorable map with no instanced areas, "
                   "traversed in whatever order the player likes."),
    "space-bounded": ("Zone", "Bounded Play Space",
                      "One clearly bounded, single-level space that the whole "
                      "activity happens inside."),
    "rooms-sequence": ("Zone", "Room Sequence",
                       "A run of discrete enclosed rooms joined by corridors and "
                       "worked through in order, rather than one open space."),
    "route-guided": ("Path", "Guided Route",
                     "A single directed route through one continuous space, "
                     "sequencing the player past its key moments rather than "
                     "letting them wander."),
}

SHAPE_BLOCK = re.compile(
    r"(\*\*Shape — pick one\.\*\*[^\n]*\n)"      # intro, kept verbatim
    r"\n\| ID \| Shape \|[^\n]*\n\|[^\n]*\n"     # header + divider
    r"((?:\|[^\n]*\n)+)",                        # rows
)
CATALOG_ANCHOR = "## **Universal Options**"


def fmt_shape(type_: str, name: str) -> str:
    return f"**{type_} ({name})**" if type_ else f"**{name}**"


def main() -> int:
    text = BUILD_MD.read_text(encoding="utf-8")
    genres, _ = parse_all(text)

    # ---- build the catalogue -------------------------------------------------
    catalog: dict[str, dict] = {}
    per_genre: dict[str, dict[str, dict]] = {}

    for g in genres:
        per_genre[g["slug"]] = {}
        for s in g["shapes"]:
            new_id = MERGE.get(s["id"], s["id"])
            row = {"type": s["type"] or "", "name": s["name"], "what": s["what"],
                   "pipeline": s["pipeline"]}
            per_genre[g["slug"]][new_id] = row
            if new_id in CANON:
                t, n, w = CANON[new_id]
                catalog.setdefault(new_id, {"type": t, "name": n, "what": w,
                                            "pipeline": s["pipeline"]})
            elif new_id not in catalog:
                catalog[new_id] = dict(row)
            elif catalog[new_id]["what"] != row["what"]:
                # An already-shared ID with two wordings; the first stays canonical.
                pass

    order = [sid for g in genres for sid in per_genre[g["slug"]]]
    seen: set[str] = set()
    ordered = [s for s in order if not (s in seen or seen.add(s))]

    lines = ["## **Shape Catalog**", "",
             "Every shape in the system, and **every one of them is reachable from every "
             "genre**. A shape answers one question — *what shape is this space?* — so a "
             "game has exactly one, and the pick is almost always the pipeline-routing "
             "decision. The route lives here and only here.", "",
             "Genres do not own shapes; they **recommend** a handful and name a default, "
             "listed in each genre's section below. That list is presentation, not a "
             "restriction: when a prompt fits none of them, take any other row in this "
             "table and say which one you took and why.", "",
             "**A genre may reword any row** — same ID, its own sentence, exactly as "
             "shared options work. The wording below is what a genre inherits when it "
             "states none of its own.", "",
             "| ID | Shape | What it is | Pipeline |",
             "| :---- | :---- | :---- | :---- |"]
    for sid in ordered:
        c = catalog[sid]
        route = f"`{' + '.join(c['pipeline'])}`" if c["pipeline"] else ""
        lines.append(f"| `{sid}` | {fmt_shape(c['type'], c['name'])} | {c['what']} | {route} |")
    lines += ["", f"**{len(ordered)} shapes.** Twelve IDs were retired into four in the "
                  "move — see D14; the wording each genre gave them survives as an "
                  "override.", "", ""]
    text = text.replace(CATALOG_ANCHOR, "\n".join(lines) + CATALOG_ANCHOR, 1)

    # ---- rewrite each genre's shape block ------------------------------------
    preset_refs: dict[str, list[str]] = {g["slug"]: [p["shape"] for p in g["presets"]]
                                         for g in genres}

    def rewrite(g: dict) -> None:
        nonlocal text
        shapes = per_genre[g["slug"]]
        refs = [MERGE.get(s, s) for s in preset_refs[g["slug"]]]
        default = max(shapes, key=lambda s: (refs.count(s), -list(shapes).index(s)))

        rec = " · ".join(f"`{s}`" + (" *(default)*" if s == default else "")
                         for s in shapes)
        overrides = [s for s, r in shapes.items()
                     if (r["type"], r["name"], r["what"]) !=
                        (catalog[s]["type"], catalog[s]["name"], catalog[s]["what"])]

        body = ["", f"**Typical shapes.** {rec}"]
        if overrides:
            body += ["", "**Its own wording.** Same shapes, this genre's words.", "",
                     "| ID | Shape | What it is |", "| :---- | :---- | :---- |"]
            body += [f"| `{s}` | {fmt_shape(shapes[s]['type'], shapes[s]['name'])} "
                     f"| {shapes[s]['what']} |" for s in overrides]
        body.append("")

        def sub(m: re.Match) -> str:
            return m.group(1) + "\n".join(body) + "\n"

        start = text.index(f"## **{g['number']}\\. {g['title']}**")
        end = text.index("\n## **", start + 10)
        chunk = text[start:end]
        new_chunk, n = SHAPE_BLOCK.subn(sub, chunk, count=1)
        if n != 1:
            raise SystemExit(f"error: shape block not matched in {g['slug']}")
        text = text[:start] + new_chunk + text[end:]

    for g in genres:
        rewrite(g)

    # ---- repoint presets -----------------------------------------------------
    for old, new in MERGE.items():
        text = re.sub(rf"\| `{re.escape(old)}` \|", f"| `{new}` |", text)
        text = text.replace(f"`{old}`", f"`{new}`")

    BUILD_MD.write_text(text, encoding="utf-8")
    MIGRATION.write_text(json.dumps(MERGE, indent=1, sort_keys=True), encoding="utf-8")
    print(f"catalogue: {len(ordered)} shapes ({len(MERGE)} IDs retired into "
          f"{len(set(MERGE.values()))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
