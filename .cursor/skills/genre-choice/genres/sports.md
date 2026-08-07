# 12. Sports

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Stadium events, team court and field sports, and physics-based athletics — soccer, basketball, baseball, tennis, cricket.*

Regulation fields are fixed templates, so parametric placement of a known field spec generally beats free image generation — a **P6-lite** generator choice rather than a routing change.

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `field-bounded` | **Zone (Bounded Field or Court)** | A rigid geometric perimeter — foul lines, touchlines, baselines — defining the active area, with teams competing inside it. | |
| `range-directed` | **Lane (Directed Range)** | A single directed lane or range replacing a foul perimeter entirely, with a discrete target at the end — bowling, golf, archery, darts. | |

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
| **Field Sport** | FIFA, Madden; Football Fusion 2 (Roblox) | `field-bounded` | `trigger-bounds`, `startpoint-play`, `trigger-scoring`, `marker-distance` |
| **Court Sport** | NBA 2K; Roblox basketball games | `field-bounded` | `trigger-bounds`, `trigger-scoring`, `startpoint-play` |
| **Target Sport** | Golf, bowling; Super Golf! (Roblox) | `range-directed` | `trigger-scoring`, `marker-distance` |
| **Physics Sport** | Rocket League | `field-bounded` | `trigger-scoring`, `barrier-perimeter`, `startpoint-play` |
| **Full Stadium** | Any of the above, dressed | `field-bounded` | `spectator-bleachers`, `barrier-perimeter`, `spectator-zone` |

**Genre notes**

* **Target sports don't fit the field model at all.** Bowling, golf, archery, and darts have no foul perimeter and no scoring plane — they have a directed range and a target at the end. Two of the three field-sport staples simply don't apply, which is worth watching: if a third such variant appears, Sports is really two genres.
* **Dugouts are a stadium-build feature, not a sport feature.** An informal pitch or a street court needs none of it. Build's original version required team enclosures of every sports game.
* **Bleachers are the genre's most common source of tiered elevation.** Stepped seating is relief with no overhang, so it stays P0 — but the height has to be captured or the stadium builds completely flat.
* **Field specs are known quantities.** Regulation dimensions are public and fixed, which makes parametric placement more reliable than asking an image model to invent a tennis court.
* **Roblox files Sports and Racing as two subgenres of one Sports & Racing genre.** This document splits them into genres 12 and 13 instead, because Racing routes P6 and Sports is a parametric template — they share a taxonomy label but almost nothing about how they generate.
* **The scoring options are nearly all `both`.** A goal mouth is visible geometry and an invisible detection plane at the same time, which makes Sports the genre where the drawn/placed distinction shows up most often within single options.
