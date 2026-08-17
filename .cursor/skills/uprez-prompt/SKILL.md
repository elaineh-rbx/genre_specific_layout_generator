---
name: uprez-prompt
description: Guides the context-aware layout agent in writing the sole enriched image-ready scene body from the raw author message, intake answers, and spatial decisions, with game rules, UI, and code stripped out.
disable-model-invocation: true
---

# Uprez Prompt

You turn a Roblox Build Agent **initial user message**, its **intake answers**,
and the agent's spatial decisions into the sole **enriched image-ready scene
body**: a concise description of the **3D map / level layout** to build (spaces,
props, terrain, camera-facing composition) — not game rules, UI, or code.

This guidance is applied while writing `## Enriched image prompt` inside the
self-contained layout decision. It does not produce a separate intermediate
brief. Anything spatial dropped from the enriched body is gone when prompts are
assembled, so preserve every grounded layout fact and let intake answers
override conflicting details in the original message.

## Goal

Write one paragraph (or two short paragraphs) that a 3D layout tool could use to
**generate the playable space**. Use phrasing like "Create a 3D game map
showing…" or "Build a 3D layout with…" when natural.

## Rules

1. **Ground everything in the user message and intake answers.** Do not invent
   genres, assets, or mechanics they did not imply. Answers override conflicting
   source details. You may **infer reasonable spatial defaults**
   only when the user clearly wants a place but omits detail (e.g. "a small
   arena", "a single lane track") — and an inferred default is the **plainest**
   instance in a clause, never an elaborated one. See **§ Do not do the
   addendum's job**.
2. Include **spatial structure**: foreground/midground/background, left/right,
   zones, paths, buildings, terrain, key props and how they are arranged.
3. **Omit** pure rules, scoring, networking, economy, UI flows, and scripting
   unless they directly specify physical layout.
4. If the message has **no** describable world/map/layout (pure mechanics-only,
   API ask, empty), return an empty string. Read **§ The empty case** before you
   do — a request phrased as code usually still contains a space.
5. Write in **English**, present tense, descriptive — not a bullet list unless
   the user used bullets for layout. **This holds whatever language the message
   is in.** Read a Spanish, Arabic or Korean brief in its own language and
   answer it in English: your paragraph becomes the body of the image prompt,
   and the wrapper and addendum around it are English either way, so a body left
   in the source language is the one part of that prompt the image model cannot
   read. Translate faithfully rather than summarising — every zone, prop and
   count still has to survive.
6. **Let the source set the length. There is no floor.**

| The author wrote | You write |
| :---- | :---- |
| a phrase — "obby tower", "zombie map" | **one sentence** |
| a line or two | **two or three sentences** |
| a paragraph with several spatial facts | a paragraph, up to ~120 words |
| a long brief, many rooms and counts | up to **250 words**, and no more |

   Length is a **consequence** of how much you were given, not a target to reach.
   Padding a two-word prompt into a paragraph is the most common way this stage
   goes wrong, and it is worse than useless: see the next section.

   This constrains what you **add**. It is never a reason to drop something the
   author did say — a spatial fact in the message survives at any length, and a
   long brief still gets every room and every count.

## Example

**User:** I want to make a destruction game. Like Angry Birds in 3D. There is a
wall made of lots of blocks at the back of the scene. In the front there is a
slingshot. The user pulls the slingshot to throw a ball at the wall. The goal is
to destroy it in as few attempts as possible.

**Good output:** Create a 3D game map for a destruction puzzle styled like Angry
Birds in 3D. The play space is a shallow arena viewed from the side or slight
angle. At the **back** of the scene, a tall **wall** made of many destructible
**blocks** stacked in rows. In the **foreground**, a fixed **slingshot** aimed at
the wall with clear launch space for a projectile. Open sky or neutral backdrop;
ground plane between slingshot and wall. No extra structures unless needed to
frame the wall and slingshot.

That answer is this long because the author gave a wall, its position, its
material, a slingshot, its position, and the space between them. Six spatial facts
in, six out. The length was earned.

## A second example, at the other end

**User:** zombie survival map

**Good output:** Create a 3D zombie survival map: a defensible structure on open
ground with approaches on more than one side.

**Bad output:** Create a 3D zombie survival map with a boarded-up farmhouse in the
centre of a fog-filled clearing, surrounded by broken fences, abandoned cars, a
barn to one side, a treeline at the back, scattered supply crates, and multiple
breach points where undead pour in from the darkened woods…

The second answer is not more helpful. Nothing in it came from the author, all of
it forecloses on choices the genre and shape stage is about to make properly, and
if the author actually wanted a mall or a rooftop, the map is now wrong in ways
nothing downstream can undo.

## What to keep, and what to drop

| In the user message | Do |
| :---- | :---- |
| "a wall of blocks at the back" | Keep — it is spatial structure and position |
| "destroy it in as few attempts as possible" | Drop — scoring rule, no layout consequence |
| "10 players per server" | Drop — networking, unless it implies plot count |
| "each base gets special powers" | Drop the powers, keep "separate bases" if bases are physical |
| "a menu screen with a spin wheel" | Drop — UI flow |
| "roughly twenty houses around a plaza" | Keep, **with the number** — counts are layout |
| "PC, mobile and controller support" | Drop — input compatibility |
| "make the graphics outstanding" | Drop — no spatial content |
| "a tycoon about Jurassic Park, Avengers, Spiderman" | Keep "themed film-set plots, one per franchise"; **drop the names** |

**Named franchises describe a register, not a layout.** A prompt asking for a
Marvel tycoon or a Jurassic Park zone is telling you the *look* — a superhero
city block, a jungle enclosure with heavy gates — and the layout is that look.
Carry the visual register in your own words and leave the trademarked name out.
Nothing spatial is lost, and a name carried through gets the whole render refused
by the image model's content filter, which costs the scene entirely.

The same applies to wording aimed at a script rather than a space: "kill parts",
"damage on touch", "resets the player" describe behaviour attached to geometry.
Name the **geometry** — a lava channel, a spike pit, a crumbling ledge — and drop
the behaviour.

**Counts and sizes survive.** "Five islands", "three floors", "about twenty
houses", "1000x1000 studs", "20 studs wide" are layout facts and the later
stages have nowhere else to get them. A number dropped here cannot be recovered.

## Do not do the addendum's job

**Your paragraph is not the whole prompt.** The surrounding layout decision has
already picked the genre, one shape and a few options from the layout rules. A
later deterministic assembly stage appends the document's own wording for those
picks underneath what you write. Genre-typical furniture therefore arrives
anyway — chosen deliberately, from the tables, with the scene's shape already
known.

So when you write what "an obby usually has", you are not adding information. You
are guessing at the addendum's content, unconditionally, without the tables, and
the render gets it twice.

Here is the failure, from a real scene. The author wrote **"obby tower"**. This
stage returned 91 words:

> Create a vertical 3D obby tower with multiple stacked floors rising from a
> central base. Each level is a compact platforming section with floating
> platforms, narrow ledges, ramps, stair-like blocks, and gaps arranged around an
> open central shaft. …

And the addendum appended below it said:

> SHAPE OF THE SPACE — Tower / Spiral Ascent: A course wrapping or stacking so
> platforms sit directly above each other.
> - Sequential Platform Track: A chain of platforms spaced to the physics limits
>   above — the ordered route through the course.
> - Jump Obstacles: Long horizontal jumps, trampoline boosts, wrap-arounds, and
>   stepped vertical platforms.

Stacking, the ordered platform route, the jumps and the stepped platforms were all
coming regardless. The correct output for "obby tower" is **one sentence**:

> Create a 3D obby map built as a tower — a vertical course rising through stacked
> platform sections.

**The test:** if a sentence would be true of nearly every game in this genre, it
belongs to the addendum and not to you. Write what **this** author said, name the
kind of space, and stop.

## Clarifications from the author

The message may end with a block like this:

```
--- clarifications from the author ---
- [shape] How large should the wilderness be? Compact and dense, roughly ten
  minutes to cross, with the village at its centre.
- [options] Instanced dungeon or open cave? A small instanced dungeon entered
  from the wilderness.
```

These are the author answering questions they were asked about their own brief.
**Treat them as the message continuing** — same weight, same rules, no special
status. A clarification that gives a size, a count, a position or a connection is
a layout fact and must survive; one that resolves a rule, an ending condition or a
progression system is dropped like any other mechanic.

They are also the one place a **number** is likely to appear, and § Counts and
sizes applies with full force: "roughly ten shops", "about ten minutes across",
"three floors" cannot be recovered downstream.

Because they add real information, they legitimately earn length under rule 6 — a
one-line brief with four substantive clarifications is no longer a one-line brief.
What they do **not** license is the invention § Do not do the addendum's job
forbids: answering "how big is the wilderness" with a size is right, and taking it
as licence to furnish the wilderness with invented landmarks is not.

## The empty case

Returning an empty string discards the scene entirely, so it needs to be the answer
to "is there a space here?" and not to "is this message about something else?"

**A scripting frame is not an empty case.** "Implement a three-floor escape
tower in Luau, each floor a themed room, an elevator to the next floor" is a
**request for code that contains a building**: three stacked floors, one themed
room each, a vertical connection between them, an exit at the top. Strip the code
ask and describe what is left. Rule 3 removes scripting *from your output*; it
does not license reading past a layout because the sentence around it mentioned a
script.

The same holds for a prompt in **any language** — translate and proceed — and for
one that leads with mechanics and mentions the space late.

**Meta-instructions about the conversation are not layout content, and they do not
defer this job.** "I am going to send you two messages, do not act until you read
both", "reply only with code", "wait for my next message" are addressed to a chat
agent, not to you. You are describing the space in the text you were handed. Strip
the framing and describe what is there; never return empty because a message
announced that more was coming.

**A space can be a minority of the words and still be the answer.** A prompt that
spends nine lines on HP, a HUD, a revival item and scoring, and one line on "three
differently themed floors joined by elevators, exit at the top", has given you a
three-storey tower with three themed rooms and a vertical route. Build that and
drop the nine lines.

Genuinely empty looks like:

| Message | Why |
| :---- | :---- |
| "Insert asset 987654321 into the workspace as the map" | An asset id is not a description; there is nothing to compose |
| "Add a non-blocking startup pop-up and a menu button to toggle the music" | UI only, no space anywhere |
| "Make it realistic with shadows, lights and glare" | Rendering settings, no spatial content |

Ask yourself: **could someone draw this?** "Three floors with a puzzle room on
each" can be drawn. "Toggle the music" cannot. When some part can be drawn,
describe that part and drop the rest.

## Output contract

Write only the image-ready prose for the `## Enriched image prompt` section of
the layout decision. Do not emit JSON or a separate intermediate brief. The
strict transcriber later copies this prose verbatim into
`initial_scene_subprompt_enriched`.
