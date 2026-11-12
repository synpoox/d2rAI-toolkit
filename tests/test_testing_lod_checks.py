"""Tests for check_helpers.plugin_log and testing/lod_checks.py (no game: a fake game and a temporary slot)."""
from __future__ import annotations

import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "testing"))
sys.path.insert(0, str(ROOT))

import check_helpers as ch  # noqa: E402
import game_checks  # noqa: E402
import lod_checks as lc  # noqa: E402
import menu_layout as ml  # noqa: E402
import testing_config as tc  # noqa: E402

from modkit.saves import checksum  # noqa: E402


def good_save(name="lodcheck", cls=4, level=1) -> bytes:
    d = bytearray(0x200)
    d[:4] = lc.SIGNATURE
    d[6:8] = lc.EXTENDED_MARK
    d[lc.CLASS_OFFSET], d[lc.LEVEL_OFFSET] = cls, level
    d[lc.NAME_OFFSET:lc.NAME_OFFSET + len(name)] = name.encode()
    struct.pack_into("<I", d, 8, len(d))
    struct.pack_into("<I", d, 0xC, checksum(bytes(d)))
    return bytes(d)


class Ctx:
    def __init__(self, cfg, slot=2):
        self.cfg, self.slot = cfg, slot
        self.skipped = None

    def skip(self, why):
        self.skipped = why
        raise game_checks.Skip(why)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name).as_posix()
        self.cfg = tc.Config({"game": {"install_dir": f"{t}/i", "slots_dir": f"{t}/s"}, "mod": {"folder": "MyMod"},
                              "saves": {"root": f"{t}/saves"}}, base_dir=self.tmp.name)
        self.ctx = Ctx(self.cfg)

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Path(path).write_text(text, encoding="utf-8")


class PluginLog(Base):
    LOG = "p: 1.0 loaded (mod MyMod, D2R 3.3, image 0x1, file x)\np: environment ok\n"

    def test_since_last_load(self):
        path = ch.plugin_log_path(self.cfg, 2, "p", "mod")
        self.write(path, "p: 0.9 loaded (old)\nold line\n" + self.LOG)
        text = ch.plugin_log(self.ctx, "p")
        self.assertTrue(text.startswith("p: 1.0 loaded"))
        self.assertNotIn("old line", text)

    def test_auto_prefers_mod_then_game(self):
        game = ch.plugin_log_path(self.cfg, 2, "p", "game")
        self.write(game, self.LOG)
        self.assertEqual(ch.plugin_log_path(self.cfg, 2, "p"), game)
        mod = ch.plugin_log_path(self.cfg, 2, "p", "mod")
        self.write(mod, self.LOG)
        self.assertEqual(ch.plugin_log_path(self.cfg, 2, "p"), mod)

    def test_missing(self):
        self.assertEqual(ch.plugin_log(self.ctx, "p"), "")
        with self.assertRaises(game_checks.Skip):
            ch.plugin_log(self.ctx, "p", skip_if_missing=True)

    def test_bad_scope(self):
        with self.assertRaises(ValueError):
            ch.plugin_log_path(self.cfg, 2, "p", "x")

    def test_plugin_name_is_literal(self):
        self.write(ch.plugin_log_path(self.cfg, 2, "a.b", "mod"), "aXb: 1 loaded (x)\n")
        self.assertEqual(ch.plugin_log(self.ctx, "a.b"), "")


class AssertLoaded(Base):
    def setUp(self):
        super().setUp()
        self.ctx.ensure_running = lambda: None

    def test_ok_and_expect(self):
        self.write(ch.plugin_log_path(self.cfg, 2, "p", "mod"), PluginLog.LOG)
        line = lc.assert_plugin_loaded(self.ctx, "p", "MyMod", expect=("environment ok",))
        self.assertTrue(line.startswith("1.0 loaded (mod MyMod,"))
        with self.assertRaises(AssertionError):
            lc.assert_plugin_loaded(self.ctx, "p", "Other")
        with self.assertRaises(AssertionError):
            lc.assert_plugin_loaded(self.ctx, "p", "MyMod", expect=("nope",))

    def test_not_loaded(self):
        with mock.patch.object(lc.game_ctl, "wait_for", side_effect=lc.game_ctl.WaitTimeout("x")):
            with self.assertRaises(AssertionError):
                lc.assert_plugin_loaded(self.ctx, "p", "MyMod")


class Saves(Base):
    def test_read_and_check(self):
        self.write(lc.save_path(self.ctx, "lodcheck"), "")
        Path(lc.save_path(self.ctx, "lodcheck")).write_bytes(good_save())
        self.assertEqual(lc.read_save(self.ctx, "lodcheck")[lc.CLASS_OFFSET], 4)

    def test_bad_saves(self):
        for data in (b"junk" * 50, good_save()[:-1], good_save()[:0xC] + b"\0\0\0\0" + good_save()[0x10:]):
            with self.assertRaises(AssertionError):
                lc.check_save(data)

    def test_delete_character(self):
        folder = self.cfg.save_dir(2)
        os.makedirs(folder)
        for n in ("lodcheck.d2s", "lodcheck.d2rl", "other.d2s"):
            Path(folder, n).write_bytes(b"x")
        lc.delete_character(self.ctx, "lodcheck")
        self.assertEqual(os.listdir(folder), ["other.d2s"])

    def test_menu_layout_is_fractions(self):
        for pos in (ml.CREATE_NEW, ml.PLAY, ml.NAME_FIELD, ml.CREATE, ml.VERSION_LIST, ml.EXPANSION, ml.SAVE_AND_EXIT,
                    *[p for _, p in ml.CLASSES.values()]):
            self.assertTrue(0 < pos[0] < 1 and 0 < pos[1] < 1, pos)

    def test_create_arguments_checked(self):
        with self.assertRaises(ValueError):
            lc.create_save_reload(self.ctx, "x1")
        with self.assertRaises(ValueError):
            lc.create_save_reload(self.ctx, "okname", class_name="sorceress")
        with self.assertRaises(ValueError):
            lc.create_save_reload(self.ctx, "okname", class_pos=(0.5, 0.5))


if __name__ == "__main__":
    unittest.main()
