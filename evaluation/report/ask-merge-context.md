# Non-map asks: merged concepts and proposed context-file fields

632 clusters / 1176 asks merged by meaning into **71 concepts**, **55** with a total of 6+.

## Top concepts

| Concept | Total | Dest | Merged from | What it is |
|---|---|---|---|---|
| Game title & naming | 77 | metadata | game title, place name, boss name, faction name… | Name for the game or an entity |
| Leaderboard / scoreboard | 42 | ui | leaderboard, scoreboard, rank ladder, player ranking… | Ranked list of players |
| Reward / earning rule | 41 | progression | currency reward, coin reward, currency drop, idle income… | How the player earns |
| Currency | 40 | progression | currency, in-game currency, coin currency, premium currency… | A spendable resource |
| Sound effects | 39 | audio | sound effect, sound design, impact sound, engine sound… | Event-triggered SFX |
| Shop & pricing | 36 | progression | shop, cosmetic shop, purchase system, shop price… | Store contents and prices |
| Music / soundtrack | 35 | audio | music, ambient music, original music, adaptive music… | Background score |
| HUD (generic) | 35 | ui | hud, hud overlay, combat hud, player hud… | "Give it a HUD", unspecified |
| Purchase / shop UI | 35 | ui | purchase menu, shop menu, upgrade menu, catalog menu… | Screen you buy from |
| Counters & readouts | 32 | ui | wave counter, kill counter, score display, currency readout… | A number on screen |
| Cosmetics & skins | 31 | progression | cosmetic unlock, avatar skin, cosmetic trail, character outfit… | Appearance-only items |
| Upgrades | 31 | progression | upgrade, speed upgrade, tool upgrade, unit upgrade… | Buyable improvements |
| Lighting mood | 28 | sky | darkness, night lighting, dynamic shadow, dramatic lighting… | A fixed lighting look |
| Weather | 28 | sky | weather system, weather cycle, weather event, rain weather… | Precipitation and storms |
| Main menu / lobby | 27 | ui | main menu, menu screen, start button, loading screen… | Pre-play navigation |
| Score & scoring rule | 26 | progression | score, score tracking, scoring rule, drift scoring… | What earns points |
| World-space markers | 25 | ui | minimap, compass indicator, objective marker, floating text… | Markers over the world |
| Loot crate / gacha | 24 | progression | crate, egg hatching, loot box, gacha roll… | Randomised container pull |
| Rarity & drop tables | 21 | progression | rarity tier, loot rarity, unit rarity table, loot table… | Tiers and drop odds |
| Health & status bars | 21 | ui | health bar, boss health bar, hunger meter, energy meter… | A depleting bar |
| Day / night cycle | 20 | sky | day night cycle, time of day, night time, lighting change | Cycle, or a fixed hour |
| Customization UI | 20 | ui | character select menu, avatar editor, outfit editor, colour picker… | Build your look |
| Unlock gating | 19 | progression | gear unlock, weapon unlock, hidden unlock, unlock requirement… | What is locked, by what |
| Ambient soundscape | 17 | audio | ambient sound, ambient audio, ambient soundscape, crowd noise | Environmental audio loop |
| Inventory | 16 | progression+ui | inventory, player inventory, inventory panel, carry capacity | Held items and their screen |
| Rebirth / prestige | 15 | progression | rebirth system, rebirth reset, prestige reset, rebirth multiplier… | Reset-for-multiplier loop |
| Daily & seasonal rewards | 15 | progression | daily reward, daily streak, battle pass, seasonal event… | Time-gated rewards |
| Economy (generic) | 14 | progression | economy, currency economy, tycoon economy, resource economy… | "An economy", unspecified |
| Mobile controls | 14 | ui | mobile button, touch control, mobile joystick, virtual thumbstick | Touchscreen input |
| UI styling / scale | 14 | ui | hud layout, hud sizing, ui scale, polished interface… | How the UI looks |
| Roster (ownable units) | 14 | progression | unit roster, team roster, pet roster, starter unit… | Units you own or field |
| Quests & missions | 13 | progression | quest, daily quest, quest board, mission system… | Assigned objectives |
| Fog | 13 | sky | fog, volumetric fog, atmospheric fog, ground fog… | Fog density and colour |
| Settings menu | 13 | ui | settings menu, control binding, input mapping, privacy toggle… | Options screen |
| Collection / index | 13 | progression | collection book, collectible set, collection log, creature collection | Pokédex-style set |
| Pre-match selection | 13 | ui | map select menu, team selection, difficulty select, spawn menu… | Choosing before a round |
| Voting | 12 | ui | player voting, map vote, difficulty vote, voting panel… | Players vote |
| Results screen | 12 | ui | result screen, win screen, victory screen, replay screen… | End-of-round screen |
| Story & lore | 12 | metadata | story beat, story premise, game lore, multiple endings… | Narrative content |
| Timer / countdown | 11 | ui | countdown timer, timer display, round timer display, run timer | A clock on screen |
| Trading | 10 | progression | trading, player trading, item trading, gift exchange… | Player-to-player exchange |
| Levels & XP | 10 | progression | experience level, level cap, level progression, experience table… | XP curve and ceiling |
| Skybox | 10 | sky | skybox, cosmic skybox, starry skybox, sunset sky… | The sky's appearance |
| Dialogue UI | 10 | ui | dialogue choice, dialogue text, dialogue prompt, subtitle caption… | On-screen written lines |
| Stats | 9 | progression | stat system, speed stat, luck stat, damage value table… | Named numeric attributes |
| Store listing | 9 | metadata | game thumbnail, game description, concept art, store tag… | Roblox listing assets |
| Achievements & badges | 8 | progression | badge, collectible badge, achievement, achievement set | One-off awards |
| Gamepass monetization | 8 | progression | game pass, gamepass, gamepass perk, gamepass paywall… | Robux-gated content |
| Crafting & resources | 8 | progression | crafting, crafting system, resource gathering, worker hiring | Inputs into outputs |
| Progression tree | 8 | progression | skill tree, tech tree, research tree, class system… | Branching unlock tree |
| Starting loadout | 8 | progression | starting loadout, starter unit, starting currency, starting capital | What you begin with |
| Notifications & feeds | 8 | ui | announcement feed, notification toast, kill feed, warning popup… | Transient messages |
| Tutorial & hints | 8 | ui | tutorial, no tutorial, hint system, tutorial overlay… | Onboarding, incl. "none" |
| Action buttons | 6 | ui | action button, ability button, attack button, skill button | Ability-firing buttons |
| Difficulty scaling | 6 | progression | difficulty tier, wave difficulty, difficulty escalation, wave gate | How hard it gets |

