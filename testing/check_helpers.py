"""Helpers for game checks: a paired HD/legacy shot at a warp point, and a probe that says whether the character moved.

  python testing/game_ctl.py --slot N pair NAME LEVEL,X,Y [--light 12] [--settle 3] [--key g]
  python testing/game_ctl.py --slot N moved (click FX FY [right] | key KEY..) [--wait 1.5]

`pair` raises the light radius (`cheat stat item_lightradius,N`, so a dark map is readable; it lasts for the rest of the
game session), warps (`cheat goto LEVEL,X,Y`), waits `--settle` seconds, shoots, presses the toggle key (`g`, D2RLoader's legacy graphics), shoots, presses it
back, and saves HD on the left and legacy on the right as <run>/screenshots/NAME.png. Before every shot and key the
game window is looked up again (by PID), so a window that was recreated is not lost. It warns when both shots are
identical (the toggle did nothing, or the game is not in HD) and then exits 1. It prints the HD-to-legacy distance and the
noise between two HD shots; identical means the distance is within max(IDENTICAL_MAX, 3 x noise).

`moved` reads the player's position before and after the action and prints whether and how far the character moved
(exit 0 = moved, 1 = did not, 2 = cannot tell). It needs the plugin to write the position into the harness block
(`harness.idx_player_x`, `idx_player_y`, optionally `idx_player_level`: world subtiles, see docs/testing.md) and refuses
(exit 2) without it: there is no screen fallback, because animation made it report a move at a wall. The pure parts
(pairing, identical shots, the position difference) are plain functions below. Everything that needs the game goes
through a `game_ctl.Game`.
"""
from __future__ import annotations

import math
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_ctl  # noqa: E402
from game_ctl import GameCtlError, Image  # noqa: E402

SETTLE = 3.0        # seconds after a warp before the first shot (the level loads)
TOGGLE = 1.5        # seconds after the toggle key before the shot
LIGHT = 12          # item_lightradius value; a few levels above the default makes a dark map readable
LIGHT_STAT = "item_lightradius"
MOVED_MIN = 2.0     # world subtiles; less than this is not a move (a tile is 5 subtiles)
IDENTICAL_MAX = 0.5   # signature distance (mean grey levels per cell) at or below this, and within 3x the noise, is the same picture
NOISE_FACTOR = 3.0
NOISE_WAIT = 0.5      # seconds between the two HD shots that measure the noise


# ---------------------------------------------------------------- pure parts

def side_by_side(left: Image, right: Image) -> Image:
    """One image holding two of the same size, `left` on the left."""
    if (left.width, left.height) != (right.width, right.height):
        raise ValueError(f"the two shots differ in size ({left.width}x{left.height} and {right.width}x{right.height})")
    stride = left.width * 3
    rows = [left.rgb[y * stride:(y + 1) * stride] + right.rgb[y * stride:(y + 1) * stride] for y in range(left.height)]
    return Image(2 * left.width, left.height, b"".join(rows))


def split_pair(pair: Image) -> tuple[Image, Image]:
    """The inverse of side_by_side: the left and the right half of a pair image."""
    if pair.width % 2:
        raise ValueError(f"a pair image has an even width, not {pair.width}")
    half = pair.width // 2
    stride = pair.width * 3
    left = [pair.rgb[y * stride:y * stride + half * 3] for y in range(pair.height)]
    right = [pair.rgb[y * stride + half * 3:(y + 1) * stride] for y in range(pair.height)]
    return Image(half, pair.height, b"".join(left)), Image(half, pair.height, b"".join(right))


def distance(a: Image, b: Image) -> float:
    """Signature distance of two shots (0 = same picture); infinite when the sizes differ."""
    if (a.width, a.height) != (b.width, b.height):
        return float("inf")
    return game_ctl.signature_distance(a.signature(), b.signature())


def identical(shot: Image, other: Image, noise: float = 0.0, tol: float = IDENTICAL_MAX) -> bool:
    """True when `other` is the same picture as `shot`: within `tol`, and within NOISE_FACTOR times `noise`, the
    distance between two shots of the same scene (fire and monsters move even when nothing changed)."""
    return distance(shot, other) <= max(tol, NOISE_FACTOR * noise)


def parse_warp(text: str) -> tuple[int, int | None, int | None]:
    """'189,20222,10162' -> (189, 20222, 10162); '189' -> (189, None, None)."""
    parts = [p.strip() for p in text.replace(" ", ",").split(",") if p.strip()]
    if len(parts) not in (1, 3) or not all(p.lstrip("-").isdigit() for p in parts):
        raise GameCtlError(f"a warp is LEVEL or LEVEL,X,Y (numbers), not {text!r}")
    nums = [int(p) for p in parts]
    return (nums[0], None, None) if len(nums) == 1 else (nums[0], nums[1], nums[2])


