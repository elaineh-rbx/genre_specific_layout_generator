# **Game Building Rules**

This document defines the rules for building Roblox games in 3D. It is organized into two parts:

* **Part I — Environment Rules:** Standard rules that always apply when building a Roblox game in 3D.  
* **Part II — Genre Layout Options:** A menu of layout features per genre. **Nothing in Part II is mandatory.** The user prompts, we infer a genre, we offer options, they pick, and the picks are injected into image generation. If a user picks nothing, we inject nothing and they get a simple map — that is a legitimate outcome, not a failure.

This document covers **layout and scene construction only**. Camera behavior, game mechanics, and visual theme are defined in separate documents; where those domains inform a rule here, they appear as rationale or a brief hint (not as rules).

All spatial concepts use the shared vocabulary defined below.

---

# **Shared Vocabulary**

To keep rules consistent — and machine-readable for future tooling — all spatial concepts use a small set of typed terms. Flavor names are preserved in parentheses, e.g. `HazardZone (Aggro Bowl)`.

**Reserved engine words** — never used as design nouns, only in their literal Roblox meaning: `Anchored`, `Part`, `Model`, `Transparency`, `CanCollide`, `CanTouch`, `CollisionGroup`.

**Functional hooks.** Some primitives are pure geometry; others are *functional* — objects and regions meant to be wired to gameplay behavior (scoring, triggers, spawns, pickups, teleports, and so on) by a separate functional game framework. These rules define each primitive's layout role and name; the mechanic wiring itself is out of scope for this document. The **Wiring** column indicates how a primitive becomes functional:

* **mechanic** — wired to a gameplay mechanic by the functional framework.  
* **layout-only** — pure geometry/composition; no wiring.  
* **engine** — handled by a Roblox built-in (e.g. `SpawnLocation`).  
* **composite** — no single mechanic; built from other objects \+ game logic.

### **Region types (bounded 3D areas)**

| Term | Meaning | Wiring |
| :---- | :---- | :---- |
| `Zone` | generic bounded area — use a specific type below when one fits | layout-only |
| `SpawnZone` | player starting area | engine (`SpawnLocation`) |
| `SafeZone` | hazard-free area isolated from combat/AI | layout-only |
| `CombatZone` | active combat/gameplay area | layout-only |
| `BuildZone` (alias `Plot`) | per-player construction area | layout-only |
| `SocialZone` | shared gathering hub | layout-only |
| `SpectatorZone` | non-play area for inactive/eliminated players | layout-only |
| `WinnerZone` | end-of-course reward area | mechanic |
| `BoundaryZone` | map-limit region | layout-only |
| `TriggerZone` | entry/exit detection region (scoring, laps, plates, finish, despawn) | mechanic |
| `CaptureZone` | deliver-/hold-to-score area (CTF, territory) | mechanic |
| `ControlZone` | capacity-limited player-occupancy area with indicator (KotH hill) | mechanic |
| `HazardZone` | damaging region (lava, ring-out, kill volume) | mechanic |

> ⚠️ `ControlZone` is the **specific** capacity/indicator occupancy area (KotH hill). Plain regions that only need entry detection are `TriggerZone`s — do not conflate the two.

> ⚠️ `Zone` is the fallback. If a region is a spawn, a hub, a hazard, or a detection volume, use that type instead — `Zone` is for bounded areas with no more specific role (a maze segment, a district, a sealed chamber).

### **Markers & objects (single placed items)**

| Term | Meaning | Wiring |
| :---- | :---- | :---- |
| `SpawnPoint` | single player start marker | engine (`SpawnLocation`) |
| `StartPoint` | play-origin (ball reset, serve box, race start) | layout-only \+ game logic |
| `Checkpoint` | touch-to-activate respawn point | mechanic |
| `Teleporter` | point-to-point teleport (was `TravelPoint`) | mechanic |
| `Spawner` | NPC/entity/mob emitter (was NPC/mob `SpawnZone`) | mechanic |
| `Collectible` | coin, flag, key, gem, quest item, resource node | mechanic |
| `PowerUp` | timed pickup (speed, jump, shield, etc.) | mechanic |
| `Button` | clickable interaction (door, lever, puzzle press) | mechanic |
| `Tracker` | physical progress host (quest board, objective pillar, health-pool base) | mechanic |
| `Marker` | non-functional visual reference (distance line, pacing flag, lane number) | layout-only |
| `Landmark` | large orientation focal object | layout-only |

> ⚠️ `Tracker` covers the tower-defense core base and the leaderboard wall. There is no `ObjectivePoint` type — that name was used in earlier drafts and is retired.

### **Paths & structure**

| Term | Meaning | Wiring |
| :---- | :---- | :---- |
| `Path` | a defined movement route | layout-only |
| `Lane` | a parallel movement corridor | layout-only |
| `Choke` | a bottleneck | layout-only |
| `Gate` | a blockable transition | composite (`Button`/`TriggerZone` \+ moving geometry) |
| `Barrier` | blocks movement or sight (map limit, wall) | layout-only |
| `Cover` | waist- or full-body line-of-sight cover (combat, stealth, or hiding) | layout-only |
| `Destructible` | multi-part structure authored to break apart | layout-only \+ physics (see Part I §4) |
| `Chunk` | modular procedural segment (Infinite Runner) | layout-only (procgen) |

> ⚠️ `Barrier` blocks movement or sight. A painted lane line does neither — that is a `Lane` boundary. A guardrail is both.

---

# **Layout Attributes (Sub-Genre Tags)**

Genre answers *what kind of game* this is; **Layout Attributes** answer *what shape the space takes*. They are **not genre-specific** — every 3D game has a value on each axis, even if it's the trivial default.

Each axis has a **default** value (the simplest, most common shape) and one or more **deviations**. Tagging a game along these axes is what lets tooling reason about it consistently. *(How each deviation affects generation — and which are supported today — is defined in `LayoutGen - Pipeline.md`; this section only defines the tags, not the buildability.)*

| Attribute | Default | Deviations | Meaning |
| :---- | :---- | :---- | :---- |
| **Enclosure** | `exterior` | `interior-only` · `transition` (outside↔inside) | Whether play happens outdoors, entirely inside one enclosed space, or moves between the two. An **interior-only** game is still a single space (a roofless room/cave/dungeon); a **transition** game moves between an outside and an inside. |
| **Verticality** | `single-surface` | `tiered` · `stacked` | The real question is **does anything overhang anything else?** `single-surface` = flat/rolling heightfield. `tiered` = stepped/terraced relief (amphitheater, hillside town, set-back pyramid, stadium seating) — strong elevation but **nothing overhangs**, so it's still one surface per (x,y); supported, but **flag it** so the elevation is captured and not built flat. `stacked` = surfaces **overhang / share the same (x,y)** (floors, towers, spiral climbs, bridges over paths, tunnels) — true occlusion. |
| **Zone count** | `single` | `multi-zone` | Whether the experience is one contiguous map or **several distinct maps/levels** (level select, dungeons, biomes, lobby + stage, hub portals). |
| **Structure-criticality** | `dressed` | `must-be-valid` | Whether the layout is free-form set dressing, or its **exact topology is the game** and must be provably valid (solvable maze, connected race circuit, single tower-defense lane, physics-legal obby path). |
| **Play-space dimensionality** | `grounded-surface` | `volumetric` | Whether players move on a **ground surface**, or through a **3D volume** (flight, swimming, space). Volumetric play is usually still fine: if the whole area is captured over a representable surface (fly over terrain, swim above a seafloor), the surface generates normally and the volume is just a **play-height envelope** above it. It only becomes a real problem when the volume **self-occludes** (asteroid fields, layered floating islands, 3D cave networks) — which is an occlusion/verticality case. Treat this axis as a **check**, not an automatic block. |

Worked examples:

* **Flat difficulty-chart obby** = Obby, all defaults (no tags).
* **Tower / spiral obby** = Obby + `[Verticality: stacked]` (surfaces overhang).
* **Amphitheater / terraced arena** = its genre + `[Verticality: tiered]` (relief, no overhang — an orange flag, not a break).
* **Escape room** = Puzzle + `[Enclosure: interior-only]`.
* **Brookhaven (enter houses)** = Roleplay & Avatar Sim + `[Enclosure: transition]`.
* **Maze / race circuit / tower-defense** = their genre + `[Structure-criticality: must-be-valid]`.
* **Flight sim over terrain / underwater over a seafloor** = its genre + `[Play-space: volumetric]` — fine as long as the whole area fits one image; the volume becomes a play-height envelope.
* **Mining tycoon (surface → underground layers)** = Simulation + `[Verticality: stacked] + [Enclosure: transition]`.

**Relationship to Part II.** These axes are the router's conceptual model. The genre options in Part II skip straight to the *result* — each option carries the pipeline modifier it forces (`P2`, `P3`, `P4`, `P6`) rather than the attribute behind it, so the cost of a pick is visible at the moment of picking. The mapping from axis to modifier lives in `LayoutGen - Pipeline.md`, Part IV.

---

# **Part I — Environment Rules**

## **📐 1\. Avatar Physics & Engine Metrics (The Mathematical Baseline)**

These are the core engine settings that govern character movement. All modular pieces and obstacle spaces are built as a direct mathematical response to these settings.

* **Workspace.Gravity:** **196.2** (Roblox Default). Changing this requires a complete overhaul of vertical boundaries, step heights, and ceiling clearance.  
* **Humanoid.WalkSpeed:** **16 studs per second** (Roblox Default). This dictates the standard travel pacing, map scales, and hallway lengths.  
* **Humanoid.JumpHeight:** **7.2 studs** — the modern default, since `UseJumpPower` is `false` by default. (Legacy alternative: if `UseJumpPower = true`, then `Humanoid.JumpPower = 50` yields a physical jump height of approximately 6.3 studs. Standardize on JumpHeight unless a game explicitly opts into JumpPower.)  
* **Horizontal Jump Limit:** At default speed and power, the absolute maximum horizontal gap an avatar can clear is **11 to 12 studs**.  
* **Vertical Step Limit:** Due to default `HipHeight` settings and leg collision exemption, avatars will automatically glide over obstacles up to **2.3 studs** high. Any obstacle **2.4 studs or higher** collides directly with the `HumanoidRootPart` and acts as a solid wall, forcing a manual jump.  
* **Humanoid.MaxSlopeAngle:** **89°** (Roblox Default, set via `StarterPlayer.CharacterMaxSlopeAngle`) — the steepest slope an avatar can walk up without sliding back down. Since the default allows climbing almost any grade, every ramp, hill, and sloped surface in the level is a potential climb path unless this baseline is deliberately respected or overridden (see Section 6 for its map-boundary application).