**Related-but-not-identical merges, flagged so they can be undone.** *Leaderboard* = global rankings (30) + live in-match scoreboards (6) + rank ladders (4). *Reward rule* = passive income (~8) + per-action currency drops (~22) + event payouts (~11). *Health bars* = literal health (13) + survival meters, i.e. hunger/thirst/energy/happiness (5). *World-space markers* = maps (5) + navigation markers (6) + targeting reticles (5) + floating text (7). *Day/night cycle* = a moving cycle (15) + a fixed hour (5). *Cosmetics* = avatar cosmetics (~24) + vehicle customization (3) + trails/auras (3).

## Proposed context-file fields

**progression — ~470 asks (40%)**
- `currencies[]` — `{name, kind: soft|premium, starting_amount}`, ~40.
- `earning_rules[]` — `{trigger: kill|wave|win|idle|offline|pickup, currency, note}`, ~41.
- `shop` — `{sells[], price_note, stock_rotation}`, ~36; also drives the shop screen.
- `upgrade_targets[]` — speed, tool, tower, unit, weapon, room — ~31.
- `cosmetics[]` — `{slot, unlock_method}`, ~31.
- `unlockables[]` — `{thing, gate: level|currency|gamepass|hidden|wave}`, ~19 + 8 gamepass.
- `rarity` — `{tiers[], drop_odds_note}`, ~21. `loot_containers[]` — `{form: crate|egg|gacha|spin, cost, pool}`, ~24.
- `scoring` — `{metrics[]: distance|drift|trick|damage|kills, formula_note, multipliers}`, ~26.
- `reset_loop` — `{kind: rebirth|prestige, multiplier_note}`, ~15.
- `recurring_rewards[]` — `{cadence: daily|streak|season|battle_pass, reward}`, ~15.
- `xp` — `{level_cap, curve_note}`, ~10. `stats[]` — named attributes, ~9.
- Small lists/flags, ~8–16 asks each (~105 total): `quests[]`, `collection`, `roster[]`, `crafting`, `progression_tree`, `starting_loadout`, `achievements[]`, `trading`, `inventory.capacity`, `difficulty_curve`.
- `economy_note` — free text, for the 14 bare "give it an economy" asks.

