# 5. Puzzle

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Logic challenges, rooms, escape scenarios, and mazes.*

**Shape — pick one.**

**Typical shapes.** `puzzle-open` *(default)* · `rooms-sequence` · `puzzle-maze` · `interior-single`

This genre words these its own way:

| ID | Shape | What it is |
| :---- | :---- | :---- |
| `rooms-sequence` | **Zone (Sealed Chambers)** | Fully enclosed rooms that physically hold the player until the logic criteria are met. |


**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `gate-solve` | **Gate (Solve Gate)** | Forward progress blocked until something is solved. The gating is the requirement — the space around it can be a sealed room, a plaza, an island, or a garden. | ● | `image` | |
| `trigger-solve` | **TriggerZone (Solve Input Slot)** | A physical receptacle that accepts a key item — a shaped indentation, a pedestal, a socket in a wall or table. | ● | `both` | |
| `button-solve` | **Button (Solve Input Press)** | Levers, keypads, pressure plates, and other pressable puzzle inputs. | ● | `both` | |
| `facade-clue` | **Barrier (Clue Facade)** | A feature wall placed directly in the player's natural camera path, hosting a riddle, pattern, or hint. | ● | `image` | |
| `collectible-nodes` | **Collectible (Key Items)** | Keys, fragments, and carryable pieces that the solve inputs are waiting for. | | `layout` | |
| `path-loop` | **Path (Loop-Back Corridors)** | Hallways that circle back to the central chamber, so a wrong turn never means long frustrating backtracking. | | `image` | |
| `gate-progression` | **Gate (Sequenced Unlock)** | A barrier that opens only once an earlier puzzle in the chain is complete. | | `image` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Escape Room** | The Room, Portal; Roblox escape-room games | `rooms-sequence` | `button-solve`, `facade-clue`, `collectible-nodes`, `gate-progression` |
| **Maze / Labyrinth** | Pac-Man; Roblox maze games | `puzzle-maze` | `path-loop`, `collectible-nodes` |
| **Open-Air Puzzle** | The Witness | `puzzle-open` | `gate-solve`, `trigger-solve`, `facade-clue` |
| **Word / Quiz Puzzle** | [The Logo Quiz!](https://www.roblox.com/games/14826510707/The-Logo-Quiz) (Roblox) | `puzzle-open` | `facade-clue`, `gate-solve` |

**Genre notes**

* **Reference.** [The Logo Quiz!](https://www.roblox.com/games/14826510707/The-Logo-Quiz) — players face a displayed image and type their guess into chat.
* **Boundaries.** If a game is chat-quiz-only with no logic rooms or physical puzzle elements, build it under Party & Casual instead. If the pressure is a pursuing threat rather than a locked door, it's Survival.
* **The requirement is the gate, not the enclosure.** Sealed hermetic rooms describe escape rooms specifically and exclude every open-air puzzle. A garden with a locked bridge is a puzzle.
* **Non-spatial answers shrink the layout job.** When the answer is typed into chat or a UI box there's no slot to build — the layout only has to house the clue and gate the path once a correct answer registers. Verification itself is Mechanics/UI, out of scope here.
* **Why mazes invert the pipeline.** A traversable maze with a reachable exit cannot be guaranteed by a free image — the reference failure case (`topdown_k`) produced a maze with no exit at all. So the topology is generated procedurally first and dressed afterward.
* **Roblox's own subgenres here are Escape Room, Match & Merge, and Word.** All three are presets above — *Word / Quiz Puzzle* covers the third. *Match & Merge* routes to **P5** when the grid is a flat UI overlay, and is a **`SET`** when it is physical: a board on a table, tiles the camera looks down on, a merge yard with the pieces built as objects.
* **Check the Word / Quiz preset before falling through to another genre.** It is easy to overlook, and spelling games get filed under Party & Casual instead. The preset name comes from Roblox's taxonomy, so it will not echo the user's words — "type the word that appears," "guess the answer before the timer," and trivia with a physical set all land here.

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
