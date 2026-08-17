"""Guard the Phase 6 shape-catalogue refactor against losing anything.

The refactor moves 49 per-genre shape rows into one shared catalogue that every
genre can reach. The whole point is that reachability **grows**, so the failure
mode worth guarding is the opposite: a shape that used to be offered under a
genre, or a preset whose shape no longer resolves, quietly disappearing in the
move.

    python tools/check_shape_reachability.py --save      # before the refactor
    python tools/check_shape_reachability.py             # after; diffs vs saved

Reports three things, and only the first two are failures:

  lost shape     a (genre, shape) pair that used to exist and no longer does
  broken preset  a preset naming a shape its genre cannot reach
  gained         new (genre, shape) reachability -- expected, informational

Route changes are reported as failures too: the catalogue move is meant to be
behaviour-preserving, so a shape's route must not drift while it relocates.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_genre_skills import BUILD_MD, parse_all  # noqa: E402

HERE = Path(__file__).resolve().parent
SNAPSHOT = HERE / "shape-reachability.json"
MIGRATION = HERE / "shape-migration.json"


GENRE_DIR = Path(__file__).resolve().parents[1] / ".cursor/skills/genre-choice/genres"
NAMED = re.compile(r"`[a-z0-9-]+`\s+\*\*[^*]+\*\*")
ROUTED = re.compile(r"\*\*[^*]+\*\*\s+`(P[0-6]|CHECK|SET)`")


def unnamed_shortlist_entries() -> list[str]:
    """A shortlist entry the handoff cannot be filled from.

    Reachability was never the whole story: step 6 emits shape.type and
    shape.name, so an entry naming only its ID sends the lane to shapes.md --
    which step 2 tells it not to load when the shortlist fits. Most pilot
    lanes hit this and either broke read scope or emitted nulls.
    """
    out = []
    for path in sorted(GENRE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        line = next(
            (
                candidate
                for candidate in text.splitlines()
                if candidate.startswith("**Typical shapes.")
            ),
            "",
        )
        for chunk in line.split("·"):
            if "`" in chunk and not NAMED.search(chunk):
                out.append(f"{path.stem}: {chunk.strip()}")
            elif "`" in chunk and not ROUTED.search(chunk):
                out.append(f"{path.stem}: no route on {chunk.strip()}")
        # The shortlist and the genre's own wording table are two statements
        # about one ID, and a silently dead lookup let them disagree for
        # months. Emit needs exactly one Type (Flavor Name).
        for sid, named in re.findall(r"^\| `([a-z0-9-]+)` \| \*\*(.+?)\*\* \|",
                                     text, re.M):
            if f"`{sid}` **{named}**" not in line and f"`{sid}`" in line:
                out.append(f"{path.stem}: shortlist and wording table "
                           f"disagree on {sid}")
    return out


def migration() -> dict[str, str]:
    """Retired shape id -> the id it merged into (D14). Empty before the merge."""
    return json.loads(MIGRATION.read_text(encoding="utf-8")) if MIGRATION.exists() else {}


def snapshot() -> dict:
    """{genre slug: {shape id: route}} plus {genre slug: {preset: shape id}}.

    Since Phase 6 **every catalogue shape is reachable from every genre**, so a
    genre's map is the whole catalogue rather than its own table. A shape's
    route is the catalogue's, unless the genre forces one on everything it
    builds (Obby, Racing and Infinite Runner are P6 whatever the shape).
    """
    genres, _no_genre, catalog = parse_all(BUILD_MD.read_text(encoding="utf-8"))
    reach, presets = {}, {}
    for g in genres:
        wide = g.get("route") or []
        reach[g["slug"]] = {
            sid: "+".join(sorted(set(c["pipeline"] or wide) | set(wide))) or "P0"
            for sid, c in (catalog.items() or [])
        }
        presets[g["slug"]] = {p["name"]: p["shape"] for p in g["presets"]}
    return {"reach": reach, "presets": presets}


def main() -> int:
    current = snapshot()

    if "--save" in sys.argv:
        SNAPSHOT.write_text(json.dumps(current, indent=1, sort_keys=True), encoding="utf-8")
        pairs = sum(len(v) for v in current["reach"].values())
        print(f"saved {pairs} (genre, shape) pairs across {len(current['reach'])} genres")
        return 0

    if not SNAPSHOT.exists():
        print(f"error: no snapshot at {SNAPSHOT.name}; run with --save first", file=sys.stderr)
        return 2

    before = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    merged = migration()
    lost, rerouted, gained, broken = [], [], [], []

    for slug, shapes in before["reach"].items():
        now = current["reach"].get(slug, {})
        for sid, route in shapes.items():
            new_id = merged.get(sid, sid)
            note = f" (merged into {new_id})" if new_id != sid else ""
            if new_id not in now:
                lost.append(f"{slug} lost {sid}{note}")
            elif now[new_id] != route:
                rerouted.append(f"{slug}/{sid}{note}: {route} -> {now[new_id]}")
    for slug, shapes in current["reach"].items():
        was = {merged.get(s, s) for s in before["reach"].get(slug, {})}
        gained += [f"{slug} gained {sid}" for sid in shapes if sid not in was]

    for slug, mapping in current["presets"].items():
        for name, sid in mapping.items():
            if sid and sid not in current["reach"].get(slug, {}):
                broken.append(f"{slug}: preset '{name}' names unreachable shape '{sid}'")

    unnamed = unnamed_shortlist_entries()

    for label, items in (("lost shape", lost), ("route changed", rerouted),
                         ("broken preset", broken),
                         ("shortlist entry with no Type (Flavor Name)", unnamed)):
        print(f"{label}: {len(items)}")
        for i in items:
            print(f"    {i}")
    print(f"gained (expected): {len(gained)}")
    if "-v" in sys.argv:
        for i in gained:
            print(f"    {i}")

    problems = len(lost) + len(rerouted) + len(broken) + len(unnamed)
    print(f"\n{problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
