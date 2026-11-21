"""game_ctl cursor_report: the red-cell tint is the shot's only sign of a held item."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "testing"))

import game_ctl  # noqa: E402
from game_ctl import Image  # noqa: E402


class CursorReport(unittest.TestCase):
    def test_grey_is_empty(self):
        self.assertIn("cursor: empty", game_ctl.cursor_report(Image(10, 10, bytes((60, 60, 60)) * 100)))

    def test_red_is_held(self):
        self.assertIn("ITEM HELD", game_ctl.cursor_report(Image(10, 10, bytes((160, 20, 20)) * 100)))

    def test_red_on_left_half_ignored(self):
        px = bytearray(bytes((60, 60, 60)) * 100)
        for y in range(10):
            for x in range(5):
                px[(y * 10 + x) * 3:(y * 10 + x) * 3 + 3] = bytes((160, 20, 20))
        self.assertIn("cursor: empty", game_ctl.cursor_report(Image(10, 10, bytes(px))))


if __name__ == "__main__":
    unittest.main()
