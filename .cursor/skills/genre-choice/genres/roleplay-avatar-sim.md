# 7. Roleplay & Avatar Sim

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Social life-simulations, town building, and avatar customization.*

**Shape — pick one.** This is the housing model, and it is the single highest-cost decision in the genre.

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `settlement-static` | **Zone (Static Settlement)** | A fixed, pre-built town with no personal property at all; personalization happens through the avatar, never property. | |
| `settlement-claimable` | **Zone (Claimable Houses)** | Pre-built houses scattered through the town that players claim rather than construct, customizing paint or swapping a preset interior. | `P3` |
| `settlement-buildable` | **BuildZone (Personalized Plots)** | Uniform, flat, square lot footprints on a strict grid where players cleanly spawn and build their own houses. | `P3`, plus `P4` if interiors are per-player instances |
| `wilderness-open` | **Zone (Open Natural World)** | No settlement at all — a natural biome of dens, water, and terrain features that players inhabit as creatures. | |
| `stage-runway` | **Zone (Stage and Dressing Rooms)** | A judging runway or catwalk fed by preparation booths, with the audience arranged around it. | |

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
| **Life** | Brookhaven, Bloxburg (Roblox) | `settlement-buildable` | `path-road-vehicle`, `district-zoned`, `building-interior` |
| **Pet Care** | Adopt Me! (Roblox) | `settlement-claimable` | `building-interior`, `social-hub`, `path-street` |
| **Morph Roleplay** | [Welcome to The Town of Robloxia](https://www.roblox.com/games/13213733678/Welcome-to-The-Town-of-Robloxia) (Roblox) | `settlement-static` | `social-hub`, `vignette-photo`, `landmark-focal` |
| **Animal Sim** | Wolves' Life, Warrior Cats (Roblox) | `wilderness-open` | `den-shelter`, `landmark-focal`, `social-hub` |
| **Dress Up** | Dress to Impress (Roblox) | `stage-runway` | `vignette-photo`, `social-hub` |

**Genre notes**

* **References.** [Adventure Time: Land of Ooo Showcase](https://www.roblox.com/games/11753761261/Adventure-Time-Land-of-Ooo-Showcase) for static map. [Welcome to The Town of Robloxia](https://www.roblox.com/games/13213733678/Welcome-to-The-Town-of-Robloxia) for claimable houses. Bloxburg and Brookhaven for full personalized building.
* **Pick the housing model before assuming a plot.** Full player-constructed housing is common on front-page hits, which makes it look like the default — but it's actually the *least* common of the three models across the genre. Check which one the game really is before laying out a grid of empty lots.
* **Boundaries.** Roleplay is open-ended social storytelling. If the loop is a defined, repeatable set of job tasks — pilot, doctor, trucker, farmer — it's Simulation's Role Sim bundle instead.
* **Vehicle roads are conditional.** 15- and 30-stud streets exist so car meshes can turn. A walking-only roleplay town doesn't need them, and Build's original version wrongly demanded them of every game in the genre.
* **This genre is P3 by default in practice.** Every housing model except Static Settlement involves enterable interiors, which is a real and unavoidable pipeline cost — worth surfacing to the user early rather than at build time.
* **Roblox's own subgenres here are Animal Sim, Dress Up, Life, Morph Roleplay, and Pet Care** — all five are presets above, and building them forced two shapes and one option that did not exist. **An animal sim has no town**, so it needed `wilderness-open` and `den-shelter`; **a dress-up game has no settlement either**, just a runway and preparation booths, so it needed `stage-runway`. The genre had silently assumed a human town.
* **Two of the five presets are among the largest games on the platform.** Adopt Me! and Dress to Impress are Pet Care and Dress Up respectively, so these are not fringe cases — they were simply unrepresented.
