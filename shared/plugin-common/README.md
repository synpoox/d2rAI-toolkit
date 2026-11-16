# plugin-common: the shared plugin library

The code every D2RLoader plugin made with this toolkit needs, as one CMake static library (`plugin_common`). Link it
instead of copying these files into each project, so a fix lands once.

Target: **D2R 3.3.0 build 93847 + D2RLoader 1.3.1, PluginSDK 0.4.0**; parts gated by signature entries also run
on other builds where their code is found. `plugin-template/` is the working example.

| File | What it is |
| --- | --- |
| `src/build_guard.h` | Image check: the PE TimeDateStamp of the running game against `rva::ImageStamp` (`0x6ab3782c`), and the log/status line |
| `src/rvas_93847.h` | Engine facts for build 93847: `ImageStamp`, and the RVAs and record offsets by area in `src/rvas_93847/` (tables, damage, units, offsets, stats, items, levels, ai, client, pools). One header per build. The structures (`MissileParams`, `SummonParams` and the rest) and helpers are in `d2r.h` |
| `src/sig.h`, `src/sig.cpp` | The signature resolver: `sigscan::Entry` (a byte pattern and how to get the address from its match), `Find`, `Resolve` (build cache or scan) |
| `src/signatures.h`, `src/sig/` | The shared addresses as entries, `d2r::sig::<Name>` (`sig/shared.inc`), and the cache of build 93847 (`sig/cache_6ab3782c.inc`), both made by `tools/make_signatures.py` |
| `src/d2r.h`, `src/d2r.cpp` | `d2r::Bind()` (resolves the entries on any image, binds `d2r::api` from them; true only on build 93847's image, which the fixed `rva::` values need), `Engine<Fn>`, `At<T>`, `UnitXY`, `EvalCalc`, `ValidMissile`, D2 RNG |
| `src/ai_registry.*` | `ai_registry::Register(context, monaiRow, d2rThink, classId, think)`: a monster think function by monai row and monstats class, D2R's think for every other monster (`ai_registry::Vanilla(row)`); `RegisterAt(context, row, d2rThinkAddress, classId, think)` takes the think as a resolved signature address (`d2r::sig::AiMephisto.address`), the table from `d2r::sig::AiTable`; `SetBeforeThink(fn)` runs a callback before any registered think. Up to 16 rows (`MaxRows`) and 8 classes per row |
| `src/env_guard.*` | Environment guard: another mod running, the DLL outside its mod folder, a second copy, other plugins |
| `src/off_switch.*` | Reads `<name>-off.txt` beside the path you pass (the DLL or the plugin's config): part words to leave out |
| `src/parts.*` | The parts table: `{word, engine, install, state, uses}` rows, `InstallAll` (off file, unresolved entry or wrong image, log line per part) and `WriteStatus` for the console command |
| `src/level_palette.*` | `level_palette::Install`: loads a level's own legacy palette when a level change crosses a `levels.txt` Pal (no load screen), through D2R's act palette load; `NeedsLoad`, `Counters` |
| `src/log.*` | Log helper (`plog::Info/Warn/Error`, `plog::Sample` for hot paths) |
| `src/crash_guard.h` | Logs a FAULT line when the game faults: address, why, whether this plugin is on the stack |

**Policy:** every RVA in these headers has a row in `knowledge/d2r-93847-addresses.md` (RVA, signature, meaning, evidence H/C/T/R/P/D). Add the row with the value; `tests/test_rva_knowledge.py` fails when one is missing.

Only generic engine facts go in here. A value or helper only one project uses stays in that project until a second
project needs the same code.

## Use it in a plugin project

Your project needs a checkout of this toolkit (a sibling folder or a submodule). In your `CMakeLists.txt`:

```cmake
add_subdirectory(<toolkit>/shared/plugin-common plugin-common)
target_link_libraries(<your plugin> PRIVATE plugin_common)
```

That brings the include path, the PluginSDK (`D2RLPlugin::D2RLPlugin`) and C++20. The library adds the toolkit's
PluginSDK (`third_party/PluginSDK`) unless your project added one before; pass `-DPLUGIN_COMMON_SDK_DIR=<dir>` to use
another copy. Build your plugin with the static CRT (`MultiThreaded`), as the library does.

At load, in this order (see `plugin-template/src/plugin.cpp`):

```cpp
plog::Init(context, PluginName);
crash_guard::Install(PluginVersion, context->exeBase);
off_switch::Read(context->pluginPath);            // or context->pluginConfigPath
const bool imageOk = d2r::Bind(context->exeBase); // true only on build 93847: parts without `uses` need it
```

and `crash_guard::Remove()` on unload.

## Engine addresses by signature

A D2R patch moves every address. So that a plugin keeps working on a build whose code it can still find, each shared
address is also an **entry**: a byte pattern that must match exactly once in the game image's executable sections,
and how to get the address from the match. `d2r::Bind()` resolves all of them at load: on a known build from its
**cache** (the PE stamp picks it; nothing is scanned), else by a scan (0.4 s for all 362 on 93847).

```
// sig/shared.inc: D2R_SIG(name, area, kind, at, next, pattern)
D2R_SIG(AiBaalCrab, ai, Code, 0, 0, "4c 8b dc 49 89 5b 08 55 56 57 41 56 41 57 48 83 ec 70")
D2R_SIG(GetSkillRecord, units, Rip, 1, 5, "e8 ?? ?? ?? ?? 48 85 c0 74 43 44 0f b6 40 35")  // through a call to it
D2R_SIG(SrvDoTable, tables, Rip, 3, 7, "4c 8d 25 ?? ?? ?? ?? 49 83 3c cc 00")
D2R_SIG(DirectionX, units, Abs, 6, 0, "33 db 42 8b 84 33 ?? ?? ?? ?? 48 8d 54 24 20")
```

| Kind | Address | For |
| --- | --- | --- |
| `Code` | match + `at` | a function entry or a patch site, by its own bytes |
| `Rip` | match + `next` + the int32 at match + `at` | anything a call, jump or rip-relative operand points at (`next` = the end of that instruction): data, small functions, hooked entries |
| `Abs` | the uint32 at match + `at`, + `next` | a disp32 that is the RVA itself: MSVC's image-base-relative table reads (`mov eax, [rbx + r14 + table]`) |
| pattern `""` | cache only | an address no code points at (D2RLoader's own slots, `DamageTypeStepSlot`): known builds only |

For `Rip` and `Abs`, `next` also holds a field offset: a table the code only reads as `[table + 0x10]` is found
through that reference with 0x10 taken off.

`??` is any byte: rip-relative displacements, call / jump targets and other image addresses in the pattern are always
`??`, since they change with every build. An entry is resolved only for **exactly one match** whose address lies in
the image (in code for `Code`); else it stays off with a reason (`not found`, `found more than once`, ...). The
expected bytes every `InstallInlineHook` / `PatchWrite` checks stay the second line of defence.

**Two ways to an address:**

- `d2r::sig::<Name>` (the entry): `d2r::Engine<Fn>(d2r::sig::CreateMissile)`, `d2r::sig::SrvDoTable.rva`,
  `.address` (image base + RVA). Works on any build where the entry resolved.
- `d2r::rva::<Name>` (the fixed RVA of build 93847, `constexpr`): unchanged, for code not moved yet. Correct only on
  that image.

**Per-part gating.** A part lists the entries it reads in `uses`; it then installs on any image where all of them
resolved, and otherwise stays off alone, its report naming the entry (`off: engine address SrvDoTable not found on
this game image`). A part without `uses` reads fixed `rva::` values and installs only when `Bind()` returned true
(build 93847), as before. Only list `uses` when the part reads **no** fixed `rva::` value, the plugin's own included.

```cpp
sigscan::Entry* const MissileUses[] = {&d2r::sig::CreateMissile, &d2r::sig::MissileRecord, &d2r::sig::SrvDoTable};
parts::Part g_parts[] = {
	{"missiles", true, InstallMissiles, nullptr, MissileUses},  // any build where these three are found
	{"oldpart",  true, InstallOld},                              // fixed rva:: values: build 93847 only
};
```

**Record offsets** (`rva::UnitType`, `rva::SkCalc1` and the other `int` offsets) have no signature: they are
known for build 93847 only. A part that reads any lists `&d2r::sig::RecordOffsets` in `uses`: a cache-only entry
that resolves only on builds whose cache lists it, so the part stays off on a build whose offsets nobody checked.
A txt record field can instead be found at table load: "Record offsets by calibration" below.

**A plugin's own addresses** stay in the plugin (only engine facts more than one project needs go in here) and use
the same machinery: declare `sigscan::Entry` objects (pattern, kind, at, next), a `sigscan::CacheRow` table per
known build, and call `sigscan::Resolve(entries, n, context->exeBase, caches, m)` after `d2r::Bind()`.
`plugin-template/src/hook_example.cpp` is the example. Make the patterns from a dump with the same rules (or adapt
`tools/make_signatures.py`).

**A fixed RVA valid on one build only** (no pattern yet, or none possible) is an entry with the pattern `""` and a
row in that build's cache. It resolves there and stays off, `has no signature (known builds only)`, everywhere else:
the same gate as a fixed `rva::` value, but per entry and per part, for any build a plugin lists.

**Adding or changing a shared address:** add the `rva::` value (and its knowledge row) as before, then run
`py -3 tools/make_signatures.py` on the build's dump: it keeps every entry that still finds its RVA, makes the
missing ones and rewrites the cache. `tests/test_signatures.py` fails when an `rva::` value has no entry; the
`sig_dump_test` checks every pattern against the dump. **A new D2R build:** dump it, run the tests of each plugin's
parts on it, and add its cache (`sig/cache_<stamp>.inc` and a row in `d2r::sig::Caches`) once its entries are checked.

A scan finds code by its bytes, so a pattern over a function entry another plugin has already hooked no longer
matches on an unknown build: that part stays off rather than patching through someone else's hook. On a known build
the cache is used and nothing changes.

## Record offsets by calibration

`calib.h` finds a txt record field's byte offset at table load, so a part that reads it does not need a fixed value
per build. On a new build where a column moved, the part reads the new place. When the table can't single out one
place, the part stays off. It never reads the wrong field. Resurrected 09's `offsets` part uses it
(resurrected-09 `docs/offset-calibration.md`, its #323).

- **Where.** After D2RLoader's `DataTablesLoaded` event, take the compiled rows from the data table service
  (`getTable`: rows, rowCount, rowSize). Read the mod's own txt for that table set
  (`<mod>.mpq/data/global/excel/base/` for Lod and Classic, `excel/` for Reign of the Warlock) with `calib::LoadTxt`.
  Row *i* of the txt is record *i*. `Expansion` rows are skipped, as D2R skips them.
- **A field** (`calib::Field`) is a group of cells: a column and its byte offset from the field start (all
  difficulties, all numbered columns), with a kind (signed, unsigned, a bit of a flag word) and a width. A name column
  has a lookup key: the record holds the row number of that name in another txt (`Skill1` holds a `skills.txt` row).
- **The rule** (`calib::Sample`):
  - Every row is sampled. An empty cell, an unknown name, or text in a number column is no sample.
  - Every value must fit the width (`does not fit`, off).
  - A candidate offset is a multiple of the width and must hold every sample of every cell.
  - **Exactly one** offset may match. None or several is off, also on a build with a cache row.
  - The field needs at least `MinInformative` (16) rows where a cell differs from its column's most common value, or
    it is not sampled. An all-zero or nearly constant column matches any zero bytes.
- **The build cache** (`calib::Decide`). Each field lists its verified offset per PE stamp (`CacheRow`). A found
  offset that differs from the build's row is off. A field that could not be sampled (no txt, a missing column, too
  few informative rows, another row count) takes the build's row, or is off on a build without one.
- **Not sampled from a txt:**
  - A record size is the table view's `rowSize`.
  - A DataTables slot holding a table (`TablesLevels`, ...) is the one slot that holds the view's `rows` pointer, with
    its count after it.
  - Structure offsets (unit, game, path, unit skill, damage block) have no table to sample. They stay fixed, valid
    on the builds whose cache lists `RecordOffsets`, as before.
- **Don't sample a column a plugin writes** at run time (09 sets monstats `noRatio` on every record). Pick columns
  that vary in the mod's data. The informative-row count in the log says how much they do.

Inventory of `rvas_93847/offsets.h`, by whether a table can be sampled:

| Group | Offsets | Calibrate by |
| --- | --- | --- |
| skills.txt record | `SkSrvDoFunc`, `SkSrvPrgFunc1`, `SkSrvMissile*`, `SkAuraStat1`, `SkAuraState`, `SkSummon`, `SkPetType`, `SkCltMissileA`, `SkParam1-6`, `SkReqLevel`, `SkEType`, `SkSrcDam`, `SkResultFlags`, `SkHitFlags`, `SkHitClass`, `SkAuraFilter` | sampling skills.txt; name columns by lookup (missiles, monstats, states, pettype) |
| skills.txt calcs | `SkCalc1-4`, `SkCltCalc1-3`, `SkPrgCalc1`, `SkAura*Calc`, `SkPetMaxCalc`, `SkPerDelayCalc`, `SkLocalDelay` | fixed: the record holds a compiled calc index, not a txt value |
| missiles.txt record | `MsParam1`, `MsHitPar1-3`, `MsCltHitPar1-3`, `MsDParam1-2`, `MsAnimSpeed`, `MsCollideKill`, `MsSkill`, `Ms*SubMissile1`, `MsHitFlags`, `MsResultFlags` | sampling missiles.txt (`MsCollideKill` is 0/1: check its informative rows) |
| missiles.txt calcs | `MsHitCalc1`, `MsCltHitCalc1`, `MsDmgCalc1` | fixed (calc index) |
| monstats.txt record | `MonFlags` (bits), `MonSpawn`, `MonPartyMin/Max`, `MonMinGrp/MaxGrp`, `MonRun`, `MonDrain`, `MonAlign`, `MonAiDel`, `MonAiParams`, `MonAiDist`, `MonSkills` | sampling monstats.txt (resurrected-09 does `MonFlags`, `MonDrain`, `MonAiParams`, `MonSkills`) |
| monstats modes | `MonSkillModes` | fixed: the column holds monseq names whose compiled number is not known |
| other records | `LvlPal`, `LvlMon1`, `LvlNMon1`, `CsChargeVelocity`, `ItCode`, `ItNormCode`, `ItType`, `It2Handed`, `ItemPSpell`, `AffixRare`, `ObjOperateFn`, `ObjOpenFrames` | sampling the table (codes: a 4-byte code compare) |
| record sizes | `LevelRecordSize`, `CharStatsSize` | the table view's `rowSize` |
| DataTables slots | `TablesCharStats(Count)`, `TablesLevels`, `TablesLevelCount`, `TablesProgressive*`, `TablesStateCount`, ... | the slot holding the view's pointer and count |
| structures | `Game*`, `Unit*`, `Path*`, `USkill*`, `Md*`, `MonDataTypeFlags`, the damage block | fixed, `RecordOffsets` per build |

The shared fields themselves are not calibrated yet: the table lists how. A part that reads a shared txt field moves
from `RecordOffsets` to a calibrated field the first time a plugin needs one on a build with no cache row.

## Record the toolkit commit

The library changes with the toolkit, so each project pins the toolkit commit it was built and tested with:

- as a git submodule, the pin is the submodule commit (`git submodule status`);
- as a sibling checkout, write the commit in the project (for example a `toolkit.lock` or a line in its README:
  `d2rAI-toolkit 1a2b3c4`, from `git -C <toolkit> rev-parse --short HEAD`) and check it out before you build.

Update the pin on purpose, rebuild, and rerun the project's game checks before you ship.

## Tests

The image guard has a test (a fake PE header with an unknown stamp must bind nothing); `calib_test` covers the calibration rule; `sig_test` covers the pattern
matcher, the resolver and the per-part gate; `sig_dump_test` scans build 93847's dump (`D2R_DUMP_93847`, else
`C:/ghidra-work/D2RLoader_6ab3782c_dump.exe`; skipped without one). Windows with Visual Studio:

```powershell
cmake -S shared/plugin-common -B build/plugin-common -A x64
cmake --build build/plugin-common --config Release
ctest --test-dir build/plugin-common -C Release --output-on-failure
```
