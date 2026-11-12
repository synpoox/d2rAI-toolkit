# testing/

Tools to test a D2R mod in the real game without a human at the keyboard. Python 3.12+, standard library only.
Windows is needed to run the game; everything else (locks, config, checks, release installs) works anywhere.

| File | What it is |
|---|---|
| `testing.example.toml` | The one config. Copy to `modkit-testing.toml` and edit. No paths or names live in the scripts. |
| `testing_config.py` | Reads the config and does all the path math (slot folders, save folders, lock folders). |
| `game_slots.py` | Slots = separate copies of the game install. Setup, sync, lock, unlock, status. |
| `game_ctl.py` | Starts, stops and drives one slot's game: screenshots, keys, clicks, console commands. |
| `check_helpers.py` | `pair` (warp, light up, HD \| legacy side-by-side PNG) and `moved` (did the character move?), run as `game_ctl.py` subcommands; also the shared plugin-log reader (`plugin_log_path`). |
| `check_helpers.py` (`plugin_log`, `plugin_log_path`) | A plugin's log since its last load line, from the mod, game-wide or configured log, for checks to read. |
| `lod_checks.py` | Reusable Lord of Destruction checks: plugin loaded, read and verify a `.d2s`, Save and Exit, create / save / reload a character. Plugin, mod and character are parameters. |
| `menu_layout.py` | Menu click positions (fractions of the window) for `lod_checks`; measured for D2R 3.3 at 1920x1080, re-measure for another version. |
| `game_checks.py` | Small checks framework: `@check` registry, runner, results JSON, summary, screenshots. |
| `example_checks.py` | Example checks to copy (`config-sane`, `game-starts`, `main-menu-visible`, `console-echo`, `no-new-crash-files`). |
| `d2r_only.py` | Checks for content the mod switches off (Terror Zones, Heralds, the Colossal Summit portal). Its in-game parts leave town: tag them `leaves-town` and run them only on a slot locked for out-of-town checks. |
| `stock_checks.py` | Stock checks for any mod (`slot-savepath`: each modinfo savepath is the slot's own save folder). List it in `checks.modules` to use it. |
| `slot_registry.py` | The slot-to-owner table (`~/.d2r-modkit/slots.toml`, machine config): which project may lock which slot. |
| `warps.py` | `cheat goto` lines (and a markdown doc for a list of levels) for a DS1 map's centre, waypoints and boss presets. |
| `slot_install.py` | Installs a built mod project into a slot (`modkit install`), keeping the slot's own savepath. |
| `force_ds1.py` | Test-only: pins a level to one DS1 variant in a slot's installed `lvlprest.txt`, so a warp lands on the preset under test. |
| `unit_probe.py` | Reads the client's units (monsters, missiles) from a running game, read-only, build 93847 only. |
| `release_install.py` | Installs the PUBLISHED release into a slot, as a player would get it. |
| `stats.py` | Rate checks for random outcomes (drop, proc, block): `count`, `tolerance_for`, `assert_rate`. |
| `lod_checks.py` | Checks and helpers for a Lord of Destruction character: plugin loaded, save read, save and exit, create, reload, delete. |
| `menu_layout.py` | Where the 3.3 menu buttons are, as fractions of a 1920x1080 client, for `lod_checks.py`. |
| `image_bytes.py` | Reads the game image's PE stamp and classifies byte spans, so a check can see that an engine patch is in. The PE stamp tells which build; `classify` tells stock bytes from patched ones. |
| `save_edit.py` | Edits a `.d2s` save for a test (unlock difficulties, set the current location), checksum fixed. |
| `d2r_only.py` | Checks that a mod switched off D2R 3.3's Terror Zones, Heralds and Colossal Summit portal: data checks plus in-game purple scans. |
| `contact_sheet.py` | Turns a folder of HD \| legacy pair PNGs into one contact sheet plus brightness and black-pixel numbers. |
| `warps.py` | `cheat goto` lines for a DS1 map's centre, waypoints and boss presets, from a data folder. |
| `force_ds1.py` | Pins a level to one DS1 variant in a slot's installed `lvlprest.txt`, so a warp lands on the preset under test. |
| `stock_checks.py` | Checks any mod can list in `checks.modules`: `slot-savepath`. |

## Quick start

```
cp testing/testing.example.toml modkit-testing.toml        # edit game.install_dir, game.slots_dir, [mod]
python testing/game_slots.py setup 2                       # copy your install into slot 2
python testing/game_slots.py lock 2 my-lane                # take the slot (queue: add --wait 600)
MODKIT_RUN=my-lane python testing/slot_install.py --slot 2 my-project   # your built mod, slot's savepath
MODKIT_RUN=my-lane python testing/game_checks.py run --slot 2
MODKIT_RUN=my-lane python testing/game_slots.py unlock 2 my-lane
```

`python testing/game_checks.py list` shows the checks. Results: `<runs.dir>/<run id>/results.json`,
`summary.txt` and `screenshots/`. Exit code 0 = no failures, 1 = a check failed, 2 = bad usage or slot not available.

## Fixture pattern: one tiny mod per check

A check that needs a game rule in a known state does not depend on the real mod's data. It ships a **fixture**: the
smallest mod that sets only that rule, installed into a slot for the run.

```
tests/game/fixtures/<check name>/
  mod.json                  name (= mod.folder), savepath, title ("<mod> (<check> game check)"), version 0.0.0, plugins []
  patches/010-<check>.json  the data change: the rows or values the check needs, nothing else
```

- `mod.json` `name` must equal the testing config's `mod.folder` (the real mod's folder name); `slot_install.py`
  refuses any other name ("is mod X but mod.folder is Y"). Name the fixture's folder after the check, but keep `name`
  as the real mod's. Give the title the word "check" so a fixture install cannot be mistaken for a release.
