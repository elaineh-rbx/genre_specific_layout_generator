# 2. Adventure

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Story-driven journeys and exploration — anywhere from a single explorable map to a multi-chapter quest.*

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `world-open` | **Open World** | One contiguous explorable map, found in any order the player likes. | |
| `world-corridor` | **Guided Corridor** | A single directed route through one continuous space, gated so the player can't wander backward. | |
| `world-chaptered` | **Chaptered Journey** | Story chapters as genuinely separate maps that don't co-exist on one surface. | `P4` |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `path-trail` | **Path (Exploration Trail)** | A walkable route threading the space — a worn track, road, canyon floor, or ridge line. | ● | `image` | |
| `landmark-focal` | **Landmark (Directed Point of Interest)** | A ruin, vista, or structure that pulls the player toward it and gives exploration a direction. | ● | `image` | |
| `collectible-nodes` | **Collectible (Objective Items)** | Quest items and narrative targets housed on altars, pedestals, or in ruins. | ● | `layout` | |
| `alcove-secret` | **Zone (Discovery Alcove)** | Hidden cutouts behind waterfalls, fake walls, or overgrowth that reward poking around. | | `image` | |
| `gate-oneway` | **Gate (One-Way Drop)** | Low cliffs or drop-downs that stop players wandering back into finished areas. | | `image` | |
| `gate-chapter` | **Gate (Chapter Threshold)** | A canyon, gate, or structural door marking a definite transition between story chapters. | | `image` | |
| `reveal-exit` | **Path (Cinematic Reveal Exit)** | A structural exit — a tight cave opening into a massive valley — placed so the layout itself reveals a distant landmark. | | `image` | `P3` |
| `tracker-quest` | **Tracker (Quest Board)** | A physical board or pillar where objectives are posted and tracked. | | `both` | |
| `gate-progression` | **Gate (Story Lock)** | A door or barrier that stays shut until the current objective is done. | | `image` | |
| `teleporter-link` | **Teleporter (Fast Travel)** | Paired markers letting players skip back to already-discovered locations. | | `both` | |
| `checkpoint-respawn` | **Checkpoint (Journey Save Point)** | Rest points along the route that players return to rather than restarting the chapter. | | `layout` | |
| `hazard-kill` | **HazardZone (Environmental Danger)** | Chasms, rapids, or lava fields that punish careless traversal. | | `image` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Exploration** | Breath of the Wild, Journey | `world-open` | `landmark-focal`, `alcove-secret`, `path-trail` |
| **Scavenger Hunt** | Find the Markers (Roblox); Roblox Egg Hunt events | `world-open` | `collectible-nodes`, `alcove-secret`, `tracker-quest` |
| **Story** | Uncharted, A Short Hike | `world-chaptered` | `gate-chapter`, `reveal-exit`, `gate-oneway` |
| **Quest Hub** | The Legend of Zelda; World // Zero (Roblox) | `world-open` | `tracker-quest`, `gate-progression`, `teleporter-link` |
| **Guided Trail** | Firewatch | `world-corridor` | `path-trail`, `landmark-focal`, `reveal-exit` |

**Genre notes**

* **Boundaries.** Without a focal pull the space is a sandbox, not an adventure. And if the landmark is the whole point rather than a reward for reaching it — nothing to collect, no gate it opens, no further reveal — it's an Entertainment Showcase. Add stats, levelling, or a combat loop and it becomes RPG.
* **Linear does not automatically mean multi-zone.** A valley trail gated by canyons is one contiguous surface and routes P0. Only tag `P4` when chapters are genuinely separate maps that can't co-exist.
* **The reveal is a layout job, not a camera job.** The layout's role is placing the opening and the distant landmark so the composition exists. How the camera frames it belongs to the Mechanics doc.
* **Original framing was too narrow.** Build's first version required chapter gates, cinematic reveals, and objective pedestals — that describes one style of adventure, not the genre. A single explorable map with a ruin in it qualifies.
* **Roblox's own subgenres for Adventure are Exploration, Scavenger Hunt, and Story**, and all three are presets above. Scavenger Hunt is a much larger category on Roblox than off it, driven by the platform's event and badge culture.
