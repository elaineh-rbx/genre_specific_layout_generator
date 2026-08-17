"""Check that Pipeline.md's routing tables still match Build.md Part II.

Build.md is canonical for what a genre needs; Pipeline.md is canonical for how
the layout gets generated. The seam between them is **Part VI, Shape -> Pipeline
Route**, which restates every shape in Build.md together with the route it
forces. That restatement is hand-maintained, so it drifts every time a shape is
added or a route changes.

This reports three things:

  missing   a shape in Build.md with no entry in Pipeline.md Part VI
  extra     an entry in Part VI naming a shape Build.md no longer has
  mismatch  both have it, and the route disagrees

    python tools/check_pipeline_sync.py
    python tools/check_pipeline_sync.py --check    # exit 1 on any finding
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_genre_skills import (  # noqa: E402
    BUILD_MD, SHAPE_CATALOG_HEADING, UNIVERSAL_HEADING, parse_genres,
    parse_universal_options, section_body, table_after,
)

PIPELINE_MD = BUILD_MD.parent / "LayoutGen - Pipeline.md"
PART_VI = re.compile(r"^# \*\*Part VI")
GENRE_TABLE = re.compile(r"^### \*\*Genre-wide routes\*\*")
# "| `space-bounded` | P0 | The most-used shape in the catalogue... |"
SHAPE_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|(.+?)\|(.*?)\|\s*$")
# "| **Obby & Platformer** | **P6** |"
GENRE_ROW = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|(.+?)\|\s*$")
TICKED = re.compile(r"`([^`]+)`")

CODE = re.compile(r"\bP[0-9]\b|\btiered\b|\bCHECK\b|\bSET\b", re.I)


def norm(route: str) -> str:
    """Compare route *codes* as a set, ignoring how the cell is worded.

    The two documents phrase the same route very differently - Build.md writes
    "`P0 + tiered` for `tiered`, `P2` for `stacked`" where Part VI writes
    "tiered / **P2**" - and both are correct. Structure is prose; only the set
    of codes is data. P0 is the baseline, so it drops out whenever anything
    else is present.
    """
    codes = {c.lower() if c.lower() == "tiered" else c.upper()
             for c in CODE.findall(route)}
    codes.discard("P0")
    return " + ".join(sorted(codes)) or "P0"


def build_shapes() -> dict[str, str]:
    """Shape id -> route, read from Build.md's Shape Catalog.

    Since Phase 6 a shape's route is a property of the shape rather than of the
    genre offering it, so this is a single flat table. Genre-wide routes are
    checked separately by `genre_routes` -- they compose with a shape's route
    rather than replacing it, and Part VI now states them once instead of
    folding them into every row.
    """
    text = BUILD_MD.read_text(encoding="utf-8")
    body = section_body(text, SHAPE_CATALOG_HEADING)
    out: dict[str, str] = {}
    for r in table_after(body.splitlines(), 0):
        if len(r) < 4:
            continue
        out[r[0].strip("`")] = norm(r[3])
    return out


def genre_routes() -> dict[str, str]:
    """Genre title -> the route it forces whatever shape is chosen."""
    text = BUILD_MD.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for _n, title, body in parse_genres(text):
        line = next(
            (
                candidate
                for candidate in body.splitlines()
                if candidate.startswith("**Genre route:")
            ),
            None,
        )
        if line:
            out[title] = norm(line)
    return out


def pipeline_shapes() -> tuple[dict[str, str], dict[str, str]]:
    """Part VI's two tables: shape -> route, and genre -> genre-wide route.

    The shape table runs from the Part VI heading to the genre-wide subheading.
    Notes are prose and are ignored; only the Route column is data, and a note
    mentioning a modifier must not be read as one.
    """
    lines = PIPELINE_MD.read_text(encoding="utf-8").splitlines()
    start = next(
        (i for i, line in enumerate(lines) if PART_VI.match(line)),
        None,
    )
    if start is None:
        raise SystemExit("error: Part VI heading not found in Pipeline.md")

    shapes: dict[str, str] = {}
    genres: dict[str, str] = {}
    in_genre_table = False
    for line in lines[start:]:
        if line.startswith("# **Part VII"):
            break
        if GENRE_TABLE.match(line):
            in_genre_table = True
        if in_genre_table:
            m = GENRE_ROW.match(line)
            if m and m.group(1) != "Genre":
                genres[m.group(1)] = norm(m.group(2))
            continue
        m = SHAPE_ROW.match(line)
        if m:
            shapes[m.group(1)] = norm(m.group(2))
    return shapes, genres


def main() -> int:
    strict = "--check" in sys.argv
    build = build_shapes()
    pipe, pipe_genres = pipeline_shapes()
    build_genres = genre_routes()

    missing = sorted(set(build) - set(pipe))
    extra = sorted(set(pipe) - set(build))
    mismatch = sorted(s for s in set(build) & set(pipe) if build[s] != pipe[s])

    print(f"Build.md shapes: {len(build)}    Pipeline.md Part VI entries: {len(pipe)}\n")
    for label, items in (("missing from Pipeline.md", missing), ("not in Build.md", extra)):
        print(f"{label}: {len(items)}")
        for s in items:
            print(f"    {s:<24} Build.md says {build.get(s, '-')}")
    print(f"route mismatch: {len(mismatch)}")
    for s in mismatch:
        print(f"    {s:<24} Build.md {build[s]:<16} Pipeline.md {pipe[s]}")

    genre_bad = sorted(set(build_genres) ^ set(pipe_genres)) + sorted(
        g for g in set(build_genres) & set(pipe_genres)
        if build_genres[g] != pipe_genres[g])
    print(f"\ngenre-wide route problems: {len(genre_bad)}")
    for g in genre_bad:
        print(f"    {g:<24} Build.md {build_genres.get(g,'-'):<10} Pipeline.md {pipe_genres.get(g,'-')}")

    # Universal options apply to all 15 genres, so Part VI's per-genre "options
    # that add a modifier" column structurally cannot express them.
    universal = parse_universal_options(section_body(
        BUILD_MD.read_text(encoding="utf-8"), UNIVERSAL_HEADING))
    routed = [o for o in universal if o["pipeline"]]
    pipeline_text = PIPELINE_MD.read_text(encoding="utf-8")
    unmentioned = [o["id"] for o in routed if o["id"] not in pipeline_text]
    print(f"\nuniversal options carrying a route: {len(routed)}")
    for o in routed:
        seen = "mentioned" if o["id"] in pipeline_text else "NOT MENTIONED"
        print(f"    {o['id']:<24} {' + '.join(o['pipeline']):<16} {seen}")

    problems = (len(missing) + len(extra) + len(mismatch) + len(unmentioned)
                + len(genre_bad))
    if strict and problems:
        print(f"\n{problems} problem(s)", file=sys.stderr)
        return 1
    print(f"\n{problems} problem(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
