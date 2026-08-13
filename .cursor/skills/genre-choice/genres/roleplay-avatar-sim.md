# 7. Roleplay & Avatar Sim

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Social life-simulations, town building, and avatar customization.*

**Shape — pick one.** This is the housing model, and it is the single highest-cost decision in the genre.

**Typical shapes.** `settlement-static` · `settlement-claimable` *(default)* · `settlement-buildable` · `wilderness-open` · `stage-runway` · `interior-single`


**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `social-hub` | **SocialZone (Town Square Core)** | A central, deliberately oversized gathering hub built to handle maximum avatar density without traffic jams. | ● | `image` | |
| `path-street` | **Path (Pedestrian Circulation)** | Walkable circulation linking the square to the game's venues — streets, walkways, hallways sized for foot traffic. | ● | `image` | |
| `path-road-vehicle` | **Path (Vehicle Road Network)** | Wide, flat, grid-aligned streets — **15 studs minimum one-way, 30 studs two-way** — snaking between residential and commercial zones so vehicle meshes turn without clipping walls. | | `image` | |
| `district-zoned` | **Zone (Zoned Districts)** | Clear physical separation between loud commercial strips — stores, dealerships — and quiet residential streets. | | `image` | |
| `vignette-photo` | **SocialZone (Scenic Backdrop)** | Highly detailed spots — fountains, parks, beach boardwalks — built specifically as backgrounds for screenshots and roleplay scenes. | | `image` | |
| `landmark-focal` | **Landmark (Town Orientation Anchor)** | A distinct structure visible across the map so players can navigate by sight. | | `image` | |
| `teleporter-link` | **Teleporter (Venue Shortcut)** | Fast transport between distant districts for players who don't want to walk. | | `both` | |
| `building-interior` | **Zone (Enterable Interior)** | Shops, homes, and venues players go inside. | | `image` | `P3` |
| `den-shelter` | **Zone (Den or Nest)** | Natural shelters — caves, hollows, burrows — that animal players claim and return to. | | `image` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Life** | Brookhaven (Roblox) | `settlement-claimable` | `path-road-vehicle`, `district-zoned`, `building-interior` |
| **Home Builder** | Bloxburg (Roblox) | `settlement-buildable` | `path-road-vehicle`, `building-interior`, `social-hub` |
| **Pet Care** | Adopt Me! (Roblox) | `settlement-claimable` | `building-interior`, `social-hub`, `path-street` |
| **Morph Roleplay** | [Welcome to The Town of Robloxia](https://www.roblox.com/games/13213733678/Welcome-to-The-Town-of-Robloxia) (Roblox) | `settlement-static` | `social-hub`, `vignette-photo`, `landmark-focal` |
| **Animal Sim** | Wolves' Life, Warrior Cats (Roblox) | `wilderness-open` | `den-shelter`, `landmark-focal`, `social-hub` |
| **Dress Up** | Dress to Impress (Roblox) | `stage-runway` | `vignette-photo`, `social-hub` |

**Genre notes**

* **References.** [Adventure Time: Land of Ooo Showcase](https://www.roblox.com/games/11753761261/Adventure-Time-Land-of-Ooo-Showcase) for static map. [Welcome to The Town of Robloxia](https://www.roblox.com/games/13213733678/Welcome-to-The-Town-of-Robloxia) for claimable houses. Bloxburg and Brookhaven for full personalized building.
* **Pick the housing model before assuming a plot.** Full player-constructed housing is common on front-page hits, which makes it look like the default — but it's actually the *least* common of the three models across the genre. Check which one the game really is before laying out a grid of empty lots.
* **Life and Home Builder are two presets because Brookhaven and Bloxburg are two games.** A single preset citing both defaults to buildable plots, so a prompt naming Brookhaven outright gets a grid of empty lots. **Brookhaven hands players a finished house to claim.** The note directly above already said so; a single preset spanning both models was what overrode it. When a prompt names neither game, "move into a house" is Life and "build your own house" is Home Builder; if it is genuinely unclear, Life is the safer default because claiming is the more common model.
* **Boundaries.** Roleplay is open-ended social storytelling. If the loop is a defined, repeatable set of job tasks — pilot, doctor, trucker, farmer — it's Simulation's Role Sim bundle instead.
* **Vehicle roads are conditional.** 15- and 30-stud streets exist so car meshes can turn. A walking-only roleplay town does not need them, so do not apply the street widths genre-wide.
* **This genre is P3 by default in practice.** Every housing model except Static Settlement involves enterable interiors, which is a real and unavoidable pipeline cost — worth surfacing to the user early rather than at build time.
* **Roblox's own subgenres here are Animal Sim, Dress Up, Life, Morph Roleplay, and Pet Care** — all five are presets above, and three of them need shapes that are not a human town. **An animal sim has no town**: it is `wilderness-open` and `den-shelter`. **A dress-up game has no settlement either**, just a runway and preparation booths, which is `stage-runway`. Do not assume housing.
* **Two of those five are among the largest games on the platform.** Adopt Me! is Pet Care and Dress to Impress is Dress Up, so neither is a fringe case.

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
