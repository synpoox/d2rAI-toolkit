"""Tests for testing/contact_sheet.py and check_helpers.split_pair (synthetic images, no game)."""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "testing"))

import check_helpers as ch  # noqa: E402
import contact_sheet as cs  # noqa: E402
from game_ctl import Image  # noqa: E402


def flat(w, h, rgb):
    return Image(w, h, bytes(rgb) * (w * h))


def pair(hd_rgb, legacy_rgb, w=100, h=50):
    return ch.side_by_side(flat(w, h, hd_rgb), flat(w, h, legacy_rgb))


class Split(unittest.TestCase):
    def test_round_trip(self):
        a, b = flat(4, 3, (1, 2, 3)), flat(4, 3, (9, 8, 7))
        left, right = ch.split_pair(ch.side_by_side(a, b))
        self.assertEqual((left.rgb, right.rgb), (a.rgb, b.rgb))

    def test_odd_width_refused(self):
        with self.assertRaises(ValueError):
            ch.split_pair(flat(3, 1, (0, 0, 0)))


class Metrics(unittest.TestCase):
    def test_luma_and_black(self):
        m = cs.metrics(pair((200, 200, 200), (100, 100, 100), 200, 100))
        self.assertAlmostEqual(m["hd"][0], 200, delta=1)
        self.assertAlmostEqual(m["legacy"][0], 100, delta=1)
        self.assertAlmostEqual(m["ratio"], 2.0, delta=0.05)
        self.assertEqual((m["hd"][1], m["legacy"][1]), (0.0, 0.0))

    def test_black_share(self):
        m = cs.metrics(pair((0, 0, 0), (50, 50, 50), 200, 100))
        self.assertEqual(m["hd"][1], 1.0)
        self.assertEqual(m["legacy"][1], 0.0)
        self.assertEqual(m["hd"][0], 0.0)

    def test_playfield_cuts_hud_and_pillarbox(self):
        w, h = 200, 100
        hd, legacy = cs.playfield(pair((9, 9, 9), (9, 9, 9), w, h))
        self.assertEqual(hd.height, int(h * (1 - cs.HUD)))
        self.assertEqual(legacy.width, int(w * cs.LEGACY_W))

    def test_legacy_bars_do_not_count(self):
        # legacy: black bars at the sides, bright picture in the middle 3/4
        w, h = 200, 100
        left = flat(w, h, (100, 100, 100))
        rows = []
        bar = int(w * (1 - cs.LEGACY_W) / 2)
        for _ in range(h):
            rows.append(bytes((0, 0, 0)) * bar + bytes((100, 100, 100)) * (w - 2 * bar) + bytes((0, 0, 0)) * bar)
        m = cs.metrics(ch.side_by_side(left, Image(w, h, b"".join(rows))))
        self.assertEqual(m["legacy"][1], 0.0)

    def test_format(self):
        line = cs.format_metrics("a", cs.metrics(pair((200, 200, 200), (100, 100, 100), 200, 100)))
        self.assertTrue(line.startswith("a\tluma 200/100 = 2.00"))


class Sheet(unittest.TestCase):
    def test_layout(self):
        pairs = [(f"p{i}", pair((i * 40, 0, 0), (0, 0, 0), 40, 20)) for i in range(3)]
        img, found = cs.sheet(pairs, cols=2, width=80)
        self.assertEqual(img.width, 80)
        self.assertEqual(img.height, 2 * 10)  # an 80x20 pair at cell width 40 is 40x10; two rows of cells
        self.assertEqual([n for n, _ in found], ["p0", "p1", "p2"])

    def test_empty_and_bad(self):
        with self.assertRaises(ValueError):
            cs.sheet([])
        with self.assertRaises(ValueError):
            cs.sheet([("a", pair((1, 1, 1), (1, 1, 1)))], cols=0)

    def test_folder_round_trip_and_cli(self):
        with tempfile.TemporaryDirectory() as t:
            pair((120, 120, 120), (60, 60, 60), 40, 20).save(os.path.join(t, "b.png"))
            pair((10, 10, 10), (10, 10, 10), 40, 20).save(os.path.join(t, "a.png"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = cs.main([t, os.path.join(t, "sheet", "s.png"), "--cols", "1", "--width", "40"])
            self.assertEqual(rc, 0)
            lines = out.getvalue().splitlines()
            self.assertTrue(lines[0].startswith("a\t") and lines[1].startswith("b\t"))
            self.assertTrue(os.path.isfile(os.path.join(t, "sheet", "s.png")))

    def test_no_pairs(self):
        with tempfile.TemporaryDirectory() as t, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cs.main([t, os.path.join(t, "o.png")]), 2)


if __name__ == "__main__":
    unittest.main()
