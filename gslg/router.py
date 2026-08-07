"""LLM step: route a raw game prompt to a genre, a shape, and a set of options.

Build.md's Presentation section says to offer the closest preset first, then the
shape question and the core options. This does that inference in two calls rather
than asking a human:

    1. genre    one of the fifteen, plus any secondary genres the prompt mixes in
    2. settings the closest preset, the one shape, the options, and any request the
                prompt makes that has no row in the table at all

Two calls rather than one because the shape and option enums differ per genre.
Splitting them lets each answer be constrained by a JSON-schema enum built from that
genre's own tables, so the model cannot invent a shape or an option ID - the worst
case is the wrong pick, which shows up as low confidence rather than as an
unresolvable label.

Nothing in Part II is mandatory, so the model is told plainly that picking few
options is a good answer and that inventing evidence to justify a pick is not. An
unlisted request is classified with the document's own rule: geometry a segmenter
could identify is `image`, an invisible volume or marker is `layout`.

Usage:
    python -m gslg.router --text "..."
    python -m gslg.router --golden
    python -m gslg.router --golden --audit
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field

from gslg import llm
from gslg import rules as br
from gslg.paths import PROMPTS as GOLDEN
from gslg.paths import ROUTING

OUT = ROUTING / "rules.jsonl"

GENRE_SYSTEM = """You route Roblox game prompts to a layout genre.

Genre answers what kind of game this is. Rules:

1. Route on the LAYOUT JOB the prompt implies, not on theme or subject matter. A
   medieval tower-defense and a sci-fi tower-defense are the same genre.
2. If the prompt mixes genres, the dominant one is whichever the space is actually
   built for - the space the player spends the game in. Name the others as secondary;
   they contribute features later but never the shape.
3. Judge only what is written. Do not assume a lobby, a hub, or a combat loop the
   prompt does not mention.

Watch the boundaries the document draws between neighbours:
- Action is a shared clash space; Shooter is firing corridors and sightlines.
- Racing has a lap or a finish; a vehicle game without either is Simulation.
- An Obby player moves at their own pace; an Infinite Runner's motion is automatic.
- Adventure rewards reaching a landmark; if the landmark IS the content with nothing
  to collect and no gate it opens, it is Entertainment.
- Add stats, levelling, and a combat loop to Adventure and it becomes RPG.
- A defined repeatable job loop is Simulation's Role Sim; open-ended social
  storytelling is Roleplay & Avatar Sim."""

PRESET_SYSTEM = """You configure a layout for one game prompt from a fixed menu.

You get one genre's presets. A preset IS the configuration: a shape plus a few option
IDs, modelled on a real game. Naming one is the whole decision - the shape and the
options follow from it, so there is nothing else to choose.

Rules:

1. Pick the preset whose shape and options best match what the prompt describes. Read
   the option IDs, not just the preset's name.

2. Prefer the plainest preset that fits. A preset's shape is almost always the
   pipeline-routing decision, so only pick one carrying a pipeline cost when the prompt
   gives positive evidence for it - an explicit interior, explicit floors overhanging
   each other, explicit separate maps or level select, an explicit maze or circuit that
   must connect. Never infer a deviation from silence.

3. Answer "none" when no preset genuinely fits - when every one of them would bring in
   structure the prompt gives no reason to want. That is a real answer, not a failure,
   and the configuration is then built option by option instead.

4. The "modelled on" games are your internal reference for what a preset means. Never
   repeat them back as the answer.

Report confidence honestly: "high" when the prompt names the structure outright,
"medium" when you infer it from strong genre convention, "low" when the prompt is too
vague and you are falling back on the genre's plainest form."""


