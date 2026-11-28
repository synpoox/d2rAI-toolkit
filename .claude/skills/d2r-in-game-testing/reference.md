# Check a change in the real game

**Read little.** Grep, do not read whole: `${CLAUDE_PLUGIN_ROOT}/knowledge/cheat-commands.md` (what cheats did in game; all commands: `cheat-commands-all.md` beside it)
and `${CLAUDE_PLUGIN_ROOT}/docs/testing.md` (grep its headings: `Slots, locks`, `Controlling the game`, `Practical hazards`, `Troubleshooting`).
**If the mod repo has its own game-check doc** (`docs/agents/game-check.md` or similar), its rules win over the steps below
where they differ (character, DS1 pinning, slots, proof), but cannot waive the safety rules or a lane's no-wait requirement.

## The recipe

Set once per shell: `MODKIT_RUN=<lane>` and, when the machine has a slot table (`~/.d2r-modkit/slots.toml`), `MODKIT_PROJECT=<project>`
(`lock` refuses an owned slot without it), plus `MODKIT_TESTING_CONFIG` unless the config is `./modkit-testing.toml`. PowerShell: `$env:NAME='value'`.
Name the slot in every command (`--slot <N>`). Tools: `python ${CLAUDE_PLUGIN_ROOT}/testing/<tool>.py`.

1. **Lock**: run `game_slots.py status`; choose one permitted slot from `[testing].game_slots` (never slot 1 or the owner's game). One named attempt: `game_slots.py lock <N> <lane> --wait 0`. Never poll, wait or add slots. If unavailable, stop, file (or ask the orchestrator to file) a `ready-for-agent` issue with run steps, and report.
2. **Install** with the game closed, after building in this worktree. Use only an installer that stops on lock failure; immediately before installing or stopping the game, `game_slots.py check <N> <lane>` must succeed. Commands: `slot_install.py --slot <N> <project>` (plugins: `powershell -ExecutionPolicy Bypass -File ${CLAUDE_PLUGIN_ROOT}/tools/install_plugins.ps1 -Game <N> -Project <mod> -Plugins <name>`; release: `release_install.py install --slot <N>`).
   Then `game_checks.py --module stock_checks run slot-savepath --slot <N>` (`--module` before `run`): the slot's `modinfo.json` must name the slot's own save folder.
3. **DS1 pin** (only when the level has several variants and the project pins): `force_ds1.py --slot <N> "<Level>=<File>.ds1"`, game closed; `--reset` undoes it.
4. **Start**: `game_ctl.py --slot <N> start`, on a test character (below).
4a. **Startup scan**, once the menu is up: every part the plugins left off, with the project's full plugin set installed: `grep -E -i -h "matches nowhere|skipped [^:]+: ([0-9]+ matches|bad pattern)|off: engine address|not found on this game image" <slot>/mods/<mod>/d2rloader/logs/*.log <slot>/d2rloader/logs/*.log`. A hit a plugin did not log before is a finding even when the check passes: often another plugin hooked that function (`${CLAUDE_PLUGIN_ROOT}/knowledge/engine-re.md`, "Start a function's signature past its entry").
5. **Cheats**, one console line each: `debug_mode`, then e.g. `cheat god 1`, `cheat nogethit 1`, `cheat speedup 300` (`game_ctl.py --slot <N> console "<line>"`).
   God mode kills any unit the character hits in one hit: never judge a boss's life or stages from hits; lower life with the plugin's test commands.
6. **Evidence stays outside the repo** (`<runs.dir>/<lane>/screenshots/`). Never commit or push a screenshot, save or log, on any branch. Report pictures in words.
7. **Close out** right after the check, also on failure: `game_ctl.py --slot <N> stop`, `force_ds1.py --slot <N> --reset` if pinned, `game_slots.py unlock <N> <lane>`; check `game_slots.py status` afterward. Restore the slot. Kill only processes you started, by PID.
8. **Report** per check: what you did, saw, counts of passed, failed and **skipped**, and what you did not verify.

## The test character

Level 99, experience 3520485254, 490 stat points, 98 skill points, **Reign of the Warlock** (Classic/LoD characters play vanilla base tables, not the mod's; `cheat expansion 2` crashed the game). Hell open.
**Reuse an existing level 99 Reign of the Warlock save with Hell open in the slot's save folder first.** Only if none exists, with the game closed:
1. Create it in the slot's game (RotW is the default), save and exit, `game_ctl.py --slot <N> stop`.
2. `python -m modkit save-set <save.d2s> level=99 experience=3520485254 statpts=490 newskills=98` (backs the folder up; add `--extended` when `mod.json` has `"extendedSaves": true`, `--project <mod>` when the mod changes itemstatcost `CSvBits`; `save-info` shows the result; look at the level in game once).
3. Open Hell: `python -c "import sys; sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}/testing'); from save_edit import unlock_difficulties; unlock_difficulties(r'<save.d2s>')"`.

## Rules

Run offline checks first; targeted checks plus build validator and unit tests, full suite only at milestones (one game at a time). Player-facing changes require a release-like install/check/restore. Background harness only: no synthetic OS keyboard/mouse input (SendInput, SetCursorPos, SetForegroundWindow) or focus stealing. Never move, rename or delete saves you did not create.

1. Hell difficulty (monsters live long enough to show a skill).
2. Console first, clicks last: cheats spawn the item, monster, level and stats; use clicks only for what the console cannot do. Before an inventory click: `I`, then `game_ctl.py --slot <N> cursor` (a shot never proves the cursor is empty; see cheat-commands.md, "The cursor item").
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
