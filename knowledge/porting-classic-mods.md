# Porting a classic (1.13c-era) mod to D2R 3.x

How to move a classic Diablo II mod (1.10 / 1.13c, with or without its own engine DLL) onto Diablo II: Resurrected
3.3 with D2RLoader. **Only port a mod whose creators allow it** (see the first rule below). Learned from a large classic-to-D2R overhaul port. Every example here is vanilla; the
numbers are for D2R 3.3.0 build 93847 unless marked otherwise.

Read with: [tables.md](tables.md) (how D2R reads tables), [engine-limits.md](engine-limits.md) (what D2R hard-codes),
[strings.md](strings.md), [hd-graphics.md](hd-graphics.md), [engine-re.md](engine-re.md) (finding code),
[d2rloader.md](d2rloader.md), [crash-triage.md](crash-triage.md).

## 0. Policy (decide these first)

| Rule | Why |
|---|---|
| **Follow the original mod, not D2R.** Where the two disagree on a rule, the original mod wins; note every place where you could not follow it | Players of the original know its rules; "D2R does it differently" is a bug report waiting to happen |
| **Port only with the mod creators' permission.** Ask before any work starts, keep their answer, and follow their terms (credit, whether and where the port may be published, what may be changed). No answer or a no means no port | The mod is their work; a port without permission takes it from them |
| **Never ship Blizzard's files or the original mod's archives** in your repo | Players own D2R; the original mod's files come from its own release |
| **HD first.** Make every feature work in HD graphics; classic graphics (the G key) come later | Almost every D2R player plays in HD, and both modes load different files |
| **Stand-in art first, custom art last.** Give every new monster, missile and item the closest vanilla look until the rules work | Art is the biggest single job; gameplay bugs are found faster with a playable build |
| **Keep a deviations ledger** (section 10) | So "missing" never gets mistaken for "broken" |
| First milestone: **a new character in Act 1** as early as possible | From then on, work from what breaks in game |

### 0a. Decisions to make first

Three decisions shape the whole port. Make each one before converting data, write down the choice, and record
who approved it. Each is shown as options and consequences, not as the one right answer.

**Bank choice.** D2R 3.3 loads two banks of tables: Reign of the Warlock (RotW) and the Lord of Destruction (LoD/classic) bank.

