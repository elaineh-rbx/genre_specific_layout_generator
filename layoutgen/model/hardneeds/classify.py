"""LLM step: route a raw game prompt to one of the 44 sub-genres.

Genre is blocking in Pipeline.md Part V - it cannot be defaulted - and the layout
attributes are inferable from the prompt. This makes that inference an explicit
call rather than a human question, returning one of the fixed
"Genre :: Variation" ids so the answer is always resolvable.

The id is constrained by a JSON-schema enum, so the model cannot invent a
sub-genre; the worst case is picking the wrong one of the 44, which shows up as
low confidence rather than as an unresolvable label.

The model is also asked for the five layout attribute values it believes the
prompt implies. Those are not used to build the prompt - the chosen variation
already fixes them - but disagreeing with the variation's own tags is a useful
signal that the pick is wrong, and `--audit` reports it.

Usage:
    python -m layoutgen.hardneeds.classify --golden      # all 75
    python -m layoutgen.hardneeds.classify --text "..."  # one prompt
    python -m layoutgen.hardneeds.classify --golden --audit
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass

from layoutgen.backends import llm
from layoutgen.model.hardneeds import guidance as gd
from layoutgen.paths import PROMPTS as GOLDEN
from layoutgen.paths import ROUTING

OUT = ROUTING / "subgenres.jsonl"

SYSTEM = """You route Roblox game prompts to a layout sub-genre.

A sub-genre is a genre plus the shape its space takes. You are given the complete
catalog; you must pick exactly one id from it. Rules:

1. Pick on the SHAPE OF THE SPACE the prompt implies, not on theme or subject
   matter. A medieval castle tower-defense and a sci-fi tower-defense are the same
   sub-genre.
2. Prefer the plainest sub-genre that fits. Only pick one carrying attribute tags
   when the prompt gives positive evidence for that deviation - an explicit
   interior, an explicit second map or level select, explicit floors stacking over
   each other, an explicit circuit or maze that must connect, explicit flight or
   swimming. Never infer a deviation from silence.
3. If the prompt describes several modes, pick the one the layout must be built
   for - the space the player spends the game in.
4. Judge only what is written. Do not assume a lobby, a hub, or interiors that the
   prompt does not mention.