SETTINGS_SYSTEM = """You configure a layout for one game prompt from a fixed menu.

No preset fits this prompt, so you are building the configuration directly: one shape,
plus whichever options the prompt gives you a reason to want.

Rules, in order of importance:

1. SHAPE: pick exactly one. Shapes are mutually exclusive and this is almost always
   the pipeline-routing decision, so pick the plainest shape that fits. Only pick a
   shape carrying a pipeline cost when the prompt gives positive evidence for it - an
   explicit interior, explicit floors overhanging each other, explicit separate maps
   or level select, an explicit maze or circuit that must connect. Never infer a
   deviation from silence.

2. NOTHING IS MANDATORY. Picking few options is a good answer. If a user picks
   nothing they get a simple map, and the document is explicit that this is a
   legitimate outcome and not a failure. Do not pad the list to look thorough, and do
   not pick an option the prompt gives you no reason to want.

3. A dot marked "core" means signature to the genre - use it to rank when several
   options are equally plausible, not as a reason to include something.

4. UNLISTED REQUESTS: rare, and usually none at all. The user's prompt is already
   sent to the image model in full, so NEVER restate its scenery, theme, style, or
   subject matter here - that is duplication, not information. Add a row only when the
   prompt asks for a specific STRUCTURAL layout feature that no option covers, and
   write only the part the tables miss. At most two. Classify each: "image" if a
   segmenter could identify it as geometry, "layout" if it is an invisible volume, a
   marker, a trigger, or a property of geometry rather than geometry itself.

Report confidence honestly: "high" when the prompt names the shape outright, "medium"
when you infer it from strong genre convention, "low" when the prompt is too vague and
you are falling back on the genre's plainest form."""


@dataclass
class Settings:
    scene: str
    prompt: str
    manifest_genre: str
    genre: str
    genre_evidence: str
    secondary: list[str]
    preset: str
    shape: str
    shape_label: str
    options: list[str]
    dropped_options: list[str]
    extras: list[dict]
    confidence: str
    evidence: str
    route: list[str]
    addendum: str
    preset_delta: dict = field(default_factory=dict)


def _ask(system: str, user: str, schema: dict, retries: int = 3) -> dict:
    return llm.ask(system, user, schema, retries=retries)


GENRE_SCHEMA = {
    "name": "genre", "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "genre": {"type": "string", "enum": list(br.GENRES)},
            "secondary": {
                "type": "array", "items": {"type": "string", "enum": list(br.GENRES)},
                "description": "Other genres the prompt mixes in. Empty is normal.",
            },
            "evidence": {
                "type": "string",
                "description": "The words in the prompt that decided the genre. "
                               "Quote them.",
            },
        },
        "required": ["genre", "secondary", "evidence"],
        "additionalProperties": False,
    },
}


def preset_schema(g: br.Genre) -> dict:
    return {
        "name": "preset_choice", "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "preset": {"type": "string",
                           "enum": [p.name for p in g.presets] + ["none"]},
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "evidence": {
                    "type": "string",
                    "description": "The words in the prompt that chose this preset, "
                                   "quoted. If nothing speaks to structure, say so.",
                },
            },
            "required": ["preset", "confidence", "evidence"],
            "additionalProperties": False,
        },
    }


def settings_schema(g: br.Genre) -> dict:
    """The fallback shape - used only when no preset fits."""
    return {
        "name": "settings", "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "shape": {"type": "string", "enum": [s.id for s in g.shapes]},
                "options": {
                    "type": "array",
                    "items": {"type": "string", "enum": [o.id for o in g.options]},
                    "description": "Only options the prompt gives a reason to want. "
                                   "An empty list is a valid answer.",
                },
                "extras": {
                    "type": "array",
                    "description": "Requests in the prompt with no row in the table. "
                                   "Usually empty.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string",
                                     "description": "One sentence, phrased so it can "
                                                    "be lifted into an image prompt."},
                            "goes_to": {"type": "string", "enum": ["image", "layout"]},
                        },
                        "required": ["text", "goes_to"],
                        "additionalProperties": False,
                    },
                },
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "evidence": {
                    "type": "string",
                    "description": "The words in the prompt that decided the shape, "
                                   "quoted. If nothing speaks to shape, say so.",
                },
            },
            "required": ["shape", "options", "extras", "confidence", "evidence"],
            "additionalProperties": False,
        },
    }


def pick_genre(prompt: str) -> dict:
    return _ask(GENRE_SYSTEM,
                f"GENRE LIST\n{br.genre_list_text()}\n\n"
                f"GAME PROMPT\n\"\"\"\n{prompt.strip()[:6000]}\n\"\"\"\n\n"
                "Which genre is this game's layout built for?",
                GENRE_SCHEMA)


