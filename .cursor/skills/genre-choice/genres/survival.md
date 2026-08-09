# 11. Survival

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Threat evasion, disaster survival, and mascot horror.*

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `arena-contained` | **BoundaryZone (Contained Arena)** | A clearly bounded space the round plays out in, keeping the threat and the player in meaningful proximity. | |
| `warren-looping` | **Path (Looping Warren)** | Architecture built on interconnected circles with **zero dead ends**, so a fleeing player is never artificially cornered by pathfinding AI. | `P6` |
| `world-biomes` | **Zone (Biome World)** | Regions whose threat level scales with distance or depth. | `P4` |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `hazard-kill` | **HazardZone (The Threat)** | The thing being survived as a damaging region — a scripted disaster volume, a spreading hazard, a kill zone. | ● | `image` | |
| `spawner-npc` | **Spawner (Hostile Origin)** | The thing being survived as hostile AI — where it enters and the ground it patrols. | ● | `layout` | |
| `cover-los` | **Cover (Crawlspaces & Lockers)** | Small localized cutouts built into lower walls where players break enemy sightlines and hide. **Minimum 4 studs on the entry axis** (Part I §2). | ● | `image` | |
| `destructible-cluster` | **Destructible (Collapsing Structures)** | Multi-part buildings held together by structural welds so disaster scripts can realistically bring them down. | | `image` | |
| `collectible-nodes` | **Collectible (Survival Resources)** | Gatherable wood, stone, and ore for players building against the threat. | | `layout` | |
| `terrain-tiered` | **Zone (High Ground Relief)** | Raised safe spots to climb when the ground floods, burns, or collapses. | | `image` | `P0 + tiered` |
| `gate-escape` | **Gate (Escape Exit)** | Large structural doors or escape hatches set into the outer boundary, acting as the round-win trigger. | | `both` | |
| `building-interior` | **Zone (Enterable Shelter)** | Buildings players flee into and hide inside. | | `image` | `P3` |
| `buildzone-plot` | **BuildZone (Player Base Ground)** | Open buildable land where players raise shelters and fortifications against the threat. | | `image` | |
| `spawn-protected` | **SpawnZone (Role Assignment Points)** | Separated start points for asymmetric roles, so the hunter and the hunted don't begin on top of each other. | | `layout` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **1 vs All** | Flee the Facility, Survive the Killer (Roblox); Dead by Daylight | `warren-looping` | `cover-los`, `gate-escape`, `spawn-protected` |
| **Escape** | Piggy (Roblox) | `warren-looping` | `gate-escape`, `cover-los`, `building-interior` |
| **Disaster Survival** | Natural Disaster Survival (Roblox) | `arena-contained` | `hazard-kill`, `terrain-tiered`, `destructible-cluster` |
| **Horde Defense** | Left 4 Dead, Killing Floor | `arena-contained` | `spawner-npc`, `destructible-cluster`, `cover-los` |
| **Resource Survival** | [Booga Booga](https://www.roblox.com/games/11729688377/Booga-Booga) (Roblox); Rust | `world-biomes` | `collectible-nodes`, `buildzone-plot` |

**Genre notes**

* **Reference.** Natural Disaster Survival for the disaster bundle.
* **Disaster survival has no exit, and that's the whole distinction.** The arena is periodically engulfed by scripted events and players survive *in place* using high ground, cover, and collapsing structures. **The win is outlasting the timer, not reaching an escape.** Adding an exit gate breaks the mode.
* **Boundaries.** Resource/Base Survival overlaps heavily with the RPG Open World & Survival bundle — they're near-duplicates, so pick one. Chase horror versus Puzzle escape room: the pressure is a pursuing threat, not a locked door.
* **The threat can be a region or an actor, and they're different builds.** A damaging volume needs a shape and a boundary; patrolling AI needs an origin and navigable ground. Build's original version only described the chase case and missed disaster survival entirely.
* **Zero dead ends is a hard topology property.** A single cornered corridor makes a chase game unfair, and a free image won't guarantee loop connectivity — hence the procedural-first route.
* **Roblox's own subgenres here are 1 vs All and Escape**, both presets above. *1 vs All* is the asymmetric-roles case — one player is "it" — which needed `spawn-protected` so the hunter and the hunted don't start on top of each other. The genre had no way to express separated role spawns.
* **Disaster Survival deliberately has no escape gate.** It is the one preset here whose win condition is a timer rather than an exit, so `gate-escape` is absent on purpose rather than by oversight.

## Universal Options

Six features that belong to **no genre in particular because they belong to all of them**. Every genre inherits this table on top of its own.

They exist because the alternative is worse. Each was measured against 620 real prompts and requested in eleven to fifteen different genres, so filing them per-genre would restate the same row seventy-eight times — and leaving them out is what produced the largest hole in the system, with *who is in the world* having no home anywhere.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `npc-population` | **Zone (Ambient Population)** | The non-hostile characters who inhabit the space — shopkeepers, wandering crowds, ambient animals, a named figure players come to see — and the ground they occupy. | | `both` | |
| `building-interior` | **Zone (Enterable Interior)** | Buildings players actually go inside rather than interact with from the street. | | `image` | `P3` |
| `water-body` | **Zone (Water Body)** | Standing or flowing water as a real feature of the map — a lake, river, sea, or pool — whether swum through or treated as a barrier. | | `image` | `CHECK` |
| `settlement-density` | **Zone (Settlement)** | Built-up ground at a stated density — a hamlet, a town, or a dense city block grid — rather than scattered individual buildings. | | `image` | |
| `terrain-relief` | **Zone (Terrain Relief)** | Natural landform shaping the ground: hills, mountains, cliffs, a valley, or a canyon. | | `image` | `P0 + tiered` |
| `island-cluster` | **Zone (Island Cluster)** | Several separate landmasses with water or open air between them, crossed by bridge, boat, or flight. | | `image` | `CHECK` |

**None of these is `Core`, and that is deliberate.** They must never appear in the tune menu, which shows `Core` options only, and no preset includes one. A universal option is a **landing place for a request the user actually made** — reached from the open question in step 5 when a free-text ask matches it — never a default and never a suggestion. Measured against 620 prompts, each of the six would fire on 6–15% of them, so a run that applies one unasked is wrong far more often than it is right.

**A genre's own wording wins.** Four genres already define `building-interior` in their own terms — Shooter's is a breachable structure, Survival's is a shelter to hide in. Those rows are the definition for those genres; the universal row is the fallback for the other eleven. Dedupe by ID exactly as with any shared ID.

**Bend the wording to the prompt.** These are written generically because they are genre-neutral, which makes the instruction to rewrite them *more* important than usual, not less. `water-body` for a pirate game is "open sea between the islands, deep enough to sail"; for a park it is "a duck pond at the centre of the green." Ship the prompt's water, not the word "water."

**Two pipeline notes.** `terrain-relief` is `P0 + tiered` for hills and cliffs, but **caves, overhangs, and tunnels push it to `P2`** — say so when the prompt asks for them. `water-body` and `island-cluster` are `CHECK` because swimming and flight are volumetric: usually fine as a play-height envelope over a representable surface, and only a real problem when the volume self-occludes (layered floating islands, 3D cave networks). See *Layout Attributes* in Build.md for the underlying axis.

**`npc-population` is not `spawner-npc`.** `spawner-npc` is where hostiles enter a fight — an emitter, wired to combat. `npc-population` is who lives here. A market crowd, a quest giver, and a herd of deer are not spawners, and filing them as one produces enemy waves in a town square.

### **Counts and quantities**

Any pick may carry a **count** when the prompt states one. "Five islands," "a village of about twenty houses," "three floors" — the number is part of the request and there is nowhere else for it to live. The scale band is a four-value enum and destroys exact figures by design, so a stated quantity that is dropped here is gone.

Record the number the user gave, not a normalised one. If they said "a few," that is not a count — carry it in the text and leave the count empty.
