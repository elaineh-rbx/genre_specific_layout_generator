# 14. Infinite Runner

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Automated forward translation, reaction timing, and surviving a procedurally generated endless path.*

**Genre route: `P6`.** Procedural by nature — the layout is chunk rules, not a fixed map. Obstacle spacing must be elastic (`spacing = CurrentSpeed × 0.5 s` of reaction time) so every emitted sequence stays clearable as the player accelerates.

**Shape — pick one.** This is the genre's real fork, and it changes the chunk geometry.

**Typical shapes.** `lane-snap` **Lane (Fixed Lane Snap)** `P6` · `lane-free` **Lane (Free Lateral Steering)** `P6` *(default)*

**The bold name is `Type (Flavor Name)`, and the tag after it is the shape's route** — between them, everything `shape` and `pipeline` need at emit. Take both from here rather than loading `shapes.md`; where this genre rewords a shape, the name above is already its own.


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
* **The cleanup volume is specified by placement, not by the memory concern.** It is a placed volume, so it is layout; what it is *for* is runtime memory management, which is Mechanics. Specify how far behind the camera it sits and leave the rest alone.
* **Roblox files Runner as a subgenre of Obby & Platformer; here it is its own genre.** A runner routes P6 with elastic speed-derived spacing and shares almost none of its generation with a difficulty-chart obby. The skill should still recognise "runner" arriving as an obby request, since that is the wording Roblox's own taxonomy teaches creators.

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
