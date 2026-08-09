# 4. Party & Casual

<!-- Generated from `docs/LayoutGen - Build.md` Part II by `tools/generate_genre_skills.py`. Do not edit directly. -->

*Social, round-based minigames, trivia, and childhood classics like tag and hide-and-seek.*

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `space-continuous` | **SocialZone (Continuous Play Space)** | The gathering space *is* the play space; there are no discrete rounds to stage. | |
| `space-staged` | **Zone (Lobby and Isolated Stage)** | A match area fully separated from the lobby so waiting players can't see in, clip in, or interfere. | `P4` |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `social-hub` | **SocialZone (Lobby / Staging Area)** | The shared space where players gather before and between rounds, sized for the full server without bottlenecking at exits. | ● | `image` | |
| `tracker-leaderboard` | **Tracker (Leaderboard Wall)** | A prominent structural wall in the lobby sized to host the game's global leaderboard. | ● | `both` | |
| `tile-grid` | **Zone (Symmetric Tile Grid)** | A floor split into even, easily identifiable quadrants for trivia answers or tile-drop rounds. | | `image` | |
| `cover-los` | **Cover (Dense Clutter Clusters)** | Large arrays of repeating props — closets, boxes, bushes — arranged to break sightlines for hide-and-seek. | | `image` | |
| `trigger-scoring` | **TriggerZone (Round Scoring Volume)** | Detection regions that register a point, a tag, or a successful round completion. | | `layout` | |
| `spectator-zone` | **SpectatorZone (Eliminated Players Area)** | Somewhere out-of-play for eliminated players to wait and watch the rest of the round. | | `image` | |
| `spawn-protected` | **SpawnZone (Round Start Points)** | Evenly distributed start points so no player begins a round at an unfair advantage. | | `layout` | |
| `teleporter-link` | **Teleporter (Lobby-to-Stage Transport)** | The markers that move everyone from lobby into the match and back at round end. | | `both` | |
| `obstacle-maze` | **Zone (Hide-and-Seek Maze)** | A maze-like warren of rooms and corridors to hide and be hunted in. | | `image` | `P6` |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Childhood Game** | Tag, hide-and-seek; Roblox hide-and-seek games | `space-continuous` | `cover-los`, `obstacle-maze`, `social-hub` |
| **Minigame** | Fall Guys; Epic Minigames (Roblox) | `space-staged` | `teleporter-link`, `tracker-leaderboard`, `trigger-scoring`, `spectator-zone` |
| **Quiz** | [The Logo Quiz!](https://www.roblox.com/games/14826510707/The-Logo-Quiz) (Roblox) | `space-continuous` | `tile-grid`, `social-hub` |
| **Party Board** | Mario Party | `space-staged` | `tile-grid`, `trigger-scoring`, `tracker-leaderboard` |

**Genre notes**

* **Boundaries.** A chat-quiz game with no logic rooms or physical puzzle elements belongs here rather than in Puzzle — the layout job is just hosting the question and the crowd. If forward progress is gated on solving something spatial, it's Puzzle.
* **The isolated stage is conditional, not structural.** Single continuous-space party games — tag, freeze tag, a shared playground — don't need one, and forcing one costs `P4` for nothing.
* **The lobby carries the genre.** Of everything here, the gathering space is what makes a game read as "party." It's also the highest-density space in the build, so size it for peak concurrency.
* **Roblox's own subgenres here are Childhood Game, Coloring & Drawing, Minigame, and Quiz.** Three are presets above. *Coloring & Drawing* routes to **P5** only when it is genuinely a UI surface. If the prompt puts the drawing in a room — an art class, a studio, easels in a park — that room is a **`SET`** and gets built.

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
