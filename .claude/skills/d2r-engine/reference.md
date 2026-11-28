# Engine work: D2RLoader plugins and reverse engineering

Data first: check ${CLAUDE_PLUGIN_ROOT}/knowledge/engine-limits.md and the vanilla function catalogs (`python -m modkit functions`)
before writing code. When code is needed, read ${CLAUDE_PLUGIN_ROOT}/knowledge/engine-re.md and ${CLAUDE_PLUGIN_ROOT}/knowledge/d2r-93847-addresses.md, and
${CLAUDE_PLUGIN_ROOT}/knowledge/d2rloader.md for what the loader does on players' machines. Check
${CLAUDE_PLUGIN_ROOT}/knowledge/d2rloader-capabilities.md (the capability matrix for loader 1.3.1 / SDK 0.4.0, and the
loader gaps) before you plan a service call or a hook; an item that is reusable or holds charges starts with
${CLAUDE_PLUGIN_ROOT}/knowledge/charged-items.md. Porting a classic engine DLL: the `d2r-port`
skill first. A whole new game system (a mapping system, a new crafting bench, a new panel): plan it with
${CLAUDE_PLUGIN_ROOT}/knowledge/new-game-systems.md first (player steps, data vs plugin split, an RE spike for every hook, where state
lives), then build it part by part with this skill.

## The plugin
1. Copy `${CLAUDE_PLUGIN_ROOT}/plugin-template/` into the mod project (e.g. `<project>/plugin/`), build with
   `powershell -ExecutionPolicy Bypass -File plugin\build.ps1 -Name <mod>-core` (add `-Toolkit ${CLAUDE_PLUGIN_ROOT}` if the build
   does not find the toolkit by itself, see docs/toolkit-finder.md). Add the DLL path to mod.json `plugins`; `modkit install` copies it to
   `<game>/mods/<Mod>/d2rloader/plugins/`. Players run the mod through D2RLoader. Keep `src/plugin.rc` (the ABI
   manifest resource) in every plugin, including one written from scratch: without it D2RLoader rejects the DLL as
   "an old alpha plugin" (${CLAUDE_PLUGIN_ROOT}/knowledge/d2rloader.md).
2. New hooks resolve by unique signature, never fixed RVA. Signature-only parts install on any image where all their declared signatures match exactly once; otherwise disable that part alone. Existing fixed-RVA parts require their exact image stamp (0x6ab3782c = reference build 93847). Re-verify addresses and ABI after game/loader updates; never infer compatibility from one build. Installer requirements use major.minor, not build number.
3. Keep the template's guards on: image guard for fixed-RVA parts, signature uniqueness for signature-only parts, environment guard (other plugins,
   stray copies, `default_mod`), sound guard (bad sound ids, the cache-building start), item type id self-check.
   Each part has a status line in the `<plugin>` console command and one log line at load (`log.h`).
4. Every feature has a word in the off-switch file `<plugin>-off.txt` (next to the DLL): list words to turn
   features off when bisecting a crash. Keep this for every feature you add.

## Common jobs
- **New skill function**: write `int64_t Fn(Game*, Unit*, int32_t skillId, int32_t level) noexcept` in
  `skill_functions.cpp`, register it in a free srvdofunc slot (172-190; D2R uses up to 171), set the skill's
  `srvdofunc` to that number. The template's slot-172 missile fan shows target lookup, calc evaluation and missile
  creation.
- **Hook a function**: resolve a unique signature first; `InstallInlineHook(rva, entryBytes, size, Hook, &original)` describes the lower-level validated operation, not permission to hard-code an RVA. Entry bytes must be whole
  instructions (REX prefixes like 40/48 included), copied from the disassembly (`Disasm.java`), ending on an
  instruction boundary. There is no 14-byte minimum: 8- to 12-byte signatures ran in game; longer is only safer
  against a false match (${CLAUDE_PLUGIN_ROOT}/knowledge/engine-re.md section 6). The SDK refuses on mismatch. Hook function pointer types must be `noexcept`.
- **Resolve the address by a unique byte signature at load** (`sigscan::HookBySignature`, plugin-common `sig_hook.h`), never a fixed RVA; the RVA is only the build-93847 reference (${CLAUDE_PLUGIN_ROOT}/knowledge/engine-re.md, "Resolve addresses by signature").
- **One owner per hook site**: two plugins hooking the same entry disable each other by load order. Search your
  plugins for the address first; one site, one owner (${CLAUDE_PLUGIN_ROOT}/knowledge/engine-re.md section 5).
- **Before patching anything**, check the function entry for `FF 25` (jmp [rip+x]): D2RLoader already hooks it
  (e.g. its wide state sync). Work with D2RLoader's exports instead of fighting them; patching state arrays yourself
  broke monster hover and overlays in a past port.
- **Table slots** (do-function tables, missile/item function tables): `PatchWriteU64(rva, expected, size, value)`
  with the slot's current bytes as expected (zero for empty slots).

## Finding code (Ghidra)
1. With the game running through D2RLoader: `python ${CLAUDE_PLUGIN_ROOT}/tools/dump_image.py` (D2R's code is encrypted on disk; the
   dump is the in-memory image, RVA = address - image base). Analyse once: `${CLAUDE_PLUGIN_ROOT}/tools/ghidra_analyze.ps1` (hours).
2. Query read-only: `powershell -ExecutionPolicy Bypass -File ${CLAUDE_PLUGIN_ROOT}/tools/ghidra_query.ps1 <Script>.java args`:
   `StringXrefs <text>`, `NearRefs`, `Refs <rva>`, `Decompile <rva>`, `Disasm <rva>`, `FindDisp <offset>`
   (users of a struct field), `FindSwitch <bound>` (switches with N cases), `FindPtrTables` (dispatch tables),
   `FuncsInRange <lo> <hi>` (functions in a range, with callers), `RangeAsm <startRva> <endRva>` (instructions in a
   range).
3. Fastest lead: D2R keeps its source paths in asserts (`D2Game\src\Player\PlrTrade.cpp`,
   `D2Common\src\DataTbls\HoradricCube.cpp`): StringXrefs the file name -> NearRefs the descriptor -> Refs the
   tiny assert stub -> the functions of that source file. Then decompile and match by constants, switch shapes and
   record offsets (FindDisp on a data-table offset lists every reader of a table).
4. Record every confirmed address in ${CLAUDE_PLUGIN_ROOT}/knowledge/d2r-93847-addresses.md (or your build's file) with its signature, uniqueness result in the target dump, and entry bytes. Mark static RE separately from runtime proof.

## Debug
Logs and crash dumps: d2r-debug skill. Add one log line per feature at install (installed / skipped and why).
