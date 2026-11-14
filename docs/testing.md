# Testing a mod in the real game

How to run Diablo II: Resurrected with your mod, check that it works, and take pictures of what happened. No human
needs to sit at the keyboard, and your own game and characters are never touched.

The tools are in `testing/`. They are plain Python 3.12+ (standard library only) and run on Windows, where the game
runs. Everything that needs Windows is behind a function, so the scripts also import and unit-test on other systems.

| Tool | What it does |
|---|---|
| `testing/game_slots.py` | Makes and syncs the game copies ("slots"), shows their state, and handles the queue locks. |
| `testing/game_ctl.py` | Starts and stops the game in a slot, takes screenshots, sends keys, clicks and console lines. |
| `testing/game_checks.py` | Runs named in-game checks and writes the results and screenshots. |
| `testing/release_install.py` | Puts the **published** release into a slot, the way a player gets it. |
| `testing/warps.py` | Makes `cheat goto` lines for a level's DS1 reference spots, or a markdown doc for a list of levels. |
| `testing/force_ds1.py` | Test-only: pins a level to one DS1 variant in a slot's installed `lvlprest.txt`. |
| `testing/unit_probe.py` | Reads the client's units (monsters, missiles) from the game running in a slot, read-only; see [Reading units](#reading-units-unit_probe). |
| `testing/example_checks.py` | Five example checks. Copy it and make your own. |
| `testing/stock_checks.py` | Stock checks that hold for any mod (`slot-savepath`). Turn on with `modules = ["stock_checks"]`. |
| `testing/testing.example.toml` | The config. Copy it to `modkit-testing.toml`. |

