# How D2R reads its tables

Tables live in `data/global/excel/` as tab-separated `.txt` (Latin-1 safe, CRLF) with compiled `.bin` twins. A mod
ships its tables inside its folder MPQ (`<game>/mods/<Mod>/<Mod>.mpq/data/global/excel/...`). The port compiled
them with D2RLoader (`d2rl compile <Mod>` in the developer console). D2RLoader 1.3.1 compiles a mod's `.txt` tables
itself at start-up ("Compiled N tables from TXT"), so `-txt` is not needed; shipping any `.bin` makes D2RLoader treat
the mod as a "custom BIN set" that must be complete. On its cache-building first start it loads D2R's own sounds
table, not the mod's ([d2rloader.md](d2rloader.md)).

## Two banks: `excel/` and `excel/base/`

Since 3.0 (dataguide `docs/game-mode-split.html`):

| Folder | Game mode | 93847 |
|---|---|---|
| `data/global/excel/base/` | Classic and Lord of Destruction | 177 tables |
| `data/global/excel/` | Reign of the Warlock (RotW) | 184 tables |

- No inheritance between the two: each mode reads only its own folder.
- Exceptions shared by all modes (always read from `excel/`): `sounds.txt`, `soundenviron.txt`.
- **Indices must match across modes** (a character upgraded from LoD to RotW keeps its row numbers).
- An overhaul should write **both banks** with identical row IDs until it knows which mode its characters use.
- Bank differences in 93847 (records): skills 429 (RotW) vs 427 (base); missiles 742 vs 736; skilldesc 263 vs
  232; levels 138 vs 137; overlay 334 vs 333; skillcalc 127 vs 121 rows; srvdofunc max 171 vs 152; cltdofunc max
  109 vs 97. Both banks have the Warlock class (30 skills) in skills.txt.

### Warlock rows in the LoD bank (build 93847)

Facts from comparing D2R's own `base/` and `excel/` row by row on each table's first column (files only; the game was
not launched, and tables with repeated keys such as `itemratio` were not compared). In `base/` the Warlock-era rows
are **disabled placeholders**: the row exists so row numbers match across modes, but it is switched off.

| Table | `base/` (LoD) | `excel/` (RotW) |
|---|---|---|
| charstats | `Warlock` row present | same, plus `HealthPotionPercent` 150 and `TwoHandedOffHandRestrictItemType` `grim` (column absent in base) |
| skills | all 30 Warlock skills present with `InGame` and `reqlevel` blank; the RotW-only rows `Korlic's Bash` and `HeraldThorns` missing | `InGame` 1 |
| skilldesc | the 31 Warlock descriptions missing | present |
| itemtypes | `Warlock Item` and `Grimoire` with no `Class` / `StaffMods` | `Class` `war`; `Crafted Sunder Charm` type added |
| armor | 15 grimoire bases present with blank stats, level and name | full rows |
| uniqueitems / setitems / runes | 4 uniques with no `code`, 2 sets (8 items) `disabled` 1, 5 runewords incomplete | spawnable and complete |
| monstats | Warlock summons and the Colossal set with `enabled` 0 | enabled |
| objects, levels | Colossal altar and statues unnamed; no Colossal Summit row (137 level rows) | named; `Act 5 - Colossal Summit` at id 137 (138 rows) |
| misc | Worldstone shards present, not spawnable | spawnable; 91 items flagged `AdvancedStashStackable` (0 in base) |
| cubemain, treasureclassex | 155 recipes, 1138 classes | 72 and 220 more (Worldstone-shard crafting, Sunder Charm upgrades, Terrorize consumables, Herald charms) |

- Dropping the placeholders when a table replaces the LoD bank shifts indexed rows (tables are addressed by row
  number), the `uniqueitems` / `setitems` / `runes` indexes saves store, and item-type numbers the engine tests
  (`warl` at row 67). D2R itself keeps them disabled (blank `InGame`, `enabled` 0, `disabled` 1, not spawnable, no
  recipe).
- `sounds.txt` and `soundenviron.txt` are read from `excel/` in every mode. `excel/` holds 18 RotW-only sounds
  (Warlock skills, Worldstone shards, desecrated-zone cues); they have no gameplay effect.
- A character converted from LoD to RotW (or opened in RotW mode) reads `excel/`. Blizzard's ladder season 16 notes
  end online conversion for Expansion characters from 16 November; whether offline conversion remains is not
  checked. The `expansion` cheat command changes a character's version for good when it saves
  ([cheat-commands.md](cheat-commands.md)).
- RotW-only flags: the stackable advanced-stash flag is set only in `excel/`, and `disableChronicle` exists only
  there. Whether the Chronicle, Loot Filter and stackable stash tabs appear in LoD mode is unverified (they are code
  and UI features sold with the RotW DLC).
