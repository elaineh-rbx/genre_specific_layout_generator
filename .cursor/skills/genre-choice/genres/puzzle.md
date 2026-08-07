# 5. Puzzle

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Logic challenges, rooms, escape scenarios, and mazes.*

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `puzzle-open` | **Zone (Open-Air Puzzle Space)** | Puzzles staged across a plaza, island chain, or garden with no enclosure at all. | |
| `puzzle-rooms` | **Zone (Sealed Chambers)** | Fully enclosed rooms that physically hold the player until the logic criteria are met. | `P0` if the whole game is indoors · `P3` if sealed rooms sit inside an open game |
| `puzzle-maze` | **Zone (Maze / Labyrinth)** | A maze whose solvable topology *is* the puzzle — sealed interior or open hedge maze alike. | `P6` |

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
| **Escape Room** | The Room, Portal; Roblox escape-room games | `puzzle-rooms` | `button-solve`, `facade-clue`, `collectible-nodes`, `gate-progression` |
| **Maze / Labyrinth** | Pac-Man; Roblox maze games | `puzzle-maze` | `path-loop`, `collectible-nodes` |
| **Open-Air Puzzle** | The Witness | `puzzle-open` | `gate-solve`, `trigger-solve`, `facade-clue` |
| **Word / Quiz Puzzle** | [The Logo Quiz!](https://www.roblox.com/games/14826510707/The-Logo-Quiz) (Roblox) | `puzzle-open` | `facade-clue`, `gate-solve` |

**Genre notes**

* **Reference.** [The Logo Quiz!](https://www.roblox.com/games/14826510707/The-Logo-Quiz) — players face a displayed image and type their guess into chat.
* **Boundaries.** If a game is chat-quiz-only with no logic rooms or physical puzzle elements, build it under Party & Casual instead. If the pressure is a pursuing threat rather than a locked door, it's Survival.
* **The requirement is the gate, not the enclosure.** Build's original version demanded sealed hermetic rooms, which described escape rooms specifically and excluded every open-air puzzle. A garden with a locked bridge is a puzzle.
* **Non-spatial answers shrink the layout job.** When the answer is typed into chat or a UI box there's no slot to build — the layout only has to house the clue and gate the path once a correct answer registers. Verification itself is Mechanics/UI, out of scope here.
* **Why mazes invert the pipeline.** A traversable maze with a reachable exit cannot be guaranteed by a free image — the reference failure case (`topdown_k`) produced a maze with no exit at all. So the topology is generated procedurally first and dressed afterward.
* **Roblox's own subgenres here are Escape Room, Match & Merge, and Word.** Escape Room and Word are presets above. *Match & Merge* is a grid-of-tiles UI game with no 3D layout and routes to **P5** — which resolves the Genre List's old "match-and-merge" wording, since it names a real Roblox subgenre that this genre simply routes out.
