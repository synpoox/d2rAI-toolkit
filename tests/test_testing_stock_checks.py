"""Tests for testing/stock_checks.py: modinfo files in a temporary slot, no game."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "testing"))

import game_checks as gc  # noqa: E402
import stock_checks as sc  # noqa: E402
import testing_config as tc  # noqa: E402


class SavePath(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name).as_posix()
        self.cfg = tc.Config({"game": {"install_dir": f"{t}/i", "slots_dir": f"{t}/s", "slot_count": 3},
                              "mod": {"folder": "MyMod"}, "runs": {"dir": f"{t}/runs"},
                              "saves": {"root": f"{t}/saves"}}, base_dir=self.tmp.name)

    def put(self, slot, savepath, which=0):
        path = Path(self.cfg.modinfo_paths(slot)[which])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"name": "MyMod", "savepath": savepath}), "utf-8")
        return path

    def test_right_slot_names(self):
        self.put(2, "MyMod-s2/")
        self.assertEqual(sc.savepath_problems(self.cfg, 2), [])
        self.put(1, "MyMod/")
        self.assertEqual(sc.savepath_problems(self.cfg, 1), [])

    def test_wrong_name(self):
        self.put(2, "MyMod/")  # the user's saves
        self.assertIn("MyMod-s2/", sc.savepath_problems(self.cfg, 2)[0])
        self.put(3, "MyMod-s3")  # no trailing slash
        self.assertEqual(len(sc.savepath_problems(self.cfg, 3)), 1)

    def test_every_modinfo_is_checked(self):
        self.put(2, "MyMod-s2/", 0)
        self.put(2, "MyMod/", 1)
        self.assertEqual(len(sc.savepath_problems(self.cfg, 2)), 1)

    def test_missing_and_unreadable(self):
        self.assertIn("no modinfo", sc.savepath_problems(self.cfg, 2)[0])
        self.put(2, "x").write_text("{not json", "utf-8")
        self.assertIn("cannot read", sc.savepath_problems(self.cfg, 2)[0])

    def test_registered_check(self):
        self.assertIn("slot-savepath", gc.REGISTRY)
        ctx = SimpleNamespace(cfg=self.cfg, slot=2)
        self.put(2, "MyMod-s2/")
        self.assertEqual(sc.slot_savepath(ctx), "savepath MyMod-s2/")
        self.put(2, "MyMod/")
        with self.assertRaises(AssertionError):
            sc.slot_savepath(ctx)


if __name__ == "__main__":
    unittest.main()
