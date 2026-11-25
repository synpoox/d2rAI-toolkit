---
name: d2r-in-game-testing
description: Run a check of a Diablo II Resurrected mod in the real game yourself, in a game slot - lock a slot, install, start the game, set up with cheats, clean up and report. Use whenever a change needs proof in game, a brief says "game check", or before you hand a test to the human.
---

# Check a change in the real game

Toolkit root: `${CLAUDE_PLUGIN_ROOT}` (the placeholder itself means you are inside the toolkit repo: use its root). Run the tools from there.
**You run the check, in a slot**, through the harness (no real mouse or keyboard). Ask the human only per "When to hand it over".

**Read little.** Grep, do not read whole: `${CLAUDE_PLUGIN_ROOT}/knowledge/cheat-commands.md` (what cheats did in game; all commands: `cheat-commands-all.md` beside it)
and `${CLAUDE_PLUGIN_ROOT}/docs/testing.md` (grep its headings: `Slots, locks`, `Controlling the game`, `Practical hazards`, `Troubleshooting`).
**If the mod repo has its own game-check doc** (`docs/agents/game-check.md` or similar), its rules win over the steps below
where they differ (character, DS1 pinning, slots, proof).

## The recipe

Set once per shell: `MODKIT_RUN=<lane>` and, when the machine has a slot table (`~/.d2r-modkit/slots.toml`), `MODKIT_PROJECT=<project>`
(`lock` refuses an owned slot without it), plus `MODKIT_TESTING_CONFIG` unless the config is `./modkit-testing.toml`. PowerShell: `$env:NAME='value'`.
Name the slot in every command (`--slot <N>`). Tools: `python ${CLAUDE_PLUGIN_ROOT}/testing/<tool>.py`.

1. **Lock** a free slot that is yours: `game_slots.py status`, then `game_slots.py lock <N> <lane>` (`--wait <s>` to queue). None free: hand the steps over.
2. **Install** with the game closed, after building in this worktree: `slot_install.py --slot <N> <project>` (plugins: `${CLAUDE_PLUGIN_ROOT}/tools/install_plugins.ps1 -Game <N> -Project <mod> -Plugins <name>`; release: `release_install.py install --slot <N>`).
   Then `game_checks.py --module stock_checks run slot-savepath --slot <N>` (`--module` before `run`): the slot's `modinfo.json` must name the slot's own save folder.
3. **DS1 pin** (only when the level has several variants and the project pins): `force_ds1.py --slot <N> "<Level>=<File>.ds1"`, game closed; `--reset` undoes it.
4. **Start**: `game_ctl.py --slot <N> start`, on a test character (below).
5. **Cheats**, one console line each: `debug_mode`, then e.g. `cheat god 1`, `cheat nogethit 1`, `cheat speedup 300` (`game_ctl.py --slot <N> console "<line>"`).
   God mode kills any unit the character hits in one hit: never judge a boss's life or stages from hits; lower life with the plugin's test commands.
6. **Evidence stays outside the repo** (`<runs.dir>/<lane>/screenshots/`). Never commit or push a screenshot, save or log, on any branch. Report pictures in words.
7. **Close out** right after the check, also on failure: `game_ctl.py --slot <N> stop`, `force_ds1.py --slot <N> --reset` if pinned, `game_slots.py unlock <N> <lane>`.
8. **Report** per check: what you did, saw, counts of passed, failed and **skipped**, and what you did not verify.

## The test character

Level 99, experience 3520485254, 490 stat points, 98 skill points, **Reign of the Warlock** (Classic/LoD characters play vanilla base tables, not the mod's; `cheat expansion 2` crashed the game). Hell open.
**Reuse an existing level 99 save in the slot's save folder first.** Only if none exists, with the game closed:
1. Create it in the slot's game (RotW is the default), save and exit, `game_ctl.py --slot <N> stop`.
2. `python -m modkit save-set <save.d2s> level=99 experience=3520485254 statpts=490 newskills=98` (backs the folder up; add `--extended` when `mod.json` has `"extendedSaves": true`, `--project <mod>` when the mod changes itemstatcost `CSvBits`; `save-info` shows the result; look at the level in game once).
3. Open Hell: `python -c "import sys; sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}/testing'); from save_edit import unlock_difficulties; unlock_difficulties(r'<save.d2s>')"`.

## Rules

1. Hell difficulty (monsters live long enough to show a skill).
2. Console first, clicks last: cheats spawn the item, monster, level and stats; use clicks only for what the console cannot do.
3. **Stop only after 5 minutes with no progress (stuck or idle).** Not a time limit: while the check progresses, keep going. Then stop the game, unlock, and file an issue labelled `ready-for-human` (create the label with `gh label create ready-for-human` if missing; a mod repo's own rule may name another label) with the steps left and what you verified.
4. One lock from install to cleanup; never release and retake it between steps.
5. Never `lock any`: name the slot.
6. Check the savepath after every install (a plain `modkit install` writes the project's savepath, not the slot's).
7. Count the skips: exit 0 may hide skipped checks. Report passed, failed, skipped.
8. HD JSON keys are case-sensitive: use the exact table `Id` or name.
9. Prefer a PluginSDK service to a native hook in a plugin; hook game code only when none does the job, and say why (`d2r-engine` skill).
10. An acknowledgement is not output: the console file says a line was handled; what it printed is in the plugin's log (`docs/testing.md`, "Practical hazards").

## When to hand it over

Only for a check that needs a real mouse or hand input the harness cannot send (the Item Spawner's double-clicks), a real-player judgement, the human's own game (slot 1, untouched), or rule 3.
Put the slot, the lock owner and the unlock command in the handover. Everything else you run, and keep working while it runs.
A crash: the `d2r-debug` skill.