## **🏛️ 2\. Architectural Dimensions & Scaling (Modern City Standard)**

These specific spatial constraints are optimized for modern urban environments, balancing avatar navigation with proper third-person camera clearance.

* **Doorway Width:** **4 studs wide minimum**. (Provides the minimum exact clearance needed for a 4-stud wide classic avatar's bounding box). **This is also the floor for any opening a player must physically enter** — crawlspaces, lockers, vents. A 3-stud opening cannot be entered at all; anything tighter requires a scripted hide that repositions and conceals the character, which is a Mechanics concern.  
* **Doorway Height:** **7.5 studs tall minimum**. (Ensures safe clearance for tall Rthro avatars and vertical accessories/hats).  
* **Ceiling Height:** **13.5 studs minimum clear height**. (Crucial threshold to prevent the third-person camera from violently zooming into the player's skull when indoors).  
* **Ceiling & Floor Thickness:** **1 stud tall minimum**. Floor and ceiling slabs sit **outside** the 15-stud wall module rather than inside it, so the wall's full 15 studs is clear interior height and **floor-to-floor pitch is 17 studs**. *(Fitting both slabs inside a 15-stud wall would leave only 13 studs clear — below the 13.5 minimum above.)*  
* **Stair Step Height:** **0.75 studs** (Ideal) to **1.0 stud** (Maximum). (Stays well within the avatar's automatic step-over range described in Section 1, allowing smooth vertical scaling without forcing players to jump).

## **🧱 3\. Geometry & Grid Standards (Modular Asset Rules)**

Clean grid alignment in Roblox Studio eliminates ugly visual seams, texture bugs, and manual alignment errors.

* **Anti-Flicker Rule (Z-Fighting):** Never allow two faces to occupy the exact same 3D coordinate. Snap strictly to grid increments (**1, 0.5, or 0.25 studs**), or offset overlapping faces by a microscopic variable (e.g., 0.001 studs).  
* **The Clean Horizon Floor:** A perfectly level, seamless geometric base layer aligned strictly to the grid beneath any uneven custom terrain to prevent avatar physics from clipping through the world.  
* **Modular Building Standard:** Structural assets (walls, floors, pillars) must be built in fixed, predictable dimensions to snap together seamlessly like LEGO bricks.  
  * *Small Walls & Doors:* **7.5 studs wide x 15 studs tall**.  
  * *Medium Walls:* **15 studs wide x 15 studs tall**.  
  * *Extended Assets:* Must be constructed in strict multiples of these baselines.  
* **The Origin Pivot Rule:** All modular structural assets must have their pivot points set to the **bottom-front-left geometry corner** for exact, predictable grid snapping **(not bounding box corner)**.

## **⚙️ 4\. Physics & Collision Optimization**

Minimizing active physics calculations prevents server lag and ensures crisp player movement.

* **The Small Detail Rule:** Set CanCollide \= false for any prop smaller than a player's leg (pebbles, trash debris, decorative fences, door handles). Players should pass through them cleanly so movement never feels bumpy or jittery.  
* **The Mesh Collision Rule:** Set CollisionFidelity to **Box** or **Hull** for complex 3D meshes. Strictly avoid using "Precise" unless the exact, intricate geometry is explicitly required for gameplay.  
* **The Touch Rule:** Set CanTouch \= false on all environmental parts that do not possess a script checking for touch interactions (like kill-bricks or checkpoints). This stops the engine from wasting CPU power calculating touch math frames. **Exception:** gameplay detection regions (`TriggerZone`s — scoring, lap, hazard, despawn volumes) are exempt from this rule. Even so, prefer spatial queries (`Workspace:GetPartBoundsInBox` or a Zone module) over `.Touched` where possible, and only enable `CanTouch` when `.Touched` is genuinely required.  
* **The Destructible Debris Rule:** Any environmental asset designed to fracture, break apart, or simulate physics dynamically must automatically toggle `CanTouch = false` upon breaking. To prevent catastrophic server-side network lag caused by unanchored parts, these debris pieces must utilize the `Debris` service (`Debris:AddItem()`) with a strict **3 to 5-second maximum lifespan**, or be rendered purely on the client side. Never let unanchored physics objects persist in the workspace indefinitely.

## **🖥️ 5\. Graphics & Rendering Performance**

Optimizing rendering workflows ensures the experience remains fully playable across mobile devices and low-end hardware.

* **Performance Sightline Breaks:** Design layouts with intentional structural bends, occlusion walls, or hills to physically block long-distance camera views. This forces the engine's frustum culling to drop unseen assets from the rendering queue and maintain stable mobile frame rates.  
* **The Shadow Culling Rule:** Set CastShadow \= false for all foliage, small props, interior furniture, and distant background structures.  
* **The Overdraw Law:** Avoid stacking semi-transparent geometries (e.g., multiple layers of glass or overlapping alpha-blended leaf meshes). Stacking transparent layers causes the engine to repeatedly redraw the same pixels, heavily dropping frame rates.  
* **The Copy-Paste Law:** Never manually duplicate heavy, high-poly unique assets. Utilize **Roblox Packages** or instance your models to ensure the engine only loads the base asset data into system memory once.

## **🚧 6\. Map Boundaries & Player Containment**

Preventing players from escaping the map layout maintains spatial immersion, protects spawn points, and stops game-breaking boundary exploits.

* **The Global SpawnZone Standard:** A master, hazard-free `SpawnZone` completely isolated from gameplay risks (kill-bricks, hostile AI, active combat loops). It must maintain a minimum clear physical footprint of **5x5 studs per player slot** to prevent classic or Rthro avatar bounding boxes from clipping or stacking upon joining. All genre-specific starting configurations (e.g. Shooter team bases, Racing launch grids, Party lobbies) explicitly inherit these baseline safety and volumetric metrics — genre options only add what is specific to them, such as anti-camp placement.  
* **The "Natural Barrier" First Rule:** Hide map limits using organic, visual `Barrier`s first (unclimbable mountains, dense forests, deep oceans, tall city high-rises, or security fences). Invisible walls should only serve as a hidden safety net directly behind these visible barriers.  
* **Invisible Wall Property Standard:** When deploying invisible collision `Barrier`s, configure them exactly as follows to conserve engine resources:  
  * Transparency \= 1 (Completely invisible)  
  * CanCollide \= true (Solid barrier)  
  * CastShadow \= false (Prevents anomalous ghost shadows)  
  * CanTouch \= false (Saves CPU touch overhead)  
* **The Anti-Climb Angle:** `Humanoid.MaxSlopeAngle` (Section 1\) defaults to **89°**, so map boundaries are climbable unless this is deliberately addressed. To make boundaries unclimbable, choose one approach: (a) lower `MaxSlopeAngle` game-wide to roughly **45° to 50°**, after which any boundary slope steeper than that becomes unclimbable; or (b) leave the default and build boundaries that are effectively vertical (**≥ 85°**) or true walls. Do not rely on a 70–80° slope being unclimbable unless `MaxSlopeAngle` has been lowered.  
* **The Safety Net (FallenPartsDestroyHeight):** Located inside Workspace.Properties. Configure this to **50–100 studs below your lowest playable floor**. If a player clips through the geometry, this threshold cleanly intercepts them and resets/kills the avatar for a safe respawn.

## **🗺️ 7\. Level Design & Player Flow**

Subconscious environmental cues naturally direct players through the spatial layout and keep them oriented.

* **Spatial Orientation & Landmarks:**  
  * *In open-world or outdoor settings:* Position a massive, distinct `Landmark` (the classic "Weenie" principle, like a massive central skyscraper) to provide an instant sense of global direction.  
  * *In tight indoor settings or dungeons:* Use distinct, localized visual reference points (contrasting wall colors, asymmetrical pillars, unique lighting pockets) so players subconsciously understand their direction and don't walk in circles.  
* **Lighting Contrast (layout placement only):** Use light as a directional compass — players instinctively gravitate toward illuminated zones, so position brighter and darker areas to highlight doorways, main pathways, and objectives rather than lighting environments uniformly. *(Lighting mood, color, and fixtures are defined by the Theme doc.)*

## **Master Property Reference Table**

| Property / Feature | Optimized Configuration | Application Context |
| :---- | :---- | :---- |
| CanCollide | False | Small clutter, door handles, trash, decorative props, and visual stairs. |
| CanTouch | False | Static environmental walls, floors, and decorations without touch scripts. (Exception: `TriggerZone`s.) |
| CastShadow | False | Foliage, minor clutter, interior furniture, and far-off background architecture. |
| CollisionFidelity | Box or Hull | Set on complex 3D models and meshes to simplify physical hitboxes. |
| Transparency | Keep at 0 or 1 | Avoid stacking values between 0.1 and 0.9 to prevent mobile rendering lag. |
| InvisibleBarrier | Transparency \= 1, CanCollide \= true, CastShadow \= false, CanTouch \= false | Used directly behind natural barriers to cleanly enclose the map coordinate space. |
| FallenPartsDestroyHeight | **50–100 studs** below map base | Configured in Workspace properties to instantly catch and reset out-of-bounds players. |
| DestructibleDebris | CanTouch \= false; Debris:AddItem(part, 3\) | Applied immediately to unanchored physics clusters, breaking walls, or collapsing map elements to protect server CPU frames. |

---

# **Part II — Genre Layout Options**

Nothing in Part II is mandatory. Each genre is a menu of layout features the user picks from; the picks are what get injected into image generation.

## **How options work**

Every genre is one table. Every row is one pickable option.

| Field | Purpose |
| :---- | :---- |
| **ID** | Stable slug. **Shared across genres when it is the same concept** — this is the dedupe key for genre mixing. |
| **Option** | `Type (Flavor Name)`, where Type is a Shared Vocabulary term. No exceptions. |
| **What it is** | One sentence, written for *this genre*, phrased so it can be lifted more or less directly into an image-generation prompt. |
| **Core** | ● marks options that are signature to the genre. |
| **Goes to** | Whether the pick is drawn by the image model or placed after segmentation. See below. |
| **Pipeline** | Blank = fits the current pipeline (P0). Otherwise the modifier this option forces. |

### **Shape comes first, and you pick exactly one**

Each genre opens with a short **Shape** table. These are answers to a single question — *what shape is this space?* — so they are mutually exclusive, and a game has exactly one. Everything in the options table below is additive on top of the chosen shape and can be combined freely.

Shape is separated out because it is almost always the **pipeline-routing decision**. A flat arena is P0 and a multi-level one is P2; static roleplay housing is P0 and claimable housing is P3. Asking it first puts the expensive choice where its cost is visible, and it removes any chance of a user selecting two contradictory answers.

**A shape carries a Shared Vocabulary type when it is itself a region**, using the same `Type (Flavor Name)` form as an option — an arena is a `CombatZone` whatever form it takes, and segmentation needs it typed like anything else. Shapes that describe **map topology** rather than a place — *Open World* versus *Chaptered Journey* — carry no type, because there is no single region to name.

### **`Goes to` — image or layout**

Pipeline step 4 segments the isometric render into visible geometry: `Path`s, `Barrier`s, buildings, props, terrain. Anything invisible cannot be recovered from an image, so it must not be sent to the image model at all.

| Value | Meaning |
| :---- | :---- |
| `image` | Visible geometry. Injected into the image-generation prompt. |
| `layout` | Invisible or non-geometric — a trigger volume, a spawn marker, a pickup, an emitter. Placed against the segmented layout afterward. |
| `both` | Has a visible part and an invisible part. **Only the visible part is injected**; the rest is placed. |

**The rule, for anything not in a table.** If a segmenter could identify it as geometry, it is `image`. If it is an invisible volume, a marker, a trigger, or a *property* of geometry rather than geometry itself, it is `layout`. This matters because the user can always type a request that has no row to look up.

This split is also what keeps the image prompt from saturating. Roughly half of a genre's options never reach the image model, so the user's freedom to pick is not limited by the image model's tolerance for instructions.

### **Shared IDs carry genre-specific wording**

A shared ID means two genres want the *same concept*, so the menu presents it once. It does **not** mean they describe it the same way. `hazard-kill` is "bottomless pits wrapping the arena" in Action and "a spreading disaster volume" in Survival — same dedupe key, different words, and the genre-specific words are what get injected. Generic phrasing is useless to an image model.

Each genre table therefore stands alone and is readable without the registry below.

### **`Core` is a ranking aid, not a rule**

● does **not** mean "include automatically." It means "if the list is long, lead with these." It exists for the mixed-genre case: an *Action Adventure RPG Shooter Puzzle* game merges five tables into something unwieldy, and ● signals which handful actually characterize each genre. An option without ● is equally valid to pick.

### **Pipeline costs**

From `LayoutGen - Pipeline.md`. Shown per-option so the cost of a pick is visible at the moment of picking.

| Tag | Meaning |
| :---- | :---- |
| *(blank)* | P0 — current pipeline handles it. |
| `P0 + tiered` | Elevation relief with no overhang. Supported, but the height must be captured or it builds flat. |
| `P2` | Surfaces overhang. Needs per-elevation slices plus a vertical connectivity graph. |
| `P3` | Play moves outside↔inside. Needs a second, linked roofless interior top-down. |
| `P4` | Several distinct maps that don't co-exist on one surface. Needs per-zone passes. |
| `P6` | Structure must be valid by construction. Layout is generated procedurally first, then dressed. |
| `CHECK` | Usually fine; only breaks if the play volume self-occludes. |

### **Presets**

A preset is **one shape answer plus a few option IDs**, modelled on a real game. It exists so the common case is a single decision rather than a dozen, and it replaces what earlier drafts called sub-genres. Picking a preset is picking its contents in one action; the user can add or drop anything afterward.

**Presets carry two names.** The *Modelled on* column names real games and is **internal reference for the LLM only** — it grounds the preset in something concrete and makes the intent unambiguous. What gets shown to a user is the generic style name. A Counter-Strike map is offered as "round-based bomb defusal," never by the game's name.

Reference games are drawn from 3D games generally, with Roblox examples wherever the platform has a canonical one, since Roblox convention is often what a user is actually picturing.

**Naming comes from published taxonomies, not invention**, in this order of preference:

1. **Roblox's official subgenre name**, where one fits. The Genre List below is already Roblox's genre taxonomy, so its subgenres are the most authoritative names available — they are what a creator sees in the Creator Dashboard and what Discovery sorts by. *Battlegrounds*, *Tower Obby*, *Escape Room*, *Tycoon*, *Battle Royale*, and *Open World Action* all come from there.
2. **The established industry subgenre term**, where Roblox's taxonomy is too coarse. Roblox files Team Deathmatch, Capture the Flag, and free-for-all all under *Deathmatch Shooter*, but those are three different layouts, so the standard mode names are used instead.
3. **A plain descriptive name**, only when neither exists.

Never invent a name that competes with an existing one — the point is that the user recognises it immediately.

### **Presentation**

Offer the closest preset first. If the user wants to tune, show the shape question and the `Core` options — around five items on screen, never the full table. Then ask an open question for anything else they want, and classify whatever comes back with the `Goes to` rule above.

Never truncate the list silently. Five options plus an open question is safe; the top five of forty is not, because the rest become undiscoverable.

### **Mixing genres**

Load each genre's table, union the rows, **drop duplicate IDs**. Present each option once, using the phrasing from whichever genre dominates the prompt.

**The dominant genre owns the shape.** Secondary genres contribute additive options only. Shape answers are mutually exclusive *within* a genre and they compete *across* genres — "an action RPG with a tower section" makes three shape claims, and honouring all three stacks P2, P3, and P4 out of a single sentence. Pick one shape, and offer the others' distinguishing features as ordinary options.

## **Genre List**

1. **Action** — fast-paced physical combat, arenas, and battlegrounds.  
2. **Adventure** — story-driven exploration, scavenger hunts, and narrative quests.  
3. **Obby & Platformer** — obstacle courses, tower climbs, and skill-based jumping (e.g. Tower of Hell).  
4. **Party & Casual** — social and round-based minigames, trivia, and childhood classics like tag and hide-and-seek.  
5. **Puzzle** — logic challenges, escape rooms, and mazes.  
6. **RPG** — worlds with character progression, stats, and real-time or turn-based combat.  
7. **Roleplay & Avatar Sim** — town-and-life simulations where players adopt characters, care for pets, or customize avatars (e.g. Brookhaven).  
8. **Shooter** — competitive team deathmatches, Battle Royales, and PvE shooters.  
9. **Simulation** — tycoons, role and job sims, vehicle operation, and incremental/idle clicking.  
10. **Strategy** — tower defense, real-time strategy, and top-down management.  
11. **Survival** — threat evasion, disaster survival, and mascot horror.  
12. **Sports** — stadium sports, court and field games, and physics-based athletics.  
13. **Racing** — competitive racing over a finite track or lap count (cars, track, swimming).  
14. **Infinite Runner** — procedural auto-runners centered on automated forward translation and reaction timing.  
15. **Entertainment (Showcase & Hub)** — experiences built to be consumed or explored rather than "won." Covers art and graphics Showcases and Hub worlds that portal players onward. The Music & Audio and Video subgenres rarely involve a 3D environment and route out to P5.

## **Shared ID registry**

Which IDs appear in more than one genre, so dedupe is a set union. **This is an index, not the definition source** — each genre table below carries its own wording.

| ID | Concept | Appears in |
| :---- | :---- | :---- |
| `collectible-nodes` | Scattered pickups | Adventure, Obby, Puzzle, RPG, Simulation, Survival, Infinite Runner, Entertainment |
| `hazard-kill` | A region that damages or kills | Action, Adventure, Obby, Simulation, Survival, Racing, Infinite Runner |
| `teleporter-link` | Paired point-to-point transport | Adventure, Obby, Party, RPG, Roleplay, Entertainment |
| `cover-los` | Geometry that breaks line of sight | Action, Party, Shooter, Strategy, Survival |
| `gate-progression` | A blockade that opens on purchase, level, or solve | Adventure, Puzzle, RPG, Simulation, Strategy |
| `social-hub` | A shared space sized for crowds | Party, RPG, Roleplay, Simulation, Entertainment |
| `spawner-npc` | Where NPCs enter the space | Action, RPG, Shooter, Strategy, Survival |
| `spectator-zone` | A non-play area to watch from | Action, Obby, Party, Sports, Racing |
| `building-interior` | A structure players go inside | RPG, Roleplay, Shooter, Survival |
| `landmark-focal` | A large orienting structure visible from distance | Adventure, RPG, Roleplay, Entertainment |
| `powerup-buffs` | Timed pickups | Action, Obby, Shooter, Infinite Runner |
| `spawn-protected` | Start points shielded from immediate threat | Action, Party, Shooter, Survival |
| `buildzone-plot` | A footprint where players place their own structures | RPG, Strategy, Survival |
| `checkpoint-respawn` | Touch-to-activate recovery point | Adventure, Obby, Racing |
| `choke-bottleneck` | A deliberate narrow point concentrating traffic | Action, Shooter, Strategy |
| `destructible-cluster` | Structures authored to break apart | Action, Strategy, Survival |
| `marker-distance` | Visual increments showing progress | Sports, Racing, Infinite Runner |
| `obstacle-jump` | Jump-based obstacles | Obby, Infinite Runner |
| `obstacle-maze` | A maze the player routes through | Obby, Party |
| `obstacle-moving` | Moving or rotating obstacles | Obby, Infinite Runner |
| `path-loop` | Routes that circle back, no dead ends | Puzzle, Shooter |
| `path-road-vehicle` | Vehicle-width road network | Roleplay, Simulation |
| `trigger-scoring` | A detection region registering a point | Party, Sports |
| `vignette-photo` | A spot composed for screenshots | Roleplay, Entertainment |

---

## **1\. Action**

*Fast-paced physical combat and arenas.*

**Shape — pick one.** Every Action map is a bounded, collision-clean clash space with readable geometry for reliable hitbox math. The question is what form it takes.

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `arena-flat` | **CombatZone (Flat Arena)** | A single level floor, free of minor tripping geometry, for the cleanest possible physics. | |
| `arena-tiered` | **CombatZone (Terraced Arena)** | Stepped or terraced relief — strong elevation, nothing overhanging. | `P0 + tiered` |
| `arena-stacked` | **CombatZone (Multi-Level Arena)** | Catwalks, balconies, or floors that overhang the arena below. | `P2` |
| `arena-chain` | **CombatZone (Arena Chain)** | A linear run of combat rooms joined by corridors rather than one open space. | |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `cover-los` | **Cover (Line-of-Sight Pillars)** | Large columns scattered across the floor, letting a retreating player break combat lock and heal. | ● | `image` | |
| `hazard-kill` | **HazardZone (Ring-Out Edges)** | Open edges or bottomless pits wrapping the arena, making aggressive positioning a real risk. | ● | `image` | |
| `spawn-protected` | **SpawnZone (Anti-Camp Placement)** | Spawns set back, screened, or elevated so a player isn't in an enemy firing line the frame they appear. | ● | `both` | |
| `choke-bottleneck` | **Choke (Conflict Chokepoint)** | Doorways, bridges, or narrow gaps that funnel fighters together into predictable flashpoints. | | `image` | |
| `destructible-cluster` | **Destructible (Breakable Cover)** | Welded structures that fracture under fire, so cover degrades as the fight goes on. | | `image` | |
| `arena-lockin` | **Gate (Combat Lock-In)** | Shutters or barriers that seal the exits until the current wave is cleared. | | `image` | |
| `spectator-zone` | **SpectatorZone (Ringside Stands)** | Raised seating or a walled gallery where eliminated players watch the fight. | | `image` | `P0 + tiered` |
| `spawner-npc` | **Spawner (NPC & Trap Emitters)** | Points where hostile NPCs or traps enter the arena mid-fight. | | `layout` | |
| `powerup-buffs` | **PowerUp (Combat Buffs)** | Damage, shield, or speed pickups placed around the floor to pull players into contested space. | | `layout` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Battlegrounds** | The Strongest Battlegrounds, Jujutsu Shenanigans (Roblox); Power Stone | `arena-flat` | `hazard-kill`, `spawn-protected`, `cover-los` |
| **Fighting** | For Honor, Chivalry; Untitled Boxing Game (Roblox) | `arena-flat` | `spawn-protected`, `cover-los`, `choke-bottleneck` |
| **Sword Fighting** | Sword Fights on the Heights IV (Roblox) | `arena-tiered` | `powerup-buffs`, `hazard-kill`, `cover-los` |
| **Platform Fighter** | Super Smash Bros. | `arena-tiered` | `hazard-kill`, `cover-los` |
| **Open World Action** | Assassin's Creed; Jujutsu Shenanigans open-world mode (Roblox) | `arena-stacked` | `cover-los`, `choke-bottleneck` |
| **Boss Raid** | Monster Hunter, Dark Souls; Dungeon Quest (Roblox) | `arena-flat` | `spawner-npc`, `destructible-cluster`, `hazard-kill` |
| **Hack & Slash** | Devil May Cry, God of War, Bayonetta | `arena-chain` | `arena-lockin`, `spawner-npc`, `destructible-cluster` |

**Genre notes**

* **Boundaries.** Action is physical and melee-leaning; Shooter is about ranged sightlines and lane discipline. If the map is organized around firing corridors rather than a shared clash space, use Shooter. If there are formal scoring rules and a fixed field spec, it's Sports.
* **Spawn safety is mostly inherited.** Part I §6 already mandates a hazard-free spawn isolated from gameplay risk, at 5×5 studs per player slot. The Action-specific part is *only* the anti-camp placement — don't restate the baseline.
* **Verticality is optional here and often assumed mandatory.** A flat arena is a perfectly valid Action map. Terracing and multi-level catwalks are style choices with real pipeline cost, not requirements.
* **Two options exist because the presets demanded them.** Building the preset list surfaced that the genre could not express a hack-and-slash at all — no linear room-to-room form and no combat lock-in, despite both being staples. `arena-chain` and `arena-lockin` were added for it.
* **Roblox's own subgenres for Action are Battlegrounds & Fighting, Music & Rhythm, and Open World Action.** Two of the three are presets above. *Music & Rhythm* has no meaningful 3D layout job and routes to **P5**.
* **Battlegrounds is a Roblox-native format.** The Strongest Battlegrounds effectively created it, and the flat bounded arena with ring-out edges is the shape the whole wave of imitators inherited. When a user asks for an anime fighting game, this is almost always the layout they are picturing.

---

## **2\. Adventure**

*Story-driven journeys and exploration — anywhere from a single explorable map to a multi-chapter quest.*

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `world-open` | **Open World** | One contiguous explorable map, found in any order the player likes. | |
| `world-corridor` | **Guided Corridor** | A single directed route through one continuous space, gated so the player can't wander backward. | |
| `world-chaptered` | **Chaptered Journey** | Story chapters as genuinely separate maps that don't co-exist on one surface. | `P4` |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `path-trail` | **Path (Exploration Trail)** | A walkable route threading the space — a worn track, road, canyon floor, or ridge line. | ● | `image` | |
| `landmark-focal` | **Landmark (Directed Point of Interest)** | A ruin, vista, or structure that pulls the player toward it and gives exploration a direction. | ● | `image` | |
| `collectible-nodes` | **Collectible (Objective Items)** | Quest items and narrative targets housed on altars, pedestals, or in ruins. | ● | `layout` | |
| `alcove-secret` | **Zone (Discovery Alcove)** | Hidden cutouts behind waterfalls, fake walls, or overgrowth that reward poking around. | | `image` | |
| `gate-oneway` | **Gate (One-Way Drop)** | Low cliffs or drop-downs that stop players wandering back into finished areas. | | `image` | |
| `gate-chapter` | **Gate (Chapter Threshold)** | A canyon, gate, or structural door marking a definite transition between story chapters. | | `image` | |
| `reveal-exit` | **Path (Cinematic Reveal Exit)** | A structural exit — a tight cave opening into a massive valley — placed so the layout itself reveals a distant landmark. | | `image` | `P3` |
| `tracker-quest` | **Tracker (Quest Board)** | A physical board or pillar where objectives are posted and tracked. | | `both` | |
| `gate-progression` | **Gate (Story Lock)** | A door or barrier that stays shut until the current objective is done. | | `image` | |
| `teleporter-link` | **Teleporter (Fast Travel)** | Paired markers letting players skip back to already-discovered locations. | | `both` | |
| `checkpoint-respawn` | **Checkpoint (Journey Save Point)** | Rest points along the route that players return to rather than restarting the chapter. | | `layout` | |
| `hazard-kill` | **HazardZone (Environmental Danger)** | Chasms, rapids, or lava fields that punish careless traversal. | | `image` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Exploration** | Breath of the Wild, Journey | `world-open` | `landmark-focal`, `alcove-secret`, `path-trail` |
| **Scavenger Hunt** | Find the Markers (Roblox); Roblox Egg Hunt events | `world-open` | `collectible-nodes`, `alcove-secret`, `tracker-quest` |
| **Story** | Uncharted, A Short Hike | `world-chaptered` | `gate-chapter`, `reveal-exit`, `gate-oneway` |
| **Quest Hub** | The Legend of Zelda; World // Zero (Roblox) | `world-open` | `tracker-quest`, `gate-progression`, `teleporter-link` |
| **Guided Trail** | Firewatch | `world-corridor` | `path-trail`, `landmark-focal`, `reveal-exit` |

**Genre notes**

* **Boundaries.** Without a focal pull the space is a sandbox, not an adventure. And if the landmark is the whole point rather than a reward for reaching it — nothing to collect, no gate it opens, no further reveal — it's an Entertainment Showcase. Add stats, levelling, or a combat loop and it becomes RPG.
* **Linear does not automatically mean multi-zone.** A valley trail gated by canyons is one contiguous surface and routes P0. Only tag `P4` when chapters are genuinely separate maps that can't co-exist.
* **The reveal is a layout job, not a camera job.** The layout's role is placing the opening and the distant landmark so the composition exists. How the camera frames it belongs to the Mechanics doc.
* **Original framing was too narrow.** Build's first version required chapter gates, cinematic reveals, and objective pedestals — that describes one style of adventure, not the genre. A single explorable map with a ruin in it qualifies.
* **Roblox's own subgenres for Adventure are Exploration, Scavenger Hunt, and Story**, and all three are presets above. Scavenger Hunt is a much larger category on Roblox than off it, driven by the platform's event and badge culture.

---

## **3\. Obby & Platformer**

*Obstacle courses, skill-based climbing, and movement challenges. The player controls their own movement and takes discrete jumps at their own pace.*

**Genre route: `P6`.** Physics-legal platform spacing *is* the game, so the course is generated procedurally first and dressed after. Gaps on the critical path must stay within Part I §1 limits — **≤ 11 studs** horizontal, **≤ 7.2 studs** vertical at default `WalkSpeed`/`JumpHeight`.

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `course-flat` | **Path (Flat Course)** | A course laid out across the ground, progressing horizontally. | `P6` |
| `course-terraced` | **Path (Ascending Terraces)** | A course climbing a hillside or staircase — strong vertical gain, nothing overhanging. | `P6 + tiered` |
| `course-tower` | **Path (Tower / Spiral Ascent)** | A course wrapping or stacking so platforms sit directly above each other. | `P6 + P2` |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `path-track` | **Path (Sequential Platform Track)** | A chain of platforms spaced to the physics limits above — the ordered route through the course. | ● | `image` | `P6` |
| `checkpoint-respawn` | **Checkpoint (Safe Landing Pad)** | Flat enclosed pads where players stop safely and respawn on failure instead of restarting the course. | ● | `both` | |
| `hazard-kill` | **HazardZone (Contact-Lethal Surfaces)** | Surfaces that kill on touch — strips, checkers, rolling balls, closing walls, deadly-sided paths. | ● | `image` | |
| `obstacle-jump` | **Path (Jump Obstacles)** | Long horizontal jumps, trampoline boosts, wrap-arounds, and stepped vertical platforms. | | `image` | |
| `obstacle-moving` | **Path (Moving Obstacles)** | Rotating platforms, conveyors, and swinging or sliding hazards. | | `image` | |
| `obstacle-timing` | **Path (Timed Obstacles)** | Platforms that vanish after being stepped on, or a set time after activation. | | `image` | |
| `obstacle-climb` | **Path (Climb Obstacles)** | Trusses, ladders, tightropes, and wall scrambles. | | `image` | |
| `obstacle-guess` | **Path (Guess Obstacles)** | Hidden-correct-path and door-guessing sections where the wrong pick drops you. | | `image` | |
| `obstacle-maze` | **Zone (Maze Segment)** | A maze the player has to route through mid-course. | | `image` | `P6` |
| `path-shortcut` | **Path (High-Risk Shortcut)** | Significantly tighter alternate routes that skip ahead for skilled players. | | `image` | |
| `winner-zone` | **WinnerZone (End Reward Area)** | The payoff at the end — path tools, flight tools, speed, morphs, interactables. | | `both` | |
| `spectator-zone` | **SpectatorZone (Glass Overlook)** | A separate balcony where eliminated players watch the active track. | | `image` | |
| `collectible-nodes` | **Collectible (Course Pickups)** | Coins or tokens placed on risky lines to bait players off the safe route. | | `layout` | |
| `powerup-buffs` | **PowerUp (Movement Buffs)** | Speed or jump pickups that change how a section can be cleared. | | `layout` | |
| `teleporter-link` | **Teleporter (Stage Skip)** | Markers that jump players between stages or back to a hub. | | `both` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Classic Obby** | [Doc's Difficulty Chart Obby 2](https://www.roblox.com/games/7013860652/Docs-Difficulty-Chart-Obby-2) (Roblox) | `course-flat` | `path-track`, `checkpoint-respawn`, `obstacle-jump`, `obstacle-moving` |
| **Tower Obby** | Tower of Hell (Roblox) | `course-tower` | `path-track`, `obstacle-timing`, `obstacle-climb`, `winner-zone` |
| **Precision Platformer** | Super Mario 64, Celeste | `course-terraced` | `obstacle-jump`, `obstacle-moving`, `path-shortcut` |
| **Vehicle Obby** | Roblox vehicle obbies | `course-flat` | `path-track`, `checkpoint-respawn`, `hazard-kill` |
| **Co-op Obby** | Roblox two-player obbies | `course-flat` | `path-track`, `checkpoint-respawn`, `teleporter-link` |
| **Glitch Obby** | Roblox glitch obbies | `course-tower` | `obstacle-climb`, `path-shortcut` |

**Preset caveats.** *Vehicle Obby* derives spacing from turning radius, top speed, and ramp tolerance rather than jump metrics; checkpoints restore vehicle position, orientation, and zeroed velocity; lane widths follow the vehicle bounding box rather than the 4-stud avatar standard. *Co-op Obby* spaces to the pair's combined reach, saves both players at a checkpoint together, and may use `teleporter-link` to swap roles. *Glitch Obby* sets gaps deliberately **beyond** normal limits and cannot be validated — see the notes below.

**Genre notes**

* **Reference.** [Doc's Difficulty Chart Obby 2](https://www.roblox.com/games/7013860652/Docs-Difficulty-Chart-Obby-2). Tower of Hell is the platform's canonical tower obby.
* **Boundaries.** Obby vs Racing: the obby player moves at their own pace over discrete jumps; a racer is competing on speed over a finite track or lap count. **A vehicle obby that adds lap counting or a multi-lane starting grid has become Racing — build it there.** Obby vs Infinite Runner: forward motion is the player's in an obby, automatic in a runner.
* **The full obstacle catalog.** The five grouped `obstacle-*` options above compress a longer working list: *Guess* — hidden path, door choice. *Jumps* — horizontal long jumps, trampoline boosts, wraps (horizontal in-and-out movement around a part), vertical platforms (in-and-out movement to climb). *Other* — maze, moving and rotating platforms and deadly objects, conveyors (which hinder by slowing the player or by making them too fast to judge jumps), tight rope, truss and ladder climbs, timed paths (disappear *t* seconds after activation — beat-the-clock feel), disappearing paths (vanish after being stepped on — survival feel). Treat it as a toolkit, not a taxonomy.
* **Classic vs bespoke.** Difficulty-chart obbies reuse these blocks directly and repetitively. Modern bespoke obbies increasingly blend several into unique hand-built stage environments rather than repeating a fixed set — so don't assume a stage is one obstacle type.
* **Most obbies aren't lethal on contact.** Failure is usually falling into a void or timing out, not touching something deadly. Reserve `hazard-kill` for genuinely contact-lethal obstacles rather than applying it to every hazard.
* **Checkpoints are near-universal but not universal.** Very short courses and intentionally hardcore no-checkpoint obbies deliberately omit them.
* **Glitch obbies can't be validated.** They rely on undocumented `Humanoid` state-machine timing — wallhopping, ladder flicking, corner clipping — rather than the documented physics baseline. Spacing can't be derived from Part I and the P6 generator can't check it; treat the structure as author-supplied.
* **Co-op obbies break the "own pace" assumption.** Balloon-and-holder and frog-and-tongue pairs have complementary movement abilities, so neither player can progress solo. The layout has to make separation and permanent stranding impossible.
* **Roblox's own subgenres here are Classic Obby, Tower Obby, and Runner.** The first two are presets above. **Runner is filed by Roblox under this genre but is genre 14 here** — see the note there for why the split is deliberate.

---

## **4\. Party & Casual**

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

---

## **5\. Puzzle**

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

---

## **6\. RPG**

*Character progression, stat grinding, combat loops, and economic hubs.*

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `world-single` | **Single Contiguous Map** | Town, roads, and mob clearings all on one surface, no instanced areas. | |
| `world-hub-dungeon` | **Hub and Dungeons** | A safe hub feeding separate instanced combat areas entered from the overworld. | `P4 + P3` |
| `world-open-biomes` | **Open World with Biomes** | Regions whose difficulty and reward scale with distance — tougher wildlife and scarcer resources further out. | `P4` |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `safezone-town` | **SafeZone (Sanctuary Town)** | A settlement completely isolated from enemy AI where players restock, repair, and turn in quests. | ● | `image` | |
| `social-hub` | **SocialZone (Economy Ring)** | Shop, quest giver, and blacksmith clustered tightly together to cut repetitive travel for grinding players. | ● | `image` | |
| `hazard-aggro` | **HazardZone (Aggro Bowl)** | Wide open clearings or monster nests holding hostile spawns, set well back from travel roads so low-level players aren't ambushed in transit. | ● | `image` | |
| `spawner-npc` | **Spawner (Mob Emitters)** | The specific points inside a nest or clearing where mobs come from. | | `layout` | |
| `gate-progression` | **Gate (Level-Gated Throat)** | Highly visible blockades — guarded bridges, castle gates, mountain cracks — physically stopping under-levelled players entering high-threat ground. | | `image` | |
| `collectible-nodes` | **Collectible (Resource Veins)** | Repeating alcoves reserved for mining nodes, woodcutting stands, and herb patches. | | `both` | |
| `teleporter-link` | **Teleporter (Fast-Travel Plinth)** | Standardized stone platforms outside major landmarks acting as travel endpoints. | | `both` | |
| `landmark-focal` | **Landmark (Regional Waypoint)** | Distant structures that let a player orient themselves across a large world. | | `image` | |
| `buildzone-plot` | **BuildZone (Unclaimed Territory)** | Broad open buildable land where players and tribes raise their own bases anywhere they like. | | `image` | |
| `building-interior` | **Zone (Enterable Shop or Inn)** | Buildings players actually go inside rather than interact with from the street. | | `image` | `P3` |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Action RPG** | [World // Zero](https://www.roblox.com/games/2727067538/World-Zero-Anime-RPG) (Roblox); Diablo | `world-hub-dungeon` | `safezone-town`, `social-hub`, `hazard-aggro`, `spawner-npc` |
| **Open World & Survival RPG** | [Booga Booga](https://www.roblox.com/games/11729688377/Booga-Booga) (Roblox); Valheim | `world-open-biomes` | `buildzone-plot`, `collectible-nodes`, `landmark-focal` |
| **Turn-based RPG** | Pokémon; Loomian Legacy (Roblox) | `world-single` | `safezone-town`, `spawner-npc`, `gate-progression` |
| **Dungeon Crawler** | Dungeon Quest (Roblox); Diablo | `world-hub-dungeon` | `spawner-npc`, `gate-progression`, `social-hub` |
| **MMO Town Hub** | World of Warcraft | `world-single` | `safezone-town`, `social-hub`, `teleporter-link`, `landmark-focal` |

**Genre notes**

* **References.** [World // Zero](https://www.roblox.com/games/2727067538/World-Zero-Anime-RPG) for hub-and-dungeon — NPC quest hubs, fenced-off mob nests, physical level gates. [Booga Booga](https://www.roblox.com/games/11729688377/Booga-Booga) for open-world survival RPG.
* **Boundaries.** RPG vs Adventure: progression systems, stats, and a combat loop. The Open World & Survival RPG bundle overlaps heavily with Survival's Resource/Base bundle — they're close enough to be near-duplicates, so pick one and don't build both.
* **Don't force a level gate onto survival RPG.** Progression there comes from gear tier and a rebirth or reset loop, not physical blockades. No zone is unconditionally off-limits by level alone, so a guarded bridge is actively wrong for the style.
* **Danger is a gradient, not a fence.** In the survival style, threat scales continuously across the map — tougher wildlife and scarcer resources the further or deeper you go — and player-versus-player risk exists everywhere, not just around NPC spawns.
* **Resource nodes change tier by style.** Optional flavor in hub-and-dungeon; the entire progression loop in open-world survival.
* **Roblox's own subgenres here are Action RPG, Open World & Survival RPG, and Turn-based RPG** — all three are presets above, and the middle one matches the bundle this doc already had under that exact name.
* **Turn-based RPG barely changes the layout.** Combat resolution is a mechanic, not a space. The layout job is the same town-and-overworld work as any other RPG, which is why it carries no distinct shape.

---

## **7\. Roleplay & Avatar Sim**

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

---

## **8\. Shooter**

*Competitive team deathmatches, tactical combat, and positioning.*

**Shape — pick one.** How the map organises movement between the shooting.

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `lane-network` | **Lane (Lane Network)** | Parallel routes, classically three, channelling team traffic into predictable engagement fronts. | |
| `breach-sequence` | **Path (Breach Sequence)** | A raid site of rooms that dead-end into breach points, cleared in a defined order rather than looped. | |
| `open-battlefield` | **Zone (Open Battlefield)** | One large contiguous map with dispersed points of interest instead of defined lanes. | |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `cover-los` | **Cover (Tactical Cover Arrays)** | Waist-high (3–4 studs) and full-body (7–8 studs) cover distributed evenly across every lane. | ● | `image` | |
| `spawn-teambase` | **SpawnZone (Opposing Team Bases)** | Balanced bases at opposite ends of the map, completely shielded from enemy sniper lines. | ● | `both` | |
| `choke-bottleneck` | **Choke (Lane Pinch Point)** | Narrow transitions where lanes meet, concentrating fights into contested ground. | ● | `image` | |
| `spawn-protected` | **SpawnZone (Spawn Shield)** | Geometry directly around a spawn breaking the sightlines into it. | | `both` | |
| `path-loop` | **Path (Interconnected Rooms)** | Rooms with two or more entrances and exits, favouring constant interconnectedness over realistic dead ends. | | `image` | |
| `capture-zone` | **CaptureZone (Flag Stand / Bomb Site)** | A point scored by carrying something to it or holding it against contest. | | `both` | |
| `control-zone` | **ControlZone (Held Point)** | A capacity-limited occupancy area with a visible indicator — the King-of-the-Hill hill. | | `both` | |
| `cover-elevated` | **Cover (Elevated Firing Position)** | Windows, towers, and nests reachable only through exposed, predictable stairs or ladders. | | `image` | `P0 + tiered`, or `P2` if it overhangs the floor below |
| `path-flank-tunnel` | **Path (Flanker Tunnel)** | Subterranean or interior routes letting fast players bypass the main-lane standoff. | | `image` | `P2` |
| `building-interior` | **Zone (Breachable Structure)** | A house, apartment, or compound entered from outside. | | `image` | `P3` |
| `spawner-npc` | **Spawner (Enemy Wave Origin)** | Where hostile AI enters the map, sited so defenders have a readable direction to hold against. | | `layout` | |
| `boundary-shrinking` | **BoundaryZone (Closing Play Area)** | A play boundary that contracts over the match, compressing survivors toward a shifting centre. | | `layout` | |
| `collectible-loot` | **Collectible (Scattered Loot)** | Weapons and equipment distributed across the map so players arm themselves from the world. | | `layout` | |
| `powerup-buffs` | **PowerUp (Armour & Weapon Spawns)** | Fixed-position pickups on a respawn timer that players fight to control. | | `layout` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Team Deathmatch** | Phantom Forces, Arsenal (Roblox); Call of Duty | `lane-network` | `spawn-teambase`, `cover-los`, `choke-bottleneck` |
| **Bomb Defusal** | Counter-Strike, Valorant | `lane-network` | `capture-zone`, `choke-bottleneck`, `cover-los`, `spawn-teambase` |
| **Capture the Flag** | Halo, Team Fortress 2 | `lane-network` | `capture-zone`, `path-flank-tunnel`, `spawn-teambase` |
| **King of the Hill** | Halo, Battlefield Conquest | `lane-network` | `control-zone`, `cover-elevated`, `cover-los` |
| **Arena Deathmatch** | Quake, Doom | `lane-network` | `powerup-buffs`, `cover-elevated`, `path-loop` |
| **Tactical Shooter** | Rainbow Six Siege; [BODYCAM: SWAT Simulator](https://www.roblox.com/games/16404660684/BODYCAM-SWAT-Simulator) (Roblox) | `breach-sequence` | `building-interior`, `cover-los` |
| **PvE Shooter** | Left 4 Dead, Killing Floor | `lane-network` | `spawner-npc`, `choke-bottleneck`, `building-interior` |
| **Battle Royale** | PUBG, Fortnite, Apex Legends | `open-battlefield` | `boundary-shrinking`, `collectible-loot`, `building-interior` |

**Genre notes**

* **References.** Phantom Forces and Arsenal for arcade run-and-gun — by far the most common shooter style on the platform. [BODYCAM: SWAT Simulator](https://www.roblox.com/games/16404660684/BODYCAM-SWAT-Simulator) for MilSim.
* **MilSim inverts the arcade assumptions.** Slow, deliberate, high-punishment pacing instead of constant action. The map is a raid site built from rooms that dead-end into breach points, not a looping lane network — players clear in sequence rather than choosing between parallel lanes.
* **Exposed chokepoints are the point in MilSim.** Arcade cover is distributed evenly to keep fights constant; MilSim breach points are *deliberately* exposed because that tension is the design. Don't "fix" them.
* **MilSim usually has no mirrored bases.** It's typically squad-versus-objective PvE, or squad-versus-squad with one life. That implies one staging spawn per squad, not two symmetric respawning bases.
* **Boundaries.** Shooter organizes around firing corridors and sightlines; Action organizes around a shared clash space. Arcade shooters favor unrealistic interconnectedness — rooms with multiple exits — precisely to avoid the dead ends MilSim wants.
* **Four options exist because the presets demanded them.** The Genre List has always named Battle Royale and PvE shooters, and Roblox's official taxonomy has both as subgenres, yet the table could express neither — no contracting boundary, no scattered loot, no enemy emitter. `boundary-shrinking`, `collectible-loot`, `powerup-buffs`, and `spawner-npc` were added when the preset list made the gaps obvious.
* **Roblox's own subgenres for Shooter are Battle Royale, Deathmatch Shooter, and PvE Shooter.** That taxonomy is too coarse for layout: Team Deathmatch, Capture the Flag, King of the Hill, and free-for-all are all *Deathmatch Shooter* to Roblox but need four different maps. The presets use the standard mode names instead, which is the one place a Roblox subgenre name is deliberately not used.
* **The contracting boundary is the cleanest example of an invisible pick.** It has no geometry at all, so it cannot be segmented out of a render and must never enter the image prompt. It is computed and placed against the finished layout.
* **Still uncovered.** Rail and gallery shooters with no player movement at all (Duck Hunt) have no meaningful layout job and probably route to P5. Hero shooters are served by the Hill Control preset today, but class-specific spawn rooms and ability-traversal geometry are not represented — flag it if one comes up.

---

## **9\. Simulation**

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

---

## **10\. Strategy**

*Tower defense, tactical layouts, and top-down management.*

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `lane-actor-track` | **Path (Enemy Lane)** | A single continuous, unchanging lane winding from spawn to the core that enemy waves are hard-coded to follow — no dead-end branches, no ambiguous self-crossings. | `P6` |
| `terrain-open` | **Zone (Open Contested Terrain)** | No lane at all — units path dynamically across open ground between symmetrically distributed bases. | |
| `board-grid` | **Zone (Board Grid)** | A tabletop-scale grid or board that players act on rather than move through. | |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `buildzone-grid` | **BuildZone (Tower Placement Grid)** | Flat structural zones framing both sides of the track where players click to deploy defenders. | ● | `image` | |
| `tracker-core` | **Tracker (The Core Base)** | The structure at the end of the track that visually represents the player's primary health pool. | ● | `both` | |
| `spawner-npc` | **Spawner (Wave Origin)** | The mouth of the track where each enemy wave enters. | ● | `layout` | |
| `buildzone-plateau` | **BuildZone (High-Ground Plateau)** | Raised build zones sitting inside path loops, giving long-range units a placement advantage. | | `image` | `P0 + tiered` |
| `cover-los` | **Cover (Line-of-Sight Blockers)** | High walls blocking specific angles of the track so no single placement dominates the whole map. | | `image` | |
| `choke-bottleneck` | **Choke (Track Pinch Point)** | A narrowing in the lane where waves bunch up and area damage pays off. | | `image` | |
| `destructible-cluster` | **Destructible (Breakable Terrain)** | Structures along the route that units or abilities can clear. | | `image` | |
| `buildzone-plot` | **BuildZone (Territorial Free Placement)** | Broad open buildable land radiating outward from each player's base, gated by proximity rules rather than a fixed grid. | | `image` | |
| `gate-progression` | **Gate (Tier Unlock)** | A barrier opening onto later map sections or stronger unit tiers. | | `image` | |
| `collectible-nodes` | **Collectible (Contested Resource Sites)** | Ore, timber, and food sites scattered across the terrain that players expand toward and fight over. | | `layout` | |
| `tile-grid` | **Zone (Playing Board)** | A tabletop-scale grid of evenly divided squares or spaces that pieces move across. | | `image` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Tower Defense** | Tower Defense Simulator (Roblox); Bloons TD | `lane-actor-track` | `buildzone-grid`, `tracker-core`, `spawner-npc`, `choke-bottleneck` |
| **Real-Time Strategy** | [MEDIEVAL REAL TIME STRATEGY](https://www.roblox.com/games/10853515606/MEDIEVAL-REAL-TIME-STRATEGY) (Roblox); Age of Empires | `terrain-open` | `buildzone-plot`, `tracker-core`, `collectible-nodes` |
| **Base Defense** | They Are Billions | `terrain-open` | `tracker-core`, `spawner-npc`, `destructible-cluster`, `cover-los` |
| **Board & Card Games** | Chess, Monopoly; Roblox board games | `board-grid` | `tile-grid` |

**Genre notes**

* **Reference.** [MEDIEVAL REAL TIME STRATEGY](https://www.roblox.com/games/10853515606/MEDIEVAL-REAL-TIME-STRATEGY).
* **RTS may have no path, no AI track, and no hard-coded movement at all.** Units path dynamically toward whatever they're attacking across open terrain. There is no winding enemy lane to build, so don't generate one — bases are distributed symmetrically instead.
* **The core base reframes between styles.** In tower defense it sits at the literal end of one enemy path, so it only needs defending from one approach. In RTS it's the fixed heart of a player's own territory with no lane funnelling attackers, so it has to be defensible from every direction.
* **RTS placement is rule-gated, not grid-gated.** Buildable land is usually constrained by proximity — must be near your own structures, can't be too close to an enemy's — rather than by a narrow strip flanking a lane.
* **Why the track inverts the pipeline.** A tower defense lane has to be one valid continuous route or the game doesn't function. An image can't guarantee that, so the lane is generated procedurally first and dressed after.
* **Roblox's own subgenres here are Board & Card Games and Tower Defense**, both presets above. *Board & Card Games* has the smallest layout job of anything in this document — a table, a board, and seating — and could reasonably route to P5 if the board is a UI surface rather than physical geometry.
* **Two IDs are shared with other genres but written locally.** `tile-grid` also appears in Party & Casual and `collectible-nodes` in five other genres. The ID is the dedupe key; the wording here is Strategy's own, because a contested ore site and an RPG herb patch are not described the same way even though a mixed-genre menu should only offer one of them.

---

## **11\. Survival**

*Threat evasion, disaster survival, and mascot horror.*

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `arena-contained` | **BoundaryZone (Contained Arena)** | A clearly bounded space the round plays out in, keeping the threat and the player in meaningful proximity. | |
| `warren-looping` | **Path (Looping Warren)** | Architecture built on interconnected circles with **zero dead ends**, so a fleeing player is never artificially cornered by pathfinding AI. | `P6` |
| `world-biomes` | **Zone (Biome World)** | Regions whose threat level scales with distance or depth. | `P4` |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `hazard-kill` | **HazardZone (The Threat)** | The thing being survived as a damaging region — a scripted disaster volume, a spreading hazard, a kill zone. | ● | `image` | |
| `spawner-npc` | **Spawner (Hostile Origin)** | The thing being survived as hostile AI — where it enters and the ground it patrols. | ● | `layout` | |
| `cover-los` | **Cover (Crawlspaces & Lockers)** | Small localized cutouts built into lower walls where players break enemy sightlines and hide. **Minimum 4 studs on the entry axis** (Part I §2). | ● | `image` | |
| `destructible-cluster` | **Destructible (Collapsing Structures)** | Multi-part buildings held together by structural welds so disaster scripts can realistically bring them down. | | `image` | |
| `collectible-nodes` | **Collectible (Survival Resources)** | Gatherable wood, stone, and ore for players building against the threat. | | `layout` | |
| `terrain-tiered` | **Zone (High Ground Relief)** | Raised safe spots to climb when the ground floods, burns, or collapses. | | `image` | `P0 + tiered` |
| `gate-escape` | **Gate (Escape Exit)** | Large structural doors or escape hatches set into the outer boundary, acting as the round-win trigger. | | `both` | |
| `building-interior` | **Zone (Enterable Shelter)** | Buildings players flee into and hide inside. | | `image` | `P3` |
| `buildzone-plot` | **BuildZone (Player Base Ground)** | Open buildable land where players raise shelters and fortifications against the threat. | | `image` | |
| `spawn-protected` | **SpawnZone (Role Assignment Points)** | Separated start points for asymmetric roles, so the hunter and the hunted don't begin on top of each other. | | `layout` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **1 vs All** | Flee the Facility, Survive the Killer (Roblox); Dead by Daylight | `warren-looping` | `cover-los`, `gate-escape`, `spawn-protected` |
| **Escape** | Piggy (Roblox) | `warren-looping` | `gate-escape`, `cover-los`, `building-interior` |
| **Disaster Survival** | Natural Disaster Survival (Roblox) | `arena-contained` | `hazard-kill`, `terrain-tiered`, `destructible-cluster` |
| **Horde Defense** | Left 4 Dead, Killing Floor | `arena-contained` | `spawner-npc`, `destructible-cluster`, `cover-los` |
| **Resource Survival** | [Booga Booga](https://www.roblox.com/games/11729688377/Booga-Booga) (Roblox); Rust | `world-biomes` | `collectible-nodes`, `buildzone-plot` |

**Genre notes**

* **Reference.** Natural Disaster Survival for the disaster bundle.
* **Disaster survival has no exit, and that's the whole distinction.** The arena is periodically engulfed by scripted events and players survive *in place* using high ground, cover, and collapsing structures. **The win is outlasting the timer, not reaching an escape.** Adding an exit gate breaks the mode.
* **Boundaries.** Resource/Base Survival overlaps heavily with the RPG Open World & Survival bundle — they're near-duplicates, so pick one. Chase horror versus Puzzle escape room: the pressure is a pursuing threat, not a locked door.
* **The threat can be a region or an actor, and they're different builds.** A damaging volume needs a shape and a boundary; patrolling AI needs an origin and navigable ground. Build's original version only described the chase case and missed disaster survival entirely.
* **Zero dead ends is a hard topology property.** A single cornered corridor makes a chase game unfair, and a free image won't guarantee loop connectivity — hence the procedural-first route.
* **Roblox's own subgenres here are 1 vs All and Escape**, both presets above. *1 vs All* is the asymmetric-roles case — one player is "it" — which needed `spawn-protected` so the hunter and the hunted don't start on top of each other. The genre had no way to express separated role spawns.
* **Disaster Survival deliberately has no escape gate.** It is the one preset here whose win condition is a timer rather than an exit, so `gate-escape` is absent on purpose rather than by oversight.

---

## **12\. Sports**

*Stadium events, team court and field sports, and physics-based athletics — soccer, basketball, baseball, tennis, cricket.*

Regulation fields are fixed templates, so parametric placement of a known field spec generally beats free image generation — a **P6-lite** generator choice rather than a routing change.

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `field-bounded` | **Zone (Bounded Field or Court)** | A rigid geometric perimeter — foul lines, touchlines, baselines — defining the active area, with teams competing inside it. | |
| `range-directed` | **Lane (Directed Range)** | A single directed lane or range replacing a foul perimeter entirely, with a discrete target at the end — bowling, golf, archery, darts. | |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `trigger-bounds` | **TriggerZone (Play / Foul Boundary)** | A detection perimeter built so a script can pause or reset play the microsecond a player or ball crosses it. | ● | `both` | |
| `startpoint-play` | **StartPoint (Play-Start Position)** | Pre-determined static positions the ball or players reset to in order to initiate play — pitcher's mound and home plate, centre circle, serve box. | ● | `both` | |
| `trigger-scoring` | **TriggerZone (Scoring Target)** | Volumes or coordinate planes engineered to register points — crossing home plate, entering a goal mouth, passing through a hoop's invisible cylinder. | ● | `both` | |
| `spectator-zone` | **SpectatorZone (Team Sector)** | Dugouts, benches, and sidelines outside the boundary housing inactive players, coaches, and team assets. | | `image` | |
| `marker-distance` | **Marker (Distance Markers)** | Visual cues built into the field denoting spatial progress — yard lines, painted outfield distances. | | `image` | |
| `barrier-perimeter` | **Barrier (Stadium Enclosure)** | The outer wall closing the stadium off and containing balls and players. | | `image` | |
| `spectator-bleachers` | **SpectatorZone (Atmospheric Bleachers)** | Large tiered seating framing the outer perimeter, grounding the player's camera, giving scale, and visually enclosing the map. | | `image` | `P0 + tiered` |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Field Sport** | FIFA, Madden; Football Fusion 2 (Roblox) | `field-bounded` | `trigger-bounds`, `startpoint-play`, `trigger-scoring`, `marker-distance` |
| **Court Sport** | NBA 2K; Roblox basketball games | `field-bounded` | `trigger-bounds`, `trigger-scoring`, `startpoint-play` |
| **Target Sport** | Golf, bowling; Super Golf! (Roblox) | `range-directed` | `trigger-scoring`, `marker-distance` |
| **Physics Sport** | Rocket League | `field-bounded` | `trigger-scoring`, `barrier-perimeter`, `startpoint-play` |
| **Full Stadium** | Any of the above, dressed | `field-bounded` | `spectator-bleachers`, `barrier-perimeter`, `spectator-zone` |

**Genre notes**

* **Target sports don't fit the field model at all.** Bowling, golf, archery, and darts have no foul perimeter and no scoring plane — they have a directed range and a target at the end. Two of the three field-sport staples simply don't apply, which is worth watching: if a third such variant appears, Sports is really two genres.
* **Dugouts are a stadium-build feature, not a sport feature.** An informal pitch or a street court needs none of it. Build's original version required team enclosures of every sports game.
* **Bleachers are the genre's most common source of tiered elevation.** Stepped seating is relief with no overhang, so it stays P0 — but the height has to be captured or the stadium builds completely flat.
* **Field specs are known quantities.** Regulation dimensions are public and fixed, which makes parametric placement more reliable than asking an image model to invent a tennis court.
* **Roblox files Sports and Racing as two subgenres of one Sports & Racing genre.** This document splits them into genres 12 and 13 instead, because Racing routes P6 and Sports is a parametric template — they share a taxonomy label but almost nothing about how they generate.
* **The scoring options are nearly all `both`.** A goal mouth is visible geometry and an invisible detection plane at the same time, which makes Sports the genre where the drawn/placed distinction shows up most often within single options.

---

## **13\. Racing**

*Speed, forward translation, and a designated route from a start point to an end point — foot races, swimming laps, horse racing, vehicle driving.*

**Genre route: `P6`.** The track must read as one continuous connected route, legible from plan view, with no broken or ambiguously self-crossing segments. A free image can't guarantee that, so the route is laid out procedurally first and dressed after.

**Shape — pick one.**

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `route-point-to-point` | **Path (Point to Point)** | A course that starts in one place and ends in another — downhill, drag, sprint, single-swimmer. | `P6` |
| `route-circuit` | **Path (Lap Circuit)** | A closed loop run a set number of times. | `P6` |
| `route-multitier` | **Path (Multi-Tier Circuit)** | A circuit whose sections cross above or below other sections of the same course. | `P6 + P2` |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `startpoint-line` | **StartPoint (Start Line)** | The defined position the race begins from — a single marker or a lane slot. | ● | `both` | `P6` |
| `lane-corridor` | **Lane (Lateral Corridor)** | Dividers explicitly marking the allowed corridor of movement — lane ropes in a pool, chalk lines on a track, painted edges on a circuit. | ● | `image` | `P6` |
| `trigger-finish` | **TriggerZone (Terminal Finish)** | A dedicated detection zone at the exact end of the course housing the round-ending trigger — a pool touch-pad wall, a finish line tape, a finish gate. | ● | `both` | `P6` |
| `spawn-grid` | **SpawnZone (Multi-Lane Starting Grid)** | A wide standardized launch front of evenly spaced slots — blocks in a pool, lanes on a track, grid spots on a circuit — so racers align side by side and launch simultaneously without colliding. | | `both` | |
| `trigger-lap` | **TriggerZone (Lap / Split Detection)** | Detection regions at key intervals and turnarounds for split times, lap counting, and checking a runner didn't cut across the field. | | `layout` | |
| `barrier-guardrail` | **Barrier (Physical Guardrail)** | Walls and rails that actually block the racer, as opposed to painted lane markings that only indicate. | | `image` | |
| `path-turnaround` | **Path (180° Turnaround)** | A boundary wall or curved track element forcing a clean direction reversal to begin another lap. | | `image` | |
| `marker-distance` | **Marker (Pacing Markers)** | Visual increments along the lateral boundaries giving an immediate sense of distance covered and relative speed. | | `image` | |
| `spectator-zone` | **SpectatorZone (Trackside Stands)** | Viewing areas outside the corridor for eliminated or waiting players. | | `image` | |
| `hazard-kill` | **HazardZone (Off-Track Penalty)** | Water, gravel, or fall-away edges punishing racers who leave the corridor. | | `image` | |
| `checkpoint-respawn` | **Checkpoint (Course Recovery Point)** | Points a wrecked or fallen racer is restored to, with position, orientation, and zeroed velocity. | | `layout` | |
| `volume-open` | **Zone (Open Play Volume)** | Racing through a volume rather than across a surface — swimming lanes, flight circuits. | | `image` | `CHECK` — fine over one framed surface as a play-height envelope; `P2` only if the volume self-occludes |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Circuit Racing** | Mario Kart; Ultimate Driving (Roblox) | `route-circuit` | `spawn-grid`, `trigger-lap`, `barrier-guardrail`, `path-turnaround` |
| **Sprint / Drag** | Drag racing, track sprints | `route-point-to-point` | `startpoint-line`, `lane-corridor`, `trigger-finish` |
| **Downhill Descent** | Descenders, SSX | `route-point-to-point` | `hazard-kill`, `marker-distance`, `checkpoint-respawn` |
| **Obstacle Race** | Speed Run 4 (Roblox) | `route-point-to-point` | `hazard-kill`, `trigger-finish`, `checkpoint-respawn` |
| **Swimming Lanes** | Olympic swimming | `route-point-to-point` | `lane-corridor`, `trigger-finish`, `path-turnaround`, `volume-open` |

**Genre notes**

* **Boundaries.** Racing vs Obby: the racer competes on speed across a finite track or lap count; the obby player takes discrete jumps at their own pace. Racing vs Infinite Runner: the racer controls their own speed and the course ends. Racing vs Vehicle Sim: **if there's no lap and no finish, it's Simulation.**
* **The route failure mode is real and observed.** The reference case (`isometric_i`) produced a track that crossed itself illogically through tunnels and bridges with no followable route. This is the entire reason Racing inverts the pipeline.
* **Coherence applies to A→B courses too.** It's tempting to think only circuits need validating, but a point-to-point downhill still has to read as one followable route in plan view.
* **Lane markings and barriers are different things.** A chalk line indicates a corridor; a guardrail physically stops you. Both are common, they're often both present, and only the second blocks movement.
* **Detection zones are exempt from the global CanTouch rule.** Finish and lap triggers are gameplay detection regions, so Part I §4's blanket `CanTouch = false` doesn't apply to them.
* **Roblox files Racing as a subgenre of Sports & Racing.** Split out here as genre 13 — see the Sports notes for why.
* **Checkpoints were missing.** Every vehicle and obstacle race needs a recovery point that restores position, orientation, and zeroed velocity, and the option only existed under Obby. Now shared.

---

## **14\. Infinite Runner**

*Automated forward translation, reaction timing, and surviving a procedurally generated endless path.*

**Genre route: `P6`.** Procedural by nature — the layout is chunk rules, not a fixed map. Obstacle spacing must be elastic (`spacing = CurrentSpeed × 0.5 s` of reaction time) so every emitted sequence stays clearable as the player accelerates.

**Shape — pick one.** This is the genre's real fork, and it changes the chunk geometry.

| ID | Shape | What it is | Pipeline |
| :---- | :---- | :---- | :---- |
| `lane-snap` | **Lane (Fixed Lane Snap)** | Rigid parallel lanes, typically three, each the avatar bounding box plus a 2-stud safety margin so lateral dashes snap instantly without clipping geometry. | `P6` |
| `lane-free` | **Lane (Free Lateral Steering)** | Continuous lateral movement across a corridor instead of discrete lane slots. | `P6` |

**Options** — combine freely on top of the chosen shape.

| ID | Option | What it is | Core | Goes to | Pipeline |
| :---- | :---- | :---- | :--: | :---- | :---- |
| `chunk-modular` | **Chunk (Deterministic Segment)** | Modular track segments whose exit pivot matches the next segment's origin pivot on a single axis, preventing progressive geometric drift over a long run. | ● | `image` | `P6` |
| `hazard-kill` | **HazardZone (Run-Ending Hazard)** | Whatever ends the run on contact — a train, a pit, a pursuing threat. | ● | `image` | |
| `obstacle-jump` | **Path (Jump Obstacles)** | Barriers to hurdle and gaps to clear as the lanes scroll past. | ● | `image` | |
| `obstacle-moving` | **Path (Moving Obstacles)** | Traffic, swinging hazards, and lane-crossing objects timed against the player's speed. | | `image` | |
| `trigger-despawn` | **TriggerZone (Cleanup Volume)** | A volume set a fixed distance behind the camera that recycles cleared geometry out of the world. | | `layout` | |
| `barrier-horizon` | **Barrier (Horizon Occlusion)** | Atmospheric fog or a sharp turn at the end of the chunk queue, masking the fact the next piece of world is spawning from nothing. | | `image` | |
| `collectible-nodes` | **Collectible (Coin Trails)** | Pickup runs laid along lanes to bait players into riskier lines. | | `layout` | |
| `powerup-buffs` | **PowerUp (Run Boosts)** | Magnets, shields, and speed boosts that alter a stretch of the run. | | `layout` | |
| `marker-distance` | **Marker (Distance Feedback)** | Environmental increments giving a sense of how far the run has gone. | | `image` | |

**Presets** — show the generic name, not the reference.

| Preset | Modelled on *(internal)* | Shape | Options |
| :---- | :---- | :---- | :---- |
| **Lane Runner** | Subway Surfers | `lane-snap` | `chunk-modular`, `collectible-nodes`, `obstacle-moving` |
| **Free Runner** | Temple Run | `lane-free` | `chunk-modular`, `obstacle-jump`, `hazard-kill` |
| **Chase Runner** | Temple Run, Crash Bandicoot boulder runs | `lane-free` | `hazard-kill`, `obstacle-moving`, `barrier-horizon` |
| **Endless Climber** | Doodle Jump | `lane-free` | `obstacle-jump`, `collectible-nodes` |

**Genre notes**

* **Boundaries.** Forward motion is automatic and the path is endless. If the player controls their own speed, it's Racing; if they control their own movement over discrete jumps, it's Obby.
* **Lane snap versus free lateral is the genre's real fork.** Subway Surfers snaps between three fixed lanes; Temple Run steers continuously. They produce different chunk geometry, and the 3-lane assumption shouldn't be applied to both.
* **Spacing must be elastic, not fixed.** Players accelerate the further they get, so a gap authored in fixed studs becomes unclearable later in the run. Everything is derived from current speed against reaction time.
* **Chunk pivots are the thing that breaks silently.** If exit and origin pivots don't match exactly on one axis, the track drifts a little per chunk and the run degrades over minutes rather than failing visibly.
* **Scope caveat on the cleanup volume.** It's a placed volume, so it's arguably layout, but its justification is runtime memory management. Kept here framed by *placement* — how far behind the camera it sits — rather than by the memory concern, which is Mechanics.
* **Roblox files Runner as a subgenre of Obby & Platformer, not as its own genre.** Kept separate here because a runner routes P6 with elastic speed-derived spacing and shares almost none of its generation with a difficulty-chart obby. The skill should still recognise "runner" arriving as an obby request, since that is the wording Roblox's own taxonomy teaches creators.

---

## **15\. Entertainment (Showcase & Hub)**

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

---

## **Themes List**

* **Sci-Fi / Cyberpunk:** Neon lighting, metallic surfaces, industrial tech.  
* **High Fantasy:** Stone, wood, torches, natural landscapes, glowing magic.  
* **Modern Urban:** Asphalt, concrete, contemporary street props.  
* **Post-Apocalyptic:** Overgrown foliage, rusted metal, debris, broken structures.  
* **Horror:** Dim lighting, heavy fog, aged wood, distressed textures.  
* **Stylized / Toon:** Oversaturated colors, soft lighting, playful oversized assets.

---

# **Appendix — Wiring Layout to Gameplay**

Primitives marked **mechanic** in the vocabulary are wired to gameplay behavior by a separate functional game framework (the mechanic wiring is out of scope for this document — these rules only define the layout role and name). This appendix captures guidance that spans that layout/gameplay boundary, independent of which framework does the wiring.

* `ControlZone` **vs plain regions.** `ControlZone` is a capacity/occupancy area with an indicator (KotH-style). Plain regions that only need entry/exit detection are `TriggerZone`s. Never conflate the two.  
* `Gate` **and** `HazardZone` **are composites.** A `Gate` is a `Button` or `TriggerZone` plus moving geometry and logic; a `HazardZone` is entry-detection plus damage logic. Author them from their component primitives, not as a single mechanic.  
* **Player spawns are not a wired mechanic.** `SpawnZone` / `SpawnPoint` are Roblox `SpawnLocation`s coordinated by the engine/player layer.  
* **Layout can lead the mechanics.** `BuildZone` (Tycoon plots), `SocialZone` (town/lobby), and `Chunk` (procgen) are meaningful layout roles even where no reusable mechanic exists for them yet.  
* **Functional pickups and areas are options, not requirements.** `Collectible`, `CaptureZone`, `PowerUp`, and `ControlZone` appear as pickable options in the genres that commonly use them. Whether a given game needs one is the user's pick, not a rule this document imposes — which is what the whole of Part II now assumes.
