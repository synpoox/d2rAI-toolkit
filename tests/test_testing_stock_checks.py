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

# Importing stock_checks registers its check; keep the shared registry as it was so other tests' tag runs are unaffected.
_before = dict(gc.REGISTRY)
import stock_checks as sc  # noqa: E402

_STOCK = gc.REGISTRY["slot-savepath"]
gc.REGISTRY.clear()
gc.REGISTRY.update(_before)
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

    def put_all(self, slot, savepath):
        for which in range(len(self.cfg.modinfo_paths(slot))):
            self.put(slot, savepath, which)

    def test_right_slot_names(self):
        self.put_all(2, "MyMod-s2/")
        self.assertEqual(sc.savepath_problems(self.cfg, 2), [])
        self.put_all(1, "MyMod/")
        self.assertEqual(sc.savepath_problems(self.cfg, 1), [])

    def test_wrong_name(self):
        self.put_all(2, "MyMod/")  # the user's saves
        self.assertIn("MyMod-s2/", sc.savepath_problems(self.cfg, 2)[0])
        self.put(3, "MyMod-s3")  # no trailing slash
        self.put(3, "MyMod-s3/", 1)
        problems = sc.savepath_problems(self.cfg, 3)
        self.assertEqual(len(problems), 1)
        self.assertIn("'MyMod-s3/'", problems[0])

    def test_case_insensitive(self):
        self.put_all(2, "mymod-S2/")
        self.assertEqual(sc.savepath_problems(self.cfg, 2), [])
        self.put(3, "mymod-s3")  # still needs its trailing slash
        self.put(3, "MyMod-s3/", 1)
        self.assertEqual(len(sc.savepath_problems(self.cfg, 3)), 1)

    def test_missing_file_in_existing_folder(self):
        self.put(2, "MyMod-s2/", 0)
        Path(self.cfg.modinfo_paths(2)[1]).parent.mkdir(parents=True, exist_ok=True)
        problems = sc.savepath_problems(self.cfg, 2)
        self.assertEqual(len(problems), 1)
        self.assertIn("missing", problems[0])

    def test_empty_modinfo_files(self):
        self.cfg.data["mod"]["modinfo_files"] = []
        msg = sc.savepath_problems(self.cfg, 2)[0]
        self.assertIn("modinfo_files is empty", msg)
        self.assertFalse(msg.rstrip().endswith("looked for"))

    def test_every_modinfo_is_checked(self):
        self.put(2, "MyMod-s2/", 0)
        self.put(2, "MyMod/", 1)
        self.assertEqual(len(sc.savepath_problems(self.cfg, 2)), 1)

    def test_missing_and_unreadable(self):
        self.assertIn("no modinfo", sc.savepath_problems(self.cfg, 2)[0])
        self.put(2, "x").write_text("{not json", "utf-8")
        self.assertIn("cannot read", sc.savepath_problems(self.cfg, 2)[0])

    def test_registered_check(self):
        self.assertEqual(_STOCK.name, "slot-savepath")
        self.assertNotIn("slot-savepath", gc.REGISTRY)
        ctx = SimpleNamespace(cfg=self.cfg, slot=2)
        self.put_all(2, "MyMod-s2/")
        self.assertEqual(sc.slot_savepath(ctx), "savepath MyMod-s2/")
        self.put_all(2, "MyMod/")
        with self.assertRaises(AssertionError):
            sc.slot_savepath(ctx)


if __name__ == "__main__":
    unittest.main()