def goto_line(level: int, x: int | None = None, y: int | None = None) -> str:
    return f"cheat goto {level}" if x is None else f"cheat goto {level},{x},{y}"


def position_diff(before: tuple[int, int], after: tuple[int, int], min_move: float = MOVED_MIN
                  ) -> tuple[bool, int, int, float]:
    """(moved, dx, dy, distance in subtiles) between two player positions."""
    dx, dy = after[0] - before[0], after[1] - before[1]
    dist = math.hypot(dx, dy)
    return dist >= min_move, dx, dy, dist


def describe_move(moved: bool, dx: int, dy: int, dist: float) -> str:
    if not moved:
        return f"did not move (dx {dx}, dy {dy}, {dist:.1f} subtiles)"
    return f"moved dx {dx}, dy {dy} ({dist:.1f} subtiles, about {dist / 5:.1f} tiles)"


# ---------------------------------------------------------------- plugin log

def plugin_log_path(cfg, slot: int, plugin: str, scope: str = "auto") -> str:
    """Where <plugin>'s log is. D2RLoader writes a mod-scoped plugin's log inside the mod folder
    (<mod>/d2rloader/logs/) and a game-wide plugin's in the slot's own d2rloader/logs/. scope: "mod", "game",
    "config" (the config's `[logs] plugin_log`, the harness's single log; "" if it is not set), or "auto" (the config's
    plugin_log when it is set and is named `<plugin>.log`, else the mod folder's log if there is one, else the
    game-wide one)."""
    mod = os.path.join(cfg.mod_dir(slot), "d2rloader", "logs", f"{plugin}.log")
    game = os.path.join(cfg.slot_dir(slot), "d2rloader", "logs", f"{plugin}.log")
    if scope == "mod":
        return mod
    if scope == "game":
        return game
    if scope == "config":
        return cfg.plugin_log(slot)
    if scope != "auto":
        raise ValueError(f"scope must be 'mod', 'game', 'config' or 'auto', not {scope!r}")
    configured = cfg.plugin_log(slot)
    if configured and os.path.basename(configured) == f"{plugin}.log":
        return configured
    return mod if os.path.isfile(mod) or not os.path.isfile(game) else game


def plugin_log_size(ctx, plugin: str, scope: str = "auto") -> int:
    """The size in bytes of <plugin>'s log now (0 if none). Take it before starting the game and pass it as
    `since_size` to plugin_log, so a previous run's lines do not count."""
    return game_ctl.file_size(plugin_log_path(ctx.cfg, ctx.slot, plugin, scope))


def plugin_log(ctx, plugin: str, scope: str = "auto", skip_if_missing: bool = False, since_size: int = 0) -> str:
    """The text of <plugin>'s log since its last load line (`<plugin>: <version> loaded (`), so an old run's lines
    do not count. Only text after byte `since_size` is looked at (default: the whole file; ignored when the file is
    now smaller, as after a new log). "" when there is no file or no load line yet; with skip_if_missing a missing
    file skips the check (ctx.skip). `ctx` needs .cfg and .slot (a game_checks Context)."""
    path = plugin_log_path(ctx.cfg, ctx.slot, plugin, scope)
    if not path or not os.path.isfile(path):
        if skip_if_missing:
            ctx.skip(f"no plugin log yet: {path}")
        return ""
    with open(path, "rb") as f:
        raw = f.read()
    text = (raw[since_size:] if 0 < since_size <= len(raw) else raw).decode("utf-8", errors="replace")
    starts = [m.start() for m in re.finditer(rf"{re.escape(plugin)}: \S+ loaded \(", text)]
    return text[starts[-1]:] if starts else ""


# ---------------------------------------------------------------- with a game

NEEDS_POSITION = ("moved needs the plugin to write the player position "
                  "(harness.idx_player_x/idx_player_y, docs/testing.md)")


def read_position(game) -> tuple[int, int, int | None]:
    """(x, y, level) of the player from the harness block; level is None when idx_player_level is not offered.
    Raises GameUnavailable when the plugin offers no position, or has not written one yet ((0, 0))."""
    hn = game.need_harness()
    ix, iy = hn.h.get("idx_player_x", -1), hn.h.get("idx_player_y", -1)
    if ix is None or iy is None or ix < 0 or iy < 0:
        raise game_ctl.GameUnavailable(NEEDS_POSITION)
    x, y = hn.block.get(ix), hn.block.get(iy)
    if x == 0 and y == 0:
        raise game_ctl.GameUnavailable("the plugin has not written a player position yet (0, 0): is a game running?")
    il = hn.h.get("idx_player_level", -1)
    return x, y, (hn.block.get(il) if il is not None and il >= 0 else None)


