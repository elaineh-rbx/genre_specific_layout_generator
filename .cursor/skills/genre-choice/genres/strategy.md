# 10. Strategy

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Tower defense, tactical layouts, and top-down management.*

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `lane-actor-track` | **Path (Enemy Lane)** | A single continuous, unchanging lane winding from spawn to the core that enemy waves are hard-coded to follow — no dead-end branches, no ambiguous self-crossings. | `P6` |
| `terrain-open` | **Zone (Open Contested Terrain)** | No lane at all — units path dynamically across open ground between symmetrically distributed bases. | |
| `board-grid` | **Zone (Board Grid)** | A tabletop-scale grid or board that players act on rather than move through. | `SET` |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `buildzone-grid` | **BuildZone (Tower Placement Grid)** | Flat structural zones framing both sides of the track where players click to deploy defenders. | ● | `image` | |
| `tracker-core` | **Tracker (The Core Base)** | The structure at the end of the track that visually represents the player's primary health pool. | ● | `both` | |
| `spawner-npc` | **Spawner (Wave Origin)** | The mouth of the track where each enemy wave enters. | ● | `layout` | |
| `buildzone-plateau` | **BuildZone (High-Ground Plateau)** | Raised build zones sitting inside path loops, giving long-range units a placement advantage. | | `image` | `P0 + tiered` |
| `cover-los` | **Cover (Line-of-Sight Blockers)** | High walls blocking specific angles of the track so no single placement dominates the whole map. | | `image` | |
| `choke-bottleneck` | **Choke (Track Pinch Point)** | A narrowing in the lane where waves bunch up and area damage pays off. | | `image` | |
| `destructible-cluster` | **Destructible (Breakable Terrain)** | Structures along the route that units or abilities can clear. | | `image` | |
| `buildzone-plot` | **BuildZone (Territorial Free Placement)** | Broad open buildable land radiating outward from each player's base, gated by proximity rules rather than a fixed grid. | | `image` | |
| `gate-progression` | **Gate (Tier Unlock)** | A barrier opening onto later map sections or stronger unit tiers. | | `image` | |
| `collectible-nodes` | **Collectible (Contested Resource Sites)** | Ore, timber, and food sites scattered across the terrain that players expand toward and fight over. | | `layout` | |
| `tile-grid` | **Zone (Playing Board)** | A tabletop-scale grid of evenly divided squares or spaces that pieces move across. | | `image` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Tower Defense** | Tower Defense Simulator (Roblox); Bloons TD | `lane-actor-track` | `buildzone-grid`, `tracker-core`, `spawner-npc`, `choke-bottleneck` |
| **Real-Time Strategy** | [MEDIEVAL REAL TIME STRATEGY](https://www.roblox.com/games/10853515606/MEDIEVAL-REAL-TIME-STRATEGY) (Roblox); Age of Empires | `terrain-open` | `buildzone-plot`, `tracker-core`, `collectible-nodes` |
| **Base Defense** | They Are Billions | `terrain-open` | `tracker-core`, `spawner-npc`, `destructible-cluster`, `cover-los` |
| **Board & Card Games** | Chess, Monopoly; Roblox board games | `board-grid` | `tile-grid` |

**Genre notes**

* **Reference.** [MEDIEVAL REAL TIME STRATEGY](https://www.roblox.com/games/10853515606/MEDIEVAL-REAL-TIME-STRATEGY).
* **RTS may have no path, no AI track, and no hard-coded movement at all.** Units path dynamically toward whatever they're attacking across open terrain. There is no winding enemy lane to build, so don't generate one — bases are distributed symmetrically instead.
* **The core base reframes between styles.** In tower defense it sits at the literal end of one enemy path, so it only needs defending from one approach. In RTS it's the fixed heart of a player's own territory with no lane funnelling attackers, so it has to be defensible from every direction.
* **RTS placement is rule-gated, not grid-gated.** Buildable land is usually constrained by proximity — must be near your own structures, can't be too close to an enemy's — rather than by a narrow strip flanking a lane.
* **Why the track inverts the pipeline.** A tower defense lane has to be one valid continuous route or the game doesn't function. An image can't guarantee that, so the lane is generated procedurally first and dressed after.
* **Roblox's own subgenres here are Board & Card Games and Tower Defense**, both presets above. *Board & Card Games* has the smallest layout job of anything in this document — a table, a board, and seating — but it is a layout, and `board-grid` is the original `SET`: real geometry that nobody walks on. Build it and skip the traversal checks. Only a board that is genuinely a flat UI surface with no room around it is P5.
* **Two IDs are shared with other genres but written locally.** `tile-grid` also appears in Party & Casual and `collectible-nodes` in five other genres. The ID is the dedupe key; the wording here is Strategy's own, because a contested ore site and an RPG herb patch are not described the same way even though a mixed-genre menu should only offer one of them.

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
