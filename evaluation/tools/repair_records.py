"""Close records a lane left one brace short, and report anything else.

Some lanes append a record whose final `}` is missing -- the content is whole,
the terminator is not. Left alone the line will not parse and ten minutes of a
lane's work is thrown away for a single character.

The repair is only applied when it is unambiguous: brace depth is computed
outside of strings, the missing closers are appended, and the result must parse.
Nothing is guessed. A line that still fails is printed and left for a re-run,
because a record we cannot read is one to run again rather than invent.

    python evaluation/tools/repair_records.py            # report only
    python evaluation/tools/repair_records.py --write    # repair in place
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RECORDS = Path(__file__).resolve().parents[1] / "data/run-2/records"


def unclosed(line: str) -> tuple[int, int]:
    """Open braces and brackets at end of line, ignoring string contents."""
    curly = square = 0
    in_string = escaped = False
    for ch in line:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            curly += 1
        elif ch == "}":
            curly -= 1
        elif ch == "[":
            square += 1
        elif ch == "]":
            square -= 1
    return curly, square


def close(line: str) -> str | None:
    curly, square = unclosed(line)
    if curly < 0 or square < 0 or (curly == 0 and square == 0):
        return None
    # Brackets always sit inside the object here, so they close first.
    return line + "]" * square + "}" * curly


def main() -> int:
    write = "--write" in sys.argv
    files = sorted(RECORDS.glob("*.jsonl"))
    if not files:
        print(f"no record files under {RECORDS}")
        return 1

    total = fixed = broken = 0
    for path in files:
        out, changed = [], False
        for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            total += 1
            line = raw
            try:
                json.loads(line)
            except json.JSONDecodeError as first:
                candidate = close(line)
                if candidate is not None:
                    try:
                        json.loads(candidate)
                    except json.JSONDecodeError:
                        candidate = None
                if candidate is None:
                    broken += 1
                    print(f"  unrecoverable {path.name}:{n}: {first.msg} "
                          f"at {first.pos}/{len(line)}")
                else:
                    fixed += 1
                    changed = True
                    line = candidate
            out.append(line)
        if changed and write:
            path.write_text("\n".join(out) + "\n", encoding="utf-8")

    verb = "closed" if write else "closeable"
    print(f"{len(files)} files, {total} records, {fixed} {verb}, {broken} unrecoverable")
    if fixed and not write:
        print("run again with --write to apply")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
