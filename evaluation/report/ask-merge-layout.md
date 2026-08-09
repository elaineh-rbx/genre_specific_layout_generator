# Layout / image ask consolidation

942 clusters (1386 asks) regrouped into **70 concepts**; **61** reach 8+, covering 1277 asks (92%). "Merged from" shows only the two largest labels; the word cap forces heavy truncation.

## Top concepts

| Concept | Total | Merged from | What it is |
|---|---|---|---|
| Interior rooms | 52 | building interior, room count… | walk-in interiors |
| Water body | 50 | water body, open water, river… | lakes, rivers, sea |
| Settlement | 49 | city block, town, village cluster… | cities, towns, houses |
| Biome / themed zone | 45 | biome zone, themed zone… | map split into regions |
| Stage + show lighting | 40 | performance stage, stage lighting… | stage venue |
| Forest / vegetation | 35 | forest, tree cluster, flower field… | trees, plants |
| Shop / vendor | 33 | shop building, shop counter… | retail buildings |
| Player spawn | 31 | spawn point, player spawn… | where players appear |
| Combat arena | 31 | boss arena, pvp arena… | enclosed fight space |
| Island / archipelago | 29 | island, island landmass… | land ringed by water |
| Traversal anchors | 29 | grapple anchor, grind rail… | movement geometry |
| Job / activity station | 27 | job station, minigame station… | interactable spot |
| Interactive NPC | 27 | quest npc, npc vendor… | talk-to characters |
| Enemy NPC | 26 | enemy npc, boss creature… | hostile placement |
| Ambient NPC crowd | 26 | npc character, crowd npc… | background population |
| Vehicles & transit | 26 | vehicle prop, traffic car, rail track… | cars, trains, docks |
| Goal / checkpoint | 25 | checkpoint, exit, finish line… | run markers |
| Decorative prop | 24 | themed prop set, street furniture… | set dressing |
| Collectible / loot chest | 24 | treasure chest, currency pickup… | pickups |
| Non-flat terrain | 23 | natural terrain, rolling hill… | hills, cliffs, pits |
| Interior furniture | 23 | bed, interior furniture… | furniture |
| Wildlife | 22 | wildlife, farm animal… | creatures |
| Customization station | 22 | wardrobe station, morph station… | change-look spot |
| Training / target range | 22 | shooting range, target dummy… | practice range |
| Build zone / grid | 22 | placement slot, build zone… | where players build |
| Signage / branding | 22 | billboard, signage, brand logo… | signs, logos |
| Screen / display board | 21 | video screen, achievement display… | in-world screens |
| Ground material | 21 | mud terrain, surface condition… | ground surface |
| Objective / quest key | 20 | objective station, key item… | mission targets |
| Entity spawner | 19 | vehicle spawn, vehicle spawner… | non-player spawns |
| Road network | 19 | road, city street, lane count… | drivable streets |
| Ambient light fixture | 19 | flickering light, street light… | lamps, glow |
| Underground / cave | 18 | cave, cave entrance… | below-surface space |
| Route topology | 18 | dead end, branching path… | how paths connect |
| Race / obstacle course | 18 | floating track, obstacle course… | course to run |
| Multi-floor / rooftop | 18 | multi-story building, tower floor… | vertical stacking |
| Moving geometry | 18 | conveyor belt, moving platform… | animated geometry |
| Interaction trigger | 18 | interaction prompt, mode selector… | press-to-use triggers |
| Lobby / hub | 16 | lobby, lobby hub… | staging space |
| Hazard / trap | 16 | hazard prop, laser hazard… | damaging features |
| Portal to separate area | 16 | teleporter, separate world… | travel elsewhere |
| Real-world / IP reference | 15 | real world location, map replica… | "look like X" |
| Player plot / base | 15 | player base, player plot… | per-player parcel |
| Destructible geometry | 15 | breakable prop, destructible prop… | breakable geometry |
| Arcade / casino machine | 15 | arcade cabinet, spinner wheel… | play furniture |
| Flat baseplate | 14 | flat baseplate, ground plane… | flat ground |
| Turret / defense tower | 13 | tower type, defense tower… | defensive structures |
| Map variant / pool | 13 | map variant, map pool… | several map versions |
| Difficulty tier | 12 | stage count, world tier… | stage count, ramp |
| Seating | 11 | seating, seating area… | somewhere to sit |
| Map boundary | 10 | perimeter wall, boundary wall… | playable edge |
| Secret / hidden area | 9 | secret area, secret room… | concealed space |
| Progression gate | 9 | access gate, upgrade gate… | locked area |
| Particle effect | 9 | particle effect, smoke effect | ambient VFX |
| Maze / corridor | 9 | endless maze, hallway corridor… | corridor interior |
| Statue / monument | 8 | statue prop, landmark statue… | landmark object |
| Safe zone | 8 | safe zone, buff zone, pvp zone… | zone rules |
| Ruined / derelict | 8 | ruined building, debris field… | broken look |
| Park / green space | 8 | park, theme park, fountain… | greenery |
| Elevator | 8 | elevator, queue elevator… | vertical transport |
| Door / window | 8 | window, closable door… | wall openings |

