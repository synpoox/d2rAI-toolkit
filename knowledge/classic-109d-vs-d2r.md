# Classic 1.09d against D2R 3.3: rules the engine code changed

Gameplay rules that changed in engine **code** between Lord of Destruction 1.09d and D2R 3.3 build 93847, which the
1.09d tables alone cannot bring back. This is the engine work list for a port that wants 1.09d behaviour. Skills,
missiles and AI are in [classic-109d-engine.md](classic-109d-engine.md); table schemas in
[classic-109d-tables.md](classic-109d-tables.md). A port's own choices (which rules it restores, which values it picks)
stay in the port.

## Evidence

- **Verified** rows come from Ghidra on the stock 1.09d DLLs (hashes in
  [classic-reference-installs.md](classic-reference-installs.md)), on 1.13c's `D2Game.dll`, and on a memory dump of
  D2R build 93847 ([engine-re.md](engine-re.md)). Nothing was run in game.
- **Unverified** rows come from patch notes and community knowledge (the 1.10 beta change list, community wiki copies
  of the 1.10 to 1.13d notes, Blizzard's D2R patch posts 2.4 to 3.3). They name a rule that changed, not where.
- 1.09d addresses are RVAs in `D2Game.dll` (base `0x6fc30000`) or `D2Common.dll` (base `0x6fd40000`). D2R addresses
  are RVAs of build 93847. Size: S under one session, M one to two, L three or more (estimates).
- `data` = fixable with the 1.09d tables plus the schema transform. `code` = needs a plugin. `both` = values plus code.

## Rule table

| Rule | 1.09d | D2R 3.3 (build 93847) | Kind | Evidence | Size |
|---|---|---|---|---|---|
| Skill synergies | none | per-skill synergy calcs | data | schema ([tables](classic-109d-tables.md)) | S |
| Skill damage per level | 3 brackets (`LevDam1-3`) | 5 brackets, min and max split | data; the 1.09d bracket boundaries were not read from code | schema | S |
| Skill and missile function bodies | one function per skill, id inside | one generic function per behaviour driven by columns | code, largest item | [engine file](classic-109d-engine.md): 156 different and 48 not settled of 319 skills (115 same) | L |
| Experience penalty from level 70 | none | `ExpRatio` curve | data | `experience` has no `ExpRatio` in 1.09d | S |
| Life and mana leech | rounded integer percent | 1/64 fixed point | both | [Life and mana leech](#life-and-mana-leech) | S |
| Item events (crushing blow, open wounds, knockback) | hard-coded in `D2Game` | `itemstatcost` `itemevent*` / `itemeventfunc*` | both | schema; see the next two rows | M |
| Crushing blow | `0xb44f0`, stat 136, via the SkillItem stat-event table `0x6fd1e3f8` | event 16 `0x583150`, body `0x581bd0` through the jump slot `0x3e2a448` | probably none; the D2R body was not decoded | below | S |
| Open wounds | `0xb43e0`, stat 135 | event 15 `0x584170` | code | below | S |
| Physical damage-reduction cap | 75 | 50 | code, one byte | [Damage reduction cap](#damage-reduction-cap) | S |
| Quality roll and magic find | ratio formula, MF diminished 250 / 500 / 600 above 10 | the same | none | below | none |
| `UniqueMin` / `SetMin` / `RareMin` / `MagicMin` | never read | chance raised to the Min | data: write 0 | below | S |
| Unique and set roll per item type | skipped for types whose Rare flag is 0 (charms) | rolled for every type; only rare is gated | code (or data) | below | S |
| Gambling odds | rand(100000): 92000 magic, rare to 99988, set to 99998, unique 99999 | `difficultylevels` `GambleRare` / `Set` / `Unique` | data: 8000 / 10 / 1 | below | S |
| Affix level, rare affix count | the 1.10 formulas already | the same | none | below | none |
| Monster level in Nightmare and Hell | monstats `Level(N)` / `Level(H)`; no champion or unique bonus found | area level; champions +2, uniques +3 (unverified in D2R code) | code (hook the monster init) | below | M |
| Monster stats | absolute monstats values | monlvl value times a monstats percent | both | [tables](classic-109d-tables.md) | S with the level hook |
| IAS / FCR / FHR / FBR / FRW | diminishing constants 120 / 120 / 120 / 120 / 150, rates 15-175 | the same constants | none | below | none |
| Dual-wield attack rate | base + avg(WSM A, WSM B) - WSM A | average of the two full rates (2.4) | code | below | S |
| Extra attack-rate stat 213, shapeshift cap | none, cap 175 | stat 213 added; cap 250 | code | below | S |
| Werewolf and Werebear frames | D2Common `0x6fa90` (not decoded) | 2.4 formula | code | not decoded | S-M |
| Lower Resist and Conviction against immune monsters | full effect | 1/5 | code | unverified | S-M |
| Cold Mastery against immune monsters | no effect | applies (1/5 after an immunity is broken, 2.6) | code | unverified | S |
| Reduce Defense, Ignore Target Defense on bosses | flat; ITD works on bosses | percentage, halved on bosses; ITD ignored by super uniques, act bosses, hirelings | both | unverified | S |
| Block lock, block speed | blocks can chain | block cooldown scales with block speed; 2.4 blocking no longer interrupts | code | unverified | M |
| Interruptibility | 1.09d rules | 2.4: Werebear attacks and Impale uninterruptible, no one-frame interrupt window | code | unverified | S-M |
| Hit recovery request window | not checked | the server allows the next request at 1 frame left (`0x42d700`); PvP hit recovery diminishes (2.4) | code | one mod's finding for D2R; vanilla 1.13c value not established | S |
| Casting delay | not checked | 2.4: not shared between skills | code | unverified | S |
| Monster HP by player count | 1.09d formula | 1.10 formula (more HP in one-player games, smaller rise per player) | both | unverified | S |
| Monster AI | 1.09d functions, one parameter set for every difficulty | 1.10+ functions, faster decisions in Nightmare and Hell | both | [engine file](classic-109d-engine.md) | L |
| Unique monster mods triggering each other | yes | 2.5: no | code | unverified | S |
| Experience back on corpse recovery | 50 % (Nightmare, Hell) | 75 % | code | unverified | S |
| Hirelings | no gear requirement check; own leash, revive cost, regen, hire level | 1.10 gear requirements; 1.11 level within 1-5 of the character; 2.4 hired at the character's level, class skill bonuses, fixed damage bonus; 1.13d several auras; 2.5 Act V swings twice | code (stats are data) | unverified | M |
| Pets and summons | 1.09d | 2.4: no hidden random HP, several summon types at once, pets teleport to the player | both | unverified | S |
| Werewolf and Werebear switching | through human form | 2.7: direct | code | unverified | S |
| Assassin traps | 1.09d scaling | 2.7: benefit from +% elemental skill damage; 2.6 -% enemy resistance | code | unverified | S |
| Item generation limits | 1.09d rules | 1.10+: quality caps, no items above requirement level 99, item skills give lower levels to classes that have the skill | both | unverified | M |
| Treasure classes for guest monsters | 1.09d | 1.10: recomputed at the guest's new level | both | unverified | S |
| Town portal past unfinished quests | allowed | blocked (Tristram, Canyon, Durance, Worldstone Keep, cows); 2.4 Compelling Orb for Durance | code | unverified | S |
| Quest items | not auto-identified; lower-difficulty items accepted | auto-identified on drop; refused across difficulties | code | unverified | S |
| Skills persisting in town | persist | end on entering town | code | unverified | S |
| Atma heals | no | heals on talk | code | unverified | S |
| Ancients experience | uncapped | capped at one level | code | unverified | S |
| Respec | none | free respec after Den of Evil; Token of Absolution (1.13) | code and data | unverified | S |
| Stash gold cap | rises with level | 2.5M flat since 1.13; shared stash holds gold | code | unverified | S |
| Late-added content: Uber Tristram, Pandemonium, Diablo Clone, Hellfire Torch | none | present from 1.11 | data (inert without the recipes) | unverified | none |
| Terror Zones, Sunder Charms, Heralds, Colossal Ancients | none | D2R 2.5 and later | code and data, switched by settings and tables | unverified | S |
| 2.3 and 2.6 skill fixes | 1.09d | Telekinesis no longer needs line of sight and overlapping Fire Wall/Blaze no longer stack (2.3, both in shared code, see the [engine file](classic-109d-engine.md)); auras no longer remove a skill's own passives, Blessed Aim no longer overwrites Penetrate, Fire Mastery boosts Enchant, Strafe and Power Strike apply their attack rating (2.6) | code | unverified | with the skill diff |
| Monster immunity in Hell | resist 100 or more is immune | the same | data | unverified | none |

## Item generation, gambling and breakpoints (verified)

- **Quality roll.** 1.09d does it inline in the treasure-class drop function `0x1f250` (Items.cpp). 1.13c `0xfc40` and
  D2R `0x4421b0` use the same formula: chance = (ratio - (ilvl - qlvl) / divisor) * 128, less the TC's per-quality
  ratio / 1024, then `rand(chance) < 128`. Magic find is diminished above 10: unique 250*MF/(250+MF), set 500, rare 600,
  magic not diminished. The 1.09d magic find curve is the one D2R uses.
  - 1.09d **never reads the `*Min` columns** of itemratio; 1.13c and D2R raise the chance to at least Min. Write 0 in
    every Min column and D2R's clamp gives the 1.09d result (1.09d applies the TC ratio before MF and D2R after it, so
    integer rounding differs by at most one).
  - **Item-type gate.** 1.09d skips unique, set and rare together when the itemtypes Rare flag (1.09d record `+0x19`)
    is 0. D2R rolls unique and set for every type and gates only rare (`+0x15`). 1.09d has no unique or set charm, so
    in D2R a charm that wins the unique roll falls back to whatever D2R makes of a failed unique (not checked). Fix in
    code, or set the charm types' Rare flag in data if the fallback is harmless.
- **Gambling.** 1.09d `0x88760` (SUNITNPC.CPP) takes `r = rand(100000)`: magic below 92000, rare 92000-99988, set
  99989-99998, unique 99999. That is 7.989 % rare, 0.01 % set, 0.001 % unique. 1.13c `0xbe2a0` and D2R use
  `difficultylevels`: unique if `r < GambleUnique`, set below `GambleUnique + GambleSet`, rare below `GambleRare`.
  `GambleRare` 8000, `GambleSet` 10, `GambleUnique` 1 reproduce 1.09d exactly on every difficulty. The gamble item level
  (clvl - 5 + rand, clamped 5-99) and the first two slots offering a ring and an amulet are the same.
- **Affix level.** 1.09d `0x20540` (ItemsMagic.cpp) already has the formula usually credited to 1.10: ilvl = max(ilvl,
  qlvl). Without `magic lvl`, alvl = ilvl - qlvl/2 if ilvl < 99 - qlvl/2, else 2*ilvl - 99; with it, alvl = ilvl + magic
  lvl; clamped 1-99. **Rare affix count**, 1.09d `0x20a00`: 3 + rand(4) affixes, jewels (type 58) 3 + rand(2), at most
  3 prefixes and 3 suffixes, each slot a 50/50 pick. D2R's copy was not disassembled. A failed set becomes magic with
  doubled durability and a failed rare becomes magic (`0x1adb0`, cases 5 and 6).
- **Monster level.** 1.09d `0x29710` (Monster.cpp) sets the level stat from monstats `Level` / `Level(N)` / `Level(H)`
  (record `+0x1c4` + difficulty). Hit points come from `MinHP` / `MaxHP` of that difficulty plus the player-count
  bonus, with no monlvl lookup. The area level (`levels.MonLvl*`, D2Common ordinal 11247) is used only for Act V
  summoned minions (`0x337f0`) and object drops (`0x1e5d0`). Champions and uniques get no extra level. In 1.10 and
  later, Nightmare and Hell normal monsters take the area level (champions +2, uniques +3); that is from community
  sources and the D2R site was not located. The item level of every Nightmare and Hell drop changes with it, and with
  it every TC and quality roll, so a port that wants 1.09d drops needs a hook on D2R's monster init.
- **Breakpoints.** 1.09d's animation-rate function is D2Common ordinal 10376 (`0x6f390`); its constants table at
  `0x6fdc2038` holds five rows {diminish flag, constant, three stat ids}: attack 120 (stats 92-94), hit recovery 120
  (98-100), cast 120 (104-106), block 120 (101-103), walk/run 150 (95-97), each diminished as c*x/(c+x). Rates:
  attack = `attackrate` + EIAS (dual-wield adds avg(weapon A, weapon B) - weapon A; sequence mode 18 takes -30; clamp
  15-175, times the mode's base rate / 100); cast = 100 + EFCR, at most 175; hit recovery = 50 + EFHR; block = 50 + EFBR
  (100 + EFBR with state 101, Holy Shield); run/walk = velocity + EFRW, at least 25. 1.13c `0x33110` matches branch for
  branch, so 1.09d and 1.10 breakpoints differ only through data (WSM, animdata, skill IAS). D2R `0x350b40` differs:
  dual-wield averages the two full rates (each with that weapon's stats), stat 213 (`0xd5`) is added, and the cap
  rises from 175 to 250 under state 39 plus a further check. The 1.09d shapeshift frame path (D2Common `0x6fa90`) was
  not decoded.
- **Crushing blow, 1.09d `0xb44f0`.** `rand(100) < CB`; blow = target life / 4, divisor 10 when the target is a
  player, hireling or boss/champion (`0x6fc617d0` / `0x6fc61810`), doubled when the event's melee flag is 0; less the
  target's `damageresist` %, capped at 100; life is set to life - blow with the kill flag 0. D2R event 16 `0x583150`
  makes the same roll and passes {4, 10, 10, missile} to `0x581bd0`, whose body (via jump slot `0x3e2a448`) was not
  decoded. The 1.10 fix "works at the stated chance" is not in this function.
- **Open wounds, 1.09d `0xb43e0`.** On `rand(100) < OW`, a timed `hpregen` (stat 74) of -(9*clvl + 40), halved on players
  and bosses, with state 62, through the timed-stat helper `0xbbf30` (length 100 frames as passed; units not checked).
  D2R event 15 `0x584170` uses a piecewise level curve: 9*clvl + 31 below level 16, then 18*clvl - 104, 27*clvl - 374,
  36*clvl - 779 and 45*clvl - 1319 from 61; divides by 8 on players for melee and by 4 otherwise; halves on some
  monsters.

## Damage reduction cap

1.09d `0x7e350` (SUnitDmg.cpp) loops a 12-row resist chart at `0x6fd03858` {damage field, resist stat, max-resist
stat, ...}. For players and hirelings the cap is `75 + max-resist stat`, at most 95. Physical `damageresist` (stat 36)
has no max stat, so it is capped at **75**. 1.13c `0xdb3c0` and D2R `0x4523e0` take `50` when the max stat is -1 and the
stat is 36. The one-byte patch site (`0x4524d0`, 13 bytes to byte-check) and the patch value are in
[d2r-93847-addresses.md](d2r-93847-addresses.md) "Damage reduction cap"; this file does not repeat them. Whether a
port keeps 75 is the port's choice; 75 is the 1.09d fact.

## Life and mana leech

- **1.09d** `D2Game` `0x6fcaf4a0` (SUnitDmg.cpp): leech applies when the **target is a monster** that has monstats
  `CanStealFrom` set (byte `+0x1c7`). The leech percent is integer-divided by the difficulty record's life or mana steal
  divisor (`+0x28` / `+0x2c`, asserted next to `nMonsterColdDivisor`): `pct / divisor`, then `damage * pct / 100`. The
  divided fraction is dropped: 3 % life steal with a divisor of 2 gives 1 %. The divide is on the monster branch only,
  whoever attacks; a player hitting a player leeches the plain percent.
- **1.13c** `0x6fcfba40` and **D2R** `0x450c90`: the percent is first shifted `<< 6` (1/64 fixed point), multiplied by
  the monster's per-difficulty `Drain` byte (1.13c record `+0xa0`, D2R `+0xf2`), then divided by the difficultylevels
  divisors (D2R record `+0x1c` / `+0x20`); in D2R the divide is for a **player attacker** only. 3 % in Nightmare
  steals 1.5 %.
- **Data side.** `Drain` is 100 or 0 from `CanStealFrom`; the divisors are the difficulty rows. The difference to
  1.09d is the fraction and which attackers divide, and matters only in Nightmare and Hell.
- **Restoring 1.09d's rounding** needs an entry hook on `0x450c90` that hands D2R's own code a percent whose 1/64 steps
  end where 1.09d's integer step ends; the hook, the percent formulas per attacker and target, and the damage-block
  fields to write back are in [d2r-93847-addresses.md](d2r-93847-addresses.md) "Life and mana leech". D2R's add-life
  `0x451820` is called from the leech.

## Gaps

1. No per-function diff of skill and AI code beyond the [engine file](classic-109d-engine.md).
2. The 1.09d werewolf/werebear speed path (`0x6fa90`) and the per-class frame tables were not decoded.
3. D2R's bodies for the failed-unique fallback, the crushing-blow jump-slot target and the rare affix count were not
   disassembled; the D2R monster level and HP init site was not located.
4. Whether the 1.09d `.txt` `*Min` columns hold non-zero values was not checked (writing 0 is correct either way).
5. Official text for 1.11 to 1.13d (secondary summaries only) and D2R 2.3, 3.0 and 3.1 was not read.
