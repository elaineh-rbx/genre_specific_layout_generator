# 14. Infinite Runner

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Automated forward translation, reaction timing, and surviving a procedurally generated endless path.*

**Genre route: `P6`.** Procedural by nature — the layout is chunk rules, not a fixed map. Obstacle spacing must be elastic (`spacing = CurrentSpeed × 0.5 s` of reaction time) so every emitted sequence stays clearable as the player accelerates.

**Shape — pick one.** This is the genre's real fork, and it changes the chunk geometry.

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `lane-snap` | **Lane (Fixed Lane Snap)** | Rigid parallel lanes, typically three, each the avatar bounding box plus a 2-stud safety margin so lateral dashes snap instantly without clipping geometry. | `P6` |
| `lane-free` | **Lane (Free Lateral Steering)** | Continuous lateral movement across a corridor instead of discrete lane slots. | `P6` |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `chunk-modular` | **Chunk (Deterministic Segment)** | Modular track segments whose exit pivot matches the next segment's origin pivot on a single axis, preventing progressive geometric drift over a long run. | ● | `image` | `P6` |
| `hazard-kill` | **HazardZone (Run-Ending Hazard)** | Whatever ends the run on contact — a train, a pit, a pursuing threat. | ● | `image` | |
| `obstacle-jump` | **Path (Jump Obstacles)** | Barriers to hurdle and gaps to clear as the lanes scroll past. | ● | `image` | |
| `obstacle-moving` | **Path (Moving Obstacles)** | Traffic, swinging hazards, and lane-crossing objects timed against the player's speed. | | `image` | |
| `trigger-despawn` | **TriggerZone (Cleanup Volume)** | A volume set a fixed distance behind the camera that recycles cleared geometry out of the world. | | `layout` | |
| `barrier-horizon` | **Barrier (Horizon Occlusion)** | Atmospheric fog or a sharp turn at the end of the chunk queue, masking the fact the next piece of world is spawning from nothing. | | `image` | |
| `collectible-nodes` | **Collectible (Coin Trails)** | Pickup runs laid along lanes to bait players into riskier lines. | | `layout` | |
| `powerup-buffs` | **PowerUp (Run Boosts)** | Magnets, shields, and speed boosts that alter a stretch of the run. | | `layout` | |
| `marker-distance` | **Marker (Distance Feedback)** | Environmental increments giving a sense of how far the run has gone. | | `image` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Lane Runner** | Subway Surfers | `lane-snap` | `chunk-modular`, `collectible-nodes`, `obstacle-moving` |
| **Free Runner** | Temple Run | `lane-free` | `chunk-modular`, `obstacle-jump`, `hazard-kill` |
| **Chase Runner** | Temple Run, Crash Bandicoot boulder runs | `lane-free` | `hazard-kill`, `obstacle-moving`, `barrier-horizon` |
| **Endless Climber** | Doodle Jump | `lane-free` | `obstacle-jump`, `collectible-nodes` |

**Genre notes**

* **Boundaries.** Forward motion is automatic and the path is endless. If the player controls their own speed, it's Racing; if they control their own movement over discrete jumps, it's Obby.
* **Lane snap versus free lateral is the genre's real fork.** Subway Surfers snaps between three fixed lanes; Temple Run steers continuously. They produce different chunk geometry, and the 3-lane assumption shouldn't be applied to both.
* **Spacing must be elastic, not fixed.** Players accelerate the further they get, so a gap authored in fixed studs becomes unclearable later in the run. Everything is derived from current speed against reaction time.
* **Chunk pivots are the thing that breaks silently.** If exit and origin pivots don't match exactly on one axis, the track drifts a little per chunk and the run degrades over minutes rather than failing visibly.
* **Scope caveat on the cleanup volume.** It's a placed volume, so it's arguably layout, but its justification is runtime memory management. Kept here framed by *placement* — how far behind the camera it sits — rather than by the memory concern, which is Mechanics.
* **Roblox files Runner as a subgenre of Obby & Platformer, not as its own genre.** Kept separate here because a runner routes P6 with elastic speed-derived spacing and shares almost none of its generation with a difficulty-chart obby. The skill should still recognise "runner" arriving as an obby request, since that is the wording Roblox's own taxonomy teaches creators.