Contents: [Quick start](#quick-start) · [Why slots](#why-slots) · [The config file](#the-config-file) ·
[Slots, locks and the queue](#slots-locks-and-the-queue) · [Controlling the game](#controlling-the-game) ·
[The harness protocol](#the-harness-protocol) · [Writing and running checks](#writing-and-running-checks) ·
[Screenshots and results](#screenshots-and-results) · [Test what players get](#test-what-players-get) ·
[Targeted tests and the full suite](#targeted-tests-and-the-full-suite) · [Who runs the check](#who-runs-the-check) ·
[Evidence levels](#evidence-levels) · [Practical hazards](#practical-hazards) · [Troubleshooting](#troubleshooting)

## Quick start

You need: Windows, a normal D2R install, D2RLoader in it, and a mod folder in `<D2R>/mods/<folder>`. For the click,
key and console commands you also need a plugin that implements the [harness protocol](#the-harness-protocol).
Screenshots, starting and stopping, and the first three example checks work without one.

```sh
# 1. Config: copy the example, then set game.install_dir, game.slots_dir and mod.folder.
cp testing/testing.example.toml modkit-testing.toml

# 2. Make the slot copies (slot 2 and 3). Slot 1 is your own game and is only read.
python testing/game_slots.py setup
python testing/game_slots.py status

# 3. Take a slot for yourself. "any" = the first free slot. One attempt, no waiting (--wait 0 is the default):
#    if none is free, stop, file a `ready-for-agent` issue for the run and report.
python testing/game_slots.py lock any my-lane --wait 0           # prints which slot you got

# 4. Put your mod into that slot (the slot copy skips the mods folder by default). Keeps the slot's own savepath.
MODKIT_RUN=my-lane python testing/slot_install.py --slot 2 my-project

# 5. Run the checks on that slot. MODKIT_RUN names you; screenshots and results go to ~/modkit-runs/my-lane/.
MODKIT_RUN=my-lane python testing/game_checks.py run --slot 2

# 6. Give the slot back.
MODKIT_RUN=my-lane python testing/game_slots.py unlock 2 my-lane   # PowerShell: $env:MODKIT_RUN='my-lane'; python ...
```

In PowerShell set the variable first: `$env:MODKIT_RUN = "my-lane"`.

The exit code of `run` is 0 when every check passed (skips are fine), 1 when one failed, 2 when it could not start.

## Why slots

Testing a mod means starting the game, loading characters, writing save files and sometimes crashing. Doing that in
the install you play on is how a character gets lost. Two agents sharing one install also overwrite each other's
files and kill each other's game.

So the tools work on **slots**: separate folders, each a copy of the game install, each with its own save folder.

| Slot | What it is |
|---|---|
| **1** | **Your own game** (`game.install_dir`). The tools read it, to make the copies. They never write to it, start it, stop it or lock it. Every command that would, refuses with exit code 2. |
| 2, 3, ... | Copies in `game.slots_dir` (`slot-2`, `slot-3`, ...). The number of slots is `game.slot_count` (default 3, so slots 1 to 3). Tests run here. |

What makes a slot independent:

- **Own files.** `setup` copies the install (`copy_mode = "copy"`), or hard-links the big read-only folders in
  `game.link_dirs` (`--link`, same drive only). A synced slot copies only files whose size or time changed, and never
  deletes anything.
- **Own saves.** `setup` writes `savepath` in the mod's `modinfo.json` files so slot 2 saves into
  `.../mods/MyMod-s2/`, never into your `.../mods/MyMod/`. The folder is created.
- **Own loader.** Slot N copies `D2RLoader.exe` to `D2RLoader-sN.exe`, so its process can be told apart. The tools
  also match a process by the folder its program file lives in, never by name alone, because every slot's game is
  called `D2R.exe`.
- **Owner on screen.** `game_ctl.py start` launches a hard link of the loader named after the slot's lock owner
  (`D2RLoader-s8-agent-492-uberdiab.exe` in Task Manager) and puts the owner in front of the window title
  (`[S8 #492 agent-492-uberdiab] Diablo II: Resurrected` on the taskbar and in alt-tab). `#492` is the owner's first
  all-digit part. `game_slots.py status` prints the names it matches.
- **Own loader config.** `setup` writes `default_mod = <mod.folder>` into the slot's copy of the loader config. A later
  `setup` does not overwrite that file, so edits you make in a slot stay.
- **Straight to character select.** `setup` (and `slot_install.py`, `release_install.py`) writes `"First Time": 1`
  into the slot save folder's `Settings.json`, so the game skips the logo videos and the gamma screen. `setup` also
  turns on D2RLoader's Gameplay > *Enable RotW legacy graphics keybind* in the slot's loader config.
- **Own window.** The window is resized to `game.client_size` and placed at `window_origin + window_step * (slot - 1)`.

`mods_policy = "skip"` (the default) leaves the `mods` folder out of the copy: you or your install script fill it, with
`testing/slot_install.py --slot N <project>` or with [`release_install.py`](#test-what-players-get).
`slot_install.py` runs `modkit install` and writes the slot's own savepath (`saves.slot_name`) into both
`modinfo.json` files, so the slot never plays on the project's save folder. It needs the slot lock held by
`MODKIT_RUN` and refuses while that slot's game runs; games in other slots may keep running. Plain
`python -m modkit --game <slot folder> install` refuses a slot folder of the testing config and points you here.
Set `mods_policy = "copy"` to copy your own mods folder as well.

`tools/install_plugins.ps1 -Game <slot folder> -Project <mod> -Plugins a,b [-Data]` wraps these for a mod with built
plugins. `-Game` must be a test slot (2 and up) whose lock `MODKIT_RUN` holds, and `D2R.exe` must be version 3.3; both
are checked first, before anything changes. It copies `<Project>\plugin\build\Release\<name>.dll` into the slot's
mod-scoped `mods\<Mod>\d2rloader\plugins\`, moves every other file there (stray third-party plugins; not the
`<name>-off.txt` toggles or the plugins' own files) and any copy of its DLLs in the game-wide `d2rloader\plugins\` to a
backup folder instead of deleting it (`-KeepExtras` leaves the first kind), and with `-Data` builds first, then
installs the project's data and `mod.json` plugins through `slot_install.py` (which keeps the slot's own savepath).

## Slot owners (`~/.d2r-modkit/slots.toml`)

When several projects share one machine's slots, a table says whose slot is whose. It is machine config, outside every
repo: `~/.d2r-modkit/slots.toml` (or `--slots-file F`, or `MODKIT_SLOTS_FILE`). Example:

```toml
[owners]
"2"   = "toolkit"
"3"   = "mod-a"
"4-6" = "mod-b"
```

With the file present, `game_slots.py lock` (and the lock a `game_ctl.py start` or `game_checks.py run` takes) refuses a
slot another project owns, or an owned slot when no project is given. Give your project with `--project NAME` or
`MODKIT_PROJECT`. `lock any` picks the project's own slots first, then unowned ones, and never another project's. Slots
not listed are free for all. No file: nothing is enforced. A file that cannot be read refuses every lock. See
`testing/slot_registry.py`.

## The config file

All names, paths and numbers live in one TOML (or JSON) file. Nothing about your mod is written in the scripts.

Where it is looked for, first match wins: `--config FILE`, the environment variable `MODKIT_TESTING_CONFIG`, then
`./modkit-testing.toml`. With none of the three, every tool that touches a slot refuses (exit 2, "no testing config found"); only `game_checks.py list` runs on the defaults. Relative paths are relative to the config file. `~` and environment variables are expanded.
Every key has a default except `game.install_dir` and `game.slots_dir`. `testing/testing.example.toml` lists all of
them with their defaults. The ones you will change:

| Key | Meaning |
|---|---|
| `game.install_dir` | Slot 1: your own D2R folder. |
| `game.slots_dir` | Where the copies live: `<slots_dir>/<slot_dir_template>` (`slot-{slot}`). `game.slot_dirs = { "2" = "E:/x" }` puts one slot elsewhere. |
| `game.slot_count` | Slots 1 to N. Slot 1 is yours. |
| `game.copy_mode`, `link_dirs`, `exclude`, `mods_policy` | How `setup` copies (see above). `exclude` defaults to `["Logs"]`. |
| `game.client_size`, `window_origin`, `window_step` | The game window's size and position. |
| `mod.name`, `mod.folder` | Your mod, and its folder under `<game>/mods/`. |
| `mod.plugins_subdir`, `plugin_dlls`, `modinfo_files` | Where your plugin DLLs are, and the files that get a `savepath`. |
| `saves.root`, `slot1_name`, `slot_name` | Where saves live, and the per-slot folder name (`{folder}-s{slot}`). |
| `loader.config_file`, `section`, `default_mod_key`, `args_key` | The loader's own config file, inside each slot. |
| `logs.loader_log`, `startup_line`, `crash_dir`, `plugin_log` | Logs the tools read. The game counts as started when `startup_line` appears in `loader_log`. |
| `harness.*` | The plugin's test harness contract. See [the harness protocol](#the-harness-protocol). |
| `runs.dir` | Where locks, run folders and install state go (default `~/modkit-runs`). |
| `checks.modules`, `paths`, `start_timeout` | Which Python modules hold your checks, and how long to wait for startup (default 120 s). |
| `release.site_url`, `channel`, `seven_zip` ... | For [release installs](#test-what-players-get). |

Three environment variables save typing, and matter because a shell does not keep `export` between an agent's tool
calls: put them on the command line.

| Variable | Meaning |
|---|---|
| `MODKIT_TESTING_CONFIG` | The config file. |
| `MODKIT_SLOT` | The slot number, when `--slot` is not given. There is no default slot. |
| `MODKIT_RUN` | The run id: the owner name of the slot lock, and the folder name for results. Letters, digits, `.`, `-`, `_`; at most 64. |

## Slots, locks and the queue

Slots are queued, not multiplied. Two agents must not use one slot at the same time, and a new slot per agent costs
gigabytes. Each slot has a **lock**. An agent takes a lock, works, and gives it back.

A lock is a folder `<runs.dir>/game.lock.N/` containing `owner.txt`:

```
my-lane pid=0 2026-01-12 14:03:55
```

Creating the folder is atomic, so two agents never both win. The rules:

- **Same owner asks again:** succeeds ("already locked by <owner>").
- **pid = 0:** a *manual* lock, made by `game_slots.py lock`. It lasts until `unlock`. A lane keeps one for its whole
  session, and the runs inside it never free it.
- **pid > 0 and that process is dead:** a *stale* lock. The next `lock` replaces it. `status` shows it as `STALE`.
- **Held by somebody else:** `lock` says who, and with `--wait SECONDS` it polls every 5 seconds until the time is up.
- **`lock any`:** tries slots 2, 3, ... in order and takes the first free one. If all are held, it lists the holders.
- **Slot 1:** always refused.

```sh
python testing/game_slots.py status                          # every slot: folder, running processes, lock, savepath
python testing/game_slots.py list                            # tab separated: number, own|free|locked, folder
python testing/game_slots.py setup [N ...] [--link] [--dry-run]    # make or sync slots (default: all of 2..N); alias: sync
python testing/game_slots.py lock N|any [OWNER] [--wait SECONDS]
python testing/game_slots.py unlock N [OWNER] [--force]
```

`OWNER` defaults to `MODKIT_RUN` (then `manual`); the slot defaults to `MODKIT_SLOT`. `unlock` needs the owner, or
`--force` to clear whatever is there (use it for the lock of a lane that has died). Exit codes: 0 ok, 1 the lock is
held by somebody else (or `unlock` refused it), 2 bad usage, bad config, or slot 1.
`status` shows each lock's age. `unlock` refuses a lock younger than 30 min, or whose owner pid still runs, and names
the age and owner; a manual `owner-*` lock is released by its owner with `MODKIT_RUN=<owner>` (otherwise only after 30 min), or by `--force` once you have confirmed no one is playing; `OWNER` equal to your own `MODKIT_RUN` (you free your own lock) and `--force` pass.

### The pattern for several agents

1. Do all offline work first: edit, build, run unit tests. No slot needed.
2. `python testing/game_slots.py lock any <lane> --wait 0` (one attempt, no waiting). Note the slot number it prints.
   No slot free: stop, file a `ready-for-agent` issue holding the run's steps, and report.
3. Install, run, look. Put the slot and the run id on **every** command:
   `MODKIT_RUN=<lane> python testing/game_checks.py run --slot 2`.
4. `MODKIT_RUN=<lane> python testing/game_slots.py unlock 2 <lane>` (PowerShell: `$env:MODKIT_RUN='<lane>'` first), also when something failed. Do not end your turn while holding a
   slot or while a game you started is still running.

Only touch a slot you hold the lock for, checked at that moment. Never kill processes by a broad filter such as
"all `D2R.exe`": `game_ctl.py stop` closes the window of its own slot and then kills only the process ids that live in
that slot's folder.

## Controlling the game

`testing/game_ctl.py` drives one slot. The slot comes from `--slot N` or `MODKIT_SLOT`. Slot 1 is refused.

```sh
python testing/game_ctl.py --slot 2 status                 # folder, running pids, lock
python testing/game_ctl.py --slot 2 start                  # lock (if needed), launch the loader, wait, size the window
python testing/game_ctl.py --slot 2 shot menu              # screenshot -> <runs.dir>/<run>/screenshots/menu.png
python testing/game_ctl.py --slot 2 key esc enter ctrl+s   # key presses
python testing/game_ctl.py --slot 2 click 0.5 0.62         # click at 50% across, 62% down the game area
python testing/game_ctl.py --slot 2 click 0.5 0.62 right   # a right click
python testing/game_ctl.py --slot 2 console "some command" # a console line; prints what the plugin wrote back
python testing/game_ctl.py --slot 2 harness on|off         # create / remove the harness word file
python testing/game_ctl.py --slot 2 stop
```

Take the lock first with `game_slots.py lock`. When the slot is free, `start` takes it for you as a manual (`pid=0`)
lock of `MODKIT_RUN`, so it does not look stale when the command ends. Only `unlock` removes it.

### No real mouse, no real keyboard

The human may be using the computer, so nothing here moves the real cursor, types real keys, or takes the focus.

| Need | How |
|---|---|
| Find the game | By **process id**: the loader and game programs whose file lives in the slot's folder. The window is the biggest visible window of those pids. The title is never used alone. |
| Start | Launches the slot's loader with "show without activating", sends the window to the back, then sizes it. |
| Screenshot | `PrintWindow` with full-content rendering: works behind other windows and does not need the game in front. Saved as PNG by a pure-Python writer. |
| Keys | `WM_KEYDOWN` / `WM_KEYUP` / `WM_CHAR` window messages posted to the game window. Modifiers (`shift`, `ctrl`, `alt`) are also written into the harness block, because the game asks the keyboard state, not the message. |
| Mouse | The game reads a **virtual cursor** (position, buttons, modifiers) from the plugin's shared-memory block. The tool moves it near the target, then onto it, then presses and releases. Window mouse messages are posted too. |
| Console | A text line goes through the same block; the plugin runs it and answers. |
| Stop | `WM_CLOSE`, wait up to 20 s, then `taskkill` of this slot's own pids only. Removes the harness word file and releases a run lock of the same owner. A manual lock (from `lock` or `start`) stays until `unlock`. |

Key names: `esc enter tab space backspace left up right down`, `f1` to `f12`, `a` to `z`, `0` to `9`, and
`` ` - = . , / ; ' ``. A combination is joined with `+`: `ctrl+s`, `shift+f5`. Only `shift`, `ctrl` and `alt` are
modifiers.

A click needs the harness. Everything else except `console` works without it. If the harness is not reachable the
command says so (`the plugin harness of slot 2 is not reachable`) instead of falling back to the real mouse.

## The harness protocol

The game reads its mouse from the operating system, so a tool outside the game cannot click without taking over the
real cursor. The way out is a small **test harness inside your plugin** (`plugin-template/` does not include one): it makes a named shared
memory block, and the game's input code reads the position and buttons from it while the harness is active.
`testing/` is the other end. This section is the contract. You implement the plugin side once; the Python side is
written already.

Compile the harness **out** of release builds. `release/package_release.py` refuses a plugin DLL that still contains
the text `testharness` (config `package.plugin_forbidden_strings`) and refuses harness files in the mod folder, so the
file names and strings you choose should contain it. See [Test what players get](#test-what-players-get).

### The pieces

| Piece | What it is |
|---|---|
| **Word file** | A file `harness.word_file` in the plugin's folder (`<mod>/<plugins_subdir>/`). When the plugin loads and finds it, the harness is on; when it is missing, the harness is off. `game_ctl.py` creates it before the start and removes it at `stop`. Its content is the `harness.words` of the config joined by spaces, with `{slot}` replaced by the slot number (for example `tag=s2`). The plugin can use the words as options. |
| **Shared memory block** | A named file mapping called `harness.shm_name` with `{pid}` replaced by the game's process id (default `Local\my-harness-block-{pid}`). `harness.shm_name_shared` is an optional fallback name without a pid. Size: `harness.block_bytes` (default 576). |
| **Console file** | `harness.console_file` in the plugin's folder. The plugin **appends** the output of console commands to it. The tools read what was added since a byte offset. |

### The block

The first part is an array of little-endian `int32` values. The index of each field is a config key (`harness.idx_*`);
the defaults are:

| Index | Config key | Written by | Meaning |
|---|---|---|---|
| 0 | `idx_magic` | plugin | Must equal `harness.magic` (default `0x4D4B5448`). The tools ignore a block without it. |
| 1 | `idx_active` | tools | 0, or 1 after the tools have taken over. While 1, the game reads the fields below instead of the real mouse. |
| 2, 3 | `idx_x`, `idx_y` | tools | Virtual cursor in **client pixels** of the game window. |
| 4 | `idx_buttons` | tools | Bit 0 (1) left button, bit 1 (2) right button. |
| 5 | `idx_mods` | tools | Bit 0 (1) shift, bit 1 (2) ctrl, bit 2 (4) alt. Answer the game's keyboard-state query from this. |
| 6 | `idx_seq` | (reserved) | Free for the plugin's own use. |
| 7 | `idx_flags` | tools | `harness.flag_background` (1) means: do not bring the game window to the front. |
| 8 | `idx_cmd_seq` | tools | Command counter. The tools write the command text, then increase this by one. |
| 9 | `idx_cmd_ack` | plugin | The plugin sets this to the `cmd_seq` value it has handled. |
| 10 | `idx_cmd_result` | plugin | Result of that command: 1 = handled by the console. |
| (11, 12, 13) | `idx_player_x`, `idx_player_y`, `idx_player_level` | plugin | **Optional**, suggested indexes 11, 12, 13; the config default is `-1` = not offered. The player's position in world subtiles (the same ones `cheat goto` takes) and the level id, refreshed by the plugin at least every 100 ms while a game runs. A position of (0, 0) means "not written yet". `game_ctl.py moved` reads them and refuses (exit 2) without them; a level change during the action also stops it. |

At byte `harness.command_offset` (default 64) is the command text: UTF-8, ending with a zero byte, at most
`harness.command_max` (default 500) bytes. The block must be big enough: `command_offset + command_max + 1` must fit in
`block_bytes`.

### What the tools do

1. Find the block (`shm_name` with the game's pid, then `shm_name_shared`) and check the magic.
2. **Activate:** set `flags`, set the cursor to `harness.cursor_start` (default 800, 450), then set `active = 1`.
3. **Move and click:** write `x`, `y`; write `buttons` (1 or 2) for 80 ms, then 0.
4. **Command:** write the text at `command_offset`, add 1 to `cmd_seq` (it wraps at 2^31), then poll `cmd_ack` for up
   to 10 s until it equals that value. If it does, read `cmd_result`.

### What the plugin must do

- Create the block and set `magic` first, before anything reads it. Create it only when the word file exists.
- While `active` is 1, return the cursor position, button state and modifier state from the block for the game's own
  input queries. When `flags` has the background bit, do not raise or focus the window.
- Watch `cmd_seq`. When it changes: run the text as a console line, append any output to the console file, write
  `cmd_result`, and write `cmd_ack = cmd_seq` **last**, so that the tools never read a result that is not ready.
- Keep the same indexes as your config. The names and numbers are a contract: change them in `[harness]` **and** in the
  plugin, nowhere else.

### Without a harness

Checks can still do a lot: start and stop, screenshots, key presses, reading the logs and the crash folder, and
comparing what the screen looks like. A check that needs the harness calls `ctx.require_harness()` and is **skipped**,
not failed, when it is missing.

## Writing and running checks

A **check** is a Python function with a name and tags. It passes when it returns, fails when it raises
`AssertionError` (or any other error), and is skipped when it calls `ctx.skip("why")`. A broken check never stops the
run: the next one still runs.

```python
# my-checks/my_checks.py
from game_checks import check
import game_ctl


@check("main-menu-looks-right", tags=["smoke", "game"])
def main_menu_looks_right(ctx):
    """The main menu shows the same panel art as the reference picture."""
    ctx.ensure_running()
    img = ctx.game.screenshot()
    box = img.box(0.35, 0.40, 0.65, 0.90)          # fractions of the window: a fixed part of the screen
    ctx.shot("menu")
    got = img.signature(box)                        # a 12 x 16 grid of grey averages
    assert game_ctl.signature_distance(got, REFERENCE) < 6, "the menu looks different"
    return "menu matches"
```

Register the module in the config and run it:

```toml
[checks]
modules = ["example_checks", "stock_checks", "my_checks"]
paths = ["my-checks"]
```

`stock_checks` is the toolkit's own module of checks any mod can use; `slot-savepath` fails when a slot's modinfo.json
`savepath` is not the slot's own save folder.

```sh
python testing/game_checks.py list                                  # name, tags, first line of the doc string
python testing/game_checks.py list smoke
python testing/game_checks.py run --slot 2                          # every check
python testing/game_checks.py run config-sane game-starts --slot 2  # by name
python testing/game_checks.py run tag:smoke --slot 2                # by tag (a bare word that is not a name works too)
python testing/game_checks.py run smoke --slot 2 --run-id before-fix --keep --stop-on-fail
```

Options of `run`: `--slot N` (or `MODKIT_SLOT`), `--run-id ID` (default `MODKIT_RUN`, else `run-<date>-<time>-s<slot>`),
`--keep` (leave the game running at the end), `--stop-on-fail`. Global options, given *before* `run` or `list`: `--config FILE`, `--module NAME` and
`--path DIR` (add a check module or a folder to find it in). Checks run in the order they were registered, each once.

**The `leaves-town` tag.** A check that warps the character out of town (for example `cheat goto`) is tagged
`leaves-town` (`d2r_only.LEAVES_TOWN`) next to `game`. Run those only on a slot you locked for out-of-town checks, never
under a starting-town-only rule. `testing/d2r_only.py` (Terror Zone, Herald and Colossal portal checks) has such
checks; its pixel threshold is calibrated on build 93847 at a 1920x1080 client, default brightness, HDR off.

### What a check gets: `ctx`

| Member | Use |
|---|---|
| `ctx.cfg`, `ctx.slot` | The config and the slot number. `cfg.slot_dir(n)`, `cfg.mod_dir(n)`, `cfg.plugins_dir(n)`, `cfg.loader_log(n)`, ... |
| `ctx.game` | The `game_ctl.Game` of the slot: `is_running()`, `pids()`, `window()`, `screenshot()`, `key("esc")`, `click(fx, fy)`, `console(cmd)`, `console_mark()` / `console_new(mark)`, `log_mark()`, `crash_files()`. |
| `ctx.ensure_running()` | Starts the game if it is not up. If this run started it, the run stops it at the end (unless `--keep`). |
| `ctx.shot(name)` | Screenshot into this run's folder; returns the path. |
| `ctx.require_harness()` | The harness, or skip the check. |
| `ctx.skip(why)`, `ctx.fail(why)` | Skip, or fail with a message. |
| `ctx.log(msg)` | A line kept in `results.json` for this check. |
| `ctx.shared` | A dict shared by all checks of the run. `shared["crash_before"]` is the crash files that existed before it. |

Helpers in `game_ctl`: `wait_for(fn, timeout, interval, desc)` (poll until true, raises `WaitTimeout`), `wait_log(path,
needle, timeout, offset)`, and the picture tools of `Image`: `stats()` (mean and spread of the grey level),
`signature(box)`, `box(fx0, fy0, fx1, fy1)`, `pixel(x, y)`, and `signature_distance(a, b)`.

### Ready-made parts for a mod's checks

Three modules hold parts that are the same for every mod. The plugin, the mod and the character are always parameters;
nothing about a mod is written in them.

| Module | What it gives |
|---|---|
| `check_helpers.plugin_log(ctx, plugin, scope="auto", skip_if_missing=False, since_size=0)` | The text of `<plugin>`'s log since its last `<plugin>: <version> loaded (` line, so an old run does not count. `scope` is `mod` (`<mod>/d2rloader/logs/`), `game` (the slot's `d2rloader/logs/`), `config` (the config's `[logs] plugin_log`) or `auto` (that config key when it names `<plugin>.log`, else the mod log, else the game-wide log). `plugin_log_path` gives the path, `plugin_log_size` the size to pass as `since_size` (taken before the game starts) to ignore everything already in the file. |
| `lod_checks.py` | `assert_plugin_loaded(ctx, plugin, mod, expect=...)`, `read_save` / `check_save` (signature, size field, checksum), `save_and_exit` (Esc, Save and Exit, waits until the whole save is written in the extended format and its `.d2rl` sidecar matches it; a half-written file counts as not yet), `delete_character`, and `create_save_reload(ctx, char, class_name=...)`, which creates a Lord of Destruction character, saves, restarts the game, loads and saves again. Needs the harness; run it only in a slot you locked. |
| `menu_layout.py` | The click positions of the main menu, the create-character screen and the Esc menu as fractions of the window, with the class portraits. Measured for **D2R 3.3 at 1920x1080** (`D2R_VERSION`, `CLIENT`): re-measure them for another D2R version, and add a class by passing `class_pos` and `class_id` to `create_save_reload`. |

### The example checks

| Check | Tags | What it checks |
|---|---|---|
| `config-sane` | offline, smoke | The slot folder, the loader, the mod folder and the plugin DLLs are where the config says. Needs no game. |
| `game-starts` | smoke, game | The game launches in the slot and gets a window. |
| `main-menu-visible` | smoke, game | The window shows a real picture (not black, not flat) within a minute. Tuned by `checks.menu_min_mean` and `menu_min_stddev`. |
| `console-echo` | harness | A console line (`checks.echo_command`) sent through the harness is answered by the plugin. |
| `no-new-crash-files` | smoke | The loader wrote no crash file since the run began. |

Tips for good checks:

- **One thing per check**, with a message that says what was expected: `assert x, "the stash shows 2 tabs"`.
- **Wait for a condition, not for time.** Use `wait_for` or `wait_log`; a fixed `sleep` is too short on a slow day and
  too long on a fast one.
- **Take a screenshot before the assertion**, so a failure comes with a picture.
- **Compare art with `signature`**, not byte by byte. The game draws animated things, and the signature averages them.
- **Read the logs.** The loader log and your plugin's log are often a better proof than a picture.

## Screenshots and results

Everything a run writes goes to `<runs.dir>/<run id>/`:

| File | Content |
|---|---|
| `results.json` | `run_id`, `slot`, `started`, `finished`, `duration_s`, `counts` (pass / fail / skip), and for each check: `name`, `tags`, `status`, `message`, `duration_s`, `screenshots` (paths relative to the run folder), `log`. |
| `summary.txt` | The same in text: `PASS name (1.2 s) message`, one line per check, then its screenshots. |
| `screenshots/<check>-<name>.png` | The game window's client area, as PNG. |

`game_ctl.py shot NAME` outside a run saves under the run named by `MODKIT_RUN`, else `adhoc`.

Screenshots show the game. Keep the whole `runs.dir` **outside the repository**, and never commit a screenshot of the
game, a save or a log. Share a result by its summary text, or by describing what the picture shows.

### Screenshots that settle the question

One shot should answer the question. Before each shot:

- **A quiet spot:** warp to a spot with no monsters, or repeat `cheat killmonster` (or `cheat monfreeze 1`), and shoot
  once nothing casts or burns near you.
- **The dark:** structure shots (walls, edges, floors) need light: `cheat stat item_lightradius,25` (`game_ctl.py pair`
  does it with `--light`). The radius stays raised for the game session, so never raise it for a lighting shot.
- **Pin the DS1 variant** ([Pin a DS1 variant](#pin-a-ds1-variant)) on every level with several.
- **Lighting shots:** take several frames with no combat effects (fire, poison and spells skew the brightness) and use the
  median luma over the frames.
- **Before and after pairs** for a visual change: the same spot and settings, old build and new, or HD and legacy.
- A picture that is not blank is not proof of the effect: say what you expected, then what you saw.

### The game-check recipe

Lock a slot, install and check the savepath, pin the DS1 variant if there are several, start the game, set cheats, warp,
shoot, stop, unlock, report (pass, fail and skip counts). Hold one lock from install to cleanup, and never `lock any`.
The steps with the commands are in the `d2r-in-game-testing` skill.

## Reading units (unit_probe)

`testing/unit_probe.py` lists the units the game client holds right now (monsters alive, missiles, by their table row) and
groups missiles that appear together into bursts, so a check can count "how many of this missile did one cast make".
It uses `ReadProcessMemory` only (it never writes to the game), needs no plugin, and works on **build 93847** only: it
refuses any other image. Its addresses are copies of `shared/plugin-common/src/rvas_93847*.h`, and a unit test fails if
they drift.

```python
from unit_probe import UnitProbe, MONSTER, bursts
with UnitProbe.for_slot(cfg, 2) as probe:      # needs: MODKIT_RUN=<lane> and `game_slots.py lock 2 <lane>`
    print(probe.units(MONSTER))
    print(bursts(probe, row=5, seconds=3.0))
```

`UnitProbe.for_slot(cfg, n)` is the only way in: it refuses slot 1 (your own game), a slot that is not locked by
`MODKIT_RUN`, and a slot without a running game, and it takes the process id from that slot's own process list.

## Test what players get

A developer install is not what players have. Your install may use loose text tables, debug switches and a test
harness that the release build leaves out. Bugs hide there and show up for players. So for anything player-facing, test
the **published release**: `testing/release_install.py` fetches it from your download site, checks every hash, and
installs it into a slot exactly as the downloader would. The site layout is the one described in
[release.md](./release.md).

```sh
python testing/release_install.py check                          # read the channel and manifest, verify, change nothing
python testing/game_slots.py lock 2 my-lane
MODKIT_RUN=my-lane python testing/release_install.py install --slot 2
MODKIT_RUN=my-lane python testing/game_checks.py run smoke --slot 2
MODKIT_RUN=my-lane python testing/release_install.py restore --slot 2     # your developer install is back
MODKIT_RUN=my-lane python testing/game_slots.py unlock 2 my-lane   # PowerShell: $env:MODKIT_RUN='my-lane'; python ...
```

| Command | What it does |
|---|---|
| `check` | Reads `channels/<channel>.json` and the manifest, verifies the manifest's sha256 and fields. Changes nothing. Needs no slot. |
| `install --slot N` | Needs the slot lock held by `MODKIT_RUN` and no game running in the slot. Downloads **everything first** and verifies every sha256, then moves the slot's mod folder aside (`<slot>.release-backup`), puts the release in its place, points `modinfo` at the slot's own save folder, and writes the release's launch keys plus `release.extra_launch_args` (default `-w`, windowed, so it can be captured) into the slot's loader config. A failure before the swap changes nothing. |
| `restore --slot N` | Puts the backed-up mod folder and loader config back. |
| `status --slot N` | Shows what is installed (`release-install.json` in `<runs.dir>/release-install-sN/`). |

Options: `--channel C` (default `release.channel`), `--site S` (`https://host/path/`, `dir:<folder>` or `file:///folder`;
default `release.site_url`; the `dir:` form works on a local copy of the site, with no network),
`--method auto|archive|objects` (the 7z needs 7-Zip; `objects` is file by file in pure Python; `auto` uses the 7z when
7-Zip is found), and `--harness-dll FILE` (repeat for more). Release builds leave the test harness out, so a
`--harness-dll` copies a harness-enabled build of your plugin over the release's one for this test. The release's own
file is kept in the state folder, and `restore` brings back your previous mod folder.

It refuses: slot 1; a manifest with `complete: false`; unsafe paths (`..`, drive letters, backslashes); a manifest
that does not match the channel's `manifestSha256`; a `modFolder` other than `mod.folder`; and a slot mod folder that is
not inside the slot's `mods` folder. It accepts `schemaVersion` 1 for channel files and 2 for manifests (config keys
`release.channel_schema` and `release.manifest_schema`; 0 turns the check off).

Also compare the versions in a player's report with yours before you chase a ghost: game build, loader version and
plugin version. Many "bugs" are a stale plugin copy or a loader that starts another mod.

## Pin a DS1 variant

A level with several DS1 variants rolls one per game. To land on the preset under test, pin the level in the slot's
installed `lvlprest.txt`:

```
MODKIT_RUN=my-lane python testing/force_ds1.py --slot 2 "Dark Temple Map=DarktempleV2.ds1"
MODKIT_RUN=my-lane python testing/force_ds1.py --slot 2 --reset
```

This is test-only. It needs the slot lock held by `MODKIT_RUN`, refuses slot 1 and a slot whose game runs, and touches
only the slot's installed copy (the original is saved beside it as `lvlprest.txt.force-ds1.orig`). `--reset` or a
reinstall of the slot undoes it. The mod must ship its own `lvlprest.txt`.

## Targeted tests and the full suite

The full suite is slow and needs the game. Do not run it after every change.

| When | Run |
|---|---|
| Every change | The build validator (`python -m modkit build <project>`), the unit tests (`python -m unittest discover -s tests`), and `config-sane`. All offline. |
| A change that could break startup | The `smoke` tag: `config-sane`, `game-starts`, `main-menu-visible`, `no-new-crash-files`. |
| A change in one area | The checks for that area only. Tag your checks by area (`skills`, `stash`, `ui`), and keep a short table in your project: *source file or data table, then checks that exercise it*. Run those, plus `smoke`. |
| Something player-facing | The same checks on a slot with the **release install**. |
| Milestones: end of a phase, before a big release, before the owner plays after many changes | Everything, one game at a time. |

The unit tests of the tools themselves are in `tests/` (`test_testing_*.py`, `test_release_*.py`) and use fakes, so they
need no game and no server:

```sh
python -m unittest discover -s tests -p "test_testing_*.py"
```

## Who runs the check

Agents run in-game checks themselves, in a slot; the human is asked only when a check needs one (a real-player
judgement, input the harness cannot send, or the human's own game). The order of work, the screenshot rules and the
testing rules are in the `d2r-in-game-testing` skill (`.claude/skills/d2r-in-game-testing/SKILL.md`).

### The test character

Every test character is **level 99 with experience 3520485254, 490 stat points and 98 skill points** (owner rule,
2026-11-11). Make it with the game closed: `python -m modkit save-set <save.d2s> level=99 experience=3520485254
statpts=490 newskills=98` (backs the folder up first; add `--extended` for a mod with `"extendedSaves": true`), and open Hell with `save_edit.unlock_difficulties(<save.d2s>)` (a function, no command line; the call is in the `d2r-in-game-testing` skill). The level-99 line has not yet been run on a real save. Create it with the
Reign of the Warlock game version (the default). A Classic or Lord of Destruction character plays D2R's vanilla base
tables, not the mod's, unless the mod also writes `excel/base/`; see [cheat-commands.md](../knowledge/cheat-commands.md).

## Evidence levels

What a result proves, from weakest to strongest. Say which level you reached.

1. **Offline validation:** the build and the unit tests. Catches data errors; cannot show that a skill renders, an item
   can be used or a portal works.
2. **Startup smoke:** the `smoke` tag. Infrastructure evidence, not feature correctness.
3. **Mechanic checks:** do the action and compare what the game does (and what the plugin's log says) with a stated
   result. A **prepared** character (a save edited with `save-set`, console-spawned gear, god mode, Hell at level 99) is
   an efficient fixture for this. It is not evidence of campaign progression or balance.
4. **Progression checks:** a **fresh** character played through the intended journey. Only this shows that the journey
   works.
5. **Persistence checks:** save, exit, reload, and read the real character and item state. A one-session success says
   nothing about saving.
6. **Packaged checks:** the artifact players get ([Test what players get](#test-what-players-get)). A developer harness
   build is useful, but does not replace a smoke check of the unmodified package.

**Exit 0 does not mean nothing was skipped.** `Context.require_harness()` skips when no harness is reachable, and many
checks skip until a log line exists. The runner counts pass, fail and skip separately and can exit 0 with skips; the
required behaviour is unverified if its check skipped. Read the counts and the skip messages, not the exit code. A check
that reads an accumulated plugin log can pass on a line from an earlier session: mark the log offset, do the action
fresh, and verify the installed data and DLL are the ones under test.

## Practical hazards

What went wrong in real test runs.

- **An acknowledgement is not command output.** The harness's console file says only that the line was handled or
  refused. What the command printed is in the log of the plugin that ran it. Read that log before you say a cheat worked.
- **The background flag.** Some world clicks only reach the game with the harness's background flag off. Menu clicks
  that work do not prove combat clicks do. Check the screenshot after the first world click.
- **Zero durability after a reload.** Items spawned by the console read `Durability: 0` after the game is saved and
  loaded again, and a 0-durability item has its stats switched off. Spawn fresh items after every load and hover them
  before the test. This also means a reload test of spawned gear tests nothing.
- **A held cursor item** (a red cell behind every inventory item) blocks tooltips and the next click. Look at each
  screenshot for it. An unidentified item cannot be equipped: `cheat idall`.
- **`cheat item` and `cheat gold` do not work** as the item or gold source. Use `cheat spawn <code>,inv 0` and
  `cheat uniques <row>`, with codes and rows from the installed mod's built tables
  ([cheat-commands.md](../knowledge/cheat-commands.md)). Turn cheats on with `debug_mode` first.
- **Wait for conditions, not for time.** Prefer a log event or a screen change to a fixed sleep. Take the screenshot
  before the assertion.
- **`--no-validate` is debt.** An install or build that skips the validator does not prove the validator is clean.
  Record the bypass and the errors it hides in the report as a limitation; do not inherit it silently.
- **Do not kill other people's games.** Clean up only the game you started; the check runner stops games it started and
  leaves games and manual locks it did not.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `slot 1 is the user's own game ...` | You asked for slot 1. Use a slot from 2 to `game.slot_count`. This is on purpose. |
| `no testing config found` | No config was found, so the tool refused to touch a slot (it never falls back to the built-in defaults). Check `--config`, `MODKIT_TESTING_CONFIG`, or that `./modkit-testing.toml` exists in the current folder. |
| `slot 2 held by <owner> pid=...` | Somebody has the slot. Take another (`lock any`) or look at `status`; if none is free, stop and file a `ready-for-agent` issue. |
| A lock shows `STALE` | Its process died. The next `lock` replaces it. For a `pid=0` lock of a lane that has gone, `unlock N --force`. |
| `slot 2 is not locked by MODKIT_RUN=...` | `release_install.py` needs the lock *and* the same name in `MODKIT_RUN`. Take it with `lock 2 <lane>`, then run with `MODKIT_RUN=<lane>`. |
| `the game of slot 2 is not running` | Run `game_ctl.py --slot 2 start`, or use `ctx.ensure_running()` in the check. |
| `no loader at ...` | The slot is not set up. Run `game_slots.py setup 2`. |
| `timed out ... waiting for 'D2R startup complete.'` | The line is not in the loader log. Look at the log (`logs.loader_log`), fix `logs.startup_line` for your loader version, or raise `checks.start_timeout`. |
| `the plugin harness of slot 2 is not reachable` | The plugin did not make the block. Is the word file there (`game_ctl.py harness on` before the start), is the plugin DLL a harness build, do `harness.shm_name` and `magic` match the plugin? Release builds have no harness. |
| `the game window is minimized or has no size` | The window was minimized. The tool restores it without taking focus; try again. |
| A screenshot is black | The game was still loading, or the window is on a monitor that was switched off. Wait with `wait_for` on a non-blank screen. |
| `modkit install` says the game is running | It refuses while any `D2R.exe` or `D2RLoader.exe` runs on the machine, in any slot. Stop the games, install, start again. |
| `<slot>.release-backup exists but there is no install record` | A release install was interrupted. Look at the folder; remove it by hand if it holds nothing you need. |
| `the manifest does not match the channel's sha256` | A half-published release or a cache. Wait a minute and retry; see [release.md](./release.md). |
| A check passes on your install and players crash | Your install is not the release package. Use `release_install.py` and run the check again. |
| Crash in a slot | Keep the loader log and the crash file from `logs.crash_dir`. Your plugin's own log may stop silently when the game dies. `no-new-crash-files` catches it. |
