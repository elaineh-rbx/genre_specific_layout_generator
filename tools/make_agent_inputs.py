"""Write the subagents' inputs with the answer key removed.

`results/routing/answered/<scene>.json` holds four things in one file: the author's prompt,
their intake answers, the router's `config`, and `upstream_skill` - the upstream agents'
classification, which is the ground truth every arm is scored against. Pointing the agent
arm at that file and instructing it to use only the first two fields does not work, because
a file read returns the whole file: the instruction asks for something the tool cannot do.
Roughly twenty subagents reported exactly that, having seen the answer before deciding.

Withholding it is the only reliable way. This writes a projection carrying only the raw
author prompt and their answers. The context-aware agent turns those directly into the
single enriched image-ready scene body while deciding the layout. An agent reading this
projection cannot see what it is being compared to no matter how it reads.

Writes `results/routing/agent_input/<scene>.json`.

Usage:
    python tools/make_agent_inputs.py
    python tools/make_agent_inputs.py --golden
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from layoutgen import paths                                       # noqa: E402

SRC = paths.ROUTING / "answered"
OUT = paths.ROUTING / "agent_input"

#: Everything else in the record is another system's answer and must not travel.
KEEP = ("scene", "source", "answers")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--golden",
        action="store_true",
        help="also project the original 75 curated prompts as already-fixed inputs",
    )
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    written = skipped = 0
    for path in sorted(SRC.glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        if not (d.get("source") or "").strip():
            skipped += 1
            continue
        out = {k: d.get(k) for k in KEEP}
        out["answers"] = [{"field": a.get("field", ""), "ask": a.get("ask", ""),
                           "answer": a.get("answer", "")}
                          for a in (d.get("answers") or [])
                          if (a.get("answer") or "").strip()]
        (OUT / path.name).write_text(json.dumps(out, indent=2, ensure_ascii=False),
                                    encoding="utf-8")
        written += 1

    if args.golden:
        for line in paths.PROMPTS.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            prompt = json.loads(line)
            scene = str(prompt.get("scene") or "")
            # The historical golden set uses four-digit IDs; the later production
            # corpus uses P-prefixed IDs and already arrived through conversational
            # intake. Golden prompts are curated briefs, so they need no further fixup.
            if not (len(scene) == 4 and scene.isdigit()):
                continue
            source = (prompt.get("source_prompt") or "").strip()
            if not source:
                skipped += 1
                continue
            out = {
                "scene": scene,
                "source": source,
                "answers": [],
            }
            (OUT / f"{scene}.json").write_text(
                json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            written += 1

    # Cheap and worth doing every time: the whole point of this file is an absence, and an
    # absence is exactly the kind of thing a later edit removes without anyone noticing.
    leaked = [p.name for p in OUT.glob("*.json")
              if any(k in json.loads(p.read_text(encoding="utf-8"))
                     for k in ("config", "upstream_skill"))]
    print(f"{written} inputs written to {OUT}, {skipped} skipped for having no source")
    print("answer key present in: " + (", ".join(leaked) if leaked else "none of them"))


if __name__ == "__main__":
    main()
