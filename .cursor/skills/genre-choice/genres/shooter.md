# 8. Shooter

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Competitive team deathmatches, tactical combat, and positioning.*

**Shape — pick one.** How the map organises movement between the shooting.

**Typical shapes.** `lane-network` **Lane (Lane Network)** `P0` *(default)* · `rooms-sequence` **Path (Breach Sequence)** `P0` · `open-battlefield` **Zone (Open Battlefield)** `P0` · `range-directed` **Lane (Directed Practice Range)** `P0`

**The bold name is `Type (Flavor Name)`, and the tag after it is the shape's route** — between them, everything `shape` and `pipeline` need at emit. Take both from here rather than loading `shapes.md`; where this genre rewords a shape, the name above is already its own.

This genre words these its own way:

| ID | Shape | What it is |
| :---- | :---- | :---- |
| `rooms-sequence` | **Path (Breach Sequence)** | A raid site of rooms that dead-end into breach points, cleared in a defined order rather than looped. |


**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `cover-los` | **Cover (Tactical Cover Arrays)** | Waist-high (3–4 studs) and full-body (7–8 studs) cover distributed evenly across every lane. | ● | `image` | |
| `spawn-teambase` | **SpawnZone (Opposing Team Bases)** | Balanced bases at opposite ends of the map, completely shielded from enemy sniper lines. | ● | `both` | |
| `choke-bottleneck` | **Choke (Lane Pinch Point)** | Narrow transitions where lanes meet, concentrating fights into contested ground. | ● | `image` | |
| `spawn-protected` | **SpawnZone (Spawn Shield)** | Geometry directly around a spawn breaking the sightlines into it. | | `both` | |
| `path-loop` | **Path (Interconnected Rooms)** | Rooms with two or more entrances and exits, favouring constant interconnectedness over realistic dead ends. | | `image` | |
| `capture-zone` | **CaptureZone (Flag Stand / Bomb Site)** | A point scored by carrying something to it or holding it against contest. | | `both` | |
| `control-zone` | **ControlZone (Held Point)** | A capacity-limited occupancy area with a visible indicator — the King-of-the-Hill hill. | | `both` | |
| `cover-elevated` | **Cover (Elevated Firing Position)** | Windows, towers, and nests reachable only through exposed, predictable stairs or ladders. | | `image` | `P0 + tiered`, or `P2` if it overhangs the floor below |
| `path-flank-tunnel` | **Path (Flanker Tunnel)** | Subterranean or interior routes letting fast players bypass the main-lane standoff. | | `image` | `P2` |
| `building-interior` | **Zone (Breachable Structure)** | A house, apartment, or compound entered from outside. | | `image` | `P3` |
| `spawner-npc` | **Spawner (Enemy Wave Origin)** | Where hostile AI enters the map, sited so defenders have a readable direction to hold against. | | `layout` | |
| `target-practice` | **Target (Practice Targets)** | Static and popping targets set at graded distances downrange — plates, silhouettes, bullseyes — arranged so the player can read which distance they are hitting. | | `both` | |
| `station-loadout` | **TriggerZone (Weapon Bench)** | A bench or rack behind the firing line where players pick and swap the weapon they are practising with. | | `both` | |
| `boundary-shrinking` | **BoundaryZone (Closing Play Area)** | A play boundary that contracts over the match, compressing survivors toward a shifting centre. | | `layout` | |
| `collectible-loot` | **Collectible (Scattered Loot)** | Weapons and equipment distributed across the map so players arm themselves from the world. | | `layout` | |
| `powerup-buffs` | **PowerUp (Armour & Weapon Spawns)** | Fixed-position pickups on a respawn timer that players fight to control. | | `layout` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Team Deathmatch** | Phantom Forces, Arsenal (Roblox); Call of Duty | `lane-network` | `spawn-teambase`, `cover-los`, `choke-bottleneck` |
| **Bomb Defusal** | Counter-Strike, Valorant | `lane-network` | `capture-zone`, `choke-bottleneck`, `cover-los`, `spawn-teambase` |
| **Capture the Flag** | Halo, Team Fortress 2 | `lane-network` | `capture-zone`, `path-flank-tunnel`, `spawn-teambase` |
| **King of the Hill** | Halo, Battlefield Conquest | `lane-network` | `control-zone`, `cover-elevated`, `cover-los` |
| **Arena Deathmatch** | Quake, Doom | `lane-network` | `powerup-buffs`, `cover-elevated`, `path-loop` |
| **Tactical Shooter** | Rainbow Six Siege; [BODYCAM: SWAT Simulator](https://www.roblox.com/games/16404660684/BODYCAM-SWAT-Simulator) (Roblox) | `rooms-sequence` | `building-interior`, `cover-los` |
| **PvE Shooter** | Left 4 Dead, Killing Floor | `lane-network` | `spawner-npc`, `choke-bottleneck`, `building-interior` |
| **Battle Royale** | PUBG, Fortnite, Apex Legends | `open-battlefield` | `boundary-shrinking`, `collectible-loot`, `building-interior` |
| **Aim Trainer** | Aimlabs, Kovaak's; Roblox aim-training and gun-testing places | `range-directed` | `target-practice`, `station-loadout` |

**Genre notes**

* **References.** Phantom Forces and Arsenal for arcade run-and-gun — by far the most common shooter style on the platform. [BODYCAM: SWAT Simulator](https://www.roblox.com/games/16404660684/BODYCAM-SWAT-Simulator) for MilSim.
* **MilSim inverts the arcade assumptions.** Slow, deliberate, high-punishment pacing instead of constant action. The map is a raid site built from rooms that dead-end into breach points, not a looping lane network — players clear in sequence rather than choosing between parallel lanes.
* **Exposed chokepoints are the point in MilSim.** Arcade cover is distributed evenly to keep fights constant; MilSim breach points are *deliberately* exposed because that tension is the design. Don't "fix" them.
* **MilSim usually has no mirrored bases.** It's typically squad-versus-objective PvE, or squad-versus-squad with one life. That implies one staging spawn per squad, not two symmetric respawning bases.
* **Boundaries.** Shooter organizes around firing corridors and sightlines; Action organizes around a shared clash space. Arcade shooters favor unrealistic interconnectedness — rooms with multiple exits — precisely to avoid the dead ends MilSim wants.
* **Four rows carry the two subgenres the rest of the table cannot express.** Battle Royale needs `boundary-shrinking` and `collectible-loot`; PvE needs `spawner-npc`, and `powerup-buffs` serves both. Roblox names both as official subgenres, so they come up often.
* **Roblox's own subgenres for Shooter are Battle Royale, Deathmatch Shooter, and PvE Shooter.** That taxonomy is too coarse for layout: Team Deathmatch, Capture the Flag, King of the Hill, and free-for-all are all *Deathmatch Shooter* to Roblox but need four different maps. The presets use the standard mode names instead, which is the one place a Roblox subgenre name is deliberately not used.
* **The contracting boundary is the cleanest example of an invisible pick.** It has no geometry at all, so it cannot be segmented out of a render and must never enter the image prompt. It is computed and placed against the finished layout.
* **Not every shooter is a match.** The other eight presets are all competitive modes, so a solo aim-training range, a gun-testing place or a target gallery has only one row it can land on. **Aim Trainer** is that row: no opposing team, no route through the map, everything downrange of one firing line. `range-directed` is shared with Sports, where it is a bowling or archery lane; same shape, same P0, different words.
* **A rail or gallery shooter is an Aim Trainer that moves the camera, not a P5.** It has a real set — a firing line, targets, a backdrop — even though the player never walks. Build it and flag `SET`; see *Reading the Pipeline column* in Build.md. Hero shooters are served by the King of the Hill preset today, but class-specific spawn rooms and ability-traversal geometry are not represented — flag it if one comes up.

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
