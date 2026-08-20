# Scale reframe — two drafts, side by side

Working doc. Neither is applied. Both are complete drop-in replacements for the
**Spatial scale and boundary** section of `.cursor/skills/layout-intake/SKILL.md`
(currently lines 72–92), so they can be compared as written rather than as
descriptions.

## The problem being fixed

`scale` is the most-asked field in the golden set — **440 questions** — and 28%
of them are asked open-ended against an answer space of exactly four values.
Open phrasing invites answers the field cannot hold, and demonstrably does:
**P0005 answered "5,000 square kilometres"** and **P0011 "a trillion blocks."**
Both then needed a second round trip to negotiate down to something buildable.

The current section already carries the right rule — *"if a prompt demands
something the band cannot hold, say so plainly and offer the decomposed
alternative"* — but its only worked example is **vertical** (a hundred-floor
tower in one top-down). Nobody extended it sideways to area, which is where the
440 questions actually are.

Both drafts are grounded in the same pipeline fact, `Pipeline.md` assumption A2:

> **A2 — The whole layout fits a single isometric frame.** Large or sprawling
> games get **cropped or compressed** to fit one frame.

That gives exactly two outcomes for an oversized request, which is what makes a
closed question possible at all.

---

# Draft A — crop or compress

*Keeps inference as the default and adds a trigger. The question only fires when
the request cannot fit one frame, and it offers the two things the pipeline can
actually deliver.*

```markdown
### Spatial scale and boundary

The pipeline needs a rough sense of extent to frame a single image. Infer it;
this is the one place where inference is strongly preferred to asking, because
users rarely think in studs.

Anchor to the avatar baseline in `docs/LayoutGen - Build.md` Part I: walk speed
is 16 studs per second, so a 30-second crossing is roughly 500 studs. Pick the
smallest band that fits what was described.

| Band | Roughly | Typical of | What stays legible in one frame |
| :---- | :---- | :---- | :---- |
| Room | under 100 studs | escape room, single arena, dress-up stage | furniture, props, individual clutter |
| Block | 100–500 studs | most arenas, courses, courts, lobbies | buildings, cars, street lights, doorways |
| District | 500–2000 studs | towns, tycoon plots, raid maps | blocks and main roads; not individual cars |
| Region | over 2000 studs | open worlds, battle royale, biome maps | coastlines, forests, mountain ranges only |

State the band you assumed in the handoff so it can be corrected cheaply.

**The frame is fixed, so extent is bought with detail.** One isometric render
covers the whole map (A2), which means a bigger area is not a bigger picture —
it is the same picture holding less. A region-scale request does not come back
as a detailed world; it comes back as coastlines.

**When the prompt asks for more than one frame can hold, do not ask how big it
should be.** "How big should the world be?" invites an answer the band cannot
hold, and it has: one prompt answered *5,000 square kilometres*, another *a
trillion blocks*. Both needed a second round trip.

Instead, name the two outcomes A2 allows and let the user pick:

- **Compressed** — build all of it, coarse. The extent is honoured; streets,
  props and anything read at ground level are not.
- **Cropped** — build one part of it properly, at `block` or `district` detail,
  and treat the rest as separate maps later. This is the `P4` path.

> A whole world in one pass comes out as coastlines and mountain ranges — no
> streets, nothing you'd pick out standing in it. I can build it that way, or
> build the starting region at town detail and treat the other regions as
> separate maps later. Which do you want?

Record the answer as the band plus a note. If they choose cropped, the band is
the band of **the part being built**, and the deferred remainder goes in
`genre_choice.notes` so the pipeline knows what was set aside.

**The same rule applies vertically**, and always did: a hundred-floor tower in
one top-down cannot be framed either. Say so plainly and offer the decomposed
alternative rather than accepting an impossible frame.
```

---

# Draft B — the smallest thing you want to pick out

