# Ask merge — `mechanics` + `constraint`

757 clusters / 1223 asks → ~150 concepts; 63 have total ≥6, covering ~1037 asks (85%).
Dest: **M** mechanics, **C** constraint, **x** split. Merged-from truncated with "…".

## Top concepts

|Concept|Tot|D|Merged from|What it is|
|---|---|---|---|---|
|Player vehicle / mount|52|M|vehicle(22), player vehicle(10), rideable vehicle(4)…|Player drives it|
|Round timer|44|M|round timer(29), match timer(8), phase timer(2)…|Round countdown|
|Avatar identity|38|x|animal avatar+custom avatar(7), player avatar(4), playable species(3)…|Who the player is|
|Photorealistic art|34|C|photorealistic style(5), realistic style(3), photorealism(2)…|Must look real|
|Combat & damage|29|M|combat system(5), melee combat(2), damage model…|How hitting works|
|Enemy roster|28|M|enemy type(8), enemy roster(4), creature roster(3)…|Which enemies exist|
|Movement ability|27|M|movement ability(5), flight movement(3), dash ability(2)…|Non-walk traversal|
|Reference game / clone|24|C|reference game(10), game reference(7), existing game clone(4)…|"Like \<named game\>"|
|Platform target|24|C|platform support(13), mobile support(5), cross platform(2)…|Phone/console support|
|Pet / companion|24|M|pet companion(11), pet creature(2), pet follower(2)…|Follows you around|
|Player count|23|x|player count(19), server size(2), player count cap…|Humans per server|
|Weapon loadout|22|M|weapon loadout(6), player weapon(3), starting weapon(3)…|Weapons you get|
|Camera, POV unstated|22|x|camera mode(6), camera perspective(5), camera control(2)…|Camera value missing|
|Multiple maps|21|C|map rotation(6), multiple map(4), themed map set(3)…|More than one map|
|Art spec, axis unstated|21|C|art direction(3), render style(2), detail level(2)…|Style direction vague|
|Avatar cosmetics|21|M|avatar customization(6), avatar customizer(2), character aura(2)…|Skins and glows|
|True-3D requirement|19|C|3d requirement(7), three dimensional(4), 3d build(2)…|Not a 2D board|
|Procedural generation|19|C|procedural generation(4), placement system(2), random room…|Generate, don't place|
|Control scheme|19|x|control scheme(6), keyboard binding, tilt steering…|Button mapping|
|Player abilities|19|M|super power(3), ability loadout(3), cooldown system(2)…|Active powers|
|Multiplayer mode|18|x|multiplayer support(3), co-op play(2), single player rule…|Shared world or not|
|Roles & teams|18|M|player role(4), team assignment(4), hidden role(2)…|Asymmetric roles|
|Performance budget|18|C|performance budget(9), performance target(4), streaming radius…|FPS/part ceiling|
|Enemy waves|17|M|enemy wave(4), wave schedule(4), wave count(3)…|Waves and ramp|
|Save / persistence|17|M|save system+progress save(12), data persistence(2)…|Progress survives|
|Vehicle handling|17|M|crash death(2), trick system(2), drift mechanic…|Vehicle behaviour|
|Win condition|16|M|win condition(8), last player standing(3), victory state(2)…|How matches end|
|Generator directives|16|C|code quality, clean error console, target engine…|Orders to builder|
|Map size|15|C|map size(6), map extent, arena dimension…|Explicit dimensions|
|Originality|15|C|original asset(4), originality constraint(4), original asset rule(3)…|Must be original|
|Game modes|15|M|game mode(8), story mode, endless mode…|Named modes|
|Boss encounter|14|M|boss encounter(6), boss enemy(4)…|A boss fight|
|Ambient NPC|14|M|pedestrian npc(2), npc wander ai…|Non-hostile NPCs|
|Random events|14|M|random event(6), world event(2)…|Fires unprompted|
|Physics tuning|14|x|ball physics(3), ragdoll physics(2)…|Physics feel|
|Gravity override|13|x|low gravity(2), zero gravity(2)…|Player physics changed|
|Respawn rules|13|M|respawn rule(2), respawn timer(2)…|What death does|
|Scope limit|13|C|scope limit(5), build scope(3)…|Don't build more|
|IP / licensing|13|C|licensed ip(3), copyright avoidance…|Rights limits|
|Third-person camera|12|M|third person camera(7), chase camera(3)…|Camera behind player|
|Stylised art|12|C|low poly style(4), greybox style…|Deliberately cheap|
|Character animation|12|M|character animation(7), dance emote…|Rigged motion|
|First-person camera|11|M|first person camera(8), first person view(3)|Camera in head|
|No clarifying questions|11|C|no clarifying questions+no questions(8), no questions rule…|"Don't ask, build"|
|AI opponent|11|M|ai opponent(4), ai bot(2)…|Computer opponent|
|Asset sourcing|11|C|asset sourcing(2), official asset only…|Asset provenance|
|Cutscene|10|M|cutscene+spawn cutscene(5), intro sequence…|Scripted sequence|
|Minimal / no UI|10|C|no 2d ui, no gui only, no world text…|No GUI wanted|
|Content rating|10|x|content rating(2), no gore…|Age limits|
|Mesh over parts|10|C|custom mesh requirement, mesh over part…|Meshes not blocks|
|Round flow|10|M|round cadence, match state machine…|Phases of a round|
|Matchmaking|8|M|matchmaking(4), tournament bracket(2)…|Entering a match|
|House building|8|M|house decorating, growing base…|Placing structures|
|Destructible geometry|8|x|collapse detection(2), deformable terrain…|Geometry breaks|
|Held tool|8|M|held tool, tool pickup…|Item in hand|
|Walkspeed tuning|8|x|movement speed(2), speed multiplier…|Numeric speed change|
|Chasing enemy|7|M|chase enemy, chase monster, chaser npc…|Something hunts you|
|Difficulty curve|7|C|difficulty ramp(3), difficulty level…|Difficulty and ramp|
|Story|7|M|story script(2), narrative goal…|A plot|
|Endless world|7|C|open world(2), endless extent…|No boundary|
|Replay camera|7|x|replay camera(3), photo mode(2)…|Camera as feature|
|Team size|6|x|team size(3), team count…|Players per side|
|NPC dialogue|6|x|npc dialogue(2), quiz question…|NPC speaks|

