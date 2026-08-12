"""Copy the upstream pipeline-viewer.html here with a nav bar injected.

The upstream page (`mpalleschi/3D-LayoutBuild-Rules/pipeline-viewer.html`)
shows the pipeline flowchart with a hand-authored list of ~50 abstract
variations to pick from - the reference view of what each route means.
Our own `tools/build_pipeline_viewer.py` shows the SAME flowchart populated
with the 614 real scenes instead. We serve both, so you can switch between
"what would each variation route as" (upstream) and "what did each of my
scenes actually route as" (ours).

This script exists so a periodic refresh of the reference view is one
command rather than a manual copy: the upstream file lives out of tree,
and if it changes the injected nav has to be reapplied cleanly.

Usage:
    # First, pull the upstream repo somewhere (once):
    #   git clone https://github.rbx.com/mpalleschi/3D-LayoutBuild-Rules.git /tmp/3D-LayoutBuild-Rules
    python tools/build_pipeline_reference.py
    python tools/build_pipeline_reference.py --src /path/to/pipeline-viewer.html
"""

from __future__ import annotations

import argparse
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from layoutgen.paths import RESULTS

DEFAULT_SRC = pathlib.Path("/tmp/3D-LayoutBuild-Rules/pipeline-viewer.html")

# The nav bar is injected just after <body>. Same links as the other viewers,
# with the reference view marked active. Positioned fixed so it does not
# disturb the upstream page's own header/layout.
NAV_BAR = """
<div id="lgn-nav" style="position:fixed;top:8px;right:12px;z-index:9999;
  display:flex;gap:6px;font:12px/1 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <a href="/" style="color:#6c8cff;text-decoration:none;padding:5px 10px;
    border-radius:6px;border:1px solid #2b3153;background:#171b2e;">Config shifts</a>
  <a href="/pipeline" style="color:#6c8cff;text-decoration:none;padding:5px 10px;
    border-radius:6px;border:1px solid #2b3153;background:#171b2e;">Pipeline (per-scene)</a>
  <a href="/pipeline/reference" style="color:#e7e9f3;text-decoration:none;padding:5px 10px;
    border-radius:6px;border:1px solid #6c8cff;background:#1e2340;">Reference (upstream)</a>
</div>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=pathlib.Path, default=DEFAULT_SRC,
                    help=f"path to upstream pipeline-viewer.html (default: {DEFAULT_SRC})")
    ap.add_argument("--out", type=pathlib.Path,
                    default=RESULTS / "pipeline_reference.html")
    args = ap.parse_args()

    if not args.src.is_file():
        raise SystemExit(
            f"upstream file not found: {args.src}\n"
            "Clone the repo first:\n"
            "  git clone https://github.rbx.com/mpalleschi/3D-LayoutBuild-Rules.git /tmp/3D-LayoutBuild-Rules")

    src_html = args.src.read_text(encoding="utf-8")
    # Inject the nav right after <body>. If a previous copy is being refreshed
    # its old nav is dropped first, so re-running is idempotent.
    if 'id="lgn-nav"' in src_html:
        i = src_html.index('<div id="lgn-nav"')
        j = src_html.index("</div>", i) + len("</div>")
        src_html = src_html[:i] + src_html[j:]
    marker = "<body>"
    idx = src_html.find(marker)
    if idx < 0:
        raise SystemExit("upstream file has no <body> tag - shape unexpected")
    out_html = src_html[:idx + len(marker)] + NAV_BAR + src_html[idx + len(marker):]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(out_html, encoding="utf-8")
    print(f"wrote {args.out}  ({len(out_html) // 1024} KB)")
    print(f"served at http://localhost:8889/pipeline/reference")


if __name__ == "__main__":
    main()
