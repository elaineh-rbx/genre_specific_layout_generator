"""Drive the viewer's "Prompt -> Genre choice" tab and prove its rules fire.

check_viewer_chart.py validates the flowchart's geometry; this validates the
intake simulator's behaviour, which is the part that had silently drifted behind
Build.md. Everything here is an assertion about a rule the doc states: stage B
can stop the run or flag SET, universal options are present but never core, the
question round trip is capped at four, no-genre carries five axes plus its own
options and presets, and a stated count survives into the handoff.

A screenshot proves it rendered; only an assertion proves it decided.

Needs playwright, like shoot_viewer.py:
    pip install playwright && python -m playwright install chromium

    python tools/check_intake_tab.py           # assert only
    python tools/check_intake_tab.py --shots    # ...and write tools/_shots/
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
VIEWER = ROOT / "pipeline-viewer.html"
OUT = ROOT / "tools" / "_shots"

problems: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    if not ok:
        problems.append(f"{label}{f' - {detail}' if detail else ''}")


def blk(page, heading: str):
    """The .blk whose <h4> starts with `heading`."""
    return page.locator(".blk").filter(has=page.locator(f'h4:text-matches("^{heading}")'))


def spec_json(page) -> dict:
    return json.loads(page.eval_on_selector("#spec pre", "e => e.textContent"))


def route(page) -> str:
    return page.eval_on_selector("#spec .val .pill", "e => e.textContent").strip()


def main() -> int:
    shots = "--shots" in sys.argv
    if shots:
        OUT.mkdir(exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1800, "height": 1400})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}")
                if m.type == "error" else None)
        page.goto(VIEWER.as_uri())
        page.click('.tab[data-tab="intake"]')
        page.wait_for_timeout(200)

        data = page.evaluate(
            "({ g: GENRE_DATA.length, ng: NO_GENRE_DATA, cat: SHAPE_CATALOG.length, "
            "options: OPTION_CATALOG.length })")
        check(data["g"] == 15, "GENRE_DATA", f"{data['g']} genres, expected 15")
        check(data["cat"] >= 39, "SHAPE_CATALOG", f"{data['cat']} shapes, expected the full catalogue")
        check(data["options"] == 87, "OPTION_CATALOG",
              f"{data['options']} options, expected 87 non-universal rows "
              "including No Genre options")
        # Every genre must name a default that exists, or a silent prompt has
        # nothing to route on.
        bad_default = page.evaluate(
            "GENRE_DATA.filter(g => !SHAPE_CATALOG.some(s => s.id === g.default)).map(g => g.slug)")
        check(not bad_default, "genre defaults", f"missing or unknown: {bad_default}")
        # The recommended list is what keeps the tune menu to roughly five items.
        oversized = page.evaluate("GENRE_DATA.filter(g => g.shapes.length > 6).map(g => g.slug)")
        check(not oversized, "typical shapes", f"more than six offered by: {oversized}")
        ng = data["ng"]
        check(len(ng["axes"]) == 5, "NO_GENRE_DATA axes", f"{len(ng['axes'])}, expected 5")
        check(len(ng["options"]) == 16, "NO_GENRE_DATA options",
              f"{len(ng['options'])}, expected 11 own + 5 inherited")
        # Every universal option must be reachable from every section, whether it
        # arrives inherited or is declared in the section's own table.
        uni_ids = set(page.evaluate(
            "[...new Set(GENRE_DATA.flatMap(g => g.options.filter(o=>o.universal).map(o=>o.id)))]"))
        check(len(uni_ids) == 6, "universal options", f"{len(uni_ids)} distinct, expected 6")
        for section in [{"slug": "no-genre", "options": ng["options"]}] + page.evaluate("GENRE_DATA"):
            missing = uni_ids - {o["id"] for o in section["options"]}
            check(not missing, f"{section['slug']}", f"universal options unreachable: {sorted(missing)}")
        check(len(ng["presets"]) == 3, "NO_GENRE_DATA presets", f"{len(ng['presets'])}, expected 3")

        cards = page.locator("#stepBody .card").count()
        check(cards == 16, "genre grid", f"{cards} cards, expected 15 genres + no-genre")

        # ---------------------------------------------------------- a genre
        page.click('[data-act="genre"][data-v="action"]')
        page.wait_for_timeout(120)
        check(blk(page, "Stage B").count() == 1, "stage B block missing on the genre screen")

        uni = blk(page, "Universal options")
        check(uni.count() == 1, "universal options block missing on the genre screen")
        if uni.count():
            n = uni.locator(".pick").count()
            core = uni.locator(".pick.core").count()
            check(n == 6, "action universal options", f"{n} rendered, expected 6 - action shadows none")
            check(core == 0, "universal options", f"{core} marked core, expected 0 - none is core by design")
        own = blk(page, "Options")
        check(own.locator(".pick.core").count() > 0, "genre options", "no core option marked")
        check(own.locator('.pick:has-text("Water Body")').count() == 0,
              "genre options", "a universal option leaked into the genre's own menu")

        page.click('[data-act="allopts"]')
        page.click('[data-act="opt"][data-v="boundary-edge"]')
        h = spec_json(page)
        check(any(row["id"] == "boundary-edge" for row in h["image_prompt"]),
              "cross-genre option", "No Genre's boundary-edge did not reach Action")

        page.click('[data-act="opt"][data-v="path-road-vehicle"]')
        h = spec_json(page)
        check("P6" not in h["pipeline"], "variable option route",
              "path-road-vehicle silently borrowed Obby's P6 before a meaning was chosen")
        route_choices = page.locator('[data-act="optpipe"][data-id="path-road-vehicle"]')
        check(route_choices.count() == 2, "variable option route",
              f"{route_choices.count()} choices rendered, expected P0 and P6")
        p6 = route_choices.filter(has_text="P6")
        if p6.count():
            p6.click()
            h = spec_json(page)
            check("P6" in h["pipeline"], "variable option route",
                  f"choosing the course meaning produced {h['pipeline']}")
        page.click('[data-act="opt"][data-v="path-road-vehicle"]')

        page.click('[data-act="opt"][data-v="trigger-scoring"]')
        h = spec_json(page)
        unresolved = h["image_prompt"] + h["layout_placement"]
        check(not any(row["id"] == "trigger-scoring" for row in unresolved),
              "variable option destination",
              "trigger-scoring silently borrowed a source destination")
        page.click('[data-act="optdest"][data-id="trigger-scoring"][data-v="both"]')
        h = spec_json(page)
        check(any(row["id"] == "trigger-scoring" for row in h["image_prompt"])
              and any(row["id"] == "trigger-scoring" for row in h["layout_placement"]),
              "variable option destination", "choosing both did not populate both streams")
        page.click('[data-act="opt"][data-v="trigger-scoring"]')

        qs = blk(page, "Questions back").locator(".warns li").count()
        check(1 <= qs <= 4, "question round trip",
              f"{qs} questions, expected 1-4 (Part V caps at 4)")

        gnotes = page.locator(".blk", has=page.locator('h4:text-is("Genre notes")')).inner_text()
        check("**" not in gnotes, "genre notes", "raw markdown reached the page")

        h = spec_json(page)
        check(h["pipeline"] == ["P0"], "action default route", str(h["pipeline"]))
        check("notes" in h, "handoff", "no notes key")
        if shots:
            page.locator(".funnel-wrap").screenshot(path=str(OUT / "intake-genre.png"))

        # ------------------------------------------------- stage B: SET flag
        page.click('[data-act="walkable"][data-v="no"]')
        page.wait_for_timeout(120)
        check("SET" in route(page), "SET flag", f"route is {route(page)!r} after answering nobody walks")
        h = spec_json(page)
        check(any("SET" in n for n in h["notes"]), "SET flag", "route carries SET but no note explains it")
        page.click('[data-act="walkable"][data-v="yes"]')

        # ------------------------------------------------ stage B: P5 exit
        page.click('[data-act="space"][data-v="no"]')
        page.wait_for_timeout(120)
        check(page.locator("#stepBody .step-title").inner_text().startswith("P5"),
              "P5 exit", "answering 'not a 3D game' did not reach the P5 screen")
        h = spec_json(page)
        check(h["pipeline"] == ["P5"], "P5 exit", f"pipeline is {h['pipeline']}")
        check(not h["image_prompt"] and not h["layout_placement"],
              "P5 exit", "still emitting stream contents")
        check(page.locator('[data-act="preset"]').count() == 0,
              "P5 exit", "still offering presets after routing out")
        check("none offered" in page.locator("#spec").inner_text(),
              "P5 exit", "spec still names a shape the user was never shown")
        if shots:
            page.locator(".funnel-wrap").screenshot(path=str(OUT / "intake-p5.png"))
        page.click('[data-act="space"][data-v="yes"]')

        # ------------------------------------ a count survives into the handoff
        page.click('[data-act="preset"][data-v="0"]')
        page.wait_for_timeout(120)
        counts = page.locator('[data-act="count"]')
        check(counts.count() > 0, "quantities", "a preset selected options but no count fields appeared")
        if counts.count():
            counts.first.fill("5")
            page.wait_for_timeout(150)
            h = spec_json(page)
            picks = h["image_prompt"] + h["layout_placement"]
            check(any(p.get("count") == 5 for p in picks),
                  "quantities", "typed count did not reach the handoff")
            check(page.locator('[data-act="count"]').first.input_value() == "5",
                  "quantities", "the field lost its value on re-render")

        # -------------------------------------------- preset shape decoupling
        shape_ids = page.eval_on_selector_all('[data-act="shape"]', "es => es.map(e => e.dataset.v)")
        before = set(page.evaluate("pick.opts"))
        page.click(f'[data-act="shape"][data-v="{shape_ids[-1]}"]')
        page.wait_for_timeout(120)
        check(set(page.evaluate("pick.opts")) == before,
              "preset shape swap", "swapping the shape dropped the preset's options")
        check(page.evaluate("pick.modified") is True, "preset shape swap", "not marked modified")

        # ------------------------------- reaching a shape outside the genre
        # The whole point of the shared catalogue (D12/D14): a genre's list is a
        # shortlist, not a fence. If this cannot fire, sharing the catalogue
        # bought nothing, which is exactly how the first draft of Phase 6 failed.
        typical = set(page.eval_on_selector_all('[data-act="shape"]', "es => es.map(e => e.dataset.v)"))
        check(len(typical) <= 6, "shape shortlist", f"{len(typical)} shown before expanding")
        expand = page.locator('[data-act="allshapes"]')
        check(expand.count() == 1, "shape catalogue", "no control to reach past the genre's shortlist")
        if expand.count():
            expand.click()
            page.wait_for_timeout(120)
            everything = page.eval_on_selector_all('[data-act="shape"]', "es => es.map(e => e.dataset.v)")
            check(len(everything) == data["cat"], "shape catalogue",
                  f"{len(everything)} offered after expanding, expected all {data['cat']}")
            outside = [s for s in everything if s not in typical]
            check(bool(outside), "shape catalogue", "expanding revealed nothing new")
            if outside:
                page.click(f'[data-act="shape"][data-v="{outside[0]}"]')
                page.wait_for_timeout(120)
                h = spec_json(page)
                check(h["shape"]["id"] == outside[0], "cross-genre shape",
                      f"picked {outside[0]} but the handoff says {h['shape']['id']}")
                check(h["shape"]["name"], "cross-genre shape", "resolved to a shape with no name")
                # A shape carries its own route wherever it is used.
                want = page.evaluate(
                    f"SHAPE_CATALOG.find(s => s.id === {outside[0]!r}).pipeline")
                check(all(m in h["pipeline"] for m in want), "cross-genre shape",
                      f"{outside[0]} routes {want} but the handoff says {h['pipeline']}")

        # ------------------------------------------------------- no genre
        page.click('[data-act="reset"]')
        page.click('[data-act="nogenre"]')
        page.wait_for_timeout(150)
        rows = blk(page, "Routing axes").locator(".axis-row").count()
        check(rows == 5, "no-genre axes", f"{rows} rendered, expected 5")
        check(page.locator('[data-act="preset"]').count() == 3,
              "no-genre presets", f"{page.locator('[data-act=preset]').count()} rendered, expected 3")
        ngu = blk(page, "Universal options")
        check(ngu.count() == 1, "no-genre universal options block missing",
              "its own notes say they matter more here than anywhere else")
        if ngu.count():
            # No Genre declares building-interior in its own table, so it inherits five.
            check(ngu.locator(".pick").count() == 5, "no-genre universal options",
                  f"{ngu.locator('.pick').count()} rendered, expected 5 - building-interior is declared locally")
        check(blk(page, "Options").locator(".pick").count() == 11,
              "no-genre own options", "expected the 11 generic spatial features, inherited ones excluded")
        # Notes arrive as Build.md prose; an unpaired ** means the parser ate one.
        notes = page.locator(".blk", has=page.locator('h4:text-is("Notes")')).inner_text()
        check("**" not in notes, "no-genre notes", "raw markdown reached the page")
        h = spec_json(page)
        check(h["pipeline"] == ["P0"], "no-genre defaults", f"{h['pipeline']} - all defaults should route P0")

        # every axis must be able to move the route off P0
        for ax in ng["axes"]:
            routed = next((c for c in ax["choices"] if c["pipeline"]), None)
            check(routed is not None, f"no-genre axis {ax['id']}", "no choice carries a route")
            if not routed:
                continue
            page.click(f'[data-act="axis"][data-k="{ax["id"]}"][data-v="{routed["id"]}"]')
            page.wait_for_timeout(90)
            got = spec_json(page)["pipeline"]
            check(all(m in got for m in routed["pipeline"]),
                  f"no-genre axis {ax['id']}", f"choosing '{routed['id']}' gave {got}, expected {routed['pipeline']}")
            page.click(f'[data-act="axis"][data-k="{ax["id"]}"][data-v="{[c for c in ax["choices"] if c["default"]][0]["id"]}"]')
            page.wait_for_timeout(60)
        if shots:
            page.locator(".funnel-wrap").screenshot(path=str(OUT / "intake-nogenre.png"))

        browser.close()

    for e in errors:
        problems.append(e)
    print(f"genres 15   no-genre axes {len(ng['axes'])} options {len(ng['options'])} presets {len(ng['presets'])}")
    print(f"\n{len(problems)} problem(s)")
    for p in problems:
        print(f"  {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
