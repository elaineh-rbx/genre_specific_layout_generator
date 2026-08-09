# Family sweep findings

## Fragmented families

### 1. Play-as-an-animal (22 prompts)
`P0022 P0023 P0024 P0026 P0027 P0028 P0029 P0030 P0031 P0032 P0033 P0034 P0035 P0036 P0037 P0038 P0039 P0040 P0041 P0179 P0307 P0322 P0405`
Split: roleplay-avatar-sim x15, survival x3, simulation x2, adventure x2, puzzle x1.
You spawn as an animal and roam a big natural map; whatever verb the user attached (surviving, earning coins, escaping) outvoted the animal premise.

### 2. Keyboard Escape maps (13 prompts)
`P0090 P0095 P0103 P0170 P0175 P0176 P0177 P0178 P0184 P0185 P0398 P0410 P0586`
Split: obby-platformer x6, puzzle x5, simulation x1, (none) x1.
One well-known map, a giant keyboard crossed while a speed stat climbs; "escape" routed it to puzzle, "stages" to obby-platformer, and the Arabic P0398 to Incremental Simulator. Overlaps the known "+1 Speed" family.

### 3. Hide-and-seek / tag (17 prompts)
`P0074 P0075 P0076 P0077 P0078 P0079 P0080 P0081 P0082 P0083 P0084 P0085 P0251 P0265 P0267 P0269 P0277`
Split: party-casual x14, survival x2, obby-platformer x1.
Same round loop of one seeker versus hiders; the three outliers (P0267, P0269, P0277) differ only in dressing — monsters, a giant, an obby skin.

### 4. Wave / horde defense (12 prompts)
`P0263 P0264 P0281 P0298 P0341 P0342 P0344 P0348 P0350 P0351 P0352 P0355`
Split: shooter x8, survival x2, strategy x1, entertainment x1.
Escalating enemy waves against a fixed position; whether the user mentioned a gun, a turret, a "survival" framing, or only the lobby (P0348) decided the genre.

### 5. Horror escape: dark building, keys, one monster (12 prompts)
`P0155 P0157 P0158 P0159 P0166 P0171 P0172 P0179 P0182 P0183 P0224 P0483`
Split: puzzle x6, survival x5, roleplay-avatar-sim x1.
Identical loop — explore a locked building, collect keys, avoid the entity — routed to survival/Escape when the monster was emphasised and puzzle/Escape Room when the keys were.

### 6. Pet hatching and collecting (13 prompts)
`P0100 P0323 P0324 P0325 P0326 P0327 P0328 P0329 P0331 P0332 P0416 P0428 P0546`
Split: simulation x8, roleplay-avatar-sim x4, obby-platformer x1.
Eggs, rarities, zones, trading; "adopt/care for" went to roleplay-avatar-sim and "hatch/collect" went to simulation, though the game is the same.

### 7. Blox Fruits / anime island RPG (9 prompts)
`P0007 P0021 P0306 P0310 P0314 P0315 P0316 P0320 P0321`
Split: rpg x7, adventure x1, simulation x1.
Sea-of-islands progression with fruit powers and bosses; P0316 ("exact replica of the blox fruits first sea") read as pure exploration, and P0315 got a Tycoon preset despite being an open-world action RPG.

### 8. Steal-a-Brainrot base collectors (8 prompts)
`P0282 P0304 P0324 P0390 P0427 P0428 P0543 P0593`
Split: simulation x5, adventure x1, puzzle x1, rpg x1.
Grab a creature from the world or another player's plot, run it back to your base, earn passive income; the "find/run" verb pulled P0427 and P0543 out of simulation.

### 9. Open-world crime / GTA (7 prompts)
`P0220 P0283 P0287 P0288 P0291 P0566 P0587`
Split: roleplay-avatar-sim x3, simulation x2, adventure x1, action x1.
City, cars, cops and robbers, jobs; a genuine four-way split with nothing distinguishing the members.

### 10. Bike and motocross trick sims (6 prompts)
`P0372 P0379 P0399 P0406 P0617 P0623`
Split: racing x3, simulation x3.
P0372 and P0406 both ask explicitly for "MX Bikes" freestyle physics and landed in different genres — the cleanest single piece of evidence in the sweep.

### 11. Free-roam driving (not racing) (7 prompts)
`P0371 P0374 P0376 P0411 P0553 P0614 P0615`
Split: simulation x4, racing x3.
Cruise a city, buy cars at a dealership, drift on an open lot; no laps or finish line anywhere, yet three went to racing/Circuit Racing.

### 12. Dungeon / floor crawlers (6 prompts)
`P0004 P0006 P0020 P0300 P0305 P0529`
Split: rpg x3 (Dungeon Crawler), action x3 (Hack & Slash).
Sequential rooms or floors, clear enemies to open the next gate, boss at the end; loot and stats sent it to rpg, combat feel sent it to action.

