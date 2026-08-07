# 6. RPG

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Character progression, stat grinding, combat loops, and economic hubs.*

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `world-single` | **Single Contiguous Map** | Town, roads, and mob clearings all on one surface, no instanced areas. | |
| `world-hub-dungeon` | **Hub and Dungeons** | A safe hub feeding separate instanced combat areas entered from the overworld. | `P4 + P3` |
| `world-open-biomes` | **Open World with Biomes** | Regions whose difficulty and reward scale with distance — tougher wildlife and scarcer resources further out. | `P4` |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `safezone-town` | **SafeZone (Sanctuary Town)** | A settlement completely isolated from enemy AI where players restock, repair, and turn in quests. | ● | `image` | |
| `social-hub` | **SocialZone (Economy Ring)** | Shop, quest giver, and blacksmith clustered tightly together to cut repetitive travel for grinding players. | ● | `image` | |
| `hazard-aggro` | **HazardZone (Aggro Bowl)** | Wide open clearings or monster nests holding hostile spawns, set well back from travel roads so low-level players aren't ambushed in transit. | ● | `image` | |
| `spawner-npc` | **Spawner (Mob Emitters)** | The specific points inside a nest or clearing where mobs come from. | | `layout` | |
| `gate-progression` | **Gate (Level-Gated Throat)** | Highly visible blockades — guarded bridges, castle gates, mountain cracks — physically stopping under-levelled players entering high-threat ground. | | `image` | |
| `collectible-nodes` | **Collectible (Resource Veins)** | Repeating alcoves reserved for mining nodes, woodcutting stands, and herb patches. | | `both` | |
| `teleporter-link` | **Teleporter (Fast-Travel Plinth)** | Standardized stone platforms outside major landmarks acting as travel endpoints. | | `both` | |
| `landmark-focal` | **Landmark (Regional Waypoint)** | Distant structures that let a player orient themselves across a large world. | | `image` | |
| `buildzone-plot` | **BuildZone (Unclaimed Territory)** | Broad open buildable land where players and tribes raise their own bases anywhere they like. | | `image` | |
| `building-interior` | **Zone (Enterable Shop or Inn)** | Buildings players actually go inside rather than interact with from the street. | | `image` | `P3` |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Action RPG** | [World // Zero](https://www.roblox.com/games/2727067538/World-Zero-Anime-RPG) (Roblox); Diablo | `world-hub-dungeon` | `safezone-town`, `social-hub`, `hazard-aggro`, `spawner-npc` |
| **Open World & Survival RPG** | [Booga Booga](https://www.roblox.com/games/11729688377/Booga-Booga) (Roblox); Valheim | `world-open-biomes` | `buildzone-plot`, `collectible-nodes`, `landmark-focal` |
| **Turn-based RPG** | Pokémon; Loomian Legacy (Roblox) | `world-single` | `safezone-town`, `spawner-npc`, `gate-progression` |
| **Dungeon Crawler** | Dungeon Quest (Roblox); Diablo | `world-hub-dungeon` | `spawner-npc`, `gate-progression`, `social-hub` |
| **MMO Town Hub** | World of Warcraft | `world-single` | `safezone-town`, `social-hub`, `teleporter-link`, `landmark-focal` |

**Genre notes**

* **References.** [World // Zero](https://www.roblox.com/games/2727067538/World-Zero-Anime-RPG) for hub-and-dungeon — NPC quest hubs, fenced-off mob nests, physical level gates. [Booga Booga](https://www.roblox.com/games/11729688377/Booga-Booga) for open-world survival RPG.
* **Boundaries.** RPG vs Adventure: progression systems, stats, and a combat loop. The Open World & Survival RPG bundle overlaps heavily with Survival's Resource/Base bundle — they're close enough to be near-duplicates, so pick one and don't build both.
* **Don't force a level gate onto survival RPG.** Progression there comes from gear tier and a rebirth or reset loop, not physical blockades. No zone is unconditionally off-limits by level alone, so a guarded bridge is actively wrong for the style.
* **Danger is a gradient, not a fence.** In the survival style, threat scales continuously across the map — tougher wildlife and scarcer resources the further or deeper you go — and player-versus-player risk exists everywhere, not just around NPC spawns.
* **Resource nodes change tier by style.** Optional flavor in hub-and-dungeon; the entire progression loop in open-world survival.
* **Roblox's own subgenres here are Action RPG, Open World & Survival RPG, and Turn-based RPG** — all three are presets above, and the middle one matches the bundle this doc already had under that exact name.
* **Turn-based RPG barely changes the layout.** Combat resolution is a mechanic, not a space. The layout job is the same town-and-overworld work as any other RPG, which is why it carries no distinct shape.
