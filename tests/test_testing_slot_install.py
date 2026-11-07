"""Tests for testing/slot_install.py and modkit install's savepath (run: python -m unittest discover tests). No game."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "testing"))

import game_slots as gs  # noqa: E402
import release_install as ri  # noqa: E402
import slot_install as si  # noqa: E402
import testing_config as tc  # noqa: E402
from modkit import install as mi  # noqa: E402


class SlotInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.cfg = tc.Config({"game": {"install_dir": f"{t.as_posix()}/install", "slots_dir": f"{t.as_posix()}/slots",
                                       "slot_count": 3},
                              "mod": {"folder": "MyMod"}, "saves": {"root": f"{t.as_posix()}/saves"},
                              "runs": {"dir": f"{t.as_posix()}/runs"}}, base_dir=self.tmp.name)
        self.project = t / "proj"
        (self.project / "out/data/global").mkdir(parents=True)
        (self.project / "out/data/global/a.txt").write_text("a")
        (self.project / "mod.json").write_text(json.dumps({"name": "MyMod", "savepath": "MyMod/"}))
        for n in (2, 3):
            Path(self.cfg.slot_dir(n)).mkdir(parents=True)
            Path(self.cfg.slot_dir(n), "D2R.exe").write_text("")
        gs.acquire(self.cfg, 3, "lane", pid=0)
        no_game = mock.patch.object(gs, "slot_processes", return_value=[])
        no_game.start()
        self.addCleanup(no_game.stop)
        self.addCleanup(self.tmp.cleanup)

    def savepaths(self, n=3):
        mod = Path(self.cfg.mod_dir(n))
        return [json.loads(p.read_text())["savepath"] for p in (mod / "MyMod.mpq/modinfo.json", mod / "modinfo.json")]

    def test_fresh_install_sets_slot_savepath(self):
        with mock.patch.object(mi, "game_running", return_value=True):  # another slot's game runs: still fine
            si.install(self.cfg, 3, str(self.project), owner="lane")
        self.assertEqual(self.savepaths(), ["MyMod-s3/", "MyMod-s3/"])
        self.assertTrue(Path(self.cfg.save_dir(3)).is_dir())

    def test_save_folder_skips_first_run_screens_and_keeps_settings(self):
        Path(self.cfg.save_dir(3)).mkdir(parents=True)
        Path(self.cfg.save_dir(3), "Settings.json").write_text('{"Gamma": 155, "First Time": 0}')
        si.install(self.cfg, 3, str(self.project), owner="lane")
        settings = json.loads(Path(self.cfg.save_dir(3), "Settings.json").read_text())
        self.assertEqual(settings, {"Gamma": 155, "First Time": 1, "Tutorial": 1})

    def test_install_points_the_slot_loader_at_the_mod(self):
        toml = Path(self.cfg.loader_config_path(3))
        toml.parent.mkdir(parents=True)
        toml.write_text('[d2rloader]\ndefault_mod = "OtherMod"\n')
        si.install(self.cfg, 3, str(self.project), owner="lane")
        self.assertIn('default_mod = "MyMod"', toml.read_text())
        self.assertIn("always_enable_rotw_legacy_graphics_keybind = true", toml.read_text())

    @unittest.skipUnless(os.name == "nt", "junctions are Windows only")
    def test_slot_process_found_through_a_linked_slots_folder(self):
        import _winapi
        real, link = Path(self.tmp.name, "real"), Path(self.tmp.name, "link")
        (real / "Slot3").mkdir(parents=True)
        _winapi.CreateJunction(str(real), str(link))
        self.assertTrue(gs.under(str(real / "Slot3/D2R.exe"), str(link / "Slot3")))  # Windows names the real path
        self.assertFalse(gs.under(str(real / "Slot30/D2R.exe"), str(link / "Slot3")))

    def test_reinstall_keeps_slot_savepath(self):
        si.install(self.cfg, 3, str(self.project), owner="lane")
        (self.project / "out/data/global/a.txt").write_text("b")
        si.install(self.cfg, 3, str(self.project), owner="lane")
        self.assertEqual(self.savepaths(), ["MyMod-s3/", "MyMod-s3/"])
        self.assertEqual(Path(self.cfg.mod_dir(3), "MyMod.mpq/data/global/a.txt").read_text(), "b")

    def use_config(self):
        """Point MODKIT_TESTING_CONFIG at this test's slots, as the owner's environment does."""
        path = Path(self.tmp.name, "testing.json")
        path.write_text(json.dumps(self.cfg.data))
        return mock.patch.dict("os.environ", {"MODKIT_TESTING_CONFIG": str(path)})

    def test_plain_modkit_install_refuses_a_configured_slot(self):
        with self.use_config(), mock.patch.object(mi, "game_running", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "slot_install.py --slot 3"):
                mi.install(self.project, Path(self.cfg.slot_dir(3)))
            self.assertFalse(Path(self.cfg.mod_dir(3)).exists())
            si.install(self.cfg, 3, str(self.project), owner="lane")  # the slot-safe install still works
        self.assertEqual(self.savepaths(), ["MyMod-s3/", "MyMod-s3/"])

    def test_non_slot_install_keeps_project_savepath(self):
        other = Path(self.tmp.name, "my-own-game")
        other.mkdir()
        (other / "D2R.exe").write_text("")
        with self.use_config(), mock.patch.object(mi, "game_running", return_value=False):
            mi.install(self.project, other)  # a folder that is not a slot: today's behaviour
        mod = other / "mods" / "MyMod"
        self.assertEqual([json.loads(p.read_text())["savepath"] for p in (mod / "MyMod.mpq/modinfo.json", mod / "modinfo.json")],
                         ["MyMod/", "MyMod/"])
        with mock.patch.object(mi, "configured_slot", return_value=None),                 mock.patch.object(mi, "game_running", return_value=False):
            mi.install(self.project, Path(self.cfg.slot_dir(2)))  # no testing config: no slots known
        self.assertEqual(self.savepaths(2), ["MyMod/", "MyMod/"])
        with mock.patch.object(mi, "game_running", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "close the game"):
                mi.install(self.project, Path(self.cfg.slot_dir(2)))

    def test_refuses_without_the_lock(self):
        for owner in (None, "other-lane"):
            with mock.patch.dict("os.environ", {}, clear=True), self.assertRaisesRegex(ri.ReleaseError, "not locked"):
                si.install(self.cfg, 3, str(self.project), owner=owner)
        with self.assertRaisesRegex(ri.ReleaseError, "not locked"):
            si.install(self.cfg, 2, str(self.project), owner="lane")  # lane holds slot 3, not 2
        self.assertFalse(Path(self.cfg.mod_dir(3)).exists())

    def test_refuses_while_the_slots_game_runs(self):
        with mock.patch.object(gs, "slot_processes", return_value=[(1, "D2R.exe")]):
            with self.assertRaisesRegex(ri.ReleaseError, "running game"):
                si.install(self.cfg, 3, str(self.project), owner="lane")
        self.assertFalse(Path(self.cfg.mod_dir(3)).exists())

    def test_refuses_slot_one_and_another_mod(self):
        with self.assertRaisesRegex(ri.ReleaseError, "slot 1"):
            si.install(self.cfg, 1, str(self.project), owner="lane")
        (self.project / "mod.json").write_text(json.dumps({"name": "Other"}))
        with self.assertRaisesRegex(gs.SlotError, "mod.folder"):
            si.install(self.cfg, 3, str(self.project), owner="lane")


if __name__ == "__main__":
    unittest.main()