- What keeps a fixture character out of the user's saves: `slot_install.py` writes the slot's own savepath
  (`<saves.slot_name>/`) whatever `mod.json` says, and `slot-savepath` in `stock_checks.py` checks it. Use the usual
  `<name>/` in `mod.json`.
- One fixture per check, named after the check. The patch holds only the rows that check reads; an empty difference
  from the base data is a fixture that tests nothing.
- The check runs `modkit build <fixture>` (its patch applies to vanilla, the extracted game data, so the patch must carry
  every row the check reads), installs the result with `slot_install.py` (the lock is held, the game is stopped), runs,
  and the next install of the real project puts the real data back (both write the same mod folder). Never install a fixture into
  slot 1.
- Keep fixtures in the repo that owns the check (for example `tests/game/fixtures/`). The toolkit ships the pattern and the
  helpers, not any mod's fixtures.

## Rules

- Slot 1 is your own game (`game.install_dir`). These tools read it to make copies and never write, start or lock it.
  Every command refuses slot 1.
- `game_ctl.py start` without a prior `lock` takes a **manual** lock (pid 0) for the owner (`MODKIT_RUN`), so it never
  looks stale when the command ends. Only `unlock N <owner>` removes it; `stop` leaves it.
- There is no default slot. Pass `--slot N` or set `MODKIT_SLOT=N`, on every command.
- `MODKIT_RUN=<lane>` is the run id and the lock owner. A lock is a folder `<runs.dir>/game.lock.N` with
  `owner.txt` = `<owner> pid=<pid> <time>`. A dead pid makes it stale (replaced on the next lock). `pid=0` is a manual
  lock made by `lock`; it lasts until `unlock`, and runs inside it do not free it.
- `lock N <owner> --wait SECONDS` queues: it prints who holds the slot and polls. `lock any <owner>` takes the first
  free slot from 2 up. `unlock N <owner>`, or `unlock N --force` to clear a stale lock of a finished lane.
  `status` shows each lock's age ("held 6 min"). `unlock` refuses a lock younger than 30 min or whose owner pid still
  runs, and names the age and owner, unless `<owner>` equals your own `MODKIT_RUN` (freeing your own lock) or `--force`.
- **Slot owners.** If `~/.d2r-modkit/slots.toml` exists (or `--slots-file F` / `MODKIT_SLOTS_FILE`), `lock` refuses a slot
  another project owns. Say who you are with `--project NAME` or `MODKIT_PROJECT`; `lock any` takes only your own slots,
  then unowned ones. No file, no enforcement; an unreadable file refuses everything. The table is machine config and never
  goes into a repo. Format:

  ```toml
  [owners]
  "2"   = "toolkit"     # a slot number or a range is the key, a project name the value
  "3"   = "mod-a"
  "4-6" = "mod-b"
  ```
- Nothing here sends real mouse or keyboard input or takes focus. The window is found by PID, never by title.

## Command lines

```
python testing/game_slots.py [--config F] status | list
python testing/game_slots.py setup|sync [N ...] [--link] [--dry-run]
python testing/game_slots.py lock N|any [OWNER] [--wait SECONDS]
python testing/game_slots.py unlock N [OWNER] [--force]
python testing/game_ctl.py   --slot N status|start|stop|shot NAME|key KEY..|click FX FY [right]|console CMD|harness on|off|pair NAME LEVEL,X,Y [--light N] [--settle S]|moved click FX FY|key KEY..
python testing/game_checks.py list [names or tags]
python testing/game_checks.py run [names or tags] --slot N [--run-id ID] [--keep] [--stop-on-fail] [--module M] [--path DIR]
python testing/warps.py --data DIR --level N [--level M ...] [--ds1 NAME] [--boss-word W ...] [--out FILE]   # no slot needed
python testing/slot_install.py --slot N PROJECT
python testing/force_ds1.py --slot N [--project DIR] "<Name or LevelId>=<ds1>" | <ds1> | --reset
python testing/release_install.py check [--channel C] [--site S]
python testing/release_install.py install --slot N [--channel C] [--site S] [--method auto|archive|objects] [--harness-dll FILE]
python testing/release_install.py restore|status --slot N
```

