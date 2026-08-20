#!/usr/bin/env python3
"""One-shot: reorganise Part II so nothing is used before it is defined.

Part II grew by accretion. It opened by declaring nothing in it mandatory,
then two screens later required exactly one shape; it explained the option
row's columns in a table and then re-explained three of those columns in
their own sections further down; it stated the shape rules twice, once under
"How options work" and again under "Shape Catalog"; and it ordered its
reference tables genre list, option index, shape catalogue, universal
options, which is close to reverse dependency order.

The new order defines each thing immediately before the table that uses it:
what a genre is, how to read the Pipeline column, the axes, shapes, the
shape catalogue, options, the universal options, the shared-ID index,
presets, how to offer them, then the genres.

Two things also leave. The routing axes were a top-level section sitting
before Part I, read by nothing in Part I; they are a Part II concept and
move into it. And the readiness policy and the `SET` essay were routing
rules restated in full here -- Pipeline.md already carries both, so Build.md
keeps the legend and the one fact that changes which shape you pick.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "docs" / "LayoutGen - Build.md"

BLOCK = re.compile(r"^#{1,2} \*\*")


def split_blocks(text: str) -> list[tuple[str, str]]:
    """Cut the file at every level-1 and level-2 heading."""
    lines = text.splitlines(keepends=True)
    starts = [i for i, ln in enumerate(lines) if BLOCK.match(ln)]
    blocks = []
    if starts and starts[0] > 0:
        blocks.append(("", "".join(lines[: starts[0]])))
    for i, s in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(lines)
        heading = lines[s].strip()
        blocks.append((heading, "".join(lines[s:end])))
    return blocks


def body_of(block: str) -> str:
    """Everything after the heading line."""
    return block.split("\n", 1)[1].lstrip("\n")


LITERAL = re.compile(r"^(\||>|#|\s*(?:[*\-+]|\d+\.)\s)")


def unwrap(text: str) -> str:
    """Join wrapped prose into one line per paragraph, matching the file's style.

    The authored blocks below are hard-wrapped so they stay readable in this
    script; the document itself puts each paragraph on a single line, and a
    file edited by hand should not have two conventions in it.
    """
    out: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            out.append(" ".join(s.strip() for s in buf))
            buf.clear()

    for line in text.split("\n"):
        if not line.strip():
            flush()
            out.append("")
        elif LITERAL.match(line):
            flush()
            out.append(line)
        else:
            buf.append(line)
    flush()
    return "\n".join(out)


PART2_INTRO = """# **Part II — Genres, Shapes and Options**

A genre is three things, and only the first of them is required.

| | What it is | How many a build has |
| :---- | :---- | :---- |
| **Shape** | What shape the space is. Almost always the pipeline-routing decision. | **Exactly one, always.** |
| **Option** | A layout feature, additive on top of the shape and freely combinable. | Any number, including none. |
| **Preset** | A named bundle of one shape and a few options, modelled on a real game. | At most one, and it is offered rather than applied. |

**The shape is mandatory; every option is optional.** A build where the user
picks no options is a legitimate outcome — they get a simple map. A build with
no shape cannot be routed, so there is no such thing.

Each genre below is one **options table**, a **Typical shapes** shortlist, a set
of **presets**, and its own notes. The picks are what get injected into image
generation.

"""

PIPELINE_COLUMN = """## **Reading the Pipeline column**

Every shape row and every option row carries a **Pipeline** tag: what that pick
costs the build pipeline. It is shown per-row so the cost is visible at the
moment of picking rather than discovered at build time. `LayoutGen - Pipeline.md`
owns the routing itself; this is the legend for reading the tables below.

| Tag | Meaning |
| :---- | :---- |
| *(blank)* | P0 — the current pipeline handles it. |
| `P0 + tiered` | Elevation relief with no overhang. Supported, but the height must be captured or it builds flat. |
| `P2` | Surfaces overhang. Needs per-elevation slices plus a vertical connectivity graph. |
| `P3` | Play moves outside↔inside. Needs a second, linked roofless interior top-down. |
| `P4` | Several distinct maps that don't co-exist on one surface. Needs per-zone passes. |
| `P6` | Structure must be valid by construction. Layout is generated procedurally first, then dressed. |
| `CHECK` | Usually fine; only breaks if the play volume self-occludes. |
| `SET` | There is a space, but nobody walks through it. Build the geometry; skip traversal segmentation and jump-gap validation. |

