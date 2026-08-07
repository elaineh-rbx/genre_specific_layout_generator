# 10. Strategy

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Tower defense, tactical layouts, and top-down management.*

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `lane-actor-track` | **Path (Enemy Lane)** | A single continuous, unchanging lane winding from spawn to the core that enemy waves are hard-coded to follow — no dead-end branches, no ambiguous self-crossings. | `P6` |
| `terrain-open` | **Zone (Open Contested Terrain)** | No lane at all — units path dynamically across open ground between symmetrically distributed bases. | |
| `board-grid` | **Zone (Board Grid)** | A tabletop-scale grid or board that players act on rather than move through. | |

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
* **Roblox's own subgenres here are Board & Card Games and Tower Defense**, both presets above. *Board & Card Games* has the smallest layout job of anything in this document — a table, a board, and seating — and could reasonably route to P5 if the board is a UI surface rather than physical geometry.
* **Two IDs are shared with other genres but written locally.** `tile-grid` also appears in Party & Casual and `collectible-nodes` in five other genres. The ID is the dedupe key; the wording here is Strategy's own, because a contested ore site and an RPG herb patch are not described the same way even though a mixed-genre menu should only offer one of them.
