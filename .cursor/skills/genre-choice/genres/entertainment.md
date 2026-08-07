# 15. Entertainment (Showcase & Hub)

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Environments built to be explored or consumed rather than "won." Music & Audio and Video subgenres rarely involve a 3D environment at all — route those to **P5**.*

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `showcase-route` | **Path (Guided Route)** | A single clear walking route, or a small set of connected vignettes, sequencing the visitor through the environment's key compositions. | |
| `showcase-freeroam` | **Zone (Free-Roam Space)** | An open explorable space with no prescribed order. | |
| `hub-portals` | **Zone (Portal Hub)** | A layout whose purpose is to send visitors onward to separate experiences. | `P4` |

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

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Showcase** | [Adventure Time: Land of Ooo](https://www.roblox.com/games/11753761261/Adventure-Time-Land-of-Ooo-Showcase) (Roblox) | `showcase-route` | `landmark-focal`, `spawn-first-reveal`, `vignette-photo` |
| **Free-Roam Showcase** | Roblox architectural and environment showcases | `showcase-freeroam` | `landmark-focal`, `spawn-first-reveal`, `collectible-nodes` |
| **Hub** | Roblox portal hubs | `hub-portals` | `teleporter-link`, `social-hub`, `landmark-focal` |

**Genre notes**

* **Boundaries.** Here the landmark *is* the content, not an orientation aid or a reward for arriving. If reaching the focal point pays off with an objective, a collectible, or a gate it opens, it's Adventure.
* **The path substitutes for a gameplay loop.** With no combat, scoring, or objective to direct movement, the route itself is the only thing guiding players through the composition. That's why it carries more weight here than in any other genre.
* **The spawn shot is the highest-leverage single decision.** A showcase gets one uncontrolled first impression. Exact camera framing belongs to the Mechanics/Camera doc; placement and orientation belong here.
* **Badges mirror real showcase behaviour.** Actual Roblox showcases commonly award badges for finding side details, which is why hidden collectibles read as native to the genre rather than bolted on.
* **Open question on hub portals.** They're tagged `P4` because the Pipeline treats portals as zone transitions. If portals lead to genuinely separate Roblox *places* rather than zones of this build, the hub itself may be a single-zone P0 layout with teleport markers. Worth confirming.
* **Roblox's own subgenres here are Music & Audio, Showcase & Hub, and Video.** *Showcase & Hub* is a single Roblox subgenre but two presets here, because a showcase and a hub have different shapes and different pipeline costs. **Music & Audio and Video both route to P5** — they are content-consumption surfaces with no 3D layout job.
