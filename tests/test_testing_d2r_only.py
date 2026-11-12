"""Tests for testing/d2r_only.py: pure parts and the in-game flows against a fake game (no game runs)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "testing"))

import d2r_only as d  # noqa: E402
from game_ctl import Image  # noqa: E402

MODES, DIFFICULTIES = ("expansion", "rotw"), ("normal", "nightmare", "hell")


def all_on() -> dict:
    """desecratedzones.json's shape with every switch on."""
    game = {"type": "T", "name": "x"}
    for mode in MODES:
        game[mode] = {"type": "t", "name": "n", **{x: {"type": "t", "ladder_enabled": True, "non_ladder_enabled": True,
                                                       "max_herald_tiers": 5} for x in DIFFICULTIES}}
    return {"desecrated_zones": [{"game_difficulties": game, "zones": []}]}


def switch_off(doc) -> None:
    for config in doc["desecrated_zones"]:
        for mode in MODES:
            for x in DIFFICULTIES:
                s = config["game_difficulties"][mode][x]
                s["ladder_enabled"] = s["non_ladder_enabled"] = False
                s["max_herald_tiers"] = 0


class ZoneSwitches(unittest.TestCase):
    def test_all_on_lists_every_switch(self):
        self.assertEqual(len(d.zone_switches(all_on())), len(MODES) * len(DIFFICULTIES) * 3)

    def test_all_off_lists_nothing(self):
        doc = all_on()
        switch_off(doc)
        self.assertEqual(d.zone_switches(doc), [])

    def test_one_left_on_is_found(self):
        doc = all_on()
        switch_off(doc)
        doc["desecrated_zones"][0]["game_difficulties"]["rotw"]["hell"]["max_herald_tiers"] = 1
        self.assertEqual(d.zone_switches(doc), ["0/rotw/hell: max_herald_tiers=1"])


class ColossalPortals(unittest.TestCase):
    HEAD = "description\tenabled\tversion\toutput"

    def test_enabled_portal_found(self):
        text = f"{self.HEAD}\nportal\t1\t100\tRed Portal,lvl=137,qty=1\nother\t1\t100\tRed Portal,lvl=136,qty=1\n"
        self.assertEqual(d.colossal_portals(text), ["portal"])
        self.assertEqual(d.colossal_portals(text, level=136), ["other"])

    def test_level_match_is_exact(self):
        text = f"{self.HEAD}\nportal\t1\t100\tRed Portal,lvl=137,qty=1\nb\t1\t100\tRed Portal,lvl=130\n"
        self.assertEqual(d.colossal_portals(text, level=13), [])

    def test_short_row_ignored(self):
        self.assertEqual(d.colossal_portals("description\toutput\tenabled\nportal\tRed Portal,lvl=137\n"), [])

    def test_disabled_portal_ignored(self):
        self.assertEqual(d.colossal_portals(f"{self.HEAD}\nportal\t0\t100\tRed Portal,lvl=137,qty=1\n"), [])


class Purple(unittest.TestCase):
    def test_counts_only_terror_purple(self):
        rgb = bytes([150, 90, 240] * 4 + [200, 200, 200] * 4)  # top row the level-name purple, bottom row grey
        self.assertEqual(d.terror_purple(4, 2, rgb), 2)  # every 2nd pixel of the purple row
        self.assertEqual(d.terror_purple(4, 2, rgb, (0, 1, 4, 2)), 0)

    def test_assertions(self):
        self.assertIn("max 3", d.assert_none_lit({1: 3, 2: 0}))
        with self.assertRaises(AssertionError):
            d.assert_none_lit({1: 3, 2: d.TERROR_PURPLE_MIN})
        d.assert_control_lit(d.TERROR_PURPLE_MIN)
        with self.assertRaises(AssertionError):
            d.assert_control_lit(0)


class FakeGame:
    def __init__(self, shots, refuse=()):
        self.lines, self.keys, self.shots, self.refuse = [], [], list(shots), tuple(refuse)

    def console(self, line):
        self.lines.append(line)
        return line not in self.refuse

    def key(self, k):
        self.keys.append(k)

    def screenshot(self):
        return self.shots.pop(0)


class FakeCtx:
    def __init__(self, game):
        self.game = game
        self.names = []

    def shot(self, name):
        self.names.append(name)


def solid(rgb, w=8, h=8):
    return Image(w, h, bytes(rgb) * (w * h))


class InGame(unittest.TestCase):
    def test_scan_and_control(self):
        calm, purple = solid((20, 20, 20)), solid((150, 90, 240), 40, 40)
        g = FakeGame([calm, calm, purple])
        ctx = FakeCtx(g)
        seen = d.scan_zones(ctx, [5, 6], settle=0, sleep=lambda s: None, client=None)
        self.assertEqual(seen, {5: 0, 6: 0})
        self.assertEqual(g.lines, ["debug_mode", "cheat goto 5", "cheat goto 6"])
        self.assertEqual(g.keys, ["tab"])
        d.assert_none_lit(seen)
        control = d.herald_control(ctx, 5, settle=0, sleep=lambda s: None, client=None)
        self.assertEqual(g.lines[-1], "cheat heraldspawn 5")
        d.assert_control_lit(control)

    def test_refused_goto_fails(self):
        calm = solid((20, 20, 20))
        ctx = FakeCtx(FakeGame([calm, calm], refuse=["cheat goto 6"]))
        with self.assertRaisesRegex(AssertionError, "cheat goto 6 not handled"):
            d.scan_zones(ctx, [5, 6], settle=0, sleep=lambda s: None, client=None)

    def test_refused_heraldspawn_fails(self):
        ctx = FakeCtx(FakeGame([solid((20, 20, 20))], refuse=["cheat heraldspawn 5"]))
        with self.assertRaisesRegex(AssertionError, "heraldspawn refused"):
            d.herald_control(ctx, 5, settle=0, sleep=lambda s: None, client=None)

    def test_empty_scan_fails(self):
        with self.assertRaisesRegex(AssertionError, "no levels scanned"):
            d.assert_none_lit({})

    def test_wrong_client_size_fails(self):
        with self.assertRaisesRegex(AssertionError, "calibrated at 1920x1080"):
            d.purple_in(solid((20, 20, 20)))
        self.assertEqual(d.purple_in(solid((20, 20, 20), 1920, 1080)), 0)

    def test_tag(self):
        self.assertEqual(d.LEAVES_TOWN, "leaves-town")


if __name__ == "__main__":
    unittest.main()
