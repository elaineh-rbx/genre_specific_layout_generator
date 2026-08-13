# 9. Simulation

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Tycoons, incremental clickers, role sims, and progressive managers.*

**Shape — pick one.**

**Typical shapes.** `plot-isolated` · `plot-shared` · `world-open` *(default)* · `world-underground` · `tier-ladder` · `vehicle-deck`

This genre words these its own way:

| ID | Shape | What it is |
| :---- | :---- | :---- |
| `world-open` | **Zone (Shared Persistent World)** | No personal plot at all — one common world everybody operates in together. |


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
| `station-training` | **TriggerZone (Stat Training Station)** | The repeatable thing that raises the number — a treadmill, a weight rack, a punching bag, a click pad, a short run of speed boosters. Dense enough that a player is always standing on one. | ● | `both` | |
| `trigger-rebirth` | **TriggerZone (Rebirth Pad)** | A marked pad that trades all current progress for a permanent multiplier, sited at the far end of the last tier a player can reach. | | `layout` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Tycoon** | [2 Player Secret Hideout Tycoon](https://www.roblox.com/games/136258770/2-Player-Secret-Hideout-Tycoon) (Roblox) | `plot-shared` | `gate-progression`, `social-hub`, `path-circulation` |
| **Stat Grinder** | Roblox "+1 speed", strength and speed-run simulators | `tier-ladder` | `station-training`, `gate-progression`, `trigger-rebirth`, `social-hub` |
| **Sandbox** | Minecraft; Build a Boat for Treasure (Roblox) | `plot-isolated` | `collectible-nodes`, `social-hub` |
| **Vehicle Sim** | [Mega Miners](https://www.roblox.com/games/17541179/Mega-Miners) (Roblox); Euro Truck Simulator | `world-open` | `path-road-vehicle`, `resource-shared` |
| **Incremental Simulator** | Roblox "simulator" games | `world-open` | `social-hub`, `gate-progression`, `path-circulation` |
| **Physics Sim** | Roblox cart-ride and ragdoll games | `world-open` | `physics-rig`, `hazard-kill`, `path-circulation` |
| **Role Sim** | Emergency Response: Liberty County (Roblox) | `world-open` | `trigger-task`, `path-circulation`, `path-road-vehicle` |
| **Mining & Extraction** | [Ultimate Mining Tycoon](https://www.roblox.com/games/18680867089/Ultimate-Mining-Tycoon) (Roblox) | `world-underground` | `resource-shared`, `collectible-nodes`, `path-road-vehicle` |
| **Aircraft Operation** | Flight and rescue sims; Roblox helicopter and airline places | `volume-open-air` | `trigger-task`, `social-hub`, `gate-progression` |
| **Vessel Operation** | Roblox cruise-ship, train and boat places | `vehicle-deck` | `social-hub`, `trigger-task`, `path-circulation` |

**Genre notes**

* **References.** [2 Player Secret Hideout Tycoon](https://www.roblox.com/games/136258770/2-Player-Secret-Hideout-Tycoon) for shared plots. [Ultimate Mining Tycoon](https://www.roblox.com/games/18680867089/Ultimate-Mining-Tycoon) for the extraction hybrid. [Mega Miners](https://www.roblox.com/games/17541179/Mega-Miners) for vehicle sim.
* **Boundaries.** Role Sim vs Roleplay & Avatar Sim: Role Sim is a defined, repeatable task loop; Roleplay is open-ended social storytelling. Vehicle Sim vs Racing: **there is no lap or finish condition in a vehicle sim** — players operate machinery cooperatively in a persistent world.
* **The isolated plot is not universal, despite being the genre's mental default.** Role Sim and Vehicle Sim have no plot at all; co-op tycoons share one; the extraction hybrid pairs a personal plot with a shared field. Check which before laying out a grid.
* **The shared resource field is not a plot.** In the extraction hybrid it's common ground the whole server mines and hauls from. Building it as somebody's plot breaks the loop.
* **Role sims are often cooperative.** A shared farm several players work together is more typical than per-player isolation — pilot, doctor, trucker, and medieval farmer sims all tend this way.
* **The "+1 speed" family lives here, and it is the one most often filed wrong.** Walk or click to raise a stat, break through a barrier the stat unlocks, spend the winnings, rebirth for a multiplier — the number going up *is* the game. It is a large, well-known Roblox family whose members scatter across four genres and five presets, because each instance looks locally like whatever it borrowed: a parkour course reads as Obby, a keyboard-escape puzzle reads as Puzzle, a racing lane reads as Racing. **What they share is the layout, not the activity** — tiers in a line, a wall between each pair, a training station you stand on, and a rebirth pad at the end. That is `tier-ladder` plus **Stat Grinder**, and it is P0.
* **`tier-ladder` is not an obby, even when you jump on it.** An obby's difficulty is in the geometry and the route has to be physics-legal, which is why Obby & Platformer routes P6 whatever shape it takes. Here the barrier is a number, the geometry is just ground, and nothing has to be validated — so a "+1 speed" game that also has a parkour section is Simulation first, and it stays P0. Naming Obby second is right; letting it lead is what imported a P6 these games never needed.
* **`gate-progression` covers both kinds of wall.** A tycoon's gate opens when you pay; a stat ladder's opens when you are fast enough. Same geometry, same ID, different sentence — bend the wording, do not add a row.
* **Roblox's own subgenres here are Idle, Incremental Simulator, Physics Sim, Sandbox, Tycoon, and Vehicle Sim** — the widest subgenre list of any genre, which matches how much this label covers. Five are presets above. ***Idle* is a `SET`, not a P5.** Roblox defines it as games with little to no player input, which is easy to read as no layout job — but an idle game still has a space you watch, and most Roblox ones are a tycoon you happen to leave running. Build the set; see *Reading the Pipeline column* in Build.md. Only route P5 when there is genuinely no room, just a screen of numbers.
* **Physics Sim is `physics-rig`.** Ramps, ragdoll props and breakable assemblies are the entire point of that subgenre. It reuses `Destructible`, which Part I §4 already governs through the debris rule.

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
