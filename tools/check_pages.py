"""Open each built page in a real browser and fail on anything the build cannot see.

Every comparison page is one Python f-string that emits a few hundred lines of
JavaScript, so a mistake in it produces a valid HTML file that renders a blank panel.
`web.build` reports such a page as written and correctly sized. The only way to know
the page works is to run it, which is what this does: load it, click through to a
scene, and report uncaught errors, broken images, and empty panels.

    python tools/check_pages.py                 # against the running server
    python tools/check_pages.py --port 8888

Needs the browser, which is not a dependency of anything else:

    uv sync --extra check && python -m playwright install --with-deps chromium
"""

from __future__ import annotations

import argparse
import sys

from layoutgen import arms as A

def probe(cmp: A.Comparison) -> str:
    """A scene on this page worth landing on, so its panels get exercised.

    Asked of the comparison rather than fixed, because the arms do not all cover the
    same scenes: the original golden set counts from `0036`, and the arms built on the
    imported set have nothing by that name. A hardcoded scene reported those pages as
    broken when they were only about something else.
    """
    runs = A.load_runs()
    if not cmp.runs:
        return ""
    # Only scenes every arm actually rendered. A scene present in the run files but
    # failed - the content filter refuses a handful - has no images, and reporting its
    # missing thumbnails as a broken page points at the wrong thing.
    ok = [{s for s, row in runs[a.id].items() if row.get("status", "ok") == "ok"}
          for a in cmp.runs]
    shared = set.intersection(*ok)
    return min(shared) if shared else ""


def pages_to_check() -> list[tuple[str, str]]:
    return [(c.page, probe(c)) for c in A.COMPARISONS.values()] + [
        ("requirements.html", ""), ("roadmap.html", ""),
        ("rules_viewer/index.html", ""), ("index.html", ""),
    ]

#: What a working page has once a scene is open. A page that loads, throws nothing and
#: still shows none of these is broken in the way that is easiest to miss.
WANTED = ("#main .strip .fig", "#main table tr")


def check(pg, base: str, page: str, scene: str) -> list[str]:
    bad: list[str] = []
    pg.on("pageerror", lambda e: bad.append(f"uncaught: {e}"))
    pg.on("console", lambda m: bad.append(f"console: {m.text}")
          if m.type == "error" else None)
    pg.goto(f"{base}/{page}", wait_until="networkidle")

    if scene:
        link = pg.query_selector(f'#list a:text-matches("^{scene}")')
        if not link:
            return bad + [f"no sidebar entry for scene {scene}"]
        link.click()
        pg.wait_for_timeout(1200)
        for sel in WANTED:
            if not pg.query_selector_all(sel):
                bad.append(f"nothing matched {sel}")

    # An `img` with no src at all is the zoom dialog's placeholder, filled in on click.
    bad += [f"broken image {src}" for src in pg.evaluate(
        """() => [...document.querySelectorAll('img')]
             .filter(i => i.getAttribute('src') &&
                          (!i.complete || i.naturalWidth === 0))
             .map(i => i.getAttribute('src'))""")]
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8888)
    ap.add_argument("--page", default="", help="just this one")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print("needs a browser: uv sync --extra check && "
              "python -m playwright install --with-deps chromium")
        return 2

    base = f"http://127.0.0.1:{args.port}"
    pages = [p for p in pages_to_check() if not args.page or p[0] == args.page]
    failed = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for page, scene in pages:
            ctx = browser.new_context(viewport={"width": 1600, "height": 1200})
            bad = check(ctx.new_page(), base, page, scene)
            ctx.close()
            failed += bool(bad)
            print(f"{'FAIL' if bad else 'ok  '}  {page}")
            for line in bad:
                print(f"        {line}")
        browser.close()
    print(f"\n{len(pages) - failed}/{len(pages)} pages clean")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
