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
* **Roblox's own subgenres here are Childhood Game, Coloring & Drawing, Minigame, and Quiz.** Three are presets above. *Coloring & Drawing* is a UI-surface game with no meaningful 3D layout and routes to **P5**.
