"""Reusable parts of game checks that need a Lord of Destruction character: the plugin-loaded check, reading a save,
Save and Exit, and the create / save / reload flow.

The plugin, the mod and the character are parameters; nothing about a mod is written here. A mod's own check module
imports these and registers its checks:

    from game_checks import check
    import lod_checks

    @check("plugin-loaded", tags=["skeleton", "game"])
    def plugin_loaded(ctx):
        return lod_checks.assert_plugin_loaded(ctx, "my-plugin", "MyMod")

    @check("lod-character-saves", tags=["skeleton", "game"])
    def lod_character_saves(ctx):
        return lod_checks.create_save_reload(ctx, "lodcheck")

The character flow clicks through the menus with the test harness (the slot's game-wide harness plugin, see
docs/testing.md) at the positions in menu_layout.py (D2R 3.3, 1920x1080). Character names are letters only.
Run only in a slot you locked.
"""
from __future__ import annotations

import os
import re
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # the toolkit root, for modkit
import check_helpers  # noqa: E402
import game_ctl  # noqa: E402
import menu_layout as ml  # noqa: E402
from check_helpers import plugin_log  # noqa: E402,F401  (re-exported: lod_checks.plugin_log)
from modkit.saves import checksum  # noqa: E402

SIGNATURE = b"\x55\xaa\x55\xaa"
EXTENDED_MARK = b"RD"   # bytes 6-7 of a D2RLoader extended-format save
NAME_OFFSET = 0x12B
CLASS_OFFSET, LEVEL_OFFSET = 0x18, 0x1B


# ---------------------------------------------------------------- plugin

def assert_plugin_loaded(ctx, plugin: str, mod: str, expect: tuple[str, ...] = (), scope: str = "auto",
                         timeout: float = 90, since_size: int = 0) -> str:
    """The mod runs and `plugin` logged its load line `<plugin>: <version> loaded (mod <mod>, ...)`. Every string in
    `expect` must also be in the log since that load (for example a plugin's own "environment ok" line). Returns the
    load line. The log may hold earlier runs: the latest load line counts, so to require one from this run take
    `since_size = check_helpers.plugin_log_size(ctx, plugin, scope)` before the game starts and pass it here (only
    log text after that byte offset is looked at)."""
    ctx.ensure_running()
    try:
        game_ctl.wait_for(lambda: check_helpers.plugin_log(ctx, plugin, scope, since_size=since_size), timeout, 2.0,
                          f"{plugin}'s load line")
    except game_ctl.WaitTimeout:
        raise AssertionError(f"no '{plugin}: ... loaded' line in the plugin log (plugin not loaded?)")
    log = check_helpers.plugin_log(ctx, plugin, scope, since_size=since_size)
    m = re.search(rf"{re.escape(plugin)}: (\S+ loaded \([^\n]*)", log)
    assert m, f"no load line in the plugin log of {plugin}"
    loaded = m.group(1)
    assert f"loaded (mod {mod}," in loaded, f"expected mod {mod}: {loaded}"
    for text in expect:
        assert text in log, f"{text!r} is not in the log of {plugin} since its load"
    return loaded


# ---------------------------------------------------------------- saves

def save_path(ctx, char: str) -> str:
    return os.path.join(ctx.cfg.save_dir(ctx.slot), char + ".d2s")


def read_save(ctx, char: str) -> bytes:
    """The character's .d2s, after checking the signature, the size field and the checksum."""
    with open(save_path(ctx, char), "rb") as f:
        data = f.read()
    check_save(data)
    return data


def check_save(data: bytes) -> None:
    assert data[:4] == SIGNATURE, "not a .d2s"
    assert struct.unpack_from("<I", data, 8)[0] == len(data), "size field differs from the file size"
    assert struct.unpack_from("<I", data, 0xC)[0] == checksum(data), "bad checksum"


def sidecar_matches(sidecar: bytes, save: bytes) -> bool:
    """The `.d2rl` sidecar was written for this `.d2s`: magic `D2RL`, and its copies of the save's checksum (0x34) and
    size (0x38) equal the save's (knowledge/saves.md)."""
    return (len(sidecar) >= 0x3C and sidecar[:4] == b"D2RL"
            and struct.unpack_from("<II", sidecar, 0x34) == (struct.unpack_from("<I", save, 0xC)[0], len(save)))


def _read_bytes(path: str) -> bytes | None:
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


