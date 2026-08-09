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