**P0 and P6 are proven and running. P2, P3, P4 and `CHECK` are not
production-ready.** That changes what a modifier means: it is not a slower build
of the same thing, it is a build that **cannot be delivered today**. `SET` is
safe — it only removes validation steps from a P0 build, so it adds no
machinery.

**So when the prompt does not require a modifier, prefer the shape that keeps
the build on P0 or P6.** A modifier the user never asked for is a deferral they
did not choose. Most builds are already there, so this settles ties rather than
filtering work — **it is a tie-breaker, not a filter**, and it must never strip a
feature the game obviously has.

Read a build's route as **genre route ∪ shape route ∪ every picked option's
route**. The rules for applying the preference safely — what it must not strip,
why a downgrade is always said out loud, and how `SET` differs from `P5` — are
Pipeline.md's *readiness gate* in Part IV.

"""

SHAPES = """## **Shapes**

**A shape is one answer on each of the five routing axes, plus a description of
the space.** That is the whole definition. The axes give it a route; the
description is what reaches the image model. Because a shape answers a single
question — *what shape is this space?* — the answers are mutually exclusive and
a game has exactly one, with every option additive on top of it.

Shape is asked first because it is almost always the **pipeline-routing
decision**. A flat arena is P0 and a multi-level one is P2; static roleplay
housing is P0 and claimable housing is P3. Asking it first puts the expensive
choice where its cost is visible, and it removes any chance of the user
selecting two contradictory answers.

**Shapes live in one catalogue, not in a genre.** Every shape sits in the
**Shape Catalog** below and **every one is reachable from every genre**. What a
genre publishes is a short **Typical shapes** list naming a default — the
handful worth putting on screen. That list is presentation and never a
restriction: when a prompt fits none of them, take any other row in the
catalogue, and say which one you took and that it came from outside the genre's
usual set. A shared catalogue nobody reaches past the first five closes nothing.

**When the shortlist misses, the shape you want is almost always elsewhere in
the catalogue rather than missing from it.** A prompt wanting one large interior
finds Animal Sim assumes wilderness, Simulation assumes an outdoor shared world,
and Roleplay's housing shapes are all towns — while `interior-single` sits in
the catalogue the whole time. Look before concluding that nothing fits.

**A genre may reword any shape, and shapes share IDs exactly as options do.**
Same ID, its genre's own sentence: `range-directed` is "a firing line facing
downrange" in Shooter and "a bowling or archery lane" in Sports. One dedupe key,
two descriptions, and the genre's words are the ones that reach the image model.
A genre stating no wording of its own inherits the catalogue's. This is what
lets one row serve four genres that would each have named it differently — a
bounded single-level space is `space-bounded` whether its genre calls it a flat
arena, a contained arena, a bounded field or a continuous space.

**A shape carries a Shared Vocabulary type when it is itself a region**, using
the same `Type (Flavor Name)` form as an option — an arena is a `CombatZone`
whatever form it takes, and segmentation needs it typed like anything else.
Shapes that describe **map topology** rather than a place — *Open World* versus
*Chaptered Journey* — carry no type, because there is no single region to name.

"""

OPTIONS = """## **Options**

Every genre's options table has the same six columns, and each one is defined
here rather than further down.

| Field | What it holds |
| :---- | :---- |
| **ID** | Stable slug, and the dedupe key for genre mixing. **Shared across genres whenever it is the same concept.** |
| **Option** | `Type (Flavor Name)`, where Type is a Shared Vocabulary term. No exceptions. |
| **What it is** | One sentence written for *this genre*, phrased so it can be lifted more or less directly into an image-generation prompt. |
| **Core** | ● marks options signature to the genre. A ranking aid, never a rule — it means "if the list is long, lead with these", not "include automatically". An option without ● is equally valid to pick. It exists for the mixed-genre case, where five merged tables need some signal as to which handful characterize each genre. |
| **Goes to** | `image` for visible geometry, injected into the image prompt · `layout` for anything invisible or non-geometric — a trigger volume, a spawn marker, a pickup, an emitter — placed against the segmented layout afterward · `both` when it has a visible and an invisible part, in which case **only the visible part is injected**. |
| **Pipeline** | The tag from *Reading the Pipeline column* above. Blank means P0. |

