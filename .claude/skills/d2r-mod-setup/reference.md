# Set up the toolkit and a mod project

## One-time setup (Windows)
1. Prerequisites: D2R installed (default `C:\Program Files (x86)\Diablo II Resurrected`; else set `MODKIT_GAME`),
   Python 3.12+, git, CMake and Visual Studio C++ build tools (for CascLib and plugins). D2RLoader
   (https://github.com/D2RLoader) is needed only for plugins or extended saves.
2. `git submodule update --init` then `powershell -ExecutionPolicy Bypass -File ${CLAUDE_PLUGIN_ROOT}/tools/build_casclib.ps1`
   (reads the game's CASC storage).
3. `python -m modkit fetch` copies the tables, strings, UI layouts and data guide into `d2r-data/<build>/`
   (git-ignored: Blizzard's files are never committed). Other files are fetched on first use.

## A new mod
`python -m modkit new <dir> --name <ModName>` creates:
- `mod.json`: name, savepath (its own save folder), `extendedSaves` (D2RLoader extended save format: needed for
  more than 30 skills per class or wide stat/item IDs), `plugins` (built plugin DLL paths). `modkit new` does not write `namespace`; add it yourself to opt in to D2RLoader
  string namespaces (install writes it to `d2rloader/metadata.json`; 1-256 letters, digits, `-`, `_`, `.`; ${CLAUDE_PLUGIN_ROOT}/knowledge/strings.md).
- `patches/`: JSON change lists (${CLAUDE_PLUGIN_ROOT}/knowledge/modkit-ops.md), applied in name order on pristine game files.
- `assets/`: PNGs etc. that patches use. `files/data/`: files shipped as they are.
Keep the mod project in its own git repo: patches are text, review them like code.

## The loop
1. Write or change a patch (use the d2r-skill / d2r-items / d2r-monsters / d2r-ui / d2r-cube skills).
2. `python -m modkit build <dir>`: rebuilds `out/data` from scratch and validates (`out/validation.md`). Fix all
   errors; read warnings.
3. Close the game, then `python -m modkit install <dir>`: copies into `<game>/mods/<Name>/` with modinfo.json
   and D2RLoader metadata.
4. Run: with plugins or extended saves, start `D2RLoader.exe` and pick the mod; otherwise `D2R.exe -mod <Name> -txt`
   also works. Fully restart the game after every install. The first start after installing or updating D2RLoader
   or D2R builds D2RLoader's table cache and loads D2R's own sounds: start the game a second time. Set the default
   mod in D2RLoader's options (gear, Default Mod); see ${CLAUDE_PLUGIN_ROOT}/knowledge/d2rloader.md.
5. Keep a TESTING.md in the project: every installed change gets a row (what, how, expected). Run the in-game checks
   yourself, in a game slot (the d2r-in-game-testing skill) and move a row to "Confirmed" with what you saw; hand a row
   to the human only when its check needs one. When something breaks, use the d2r-debug skill.

## Test characters
Every test character is level 99 with experience 3520485254, 490 stat points and 98 skill points (owner rule,
2026-11-11), made with the Reign of the Warlock game version (the default):
`save-set <save> level=99 experience=3520485254 statpts=490 newskills=98`.
`python -m modkit save-info <save.d2s> [--extended] [--project <dir>]` shows stats and class skill points;
`save-set` takes any stat by its itemstatcost name and `--skill <id>=<points>`, for example `save-set <save> strength=100 --skill 12=1`; it edits them (backs up the save folder first, fixes the
checksum and D2RLoader's .d2rl hashes). Never hand-write items into saves; use D2R's debug Item Spawner.

## Shipping
Players need the `mods/<Name>` folder (and D2RLoader if you use plugins/extended saves). Ship only your mod's
files, never the game's; `out/data` already holds only what the mod changes. Requirement checks name the game
version (`3.3`), never a build number: Steam and Battle.net ship the same program under different builds. Tell
players to start twice the first time, to set Default Mod, and to remove other gameplay plugins.

Porting an existing classic mod instead of starting fresh: the `d2r-port` skill.
