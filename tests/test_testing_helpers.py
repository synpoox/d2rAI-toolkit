"""Tests for testing/check_helpers.py: the pure parts and the flows against a fake game."""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def test_identical_uses_noise(self):
        a, b = flat(32, 32, (10, 10, 10)), flat(32, 32, (14, 14, 14))  # distance 4
        self.assertFalse(ch.identical(a, b))
        self.assertTrue(ch.identical(a, b, noise=2.0))  # within 3 x noise
        self.assertFalse(ch.identical(a, b, noise=0.5))


class FakeHarness:
    def __init__(self, idx):
        self.h = idx
        self.block = type("B", (), {"vals": {}, "get": lambda s, i: s.vals.get(i, 0)})()


class FakeGame:
    def __init__(self, shots, harness=None, fail_shot=None):
        self.shots, self.harness, self.lines, self.keys, self.fail_shot = list(shots), harness, [], [], fail_shot
        self.n = 0

    def need_harness(self):
        return self.harness

    def need_window(self):
        return 1

    def screenshot(self):
        self.n += 1
        if self.fail_shot == self.n:
            raise GameCtlError("window lost")
        return self.shots.pop(0)

    def console(self, line):
        self.lines.append(line)
        return True

    def key(self, k):
        self.keys.append(k)


POS = {"idx_player_x": 11, "idx_player_y": 12, "idx_player_level": 13}


def pos_game(x=100, y=200, level=189, idx=POS):
    h = FakeHarness(dict(idx))
    h.block.vals = {11: x, 12: y, 13: level}
    return FakeGame([], h), h


class Flows(unittest.TestCase):
    def test_pair_saves_and_warns(self):
        hd, leg = flat(8, 8, (1, 2, 3)), flat(8, 8, (200, 100, 50))
        with tempfile.TemporaryDirectory() as d:
            g = FakeGame([hd, hd, leg])
            path, same = ch.pair(g, "x", "189,20222,10162", d, sleep=lambda s: None, log=lambda *a: None)
            self.assertFalse(same)
            self.assertTrue(Path(path).is_file())
            self.assertEqual(g.lines, ["cheat stat item_lightradius,12", "cheat goto 189,20222,10162"])
            self.assertEqual(g.keys, ["g", "g"])
            logs = []
            _, same = ch.pair(FakeGame([hd, hd, hd]), "y", "189", d, 0, sleep=lambda s: None, log=logs.append)
            self.assertTrue(same)
            self.assertIn("distance", logs[0])
            self.assertIn("identical", logs[1])

    def test_pair_presses_the_toggle_back_when_the_legacy_shot_fails(self):
        hd = flat(8, 8, (1, 2, 3))
        with tempfile.TemporaryDirectory() as d:
            g = FakeGame([hd, hd], fail_shot=3)
            with self.assertRaises(GameCtlError):
                ch.pair(g, "x", "189", d, sleep=lambda s: None, log=lambda *a: None)
            self.assertEqual(g.keys, ["g", "g"])

    def test_moved_with_position(self):
        g, h = pos_game()
        m, text = ch.moved(g, lambda: h.block.vals.update({11: 110}), 0, sleep=lambda s: None)
        self.assertTrue(m)
        self.assertIn("dx 10", text)
        self.assertFalse(ch.moved(g, lambda: None, 0, sleep=lambda s: None)[0])

    def test_moved_refuses_without_position(self):
        for idx in ({}, {"idx_player_x": -1, "idx_player_y": -1}, {"idx_player_x": 11}):
            g, _ = pos_game(idx=idx)
            with self.assertRaises(game_ctl.GameUnavailable) as e:
                ch.moved(g, lambda: None, 0, sleep=lambda s: None)
            self.assertIn("needs the plugin", str(e.exception))

    def test_moved_refuses_unwritten_position_and_level_change(self):
        g, _ = pos_game(0, 0)
        with self.assertRaises(game_ctl.GameUnavailable):
            ch.moved(g, lambda: None, 0, sleep=lambda s: None)
        g, h = pos_game()
        with self.assertRaises(game_ctl.GameUnavailable):
            ch.moved(g, lambda: h.block.vals.update({13: 5}), 0, sleep=lambda s: None)

    def test_position_index_zero_is_legal(self):
        g, h = pos_game(idx={"idx_player_x": 0, "idx_player_y": 12})
        h.block.vals[0] = 7
        self.assertEqual(ch.read_position(g), (7, 200, None))


class Cli(unittest.TestCase):
    """Through game_ctl.main: options in any position, unknown options rejected."""

    def run_main(self, argv):
        calls = []
        fake = mock.MagicMock()
        fake.cfg = None
        with mock.patch.object(game_ctl, "Game", return_value=fake),                 mock.patch.object(game_ctl.tc, "load", return_value=None),                 mock.patch.object(ch, "pair", side_effect=lambda g, *a, **k: calls.append((a, k)) or ("p", False)),                 mock.patch.object(ch, "moved", side_effect=lambda g, act, wait, **k: calls.append((wait,)) or (True, "ok")),                 mock.patch.object(game_ctl, "run_screens_dir", return_value="d"),                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = game_ctl.main(argv)
        return rc, calls, fake

    def test_pair_options_in_any_position(self):
        for argv in (["--slot", "6", "pair", "--light", "0", "x", "189,1,2"],
                     ["--slot", "6", "pair", "x", "189,1,2", "--light", "0"]):
            rc, calls, _ = self.run_main(argv)
            self.assertEqual(rc, 0)
            (a, _k), = calls
            self.assertEqual((a[0], a[1], a[3]), ("x", "189,1,2", 0))

    def test_moved_options_in_any_position(self):
        rc, calls, fake = self.run_main(["--slot", "6", "moved", "--wait", "2", "key", "w"])
        self.assertEqual((rc, calls), (0, [(2.0,)]))
        rc, calls, fake = self.run_main(["--slot", "6", "moved", "click", "0.5", "0.1", "--wait", "3"])
        self.assertEqual(calls, [(3.0,)])

    def test_unknown_option_rejected(self):
        for argv in (["--slot", "6", "shot", "a", "--typo"], ["--slot", "6", "console", "--typo"]):
            with self.assertRaises(SystemExit):
                self.run_main(argv)
        with self.assertRaises(SystemExit):
            self.run_main(["--slot", "6", "pair", "x", "189", "--typo"])

    def test_moved_without_position_exits_2(self):
        err = io.StringIO()
        fake = mock.MagicMock()
        with mock.patch.object(game_ctl, "Game", return_value=fake), mock.patch.object(game_ctl.tc, "load", return_value=None),                 mock.patch.object(ch, "moved", side_effect=game_ctl.GameUnavailable("needs position")),                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = game_ctl.main(["--slot", "6", "moved", "key", "w"])
        self.assertEqual(rc, 2)
        self.assertIn("cannot tell", err.getvalue())


if __name__ == "__main__":
    unittest.main()