def pick_settings(prompt: str, genre: str, secondary: list[str] | None = None) -> dict:
    g = br.GENRES[genre]
    extra = ""
    if secondary:
        # The dominant genre owns the shape; secondaries contribute options only.
        extra = ("\nThe prompt also touches " + ", ".join(secondary) +
                 ". Those genres may not change the shape - pick the shape from "
                 f"{genre} alone, and cover what they contribute with options or "
                 "with an unlisted request.\n")
    return _ask(SETTINGS_SYSTEM,
                f"{br.menu_text(g)}\n{extra}\n"
                f"GAME PROMPT\n\"\"\"\n{prompt.strip()[:6000]}\n\"\"\"\n\n"
                "Pick the one shape, and only the options this prompt gives you a "
                "reason to want.",
                settings_schema(g))


def pick_preset(prompt: str, genre: str, secondary: list[str] | None = None) -> dict:
    g = br.GENRES[genre]
    extra = ""
    if secondary:
        # The dominant genre owns the shape, so the preset comes from it alone.
        extra = ("\nThe prompt also touches " + ", ".join(secondary) +
                 f". Those genres may not change the shape - choose from {genre}'s "
                 "presets alone.\n")
    return _ask(PRESET_SYSTEM,
                f"{br.preset_menu_text(g)}\n{extra}\n"
                f"GAME PROMPT\n\"\"\"\n{prompt.strip()[:6000]}\n\"\"\"\n\n"
                "Which preset is this, or none?",
                preset_schema(g))


def classify(prompt: str, scene: str = "adhoc", manifest_genre: str = "",
             genre: str = "") -> Settings:
    """Route one prompt. Pass ``genre`` to force it and skip the first call.

    A preset is not a label alongside the shape and options - it *is* a shape and a
    set of options. So naming one settles the configuration, and the open-ended pick
    only runs for prompts no preset fits.
    """
    if genre:
        gsel = {"genre": genre, "secondary": [], "evidence": "genre supplied"}
    else:
        gsel = pick_genre(prompt)
    g = br.GENRES[gsel["genre"]]

    sel = pick_preset(prompt, g.name, gsel.get("secondary"))
    preset = g.preset(sel["preset"])
    if preset is not None:
        r = {"shape": preset.shape, "options": list(preset.options), "extras": [],
             "confidence": sel["confidence"], "evidence": sel["evidence"]}
    else:
        r = pick_settings(prompt, g.name, gsel.get("secondary"))

    shape = g.shape(r["shape"])
    picks = [o for oid in r["options"] if (o := g.option(oid))]
    bullets = [(o.label, br.visible_text(g.name, o)) for o in picks if o.drawn]
    bullets += [("", e["text"]) for e in r["extras"] if e["goes_to"] == "image"]

    return Settings(
        scene=scene, prompt=prompt, manifest_genre=manifest_genre, genre=g.name,
        genre_evidence=gsel["evidence"], secondary=gsel.get("secondary", []),
        preset=sel["preset"], shape=r["shape"],
        shape_label=shape.label if shape else "",
        options=r["options"], dropped_options=[o.id for o in picks if not o.drawn],
        extras=r["extras"], confidence=r["confidence"], evidence=r["evidence"],
        route=br.route_of(g, shape, r["options"]),
        addendum=br.render(g.name, shape, bullets), preset_delta={},
    )


def same_genre(a: str, b: str) -> bool:
    """The manifest predates this Genre List, so compare case-insensitively.

    It also uses labels that are not genres at all - Unspecified, Social, and the
    combined Sports & Racing that this document deliberately splits in two - so a
    mismatch there is a taxonomy change rather than a disagreement.
    """
    return a.strip().lower() == b.strip().lower()


#: Manifest labels with no counterpart in the current Genre List.
STALE_LABELS = {"", "unspecified", "social", "sports & racing"}


