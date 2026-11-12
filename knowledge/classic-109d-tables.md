# Classic 1.09d tables against 1.13c and D2R

What changed in the `.txt` tables between Lord of Destruction 1.09d and 1.13c (D2R 3.x inherits 1.13c's layout and
widened it). For a port that starts from 1.09d tables. Column-by-column mapping is data: the committed map is
`shared/classic_import/data/109d-to-113c-column-map.json` (per table, per 1.09d column: targets, kind, transform, value
maps) and the flat `109d-to-113c-column-map.tsv` (`table, column_109d, table_113c, column_113c, kind, transform`),
applied by `shared/classic_import/column_map.py`. This file holds the findings behind the map. Engine behaviour is in
[classic-109d-engine.md](classic-109d-engine.md) and [classic-109d-vs-d2r.md](classic-109d-vs-d2r.md). Merging onto
D2R: [porting-classic-mods.md](porting-classic-mods.md) and [tables.md](tables.md).

## Evidence

- **1.09d:** the stock set in [classic-reference-installs.md](classic-reference-installs.md), read in game priority order
  `Patch_D2.mpq`, then `d2exp.mpq`, then `d2data.mpq` (55 tables come from the patch, 90 from `d2exp.mpq`; `d2data.mpq`
  overrides nothing).
- **1.13c:** the 1.13c patch MPQ over the same base `d2exp.mpq` and `d2data.mpq` (1.13c ships only the patch, and the
  base archives are byte-identical to 1.09d's).
- Neither patch MPQ has a usable listfile for the excel folder, so every table name was probed as `.txt` and `.bin`.
- Renames were found by name, case-insensitive name and value similarity of row-aligned columns, then sampled. No
  high-trust page documents the unit change in `SrcDam`; the factor comes from the data alone (below).

## Answer in one page

- **75 `.txt` tables ship in 1.09d and 92 in 1.13c.** No table is 1.09d-only. 17 exist only in 1.13c, and 1.09d's DLLs
  do not contain their names: `compcode events misscalc monai monequip monlvl monplace monpreset monprop monseq
  monsounds monstats2 monumod pettype sets skillcalc skilldesc`. In 1.09d that data is hard-coded or folded into other
  tables. Reproducing 1.09d behaviour there means reading 1.09d code or keeping D2R's rows.
- **42 tables have identical columns** (list below); about 30 change. The big ones: `monstats`, `skills` (159 new
  columns, since 1.09d bound behaviour to skill ids in code), `setitems` (one row per set becomes `sets` plus one
  `setitems` row per item), `itemstatcost` (16 to 53 columns), `missiles`, `levels`, `states` (1 to 72 columns) and
  `uniqueitems`.
- **1.09d references rows by number; 1.13c by name.** `monstats.BaseId/Skill*/Miss*`, `superuniques.Class`,
  `levels.M*/U*/C*`, `missiles.Skill`, `skills.State*`, `charstats.StartSkill` and `itemstatcost.Target Stat` hold row
  numbers in 1.09d and keys in 1.13c. Row keys also changed style: `STATS_STRENGTH` became `strength`, `STATE_NONE`
  became `none`, `ESOUND_*` became lower-case names. The map marks each of these `recode`. **Exception:** 1.09d
  `monstats.BaseId` is the AI table index, not a monstats row number ([engine file](classic-109d-engine.md)); do not
  recode it as a row.
- **`SrcDam` x16.** `skills.SrcDam` and `missiles.SrcDamage` go from eighths (8 = 100 %) to 128ths: multiply by 16.
  The data shows it: 1.09d holds 8, 6, 4; 1.13c holds 128, 96, 64, 48 (Attack is 8 against 128).
- **Damage brackets.** Skill and missile damage per level goes from 3 brackets (`LevDam1-3`, `ELev1-3`) to 5, split into
  min and max.
- **Monster stats become percentages.** `monstats` HP, AC, experience, damage and to-hit (`MinHP` through `S1MaxD`)
  change from absolute values to percentages of `monlvl.txt`. The inverse is 100 x v / monlvl base, rounded, and 1.10
  rebalanced the values anyway, so the conversion is not mechanical.
- **Per-difficulty.** Several level and monster settings became per-difficulty (`(N)` and `(H)` columns). The map copies
  the single 1.09d value into them; that 1.09d did not scale them in code is unverified.
- **Stat ids are stable.** `itemstatcost` ids mean the same in both. Names changed, and 1.10 collapsed the multi-slot
  stats into one stat with a parameter: class skill points (83-87, 179-180), `SINGLESKILL1-3`, `SKILLONATTACK1-3`,
  `SKILLONHIT1-3`, `SKILLONGETHIT1-3` and `CHARGED_SKILL0-9`. 1.13c keeps 1.09d's item save layout in its own
  `1.09-Save Bits` / `1.09-Save Add` columns, identical by id.
- **Row identity.** Rows 0 to n-1 keep their identity in `levels` (133 to 137), `lvlprest` (1090 to 1091), `lvlwarp`,
  `objects`, `objgroup`, `itemtypes`, `weapons`, `armor`, `misc` (139 to 151), `gems`, `automagic`, `rareprefix`,
  `raresuffix`, `magicsuffix` (741 to 747) and `superuniques`. 1.13c only appends there. Those that diverge are in the
  row-shift table below.

## `.bin` is the widened `.txt`

Both versions ship a `.bin` beside nearly every `.txt`. A `.bin` is a `uint32` record count followed by fixed-size
records, with no header. In 1.09d every `.bin` record count equals its `.txt` data-row count, less the `Expansion`
marker row, so the `.txt` is the data the `.bin` was compiled from. `.bin` only: `leveldefs.bin` in both versions,
plus `itemscode.bin` and `misscode.bin` in 1.13c (compiled formula bytecode). `.txt` only (1.09d): `aiparms`,
`monname`, `soundenviron`, `sounds`, `treasureclass`, `weaponclass`. `inventory` and `plrmode` split the other way (a
patch `.txt` over a base `.bin`).

**1.13c's `automagic`, `rareprefix` and `raresuffix` have no `.txt` in any 1.10 to 1.14d patch**; every patch ships the
same `.bin` (`automagic` record 132 to 144 bytes, the rare affixes 60 to 72). The game reads the `.bin`, so the `.bin`
is the data. Each 1.13c record is the 1.09d record with the item-type slots (`itype1-7` plus the etypes) widened from
bytes to words, an empty slot (`0xFF`) becoming `0xFFFF`, and `automagic` gaining one alignment byte. Every other byte
is the same in every row. So 1.13c's `.bin` was compiled from the `.txt` in 1.09d's `d2exp.mpq`, and the map uses that
file as 1.13c's `.txt` for these three tables. Limit: a `.bin` has no header, so this proves the data of every column
the game reads, not header names or columns the compiler skips (comments, `*eol`). 1.13c's `automagic` had no
`etype4` / `etype5` column: a blank etype compiles to 0, as `etype1-3` show, and those two slots hold `0xFFFF`.
Other builds' copies are not 1.13c's: a later community build has more `automagic` rows and adds `etype4` / `etype5`,
and D2R drops `add` / `multiply` / `divide`.

## Table presence

| Status | Tables |
|---|---|
| Both, identical columns | 42 (below) |
| Both, changed | armor, books, charstats, cubemain, difficultylevels, experience, hireling, inventory, itemstatcost, itemtypes, levels, lvlmaze, misc, missiles, monmode, monstats, montype, overlay, plrmode, properties, runes, setitems, skills, sounds, states, superuniques, treasureclassex, uniqueappellation, uniqueitems, uniqueprefix, uniquesuffix, uniquetitle, weapons |
| 1.13c only | the 17 listed above |
| 1.09d only | none |

Same column set (row counts may differ): aiparms, arena, armtype, automagic, automap, belts, bodylocs, chartemplate,
colors, composit, cubemod (13 to 12 rows), cubetype, elemtypes (12 to 13), gamble, gems, hiredesc, hitclass, itemratio,
lowqualityitems, lvlprest (1090 to 1091), lvlsub, lvltypes, lvlwarp, magicprefix (667 to 669), magicsuffix (741 to 747),
monitempercent, monname, npc, objects, objgroup, objmode, objtype, playerclass, plrtype, qualityitems, rareprefix,
raresuffix, shrines, soundenviron, storepage, treasureclass, weaponclass.

## Per-table changes (1.09d to 1.13c)

Row counts are game rows (`.bin` count). "Cols" counts `.txt` headers.

| Table | Cols | Rows | Change |
|---|---|---|---|
| armor, weapons, misc | 158/165/147 to 164/166/168 | 202, 306, 139 to 151 | `sound` (item sound-class number) becomes `dropsound` + `usesound` names; the value map is consistent (6 = `item_cap`, 21 = `item_platearmor`). `misc.namco` becomes `*name`. New: `namestr`, `type2`, `dropsfxframe`, `StrBonus` / `DexBonus` (armor), `questdiffcheck`, the `misc` spell and stat columns |
| books | 11 to 11 | 3 | `SpellOffset` / `SkillScrollOffset` / `SkillBookOffset` (all 0 in 1.09d) become `pSpell` / `ScrollSkill` / `BookSkill`; take 1.13c's values |
| charstats | 63 to 79 | 7 | `StartSkill` number becomes a name. New (hard-coded in 1.09d): `StatPerLevel`, `Skill 1-10`, `StrAllSkills`, `StrSkillTab1-3`, `StrClassOnly` |
| cubemain | 46 to 105 | 99 to 151 | `start day`, `stop day`, `weekday` dropped (unused); `term` becomes `*eol`. New: `ladder`, `op` / `param` / `value`, `output b` / `output c` blocks |
| difficultylevels | 18 to 23 | 3 | `ExtraUniqueMonsters` has no 1.13c home. New: `MonsterCEDamagePercent`, `GambleRare/Set/Unique/Uber/Ultra` |
| experience | 8 to 9 | 101 | New `ExpRatio` (the high-level penalty) |
| hireling | 72 to 73 | 60 to 120 | 1.13c adds `Version` and doubles the rows (0 = classic, 100 = expansion); 1.09d's rows correspond to Version 100. `ChancePerLevelN` becomes `ChancePerLvlN` |
| inventory | 73 | 32 | `gridRows` / `gridCols` become `gridX` / `gridY`, same values |
| itemstatcost | 16 to 53 | 329 to 359 | `Stat` keys lose the `STATS_` prefix. `Save Bits` / `Save Add` become `1.09-Save Bits` / `1.09-Save Add`. `Percent` + `Target Stat` become `op 13` + `op stat1`; `PerLevel` + `PerLevelShift` become `op 2` + `op param`; `ByTime` becomes `op 6`. New: `Send*`, `Saved`, `CSv*`, `fCallback`, `fMin`, `MinAccr`, `keepzero`, `op base`, `op stat2/3`, `direct`, `maxstat`, `itemevent*`, `desc*`, `dgrp*` (descriptions and events were hard-coded) |
| itemtypes | 36 to 37 | 103 | `*eol` only |
| levels | 175 to 140 | 133 to 137 | `M1-8` / `U1-8` (monstats row numbers) become `mon1-8` (copied into `nmon1-8`) / `umon1-8` (monstats Id). `C1-4`, `CA1-4`, `CD1-4` become `cmon`, `cpct`, `camt`. `Mtot`, `Utot`, `S1-25` and slot 5 dropped. `SizeX/Y`, `MonDen`, `MonUMin/Max` copied into `(N)` / `(H)`. New: `QuestFlag`, `QuestFlagEx`, `Teleport`, `NumMon`, `rangedspawn` |
| lvlmaze | 7 to 9 | 79 to 81 | New `Rooms(N)` / `Rooms(H)` |
| missiles | 72 to 171 | 644 to 684 | Damage brackets split as above; `SrcDamage` x16; `Skill` number becomes a name; `Param1/2 Comment` become `*param1/2 desc`; `Open`, `Beta` dropped. New: function and calc columns, `Param3-5`, sound, overlay and sub-missile names, flags (`Town`, `Holy`, `NoMultiShot`, ...) |
| monmode, plrmode, overlay | +1 | same | Case-only renames; new `code` / `Code` / `version` |
| monstats | 239 to 255 | 575 to 734 | 82 graphics and selection columns move to `monstats2` (named through `MonStatsEx`). `Class` becomes `NameStr`, `Descriptor` `DescStr`, `Type` `MonType`. `BaseId`, `Skill1-5`, `Miss*` row numbers become keys (BaseId: see the exception above). `SkillNSeq` becomes `SkNmode` (lookup). `AIParam1-5` become `aip1-5` per difficulty (slots moved: [engine file](classic-109d-engine.md)). `*Resist` become `Res*`, `*ToHit` `*TH`, `e*` flags `lUndead` / `demon` / ..., `El*` `El1*`. Stat block becomes percentages. New: `Id`, `hcIdx`, `NextInClass`, `TransLvl`, `MonProp`, `AI`, spawn / minion / party columns, `MonSound`, `Skill6-8`, `Drain`, `El2/El3`, `TCQuestId` / `TCQuestCP` |
| montype | 18 to 7 | 575 to 59 | **Same name, different table.** 1.09d's is a per-monster direction table (`DT_Dir` ... `RN_Dir`) that becomes `monstats2.dDT` ... `dRN`; 1.13c's is the new type hierarchy (`type`, `equiv1-3`, `strsing`, `strplur`). No `montype.txt` comes out of a 1.09d conversion |
| properties | 8 to 36 | 244 to 268 | Comment columns starred. `ModFuncOffset` (a hard-coded function name) becomes `set/val/func/stat1-7`; take 1.13c's row for the same `code` |
| runes | 47 to 49 | 169 | `*runes` / `eol` added; rows reordered from row 24 |
| setitems (+ sets) | 255 to 94 (+ sets 69) | 32 sets to 32 sets + 127 items | Restructured. `INCode1-2` become `prop1-2`; per-item partial bonuses `INCodeA-E` become `aprop1a-5a` (A = 2 items worn is an **assumption**); `PCode2-5` become `sets.PCode2a-5a`; `FCode1-6` become `sets.FCode1-6`; `transformcolor` becomes `chrtransform` |
| skills | 98 to 256 | 319 to 357 | Brackets as for missiles; `SrcDam` x16. `anim` / `monanim` become mode codes (cast = SC, seq = SQ, attack = A1, throw = TH, kick = KK, aura / none = blank). `State1-3` numbers become names. `isaura` becomes `aura`, `leftskl` `leftskill`, `SearchMonsterNear` `SearchEnemyNear`. `SkillPage/Row/Column/IconCel` move to `skilldesc`. `itemclass1-6` become `itypea/b` (lookup). 159 new columns (functions, aura / passive / summon blocks, calcs, sounds, overlays, `maxlvl`, `restrict`, ...) |
| sounds | 25 | 4698 to 4699 | `Handle` (`ESOUND_X`) becomes `Sound` (lower-case) |
| states | 1 to 72 | 160 to 185 | 1.09d has only the name column; all state behaviour was hard-coded. Two shared rows were repurposed (97, 111) |
| superuniques | 13 to 21 | 66 | `Class` row number becomes an Id. New: `Superunique` key, `hcIdx`, `MonSound`, `Replaceable`, `Utrans*` |
| treasureclassex | 33 to 33 | 774 to 853 | `SumDrop` / `Better` (spreadsheet calcs) become `group` / `level` |
| uniqueitems | 55 to 70 | 384 to 401 | `name` becomes `index`, `completed` `enabled`, `Level` / `LevelReq` `lvl` / `lvl req`, `ItemModN*` `prop/par/min/maxN`, `transformcolor` (colors row) `chrtransform` (colors code; 14 = `dyel`). New: `ladder`, `nolimit`, `carry1`, `prop11-12`, art and sound columns |
| uniqueappellation / prefix / suffix / title | 37/38 to 1/2 | same | 1.09d's `MonType1-36` restrictions are dropped |

## Row shifts (compare on the key, not the number)

The game numbers rows without the `Expansion` marker row. Compared on the key column (case and prefix normalised).

| Table | 1.09d to 1.13c | Shared rows that differ |
|---|---|---|
| skills | 319 to 357 | 311, 312 renamed (`mon inferno sentry` / `mon death sentry`); otherwise identical, new rows appended |
| states | 160 to 185 | 97 (`ITEMFULLSET` to `skel_mastery`), 111 (`STATE_111` to `golem_mastery`) |
| itemstatcost | 329 to 359 (by `ID`) | the multi-slot stats (83-87, 107-109, 179-213, 323-326 shuffled) |
| missiles | 644 to 684 | 30 renamed rows from 32 (`Andrial` to `andarielspray`, ...); not individually confirmed to be the same missile |
| monstats | 575 to 734 | 333 (`unused` to `Diablo`); 8 `Code` changes (244-246, 333, 435, 520, 568-569) |
| uniqueitems | 384 to 401 | 286 renamed, then **301 onward shifted** (1.13c dropped or reordered rows such as the two chalices) |
| runes | 169 to 169 | reordered from 24 (117 rows): match by `Name` |
| setitems | 32 sets to 127 items | restructured |
| properties | 244 to 268 | 125 (`passives` to `aura`), 232-234 (pierce order fire / lightning / cold) |
| magicprefix | 667 to 669 | 530 (`Screaming` to `Gritty`) |
| objects | 573 to 573 | 74 spelling only |
| armor | 202 | 198 code `nec` to `neg` |
| hireling | 60 to 120 | doubled into Version 0 and 100 |
| treasureclassex | 774 to 853 | differs from 672; referenced by name, harmless |

## What cannot be mapped

1. The 17 1.13c-only tables. Exceptions: `monstats2` is fed from the monstats graphics columns plus 1.09d `montype`,
   `skilldesc` only from `SkillPage/Row/Column/IconCel`, `sets` from 1.09d `setitems`.
2. New 1.13c columns with no 1.09d source (697 in shared tables, plus every column of the 17 new tables): most of
   skills, missiles, states and itemstatcost. Their 1.09d values are code behaviour, not data. Fill them with the value
   that reproduces 1.09d ([classic-109d-vs-d2r.md](classic-109d-vs-d2r.md)).
3. Dropped 1.09d columns (239): mostly comments. Real behaviour with no 1.13c column: `difficultylevels.ExtraUniqueMonsters`,
   `levels.S1-25`, the `unique*` `MonType1-36` restrictions, `monstats.ElOver / Spawned / CanStealFrom / eMagicUsing /
   SpawnPctBonus / Switch`, `skills.Shiver`, and `monstats.PopulateId` (replaced by `NextInClass`). `CanStealFrom` maps to
   `Drain` 100 or 0.
4. Recodes that need a lookup the data does not fully give: `monstats.SkillNSeq` (sequence numbers to monmode codes or
   `monseq` names; 0, 1, 20 and 30 are ambiguous), `skills.itemclassN` to `itypea/b`, `properties.ModFuncOffset` to
   `func` / `stat`, the `books` offsets, `levels.S*`.
5. Values to write because 1.09d never read the column: `experience.ExpRatio` 1024 on every level (an empty cell
   probably reads as 0; not checked); itemratio `*Min` columns 0; `difficultylevels` gamble columns 8000 / 10 / 1;
   monstats `AI` from `BaseId`; the `*SymPerCalc` synergy columns empty; damage bracket 3 copied into 4 and 5 (the
   1.09d bracket boundaries were not read from code).

## Open checks

- Confirm the `setitems` `INCodeA-E` to `aprop1a-5a` bracket assumption against 1.09d `D2Common` or in game.
- Confirm `skills.SelectDead` to `TargetCorpse` (all 0 in 1.09d, harmless either way).
- The `(N)` / `(H)` copies assume 1.09d did not scale those settings in code.
