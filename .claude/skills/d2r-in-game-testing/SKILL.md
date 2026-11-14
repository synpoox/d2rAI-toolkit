---
name: d2r-in-game-testing
description: Run a check of a Diablo II Resurrected mod in the real game yourself, in a game slot - lock a slot, install, pin a DS1 variant, start the game, set up with cheats, warp, take screenshots that settle the question, clean up and report. Use whenever a change needs proof in game, a brief says "game check", or before you hand a test to the human.
---

# Check a change in the real game

Toolkit root: `${CLAUDE_PLUGIN_ROOT}` (if you see the placeholder itself, you are inside the toolkit repo: use its root). Run the tools below from that folder.

**You run the in-game check, in a slot.** The tools drive the game without a real mouse or keyboard
(${CLAUDE_PLUGIN_ROOT}/docs/testing.md, "Controlling the game"). Ask the human only when a check needs one (see "When to hand it over"). The slot
tools, locks, config and harness are explained in ${CLAUDE_PLUGIN_ROOT}/docs/testing.md; this skill is the order of work and the rules.
Read ${CLAUDE_PLUGIN_ROOT}/knowledge/cheat-commands.md before the first check: it lists every console cheat and what the item lines did in game.

## The recipe

Name your run once (`MODKIT_RUN=<lane>`, PowerShell: `$env:MODKIT_RUN='<lane>'`) and use that name for every command. Name the
slot every time; set `MODKIT_TESTING_CONFIG` if the machine's config is not `./modkit-testing.toml`. When the machine has a
slot table (`~/.d2r-modkit/slots.toml`), also set `MODKIT_PROJECT=<project>` (its owner name for your slots, or pass
`--project`): `lock` refuses an owned slot when no project is given.

1. **Lock a slot.** `python ${CLAUDE_PLUGIN_ROOT}/testing/game_slots.py status`, then `python ${CLAUDE_PLUGIN_ROOT}/testing/game_slots.py lock <N> <lane>` on a
   free slot that is yours. No free slot: wait (`--wait`), or stop and hand the steps to whoever plans the work.
2. **Install the build** into that slot with the game closed. Build first, in this worktree (the project's own build
   steps, generators included): `slot_install.py` copies whatever the last build left in `out/`.
   `python ${CLAUDE_PLUGIN_ROOT}/testing/slot_install.py --slot <N> <project>`
   (or, for the mod's plugins, `powershell -ExecutionPolicy Bypass -File ${CLAUDE_PLUGIN_ROOT}/tools/install_plugins.ps1 -Game <N> -Project <mod> -Plugins <name>[,<name>]`,
   or, for the published release, `python ${CLAUDE_PLUGIN_ROOT}/testing/release_install.py install --slot <N>`). Then run the stock check
   `slot-savepath` (`python ${CLAUDE_PLUGIN_ROOT}/testing/game_checks.py --module stock_checks run slot-savepath --slot <N>`; `--module` goes
   before `run`, and `stock_checks` is not in `checks.modules` by default): the slot's `modinfo.json` must name the
   slot's own save folder, or the test plays on, and writes to, somebody else's saves.
3. **Pin the DS1 variant** when the level has several (`python ${CLAUDE_PLUGIN_ROOT}/testing/force_ds1.py --slot <N> "<Level>=<File>.ds1"`),
   game closed. Otherwise the warp can land on another layout. `--reset` undoes it.
4. **Start the game** in HD on a character that meets "The test character" below (make it first, with the game closed; the
   order is in that section):
   `python ${CLAUDE_PLUGIN_ROOT}/testing/game_ctl.py --slot <N> start`.
5. **Set the cheats** through the console, one line each: `debug_mode`, then for example `cheat god 1`,
   `cheat nogethit 1`, `cheat speedup 300` (`python ${CLAUDE_PLUGIN_ROOT}/testing/game_ctl.py --slot <N> console "cheat god 1"`).
6. **Warp** with `cheat goto <levelId>,<x>,<y>`. The formula from a DS1 tile is in `${CLAUDE_PLUGIN_ROOT}/knowledge/cheat-commands.md`;
   `${CLAUDE_PLUGIN_ROOT}/testing/warps.py` makes the lines for a level's reference spots.
7. **Shoot** with `game_ctl.py --slot <N> shot <name>`, or `game_ctl.py --slot <N> pair <name> <level,x,y>` for an
   HD | legacy pair. Look at every picture before the next click (a held cursor item hides tooltips).
8. **Keep the evidence outside the repository.** Pictures land in `<runs.dir>/<lane>/screenshots/`. Never commit a
   screenshot, a save or a log (docs/testing.md, "Screenshots and results"). Report what each picture shows in words; if the
   owner needs to see one, say where it is on disk.
9. **Close out** right after the check, also when it failed: `game_ctl.py --slot <N> stop`, `force_ds1.py --slot <N> --reset`
   if you pinned, then `python ${CLAUDE_PLUGIN_ROOT}/testing/game_slots.py unlock <N> <lane>`.
10. **Report** per spot or per check: what you did, what you saw, the counts of passed, failed and **skipped** checks,
    and what you did not verify.

## Screenshots that settle the question

One shot should answer the question. Before each shot:

- **A quiet spot.** Warp to a spot with no monsters, or repeat `cheat killmonster` (or `cheat monfreeze 1`), and shoot once
  nothing casts or burns near you.
- **Structure shots** (walls, edges, floors) in the dark: `cheat stat item_lightradius,25` (`pair` does it for you with
  `--light`). The radius stays raised for the rest of the game session, so never for a lighting shot (`--light 0`).
- **Pin the DS1 variant** (step 3) on every level with several.
- **Lighting shots:** take several frames with no combat effects (fire, poison and spells skew the brightness) and use
  the median luma over the frames.
- **Before and after pairs** for a visual change: the same spot, the same settings, the old build and the new one, or
  HD and legacy (`g`). `pair` warns and exits 1 when its two shots are identical (the toggle did nothing, or not in HD).
- **Water under canopy:** the cheat list has no canopy or tree toggle. Warp where the canopy is thin, or say in the
  report that the canopy hid it.
- A picture that is not blank is not proof of the effect. Say what you expected to see, then what you saw.

## The test character

Every test character is **level 99 with experience 3520485254, 490 stat points and 98 skill points** (owner rule,
2026-11-11). Order of work, game closed unless said otherwise:

1. Create the character in the slot's game with the **Reign of the Warlock** game version (the default at character
   creation), save and exit, then `python ${CLAUDE_PLUGIN_ROOT}/testing/game_ctl.py --slot <N> stop`.
2. Set the stats on the slot's own save folder (`modkit save-set` backs the folder up first):
   `python -m modkit save-set <save.d2s> level=99 experience=3520485254 statpts=490 newskills=98` (stat names are
   itemstatcost's; ${CLAUDE_PLUGIN_ROOT}/knowledge/saves.md). Add `--extended` when the mod's `mod.json` has
   `"extendedSaves": true` (16-bit stat ids; without it the read stops at `stat N has no CSvBits`), and
   `--project <mod>` when the mod changes itemstatcost's `CSvBits` (the built table's widths are read).
   `python -m modkit save-info <save.d2s>` with the same flags shows the result. This line is checked offline against the field names and bit widths only; it has
   not yet been run on a real save, so look at the character's level in game once.
3. Open Hell (a fresh character has it closed). `save_edit.py` has no command line, call the function:
   `python -c "import sys; sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}/testing'); from save_edit import unlock_difficulties; unlock_difficulties(r'<save.d2s>')"`.
4. Start the game on it (recipe step 4).

A Classic or Lord of Destruction character plays D2R's vanilla base tables, not the mod's, unless the mod also
writes `excel/base/` (the LoD character shows an X
badge on the character select banner), and `cheat expansion 2` does not convert it: it crashed the game
(${CLAUDE_PLUGIN_ROOT}/knowledge/cheat-commands.md).

## Rules

1. **Hell difficulty.** Monsters there have the HP to live long enough to show what a skill does.
2. **Read `${CLAUDE_PLUGIN_ROOT}/knowledge/cheat-commands.md` first,** then use the console, not clicks and walking: the cheats spawn the item,
   the monster, the level and the stats. Clicks and movement are hard to get right; use them only for what the console
   cannot do.
3. **Ten minutes without significant progress on what the check checks: stop.** Stop the game, unlock the slot, and file
   an issue labelled `ready-for-human` (or the project's equivalent; the label may not exist in a mod repo, so create it
   first with `gh label create ready-for-human`) with the steps left and what you already verified.
4. **Hold one lock from install to cleanup.** Take the slot once, install, test, stop, unlock. Do not release and retake
   it between steps; another lane can take it in the gap and your install is gone.
5. **Never `lock any`.** Name the slot. `any` takes the first free slot, which can be another project's.
6. **Check the savepath after every install** (`slot-savepath`, step 2). A plain `modkit install` writes the project's own
   savepath, not the slot's.
7. **Count the skips.** A run that exits 0 may have skipped the checks that matter (no harness, no log lines yet). The
   proof is the pass count of the checks that test the change; report passed, failed and skipped.
8. **JSON keys the game reads are case-sensitive.** Key HD JSON (`monsters.json` and the others) by the exact table `Id`
   or name; a lower-cased key is invisible in game.
9. **Use the PluginSDK service before a native hook** when you write a plugin for a check's setup or a fix. Hook game
   code only when no service does the job, and say why in the code (the `d2r-engine` skill).
10. **An acknowledgement is not output.** See "Practical hazards" in ${CLAUDE_PLUGIN_ROOT}/docs/testing.md.

## When to hand it over

Ask the human only when a check needs one: a real mouse or hand-driven input the harness cannot send (the Item Spawner's
double-clicks), a real-player judgement (does it feel right), the human's own game (slot 1, which no tool touches), or
rule 3. Write the slot, the lock owner and the unlock command into the handover so they can finish. Everything else, you
run, and you keep working while a check runs.

More: ${CLAUDE_PLUGIN_ROOT}/docs/testing.md (tools, locks, harness, writing checks, evidence levels), `${CLAUDE_PLUGIN_ROOT}/testing/README.md`,
${CLAUDE_PLUGIN_ROOT}/knowledge/cheat-commands.md, and the `d2r-debug` skill when a run crashes.