- Strings, HD art and the skill-tree layout are shared by all modes and not banked: Warlock strings and art stay,
  unreachable once no table row points at them. Character select refusing a Warlock in LoD is code (owner-confirmed
  in the source project) and holds while the `Warlock` charstats row stays.
- The LoD bank is D2R's LoD, not 1.09d: it keeps 1.10-2.6 content (newer uniques and sets, the 2.4/2.6 runewords,
  Sunder Charm uniques, Desecrated boss treasure classes, the uber-boss rows).

## The schema source: the dataguide

`data/global/dataguide/` (shipped in CASC) is Blizzard's own documentation: `data/files/<table>.js` per table
(`files["skills"] = {...}` JSON after the `= `). Per field: `name`, `description`, `type`:

| type | meaning |
|---|---|
| `text` | key or free text; `dataLength` = maximum characters |
| `reference` | points at `file`.`field` (validate the target exists) |
| `string` | a string key (data/local/lng/strings) |
| `int` / `boolean` | `memSize` = bit width (8, 16, 32): values beyond it wrap |
| `parse` | BBE formula (scope by table) or property code/parameter |
| `comment` | ignored by the game |

Plus `enums.js` (enumerations), `docs/bbe-calc.html` (formula syntax, functions, `cond()` conditions),
`docs/game-mode-split.html`, `docs/damage.html`, `docs/genericpetai.html`, `docs/itemratio-calc.html`. Build a
validator from these files: it types every cell, checks references, key lengths and enum values.

## Indexed vs keyed tables

| Kind | Tables | Identity |
|---|---|---|
| **Indexed** (the engine and saves use the row number) | skills, states, itemstatcost, missiles, monstats, monstats2, overlay, properties, levels, objects, monai, pettype, monprop, skilldesc (by key only, see below), superuniques, ... | Row number = ID. Reordering changes every reference |
| **Keyed / content** (referenced by key or code) | weapons, armor, misc (by `code`), itemtypes (`Code`), uniqueitems/setitems/sets (`index`), runes, magicprefix/magicsuffix/automagic, treasureclassex, cubemain, gamble, monsounds, ... | Key; row order mostly irrelevant, but **uniqueitems/setitems/runes row indexes are stored in saves**: keep existing rows in place. **itemtypes is keyed but D2R's code tests type numbers** (75 rune, 77 hpot, 68 h2h, ...): keep D2R's rows at D2R's numbers ([engine-limits.md](engine-limits.md)) |

- Rows counted: **every row except rows whose first cell is `Expansion`**. Blank-key rows are real records
  (monsounds and montype start with one). D2R's own `*Id`/`*ID`/`*hcIdx` comment columns confirm the count.
- `skilldesc` was re-sorted alphabetically by D2R and is referenced by name only.
- `skilldesc` behaviour in build 93847. Source: the comments of the classic-port code that rewrites these lines
  (`shared/classic_import/skilldesc.py`), not a capture in this repo; each is marked as such:
  - A skill with `SkillRow` 0 is drawn in its page's first cell (a classic client hides it). To keep a skill off the
    tree, set its `SkillPage` to 0. (Port code comment; unverified in a capture.)
  - D2R's skilldesc strings carry the value's format code ("Duration: %d seconds"), so a classic line function that
    prints the text and then the value prints the value twice. (Port code comment; unverified in a capture.)
  - D2R's own classic line functions print text raw, with no format code ("+%d Percent ..." shows the code as text),
    so a string with a format code is only safe under the functions and column D2R's lines already use it in.
    (Port code comment; unverified in a capture.)
  - The tooltip stacks description lines upward: a line inserted under a built-in line takes that line's slot and the
    lines above it move up one. (Port code comment; unverified in a capture.)
- Columns starting with `*` are comments (`*ID`, `*eol`, `*ItemName`...). Keep them but the game ignores them.
- `*eol` ends some tables: keep it last.

## Rules for adding rows safely

1. **Never reorder or delete D2R rows** in indexed tables; D2R code refers to its own additions by number (states
   `cooldown`, `sharedstash` 186, `hidedead`; skills `Interact`, `Loot`, `TownPortal`; itemstatcost
   `skill_cooldown`, `skill_missile_damage_scale`, `psychicward`; missiles `recklessattacksmissile`, ...).
2. **Append** new rows after D2R's last row. 93847 record counts (not counting `Expansion` rows), RotW / base:
   skills 429 (last ID 428) / 427, states 232, itemstatcost 368, properties 284, missiles 742 / 736, monstats 751,
   monstats2 623, overlay 334 / 333, objects 587, levels 138 / 137, skilldesc 263 / 232, superuniques 66,
   lvltypes 36. New rows start after the larger bank's count so both banks share the IDs.
