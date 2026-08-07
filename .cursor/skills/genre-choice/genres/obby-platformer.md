# 3. Obby & Platformer

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Obstacle courses, skill-based climbing, and movement challenges. The player controls their own movement and takes discrete jumps at their own pace.*

**Genre route: `P6`.** Physics-legal platform spacing *is* the game, so the course is generated procedurally first and dressed after. Gaps on the critical path must stay within Part I §1 limits — **≤ 11 studs** horizontal, **≤ 7.2 studs** vertical at default `WalkSpeed`/`JumpHeight`.

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `course-flat` | **Path (Flat Course)** | A course laid out across the ground, progressing horizontally. | `P6` |
| `course-terraced` | **Path (Ascending Terraces)** | A course climbing a hillside or staircase — strong vertical gain, nothing overhanging. | `P6 + tiered` |
| `course-tower` | **Path (Tower / Spiral Ascent)** | A course wrapping or stacking so platforms sit directly above each other. | `P6 + P2` |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `path-track` | **Path (Sequential Platform Track)** | A chain of platforms spaced to the physics limits above — the ordered route through the course. | ● | `image` | `P6` |
| `checkpoint-respawn` | **Checkpoint (Safe Landing Pad)** | Flat enclosed pads where players stop safely and respawn on failure instead of restarting the course. | ● | `both` | |
| `hazard-kill` | **HazardZone (Contact-Lethal Surfaces)** | Surfaces that kill on touch — strips, checkers, rolling balls, closing walls, deadly-sided paths. | ● | `image` | |
| `obstacle-jump` | **Path (Jump Obstacles)** | Long horizontal jumps, trampoline boosts, wrap-arounds, and stepped vertical platforms. | | `image` | |
| `obstacle-moving` | **Path (Moving Obstacles)** | Rotating platforms, conveyors, and swinging or sliding hazards. | | `image` | |
| `obstacle-timing` | **Path (Timed Obstacles)** | Platforms that vanish after being stepped on, or a set time after activation. | | `image` | |
| `obstacle-climb` | **Path (Climb Obstacles)** | Trusses, ladders, tightropes, and wall scrambles. | | `image` | |
| `obstacle-guess` | **Path (Guess Obstacles)** | Hidden-correct-path and door-guessing sections where the wrong pick drops you. | | `image` | |
| `obstacle-maze` | **Zone (Maze Segment)** | A maze the player has to route through mid-course. | | `image` | `P6` |
| `path-shortcut` | **Path (High-Risk Shortcut)** | Significantly tighter alternate routes that skip ahead for skilled players. | | `image` | |
| `path-road-vehicle` | **Path (Drivable Roadway)** | A continuous surfaced route wide enough to drive, replacing discrete platforms wherever the course is driven rather than jumped. | | `image` | `P6` |
| `social-hub` | **SocialZone (Start Hub & Shop)** | A lobby at the course entrance where players gather, buy upgrades, and choose a stage before setting off. | | `image` | |
| `winner-zone` | **WinnerZone (End Reward Area)** | The payoff at the end — path tools, flight tools, speed, morphs, interactables. | | `both` | |
| `spectator-zone` | **SpectatorZone (Glass Overlook)** | A separate balcony where eliminated players watch the active track. | | `image` | |
| `collectible-nodes` | **Collectible (Course Pickups)** | Coins or tokens placed on risky lines to bait players off the safe route. | | `layout` | |
| `powerup-buffs` | **PowerUp (Movement Buffs)** | Speed or jump pickups that change how a section can be cleared. | | `layout` | |
| `teleporter-link` | **Teleporter (Stage Skip)** | Markers that jump players between stages or back to a hub. | | `both` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Classic Obby** | [Doc's Difficulty Chart Obby 2](https://www.roblox.com/games/7013860652/Docs-Difficulty-Chart-Obby-2) (Roblox) | `course-flat` | `path-track`, `checkpoint-respawn`, `obstacle-jump`, `obstacle-moving` |
| **Tower Obby** | Tower of Hell (Roblox) | `course-tower` | `path-track`, `obstacle-timing`, `obstacle-climb`, `winner-zone` |
| **Precision Platformer** | Super Mario 64, Celeste | `course-terraced` | `obstacle-jump`, `obstacle-moving`, `path-shortcut` |
| **Vehicle Obby** | Roblox vehicle obbies | `course-flat` | `path-road-vehicle`, `checkpoint-respawn`, `hazard-kill` |
| **Co-op Obby** | Roblox two-player obbies | `course-flat` | `path-track`, `checkpoint-respawn`, `teleporter-link` |
| **Glitch Obby** | Roblox glitch obbies | `course-tower` | `obstacle-climb`, `path-shortcut` |

**Preset caveats.** *Vehicle Obby* derives spacing from turning radius, top speed, and ramp tolerance rather than jump metrics; checkpoints restore vehicle position, orientation, and zeroed velocity; lane widths follow the vehicle bounding box rather than the 4-stud avatar standard. *Co-op Obby* spaces to the pair's combined reach, saves both players at a checkpoint together, and may use `teleporter-link` to swap roles. *Glitch Obby* sets gaps deliberately **beyond** normal limits and cannot be validated — see the notes below.

**Genre notes**

* **Reference.** [Doc's Difficulty Chart Obby 2](https://www.roblox.com/games/7013860652/Docs-Difficulty-Chart-Obby-2). Tower of Hell is the platform's canonical tower obby.
* **Boundaries.** Obby vs Racing: the obby player moves at their own pace over discrete jumps; a racer is competing on speed over a finite track or lap count. **A vehicle obby that adds lap counting or a multi-lane starting grid has become Racing — build it there.** Obby vs Infinite Runner: forward motion is the player's in an obby, automatic in a runner.
* **The full obstacle catalog.** The five grouped `obstacle-*` options above compress a longer working list: *Guess* — hidden path, door choice. *Jumps* — horizontal long jumps, trampoline boosts, wraps (horizontal in-and-out movement around a part), vertical platforms (in-and-out movement to climb). *Other* — maze, moving and rotating platforms and deadly objects, conveyors (which hinder by slowing the player or by making them too fast to judge jumps), tight rope, truss and ladder climbs, timed paths (disappear *t* seconds after activation — beat-the-clock feel), disappearing paths (vanish after being stepped on — survival feel). Treat it as a toolkit, not a taxonomy.
* **Classic vs bespoke.** Difficulty-chart obbies reuse these blocks directly and repetitively. Modern bespoke obbies increasingly blend several into unique hand-built stage environments rather than repeating a fixed set — so don't assume a stage is one obstacle type.
* **Most obbies aren't lethal on contact.** Failure is usually falling into a void or timing out, not touching something deadly. Reserve `hazard-kill` for genuinely contact-lethal obstacles rather than applying it to every hazard.
* **Checkpoints are near-universal but not universal.** Very short courses and intentionally hardcore no-checkpoint obbies deliberately omit them.
* **Two options exist because a dry run of the skill demanded them.** Walking real prompts through the genre file surfaced that Obby could express neither the start hub with a shop — near-universal on Roblox and the thing a user means by "and there's a shop town" — nor the drivable roadway a *Vehicle Obby* obviously runs on, which left that preset building discrete platforms for cars. `social-hub` and `path-road-vehicle` were added for them, reusing the shared IDs so the concept dedupes cleanly when Obby is mixed with Roleplay or Simulation.
* **Glitch obbies can't be validated.** They rely on undocumented `Humanoid` state-machine timing — wallhopping, ladder flicking, corner clipping — rather than the documented physics baseline. Spacing can't be derived from Part I and the P6 generator can't check it; treat the structure as author-supplied.
* **Co-op obbies break the "own pace" assumption.** Balloon-and-holder and frog-and-tongue pairs have complementary movement abilities, so neither player can progress solo. The layout has to make separation and permanent stranding impossible.
* **Roblox's own subgenres here are Classic Obby, Tower Obby, and Runner.** The first two are presets above. **Runner is filed by Roblox under this genre but is genre 14 here** — see the note there for why the split is deliberate.
