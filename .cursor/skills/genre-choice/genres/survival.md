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
