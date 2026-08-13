# Shape Catalog

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

Every shape in the system, and the **route lives here and only here**. The wording below is what a genre inherits when it states none of its own.

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `space-bounded` | **Zone (Bounded Play Space)** | One clearly bounded, single-level space that the whole activity happens inside. |  |
| `arena-tiered` | **CombatZone (Terraced Arena)** | Stepped or terraced relief — strong elevation, nothing overhanging. | `P0 + tiered` |
| `arena-stacked` | **CombatZone (Multi-Level Arena)** | Catwalks, balconies, or floors that overhang the arena below. | `P2` |
| `rooms-sequence` | **Zone (Room Sequence)** | A run of discrete enclosed rooms joined by corridors and worked through in order, rather than one open space. |  |
| `world-open` | **Open World** | One contiguous explorable map with no instanced areas, traversed in whatever order the player likes. |  |
| `route-guided` | **Path (Guided Route)** | A single directed route through one continuous space, sequencing the player past its key moments rather than letting them wander. |  |
| `world-chaptered` | **Chaptered Journey** | Story chapters as genuinely separate maps that don't co-exist on one surface. | `P4` |
| `course-flat` | **Path (Flat Course)** | A course laid out across the ground, progressing horizontally. | `P6` |
| `course-terraced` | **Path (Ascending Terraces)** | A course climbing a hillside or staircase — strong vertical gain, nothing overhanging. | `P6 + tiered` |
| `course-tower` | **Path (Tower / Spiral Ascent)** | A course wrapping or stacking so platforms sit directly above each other. | `P6 + P2` |
| `space-staged` | **Zone (Lobby and Isolated Stage)** | A match area fully separated from the lobby so waiting players can't see in, clip in, or interfere. | `P4` |
| `puzzle-open` | **Zone (Open-Air Puzzle Space)** | Puzzles staged across a plaza, island chain, or garden with no enclosure at all. |  |
| `puzzle-maze` | **Zone (Maze / Labyrinth)** | A maze whose solvable topology *is* the puzzle — sealed interior or open hedge maze alike. | `P6` |
| `world-hub-dungeon` | **Hub and Dungeons** | A safe hub feeding separate instanced combat areas entered from the overworld. | `P4 + P3` |
| `world-open-biomes` | **Open World with Biomes** | Regions whose difficulty and reward scale with distance — tougher wildlife and scarcer resources further out. | `P4` |
| `settlement-static` | **Zone (Static Settlement)** | A fixed, pre-built town with no personal property at all; personalization happens through the avatar, never property. |  |
| `settlement-claimable` | **Zone (Claimable Houses)** | Pre-built houses scattered through the town that players claim rather than construct, customizing paint or swapping a preset interior. | `P3` |
| `settlement-buildable` | **BuildZone (Personalized Plots)** | Uniform, flat, square lot footprints on a strict grid where players cleanly spawn and build their own houses. | `P3` |
| `wilderness-open` | **Zone (Open Natural World)** | No settlement at all — a natural biome of dens, water, and terrain features that players inhabit as creatures. |  |
| `stage-runway` | **Zone (Stage and Dressing Rooms)** | A judging runway or catwalk fed by preparation booths, with the audience arranged around it. |  |
| `lane-network` | **Lane (Lane Network)** | Parallel routes, classically three, channelling team traffic into predictable engagement fronts. |  |
| `open-battlefield` | **Zone (Open Battlefield)** | One large contiguous map with dispersed points of interest instead of defined lanes. |  |
| `range-directed` | **Lane (Directed Practice Range)** | A firing line facing downrange into a target field, with no opposing team and no route through — everything the player shoots at is in front of them and the space behind the line is safe. |  |
| `plot-isolated` | **BuildZone (Isolated Per-Player Plots)** | Massive, independent, equally spaced plots for building out a factory or base without ever overlapping a neighbour. |  |
| `plot-shared` | **BuildZone (Shared Team Plot)** | One right-sized plot shared by a team, with buttons and upgrades spread across the single structure benefiting everyone jointly. |  |
| `world-underground` | **Zone (Surface and Underground Layers)** | A multi-level mine or facility descending beneath the surface map. | `P2 + P3` |
| `tier-ladder` | **Zone (Tiered Training Grounds)** | A run of training areas of rising tier laid out in a readable line or spiral, each walled off from the next until a stat crosses a threshold, so the number going up is visible as ground gained. |  |
| `lane-actor-track` | **Path (Enemy Lane)** | A single continuous, unchanging lane winding from spawn to the core that enemy waves are hard-coded to follow — no dead-end branches, no ambiguous self-crossings. | `P6` |
| `terrain-open` | **Zone (Open Contested Terrain)** | No lane at all — units path dynamically across open ground between symmetrically distributed bases. |  |
| `board-grid` | **Zone (Board Grid)** | A tabletop-scale grid or board that players act on rather than move through. | `SET` |
| `warren-looping` | **Path (Looping Warren)** | Architecture built on interconnected circles with **zero dead ends**, so a fleeing player is never artificially cornered by pathfinding AI. | `P6` |
| `world-biomes` | **Zone (Biome World)** | Regions whose threat level scales with distance or depth. | `P4` |
| `route-point-to-point` | **Path (Point to Point)** | A course that starts in one place and ends in another — downhill, drag, sprint, single-swimmer. | `P6` |
| `route-circuit` | **Path (Lap Circuit)** | A closed loop run a set number of times. | `P6` |
| `route-multitier` | **Path (Multi-Tier Circuit)** | A circuit whose sections cross above or below other sections of the same course. | `P6 + P2` |
| `lane-snap` | **Lane (Fixed Lane Snap)** | Rigid parallel lanes, typically three, each the avatar bounding box plus a 2-stud safety margin so lateral dashes snap instantly without clipping geometry. | `P6` |
| `lane-free` | **Lane (Free Lateral Steering)** | Continuous lateral movement across a corridor instead of discrete lane slots. | `P6` |
| `hub-portals` | **Zone (Portal Hub)** | A layout whose purpose is to send visitors onward to separate experiences. | `P4` |
| `venue-stage` | **Zone (Stage and Audience)** | A raised performance stage with the audience floor spread in front of it, every sightline in the build oriented toward the stage rather than through the space. |  |
| `interior-single` | **Zone (Single Interior)** | One enclosed building, room or venue that is the entire map — the player never steps outside, so there is no exterior to generate and no transition to link. |  |
| `interior-endless` | **Zone (Endless Interior)** | An interior of corridors and rooms that continues without a boundary — dead ends, repeating architecture, and no exit to reach. | `P6` |
| `volume-open-air` | **Zone (Open Airspace)** | Open air is the play space, with discrete surfaces to touch down on — rooftops, platforms, landing pads — instead of one continuous ground plane. | `CHECK` |
| `vehicle-deck` | **Zone (Vehicle Deck)** | The walkable surface is a vehicle — a ship's deck, a train, an aircraft cabin — and the world moves past it rather than the player moving through the world. |  |
| `traversal-city` | **Zone (Traversal City)** | A city built to be crossed over rather than fought in: rooftops, ledges and gaps sized for a moving player, with the streets below as the fallback route. | `P2` |
| `set-display` | **Zone (Display Set)** | The build is a set arranged around one subject — a vehicle, a machine, a diorama city — framed to be looked at and operated from outside rather than walked through. | `SET` |