Held out of the camera merge, under 6: **fixed camera**(4), **top-down/isometric**(4).

## Negative constraints

**29 asks carry an explicitly negative label** (no X, ban, exclusion). Counting
prohibition-shaped labels too (restriction, limit, only, prevention, avoidance) gives
**68**, 5.6% of asks; almost all are `constraint`.

The strict 29:

- **Orders to the generator, 11** — `no clarifying questions`/`no questions`/`no
 clarifying question`(8), `no questions constraint`, `no questions instruction`, `no
 questions rule`. The single most common prohibition.
- **UI and world text, 6** — `no 2d ui`, `no ui constraint`, `no gui only`, `no gui
 geometry`, `no world text`, `text-free build`.
- **Whole features removed, 5** — `no enemies`, `no free roam`, `building mechanic
 ban`, `content exclusion`+`feature exclusion`(2), `excluded system`.
- **Gore, 3** — `no gore`, `no gore constraint`, `gore ban`. **Geometry, 2** — `no
 baseplate`, `no interior`. **Monetisation, 1** — `no dark pattern`.

The broad 68 adds: scope caps, 12 (`scope limit` 5, `build scope` 3, `scope
restriction`…); asset and IP bans, 9 (`asset restriction`, `official asset only`,
`original ip only`, `copyright avoidance`…); "only" limits, 4 (`map only build`,
`single map`, `decorative only`…); emptiness, 2 (`empty map`, `empty play space`);
gameplay caps, 7 (`spam limit`, `fall prevention`, `theft immunity`, `axis lock`…);
minimal UI, 4 (`clean hud`, `minimal interface`…); content bounds, 4 (`content
rating` 2, `age rating`, `language constraint`).

