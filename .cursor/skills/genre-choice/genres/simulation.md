# 9. Simulation

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Tycoons, incremental clickers, role sims, and progressive managers.*

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `plot-isolated` | **BuildZone (Isolated Per-Player Plots)** | Massive, independent, equally spaced plots for building out a factory or base without ever overlapping a neighbour. | |
| `plot-shared` | **BuildZone (Shared Team Plot)** | One right-sized plot shared by a team, with buttons and upgrades spread across the single structure benefiting everyone jointly. | |
| `world-shared` | **Zone (Shared Persistent World)** | No personal plot at all — one common world everybody operates in together. | |
| `world-underground` | **Zone (Surface and Underground Layers)** | A multi-level mine or facility descending beneath the surface map. | `P2 + P3` |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `social-hub` | **SocialZone (Upgrades Bazaar)** | The central storefront zone — eggs, upgrades, progression shops — that every player has to keep coming back to. | ● | `image` | |
| `path-circulation` | **Path (Progression Circulation)** | Walkable or drivable circulation chaining the hub to wherever value is actually produced. | ● | `image` | |
| `gate-progression` | **Gate (Purchase Gate)** | Physical walls blocking higher-tier zones that animate away, drop into the ground, or vanish when bought. | ● | `image` | |
| `trigger-task` | **TriggerZone (Task Station)** | A station in a repeatable job loop — pickup, delivery, patient bed, planting plot. | | `both` | |
| `resource-shared` | **Zone (Shared Resource Field)** | A large open extraction area on a regen or collapse timer that the whole server draws from — explicitly not part of anyone's personal plot. | | `image` | |
| `path-road-vehicle` | **Path (Hauling Routes)** | Vehicle-width roads between extraction ground and processing structures. | | `image` | |
| `collectible-nodes` | **Collectible (Extractable Resources)** | The ore, timber, or crops the loop is built on. | | `layout` | |
| `hazard-kill` | **HazardZone (Environmental Event)** | Dynamic hazards layered over the shared space — a rising-lava evacuation, a mine collapse. | | `image` | |
| `physics-rig` | **Destructible (Physics Contraption)** | Ramps, ragdoll props, and breakable assemblies whose reactions are the entertainment. | | `image` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Tycoon** | [2 Player Secret Hideout Tycoon](https://www.roblox.com/games/136258770/2-Player-Secret-Hideout-Tycoon) (Roblox) | `plot-shared` | `gate-progression`, `social-hub`, `path-circulation` |
| **Sandbox** | Minecraft; Build a Boat for Treasure (Roblox) | `plot-isolated` | `collectible-nodes`, `social-hub` |
| **Vehicle Sim** | [Mega Miners](https://www.roblox.com/games/17541179/Mega-Miners) (Roblox); Euro Truck Simulator | `world-shared` | `path-road-vehicle`, `resource-shared` |
| **Incremental Simulator** | Roblox "simulator" games | `world-shared` | `social-hub`, `gate-progression`, `path-circulation` |
| **Physics Sim** | Roblox cart-ride and ragdoll games | `world-shared` | `physics-rig`, `hazard-kill`, `path-circulation` |
| **Role Sim** | Emergency Response: Liberty County (Roblox) | `world-shared` | `trigger-task`, `path-circulation`, `path-road-vehicle` |
| **Mining & Extraction** | [Ultimate Mining Tycoon](https://www.roblox.com/games/18680867089/Ultimate-Mining-Tycoon) (Roblox) | `world-underground` | `resource-shared`, `collectible-nodes`, `path-road-vehicle` |

**Genre notes**

* **References.** [2 Player Secret Hideout Tycoon](https://www.roblox.com/games/136258770/2-Player-Secret-Hideout-Tycoon) for shared plots. [Ultimate Mining Tycoon](https://www.roblox.com/games/18680867089/Ultimate-Mining-Tycoon) for the extraction hybrid. [Mega Miners](https://www.roblox.com/games/17541179/Mega-Miners) for vehicle sim.
* **Boundaries.** Role Sim vs Roleplay & Avatar Sim: Role Sim is a defined, repeatable task loop; Roleplay is open-ended social storytelling. Vehicle Sim vs Racing: **there is no lap or finish condition in a vehicle sim** — players operate machinery cooperatively in a persistent world.
* **The isolated plot is not universal, despite being the genre's mental default.** Role Sim and Vehicle Sim have no plot at all; co-op tycoons share one; the extraction hybrid pairs a personal plot with a shared field. Check which before laying out a grid.
* **The shared resource field is not a plot.** In the extraction hybrid it's common ground the whole server mines and hauls from. Building it as somebody's plot breaks the loop.
* **Role sims are often cooperative.** A shared farm several players work together is more typical than per-player isolation — pilot, doctor, trucker, and medieval farmer sims all tend this way.
* **Roblox's own subgenres here are Idle, Incremental Simulator, Physics Sim, Sandbox, Tycoon, and Vehicle Sim** — the widest subgenre list of any genre, which matches how much this label covers. Five are presets above. ***Idle* routes to P5**, since Roblox defines it as games with little to no player input, and that has no layout job at all.
* **Physics Sim needed an option that did not exist.** Ramps, ragdoll props, and breakable assemblies are the entire point of that subgenre, so `physics-rig` was added. It reuses `Destructible`, which Part I §4 already governs through the debris rule.
