# 13. Racing

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Speed, forward translation, and a designated route from a start point to an end point — foot races, swimming laps, horse racing, vehicle driving.*

**Genre route: `P6`.** The track must read as one continuous connected route, legible from plan view, with no broken or ambiguously self-crossing segments. A free image can't guarantee that, so the route is laid out procedurally first and dressed after.

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `route-point-to-point` | **Path (Point to Point)** | A course that starts in one place and ends in another — downhill, drag, sprint, single-swimmer. | `P6` |
| `route-circuit` | **Path (Lap Circuit)** | A closed loop run a set number of times. | `P6` |
| `route-multitier` | **Path (Multi-Tier Circuit)** | A circuit whose sections cross above or below other sections of the same course. | `P6 + P2` |

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

**Genre notes**

* **Boundaries.** Racing vs Obby: the racer competes on speed across a finite track or lap count; the obby player takes discrete jumps at their own pace. Racing vs Infinite Runner: the racer controls their own speed and the course ends. Racing vs Vehicle Sim: **if there's no lap and no finish, it's Simulation.**
* **The route failure mode is real and observed.** The reference case (`isometric_i`) produced a track that crossed itself illogically through tunnels and bridges with no followable route. This is the entire reason Racing inverts the pipeline.
* **Coherence applies to A→B courses too.** It's tempting to think only circuits need validating, but a point-to-point downhill still has to read as one followable route in plan view.
* **Lane markings and barriers are different things.** A chalk line indicates a corridor; a guardrail physically stops you. Both are common, they're often both present, and only the second blocks movement.
* **Detection zones are exempt from the global CanTouch rule.** Finish and lap triggers are gameplay detection regions, so Part I §4's blanket `CanTouch = false` doesn't apply to them.
* **Roblox files Racing as a subgenre of Sports & Racing.** Split out here as genre 13 — see the Sports notes for why.
* **Checkpoints were missing.** Every vehicle and obstacle race needs a recovery point that restores position, orientation, and zeroed velocity, and the option only existed under Obby. Now shared.