3. To repurpose a D2R row, edit it in place and keep its key unless nothing references the key.
4. Keep both banks' IDs identical.
5. Every reference column must name an existing row (validator). Remap references when IDs move.
6. Write signed values signed (`-1`, not `4294967295`); write booleans as 0/1.
7. Keep each key within its `dataLength` (31 missiles/objects Name, 39 lvlwarp, 47 most keys).
8. Formulas: 255 chars max, 32-byte quoted names, no bare negative literals (`(0-N)`), bracketed ternary
   branches.

### New levels: `LevelEntry` and `LevelType` (build 93847)

- An empty `LevelEntry` on a level with a `LevelName` shows "Missing string" in the area banner. Give every new level
  a `LevelEntry` key that `strings` defines (D2R's own use `Entering<Name>`).
- A `LevelType` past the last lvltypes row (id 35 in D2R, 36 rows) makes the game read a null row at startup
  (function FUN_140a13860). A mod that ships no lvltypes.txt of its own must keep every level's `LevelType` within
  D2R's rows (0 is "None").

## Freeze before release

A character file stores rolled values, ids and bit-packed fields; the tables say how to decode them. After players
have saves, an edit to a "stored" field misreads old items or moves ids. Decide these before the first release.
Evidence: fields from `knowledge/saves.md`, the engine-limits notes and a read of a public Rust `.d2s` parser (v96-v105);
"unverified" means no D2R test was run ([saves.md](saves.md)).

| Table / field | What a save depends on | After release |
|---|---|---|
| `itemstatcost` row order (stat id) | item and character stat lists store the id | **Freeze.** Append only, never reorder or delete |
| `itemstatcost` `Save Bits`, `Save Add`, `Save Param Bits` | width, offset and layer width of every item stat. The `armorclass`, `maxdurability` and `durability` rows also set defense and durability widths | **Freeze** for every row that can appear on an item: the stream is bit-packed, so one wrong width misreads every later field |
| `itemstatcost` `CSvBits`, `CSvParam` | character stat widths | **Freeze** |
| `itemstatcost` new stat without `Save Bits` | a stat with no save bits is dropped on reload | give a new item stat its final widths when you add it |
| `itemstatcost` `Encode`, paired min/max stats, `ValShift` | how a stored value or parameter is split and scaled | treat as frozen (not enumerated; unverified for D2R) |
| ItemStatCost schema as a whole | recorded in the `.d2rl` sidecar and checked in multiplayer | any change is visible to the loader; the exact warn-or-block rule is not documented |
| `uniqueitems`, `setitems` row index | stored id (12 bits retail) | **Freeze** in place; append |
| `runes` row index | stored runeword id (16 bits) | **Freeze**; append |
| `magicprefix`, `magicsuffix`, `automagic`, `rareprefix`, `raresuffix` row index | stored id (11 or 8 bits retail); the affix tables start with a blank row | **Freeze**; append |
| `armor` / `weapons` / `misc` `code` | stored as a Huffman-coded item code. The table the code sits in decides whether defense, durability and quantity bits follow | **Freeze** existing codes; never move a code between tables or delete it |
| Base `invwidth` / `invheight`, `inventory.txt` grids | stored x, y | shrinking can strand stored items; a bad placement on a custom page stops the load (unverified for stock grids) |
| `itemtypes` | engine code tests numbered types (75 rune, 77 hpot, ...); charm, scroll/book and body-part classification changes which extra bits are read | **Freeze** D2R's rows at D2R's numbers and each existing base's type tree where it changes classification |
| `skills` row order and `charclass` | class-skill bytes in skill-id order, hotkey skill ids, skill params on items | **Freeze** the order: inserting a class skill shifts every character's points |
| `levels` ids and `Layer` | waypoints and quests are stored by index (unverified); the automap per `Layer` (< 100) | append only; keep `Layer` < 100 |
| `hireling` rows | the mercenary type is stored | treat as frozen (unverified) |
| Plugin id, scope and `logicalId` of every custom page | page identity in extended saves | **Freeze**; keep the provider installed, or its items are dropped after a Recovery backup |
| `modinfo.json` `savepath` | which folder holds the characters | **Freeze**: a change hides them ([saves.md](saves.md)) |

**Safe after release** (additive, the decoder is unaffected; unverified as a complete list): appending rows to indexed
tables after the larger bank's count; new uniques, sets, runewords, affixes and bases within the format's widths;
drop and spawn data (`spawnable`, rarity, treasure classes, gamble, cube); strings; skill, monster and level balance.

**Retroactive but not stored.** These change what an item already in a character does, without touching the save:
`sets.txt` partial and full bonuses (only a set item's own masked bonus lists are stored), base weapon damage,
requirements and other base-row values not listed above, `properties` / `itemstatcost` `op` behaviour and the
meaning of an existing stat, item names and graphics read from the unique or set row. Stored properties stay fixed
while the rules around them can change; whether base damage or set bonuses count as an "item property" is a policy
choice for the mod.

Release gate: keep a few retained test characters and load them in each candidate build; the validator does not
check widths for you.

## Terror Zones

Terror Zones are data plus engine code (build 93847; offline play has had them since patch 2.6, from secondary
coverage). The schedule and scaling are in `data/hd/global/excel/desecratedzones.json`; nothing else turns them on.

| Part | Where | What it holds |
|---|---|---|
| Schedule | `desecrated_zones[0]` | `seed`, `zone_duration_minutes` 30, `break_duration_minutes` 0, `start_time_utc` 2025-12-05 |
| Zones | `zones`, `manual_zones`, `warnings` | 34 zones (`id` such as `Act1-BurialGrounds`), each a list of `levels` with `level_id`, optional `waypoint_level_id` and `zone_completion_weight` (its engine reader is not found); 5 manual zones, 4 warnings |
| Per mode, difficulty | `game_difficulties.expansion` and `.rotw`, each `normal`/`nightmare`/`hell` | `ladder_enabled`, `non_ladder_enabled`, `max_herald_tiers`, `defaults` |
| Scaling | `defaults` | `bound_incl_min` / `bound_incl_max` 3-45 (Normal), 40-71 (Nightmare), 70-96 (Hell); `boost_level` 2 and `boost_experience_percent` 25 in every mode and difficulty (read from 93847's file) |
| Heralds (RotW Hell only: `max_herald_tiers` is 5 there, 0 elsewhere) | `defaults.herald_tiers` | 5 tiers; zone chance follows a logistic curve (`zone_chance_slope`, `_midpoint`, `_asymptote`, `_vertical_shift`); health, damage and minion boosts; `unique_mod_chance_boosts` |
| Drops | `monstats.txt`, `superuniques.txt` | `TreasureClassDesecrated*` / `TreasureClassHerald*`, `CannotDesecrate` / `CannotHerald`, `TC Desecrated`; formulas can test `cond(Desecrated)` |
| Engine | code | region fields from `+0x2e8` and a monster-level bump `0x35b340` inside `0x508f80` ([d2r-93847-addresses.md](d2r-93847-addresses.md)) |

- There is **no zone API**: no plugin call that sets or reads the active zone was found. The SDK's Herald request
  fails with `NotTerrorZone` outside a zone. Forcing a zone, adding cloned level ids to `zones`, or calling the
  bump from your own hook is untried.
- A level in a Terror Zone is rescaled in place and nothing teleports, so the same-act portal rule does not apply.
- Strings for an "Enable Terror Zones" game setting exist in `ui.json`; whether the offline create screen shows it on
  93847 is unverified.
- Turning the whole feature off is data: set `ladder_enabled` / `non_ladder_enabled` false and `max_herald_tiers` 0
  for every mode and difficulty, and disable the Colossal portal cube row in `excel/` (`excel/base/` has none). The
  Sunder Charm uniques are not spawnable and drop through these treasure classes, so they go with it. A ready patch:
  [examples/patches/no-terror-zones.json](../examples/patches/no-terror-zones.json).
- Hosting your own maps with this system: [new-game-systems.md](new-game-systems.md), "Map hosting".

## D2R-only columns worth knowing

| Table | Column | Meaning |
|---|---|---|
| overlay | `Character` | HD overlay folder: `data/hd/overlays/<Character>/<overlay>.json` (`common`, `paladin`, `sorceress`, `druid`, `warlock`, `monster`, `assassin`, `amazon`, `necro`, `barbarian`, `object(s)`, `npcs`, `item`). Empty = no HD effect |
| skills | `Param9`-`Param14`, cooldown/behaviour flags, `calc5`-`calc10` (free formula slots a plugin can read) | |
| monstats | `TreasureClass`, `TreasureClassChamp`, `TreasureClassUnique`, `TreasureClassQuest` (+ (N)/(H)), Desecrate / Herald columns | Classic `TreasureClass1..4` renamed |
| levels | `MonLvl`, `MonLvl(N)`, `MonLvl(H)`, `MonLvlEx...` | Classic `MonLvl1..3` renamed |
| itemtypes | `MaxSockets1..3` + `MaxSocketsLevelThreshold1/2`, `UICategory`, `RunewordCategory1/2` | |
| hireling | `ResistFire/Cold/Lightning/Poison` (+ `/Lvl`), `HireDesc` (a string key) | |
| uniqueitems / setitems / runes / treasureclassex | `firstLadderSeason`, `lastLadderSeason`, `DropConditionCalc` / `ConditionCalc`, `disableChronicle`, `diablocloneweight` | |
| armor / weapons / misc | Anya-reward, advanced-stash, quiver columns, `ShowLevel`, `DropConditionCalc` | |
| charstats | `HealthPotionPercent`, `ManaPotionPercent`, `SkillsPerLevel`, `StrSkillTab1-3` | |
| difficultylevels | mercenary / pet / prime-evil damage rules, gamble rates, `ResistFloor` | |
| inventory | Warlock rows; two rows per page | see below |
| experience | `Warlock` column | |

Classic renames to remember: `Hralti*` -> `Hratli*`, `Drehya*` -> `Anya*`, `NoShldBlock` -> `ShieldBlockOverride`,
skills `delay` -> `localdelay`, uniqueitems `enabled` -> `spawnable`, missiles `LevRange` merged into `Range`.

## Per-table cheat sheet for overhaul work

| Table | Key / ID | What to watch |
|---|---|---|
| **skills** | `skill` (47), row = ID | `charclass` (30 per class in retail), `skilldesc`, `srvstfunc`/`srvdofunc`/`srvstopfunc`, `cltstfunc`/`cltdofunc`/`cltstopfunc`, `anim`/`seqtrans` (SQ for sequences), `seqnum`, `aurastate`/`passivestate`/`auratargetstate`, `aurastat1-6` + `aurastatcalc1-6`, `aurarangecalc`, `aurafilter`, `calc1-10` (Raven-AI pets read their attack count from `calc3`), `Param1-8` (+9-14), `srvmissile(a/b/c)`, `cltmissile(a/b/c)`, `summon`/`pettype`/`summode`/`petmax`, `mana`/`lvlmana`/`minmana`/`manashift`, `localdelay`, `reqlevel`, `reqskill1-3`, `skpoints` (cost formula; 999 = cannot learn), `leftskill`/`rightskill` (D2R's picker honours them: `rightskill 1` on every active skill, innate ones too), `InTown`. D2R function maxima: srvdo 171, cltdo 109, srvst 70 (table 91-94 slots), cltst 61 (table 70 slots) |
| **skilldesc** | `skilldesc` | `SkillPage` (tab), `SkillRow`, `SkillColumn`, `ListRow`, `IconCel` (frame in the class icon strip: 2 frames per icon, normal + pressed; class-less skills read one shared sheet, and a classic mod's shared sheet may hold one frame per icon), `str name/short/long/alt`, `descline*`/`dsc2line*`/`dsc3line*` + text a/b + calc a/b. A line type whose text is missing asserts |
| **missiles** | `Missile` (31), row = ID | `pCltDoFunc`/`pCltHitFunc`/`pSrvDoFunc`/`pSrvHitFunc` (free: srv hit 61-70, srv do 46-53), `Param1-5`, `CltParam1-5`, `sHitPar1-3`, `cHitPar1-3`, `SrvCalc1`, `CltCalc1`, `SHitCalc1`, `CHitCalc1`, `DmgCalc1`, `Range` (expression; classic `LevRange` merged in). **Server hit 6 spawns the monstats row in `sHitPar1`**: remap it when monstats rows move, `CelFile` (classic only), `SubMissile1-3`, `HitSubMissile1-4`, `Skill`. HD look comes from `hd/missiles/missiles.json` by name |
| **states** | `state` (47), row = ID | `overlay1-4`, `castoverlay`, `removerlay`, `pgsvoverlay`, `stat`, `setfunc`/`remfunc`, `missile`, `skill`, `colorshift`, `nosend` (not synced to clients). Above 511 states D2R asserts at load; D2RLoader 1.3.1 syncs wide states |
| **overlay** | `overlay` (47), row = ID | `Filename` (classic DCC), **`Character`** (HD folder), `Trans`, `AnimRate`, `Height1-4` |
| **monstats** | `Id` (47), row = ID | `BaseId`/`NextInClass`, `MonStatsEx` (monstats2 row; blank = row 0), `MonType`, `AI`, `Code` (classic animation set, also used in HD for timing), `Skill1-8` + `Sk1mode-Sk8mode` (a **monmode code or a monseq name**), `TreasureClass*`, `coldeffect` (signed), `spawnx/spawny` (signed), per-difficulty columns `(N)`/`(H)` |
| **monstats2** | `Id`, row = ID | visual columns: sizes, `HitClass`, part variants, modes `m*`/directions `d*`, `isSel`/`isAtt` (hover/target), `noGfxHitTest`, `automapCel`, `Light`, `Utrans` |

### Item and affix tables

| Table | Key / ID | What to watch |
|---|---|---|
| **armor / weapons / misc** | `code` (3 characters in practice: `items.json` is keyed by the first 3 characters, so a 4-character code finds no picture and spawns nothing; see hd-graphics.md) | `type`/`type2` (itemtypes), `namestr` (string key), `invfile`/`uniqueinvfile`/`setinvfile`, `invwidth`/`invheight`, `normcode`/`ubercode`/`ultracode` (armor/weapons tiers), `level`/`levelreq`, `spawnable`, vendor `*Min/*Max` columns, misc `pSpell` (0-19), `spellicon` (signed, -1 none), `stat1-3`/`calc1-3` (timed potion `pSpell` 3: calc is the total over `len` for hp / mana / manarecovery / hpregen, a per-frame value for other stats), `state`/`cstate1-2`, `len`. HD picture: `hd/items/items.json` by code |
| **itemtypes** | `Code` | `Equiv1/2` (parent types: the type tree drives affixes, auto TCs, sockets), `BodyLoc1/2`, `MaxSockets1-3` + thresholds, `TreasureClass` (auto `weapN`/`armoN`), `StorePage`, `Class`, `VarInvGfx`/`InvGfx1-6` |
| **uniqueitems** | `index` | `code` (base item), `lvl`, `lvl req`, `rarity`, `spawnable`, `nolimit`, `prop1-12` + `par`/`min`/`max`, `invfile`. HD picture: `hd/items/uniques.json` key = index lowercased, spaces/hyphens `_`, apostrophes dropped |
| **setitems / sets** | `index` | setitems `set` (sets.index), `item`, `prop1-9`, `aprop1a..5b` (partial bonuses); sets `PCode2a..5b` (2-5 items worn), `FCode1-8` (full set). **Max 6 items per set** |
| **runes** | `Name` (63) | `complete`, `itype1-6`/`etype1-3`, `Rune1-6`, `T1Code1-7` (**7 property slots**) |
| **magicprefix / magicsuffix / automagic** | row (affix ID saved in items) | `spawnable`, `rare`, `level`/`maxlevel`/`levelreq`, `classspecific`/`class`, `frequency`, `group` (exclusive group), `mod1-3code/param/min/max`, `itype1-7`, `etype1-5`. automagic = class-specific implicit mods. Affix tables start with a blank record row |
| **properties** | `code` (47), row = ID | `func1-7` (D2R uses 1-25, 36), `stat1-7` (itemstatcost), `set`/`val`. Items reference properties by code |
| **itemstatcost** | `Stat` (47), row = ID | `Signed`, `Send Bits`/`Send Param Bits` (network), `Saved`, `CSvBits`/`CSvParam` (character save width), `Save Bits`/`Save Add`/`Save Param Bits` (item save width), `Encode` (a property with function 28, "layer = param", on a stat with no `Save Param Bits` makes D2R's item writer fail: the client crashes when the item drops), `op`/`op param`/`op base`/`op stat1-3` (derived stats), `descpriority`/`descfunc` (D2R uses 5-29)/`descval`/`descstrpos`/`descstrneg`/`descstr2`, `dgrp*`. **Widths change the save format**: decide them before players have saves |
| **treasureclassex** | `Treasure Class` | `group`, `level`, `Picks`, `Unique/Set/Rare/Magic` ratios, `NoDrop`, `Item1-10` + `Prob1-10` (items by code; quoted entries with modifiers like `"gld,mul=2560"`), `ConditionCalc`. Auto classes `weapN`/`armoN` pull every spawnable base of that level band: remove vanilla bases you don't want dropping |

### World and character tables

| Table | Key / ID | What to watch |
|---|---|---|
| **levels** | `Name`, `Id` (row = ID) | `Act`, `LevelType` (lvltypes row, **0-35 only for automap**), `DrlgType`, `SubType`, `Teleport` (0 no, 1 yes, 2 only with a clear line), `Vis0-7`/`Warp0-7`, `MonLvl*`, `MonDen*`, `mon1-25`/`nmon1-25`/`umon*`, `Waypoint`, `Quest`, `Portal`, `Layer` (**< 100**: index into the 100-bucket per-character map memory), `Position` (1 = arrive in a random entry room of the maze preset: **clear it on new maze levels** that have none, or the game crashes on entry). Level portal links are bytes in many places: keep IDs <= 255 |
| **lvlprest / lvltypes / lvlwarp / lvlmaze / lvlsub** | lvlprest `Def`, lvltypes `Name` (36 types + `Expansion` row) | lvlprest `File1-6` (.ds1 maps), lvltypes `File 1-32` (.dt1 tiles). Ship every tile file referenced. .ds1 maps hold object IDs by number |
| **automap** | (`LevelName`, `TileName`, `Style`, `StartSequence`, `EndSequence`, `Cel1-4`) | `LevelName` must be one of the 36 lvltypes names in a reformatted form ("Act 1 - Town" -> "1 Town"); others assert `ii < NUM_LEVEL_TYPES`. `Cel1-4` **<= 1498** (the atlas has 1,499 cels; a higher cel stored in a character's map memory hangs the next save) |
| **cubemain** | none (comment `description`) | `enabled`, `min diff`, `version`, `op`/`param`/`value` (player conditions 1-14 checked, item ops 15+; unknown ops pass), `class`, `numinputs`, `input 1-7`, `output`/`output b`/`output c` + `mod 1-5`. Record 0x16c bytes in memory |
| **charstats** | `class` | base stats, `LifePerLevel`/`ManaPerLevel`/`StaminaPerLevel` (quarter points), `LifePerVitality`, `ManaPerMagic`, `StatPerLevel`, `SkillsPerLevel`, `StartSkill`, `Skill 1-10`, `StrAllSkills`/`StrSkillTab1-3`/`StrClassOnly` (string keys), starting `item1-10` |
| **hireling** | `Hireling` + `Version` + `Difficulty` + `Level` rows | `Class` (monstats row), `Act`, `Skill1-6` + `Mode/Chance/Level`, stat growth, resist columns, `HireDesc` (string key). D2R repeats rows per level: key-merging re-adds vanilla mercenaries |
| **inventory** | `class` (comment), row order fixed | `invLeft/Right/Top/Bottom`, `gridX`/`gridY`, `gridLeft/Right/Top/Bottom`, `gridBoxWidth/Height`, then body slot rectangles. **Two rows per page** (`Amazon` + `Amazon2`, `Big Bank Page 1` + `Big Bank Page2`, ...). Pages: 8 classes, Monster, Trade Page 1/2, Bank Page 1 (classic stash), Transmogrify Box (cube), Big Bank (expansion stash), Hireling |
| **experience** | `Level` | first row `MaxLvl`; row L = experience at which level L+1 starts; one column per class incl. Warlock; `ExpRatio` |
| **difficultylevels** | `Name` (3 rows) | resist penalties, `DeathExpPenalty`, damage-vs rules, gamble rates, `ResistFloor` |
| **plrmode / monmode** | row = mode index | Keep D2R's `Code` column exactly (Sequence `SQ`, Knockback `KB`; the `Token` column is `GH` for both) |
| **skillcalc / misscalc** | row = code number | D2R's rows first in D2R's order; append new codes (they need a plugin to evaluate) |

## Cube recipe fields
- `description` (description used by modkit lookup, any text), `enabled` 1, `version` 100 (expansion), `min diff`, `class` (restrict).
- Inputs: `numinputs` (total item count), `input 1-7`: an item code, item type, unique/set name in quotes, with
  qualifiers after commas: `"rin,mag"` (magic ring), `qty=3`, `sock=2`, `nos` (no sockets), `pre=`/`suf=`, `upg`,
  `bas`/`exc`/`eli`, `nru`, `noe`. Quote a cell with commas.
- Output: `output` (code, type, "Cow Portal", "Pandemonium Portal", "Red Portal,lvl=<level id>" (a red portal to any level of the same act), "useitem", "usetype", ...) with qualifiers
  (`mag`, `rar`, `uni`, `set`, `crf`, `tmp`, `sock=N`, `rep`, `rch`, `pre=`, `suf=`, `reg`, `exc`, `eli`,
  `uns`, `rem`), `lvl`/`plvl`/`ilvl` (item level rules), `mod 1-5` + `chance`/`param`/`min`/`max` (properties);
  `output b`/`output c` with the same columns for extra outputs.

## Base item and vendor fields

Set `name`/`namestr` and give the name a string in `item-names.json`. The clone's damage/defence,
`reqstr`/`reqdex`, `gemsockets`, `rarity` and `cost` are separate from item level and requirements.
For gems/runes as socket fillers, `gems.txt` has `weaponMod`/`helmMod`/`shieldMod` 1–3 per target.
The classic picture is the DC6 named by `invfile`; for the HD entry see [item pictures](hd-graphics.md#item-pictures).
New stat behavior (procs, conversions) needs engine support; new display can use vanilla descfuncs.
For drops, layer and save-width limits see [item limits](engine-limits.md#items-inventory-sets-runes-cube).

Vendor stock lives in `<Vendor>Min/Max/MagicMin/MagicMax/MagicLvl` on weapons, armor and misc. Vendors include
Charsi, Gheed, Akara, Fara, Lysander, Drognan, Hratli, Alkor, Ormus, Elzix, Asheara, Cain, Halbu, Jamella,
Larzuk, Malah and Anya.

## Treasure classes and affixes

In `treasureclassex`, negative `Picks` selects each item for its stated count. Entries can be base codes,
other TC names, unique/set names or automatic `weapN`/`armoN` classes (item levels grouped in steps of 3).
Monsters use `TreasureClass` / `TreasureClassChamp` / `TreasureClassUnique` / `TreasureClassQuest` with
`(N)`/`(H)` variants and `TreasureClassDesecrated*` for Terror Zones. Superuniques use `TC`. For affix name
strings see `name` in affix rows and `rareprefix`/`raresuffix` for rare item names. The per-table cheat
sheet above lists spawn, level, group, weighting and item type fields.

## Monster records and skills

1. Clone `monstats` for behavior. In addition to the cheat sheet, set `NameStr`, `Level`, `minHP`/`maxHP`,
   `AC`, `Exp`, `A1MinD`/`A1MaxD`/`A1TH`, `ResDm`/`ResMa`/`ResFi`/`ResLi`/`ResCo`/`ResPo`, `Velocity`/`Run`,
   `aip1-8`, `MissA1` etc., `minion1/2`, `PartyMin/Max` and `MinGrp/MaxGrp` as applicable. Use difficulty
   variants where present. `AI` selects a `monai.txt` behavior which decides which `Skill1-8` slot to cast.
   Choose an AI that casts the way you need. Pair each skill with its `Sk*lvl` and a real `Sk*mode`
   (monmode such as `S1`, `A2` or `SC`, or a monseq name).
2. Clone `monstats2` for graphics. Set body parts (`HD` through `S8`), mode flags (`mDT` through `mRN`),
   size, light, selection and `Height`. Palette shifts such as `Utrans` only affect classic mode.
   Reuse the right animation `Code` and map the exact `Id` for [HD](hd-graphics.md#monsters).
3. Add a `string` op in `monsters.json` for `NameStr`.

## Monster spawns and difficulty

- `superuniques` uses `Superunique` (key), `Name` (string), `Class` (monstats Id), `Mod1-3` (monumod),
  `MinGrp/MaxGrp` and `TC`/`TC(N)`/`TC(H)`. Placement comes from presets or quests. New `monumod` behavior
  beyond existing functions requires engine code. Quest monsters and act bosses keep their role.
- In `levels`, `mon1-25` are normal spawns, `nmon1-25` nightmare/hell spawns, and `umon1-25` unique candidates.
  `NumMon` counts the mon slots used; `MonUMin/MonUMax*` control unique packs. `MonDen*` controls density.
- `MonLvl`/`MonLvl(N)`/`MonLvl(H)` and `MonLvlEx*` set area levels (the Ex columns are expansion).
  `monlvl` has per-level scaling with separate L columns by difficulty. `difficultylevels` controls resist
  penalties, mercenary/pet rules and drops. Check [level limits](engine-limits.md#levels-and-areas)
  before changing maps and automap behavior.

## Skill damage and animation fields

- **Damage**: `EType` / `EMin` / `EMax` / `EMinLev1-5` / `EMaxLev1-5` (elemental), `MinDam`/`MaxDam` +
  `MinLevDam1-5` (physical), all scaled by `HitShift` (8 = whole points, lower = fractions of a point; keep the
  clone's), `ELen` + `ELevLen1-3` in frames (25 per second) for cold/poison/burn lengths, `SrcDam` = share of weapon
  damage (128 = 100%).
  Synergies: `EDmgSymPerCalc` / `DmgSymPerCalc` formulas like `(skill('Ice Bolt'.blvl)+skill('Ice Blast'.blvl))*15`.
- **Animation**: `anim` must be a plrmode code (`SC` cast, `A1`/`A2` attack, `S1`-`S4` special, `TH` throw, `KK` kick,
  `SQ` sequence). `GH` is *get hit*, never a skill animation. `SQ` needs `seqnum`/`seqtrans` from a vanilla sequence
  skill and an HD state (the op copies one: `hdSequenceLike` must be a skill of the same class that has one, e.g.
  Whirlwind, Zeal, Fend, Strafe, Double Swing). Skills built on Whirlwind's functions keep its stop functions
  (srvstopfunc/cltstopfunc 1); without them the spin never ends.
- **Mana**: `mana`, `lvlmana`, `minmana`, `manashift` (mana = (mana + lvlmana*(lvl-1)) << manashift >> 8).

## Mod folder layout under D2RLoader (as the port installed it)

```
<game>/mods/<Mod>/
  <Mod>.mpq/modinfo.json            {"name": "<Mod>", "savepath": "<Mod>/"}   (own save folder)
  <Mod>.mpq/data/...                folder-style MPQ: global/excel, local/lng, hd/..., global/dataversionbuild.txt
  modinfo.json                      copy (D2RLoader guide layout)
  d2rloader/metadata.json           {"schemaVersion": 1, "metadata": {...}}  (+ top-level "namespace" when mod.json has one; none = native strings)
  d2rloader/config/d2rloader.toml   [d2rcore.save_format] mode = "extended"   (wider IDs in saves)
  d2rloader/plugins/<plugin>.dll    mod-scoped plugins
```

Install only while the game is closed; restart D2R fully after an install.
