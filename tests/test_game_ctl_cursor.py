"""game_ctl cursor_report: the grid highlight is the shot's only sign of a held item."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "testing"))

import game_ctl  # noqa: E402
from game_ctl import Image  # noqa: E402


def flat(rgb):
    return Image(100, 100, bytes(rgb) * 10000)


class CursorReport(unittest.TestCase):
    def test_grey_has_no_highlight(self):
        self.assertIn("no green", game_ctl.cursor_report(flat((60, 60, 60))))

    def test_green_is_a_highlight(self):
        self.assertIn("green cell", game_ctl.cursor_report(flat((10, 90, 10))))

    def test_red_is_not_tested(self):
        self.assertIn("no green", game_ctl.cursor_report(flat((100, 10, 10))))

    def test_gold_item_art_is_not_a_highlight(self):
        self.assertIn("no green", game_ctl.cursor_report(flat((200, 160, 60))))

class EmptyBlock(unittest.TestCase):
    def test_finds_the_free_block_and_skips_items(self):
        w = h = 1000
        px = bytearray(bytes((200, 160, 60)) * (w * h))  # everything is "item art"
        l, t, r, b = Image(w, h, bytes(3 * w * h)).box(*game_ctl.GRID_FULL)
        cw, ch = (r - l) // 10, (b - t) // 8
        for y in range(t + 2 * ch, t + 6 * ch):  # rows 2-5, cols 4-5 are free
            for x in range(l + 4 * cw, l + 6 * cw):
                px[(y * w + x) * 3:(y * w + x) * 3 + 3] = bytes((5, 5, 5))
        fx, fy = game_ctl.empty_block(Image(w, h, bytes(px)))
        self.assertAlmostEqual(fx * w, l + 5 * cw, delta=5)
        self.assertAlmostEqual(fy * h, t + 4 * ch, delta=5)

    def test_none_when_full(self):
        self.assertIsNone(game_ctl.empty_block(flat((200, 160, 60))))


if __name__ == "__main__":
    unittest.main()