**ui — ~330 asks (28%)**
- `hud.elements[]` — the highest-value field here. Enum: `health_bar`, `currency`, `score`, `timer`, `wave_counter`, `kill_counter`, `objective_counter`, `minimap`, `stamina`. Covers HUD-generic (35), counters (32), status bars (21), timers (11) ≈ **99 asks**.
- `screens[]` — enum + note: `main_menu`, `shop`, `inventory`, `settings`, `results`, `character_customization`, `pre_match_select`, `voting`, `leaderboard`, `chat`, `quest_log` ≈ **175 asks**.
- `world_markers[]` — minimap, compass, objective_marker, range_indicator, crosshair, floating_damage_text, nametag, interact_prompt — ~25.
- `hud.style` — free text: scale, anchor, "polished", screen effects — ~14.
- `controls` — `{mobile, touch_buttons[], rebindable}`, ~20. `dialogue` — `{style: choice|linear, subtitles}`, ~10. `notifications[]`, ~8. `tutorial` — `yes|no|hints_only`, ~8.

**audio — ~94 asks (8%)**
- `music` — `{style_note, adaptive, licensed_or_original, player_ui}`, ~35.
- `sfx[]` — named events: click, impact, pickup, footstep, engine, aggro — ~39.
- `ambience` — `{soundscape_note, crowd, reverb_zones}`, ~17. `voice` — `{lines[], prompts}`, ~3.

**sky — ~99 asks (8%)**
- `time_of_day` — a value (noon/night/sunset) **or** `cycle` with a period, ~20.
- `lighting` — `{mood: bright|dim|dark|dramatic|neon|soft, shadows, color_grade_note}`, ~28.
- `weather` — `{conditions[]: rain|storm|snow|blizzard|ashfall, dynamic, seasonal}`, ~28.
- `fog` — `{density, colour, volumetric}`, ~13. `skybox` — named preset or description, ~10.

**metadata — ~106 asks (9%)**
- `title` — a string; **70 asks alone**, the largest single field here. Plus `entity_names[]` for boss/faction/place/facility names, ~7.
- `story` — `{premise, lore_notes, endings: single|multiple}`, ~12. `description`, `thumbnail`, `tags[]` — Roblox listing, ~9.
- `deliverables[]` — design_document, build_summary, setup_instructions, build_order (~5): the user wanting paperwork, not a game.
- `ip_flags[]` — licensed character, real player likeness (~3): a moderation risk, not a frequent ask.

## What resists structure

About **75 asks (~6%)** fit no field above.

The largest slice is the `unclear` destination (~45 asks), with one shape: **the user described a 3D thing and the worker could not tell whether it belongs to geometry, art, or code.** `character model` (5), `enemy model` (2), `monster appearance`, `monster design`, `playable character`, `held weapon`, `weapon design`, `team kit`, `retexturable surface`, `3d styling`, `interactable object` (2), `tool station`, `pet facility`. These are a routing gap, not context-file material: no "character and creature appearance" destination exists, so they defaulted to `unclear`. That is the clearest signal in the residue — a missing consumer, not unstructurable data.

Second is **behaviour, which is code rather than context**: `npc behaviour rule`, `slap mechanic`, `chase threat`, `escape objective`, `objective item`, `growth mechanic`, `mutation event`, `height value scaling`. Fielding these would just store English.

Third is **meta-requests about the request**: `open brief`, `open ended addition`, `feature parity request` ("make it like X"), `genre convention reference` (2), `power reference`, `second game concept`, `modded variant`, `unclear jargon`. These name no feature; they defer to the generator or to an external game. A `freeform_note` holds them, but nothing downstream consumes it.

The rest of the tail is one-off in wording only: `paint brand`, `crop catalogue`, `par score`, `nation roster`, `engine swap` slot cleanly into `shop.sells[]`, `scoring.metrics[]`, `roster[]`, or `upgrade_targets[]`. So the genuinely unstructurable share is **6%, not the ~35% the raw singleton count implies** — the rest is vocabulary variance, as the 27% inter-worker agreement predicts.
