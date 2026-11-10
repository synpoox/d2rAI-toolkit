"""Helpers for game checks: a paired HD/legacy shot at a warp point, and a probe that says whether the character moved.

  python testing/game_ctl.py --slot N pair NAME LEVEL,X,Y [--light 12] [--settle 3] [--key g]
  python testing/game_ctl.py --slot N moved (click FX FY [right] | key KEY..) [--wait 1.5]

`pair` warps (`cheat goto LEVEL,X,Y`), raises the light radius (`cheat stat item_lightradius,N`, so a dark map is
readable), waits `--settle` seconds, shoots, presses the toggle key (`g`, D2RLoader's legacy graphics), shoots, presses it
back, and saves HD on the left and legacy on the right as <run>/screenshots/NAME.png. Before every shot and key the
game window is looked up again (by PID), so a window that was recreated is not lost. It warns when both shots are
identical (the toggle did nothing, or the game is not in HD) and then exits 1.

`moved` reads the player's position before and after the action and prints whether and how far the character moved
(exit 0 = moved, 1 = did not). The position comes from the harness block when the plugin offers it
(`harness.idx_player_x`, `idx_player_y`: the player's world subtile, see docs/testing.md); without those it falls back
to how much the screen changed (the camera follows the character), and says so. The pure parts (pairing, identical
shots, the position difference) are plain functions below. Everything that needs the game goes through a
`game_ctl.Game`.
"""
from __future__ import annotations

import math
import os
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
SCREEN_MIN = 1.0    # mean grey change (0..255) of the whole frame; below it the screen did not change
IDENTICAL_MAX = 0.05  # signature distance at or below this counts as the same picture


# ---------------------------------------------------------------- pure parts

def side_by_side(left: Image, right: Image) -> Image:
    """One image holding two of the same size, `left` on the left."""
    if (left.width, left.height) != (right.width, right.height):
        raise ValueError(f"the two shots differ in size ({left.width}x{left.height} and {right.width}x{right.height})")
    stride = left.width * 3
    rows = [left.rgb[y * stride:(y + 1) * stride] + right.rgb[y * stride:(y + 1) * stride] for y in range(left.height)]
    return Image(2 * left.width, left.height, b"".join(rows))


def identical(a: Image, b: Image, tol: float = IDENTICAL_MAX) -> bool:
    """True when two shots are the same picture (same size and a signature distance of at most `tol`)."""
    if (a.width, a.height) != (b.width, b.height):
        return False
    if a.rgb == b.rgb:
        return True
    return game_ctl.signature_distance(a.signature(), b.signature()) <= tol


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


def screen_change(a: Image, b: Image) -> float:
    """Mean absolute grey difference of the two frames' signatures: how much the picture changed (0 = none)."""
    return game_ctl.signature_distance(a.signature(cols=24, rows=32), b.signature(cols=24, rows=32))


def describe_move(moved: bool, dx: int, dy: int, dist: float) -> str:
    if not moved:
        return f"did not move (dx {dx}, dy {dy}, {dist:.1f} subtiles)"
    return f"moved dx {dx}, dy {dy} ({dist:.1f} subtiles, about {dist / 5:.1f} tiles)"


# ---------------------------------------------------------------- with a game

def read_position(game) -> tuple[int, int] | None:
    """The player's world subtile from the harness block, or None when the plugin does not offer it."""
    hn = game.need_harness()
    ix, iy = hn.h.get("idx_player_x", 0), hn.h.get("idx_player_y", 0)
    if not ix or not iy:
        return None
    return hn.block.get(ix), hn.block.get(iy)


def shoot(game) -> Image:
    """A screenshot with the window found again first (a recreated or minimized window is the usual failure)."""
    game.need_window()
    return game.screenshot()


def pair(game, name: str, warp: str, out_dir: str, light: int = LIGHT, settle: float = SETTLE,
         toggle_key: str = "g", toggle_wait: float = TOGGLE, sleep=time.sleep, log=print) -> tuple[str, bool]:
    """Warp, light up, shoot HD, toggle, shoot legacy, toggle back; save HD|legacy to <out_dir>/<name>.png.
    Returns (path, identical). The game must be in a game (Hell, level 90+) and in HD."""
    level, x, y = parse_warp(warp)
    if light:
        if not game.console(f"cheat stat {LIGHT_STAT},{light}"):
            log(f"warning: the console did not take the light radius line (cheat stat {LIGHT_STAT},{light})")
    line = goto_line(level, x, y)
    if not game.console(line):
        raise GameCtlError(f"the console did not take {line!r}")
    sleep(settle)
    hd = shoot(game)
    game.need_window()
    game.key(toggle_key)
    sleep(toggle_wait)
    legacy = shoot(game)
    game.need_window()
    game.key(toggle_key)
    sleep(toggle_wait)
    same = identical(hd, legacy)
    if same:
        log(f"warning {name}: HD and legacy shots are identical (did `{toggle_key}` toggle? is the game in HD?)")
    path = side_by_side(hd, legacy).save(os.path.join(out_dir, name if name.lower().endswith(".png") else name + ".png"))
    return path, same


def moved(game, action, wait: float = 1.5, sleep=time.sleep) -> tuple[bool, str]:
    """Run `action()` (a click or key on `game`) and report whether the character moved.
    Returns (moved, one-line description)."""
    pos = read_position(game)
    before_img = shoot(game) if pos is None else None
    action()
    sleep(wait)
    if pos is not None:
        after = read_position(game)
        m, dx, dy, d = position_diff(pos, after)
        return m, f"{describe_move(m, dx, dy, d)}; position {pos} -> {after}"
    change = screen_change(before_img, shoot(game))
    m = change >= SCREEN_MIN
    return m, (f"{'moved' if m else 'did not move'} (screen estimate: the plugin offers no player position; "
               f"the frame changed by {change:.2f}, limit {SCREEN_MIN})")


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
    wait = 1.5
    if "--wait" in args:
        i = args.index("--wait")
        wait = float(args[i + 1])
        args = args[:i] + args[i + 2:]
    if not args or args[0] not in ("click", "key"):
        raise GameCtlError("moved needs `click FX FY [right]` or `key KEY..`")
    if args[0] == "click":
        if len(args) < 3:
            raise GameCtlError("moved click needs FX FY")

        def act():
            g.click(float(args[1]), float(args[2]), args[3] if len(args) > 3 else "left")
    else:
        def act():
            for k in args[1:]:
                g.key(k)
    m, text = moved(g, act, wait)
    print(text)
    return 0 if m else 1
