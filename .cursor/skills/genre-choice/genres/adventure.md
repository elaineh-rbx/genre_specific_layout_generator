# 2. Adventure

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Story-driven journeys and exploration — anywhere from a single explorable map to a multi-chapter quest.*

**Shape — pick one.**

**Typical shapes.** `world-open` *(default)* · `route-guided` · `world-chaptered` · `volume-open-air` · `traversal-city`

This genre words these its own way:

| ID | Shape | What it is |
| :---- | :---- | :---- |
| `world-open` | **Open World** | One contiguous explorable map, found in any order the player likes. |
| `route-guided` | **Guided Corridor** | A single directed route through one continuous space, gated so the player can't wander backward. |


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
| **Guided Trail** | Firewatch | `route-guided` | `path-trail`, `landmark-focal`, `reveal-exit` |

**Genre notes**

* **Boundaries.** Without a focal pull the space is a sandbox, not an adventure. And if the landmark is the whole point rather than a reward for reaching it — nothing to collect, no gate it opens, no further reveal — it's an Entertainment Showcase. Add stats, levelling, or a combat loop and it becomes RPG.
* **Linear does not automatically mean multi-zone.** A valley trail gated by canyons is one contiguous surface and routes P0. Only tag `P4` when chapters are genuinely separate maps that can't co-exist.
* **The reveal is a layout job, not a camera job.** The layout's role is placing the opening and the distant landmark so the composition exists. How the camera frames it belongs to the Mechanics doc.
* **Original framing was too narrow.** Build's first version required chapter gates, cinematic reveals, and objective pedestals — that describes one style of adventure, not the genre. A single explorable map with a ruin in it qualifies.
* **Roblox's own subgenres for Adventure are Exploration, Scavenger Hunt, and Story**, and all three are presets above. Scavenger Hunt is a much larger category on Roblox than off it, driven by the platform's event and badge culture.

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