**45 shapes, and the catalogue is the whole answer.**

**`set-display` is the one shape whose route the shape does not decide.** Stage B already asks *does anyone walk through it?* and appends `SET` on a no, so this row does not introduce a second rule — it gives that answer somewhere to live on the shape axis. `board-grid` is Strategy's special case of it; this is the general one. Reach for it when the subject *is* the deliverable and the surroundings are its setting: a modelled vehicle, a pinball machine, a city looked down on and zoomed into. If the player walks anywhere in the build, this is the wrong shape.

#### **When nothing in the catalogue fits, describe the shape instead**

A finite catalogue cannot cover the space of real prompts, and pretending otherwise forces the nearest wrong answer. The **described shape** is the escape hatch: no ID, the five routing axes answered directly, and **the user's own words as the description**.

It costs nothing new. The axes are the same five `no-genre.md` asks, so the route is derived exactly as it is there — and because every space has an answer on all five, a described shape is always routable. The catalogue supplies names; the axes supply routes; this uses the second without the first.

The axes and their routes are **The Five Routing Axes** above; answer them there and route off the deviations. Only the non-default value costs anything, so a described shape that answers every axis at its default is a plain `P0`.

**The bar to use it is high, and it is a specific bar: you must be able to say which catalogue shapes you rejected and why.** Not "nothing fit" — *"`space-bounded` assumes one level and this is a stack of floors the player moves between; `rooms-sequence` assumes an order and these connect freely."* If that sentence cannot be written, a catalogue shape fits and should be used. The reason is not bureaucratic: that sentence is what makes a described shape reviewable, and a bundle described twice is how the catalogue earns its next row.

**Every described shape is emitted with its axis bundle**, and the bundle is the thing to watch. Two prompts independently describing the same bundle *and* the same kind of space is how a described shape earns a name; that convergence is how the shapes above were coined. A described shape is therefore not a failure to be minimised; it is the intake path for the catalogue's next entry.

**What it does not do is escape a genre-wide route.** Obby, Racing and Infinite Runner are `P6` whatever shape is chosen, described or named, because structural validity is the game rather than a property of the space.

#### **The route in a shape row is sometimes a default**

A shape row makes two claims at once: what the space is *like*, and how the pipeline has to *build* it. Usually they agree. Occasionally a prompt matches the first and contradicts the second, and because the row is a single pick, the contradicted half comes along anyway.

The clearest case: Survival's `world-biomes` is the only shape in the genre expressing danger that scales with distance. Its route is `P4` — *separate maps*. A prompt asking for exactly that on **one big map** has no way to take the description without the build instruction, and the map gets split.

**Which routes may be overridden depends on why the shape carries them.** Three kinds, and only the last is negotiable:

| Kind | Shapes | Overridable |
| :---- | :---- | :---- |
| **A structural law.** Validity *is* the game — a maze must be solvable, a tower-defense lane must be one continuous route, a warren must have no dead ends. An image cannot guarantee any of them. | Every `P6` shape, and the genre-wide `P6` on Obby, Racing and Infinite Runner | **No.** Dropping it produces a broken game, not a cheaper one. |
| **A consequence of a feature that is actually present.** Claimable houses have interiors, so `P3`. Stacked surfaces overhang, so `P2`. | `settlement-claimable`, `settlement-buildable`, `arena-stacked`, `world-underground`, `route-multitier` | **Only if the feature is absent.** A claimable house nobody enters is not `P3`. Say so when you drop it. |
| **An estimate about scale.** `P4` claims several zones cannot share one surface. That is a judgement about size, and the prompt frequently settles it. | `world-biomes`, `world-open-biomes`, `world-chaptered`, `space-staged`, `world-hub-dungeon`, `hub-portals` | **Yes.** When the prompt says one continuous map, keep the shape and route `P0`. |

**Keep the shape, change the route** — the shape was never wrong about the space. Record the override and what in the prompt justified it.

**This is a rule for a rare case.** Nearly every prompt that describes one continuous map is already routed correctly without it, so it must never become a reason to second-guess a route the prompt did not mention — **silence is not a contradiction.** When the prompt says nothing, take the default.