## Concepts worth adding as options

1. **Interior rooms (52)** — which buildings open, room count, named room types.
2. **Water body (50)** — type (still / flowing / sea / underwater), extent, swimmable or barrier.
3. **Settlement (49)** — city / town / village density, block spacing, building count.
4. **Biome / themed zone (45)** — zone count, theme each, adjacency and transition.
5. **Forest / vegetation (35)** — tree density, theme, clearing placement.
6. **Player spawn (31)** — spawn count, placement rule (random / team / per-plot); 28 of 31 asks already `layout`.
7. **Combat arena (31)** — footprint, enclosure, embedded or its own zone.
8. **Island / archipelago (29)** — island count, size spread, separating medium, connected or not.
9. **Non-flat terrain (23)** — relief type (rolling / cliff / chasm) and amplitude; **Flat baseplate (14)** is the opposite setting.
10. **Build zone / grid (22)** — cell size, buildable bounds, blocked regions.
11. **Goal / checkpoint (25)** — checkpoint count and spacing, finish placement.
12. **Road network (19)** — lane count, grid vs organic, drivable width.
13. **Multi-floor / rooftop (18)** — floor count, floor height, roof access.
14. **Underground / cave (18)** — whether a second vertical layer exists, entrance count.
15. **Route topology (18)** — branching factor, dead ends, shortcuts, loop vs linear.
16. **Map boundary (10)** — boundary kind (wall, water, cliff, invisible) and map shape.

**Frequent but not layout.** The NPC family (79 asks: Interactive 27, Enemy 26, Ambient 26) is the second-largest thing here, but layout owes it only anchor points; the characters are content work. **Screen / display board (21)** and **Interaction trigger (18)** are UI and mechanics. **Real-world / IP reference (15)** already carries `constraint` destinations — a moderation question, not geometry. **Decorative prop (24)**, **Interior furniture (23)** and **Signage / branding (22)** are image dressing.

## Notes on merging

**Merges to distrust.** *Water body* absorbs 22 labels including `underwater volume`, `underwater zone` and `beach terrain`; a playable underwater volume is arguably not a surface lake. Sub-variants: still (`lake`, `pond water`), flowing (`river`, `waterfall`), sea (`ocean`, `open water`), shoreline, underwater. *Non-flat terrain* combines `rolling hill`, `mountain terrain`, `boundary cliff`, `chasm gap`, `volcano` and the generic `natural terrain` (4) — split back out if relief type matters. *Settlement* merges city (26) with town/village/houses (23): same concept, different density. *Portal* merges the device (`teleporter`) with the destination (`separate world`, `dungeon instance`).

**Splits that look mergeable.** `spawn point` (players) vs `vehicle spawner` / `loot spawn` (entities) were kept apart deliberately. `safe zone` and `pvp zone` share a row as one knob despite being opposites. Arena, Training range and Race course are all bounded activity spaces and could collapse into one concept of 78.

**Variance is worse than 27%.** 734 of 942 clusters were singletons. Water arrived under 22 distinct names, interiors under 36. Raw counts understate demand by roughly 3–10×. One pattern the labels hide: eleven "count of X" asks (`room count`, `stage count`, `island count`, `plot count`, `zone count`, `lane count`, plus five more; 21 asks) may be one feature, not eleven. About 46 singletons (82 asks) stayed unmerged.
