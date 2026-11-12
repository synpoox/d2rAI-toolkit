# Stock 1.13c against D2R 3.3: tables, events, saves, engine code

What a classic Diablo II 1.13c install holds, set against D2R 3.3 build 93847, so that a port can tell what is the
original game, what a mod added and what D2R changed. Every row was checked against **stock** 1.13c files, not
against a mod. A mod's tables are a different question (see [porting-classic-mods.md](porting-classic-mods.md)).

Read with: [tables.md](tables.md), [engine-limits.md](engine-limits.md), [saves.md](saves.md),
[strings.md](strings.md), [d2r-93847-addresses.md](d2r-93847-addresses.md).

## 1. What "stock 1.13c" means here

| Part | How it was read | Check |
|---|---|---|
| Tables | `Patch_D2.mpq` first, then `d2exp.mpq`, then `d2data.mpq`: the first archive that has the file wins, as the game reads them. 1.13c's base archives are 1.09d's byte for byte; its patch adds or replaces files | 1.13c `Patch_D2.mpq` SHA-256 `b976e784…e919e0a9` (pinned in `shared/classic_import/gen_109d_map.py`) |
| Engine code | `D2Game.dll`, `D2Common.dll`, `D2Client.dll`, `Game.exe` of the 1.13c patch | `D2Game.dll` SHA-256 starts `24b293b8`, `D2Common.dll` `59fa5928`, `D2Client.dll` `dd8bc602`, `Game.exe` `74fe9c09` |
| D2R side | `data/global/excel/` (RotW) and `excel/base/` (classic/LoD) of build 93847 | `knowledge/` registry, `d2r-data/93847` |

A mod that ships these four files with the same hashes has **not** replaced the game's DLLs: its engine code lives in
a separate DLL that patches stock code in memory (section 6). Hash the mod's DLLs first; it settles how much to read.

Column lists below are the header lines of the stock `.txt` files. 1.13c ships a few tables only as `.bin`
(`automagic`, `rareprefix`, `raresuffix`): each record is the 1.09d `.txt` compiled, with the item-type slots widened
from bytes to words, so the 1.09d columns are its columns (proof in `gen_109d_map.py`).

## 2. Tables 1.13c has and D2R 3.3 does not

D2R 3.3 ships 91 tables in each bank. Stock 1.13c has ten with no D2R table (found in `Patch_D2.mpq`, `d2exp.mpq`
or `d2data.mpq`, `.txt` or `.bin`): `aiparms`, `arena`, `chartemplate`, `cubetype`, `hiredesc`, `monitempercent`,
`monname`, `treasureclass`, `uniquetitle`, `weaponclass`. They are classic tables D2R dropped or hard-codes; D2R has no
such file to merge them into. (`treasureclass` is the old table: the game reads `treasureclassex`.)

A table a mod ships that is in **neither** list, for example `miniskillicons`, is not stock: the mod added it, so
find what reads it before deciding anything.

D2R has nine tables stock 1.13c lacks: `actinfo`, `itemuicategories`, `levelgroups`, `moncalc`, `monpet`, `objpreset`,
`propertygroups`, `runewordUIcategories`, `wanderingmon`. None exists in any stock 1.13c archive. A port has to author
their rows from D2R's own (they hold ids and UI groups D2R's code reads).

## 3. Columns: stock 1.13c against D2R 3.3

Row counts are stock / D2R RotW, counted as data lines after the header (blank and `Expansion` separator lines
included; uniqueitems is 402 on that count, 401 without those lines). Only substantive column differences are listed; renames that
`shared/classic_import/ids.py` (`RENAME_MAP`) already maps are marked "renamed".

