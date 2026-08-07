# 8. Shooter

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Competitive team deathmatches, tactical combat, and positioning.*

**Shape — pick one.** How the map organises movement between the shooting.

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `lane-network` | **Lane (Lane Network)** | Parallel routes, classically three, channelling team traffic into predictable engagement fronts. | |
| `breach-sequence` | **Path (Breach Sequence)** | A raid site of rooms that dead-end into breach points, cleared in a defined order rather than looped. | |
| `open-battlefield` | **Zone (Open Battlefield)** | One large contiguous map with dispersed points of interest instead of defined lanes. | |

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
| **Tactical Shooter** | Rainbow Six Siege; [BODYCAM: SWAT Simulator](https://www.roblox.com/games/16404660684/BODYCAM-SWAT-Simulator) (Roblox) | `breach-sequence` | `building-interior`, `cover-los` |
| **PvE Shooter** | Left 4 Dead, Killing Floor | `lane-network` | `spawner-npc`, `choke-bottleneck`, `building-interior` |
| **Battle Royale** | PUBG, Fortnite, Apex Legends | `open-battlefield` | `boundary-shrinking`, `collectible-loot`, `building-interior` |

**Genre notes**

* **References.** Phantom Forces and Arsenal for arcade run-and-gun — by far the most common shooter style on the platform. [BODYCAM: SWAT Simulator](https://www.roblox.com/games/16404660684/BODYCAM-SWAT-Simulator) for MilSim.
* **MilSim inverts the arcade assumptions.** Slow, deliberate, high-punishment pacing instead of constant action. The map is a raid site built from rooms that dead-end into breach points, not a looping lane network — players clear in sequence rather than choosing between parallel lanes.
* **Exposed chokepoints are the point in MilSim.** Arcade cover is distributed evenly to keep fights constant; MilSim breach points are *deliberately* exposed because that tension is the design. Don't "fix" them.
* **MilSim usually has no mirrored bases.** It's typically squad-versus-objective PvE, or squad-versus-squad with one life. That implies one staging spawn per squad, not two symmetric respawning bases.
* **Boundaries.** Shooter organizes around firing corridors and sightlines; Action organizes around a shared clash space. Arcade shooters favor unrealistic interconnectedness — rooms with multiple exits — precisely to avoid the dead ends MilSim wants.
* **Four options exist because the presets demanded them.** The Genre List has always named Battle Royale and PvE shooters, and Roblox's official taxonomy has both as subgenres, yet the table could express neither — no contracting boundary, no scattered loot, no enemy emitter. `boundary-shrinking`, `collectible-loot`, `powerup-buffs`, and `spawner-npc` were added when the preset list made the gaps obvious.
* **Roblox's own subgenres for Shooter are Battle Royale, Deathmatch Shooter, and PvE Shooter.** That taxonomy is too coarse for layout: Team Deathmatch, Capture the Flag, King of the Hill, and free-for-all are all *Deathmatch Shooter* to Roblox but need four different maps. The presets use the standard mode names instead, which is the one place a Roblox subgenre name is deliberately not used.
* **The contracting boundary is the cleanest example of an invisible pick.** It has no geometry at all, so it cannot be segmented out of a render and must never enter the image prompt. It is computed and placed against the finished layout.
* **Still uncovered.** Rail and gallery shooters with no player movement at all (Duck Hunt) have no meaningful layout job and probably route to P5. Hero shooters are served by the Hill Control preset today, but class-specific spawn rooms and ability-traversal geometry are not represented — flag it if one comes up.
