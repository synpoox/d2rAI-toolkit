"""Tests for testing/check_helpers.py: the pure parts and the flows against a fake game."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "testing"))

import check_helpers as ch  # noqa: E402
import game_ctl  # noqa: E402
from game_ctl import GameCtlError, Image  # noqa: E402


def flat(w, h, rgb):
    return Image(w, h, bytes(rgb) * (w * h))


class Pure(unittest.TestCase):
    def test_side_by_side(self):
        a, b = flat(2, 2, (255, 0, 0)), flat(2, 2, (0, 0, 255))
        out = ch.side_by_side(a, b)
        self.assertEqual((out.width, out.height), (4, 2))
        self.assertEqual(out.pixel(0, 0), (255, 0, 0))
        self.assertEqual(out.pixel(3, 1), (0, 0, 255))

    def test_side_by_side_size_mismatch(self):
        with self.assertRaises(ValueError):
            ch.side_by_side(flat(2, 2, (0, 0, 0)), flat(3, 2, (0, 0, 0)))

    def test_identical(self):
        a = flat(32, 32, (10, 20, 30))
        self.assertTrue(ch.identical(a, flat(32, 32, (10, 20, 30))))
        self.assertFalse(ch.identical(a, flat(32, 32, (90, 20, 30))))
        self.assertFalse(ch.identical(a, flat(16, 32, (10, 20, 30))))

    def test_parse_warp(self):
        self.assertEqual(ch.parse_warp("189,20222,10162"), (189, 20222, 10162))
        self.assertEqual(ch.parse_warp("189"), (189, None, None))
        with self.assertRaises(GameCtlError):
            ch.parse_warp("189,5")
        with self.assertRaises(GameCtlError):
            ch.parse_warp("a,b,c")
        self.assertEqual(ch.goto_line(189, 1, 2), "cheat goto 189,1,2")
        self.assertEqual(ch.goto_line(189), "cheat goto 189")

    def test_position_diff(self):
        self.assertEqual(ch.position_diff((10, 10), (13, 14)), (True, 3, 4, 5.0))
        moved, dx, dy, d = ch.position_diff((10, 10), (10, 11))
        self.assertFalse(moved)
        self.assertEqual((dx, dy), (0, 1))
        self.assertIn("did not move", ch.describe_move(False, 0, 1, 1.0))
        self.assertIn("moved dx 3", ch.describe_move(True, 3, 4, 5.0))

    def test_screen_change(self):
        a = flat(32, 32, (10, 10, 10))
        self.assertEqual(ch.screen_change(a, a), 0)
        self.assertGreater(ch.screen_change(a, flat(32, 32, (100, 100, 100))), ch.SCREEN_MIN)


class FakeHarness:
    def __init__(self, idx):
        self.h = idx
        self.block = type("B", (), {"vals": {}, "get": lambda s, i: s.vals.get(i, 0)})()


class FakeGame:
    def __init__(self, shots, harness=None):
        self.shots, self.harness, self.lines, self.keys = list(shots), harness, [], []

    def need_harness(self):
        return self.harness

    def need_window(self):
        return 1

    def screenshot(self):
        return self.shots.pop(0)

    def console(self, line):
        self.lines.append(line)
        return True

    def key(self, k):
        self.keys.append(k)


class Flows(unittest.TestCase):
    def test_pair_saves_and_warns(self):
        hd, leg = flat(8, 8, (1, 2, 3)), flat(8, 8, (200, 100, 50))
        with tempfile.TemporaryDirectory() as d:
            g = FakeGame([hd, leg])
            path, same = ch.pair(g, "x", "189,20222,10162", d, sleep=lambda s: None, log=lambda *a: None)
            self.assertFalse(same)
            self.assertTrue(Path(path).is_file())
            self.assertEqual(g.lines, ["cheat stat item_lightradius,12", "cheat goto 189,20222,10162"])
            self.assertEqual(g.keys, ["g", "g"])
            logs = []
            _, same = ch.pair(FakeGame([hd, hd]), "y", "189", d, 0, sleep=lambda s: None, log=logs.append)
            self.assertTrue(same)
            self.assertIn("identical", logs[0])

    def test_moved_with_position(self):
        h = FakeHarness({"idx_player_x": 11, "idx_player_y": 12})
        h.block.vals = {11: 100, 12: 200}
        g = FakeGame([], h)
        m, text = ch.moved(g, lambda: h.block.vals.update({11: 110}), 0, sleep=lambda s: None)
        self.assertTrue(m)
        self.assertIn("dx 10", text)
        m, text = ch.moved(g, lambda: None, 0, sleep=lambda s: None)
        self.assertFalse(m)

    def test_moved_screen_fallback(self):
        a, b = flat(32, 32, (10, 10, 10)), flat(32, 32, (200, 200, 200))
        g = FakeGame([a, b], FakeHarness({}))
        m, text = ch.moved(g, lambda: None, 0, sleep=lambda s: None)
        self.assertTrue(m)
        self.assertIn("screen estimate", text)
        g = FakeGame([a, a], FakeHarness({}))
        self.assertFalse(ch.moved(g, lambda: None, 0, sleep=lambda s: None)[0])


if __name__ == "__main__":
    unittest.main()