| Table | Rows | Stock has, D2R lacks | D2R has, stock lacks |
|---|---|---|---|
| events | 13 / 17 (base bank 16) | | see section 4 |
| states | 185 / 232 | `immed`, `blue`; `id` and `eol` (comment-column renames) | `hidedead`, `canstack`, `sunderfull`, `sunder-res-reduce`, `vfxweaponstate` |
| skills | 357 / 429 | `auratgtevent`, `auratgteventfunc`, `passiveevent`, `passiveeventfunc`, `delay` (renamed to `localdelay` in D2R, see `RENAME_MAP`), `checkfunc`, `nocostinstate`, `general` | `globaldelay`, `alwayshit`, `ItemUseRestrict`, `calc5-10`, `Param9-20`, `srvstopfunc`, `cltstopfunc`, `auraevent4`, `auraeventfunc4`, `passivestat6-14` and `passivecalc6-14`, `passivereqweaponcount`, `requirespettype`, `requiresweapon`, `useServerMissilesOnRemoteClients`, `KeepCursorStateOnKill`, `ContinueCastUnselected`, `ClearSelectedOnHold` |
| missiles | 684 / 742 | `LevRange`, `Qty`, `SpecialSetup` | `Radius`, `CollisionOverlap`, `OnDiedSound`, `MissileWeaponVFX` |
| itemstatcost | 359 / 368 | `Divide`, `itemspecific` | `advdisplay` |
| levels | 138 / 139 | `MonLvl1-3`, `MonLvl1Ex-3Ex` (renamed to `MonLvl`, `MonLvl(N)`, `MonLvl(H)`, `MonLvlEx...`), `EntryFile`, `Beta` | `CompletionTotalRoomsOverride`, `LevelGroup` (points into `levelgroups`), `LevelEntry`, `PreventTownPortal`, `umon11-25`, `mon11-25` and `nmon11-25` style extra monster slots, `*StringName` |
| monstats | 735 / 752 | `NoShldBlock`; `TreasureClass1-4` (renamed to `TreasureClass`, `...Champ`, `...Unique`, `...Quest`) | `CannotDesecrate`, `CannotHerald`, `ShieldBlockOverride`, `TreasureClassDesecrated...`, `TreasureClassHerald...`, `nopreventmonsterheal`, `rightArmItemType`, `leftArmItemType`, `canNotUseTwoHandedItems` |
| cubemain | 151 / 227 (base bank 155) | `ladder` | `firstLadderSeason`, `lastLadderSeason` |
| uniqueitems | 402 / 439 | `enabled` (renamed to `spawnable`), `ladder` | `disabled`, `spawnable`, `disableChronicle`, `DropConditionCalc`, `firstLadderSeason`, `lastLadderSeason`, `diablocloneweight` |
| setitems | 128 / 141 | | `disabled`, `spawnable`, `disableChronicle`, `DropConditionCalc`, ladder season columns, `diablocloneweight` |
| runes | 169 / 181 | `server` | `disallowCraftingInLadder`, `disallowCraftingInNonLadder`, ladder season columns, `*Patch Release` |
| itemtypes | 104 / 110 (base bank 109) | `Charm`, `Gem`, `CostFormula`; `MaxSock1/25/40` (renamed to `MaxSockets1-3`) | `MaxSocketsLevelThreshold1/2`, `UICategory`, `RunewordCategory1/2`, `Restricted` |
| weapons, armor, misc | 307 / 307, 203 / 218, 152 / 170 | `OpenBetaGfx`, `Source Art`, `Game Art`, `special`, `throwable`, `absorbs`, `spelloffset`, `szFlavorText`; NPC price columns spelled `Hralti...` and `Drehya...` (renamed to `Hratli...` and `Anya...`) | `ShowLevel`, `reqstr`/`reqdex`, `DropConditionCalc`, `UICatOverride`, `diablocloneweight`, `Transmogrify`, `TMog*`, `spawnstack`, `PermStoreItem`, `EventItem`, `AdvancedStashStackable` (misc), `UsageConditionCalc`, `spelldesccolor`, `spelldescstr2` (misc), `questdiffcheck` (armor) |
| overlay | 294 / 335 | `Dir`, `Open`, `Beta`, `Frames` (comment column in D2R) | `WeaponStateFlags`, `WeaponStateGroup`, `StartSound` |
| plrmode, monmode | 20, 16 / 20, 16 | none | none: **identical** to D2R's, including `Code` (`SQ` sequence, `KB` knock back; the `Token` of both is `GH`) |

