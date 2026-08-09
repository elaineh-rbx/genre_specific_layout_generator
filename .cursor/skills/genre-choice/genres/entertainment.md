# 15. Entertainment (Showcase & Hub)

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Environments built to be explored, consumed, or performed in rather than "won."*

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `showcase-route` | **Path (Guided Route)** | A single clear walking route, or a small set of connected vignettes, sequencing the visitor through the environment's key compositions. | |
| `showcase-freeroam` | **Zone (Free-Roam Space)** | An open explorable space with no prescribed order. | |
| `hub-portals` | **Zone (Portal Hub)** | A layout whose purpose is to send visitors onward to separate experiences. | `P4` |
| `venue-stage` | **Zone (Stage and Audience)** | A raised performance stage with the audience floor spread in front of it, every sightline in the build oriented toward the stage rather than through the space. | |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `landmark-focal` | **Landmark (Hero Focal Build)** | Large, deliberately composed focal structures positioned to be framed from specific vantage points along the route. | ● | `image` | |
| `spawn-first-reveal` | **SpawnZone (Curated First Reveal)** | Spawn placed and oriented so the very first thing a player sees on joining is a composed shot — never backstage geometry, seams, or the underside of the build. | ● | `both` | |
| `vignette-photo` | **SocialZone (Photo Vignette)** | Well-composed spots distinct from the hero build, made specifically to look good in player screenshots. | ● | `image` | |
| `collectible-nodes` | **Collectible (Hidden Badges)** | Small optional finds tucked off the main route rewarding players who explore further. | | `layout` | |
| `zone-graphics` | **Zone (Graphics-Scaling Set Piece)** | High-fidelity detail clusters — particles, reflections, dense foliage — isolated from the main route so they can be streamed or toggled without hurting performance elsewhere. | | `image` | |
| `social-hub` | **SocialZone (Gathering Area)** | An open space where visitors congregate rather than move through. | | `image` | |
| `teleporter-link` | **Teleporter (Hub Portal Gate)** | Physical, clearly identifiable portal markers at logical endpoints of the layout, each linking out to a separate experience. | | `both` | `P4` |
| `spectator-bleachers` | **SpectatorZone (Raked Audience Seating)** | Stepped seating, terraces, or balconies lifting the back of the crowd so the stage stays visible from the rear of the room. | | `image` | `P0 + tiered` |
| `backstage-support` | **Zone (Backstage)** | Performer-only space behind or beneath the stage — wings, green rooms, and an entrance the audience never uses. | | `image` | `P3` |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Showcase** | [Adventure Time: Land of Ooo](https://www.roblox.com/games/11753761261/Adventure-Time-Land-of-Ooo-Showcase) (Roblox) | `showcase-route` | `landmark-focal`, `spawn-first-reveal`, `vignette-photo` |
| **Free-Roam Showcase** | Roblox architectural and environment showcases | `showcase-freeroam` | `landmark-focal`, `spawn-first-reveal`, `collectible-nodes` |
| **Hub** | Roblox portal hubs | `hub-portals` | `teleporter-link`, `social-hub`, `landmark-focal` |
| **Performance Venue** | Roblox concert, festival and talent-show places; Fortnite live events | `venue-stage` | `spectator-bleachers`, `social-hub`, `spawn-first-reveal` |

**Genre notes**

* **Boundaries.** Here the landmark *is* the content, not an orientation aid or a reward for arriving. If reaching the focal point pays off with an objective, a collectible, or a gate it opens, it's Adventure.
* **The path substitutes for a gameplay loop.** With no combat, scoring, or objective to direct movement, the route itself is the only thing guiding players through the composition. That's why it carries more weight here than in any other genre.
* **The spawn shot is the highest-leverage single decision.** A showcase gets one uncontrolled first impression. Exact camera framing belongs to the Mechanics/Camera doc; placement and orientation belong here.
* **Badges mirror real showcase behaviour.** Actual Roblox showcases commonly award badges for finding side details, which is why hidden collectibles read as native to the genre rather than bolted on.
* **Open question on hub portals.** They're tagged `P4` because the Pipeline treats portals as zone transitions. If portals lead to genuinely separate Roblox *places* rather than zones of this build, the hub itself may be a single-zone P0 layout with teleport markers. Worth confirming.
* **A stage with an audience is a layout, and it had no home.** In a 620-prompt evaluation, nine workers independently coined the phrase *performance venue* for concerts, festivals, talent shows and a dance institution. Every other shape here is architecture you walk around and look at, so the stage kept getting forced into `landmark-focal` — which builds the stage and loses the thing that makes a venue a venue: **the crowd faces one way.** Orientation is the whole design. Sightlines converge, the floor is sized for density rather than circulation, and there is a side of the stage the audience never sees.
* **Roblox's own subgenres here are Music & Audio, Showcase & Hub, and Video.** *Showcase & Hub* is a single Roblox subgenre but two presets here, because a showcase and a hub have different shapes and different pipeline costs. **Video routes to P5** — it is a content-consumption surface with no 3D layout job. **Music & Audio usually does not.** A concert venue, a club, and a listening lounge are all rooms; only a bare music player with no room around it is P5. Judge the space, not the subgenre label.

## Universal Options

Six features that belong to **no genre in particular because they belong to all of them**. Every genre inherits this table on top of its own.

They exist because the alternative is worse. Each was measured against 620 real prompts and requested in eleven to fifteen different genres, so filing them per-genre would restate the same row seventy-eight times — and leaving them out is what produced the largest hole in the system, with *who is in the world* having no home anywhere.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `npc-population` | **Zone (Ambient Population)** | The non-hostile characters who inhabit the space — shopkeepers, wandering crowds, ambient animals, a named figure players come to see — and the ground they occupy. | | `both` | |
| `building-interior` | **Zone (Enterable Interior)** | Buildings players actually go inside rather than interact with from the street. | | `image` | `P3` |
| `water-body` | **Zone (Water Body)** | Standing or flowing water as a real feature of the map — a lake, river, sea, or pool — whether swum through or treated as a barrier. | | `image` | `CHECK` |
| `settlement-density` | **Zone (Settlement)** | Built-up ground at a stated density — a hamlet, a town, or a dense city block grid — rather than scattered individual buildings. | | `image` | |
| `terrain-relief` | **Zone (Terrain Relief)** | Natural landform shaping the ground: hills, mountains, cliffs, a valley, or a canyon. | | `image` | `P0 + tiered` |
| `island-cluster` | **Zone (Island Cluster)** | Several separate landmasses with water or open air between them, crossed by bridge, boat, or flight. | | `image` | `CHECK` |

**None of these is `Core`, and that is deliberate.** They must never appear in the tune menu, which shows `Core` options only, and no preset includes one. A universal option is a **landing place for a request the user actually made** — reached from the open question in step 5 when a free-text ask matches it — never a default and never a suggestion. Measured against 620 prompts, each of the six would fire on 6–15% of them, so a run that applies one unasked is wrong far more often than it is right.

**A genre's own wording wins.** Four genres already define `building-interior` in their own terms — Shooter's is a breachable structure, Survival's is a shelter to hide in. Those rows are the definition for those genres; the universal row is the fallback for the other eleven. Dedupe by ID exactly as with any shared ID.

**Bend the wording to the prompt.** These are written generically because they are genre-neutral, which makes the instruction to rewrite them *more* important than usual, not less. `water-body` for a pirate game is "open sea between the islands, deep enough to sail"; for a park it is "a duck pond at the centre of the green." Ship the prompt's water, not the word "water."

**Two pipeline notes.** `terrain-relief` is `P0 + tiered` for hills and cliffs, but **caves, overhangs, and tunnels push it to `P2`** — say so when the prompt asks for them. `water-body` and `island-cluster` are `CHECK` because swimming and flight are volumetric: usually fine as a play-height envelope over a representable surface, and only a real problem when the volume self-occludes (layered floating islands, 3D cave networks). See *Layout Attributes* in Build.md for the underlying axis.

**`npc-population` is not `spawner-npc`.** `spawner-npc` is where hostiles enter a fight — an emitter, wired to combat. `npc-population` is who lives here. A market crowd, a quest giver, and a herd of deer are not spawners, and filing them as one produces enemy waves in a town square.

### **Counts and quantities**

Any pick may carry a **count** when the prompt states one. "Five islands," "a village of about twenty houses," "three floors" — the number is part of the request and there is nowhere else for it to live. The scale band is a four-value enum and destroys exact figures by design, so a stated quantity that is dropped here is gone.

Record the number the user gave, not a normalised one. If they said "a few," that is not a count — carry it in the text and leave the count empty.