**The `Goes to` rule for anything with no row to look up.** Pipeline step 4
segments the isometric render into visible geometry, so anything invisible
cannot be recovered from an image and must not be sent to the image model at
all. If a segmenter could identify it as geometry, it is `image`. If it is an
invisible volume, a marker, a trigger, or a *property* of geometry rather than
geometry itself, it is `layout`. This matters because the user can always type a
request no table anticipated.

That split is also what keeps the image prompt from saturating: roughly half of
a genre's options never reach the image model, so the user's freedom to pick is
not limited by the image model's tolerance for instructions.

**A shared ID means two genres want the same concept, not that they describe it
the same way.** `hazard-kill` is "bottomless pits wrapping the arena" in Action
and "a spreading disaster volume" in Survival — same dedupe key, different
words, and the genre-specific words are what get injected. Generic phrasing is
useless to an image model, so each genre's table stands alone and is readable
without the shared-ID index below.

"""

PRESETS = """## **Presets**

A preset is **one shape answer plus a few option IDs**, modelled on a real game.
It exists so the common case is a single decision rather than a dozen. Picking
one is picking its contents in a single action, and the user can add or drop
anything afterward.

**Its two halves are independent, and the shape half is the soft one.** Options
can be kept, dropped and reworded one at a time, but shape is exclusive — so a
preset whose mode is right and whose shape is wrong would otherwise force a
choice between accepting a contradicted shape and throwing the preset away. Take
neither. This is common rather than exceptional, and it is almost always the
shape that is wrong.

**Swap the shape, keep the options.** Take a different shape — the genre's
typical list first, then anywhere in the catalogue — and keep the rest. Say
which shape you used and why, and quote the pipeline cost of **the shape you
actually took**, never the preset's default.

> Six of Shooter's nine presets are lane networks. A prompt describing dispersed
> points of interest takes *Team Deathmatch* on `open-battlefield` and keeps the
> team bases, the cover arrays and the chokepoints, all of which it wanted.

**Drop preset options the prompt contradicts.** Keeping one is a frequent
mistake, and it is not cosmetic — a house-decorating prompt that keeps
`obstacle-maze` gets a maze built into the house. A preset is a starting set,
not a package: add what the prompt asked for and the preset lacks, drop what the
prompt rules out, keep the rest.

**A preset can come from a secondary genre.** Because the shape is separable,
taking one does not smuggle in a second shape. Take the options, use the
dominant genre's shape.

**What is not negotiable is that the preset stays recognisable.** If you have
swapped the shape *and* dropped half the options, you are building from scratch:
say so and emit `preset: null`. Roughly — keep the shape or keep most of the
options, not neither.

**Presets carry two names.** The *Modelled on* column names real games and is
**internal reference for the LLM only**; it grounds the preset in something
concrete and makes the intent unambiguous. What a user sees is the generic style
name — a Counter-Strike map is offered as "round-based bomb defusal", never by
the game's name. Reference games are drawn from 3D games generally, with Roblox
examples wherever the platform has a canonical one, since Roblox convention is
often what a user is actually picturing.

**Naming comes from published taxonomies, not invention**, in this order:

1. **Roblox's official subgenre name**, where one fits. The Genre List below is
   already Roblox's genre taxonomy, so its subgenres are the most authoritative
   names available — they are what a creator sees in the Creator Dashboard and
   what Discovery sorts by. *Battlegrounds*, *Tower Obby*, *Escape Room*,
   *Tycoon*, *Battle Royale* and *Open World Action* all come from there.
2. **The established industry subgenre term**, where Roblox's taxonomy is too
   coarse. Roblox files Team Deathmatch, Capture the Flag and free-for-all all
   under *Deathmatch Shooter*, but those are three different layouts, so the
   standard mode names are used instead.
3. **A plain descriptive name**, only when neither exists.

Never invent a name that competes with an existing one — the point is that the
user recognises it immediately.