Reading the table:

- A stock column D2R lacks is dead weight in a merged table: move it to the overflow report (the `ladder` columns
  are the exception, see below).
- A D2R column stock lacks needs a value on every row. The rules for the ones a merge can derive are in
  [porting-classic-mods.md](porting-classic-mods.md) section 3.
- `cubemain.ladder` holds 0/1 in stock (a recipe is online-only or not). D2R replaced it with a season range; a
  mod that used other values for its own recipe groups needs its own rule.
- `plrmode` and `monmode` need no conversion. The porting guide's "sequence mode spelled `GH`" is about a mod's
  skills (`anim`, `seqtrans`), not these tables.

## 4. Events

| Bank | Rows | Names |
|---|---|---|
| Stock 1.13c | 13 | hitbymissile, damagedinmelee, damagedbymissile, attackedinmelee, doactive, domeleedamage, domissiledamage, domeleeattack, domissileattack, kill, killed, absorbdamage, levelup |
| D2R base bank | 16 | the 13 above, then death, install, hextrigger |
| D2R RotW bank | 17 | the 16 above, then absorbresisteddamage |

- Rows 0-12 are the same everywhere, so an id is safe there. **Row 13 on is not**: a mod that added rows after
  `levelup` finds D2R's own rows at those numbers. Port events by **name**, never by index.
- D2R raises only the events in its own table. A stat listening on a mod's extra event row loads and never fires
  (cast on death is the worked example in [porting-classic-mods.md](porting-classic-mods.md) section 6).
- Unverified: stock 1.13c may never send some of the 13 (they exist in the table); no event and no evidence is
  named here, so check by hooking before assuming a vanilla event is live.

## 5. Saves: 1.13c version 96 against D2R version 105

| | 1.13c | D2R 3.3 |
|---|---|---|
| Header | signature `0xaa55aa55`, version dword | same signature; version 105 |
| Version | **96** (`0x60`): stock `D2Game.dll` writes the signature and then the immediate `0x60` in its header writer (RVA `0xec526`); the readers in `D2Client.dll` and `D2Launch.dll` compare the version against `0x5b` | **105**, plus the D2RLoader `.d2rl` sidecar for extended-format saves ([saves.md](saves.md)) |
| Stat ids | 9 bits on disk (max 511) | 9 bits in retail saves; wider only in the extended format |
| Class skills | 30 per class | 30 per class in retail saves; more only in the extended format |

Facts for a port:

- Version 96 is stock 1.13c's, so a mod's characters at version 96 are plain 1.13c characters. A mod with its own
  stat widths keeps them in extra columns (a second set of `Save Bits` columns in `itemstatcost`; stock has
  `1.09-Save Bits`, `1.09-Save Add`, `Save Bits`, `Save Add` and `Save Param Bits` only), so check which set the mod uses.
- Converting a version 96 character to 105 is a separate job; the item bit layout differs and no conversion exists
  in the toolkit.
- A port that adds stats past D2R's last id, or more than 30 class skills, cannot use retail saves. Decide this
  first ([porting-classic-mods.md](porting-classic-mods.md) section 0).

## 6. Reading a mod's patch table (engine code)

A classic mod's engine DLL usually patches stock 1.13c code in memory with a **table of patch records**
(typically `{dll, offset, target, type, length}`; a type that rewrites a `call rel32` is the common one). Every
record is a fact about stock code: the offset is a place in a stock DLL, the target is the mod's replacement.
How to read one:

1. Hash the mod's game DLLs against stock (section 1). If they match, every record's offset is a stock RVA.
2. For each record, read the stock bytes at the offset. A `call rel32` (`E8`) gives the vanilla callee:
   `callee = offset + 5 + rel32`. This names the function the mod replaces.
