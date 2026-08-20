#!/usr/bin/env python3
"""One-shot: turn a hand-read verdict per complaint into keyed JSON.

The verdicts below come from reading all 206 gap texts in full, in the order
`measure_shape_gaps.load()` produces them. Indices are fragile, so this script
resolves them to `item_id|name` keys once and writes the durable file. It is
kept in-tree so the reading is auditable, not so it is re-run.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_shape_gaps import load  # noqa: E402

# index (1-based, as dumped) -> verdict
VERDICTS: dict[int, str] = {
    1: "preset", 2: "reach", 3: "new", 4: "reach", 5: "reach",
    6: "field", 7: "reach", 8: "new", 9: "preset", 10: "catchall",
    11: "reach", 12: "two-shapes", 13: "field", 14: "reach", 15: "field",
    16: "multimap", 17: "preset", 18: "field", 19: "field", 20: "multimap",
    21: "catchall", 22: "catchall", 23: "reach", 24: "field", 25: "two-shapes",
    26: "two-shapes", 27: "new", 28: "field", 29: "multimap", 30: "field",
    31: "field", 32: "new", 33: "new", 34: "multimap", 35: "multimap",
    36: "reach", 37: "field", 38: "preset", 39: "two-shapes", 40: "field",
    41: "new", 42: "multimap", 43: "multimap", 44: "preset", 45: "reach",
    46: "multimap", 47: "reach", 48: "multimap", 49: "two-shapes", 50: "preset",
    51: "field", 52: "new", 53: "preset", 54: "multimap", 55: "preset",
    56: "field", 57: "field", 58: "new", 59: "multimap", 60: "multimap",
    61: "field", 62: "multimap", 63: "new", 64: "field", 65: "catchall",
    66: "reach", 67: "multimap", 68: "field", 69: "field", 70: "reach",
    71: "field", 72: "multimap", 73: "multimap", 74: "preset", 75: "field",
    76: "field", 77: "field", 78: "multimap", 79: "reach", 80: "reach",
    81: "field", 82: "preset", 83: "field", 84: "preset", 85: "preset",
    86: "new", 87: "field", 88: "reach", 89: "preset", 90: "field",
    91: "reach", 92: "reach", 93: "new", 94: "two-shapes", 95: "field",
    96: "field", 97: "field", 98: "reach", 99: "catchall", 100: "multimap",
    101: "new", 102: "preset", 103: "catchall", 104: "reach", 105: "reach",
    106: "field", 107: "multimap", 108: "reach", 109: "multimap", 110: "preset",
    111: "field", 112: "field", 113: "multimap", 114: "reach", 115: "preset",
    116: "field", 117: "new", 118: "multimap", 119: "field", 120: "field",
    121: "reach", 122: "field", 123: "reach", 124: "new", 125: "field",
    126: "field", 127: "two-shapes", 128: "field", 129: "preset", 130: "catchall",
    131: "reach", 132: "new", 133: "multimap", 134: "reach", 135: "preset",
    136: "reach", 137: "multimap", 138: "field", 139: "new", 140: "reach",
    141: "field", 142: "field", 143: "multimap", 144: "field", 145: "new",
    146: "field", 147: "new", 148: "reach", 149: "reach", 150: "reach",
    151: "field", 152: "reach", 153: "field", 154: "reach", 155: "preset",
    156: "field", 157: "two-shapes", 158: "new", 159: "multimap", 160: "preset",
    161: "field", 162: "reach", 163: "two-shapes", 164: "field", 165: "new",
    166: "multimap", 167: "field", 168: "new", 169: "route", 170: "field",
    171: "multimap", 172: "catchall", 173: "reach", 174: "preset", 175: "field",
    176: "field", 177: "field", 178: "preset", 179: "catchall", 180: "catchall",
    181: "multimap", 182: "field", 183: "multimap", 184: "new", 185: "route",
    186: "two-shapes", 187: "reach", 188: "new", 189: "new", 190: "reach",
    191: "new", 192: "preset", 193: "new", 194: "multimap", 195: "field",
    196: "field", 197: "new", 198: "multimap", 199: "multimap", 200: "field",
    201: "field", 202: "new", 203: "catchall", 204: "route", 205: "reach",
    206: "field",
}

# 41, 132, 145 and 197 all read "the prompt is an object, not a place". They were
# the only rows left with no answer, and they are why `set-display` was added
# after the re-measure rather than during step 2 -- the measurement found the
# shape, which is the loop the catchall's logging rule is meant to create.


def main() -> int:
    rows = load()
    if len(rows) != len(VERDICTS):
        print(f"row count moved: {len(rows)} rows vs {len(VERDICTS)} verdicts")
        return 1
    out = {f"{r['id']}|{r['name']}": VERDICTS[i] for i, r in enumerate(rows, 1)}
    dest = Path(__file__).resolve().parent / "shape-gap-verdicts.json"
    dest.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{len(out)} verdicts -> {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
