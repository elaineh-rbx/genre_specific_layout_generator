"""Write the subagents' inputs with the answer key removed.

`results/routing/answered/<scene>.json` holds four things in one file: the author's prompt,
their intake answers, the router's `config`, and `upstream_skill` - the upstream agents'
classification, which is the ground truth every arm is scored against. Pointing the agent
arm at that file and instructing it to use only the first two fields does not work, because
a file read returns the whole file: the instruction asks for something the tool cannot do.
Roughly twenty subagents reported exactly that, having seen the answer before deciding.

Withholding it is the only reliable way. This writes a projection carrying the prompt,
the answers, and the already-fixed uprezzed scene prompt. The latter is model output, but
not another arm's classification: both agent and gateway arms deliberately use the same
body so their config decisions are the only variable. An agent reading this projection
cannot see what it is being compared to no matter how it reads.

Writes `results/routing/agent_input/<scene>.json`.

Usage:
    python tools/make_agent_inputs.py
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from layoutgen import paths                                       # noqa: E402

SRC = paths.ROUTING / "answered"
BLOB = paths.ROUTING / "blob"
OUT = paths.ROUTING / "agent_input"

#: Everything else in the record is another system's answer and must not travel.
KEEP = ("scene", "source", "answers")


def main() -> None:
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
        body_path = BLOB / path.name
        body = json.loads(body_path.read_text(encoding="utf-8")) if body_path.is_file() else {}
        out["scene_prompt"] = (body.get("scene_prompt") or "").strip()
        (OUT / path.name).write_text(json.dumps(out, indent=2, ensure_ascii=False),
                                    encoding="utf-8")
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