Most forbidden: **scope expansion 12**, **clarifying questions 11**, **UI and text
10**, **third-party assets and IP 9**, **gore and mature content 7**, **named gameplay
systems 5**.

## Player identity and movement

**~102 asks (8.3%)** say the player is not a stock Roblox avatar or does not move
like one.

**Identity, 38.** Non-default bodies, 23: `animal avatar`+`custom avatar`(7),
`playable species`(3), `playable animal`(2), `playable creature`(2), `avatar morph`(2),
`cat avatar`, `sphere avatar`, `monster character`, `player drone`… Rig, scale, hitbox,
9: `player scale`(2), `avatar rig type`, `character rig`, `player hitbox`, `miniature
scale`, `ragdoll body`… Unresolved, 6: `player avatar`(4), `avatar requirement`,
`avatar skin rule`. Only `default avatar`(2) asserts the default.

**Player is a vehicle, 16.** `player vehicle`(10), `rideable vehicle`(4), `mount`,
`mount riding`. Generic `vehicle`(22) holds more, inseparable by label.

**Movement, 48.** Flight and gliding 10 (`flight movement`(3), `space flight`, `glide
control`, `flap control`, `aerial traversal`…); dash, parkour, sprint 14 (`movement
ability`(5), `dash ability`(2), `slide ability`, `parkour movement`, `dive
mechanic`…); walkspeed 9 (`movement speed`(2), `speed boost`(2), `walk speed`, `speed
multiplier`…); gravity 4 (`low gravity`(2), `zero gravity`(2)); grapple 2 (`grapple
ability`, `grapple gun`); jump and fall tuning 5 (`jump movement`, `fall damage`, `fall
speed limit`, `landing tolerance`, `floor grounding`); movement replaced entirely 3
(`turn-based movement`, `click to move control`, `axis lock`).

**Essentially all 102 invalidate geometry validated against a default avatar.** By
severity: **gravity (4)** breaks jump height; **walkspeed (9)** and **dash/parkour
(14)** break jump distance; **flight (10)** and **grapple (2)** make gap validation
meaningless; **non-humanoid bodies (23)** plus **rig/scale/hitbox (9)** change stride,
jump power and collision volume together. Worst is the **16 vehicle-player** asks:
a car cannot clear a validated jump gap at all.

## Notes on merging

Unsure merges, all reversible from the label lists above:

- **Photorealism vs. stylised** are opposite ends of one axis, kept apart (34 / 12),
 with direction-neutral labels (`art direction`, `render style`) in a third bucket
 of 21. As one concept it would be 67.
- **`vehicle`(22)** surely splits between the player's vehicle, NPC traffic and set
 dressing. Merged into Player vehicle on the strength of `player vehicle` and
 `rideable vehicle`, but it is impure.
- **`camera mode`(6)** and **`camera perspective`(5)** name the axis, not the value, so
 they form a bucket of 22 rather than inflating first- or third-person.
- Not merged: `player count`(19) with `team size`(6) or `server size`(2). And
 `avatar customization` stays out of avatar identity; a skin picker changes no physics.

**The 27% variance looks worse here, not better.** `chasing enemy` is the proof: seven
workers produced `chase enemy`, `chase entity`, `chase monster`, `chaser npc`, `chasing
enemy`, `chase speed ratio`, `stalking presence` — seven names, zero collisions, one
concept. `no questions` arrived under four labels, photorealism under twenty-three,
true-3D under seven. 590 of 757 clusters (78%) had total 1; merging on meaning
collapses that tail by about two-thirds. Raw counts understate frequency several-fold
for any concept lacking a canonical phrase, and barely at all for the few that have one
(`round timer`, `player count`, `save system`).