| Option | Consequence |
|---|---|
| RotW bank only | Half the tables to maintain. LoD and Classic characters cannot use the mod. D2R-only rows keep their ids (itemtypes `warl` is at id 67 in both banks) |
| LoD bank only | The Warlock is not playable; the LoD bank still carries Warlock placeholder rows at RotW's ids, so ids do not shift |
| **Both banks** (this guide's default; see "Banks" in section 3) | Double the maintenance and the testing |

**Generated data.** Data is generated from an extract of the original and is never committed (section 2). Whether the
extract is pinned by hash is a choice (options in section 2).

**Extended saves, append-only ids.** Retail D2R saves hold 30 class skills per class and 9-bit stat ids (up to 511).
Ids that appear in a save are assigned once and are append-only: renumbering a row breaks every existing character.

| Option | Consequence |
|---|---|
| Stay within retail saves | Cut or merge what does not fit; characters stay portable between installs |
| Extended saves (a plugin-owned save sidecar) | More skills and wider stats; the characters need the mod ([saves.md](saves.md)) |

### 0b. Glossary of fidelity terms

| Term | Meaning |
|---|---|
| **Baseline** | The original mod, as its own players know it |
| **Deviation** | Any observable difference from the baseline |
| **Exact** | The player observes the same values as in the baseline |
| **Approximated** | Reproduced roughly, with the difference stated |
| **Cut** | Not reproduced |
| **Not yet** | Intended, not built |
| **Function-equivalent** | A hook parity tier: the same function result for the same inputs, reached by different code or timing; the difference is stated |
| **Router slot** | One free table slot (for example srvdofunc 190) holding a plugin function that picks among several of the mod's functions by skill id. It is a plugin pattern, not part of D2RLoader |
| **Companion plugin** | A plugin built outside the port and bundled to stand in for a feature. What it lacks is a deviation |

- Fix the port-wide decisions early (game and loader versions, data before code, save format from the first build):
  [ai-workflow.md](../docs/ai-workflow.md) "Decisions for a port".
  Terms such as reference install, deviation and table set are in the glossary at the end of this file.

## 1. Inventory the mod

Before converting anything, write down:

| Question | Where to look | Why it matters |
|---|---|---|
| Game version (1.10, 1.13c, 1.14d) | The mod's readme, its launcher, the version of `Game.exe`/`D2Game.dll` it ships or patches | Table layouts and function numbers differ per version |
| Does it ship an **engine DLL** or patch the game's DLLs? | Extra `.dll` files, a plugin loader, `.dll` hashes that differ from vanilla | Everything that DLL does must be re-done in a D2RLoader plugin or dropped |
| Which **extra tables** the DLL reads | Files in the mod's `data/global/excel` that vanilla does not have; strings the DLL opens | They hold rules D2R will never read |
| Which **function numbers** it adds | Values in `srvdofunc`, `cltdofunc`, `pSrvHitFunc`, `pSpell`, `func1`, cube `op`, `descfunc` above vanilla 1.13c's range | Each one is engine code to port ([engine-limits.md](engine-limits.md), "function numbers") |
| Which **events** it raises | Rows in `events.txt` after vanilla's | D2R raises only its own events (section 6) |
| Its row counts | Every table | D2R has a 32,768-row limit per table |
| Its art formats | `.dc6`, `.dcc`, `.cof`, `.dt1`, `.ds1` | Classic mode can use them; HD needs `.sprite` and models |
| Saves | Does it change the save format (more skills, wider stats, extra stash pages)? | D2RLoader's extended save format may be needed |

Triage the engine DLL by its source files: its assert strings usually name them (`..\SkillFoo.cpp`). Sort each into
(a) data only, (b) a D2RLoader service, (c) a native hook, (d) a UI rebuild, (e) cut, and keep the list.

### 1a. DLL triage from strings

1. Hash the mod's DLLs against stock 1.13c ([classic-113c-tables.md](classic-113c-tables.md) section 1). A mod DLL
   that is a separate file patching stock code in memory is read through its patch table (section 6a).
2. Extract the strings. Assert strings name source files (`..\SkillFoo.cpp`); table names and column names the DLL
   opens show which extra tables it reads; format strings show messages it builds.
3. One row per source file or per rule in the hook list (section 5b). Bucket it:

| Bucket | Test | Result |
|---|---|---|
| a data | A table column D2R reads already expresses the rule | Convert the rows; no code |
| b service | A D2RLoader/PluginSDK service does it (strings, sounds, saves, shared parts) | Use the service |
| c native hook | Only code can do it (skill function, missile function, event raise) | Plugin hook; slot per section 5a |
| d UI rebuild | A screen the engine draws (stash pages, panels) | UI work, HD first |
| e cut | The rule has no reachable data or the cost is not worth it | Deviations ledger (section 10) |

4. Put the unknowns last. A source file with no assert strings gets its bucket from what its patch records change.

## 2. The data pipeline

1. Extract the mod's archives (MPQ) and D2R's files (CASC; `python -m modkit fetch`) into folders that git ignores.
2. Decode the mod's tables to text if they are `.bin`; decode its formulas.
3. Merge them into D2R's layout table by table (section 3), into a build folder.
4. Validate every field against D2R's own data guide (`data/global/dataguide/`). Aim for 0 errors.
5. Install into `<game>/mods/<Mod>/` with the game closed; start through D2RLoader; read `d2rloader.log`.

Rebuild from scratch every time; never hand-edit the build output.

**Decisions this pipeline implies** (see section 0a): the data is **generated from an extract of the original's files
and never committed**. Write the merge output into git-ignored folders. Pinning the extract by hash (recording the
hash of each source archive in the generator so a different extract fails loudly) is recommended, not required.

| Option | Consequence |
|---|---|
| Commit the generated patches | The repo then holds the original's data: not allowed (section 0) |
| Generate into git-ignored `files/` from a hash-pinned extract (recommended) | Every build needs the install; CI cannot build it; re-baselining the source is a hash change plus fixes to the merge rules |
| Generate from an unpinned extract | No hash upkeep; a changed or patched source drifts silently into the output |

## 3. Table by table

### How rows merge

| Kind of table | Examples | Rule |
|---|---|---|
| **Indexed** (read by row number) | skills, states, itemstatcost, missiles, monstats, monstats2, overlay, properties, levels, objects, pettype, monai, itemtypes | Keep **D2R's own added rows at their numbers**; the mod's rows at its numbers where they don't clash; the mod's extra rows **after D2R's last row**. Every reference to a moved row must be remapped (section 4) |
| **Replace** (the mod's rows only) | weapons, armor, misc, treasureclassex, magicprefix/suffix, uniqueitems, setitems, sets, runes, cubemain | Merging D2R's vanilla rows back lets vanilla items drop through the automatic treasure classes |
| **D2R wins** | sounds, skillcalc, misscalc, playerclass, plrtype, storepage | D2R's rows first; the mod's extra codes appended |
| **Keyed** (the rest) | | The mod's rows, then D2R's rows whose key the mod lacks |

Anything that has no D2R column goes to an overflow report. Nothing is dropped silently.

Which tables, columns, events and save fields differ between **stock** 1.13c and D2R 3.3 (checked against stock files,
not against a mod) is in [classic-113c-tables.md](classic-113c-tables.md). Use it to tell the original game from what
a mod added.

### Column differences (1.13c -> D2R 3.x)

| Table | Classic | D2R | What to do |
|---|---|---|---|
| skills `anim` / `seqtrans` (plrmode and monmode are identical, see [classic-113c-tables.md](classic-113c-tables.md)) | Sequence mode spelled `GH` | `Code` is `SQ` (sequence), `KB` (knockback) | Skills' `anim`/`seqtrans` `GH` -> `SQ`; never change D2R's `Code` column |
| overlay | `Character` empty | `Character` = HD overlay folder | Fill it from D2R's matching row |
| missiles | `Range` + `LevRange` | `Range` is an expression | `Range` = `base+LevRange*lvl` |
| inventory | one row per page | two rows per page (two screen layouts) plus new pages | Set grid sizes on every matching row |
| skills | srvdofunc up to ~152 | 153-171 are D2R 3.x functions | Move the mod's 153+ functions to 172-190 (section 5) |
| skills | `leftskill` / `rightskill` often ignored by the mod's DLL | D2R honours them | Section 7 |
| misc | `pSpell` up to whatever the DLL handles | D2R's table has 20 entries | Map to D2R's spell or a plugin slot 16-19 |
| itemtypes | no Warlock rows | D2R 3.x added rows (`warl` at 67) | Keep D2R's rows at D2R's numbers (section 4) |
| All tables | `-1` sometimes stored as `4294967295` or `255` | signed | Compare every numeric column with D2R on shared rows to find decode slips (`coldeffect` 236 instead of -20) |
| Banks | one `excel/` | `excel/` (RotW) and `excel/base/` (classic/LoD) | Write both banks until you know which one the mod's characters load |

Starting from 1.09d tables instead of 1.13c: 1.09d has 75 tables to 1.13c's 92, refers to rows by number where 1.13c
uses names, and stores skill and missile source damage in eighths (x16 to reach 128ths). The findings and the column
map are in [classic-109d-tables.md](classic-109d-tables.md).

### Columns D2R has and 1.13c lacks (D2R 3.3, build 93847)

`shared/classic_import/ids.py` fills these on a merged table (`DERIVED`, `derive`, `stat_display`). Counts are from
D2R 3.3's own tables, build 93847.

| Table.column | D2R's rows | Rule for a merged row |
|---|---|---|
| skills.`rightskill` | class skills (`charclass` set): 210 hold 1 and are not passive, 30 passive ones hold 0. Non-class skills (monster skills): 155 hold 0, 33 hold 1, 1 is blank | Set it on class skills only (1, or 0 when `passive` is 1). Leave a non-class row's cell: forcing 1 on a monster skill changes D2R's value |
| setitems.`spawnable` | 136 rows hold 1, 5 are blank | 1 |
| itemtypes.`MaxSocketsLevelThreshold1` / `2` | 109 rows hold 25 / 40, 1 is blank | 25 / 40 |
| itemstatcost.`descstrpos` / `descstrneg` | The strings carry the value's format code (`%+d to Strength`); a 1.13c `descfunc` / `descval` prints the value before the text | A row whose strings D2R already uses takes that D2R row's `descfunc` / `descval` (its own row when the strings are unchanged, else the D2R row with the same `descfunc`, else the first) |
| itemstatcost `descfunc` 27 / 28 | 1.13c hard-codes their text (class skills, all skills of a class); D2R reads it from `descstrpos` / `descstrneg` | A merged row with no strings and its D2R row's `descfunc` keeps D2R's strings |

### Row limits

A big overhaul can have several times D2R's row counts in skills, missiles, monstats and cubemain and still stay
far under the 32,768-row limit. More than 511 states load with an assert and work under D2RLoader 1.3.1's wide-state
sync (see [engine-limits.md](engine-limits.md)). Key lengths are the real limit: see the dataguide `dataLength`
values in [engine-limits.md](engine-limits.md).

## 4. IDs: what may move and what may not

**D2R-only rows must stay at D2R's own numbers.** D2R.exe tests many IDs with numbers written into its code. If a
merge puts the mod's rows first and appends D2R's new rows at the end, every ID after the first D2R-only row shifts,
and the engine's built-in checks hit the wrong rows.

Worked example, itemtypes: D2R 3.x has the Warlock type `warl` at row 67. A classic mod has no row 67 of that kind,
so a naive merge numbers `h2h` as 67 instead of 68, `rune` as 74 instead of 75, and so on. D2R's code asks "is this
item of type 75 (rune)" in about ten places. With the shift, its rune test hits circlets: picking up or wearing any
circlet runs the socket-filler code and asserts `UnitGetType(hUnit) == UNIT_ITEM` (ItemMode.cpp:676) and the game
hangs or dies; socketed runes apply none of their gems.txt mods.

Item type ids the engine tests by number (build 93847, `0x373890(item, type)` call sites with an immediate >= 67):

| Id | Code | Id | Code |
|---|---|---|---|
| 68 | h2h | 81 | apot |
| 73 | pelt | 82 | wpot |
| 75 | rune | 83 | scha |
| 77 | hpot | 84 | mcha |
| 96 | gem4 | 58 | jewl (below 67, also tested) |

Rules:

- Count rows the way D2R does: every row except those whose key is `Expansion` (a blank-key row is a record).
- Put each D2R-only row at its D2R number; give the mod's rows the numbers around it. Then remap.
- **Remap every reference** after rows move: skill and monster parameters in item, affix, recipe and monprop
  properties (oskills, procs, charges); `reqskill`, `srcmissile`, sub-missiles; skill-desc rows; level ids in
  portals; monster ids in missiles (below). A mismatch gives the wrong skill, not an error.
- Missiles whose **server hit function is 6** spawn the monster row in `sHitPar1`. That parameter is a monstats ID
  and must go through the monstats remap too. If it doesn't, every hit spawns some other monster next to the
  player (in one port, an invisible dummy whose broken sound crashed the client).
- Add a self-check: at build time compare your ids against D2R's for every D2R row; at run time a plugin can check
  the same (the template's `item_type_check.cpp`).

## 5. Function numbers

D2R 3.x reused classic "free" slots for its own skills. Values that meant the mod's functions now run D2R's code.

| Column | D2R 3.3 uses | Free | Classic trap |
|---|---|---|---|
| skills `srvdofunc` | 1-171 | **172-190** | A classic DLL's 153-171 are D2R 3.x skills now. Put new server functions at **172+** |
| skills `srvdofunc` 109 | D2R's itemless Town Portal | | 1.13c's 109 (monster frenzy) was merged into 9 (Frenzy) |
| skills `srvstfunc` 64 | D2R's Bind Demon | | 1.13c's 64 (frenzy start) -> use 67 |
| skills `cltstfunc` | max 61 | **62-69** | Classic 82 is past the end of D2R's 70-slot table: use none |
| skills `cltdofunc` | 1-109 (96-109 are D2R 3.x skills) | **110-129** | Classic 96-99 run D2R's Volcano / Sigil / Ring of Fire client code |
| missiles `pSrvHitFunc` | 0-60 | 61-70 | |
| misc `pSpell` | -1..15 | 16-19 | 20+ does nothing |

Before writing code, look for a D2R function that does the same with other table values: an itemless town portal
is D2R's 109; a timed potion is `pSpell` 3; resurrect is Revive's function; a storm of missiles is Armageddon's.
Audit every row against D2R's function tables and fail the build on a classic number that D2R reassigned.

### 5a. Slot-collision checklist

Run it per function column before writing code. Stock ranges are in
[classic-113c-tables.md](classic-113c-tables.md) section 8.

1. List the **distinct function numbers** per column in the mod's tables.
2. Compare with stock 1.13c's range for that column. A value above it is the mod's own function; a value inside it
   is stock's.
3. Compare with D2R's used range and free slots (table above). srvdofunc has 191 slots at `0x238ea00` (build 93847);
   free slots: srvdofunc 172-190, cltdofunc 110-129, pSrvHitFunc 61-70, pSpell 16-19.
4. **Same-name comparison**: does D2R use that number for a skill or missile of the same name? If yes the number
   probably still means the same thing; keep it and mark `verify`.
5. Check numbers **inside** D2R's range that mean something else (misc `pSpell` 12 is D2R's Resist Scroll, 13 its
   respec token).
6. Several kinds of function column may need one pool of slots (the `prg` functions with the do tables). This is a
   hypothesis, not verified.
7. Port **events by name**, not by index (section 6).
8. D2R's function tables are filled at run time: **log the non-null slots** once the game is up instead of trusting
   a static dump.
9. **Reachability pass**: which rows can the data reach at all (spawnable, in a tree, in a treasure class, in a
   recipe)? A rule no row reaches is `unreachable` in the hook list below.

### 5b. Hook list (template)

One row per rule of the original engine DLL. Keep it in the repo next to the port; it is the contract for the plugin.

| Column | Holds |
|---|---|
| Rule | What the original does, in one sentence |
| Source | The table column and value, or the engine DLL source file named by its assert strings |
| Bucket | a data, b service, c native hook, d UI rebuild, e cut (section 1) |
| D2R slot | The free slot the function takes; `->` marks a re-map (`153 -> 172`) |
| RVAs | Names only; the values live in the per-build header. `?` = not located |
| Tier | Exact or Function-equivalent |
| Size | S under 1 session, M 1-2, L 3+ |
| Status | spiked, open, verify, data, unreachable, cut |
| Test | The in-game check |
| Work item | The issue |

Prefer a PluginSDK service before a native hook, and a data change before either.

## 6. Events and behaviour D2R never raises

The mod's DLL may raise events that vanilla 1.13c also had in its table but never sent, or add its own rows to
`events.txt`. D2R raises only its own. A property listening to such an event is silently dead.

Worked example: **cast on death.** A classic engine DLL wrapped the unit death function and raised a new event
("the unit dies", a row it added to `events.txt`) on the victim before every death. Monster properties used it for
death novas and exploding summons. In D2R the rows load fine and nothing ever fires.

Port: hook D2R's unit death function (`0x44db20` in 93847, `(game, victim, killer or null, flag)`), and before the
original runs, raise the event through D2R's unit event dispatcher (`0x44d570`, `(game, event, unit, other, 0)`) on
the victim with the killer as the other unit. Read the event id from the stat's itemstatcost record so a renumbered
events.txt keeps working. Skip units already dying or dead (the death function itself returns at once for a
monster in mode 0 / 12 or a player in mode 0 / 17), or you raise it twice.

Others seen:

| Classic behaviour | D2R | Port |
|---|---|---|
| **Ranged pets**: the mod's summon code read a flag in one of the summon skill's `Param` columns and switched the pet's AI to its ranged branch | D2R's summon function has no such step: the pet melees | Plugin: after the pet is made, set its AI control field (observed in 93847: monster data `+0x30` -> `+0x44 = 1`, `+0x48 = 0` picks the NecroPet ranged branch) |
| Raven-AI pets: attack count = `Param1 + (lvl-1)*Param2` (a negative Param1 made a pet permanent) | D2R takes the count from the skill's **`calc3`** | Write the count formula into `calc3` (e.g. `ln12`), or the pet dies on its first think |
| The mod's skill picker ignored `leftskill` / `rightskill` | D2R honours them | Section 7 |
| Cube output "open a portal" for any level | D2R's `Cow Portal` output is fixed to the Cow Level; `Red Portal,lvl=<id>` (handler `0x5da800`) opens any level of the same act | Write `Red Portal,lvl=<id>`; a per-use destination or another act needs a plugin |
| A classic timed potion added its stat as is | D2R's timed potion (`pSpell` 3, `0x57ecb0`) treats a stat's calc as the **total over the duration**, except hitpoints, mana, manarecovery and hpregen; every other stat is stored as calc / len | Multiply the calc by the `len` formula for those stats |
| Quest kill handlers | D2R runs a quest's kill handler only while the quest is still open in that difficulty | Test with a character whose quest is open |

### 6a. Rules stock 1.13c never reads, and reading a patch table

- **`states.immed`**: stock 1.13c carries the column but its states loader has no field for it and no stock DLL looks
  it up. A mod that sets `immed` changed nothing: cut the column, build no rule. Evidence and the method for any
  doubtful column: [classic-113c-tables.md](classic-113c-tables.md) section 7.
- **Events past row 12** (`levelup`) are the mod's or D2R's own; match by name (section 4 of
  [classic-113c-tables.md](classic-113c-tables.md) lists the three banks).
- A classic mod's engine DLL usually patches stock code with a table of patch records (`dll, offset, target, type`).
  Read it as facts about stock 1.13c: each offset is a place in a stock DLL (hash the mod's DLLs first), each `call`
  names the vanilla function it replaces. Method: [classic-113c-tables.md](classic-113c-tables.md) section 6. A
  record gives a **rule** to re-check in D2R, never bytes to port.

## 7. Skills that can't be selected

D2R's skill picker uses `leftskill` / `rightskill`; many classic DLLs did not.

- **Every active skill needs `rightskill 1`**, including the class-less **innate skills** that `charstats` gives
  every character (`Skill 1-10`, `StartSkill`). A `leftskill`-only skill with `TargetableOnly 1` turns a click on the
  ground into a walk, and Quick Cast does nothing without a monster under the cursor (as vanilla Leap Attack).
- D2R does not quick-cast a targeted melee skill (`range h2h`, `TargetableOnly 1`) with no target. That is vanilla,
  not a bug.
- More than 30 class skills per class needs D2RLoader's extended save format.

## 8. Strings, sounds, icons

**Strings.** Use a D2RLoader string namespace for the mod's own keys; put new text for keys D2R already has into
one override file. Never append a numeric id of 65,536 or more: D2R matches ids by
their low 16 bits, so such an id collides with a lower one (an NPC greets with a skill name). Ids below 65,536 that
no string uses are safe; the budget and the evidence are in [strings.md](strings.md). Keep D2R's printf placeholders per key (`sysmsg7-9` "was slain by" crashed the
client on death when the classic text had a different `%s` count). Details: [strings.md](strings.md).

**Sounds.** New sound rows are appended to `sounds.txt` and referenced by name. A name that does not resolve becomes
id -1, and several D2R client sound readers crash on an id outside the table instead of skipping it. Also, on the
start where D2RLoader builds its table cache, the game loads D2R's own sounds table, not the mod's
([d2rloader.md](d2rloader.md)). A plugin sound guard covers both (the template's `sound_guard.cpp`).

**Skill icons.** Classic class sheets store two frames per icon (normal, pressed). A **shared** icon sheet (attack,
throw, item skills) may store **one frame per icon**: read each sheet's real layout, don't assume pairs. HD icon
strips are capped at 16,384 px (62 icons at 130 px with pressed frames), see [engine-limits.md](engine-limits.md).

## 9. Graphics

- **HD first.** Item pictures need entries in `data/hd/items/items.json` / `uniques.json` / `sets.json` (a missing
  one crashed vendors); missiles need `missiles.json`; sequence skills need an HD state; overlays need `Character`.
  See [hd-graphics.md](hd-graphics.md).
- **Stand-ins**: reuse the closest vanilla HD model for each new monster and missile (a new cold skeleton mage gets
  the vanilla cold skeleton mage, scaled), the closest vanilla item picture of the same type, and recolour later.
- New HD models and textures at **new paths** need entries in the model and texture indexes
  (`data/hd/model_lod_desc.bin`, `data/hd/texture_desc_cache.json`), or they load but are never drawn.
- **Classic mode** still reads `.cof`/`.dcc`/`.dc6` and the `.dt1`/`.ds1` tiles even in HD (monster COFs for timing,
  tiles for areas). Ship every classic file the tables reference, or the game crashes on spawn or area entry.
- Upscaling classic DC6 bilinearly is an acceptable first HD picture for items and panels.

## 10. The deviations ledger

Keep a table of what the original mod has and the port does not, with the reason. Example rows:

| Feature | Why not ported | What players see |
|---|---|---|
| A portal from a scroll to a level above 255 | D2R's portal setter clears the high byte | Plugin writes the high byte; until then the scroll does nothing |
| Item skill icons beyond 62 shared icons | HD strip limit | Those skills show a generic icon |
| Cross-act portals | D2R links portals within one act | Portal opens only in its own act |
| Classic-mode panel art | HD first | Classic panels are vanilla |
| A rule the original engine DLL implemented and no plugin does yet | Not ported yet | Name the rule and its workaround |

### 10a. Deviation status vocabulary and the D2R-only ledger

Every difference from the original is a **deviation** (section 0b glossary). Give each one a status from this list, in
the deviations ledger (`templates/deviations.md`), and use these words:

| Status | Meaning | Next step |
|---|---|---|
| **cut** | Not reproduced, by decision | Reason and what players see; reopen only by a new decision |
| **not yet** | Intended, not built | Owner, work item, size |
| **approximated** | Reproduced roughly | State the difference in numbers or behaviour |
| **exact** | Matches the original (for a hook, the parity tier is Exact or Function-equivalent, see section 0b) | Test that proves it |

**D2R-only content.** D2R has content the original never had (rows past the original's last, new areas, items, recipes,
runes, monsters). A port chooses how to treat it. Options:

| Option | Consequence |
|---|---|
| Keep D2R-only content on by default; switch items off only with a recorded approval (an approval ledger) | Players get D2R's extras and the port needs no per-item work up front; it drifts from the original wherever nobody objected |
| Switch D2R-only content off by default; switch items on only with a recorded approval | Closest to the original; more rows to switch off and keep switched off as D2R adds content |
| No ledger; decide case by case | Least paperwork; no record of why something is on or off |

Whichever is chosen, record it as a decision (section 0a). A port that keeps an approval ledger can use one row per
item or group:

| Column | Holds |
|---|---|
| Content | The D2R rows, by table and name |
| Decision | Keep on or turn off (the opposite of the port's default, with its approval) |
| Approved by, date | Who said so, and where it is recorded |
| How it is off | Keep the row in place for id stability (section 4) and switch it off in data: `spawnable 0` (or `disabled`), removed from treasure classes, recipe disabled, area unlinked. Never delete the row |
| Test | How you check it is off (a drop run, a recipe attempt, a walk to the area) |

Large items (a whole area, a class, a system) can get a decision ticket first and an approval before the ledger row.

## 11. Testing a port

- Keep a testing table (change, how to test, expected result). The player or tester runs batches.
- Write in-game checks for what you fix, where the toolkit or your harness allows.
- Test with mortal characters too: a god-mode character skips the damage path where many crashes live.
- Reset the test character's quests between runs; finished quests skip their handlers.
- When a crash comes from a player, go to [crash-triage.md](crash-triage.md).

## Starting from 1.09d (pointers)

A port that starts from Lord of Destruction 1.09d (not 1.13c) needs the 1.09d facts:

- Table schemas, number against name references, `SrcDam` x16, row shifts, `.bin` against `.txt`:
  [classic-109d-tables.md](classic-109d-tables.md).
- Skill, missile and monster-AI code, class row ranges, the `BaseId` AI index and the moved `AIParam` slots:
  [classic-109d-engine.md](classic-109d-engine.md).
- Rules the engine code changed (leech, damage reduction cap, gambling, item generation, breakpoints):
  [classic-109d-vs-d2r.md](classic-109d-vs-d2r.md).
- Which files are stock 1.09d: [classic-reference-installs.md](classic-reference-installs.md).

## Glossary

| Term | Meaning |
|---|---|
| **Reference install** | The frozen, hash-recorded classic game files (for a 1.09d port, Lord of Destruction 1.09d) that every comparison is made against, for every game mode. Not a third-party mod's folder |
| **Deviation** | Any listed way the port differs from the reference, kept on purpose and checked by a table diff |
| **Table set** | One of D2R's two copies of the tables: `excel/base/` (read by Expansion / Lord of Destruction characters) and `excel/` (read by Reign of the Warlock characters). What to write into each is in section 3, "Banks" |
| **Column map** | The mapping from each column of one classic version's table to the other version's column or columns, with the transform each needs (for example 1.09d to 1.13c). Generated from scripts, never hand-edited |
| **Rename map** | The short list of columns D2R renamed from 1.13c, used when merging 1.13c-shaped tables onto D2R's. Not the column map |
| **Placeholder row** | A D2R row with no counterpart in the reference, kept disabled at its row number so the rows after it keep theirs (the Warlock rows, content added after the reference version). Rows a kept convenience needs stay enabled and are listed as deviations |
| **Classic import** | Turning classic `.txt` tables into D2R's schemas (`shared/classic_import`) |