def _save_done(path: str, before: float, requested: float) -> bool:
    """True once `path` was rewritten after `before` in the extended format, complete (size and checksum fine), and its
    sidecar matches it or is newer than the save request. A half-written file is "not yet", not an error."""
    try:
        if os.path.getmtime(path) <= before:
            return False
    except OSError:
        return False
    data = _read_bytes(path)
    if data is None:
        return False
    try:
        check_save(data)
    except (AssertionError, struct.error):
        return False
    if data[6:8] != EXTENDED_MARK:
        return False
    sidecar_path = path[:-4] + ".d2rl"
    sidecar = _read_bytes(sidecar_path)
    if sidecar is None:
        return False
    if sidecar_matches(sidecar, data):
        return True
    try:
        return len(sidecar) >= 0x3C and sidecar[:4] == b"D2RL" and os.path.getmtime(sidecar_path) > requested
    except OSError:
        return False


def save_and_exit(ctx, char: str, label: str, timeout: float = 30) -> None:
    """Esc, Save and Exit; waits until the game wrote the whole save in D2RLoader's extended format (`RD`) and its
    `.d2rl` sidecar for it (the sidecar's checksum and size copies match the save, or it is newer than the request), so
    the next read sees the finished files. A half-written file counts as not yet."""
    path = save_path(ctx, char)
    before = os.path.getmtime(path)
    ctx.game.key("esc")
    time.sleep(1.5)
    ctx.shot(f"{label}-menu")
    requested = time.time()
    ctx.game.click(*ml.SAVE_AND_EXIT)
    game_ctl.wait_for(lambda: _save_done(path, before, requested), timeout, 1.0, f"{char}.d2s saved on exit")
    read_save(ctx, char)  # a real problem (signature, size, checksum) now raises with its own message
    time.sleep(3)
    ctx.shot(f"{label}-select")


def delete_character(ctx, char: str) -> None:
    """Remove the character's files from the slot's save folder (game closed: character select caches the list)."""
    folder = ctx.cfg.save_dir(ctx.slot)
    for name in os.listdir(folder) if os.path.isdir(folder) else []:
        if os.path.splitext(name)[0] == char:
            os.remove(os.path.join(folder, name))


# ---------------------------------------------------------------- create, save, reload

def create_save_reload(ctx, char: str, class_name: str = "barbarian", class_pos: tuple[float, float] | None = None,
                       class_id: int | None = None) -> str:
    """A new Expansion (Lord of Destruction) character is created, saved on exit, and after a game restart loads and
    saves again. Deletes an old character of the same name first. `class_name` picks a class portrait measured in
    menu_layout.CLASSES; for another class pass `class_pos` (the portrait's fractions) and `class_id` (the save's
    class byte). Returns a one-line summary."""
    if class_pos is None:
        if class_name not in ml.CLASSES:
            raise ValueError(f"menu_layout has no portrait for {class_name!r}: pass class_pos and class_id")
        want_class, class_pos = ml.CLASSES[class_name]
    else:
        if class_id is None:
            raise ValueError("class_pos needs class_id (the class byte the save should hold)")
        want_class = class_id
    if not re.fullmatch(r"[A-Za-z]{2,15}", char):
        raise ValueError(f"character name {char!r}: letters only, 2 to 15")
    ctx.require_harness()
    ctx.game.stop()  # character select caches the list: delete the last run's character with the game closed
    delete_character(ctx, char)
    ctx.ensure_running()
    ctx.require_harness()
    time.sleep(5)  # the menu takes input a little after the window shows

    ctx.game.click(*ml.CREATE_NEW)
    time.sleep(3)
    ctx.game.click(*class_pos)
    time.sleep(3)
    ctx.game.click(*ml.VERSION_LIST)
    time.sleep(1)
    ctx.game.click(*ml.EXPANSION)
    time.sleep(1)
    ctx.game.click(*ml.NAME_FIELD)
    for c in char:
        ctx.game.key(c)
    ctx.shot("create")
    ctx.game.click(*ml.CREATE)
    game_ctl.wait_for(lambda: os.path.isfile(save_path(ctx, char)), 30, 1.0, f"{char}.d2s created")
    time.sleep(10)  # entering Act 1
    ctx.shot("created")
    save_and_exit(ctx, char, "first")
    first = read_save(ctx, char)
    assert first[CLASS_OFFSET] == want_class and first[LEVEL_OFFSET] == 1, \
        f"class {first[CLASS_OFFSET]} level {first[LEVEL_OFFSET]}, want a level 1 {class_name} ({want_class})"

    ctx.game.stop()
    ctx.ensure_running()
    ctx.require_harness()
    time.sleep(5)
    ctx.shot("restarted")
    ctx.game.click(*ml.PLAY)  # the only character, so it is selected
    time.sleep(12)
    ctx.shot("reloaded")
    save_and_exit(ctx, char, "second")
    second = read_save(ctx, char)
    assert second[NAME_OFFSET:NAME_OFFSET + len(char)] == char.encode(), "the save holds another name"
    return f"{char}: {len(first)} bytes after creation, {len(second)} after the reload, checksums ok, extended format"