def shoot(game) -> Image:
    """A screenshot; the game window is found again by PID first (nothing needs focus)."""
    game.need_window()
    return game.screenshot()


def pair(game, name: str, warp: str, out_dir: str, light: int = LIGHT, settle: float = SETTLE,
         toggle_key: str = "g", toggle_wait: float = TOGGLE, sleep=time.sleep, log=print) -> tuple[str, bool]:
    """Light up, warp, shoot HD (twice, to measure noise), toggle, shoot legacy, toggle back; save HD|legacy to
    <out_dir>/<name>.png. The toggle is always pressed back, even when the legacy shot fails. Returns (path,
    identical). The game must be in a game (Hell, the level 99 test character) and in HD."""
    level, x, y = parse_warp(warp)
    if light:
        if not game.console(f"cheat stat {LIGHT_STAT},{light}"):
            log(f"warning: the console did not take the light radius line (cheat stat {LIGHT_STAT},{light})")
    line = goto_line(level, x, y)
    if not game.console(line):
        raise GameCtlError(f"the console did not take {line!r}")
    sleep(settle)
    hd = shoot(game)
    sleep(NOISE_WAIT)
    noise = distance(hd, shoot(game))
    game.key(toggle_key)
    try:
        sleep(toggle_wait)
        legacy = shoot(game)
    finally:
        game.key(toggle_key)
        sleep(toggle_wait)
    d = distance(hd, legacy)
    same = identical(hd, legacy, noise)
    log(f"{name}: HD-to-legacy distance {d:.2f}, HD noise {noise:.2f}")
    if same:
        log(f"warning {name}: HD and legacy shots are identical (did `{toggle_key}` toggle? is the game in HD?)")
    path = side_by_side(hd, legacy).save(os.path.join(out_dir, name if name.lower().endswith(".png") else name + ".png"))
    return path, same


def moved(game, action, wait: float = 1.5, sleep=time.sleep) -> tuple[bool, str]:
    """Run `action()` (a click or key on `game`) and report whether the character moved.
    Returns (moved, one-line description). Raises GameUnavailable when the position cannot be read or the level
    changed during the action."""
    x0, y0, l0 = read_position(game)
    action()
    sleep(wait)
    x1, y1, l1 = read_position(game)
    if l0 != l1:
        raise game_ctl.GameUnavailable(f"the level changed during the action ({l0} -> {l1}): cannot compare positions")
    m, dx, dy, d = position_diff((x0, y0), (x1, y1))
    return m, f"{describe_move(m, dx, dy, d)}; position ({x0}, {y0}) -> ({x1}, {y1})"


# ---------------------------------------------------------------- command line (called from game_ctl)

def run_pair(g, args: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="game_ctl.py pair")
    ap.add_argument("name")
    ap.add_argument("warp", help="LEVEL,X,Y (world subtiles) or LEVEL")
    ap.add_argument("--light", type=int, default=LIGHT, help=f"item_lightradius to set (default {LIGHT}; 0 = leave)")
    ap.add_argument("--settle", type=float, default=SETTLE)
    ap.add_argument("--key", default="g")
    a = ap.parse_args(args)
    path, same = pair(g, a.name, a.warp, game_ctl.run_screens_dir(g.cfg), a.light, a.settle, a.key)
    print(path)
    return 1 if same else 0


def run_moved(g, args: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="game_ctl.py moved")
    ap.add_argument("--wait", type=float, default=1.5, help="seconds between the action and the second reading")
    sub = ap.add_subparsers(dest="how", required=True)
    c = sub.add_parser("click")
    k = sub.add_parser("key")
    for q in (c, k):  # --wait also after the action
        q.add_argument("--wait", type=float, default=argparse.SUPPRESS)
    c.add_argument("fx", type=float)
    c.add_argument("fy", type=float)
    c.add_argument("button", nargs="?", default="left", choices=("left", "right"))
    k.add_argument("keys", nargs="+")
    a = ap.parse_args(args)

    def act():
        if a.how == "click":
            g.click(a.fx, a.fy, a.button)
        else:
            for key in a.keys:
                g.key(key)

    try:
        m, text = moved(g, act, a.wait)
    except game_ctl.GameUnavailable as e:
        print(f"cannot tell: {e}", file=sys.stderr)
        return 2
    print(text)
    return 0 if m else 1