*Replaces the inference-first framing with one closed question that pins the zoom
directly. The four answers map one-to-one onto the four bands, so the user never
sees a stud count and never states an area.*

```markdown
### Spatial scale and boundary

The pipeline frames the whole map in a single isometric render (A2), so extent
and detail are the same budget spent twice. What decides the band is not how big
the user says the world is — it is **the smallest thing they need to be able to
pick out.** That is the question to resolve, and it is the one users can answer.

Infer it when the prompt makes it obvious. An escape room means furniture; a
racing circuit means the track and its barriers; "an open world with four
biomes" means terrain. Only ask when the prompt names an extent without naming
what lives in it.

| Smallest thing that matters | Band | Roughly | Typical of |
| :---- | :---- | :---- | :---- |
| furniture, props, clutter you interact with | Room | under 100 studs | escape room, single arena, dress-up stage |
| buildings, cars, street lights, doorways | Block | 100–500 studs | most arenas, courses, courts, lobbies |
| blocks and main roads, not individual cars | District | 500–2000 studs | towns, tycoon plots, raid maps |
| coastlines, forests, mountain ranges | Region | over 2000 studs | open worlds, battle royale, biome maps |

The avatar baseline in `docs/LayoutGen - Build.md` Part I is the cross-check:
walk speed is 16 studs per second, so a 30-second crossing is roughly 500 studs.
If the stated extent and the required detail disagree, **the detail wins** — it
is the half the user will notice is missing.

> What's the smallest thing you want to be able to make out — furniture inside
> rooms, individual buildings and street lights, city blocks and main roads, or
> coastlines and forests?

State the band you assumed in the handoff so it can be corrected cheaply.

**When extent and detail cannot both be honoured, say so and offer the split.**
A user who wants street lights across a whole continent is asking for two frames'
worth of information in one. Offer the detailed part now with the remainder as
separate maps (`P4`), and put the deferral in `genre_choice.notes`.

**The same rule applies vertically**, and always did: a hundred-floor tower in
one top-down cannot be framed either. Say so plainly and offer the decomposed
alternative rather than accepting an impossible frame.
```

---

# How they differ

| | Draft A — crop or compress | Draft B — smallest thing |
| :---- | :---- | :---- |
| **Asks when** | only when the request overflows one frame | whenever extent is stated without content |
| **Question count** | fewer — most prompts never trigger it | slightly more, but replaces a worse question |
| **What the user reasons about** | their game, and which half to sacrifice | the picture, and what they need to see in it |
| **Answer maps to** | band + a `P4` deferral | band directly |
| **Failure it prevents** | "5,000 square kilometres" | the same, plus silently shipping a coarse world someone wanted detailed |
| **Risk** | assumes we can tell when the frame overflows before asking | asks a question about rendering, not about their game |

**The case for A.** It changes the least, keeps inference as the default, and
only spends a question where there is a genuine fork the pipeline cannot resolve
alone. It also states the honest tradeoff in the user's own terms — *which half
of this do you want* — and both branches are things we can build today. The
`P4` branch is a route we already have.

**The case for B.** It fixes the 28% open-ended asks directly rather than only
at the extremes, and it catches a failure A misses: a request that fits one
frame technically but at a detail level the user would reject. A never fires
there, because nothing overflowed.

**The case for taking both**, which is the third option and probably the real
answer: use B's detail column as the *inference* aid — it is what tells you which
band a prompt implies — and reserve A's crop-or-compress question for when the
request genuinely overflows. That is one added table column and one added
trigger, with no new question in the common case. The two drafts are not
mutually exclusive; A's fourth table column and B's first are the same column.

# Open question either way

Neither draft can say **where the overflow threshold is** — how much area one
frame holds before street-level detail stops surviving. The docs state that
cropping or compression happens (A2) but not when. Both drafts currently rely on
judgement for that call. If the image resolution and the isometric framing are
pinned down anywhere, that arithmetic would replace the judgement, and the
`Region` row is where it matters most.
