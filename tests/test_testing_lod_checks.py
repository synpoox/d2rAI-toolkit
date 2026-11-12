"""Tests for check_helpers.plugin_log and testing/lod_checks.py (no game: a fake game and a temporary slot)."""
from __future__ import annotations

import os
import struct
import sys
import tempfile
import time
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


class PluginLogConfig(Base):
    def test_config_scope_and_auto(self):
        t = Path(self.tmp.name).as_posix()
        cfg = tc.Config({"game": {"install_dir": f"{t}/i", "slots_dir": f"{t}/s"}, "mod": {"folder": "MyMod"},
                         "saves": {"root": f"{t}/saves"}, "logs": {"plugin_log": "logs/p.log"}},
                        base_dir=self.tmp.name)
        want = cfg.plugin_log(2)
        self.assertEqual(ch.plugin_log_path(cfg, 2, "p", "config"), want)
        self.assertEqual(ch.plugin_log_path(cfg, 2, "p"), want)
        self.assertNotEqual(ch.plugin_log_path(cfg, 2, "other"), want)   # named for another plugin
        self.assertEqual(ch.plugin_log_path(self.cfg, 2, "p", "config"), "")

    def test_since_size(self):
        path = ch.plugin_log_path(self.cfg, 2, "p", "mod")
        old = "p: 0.9 loaded (mod Old, x)\n"
        self.write(path, old)
        size = ch.plugin_log_size(self.ctx, "p", "mod")
        self.assertEqual(size, os.path.getsize(path))
        self.assertGreater(size, 0)
        self.assertEqual(ch.plugin_log(self.ctx, "p", "mod", since_size=size), "")
        self.write(path, old + PluginLog.LOG)
        self.assertTrue(ch.plugin_log(self.ctx, "p", "mod", since_size=size).startswith("p: 1.0 loaded"))
        self.write(path, PluginLog.LOG)   # a new, shorter log: the offset is ignored
        self.assertTrue(ch.plugin_log(self.ctx, "p", "mod", since_size=size + 999))


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


def sidecar_for(save: bytes, ok=True) -> bytes:
    d = bytearray(0x60)
    d[:4] = b"D2RL"
    struct.pack_into("<II", d, 0x34, struct.unpack_from("<I", save, 0xC)[0] + (0 if ok else 1), len(save))
    return bytes(d)


class FakeGame:
    """click() on Save and Exit writes the files the way the game does: a truncated save first, then the full one."""

    def __init__(self, path, steps):
        self.path, self.steps, self.keys = path, list(steps), []

    def key(self, k):
        self.keys.append(k)

    def click(self, x, y):
        self.clicked = (x, y)


class SaveAndExit(Base):
    def setUp(self):
        super().setUp()
        self.path = lc.save_path(self.ctx, "lodcheck")
        self.side = self.path[:-4] + ".d2rl"
        os.makedirs(os.path.dirname(self.path))
        Path(self.path).write_bytes(good_save()[:6] + bytes(2) + good_save()[8:])   # old save, not extended
        old = os.path.getmtime(self.path) - 100
        os.utime(self.path, (old, old))
        Path(self.side).write_bytes(sidecar_for(good_save(), ok=False))   # an old, non-matching sidecar
        os.utime(self.side, (old, old))
        self.ctx.shot = lambda *a, **k: None
        self.ctx.game = FakeGame(self.path, [])
        self.polls = []
        patcher = mock.patch.object(lc.time, "sleep", lambda *_: None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_with(self, steps, timeout=30):
        """steps: one callable per poll; the clock moves 1 s per poll."""
        steps = list(steps)
        clock = {"t": 0.0}

        def sleep(_):
            clock["t"] += 1.0
            if steps:
                steps.pop(0)()

        real = lc.game_ctl.wait_for
        with mock.patch.object(lc.game_ctl, "wait_for",
                               lambda fn, t, i, d: real(fn, t, i, d, sleep=sleep, clock=lambda: clock["t"])):
            self.ctx.game.click = lambda x, y: steps.pop(0)()
            lc.save_and_exit(self.ctx, "lodcheck", "t", timeout)

    def test_half_written_save_is_not_yet(self):
        full = good_save()
        w = lambda p, b: Path(p).write_bytes(b)   # noqa: E731
        self.run_with([lambda: w(self.path, full[:100]),                 # click: truncated save
                       lambda: w(self.path, full),                       # poll: full save, sidecar still old
                       lambda: w(self.side, sidecar_for(full))])         # poll: sidecar written
        self.assertEqual(Path(self.path).read_bytes(), full)

    def test_old_sidecar_is_waited_out(self):
        full = good_save()
        with self.assertRaises(game_ctl_timeout()):
            self.run_with([lambda: Path(self.path).write_bytes(full)], timeout=5)   # sidecar never updates

    def test_newer_sidecar_without_match_accepted(self):
        full = good_save()
        def both():
            Path(self.path).write_bytes(full)
            Path(self.side).write_bytes(sidecar_for(full, ok=False))
            t = time.time() + 5
            os.utime(self.side, (t, t))
        self.run_with([both])

    def test_sidecar_matches(self):
        full = good_save()
        self.assertTrue(lc.sidecar_matches(sidecar_for(full), full))
        self.assertFalse(lc.sidecar_matches(sidecar_for(full, ok=False), full))
        self.assertFalse(lc.sidecar_matches(b"D2RL", full))
        self.assertFalse(lc.sidecar_matches(b"XXXX" + sidecar_for(full)[4:], full))


def game_ctl_timeout():
    return lc.game_ctl.WaitTimeout


if __name__ == "__main__":
    unittest.main()
