# 1. Action

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Fast-paced physical combat and arenas.*

**Shape — pick one.** Every Action map is a bounded, collision-clean clash space with readable geometry for reliable hitbox math. The question is what form it takes.

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `arena-flat` | **CombatZone (Flat Arena)** | A single level floor, free of minor tripping geometry, for the cleanest possible physics. | |
| `arena-tiered` | **CombatZone (Terraced Arena)** | Stepped or terraced relief — strong elevation, nothing overhanging. | `P0 + tiered` |
| `arena-stacked` | **CombatZone (Multi-Level Arena)** | Catwalks, balconies, or floors that overhang the arena below. | `P2` |
| `arena-chain` | **CombatZone (Arena Chain)** | A linear run of combat rooms joined by corridors rather than one open space. | |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `cover-los` | **Cover (Line-of-Sight Pillars)** | Large columns scattered across the floor, letting a retreating player break combat lock and heal. | ● | `image` | |
| `hazard-kill` | **HazardZone (Ring-Out Edges)** | Open edges or bottomless pits wrapping the arena, making aggressive positioning a real risk. | ● | `image` | |
| `spawn-protected` | **SpawnZone (Anti-Camp Placement)** | Spawns set back, screened, or elevated so a player isn't in an enemy firing line the frame they appear. | ● | `both` | |
| `choke-bottleneck` | **Choke (Conflict Chokepoint)** | Doorways, bridges, or narrow gaps that funnel fighters together into predictable flashpoints. | | `image` | |
| `destructible-cluster` | **Destructible (Breakable Cover)** | Welded structures that fracture under fire, so cover degrades as the fight goes on. | | `image` | |
| `arena-lockin` | **Gate (Combat Lock-In)** | Shutters or barriers that seal the exits until the current wave is cleared. | | `image` | |
| `spectator-zone` | **SpectatorZone (Ringside Stands)** | Raised seating or a walled gallery where eliminated players watch the fight. | | `image` | `P0 + tiered` |
| `spawner-npc` | **Spawner (NPC & Trap Emitters)** | Points where hostile NPCs or traps enter the arena mid-fight. | | `layout` | |
| `powerup-buffs` | **PowerUp (Combat Buffs)** | Damage, shield, or speed pickups placed around the floor to pull players into contested space. | | `layout` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Battlegrounds** | The Strongest Battlegrounds, Jujutsu Shenanigans (Roblox); Power Stone | `arena-flat` | `hazard-kill`, `spawn-protected`, `cover-los` |
| **Fighting** | For Honor, Chivalry; Untitled Boxing Game (Roblox) | `arena-flat` | `spawn-protected`, `cover-los`, `choke-bottleneck` |
| **Sword Fighting** | Sword Fights on the Heights IV (Roblox) | `arena-tiered` | `powerup-buffs`, `hazard-kill`, `cover-los` |
| **Platform Fighter** | Super Smash Bros. | `arena-tiered` | `hazard-kill`, `cover-los` |
| **Open World Action** | Assassin's Creed; Jujutsu Shenanigans open-world mode (Roblox) | `arena-stacked` | `cover-los`, `choke-bottleneck` |
| **Boss Raid** | Monster Hunter, Dark Souls; Dungeon Quest (Roblox) | `arena-flat` | `spawner-npc`, `destructible-cluster`, `hazard-kill` |
| **Hack & Slash** | Devil May Cry, God of War, Bayonetta | `arena-chain` | `arena-lockin`, `spawner-npc`, `destructible-cluster` |

**Genre notes**

* **Boundaries.** Action is physical and melee-leaning; Shooter is about ranged sightlines and lane discipline. If the map is organized around firing corridors rather than a shared clash space, use Shooter. If there are formal scoring rules and a fixed field spec, it's Sports.
* **Spawn safety is mostly inherited.** Part I §6 already mandates a hazard-free spawn isolated from gameplay risk, at 5×5 studs per player slot. The Action-specific part is *only* the anti-camp placement — don't restate the baseline.
* **Verticality is optional here and often assumed mandatory.** A flat arena is a perfectly valid Action map. Terracing and multi-level catwalks are style choices with real pipeline cost, not requirements.
* **Two options exist because the presets demanded them.** Building the preset list surfaced that the genre could not express a hack-and-slash at all — no linear room-to-room form and no combat lock-in, despite both being staples. `arena-chain` and `arena-lockin` were added for it.
* **Roblox's own subgenres for Action are Battlegrounds & Fighting, Music & Rhythm, and Open World Action.** Two of the three are presets above. *Music & Rhythm* has no meaningful 3D layout job and routes to **P5**.
* **Battlegrounds is a Roblox-native format.** The Strongest Battlegrounds effectively created it, and the flat bounded arena with ring-out edges is the shape the whole wave of imitators inherited. When a user asks for an anime fighting game, this is almost always the layout they are picturing.
