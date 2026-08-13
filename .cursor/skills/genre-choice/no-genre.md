# No Genre

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

Used when the prompt names no recognisable game type, or when a clarifying question failed to land on one. **This is a legitimate outcome, not a failure.** A user who wants "a floating island city" is describing a place, not a genre, and the layout can be built without ever naming one.

**This is not a rare fallback.** It is the right answer on a meaningful share of prompts, and its *Explorable Place* preset is picked more often than most genre presets.

Every ID here is shared with the genre tables, so if a genre is identified later the picks merge by set union with nothing lost.

**Shape — answer each axis.** There is no genre prior to infer from, so the routing axes are asked directly. Each axis has a default; **the default costs nothing and needs no question.** Only ask about an axis the prompt leaves genuinely open and that would change the route.

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `axis-enclosure` | **Enclosure** | `exterior` (default) · `interior-only`, play happens entirely inside one enclosed space · `transition`, play moves between outside and inside. | `P3` for `transition` only |
| `axis-verticality` | **Verticality** | `single-surface` (default) · `tiered`, real elevation with nothing overhanging · `stacked`, surfaces above each other — floors, bridges, tunnels. | `P0 + tiered` for `tiered`, `P2` for `stacked` |
| `axis-zone-count` | **Zone count** | `single` (default) · `multi-zone`, several distinct maps that don't co-exist on one surface. | `P4` |
| `axis-structure` | **Structure-criticality** | `dressed` (default) · `must-be-valid`, where the exact topology *is* the game: a solvable maze, a connected circuit, a physics-legal jump path. | `P6` |
| `axis-play-space` | **Play-space** | `grounded-surface` (default) · `volumetric`, movement through a 3D volume — flight, swimming, space. Fine over one representable surface as a play-height envelope; a problem only if the volume self-occludes. | `CHECK` |

Phrase these as plain questions, never as attribute names. "Does the player go inside buildings?" not "what is your Enclosure value?" **Only the non-default value carries the pipeline cost shown.**

**Options** — combine freely on top of the chosen axes.

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

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Explorable Place** | Any environment showcase | `axis-enclosure` | `landmark-focal`, `path-circulation`, `vignette-photo` |
| **Social Space** | Roblox hangouts | `axis-enclosure` | `social-hub`, `spawn-area`, `landmark-focal` |
| **Open Sandbox** | Unstructured creative worlds | `axis-enclosure` | `path-circulation`, `boundary-edge`, `collectible-nodes` |

All three presets leave every axis at its default, which routes `P0`. The shape column names an axis only because the table requires one.

**Genre notes**

* **Do not invent a genre to escape this file.** Guessing "probably an obby" from a prompt that never said so produces a map the user did not ask for. Building what they described and offering these options is the better answer.
* **All defaults is a complete, valid answer.** It routes P0 and builds a single-surface exterior map, which is exactly right for most place prompts.
* **If the prompt later reveals a genre** — the user mentions scoring, or enemies, or a finish line — switch to that genre file and merge. Shared IDs mean nothing already picked is lost.
* **The Universal Options matter more here than anywhere else.** A prompt with no genre is usually describing a *place*, and water, terrain, settlement density, islands and who lives there are what a place is made of.

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