Report confidence honestly: "high" when the prompt names the shape, "medium" when
you are inferring it from strong genre convention, "low" when the prompt is too
vague to say and you are falling back on the genre default."""

ATTR_ENUMS = {
    "enclosure": ["exterior", "interior-only", "transition"],
    "verticality": ["single", "tiered", "stacked"],
    "zones": ["single", "multi-zone"],
    "structure": ["dressed", "must-be-valid"],
    "playspace": ["grounded", "volumetric (open)", "volumetric (self-occluding)"],
}

SCHEMA = {
    "name": "subgenre",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "subgenre_id": {"type": "string", "enum": gd.IDS},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "evidence": {
                "type": "string",
                "description": "The words in the prompt that decided the shape. "
                               "Quote them. If nothing in the prompt speaks to shape, "
                               "say so plainly.",
            },
            "implied_attributes": {
                "type": "object",
                "properties": {k: {"type": "string", "enum": v}
                               for k, v in ATTR_ENUMS.items()},
                "required": list(ATTR_ENUMS),
                "additionalProperties": False,
            },
        },
        "required": ["subgenre_id", "confidence", "evidence", "implied_attributes"],
        "additionalProperties": False,
    },
}


@dataclass
class Classification:
    scene: str
    prompt: str
    manifest_genre: str
    subgenre_id: str
    genre: str
    variation: str
    confidence: str
    evidence: str
    implied_attributes: dict
    attr_conflicts: list


def classify(prompt: str, *, retries: int = 3) -> dict:
    user = (f"CATALOG OF SUB-GENRES\n{gd.catalog_text()}\n\n"
            f"GAME PROMPT\n\"\"\"\n{prompt.strip()[:6000]}\n\"\"\"\n\n"
            "Pick the one sub-genre id whose space this prompt describes.")
    return llm.ask(SYSTEM, user, SCHEMA, retries=retries)


def _conflicts(chosen: dict[str, str], implied: dict[str, str]) -> list:
    return [{"axis": k, "variation_says": chosen[k], "model_implied": implied[k]}
            for k in chosen if chosen[k] != implied.get(k)]


def classify_row(scene: str, prompt: str, manifest_genre: str) -> Classification:
    r = classify(prompt)
    genre, variation = gd.split_id(r["subgenre_id"])
    g = gd.resolve(genre, variation)
    return Classification(
        scene=scene, prompt=prompt, manifest_genre=manifest_genre,
        subgenre_id=r["subgenre_id"], genre=genre, variation=variation,
        confidence=r["confidence"], evidence=r["evidence"],
        implied_attributes=r["implied_attributes"],
        attr_conflicts=_conflicts(g.attrs, r["implied_attributes"]),
    )


def golden_rows() -> list[tuple[str, str, str]]:
    rows = [json.loads(x) for x in GOLDEN.open() if x.strip()]
    return [(r["scene"], r["source_prompt"], r.get("genre") or "") for r in rows]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden", action="store_true", help="classify all 75 golden scenes")
    ap.add_argument("--text", default="", help="classify one prompt")
    ap.add_argument("--audit", action="store_true", help="report conflicts and low confidence")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if args.text:
        c = classify_row("adhoc", args.text, "")
        print(json.dumps(asdict(c), indent=2))
        g = gd.resolve(c.genre, c.variation, blueprint=False)
        print(f"\nroute: {' + '.join(g.route)}"
              + (f"   inherits: {g.implied}" if g.implied else ""))
        print("\n--- addendum injected at Stage A ---\n" + g.addendum)
        if g.structural:
            print("\n--- not expressible in the prompt (changes the run) ---")
            for s in g.structural:
                print(f"  {s['axis']}: {s['value']}\n      {s['text']}")
        return

    if not args.golden:
        ap.error("pass --golden or --text")

    rows = golden_rows()
    if args.limit:
        rows = rows[: args.limit]
    print(f"classifying {len(rows)} prompts against {len(gd.IDS)} sub-genres "
          f"via {llm.DEPLOYMENT}", flush=True)

    results: list[Classification] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(classify_row, s, p, m): s for s, p, m in rows}
        for i, (fut, scene) in enumerate(futures.items(), 1):
            try:
                results.append(fut.result())
            except Exception as exc:  # keep the batch going; report at the end
                print(f"  [{i}/{len(rows)}] {scene}: FAILED {exc}", flush=True)
            if i % 10 == 0:
                print(f"  {i}/{len(rows)} done", flush=True)

    results.sort(key=lambda c: c.scene)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as fh:
        for c in results:
            fh.write(json.dumps(asdict(c)) + "\n")
    print(f"\nwrote {OUT}  ({len(results)} rows)")

    from collections import Counter
    print("\nsub-genre distribution:")
    for sid, n in Counter(c.subgenre_id for c in results).most_common():
        print(f"  {n:3d}  {sid}")
    print("\nconfidence:", dict(Counter(c.confidence for c in results)))

    if args.audit:
        bad = [c for c in results if c.attr_conflicts]
        print(f"\nattribute conflicts (model implied != variation tags): {len(bad)}")
        for c in bad:
            axes = ", ".join(f"{x['axis']} {x['variation_says']}!={x['model_implied']}"
                             for x in c.attr_conflicts)
            print(f"  {c.scene}  {c.subgenre_id}\n      {axes}")
        low = [c for c in results if c.confidence == "low"]
        print(f"\nlow confidence: {len(low)}")
        for c in low:
            print(f"  {c.scene}  {c.subgenre_id}\n      {c.evidence[:150]}")


if __name__ == "__main__":
    main()