### 13. Battle royale (6 prompts)
`P0043 P0044 P0045 P0046 P0047 P0268`
Split: shooter x4, party-casual x2.
P0043 and P0044 are the lobby and shop for the same Fortnite-style build as P0045, and were separated from it because they described only menus.

### 14. Tower climb (6 off-genre prompts)
`P0516 P0518 P0521 P0526 P0529 P0531`
Split: obby-platformer x2, action x3, (none) x1.
Against ~14 tower obbies sitting in obby-platformer, "avatar tower" (P0518) got no genre while its twin P0526 got obby, and "slaps tower" (P0531, obby) sits opposite "Slap Tower" (P0516, action).

### 15. RNG / gacha rollers (6 prompts)
`P0212 P0409 P0448 P0497 P0502 P0504`
Split: strategy x3, simulation x1, sports x1, (none) x1.
Press roll, get a rarity, collect the set; the theme wrapped around the roll — basketball, tower units, auras — decided the genre every time.

### 16. Room and house decorating (5 prompts)
`P0227 P0401 P0402 P0407 P0419`
Split: simulation x2, roleplay-avatar-sim x2, (none) x1.
P0401 and P0402 are near-identical; one got simulation/Sandbox, the other no genre at all, so this boundary is unstable, not merely blurry.

> Correction (checked against the source rows): P0401 and P0402 are not verbatim
> identical. They match character-for-character for their first 716 characters —
> the whole game description — and P0402 then appends "Do not ask any clarifying
> questions. Make any reasonable creative decisions yourself and build the
> complete, playable game now." They were also scored by different lanes
> (batch-10 and batch-38), so the differing outcome cannot be attributed to that
> sentence. What survives is stronger than the original claim: both lanes wrote
> in their notes that no genre in the index describes a furnishing game, and
> then diverged on whether to fall through to no-genre or force a
> classification. The gap is agreed; only the remedy is unspecified.

Lower confidence: superhero city traversal (`P0009 P0293 P0294 P0301 P0302`; action x3, obby x1, (none) x1) may be two things — power fantasy and movement tech — not one. Backrooms is nearly intact in survival (`P0147 P0148 P0149 P0162 P0163`), with only `P0585` leaking to entertainment.

## Dumping grounds

**simulation.** Absorbs anything with a currency or upgrade loop: `P0315` (open-world action RPG, given a Tycoon preset), `P0398` (keyboard-escape obby, given Incremental Simulator), `P0101` (jump-for-height platformer), `P0402` (room decorating), `P0406` (motocross physics), `P0593` (steal-a-brainrot). Tycoons, clickers, vehicle sims, farming, mining and destruction sandboxes also live here, so the label carries almost no shared layout meaning.

**(none).** Beyond genuine bare-map requests (`P0573 P0576 P0588 P0597`), it swallows fully-specified games with obvious homes: `P0401` (room decorator), `P0448` (RNG roller), `P0518` (tower obby), `P0236` (match-3), `P0337` (Jenga), `P0335` (skateboard sim), `P0554` (Dolphin Olympics clone), `P0558` (social hangout, near-identical to `P0559`, which got roleplay-avatar-sim).

**roleplay-avatar-sim / Morph Roleplay.** Holds dress-up and animal RP alongside `P0287` and `P0291` (GTA-style crime), `P0218` (Prison Life), `P0224` (haunted-school horror) and `P0217` (office sim); the only common factor is "you have an avatar and a place".

**entertainment.** Used when a prompt has no clear win condition rather than when the game is entertainment-shaped: `P0348` (zombie wave-defense lobby), `P0442` (a +1 Speed reskin), `P0585` (backrooms), `P0198` (a forest to walk in).

## Suggested new genres

**idle-progression / "+1 stat" runner.** Family 2 plus the non-keyboard members `P0389 P0394 P0397 P0442 P0536`, spread over obby-platformer, puzzle, simulation, entertainment and racing. Would claim ~18. The defining shape is a stat that ticks up as you traverse, gated barriers, and rebirth, none of which the obby or puzzle presets model.

**horror-escape.** Family 5 plus the backrooms five, currently split between survival/Escape and puzzle/Escape Room. Would claim ~16. Both presets already exist and describe one game; merging them removes a coin flip.

**animal-sim.** Family 1, currently across five genres. Would claim ~22. A first-class genre with a hunger/thirst option would stop the survival-flavoured ones leaving.

**collection-sim (pets, eggs, brainrots).** Families 6 and 8. Would claim ~19. Base plot plus rarity ladder plus zones is a distinct layout, not a generic simulator.

**open-world-crime.** Family 9. Would claim ~7 — the smallest proposal, worth making only because the split is total.
