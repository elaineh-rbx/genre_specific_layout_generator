# 1. Action

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Fast-paced physical combat and arenas.*

**Shape — pick one.** Every Action map is a bounded, collision-clean clash space with readable geometry for reliable hitbox math. The question is what form it takes.

**Typical shapes.** `space-bounded` *(default)* · `arena-tiered` · `arena-stacked` · `rooms-sequence` · `traversal-city`

This genre words these its own way:

| ID | Shape | What it is |
| :---- | :---- | :---- |
| `space-bounded` | **CombatZone (Flat Arena)** | A single level floor, free of minor tripping geometry, for the cleanest possible physics. |
| `rooms-sequence` | **CombatZone (Arena Chain)** | A linear run of combat rooms joined by corridors rather than one open space. |


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
| **Battlegrounds** | The Strongest Battlegrounds, Jujutsu Shenanigans (Roblox); Power Stone | `space-bounded` | `hazard-kill`, `spawn-protected`, `cover-los` |
| **Fighting** | For Honor, Chivalry; Untitled Boxing Game (Roblox) | `space-bounded` | `spawn-protected`, `cover-los`, `choke-bottleneck` |
| **Sword Fighting** | Sword Fights on the Heights IV (Roblox) | `arena-tiered` | `powerup-buffs`, `hazard-kill`, `cover-los` |
| **Platform Fighter** | Super Smash Bros. | `arena-tiered` | `hazard-kill`, `cover-los` |
| **Open World Action** | Assassin's Creed; Jujutsu Shenanigans open-world mode (Roblox) | `arena-stacked` | `cover-los`, `choke-bottleneck` |
| **Boss Raid** | Monster Hunter, Dark Souls; Dungeon Quest (Roblox) | `space-bounded` | `spawner-npc`, `destructible-cluster`, `hazard-kill` |
| **Hack & Slash** | Devil May Cry, God of War, Bayonetta | `rooms-sequence` | `arena-lockin`, `spawner-npc`, `destructible-cluster` |
| **Parkour Traversal** | Mirror's Edge, Spider-Man; Roblox parkour and free-running places | `traversal-city` | `cover-los`, `hazard-kill`, `choke-bottleneck` |

**Genre notes**

* **Boundaries.** Action is physical and melee-leaning; Shooter is about ranged sightlines and lane discipline. If the map is organized around firing corridors rather than a shared clash space, use Shooter. If there are formal scoring rules and a fixed field spec, it's Sports.
* **Spawn safety is mostly inherited.** Part I §6 already mandates a hazard-free spawn isolated from gameplay risk, at 5×5 studs per player slot. The Action-specific part is *only* the anti-camp placement — don't restate the baseline.
* **Verticality is optional here and often assumed mandatory.** A flat arena is a perfectly valid Action map. Terracing and multi-level catwalks are style choices with real pipeline cost, not requirements.
* **Hack-and-slash needs two rows that are easy to miss.** A linear room-to-room run is `rooms-sequence`, and the door-seals-behind-you fight is `arena-lockin`. Both are staples of the genre and neither is the default arena.
* **Roblox's own subgenres for Action are Battlegrounds & Fighting, Music & Rhythm, and Open World Action.** Two of the three are presets above. *Music & Rhythm* is usually a **`SET`** rather than a P5 — a rhythm game normally has a stage, a performer, and a crowd to look at even though the player never walks anywhere. Build that and skip the traversal checks. Only a bare note highway with no room behind it is P5.
* **Battlegrounds is a Roblox-native format.** The Strongest Battlegrounds effectively created it, and the flat bounded arena with ring-out edges is the shape the whole wave of imitators inherited. When a user asks for an anime fighting game, this is almost always the layout they are picturing.

## Universal Options

Six features that belong to **no genre in particular because they belong to all of them**. Every genre inherits this table on top of its own.

They exist because the alternative is worse. Each is wanted across nearly every genre, so filing them per-genre would restate the same row dozens of times, and leaving them out strands common requests — *who is in the world* would have no home anywhere.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `npc-population` | **Zone (Ambient Population)** | The non-hostile characters who inhabit the space — shopkeepers, wandering crowds, ambient animals, a named figure players come to see — and the ground they occupy. | | `both` | |
| `building-interior` | **Zone (Enterable Interior)** | Buildings players actually go inside rather than interact with from the street. | | `image` | `P3` |
| `water-body` | **Zone (Water Body)** | Standing or flowing water as a real feature of the map — a lake, river, sea, or pool — whether swum through or treated as a barrier. | | `image` | `CHECK` |
| `settlement-density` | **Zone (Settlement)** | Built-up ground at a stated density — a hamlet, a town, or a dense city block grid — rather than scattered individual buildings. | | `image` | |
| `terrain-relief` | **Zone (Terrain Relief)** | Natural landform shaping the ground: hills, mountains, cliffs, a valley, or a canyon. | | `image` | `P0 + tiered` |
| `island-cluster` | **Zone (Island Cluster)** | Several separate landmasses with water or open air between them, crossed by bridge, boat, or flight. | | `image` | `CHECK` |

**None of these is `Core`, and that is deliberate.** They must never appear in the tune menu, which shows `Core` options only, and no preset includes one. A universal option is a **landing place for a request the user actually made** — reached from the open question in step 5 when a free-text ask matches it — never a default and never a suggestion. Most builds want none of them, so a run that applies one unasked is wrong far more often than right.

**A genre's own wording wins.** Four genres already define `building-interior` in their own terms — Shooter's is a breachable structure, Survival's is a shelter to hide in. Those rows are the definition for those genres; the universal row is the fallback for the other eleven. Dedupe by ID exactly as with any shared ID.

**Bend the wording to the prompt.** These are written generically because they are genre-neutral, which makes the instruction to rewrite them *more* important than usual, not less. `water-body` for a pirate game is "open sea between the islands, deep enough to sail"; for a park it is "a duck pond at the centre of the green." Ship the prompt's water, not the word "water."

**Two pipeline notes.** `terrain-relief` is `P0 + tiered` for hills and cliffs, but **caves, overhangs, and tunnels push it to `P2`** — say so when the prompt asks for them. `water-body` and `island-cluster` are `CHECK` because swimming and flight are volumetric: usually fine as a play-height envelope over a representable surface, and only a real problem when the volume self-occludes (layered floating islands, 3D cave networks). See *The Five Routing Axes* in Build.md for the axis behind it.

**`npc-population` is not `spawner-npc`.** `spawner-npc` is where hostiles enter a fight — an emitter, wired to combat. `npc-population` is who lives here. A market crowd, a quest giver, and a herd of deer are not spawners, and filing them as one produces enemy waves in a town square.

### **Counts and quantities**

Any pick may carry a **count** when the prompt states one. "Five islands," "a village of about twenty houses," "three floors" — the number is part of the request and there is nowhere else for it to live. The scale band is a four-value enum and destroys exact figures by design, so a stated quantity that is dropped here is gone.

Record the number the user gave, not a normalised one. If they said "a few," that is not a count — carry it in the text and leave the count empty.