3. Group records by the function that contains them, and by the source file the surrounding assert strings name.
   One vanilla file often has many patches; an assert-string search finds only the patch whose own code asserts.
4. Decode the replacement only as far as the port needs. Compare it with the vanilla function: a changed check
   is a rule, an added call is a hook.
5. Then ask what D2R does at that place. D2R rewrote most of this code; the mod's patch is not carried over
   as bytes, only as a rule.

A mod that replaces a packet handler overwrites a pointer in a handler table; the stock handler is the code at the
pointer's old value. D2R rewrote the mode-change and death code, so a mod's gate patches are rules to **re-check in
D2R**, not bytes to port.

## 7. A table column stock 1.13c never reads: `immed`

`states.immed` is a **stock 1.13c column that the stock engine ignores**:

- The 40 flag columns of the states loader in `D2Common.dll` are a fixed list (from `nosend` to `notondead`). `immed`
  is not among them, so the reader never fills a record field for it. A column the loader does not name is never read.
- The only `immed` bytes in any stock 1.13c `D2Common.dll`, `D2Game.dll`, `D2Client.dll` or `Game.exe` are inside the
  word `immediate` (the skills column), at `D2Common.dll` file offset `0x90f48`. No DLL looks the column up by name.
- Stock `states.txt` does carry `immed` (set on the aura states). D2R dropped it.

So a mod that sets `immed` on its own states changed nothing. **Cut the column**; do not build a rule for it.
The same test settles any other doubtful column: search the stock DLLs for its name, then read the loader's column
table.

## 8. Function-number columns: what stock 1.13c data uses

The highest value any stock row uses, from the stock `.txt` files. A table size is not a data maximum; D2R's tables
and free slots are in [engine-limits.md](engine-limits.md).

| Column | Stock data max | D2R data / free (build 93847) |
|---|---|---|
| skills `srvdofunc` | 152 | D2R uses 153-171 for its own skills; free 172-190 |
| skills `srvstfunc` | 65 | D2R's data goes to 70; see [porting-classic-mods.md](porting-classic-mods.md) section 5 |
| skills `cltdofunc` | 95 | D2R uses up to 109; free 110-129 |
| skills `cltstfunc` | 82 (one use, 82; the rest to 53) | D2R's data goes to 61; the table has 70 slots (`0x235f590`, [d2r-93847-addresses.md](d2r-93847-addresses.md)), 62-69 free; 82 is past the end |
| missiles `pSrvHitFunc` / `pCltHitFunc` | 59 / 63 | D2R uses 0-60 / 0-65; free 61-70 / 66-80 |
| missiles `pSrvDoFunc` / `pCltDoFunc` / `pSrvDmgFunc` | 36 / 68 / 14 | D2R's data goes to 45 / 77 / 17 |
| misc `pSpell` | 9 | D2R uses -1..15; free 16-19 |
| cubemain `op` | 28 (5 rows) | D2R's data uses 28 only |
| itemstatcost `descfunc` | 28 (1-9, 11-18, 20, 22-24, 27, 28) | D2R's data uses 5, 11-19, 22-24, 27-29 (not 1-4, 6-9, 20) |
| properties `func1` | 36 | D2R's data uses 1-25, 36 |

A value above stock's range in a mod's table is the mod's own function; a value inside it is stock's. That is the
first sort for the slot-collision checklist in [porting-classic-mods.md](porting-classic-mods.md) section 5.

## Not claimed

- The mod-specific counts (how many rows a mod has, which of its ids collide) are not here; they depend on the mod.
- Behaviour of stock function bodies for the values in section 8 was not compared with D2R's; same number and
  same name is the test, and a number inside D2R's range stays `verify` until checked in game.
- Whether a stat or state a mod sets is ever read by the mod's own DLL is not decidable from tables.
