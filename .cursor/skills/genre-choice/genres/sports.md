# 12. Sports

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Stadium events, team court and field sports, and physics-based athletics — soccer, basketball, baseball, tennis, cricket.*

Regulation fields are fixed templates, so parametric placement of a known field spec generally beats free image generation — a **P6-lite** generator choice rather than a routing change.

**Shape — pick one.**

**Typical shapes.** `space-bounded` **Zone (Bounded Field or Court)** `P0` *(default)* · `range-directed` **Lane (Directed Range)** `P0`

**The bold name is `Type (Flavor Name)`, and the tag after it is the shape's route** — between them, everything `shape` and `pipeline` need at emit. Take both from here rather than loading `shapes.md`; where this genre rewords a shape, the name above is already its own.

This genre words these its own way:

| ID | Shape | What it is |
| :---- | :---- | :---- |
| `space-bounded` | **Zone (Bounded Field or Court)** | A rigid geometric perimeter — foul lines, touchlines, baselines — defining the active area, with teams competing inside it. |
| `range-directed` | **Lane (Directed Range)** | A single directed lane or range replacing a foul perimeter entirely, with a discrete target at the end — bowling, golf, archery, darts. |


**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `trigger-bounds` | **TriggerZone (Play / Foul Boundary)** | A detection perimeter built so a script can pause or reset play the microsecond a player or ball crosses it. | ● | `both` | |
| `startpoint-play` | **StartPoint (Play-Start Position)** | Pre-determined static positions the ball or players reset to in order to initiate play — pitcher's mound and home plate, centre circle, serve box. | ● | `both` | |
| `trigger-scoring` | **TriggerZone (Scoring Target)** | Volumes or coordinate planes engineered to register points — crossing home plate, entering a goal mouth, passing through a hoop's invisible cylinder. | ● | `both` | |
| `spectator-zone` | **SpectatorZone (Team Sector)** | Dugouts, benches, and sidelines outside the boundary housing inactive players, coaches, and team assets. | | `image` | |
| `marker-distance` | **Marker (Distance Markers)** | Visual cues built into the field denoting spatial progress — yard lines, painted outfield distances. | | `image` | |
| `barrier-perimeter` | **Barrier (Stadium Enclosure)** | The outer wall closing the stadium off and containing balls and players. | | `image` | |
| `spectator-bleachers` | **SpectatorZone (Atmospheric Bleachers)** | Large tiered seating framing the outer perimeter, grounding the player's camera, giving scale, and visually enclosing the map. | | `image` | `P0 + tiered` |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Field Sport** | FIFA, Madden; Football Fusion 2 (Roblox) | `space-bounded` | `trigger-bounds`, `startpoint-play`, `trigger-scoring`, `marker-distance` |
| **Court Sport** | NBA 2K; Roblox basketball games | `space-bounded` | `trigger-bounds`, `trigger-scoring`, `startpoint-play` |
| **Target Sport** | Golf, bowling; Super Golf! (Roblox) | `range-directed` | `trigger-scoring`, `marker-distance` |
| **Physics Sport** | Rocket League | `space-bounded` | `trigger-scoring`, `barrier-perimeter`, `startpoint-play` |
| **Full Stadium** | Any of the above, dressed | `space-bounded` | `spectator-bleachers`, `barrier-perimeter`, `spectator-zone` |

**Genre notes**

* **Target sports don't fit the field model at all.** Bowling, golf, archery, and darts have no foul perimeter and no scoring plane — they have a directed range and a target at the end. Two of the three field-sport staples simply don't apply, which is worth watching: if a third such variant appears, Sports is really two genres.
* **Dugouts are a stadium-build feature, not a sport feature.** An informal pitch or a street court needs none of it, so do not require team enclosures of every sports game.
* **Bleachers are the genre's most common source of tiered elevation.** Stepped seating is relief with no overhang, so it stays P0 — but the height has to be captured or the stadium builds completely flat.
* **Field specs are known quantities.** Regulation dimensions are public and fixed, which makes parametric placement more reliable than asking an image model to invent a tennis court.
* **Roblox files Sports and Racing as two subgenres of one Sports & Racing genre.** This document splits them into genres 12 and 13 instead, because Racing routes P6 and Sports is a parametric template — they share a taxonomy label but almost nothing about how they generate.
* **The scoring options are nearly all `both`.** A goal mouth is visible geometry and an invisible detection plane at the same time, which makes Sports the genre where the drawn/placed distinction shows up most often within single options.

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
