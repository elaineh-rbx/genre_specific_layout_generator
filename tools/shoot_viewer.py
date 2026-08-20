"""Screenshot the viewer's flowchart tab so a layout change can be eyeballed.

The chart is hand-positioned absolute coordinates, so check_viewer_chart.py can
prove nodes do not collide but not that the result reads well - in particular
it cannot see an edge curving through a node it does not connect to. This
renders the thing.

Needs playwright, which nothing else here does:
    pip install playwright && python -m playwright install chromium

    python tools/shoot_viewer.py 0 5 20
    python tools/shoot_viewer.py 0 --zoom=560,20,1220,320
Output lands in tools/_shots/, which is gitignored.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
VIEWER = ROOT / "pipeline-viewer.html"
OUT = ROOT / "tools" / "_shots"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    # --zoom x,y,w,h in chart coordinates, for checking a specific edge or corner
    zoom = next((a[7:] for a in sys.argv[1:] if a.startswith("--zoom=")), None)
    picks = [int(a) for a in args] or [0]
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 2560, "height": 1200},
                                device_scale_factor=2 if zoom else 1)
        page.goto(VIEWER.as_uri())
        page.wait_for_timeout(400)
        for i in picks:
            page.select_option("#picker", str(i))
            page.wait_for_timeout(250)
            name = page.eval_on_selector("#variationName", "e => e.textContent")
            path = OUT / f"chart-{i:02d}{'-zoom' if zoom else ''}.png"
            if zoom:
                cx, cy, cw, ch = (float(v) for v in zoom.split(","))
                box = page.locator(".chart").bounding_box()
                page.screenshot(path=str(path),
                                clip={"x": box["x"] + cx, "y": box["y"] + cy,
                                      "width": cw, "height": ch})
            else:
                page.locator(".main").screenshot(path=str(path))
            print(f"{path.name}  {name}")
        browser.close()


if __name__ == "__main__":
    main()