def golden_rows() -> list[tuple[str, str, str]]:
    rows = [json.loads(x) for x in GOLDEN.open() if x.strip()]
    return [(r["scene"], r["source_prompt"], r.get("genre") or "") for r in rows]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden", action="store_true", help="route all 75 golden scenes")
    ap.add_argument("--text", default="", help="route one prompt")
    ap.add_argument("--genre", default="", help="force the genre, skipping call 1")
    ap.add_argument("--audit", action="store_true",
                    help="report low confidence and preset drift")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=llm.SEED,
                    help="sampling seed; the only determinism lever this model allows")
    args = ap.parse_args()
    llm.SEED = args.seed

    if args.text:
        s = classify(args.text, genre=args.genre)
        print(f"genre     {s.genre}"
              + (f"  (also {', '.join(s.secondary)})" if s.secondary else ""))
        print(f"          {s.genre_evidence}")
        print(f"preset    {s.preset}")
        print(f"shape     {s.shape}  {s.shape_label}")
        print(f"options   {', '.join(s.options) or '(none)'}")
        if s.dropped_options:
            print(f"          withheld from the image: {', '.join(s.dropped_options)}")
        for e in s.extras:
            print(f"extra     [{e['goes_to']}] {e['text']}")
        print(f"route     {' + '.join(s.route)}")
        print(f"conf      {s.confidence} - {s.evidence}")
        print("\n--- addendum injected at Stage A ---\n" + (s.addendum or "(nothing)"))
        return

    if not args.golden:
        ap.error("pass --golden or --text")

    rows = golden_rows()
    if args.limit:
        rows = rows[: args.limit]
    n_presets = sum(len(g.presets) for g in br.GENRES.values())
    print(f"routing {len(rows)} prompts against {len(br.GENRES)} genres / "
          f"{n_presets} presets via {llm.DEPLOYMENT}", flush=True)

    results: list[Settings] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(classify, p, s, m): s for s, p, m in rows}
        for i, (fut, scene) in enumerate(futures.items(), 1):
            try:
                results.append(fut.result())
            except Exception as exc:  # keep the batch going; report at the end
                print(f"  [{i}/{len(rows)}] {scene}: FAILED {exc}", flush=True)
            if i % 10 == 0:
                print(f"  {i}/{len(rows)} done", flush=True)

    results.sort(key=lambda s: s.scene)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as fh:
        for s in results:
            fh.write(json.dumps(asdict(s)) + "\n")
    print(f"\nwrote {OUT}  ({len(results)} rows)")

    from collections import Counter
    print("\ngenre distribution:")
    for name, n in Counter(s.genre for s in results).most_common():
        print(f"  {n:3d}  {name}")
    print("\npreset distribution:")
    for name, n in Counter(f"{s.genre} :: {s.preset}" for s in results).most_common():
        print(f"  {n:3d}  {name}")
    on_preset = sum(1 for s in results if s.preset != "none")
    print(f"\nlanded on a preset: {on_preset}/{len(results)}  "
          f"(the rest were built option by option)")
    print("confidence:", dict(Counter(s.confidence for s in results)))
    opts = [len(s.options) for s in results]
    print(f"options picked: mean {sum(opts)/max(len(opts),1):.1f}, "
          f"min {min(opts, default=0)}, max {max(opts, default=0)}")
    print("routes:", dict(Counter(" + ".join(s.route) for s in results)))
    comparable = [s for s in results
                  if s.manifest_genre.strip().lower() not in STALE_LABELS]
    agree = sum(1 for s in comparable if same_genre(s.manifest_genre, s.genre))
    print(f"agrees with the manifest genre: {agree}/{len(comparable)} comparable "
          f"({len(results) - len(comparable)} manifest labels predate this Genre List)")

    if args.audit:
        low = [s for s in results if s.confidence == "low"]
        print(f"\nlow confidence: {len(low)}")
        for s in low:
            print(f"  {s.scene}  {s.genre} :: {s.preset}\n      {s.evidence[:150]}")
        # A preset settles the whole configuration, so there is no drift to report -
        # what matters instead is the genres whose presets keep getting refused.
        misses = Counter(s.genre for s in results if s.preset == "none")
        print(f"\nno preset fitted: {sum(misses.values())}")
        for name, n in misses.most_common():
            print(f"  {n:3d}  {name}  ({len(br.GENRES[name].presets)} presets offered)")
        moved = [s for s in comparable if not same_genre(s.manifest_genre, s.genre)]
        print(f"\nmoved genre vs the manifest: {len(moved)}")
        for s in moved:
            print(f"  {s.scene}  {s.manifest_genre} -> {s.genre}\n"
                  f"      {s.genre_evidence[:150]}")


if __name__ == "__main__":
    main()
