# No Genre

Used when the prompt names no recognisable game type, or when a clarifying
question failed to land on one. **This is a legitimate outcome, not a failure.**
A user who wants "a floating island city" is describing a place, not a genre,
and the layout can be built without ever naming one.

Every ID here is shared with the genre tables, so if a genre is identified
later the picks merge by set union with nothing lost.

## Shape — answer each axis

There is no genre prior to infer from, so the routing axes are asked directly.
Each axis has a default; **the default costs nothing and needs no question.**
Only ask about an axis the prompt leaves genuinely open and that would change
the route.

| Axis | Default | Alternatives | Pipeline |
| :---- | :---- | :---- | :---- |
| **Enclosure** | `exterior` | `interior-only` · `transition` | — · — · `P3` |
| **Verticality** | `single-surface` | `tiered` · `stacked` | — · `P0 + tiered` · `P2` |
| **Zone count** | `single` | `multi-zone` | — · `P4` |
| **Structure-criticality** | `dressed` | `must-be-valid` | — · `P6` |
| **Play-space** | `grounded-surface` | `volumetric` | — · `CHECK` |

Phrase these as plain questions, never as attribute names. "Does the player go
inside buildings?" not "what is your Enclosure value?"

- `interior-only` — play happens entirely inside one enclosed space.
- `transition` — play moves between outside and inside.
- `tiered` — real elevation, but nothing overhangs anything else.
- `stacked` — surfaces sit above each other: floors, bridges, tunnels.
- `multi-zone` — several distinct maps that don't co-exist on one surface.
- `must-be-valid` — the exact topology *is* the game: a solvable maze, a
  connected circuit, a physics-legal jump path.
- `volumetric` — movement through a 3D volume: flight, swimming, space. Fine
  over one representable surface as a play-height envelope; only a problem if
  the volume self-occludes.

## Options

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `landmark-focal` | **Landmark (Orientation Anchor)** | A large distinct structure visible from a distance that tells the player where they are. | ● | `image` | |
| `path-circulation` | **Path (Circulation Route)** | Walkable routes threading the space so movement has an obvious grain. | ● | `image` | |
| `social-hub` | **SocialZone (Gathering Area)** | An open space sized for a crowd to congregate in. | ● | `image` | |
| `boundary-edge` | **BoundaryZone (Map Limit)** | The edge of the world, hidden behind natural barriers wherever possible. | | `image` | |
| `cover-los` | **Cover (Sightline Breakers)** | Geometry that interrupts long views, for concealment or just visual interest. | | `image` | |
| `hazard-kill` | **HazardZone (Dangerous Region)** | An area that damages or kills — water, a drop, a burning field. | | `image` | |
| `vignette-photo` | **SocialZone (Scenic Spot)** | Composed views built to look good from a specific vantage point. | | `image` | |
| `building-interior` | **Zone (Enterable Building)** | Structures the player actually goes inside. | | `image` | `P3` |
| `collectible-nodes` | **Collectible (Scattered Pickups)** | Things to find and gather across the space. | | `layout` | |
| `teleporter-link` | **Teleporter (Fast Travel)** | Paired markers moving players between distant points. | | `both` | |
| `spawn-area` | **SpawnZone (Arrival Point)** | Where players enter the world, placed so the first thing they see is composed. | | `both` | |

## Presets

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Explorable Place** | Any environment showcase | all defaults | `landmark-focal`, `path-circulation`, `vignette-photo` |
| **Social Space** | Roblox hangouts | all defaults | `social-hub`, `spawn-area`, `landmark-focal` |
| **Open Sandbox** | Unstructured creative worlds | all defaults | `path-circulation`, `boundary-edge`, `collectible-nodes` |

## Notes

- **Do not invent a genre to escape this file.** Guessing "probably an obby"
  from a prompt that never said so produces a map the user did not ask for.
  Building what they described and offering these options is the better answer.
- **All defaults is a complete, valid answer.** It routes P0 and builds a
  single-surface exterior map, which is exactly right for most place prompts.
- **If the prompt later reveals a genre** — the user mentions scoring, or
  enemies, or a finish line — switch to that genre file and merge. Shared IDs
  mean nothing already picked is lost.