Config file: `--config F`, else env `MODKIT_TESTING_CONFIG`, else `./modkit-testing.toml`. A JSON file works too.
With none found the tools refuse to touch a slot (exit 2, "no testing config found"); they never fall back to the built-in defaults.
Env vars: `MODKIT_SLOT`, `MODKIT_RUN`, `MODKIT_TESTING_CONFIG`.

## Check helpers

- `game_ctl.py --slot N pair NAME LEVEL,X,Y [--light 12] [--settle 3] [--key g]`: runs `cheat stat item_lightradius,<light>`
  (`--light 0` skips it; the radius stays raised for the rest of the game session, so use `--light 0` when lighting is what
  you judge), `cheat goto LEVEL,X,Y`, waits, shoots HD, presses `g`, shoots legacy, presses `g` back, and saves
  HD (left) | legacy (right) as `<runs.dir>/<run>/screenshots/NAME.png`. The window is found again by PID before every shot
  and key. The legacy toggle is pressed back even when a shot fails. Prints the path and the HD-to-legacy distance beside the noise
  between two HD shots; warns and exits 1 when the shots are identical (within the larger of 0.5 and 3x the noise: the
  toggle did nothing, or not in HD).
  The game must be in a game; use Hell and a level 90+ character.
- `game_ctl.py --slot N moved [--wait 1.5] click FX FY [right] | key KEY..`: reads the player position before and after
  and prints whether and how far the character moved (exit 0 = moved, 1 = not, 2 = cannot tell). It needs the plugin to
  write the position into the harness block: set `idx_player_x`/`idx_player_y` (and optionally `idx_player_level`) in
  `[harness]` (world subtiles, see docs/testing.md). Without them it refuses with exit 2; there is no screen fallback
  (animation made it report a move at a wall). Needs a plugin that writes the position (d2r-test-harness#1).
- The pure parts (`side_by_side`, `identical`, `position_diff`, `parse_warp`) are tested in `tests/test_testing_helpers.py`.

## Config keys

| Section | Keys |
|---|---|
| `[game]` | `install_dir` (slot 1), `slots_dir`, `slot_dir_template`, `slot_dirs`, `slot_count`, `loader_exe`, `game_exe`, `window_title_prefix`, `client_size`, `window_origin`, `window_step`, `copy_mode`, `link_dirs`, `exclude`, `mods_policy` |
| `[mod]` | `name`, `folder`, `plugins_subdir`, `plugin_dlls`, `modinfo_files` |
| `[saves]` | `root`, `slot1_name`, `slot_name` |
| `[loader]` | `config_file`, `section`, `default_mod_key`, `args_key`, `set_default_mod` |
| `[logs]` | `loader_log`, `plugin_log`, `crash_dir`, `startup_line` |
| `[harness]` | `shm_name`, `shm_name_shared`, `magic`, `block_bytes`, `command_offset`, `command_max`, `idx_*`, `flag_background`, `word_file`, `console_file`, `words`, `cursor_start` |
| `[runs]` | `dir`, `screenshots_dir` |
| `[checks]` | `modules`, `paths`, `start_timeout`, `echo_command`, `menu_min_mean`, `menu_min_stddev` |
| `[release]` | `site_url`, `channel`, `seven_zip`, `apply_launch`, `extra_launch_args`, `channel_schema`, `manifest_schema`, `retries` |

## The harness protocol

The game plugin (not part of this repo) must offer a test harness. It turns on when the word file exists in the
plugins folder (`harness.word_file`). All names and numbers below come from `[harness]`.

Shared memory `harness.shm_name` (default `Local\my-harness-block-{pid}`), one block per game process,
`block_bytes` long, little-endian int32 array:

| Index (config key) | Meaning | Written by |
|---|---|---|
| 0 `idx_magic` | `harness.magic`; the tool refuses a block without it | plugin |
| 1 `idx_active` | 1 = the game reads cursor, buttons and modifiers from this block instead of the real devices | tool |
| 2, 3 `idx_x`, `idx_y` | virtual cursor, client pixels | tool |
| 4 `idx_buttons` | button bits: 1 = left, 2 = right | tool |
| 5 `idx_mods` | modifier bits: 1 = shift, 2 = ctrl, 4 = alt | tool |
| 6 `idx_seq` | input sequence counter (reserved) | tool |
| 7 `idx_flags` | `flag_background` = do not bring the window to the front | tool |
| 8 `idx_cmd_seq` | command sequence; the tool bumps it after writing the command | tool |
| 9 `idx_cmd_ack` | plugin copies `cmd_seq` here when the command was run | plugin |
| 10 `idx_cmd_result` | 1 = the console handled the line, 0 = not | plugin |
| bytes `command_offset`.. | command text, UTF-8, NUL terminated, at most `command_max` bytes | tool |

Flow of one console command: write the text, bump `cmd_seq`, wait until `cmd_ack == cmd_seq`, read `cmd_result`.
The plugin appends any output to `harness.console_file` (in the plugins folder); `game_ctl` reads it from a byte mark.
The word file holds free-form words (`harness.words`, `{slot}` replaced) that the plugin reads at load.