"""


def build_offering(mixing_body: str) -> str:
    """Presentation and genre mixing, which are both about what reaches a user."""
    return "## **Offering, tuning and mixing**\n\n" + mixing_body


def main() -> int:
    text = BUILD.read_text(encoding="utf-8")
    blocks = split_blocks(text)
    index = {h: i for i, (h, _) in enumerate(blocks)}

    def take(heading: str) -> str:
        if heading not in index:
            raise SystemExit(f"heading not found: {heading}")
        return blocks[index[heading]][1]

    axes_block = take("# **The Five Routing Axes**")
    how_options = take("## **How options work**")

    # --- the axes, demoted into Part II and stripped of two paragraphs that
    # --- only made sense while the section lived outside it
    axes = "## **The Five Routing Axes**\n\n" + body_of(axes_block)
    axes = axes.replace(
        "The No Genre table is the machine-readable copy that generates "
        "`no-genre.md`; `tools/generate_genre_skills.py --check` fails if the "
        "two disagree.",
        "The **No Genre** section at the end of Part II holds the copy these "
        "are checked against.")
    axes = re.sub(
        r"\*\*Relationship to Part II\.\*\*.*?Part IV\.\n", "", axes, flags=re.S)
    axes = axes.rstrip("\n-\n ").rstrip("-").rstrip() + "\n\n"

    # --- salvage the two sub-sections of "How options work" that survive as
    # --- whole units rather than being rewritten
    mixing = how_options.split("### **Mixing genres**", 1)[1]
    mixing = mixing.rstrip("\n- \n").rstrip("-").rstrip() + "\n\n"
    presentation = how_options.split("### **Presentation**", 1)[1] \
                              .split("### **Mixing genres**", 1)[0].strip() + "\n\n"

    offering = ("## **Offering, tuning and mixing**\n\n"
                + presentation
                + "### **Mixing genres**\n\n" + mixing.lstrip())

    new_part2 = (
        unwrap(PART2_INTRO)
        + unwrap(PIPELINE_COLUMN)
        + axes
        + unwrap(SHAPES)
        + take("## **Shape Catalog**")
        + unwrap(OPTIONS)
        + take("## **Universal Options**")
        + take("## **Shared ID registry**")
        + unwrap(PRESETS)
        + offering
        + take("## **Genre List**")
    )

    replaced = {
        "# **The Five Routing Axes**",
        "# **Part II — Genre Layout Options**",
        "## **How options work**",
        "## **Genre List**",
        "## **Shared ID registry**",
        "## **Shape Catalog**",
        "## **Universal Options**",
    }

    out = []
    for heading, block in blocks:
        if heading == "# **Part II — Genre Layout Options**":
            out.append(new_part2)
        elif heading in replaced:
            continue
        else:
            out.append(block)

    text = "".join(out)

    # The contents entry made the same false promise the old Part II opened with.
    toc_old = ("* **Part II \u2014 Genre Layout Options:** A menu of layout features "
               "per genre. **Nothing in Part II is mandatory.** The user prompts, we "
               "infer a genre, we offer options, they pick, and the picks are injected "
               "into image generation. If a user picks nothing, we inject nothing and "
               "they get a simple map \u2014 that is a legitimate outcome, not a failure.")
    toc_new = ("* **Part II \u2014 Genres, Shapes and Options:** What each genre can be "
               "built as. Every build takes **exactly one shape**, which is what routes "
               "the pipeline, and **every option on top of it is optional**. The user "
               "prompts, we infer a genre, we offer a shape and a menu of options, they "
               "pick, and the picks are injected into image generation. A user who picks "
               "no options gets a simple map \u2014 a legitimate outcome, not a failure.")
    if toc_old not in text:
        raise SystemExit("contents entry for Part II not found")
    text = text.replace(toc_old, toc_new, 1)

    # Two genre notes point at the section that became "Reading the Pipeline column".
    renamed = text.count("see *Pipeline costs* in Build.md")
    text = text.replace("see *Pipeline costs* in Build.md",
                        "see *Reading the Pipeline column* in Build.md")

    BUILD.write_text(text, encoding="utf-8")
    print(f"Part II rebuilt; contents entry corrected; {renamed} cross-reference(s) renamed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
