"""game_ctl cursor probe: a synthetic 1920x1080 inventory (dark cells 19, grid lines 60, as measured in game)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "testing"))

import game_ctl  # noqa: E402
from game_ctl import Image  # noqa: E402

W, H = 1920, 1080
L, T, R, B = Image(W, H, bytes(3 * W * H)).box(*game_ctl.GRID_FULL)
CW, CH = (R - L) / 10, (B - T) / 8


def inventory(items=(), ghost=None, open_=True):
    """items: (col,row,cols,rows) filled with item art; ghost: same shape, drawn as the green placement preview."""
    px = bytearray(bytes((30, 40, 30)) * (W * H))  # the world behind
    if open_:
        for y in range(T, B):
            for x in range(L, R):
                line = int((x - L) % CW) < 2 or int((y - T) % CH) < 2
                px[(y * W + x) * 3:(y * W + x) * 3 + 3] = bytes((60,) * 3 if line else (19,) * 3)

    def fill(c, r, cols, rows, rgb):
        for y in range(int(T + r * CH) + 3, int(T + (r + rows) * CH)):
            for x in range(int(L + c * CW) + 3, int(L + (c + cols) * CW)):
                px[(y * W + x) * 3:(y * W + x) * 3 + 3] = bytes(rgb)
    for it in items:
        fill(*it, (200, 160, 60))
    if ghost:
        fill(*ghost, (17, 48, 15))
    return Image(W, H, bytes(px))


class Probe(unittest.TestCase):
    def test_free_block_found_in_open_inventory(self):
        self.assertIsNotNone(game_ctl.empty_block(inventory(items=[(0, 0, 3, 3)])))

    def test_closed_inventory_has_no_block(self):
        self.assertIsNone(game_ctl.empty_block(inventory(open_=False)))

    def test_full_inventory_has_no_block(self):
        self.assertIsNone(game_ctl.empty_block(inventory(items=[(c, 0, 1, 8) for c in range(0, 10, 1)])))

    def test_empty_cursor_shows_no_ghost(self):
        self.assertFalse(game_ctl.probe_cursor(inventory(items=[(0, 0, 2, 4)])))

    def test_held_item_shows_green_ghost_on_the_probe_block(self):
        img = inventory(items=[(0, 0, 2, 4)])
        fx, fy = game_ctl.empty_block(img)
        c, r = int(fx * W - L) / CW - 1, int(fy * H - T) / CH - 2
        held = inventory(items=[(0, 0, 2, 4)], ghost=(int(c), int(r), 2, 4))
        self.assertTrue(game_ctl.probe_cursor(held))

    def test_shot_line_never_claims_empty(self):
        self.assertNotIn("empty", game_ctl.cursor_report(inventory()))
        self.assertIn("possibly held", game_ctl.cursor_report(inventory(ghost=(5, 3, 2, 4))))

    def test_gold_item_art_is_not_green(self):
        self.assertFalse(game_ctl.probe_cursor(inventory(items=[(2, 2, 2, 4)])))


if __name__ == "__main__":
    unittest.main()
