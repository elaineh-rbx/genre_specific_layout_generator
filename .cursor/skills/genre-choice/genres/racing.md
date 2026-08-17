# 13. Racing

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Speed, forward translation, and a designated route from a start point to an end point — foot races, swimming laps, horse racing, vehicle driving.*

**Genre route: `P6`.** The track must read as one continuous connected route, legible from plan view, with no broken or ambiguously self-crossing segments. A free image can't guarantee that, so the route is laid out procedurally first and dressed after.

**Shape — pick one.**

**Typical shapes.** `route-point-to-point` **Path (Point to Point)** `P6` *(default)* · `route-circuit` **Path (Lap Circuit)** `P6` · `route-multitier` **Path (Multi-Tier Circuit)** `P6` + `P2`

**The bold name is `Type (Flavor Name)`, and the tag after it is the shape's route** — between them, everything `shape` and `pipeline` need at emit. Take both from here rather than loading `shapes.md`; where this genre rewords a shape, the name above is already its own.


**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `startpoint-line` | **StartPoint (Start Line)** | The defined position the race begins from — a single marker or a lane slot. | ● | `both` | `P6` |
| `lane-corridor` | **Lane (Lateral Corridor)** | Dividers explicitly marking the allowed corridor of movement — lane ropes in a pool, chalk lines on a track, painted edges on a circuit. | ● | `image` | `P6` |
| `trigger-finish` | **TriggerZone (Terminal Finish)** | A dedicated detection zone at the exact end of the course housing the round-ending trigger — a pool touch-pad wall, a finish line tape, a finish gate. | ● | `both` | `P6` |
| `spawn-grid` | **SpawnZone (Multi-Lane Starting Grid)** | A wide standardized launch front of evenly spaced slots — blocks in a pool, lanes on a track, grid spots on a circuit — so racers align side by side and launch simultaneously without colliding. | | `both` | |
| `trigger-lap` | **TriggerZone (Lap / Split Detection)** | Detection regions at key intervals and turnarounds for split times, lap counting, and checking a runner didn't cut across the field. | | `layout` | |
| `barrier-guardrail` | **Barrier (Physical Guardrail)** | Walls and rails that actually block the racer, as opposed to painted lane markings that only indicate. | | `image` | |
| `path-turnaround` | **Path (180° Turnaround)** | A boundary wall or curved track element forcing a clean direction reversal to begin another lap. | | `image` | |
| `marker-distance` | **Marker (Pacing Markers)** | Visual increments along the lateral boundaries giving an immediate sense of distance covered and relative speed. | | `image` | |
| `spectator-zone` | **SpectatorZone (Trackside Stands)** | Viewing areas outside the corridor for eliminated or waiting players. | | `image` | |
| `hazard-kill` | **HazardZone (Off-Track Penalty)** | Water, gravel, or fall-away edges punishing racers who leave the corridor. | | `image` | |
| `checkpoint-respawn` | **Checkpoint (Course Recovery Point)** | Points a wrecked or fallen racer is restored to, with position, orientation, and zeroed velocity. | | `layout` | |
| `volume-open` | **Zone (Open Play Volume)** | Racing through a volume rather than across a surface — swimming lanes, flight circuits. | | `image` | `CHECK` — fine over one framed surface as a play-height envelope; `P2` only if the volume self-occludes |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Circuit Racing** | Mario Kart; Ultimate Driving (Roblox) | `route-circuit` | `spawn-grid`, `trigger-lap`, `barrier-guardrail`, `path-turnaround` |
| **Sprint / Drag** | Drag racing, track sprints | `route-point-to-point` | `startpoint-line`, `lane-corridor`, `trigger-finish` |
| **Downhill Descent** | Descenders, SSX | `route-point-to-point` | `hazard-kill`, `marker-distance`, `checkpoint-respawn` |
| **Obstacle Race** | Speed Run 4 (Roblox) | `route-point-to-point` | `hazard-kill`, `trigger-finish`, `checkpoint-respawn` |
| **Swimming Lanes** | Olympic swimming | `route-point-to-point` | `lane-corridor`, `trigger-finish`, `path-turnaround`, `volume-open` |
| **Stunt Circuit** | Trackmania; Mario Kart's Rainbow Road | `route-multitier` | `spawn-grid`, `trigger-lap`, `barrier-guardrail` |

**Genre notes**

* **Boundaries.** Racing vs Obby: the racer competes on speed across a finite track or lap count; the obby player takes discrete jumps at their own pace. Racing vs Infinite Runner: the racer controls their own speed and the course ends. Racing vs Vehicle Sim: **if there's no lap and no finish, it's Simulation.**
* **The route failure mode is real and observed.** The reference case (`isometric_i`) produced a track that crossed itself illogically through tunnels and bridges with no followable route. This is the entire reason Racing inverts the pipeline.
* **Coherence applies to A→B courses too.** It's tempting to think only circuits need validating, but a point-to-point downhill still has to read as one followable route in plan view.
* **Lane markings and barriers are different things.** A chalk line indicates a corridor; a guardrail physically stops you. Both are common, they're often both present, and only the second blocks movement.
* **Detection zones are exempt from the global CanTouch rule.** Finish and lap triggers are gameplay detection regions, so Part I §4's blanket `CanTouch = false` doesn't apply to them.
* **Roblox files Racing as a subgenre of Sports & Racing.** Split out here as genre 13 — see the Sports notes for why.
* **Checkpoints were missing.** Every vehicle and obstacle race needs a recovery point that restores position, orientation, and zeroed velocity, and the option only existed under Obby. Now shared.

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
