"""Tests for testing/force_ds1.py: a synthetic lvlprest.txt in a temporary slot, no game."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "testing"))

import force_ds1 as fd  # noqa: E402
import game_slots as gs  # noqa: E402
import testing_config as tc  # noqa: E402

HEAD = ["Name", "Id", "LevelId", "Files", "File1", "File2", "File3", "File4", "File5", "File6"]
ROWS = [
    ["Cave Map", "1", "10", "3", "cave/a.ds1", "cave/b.ds1", "cave/c.ds1", "0", "0", "0"],
    ["Other Map", "2", "11", "2", "other/x.ds1", "other/b.ds1", "0", "0", "0", "0"],
    ["Single", "3", "12", "1", "single/s.ds1", "0", "0", "0", "0", "0"],
]


def table_text(rows=ROWS) -> str:
    return "\r\n".join("\t".join(r) for r in [HEAD] + rows) + "\r\n"


def table(rows=ROWS):
    return fd.Table.parse("lvlprest", table_text([list(r) for r in rows]))


class Force(unittest.TestCase):
    def test_by_name_id_and_ds1_alone(self):
        t = table()
        self.assertIn("-> cave/b.ds1", fd.force(t, "Cave Map=b.ds1"))
        r = t.rows[0]
        self.assertEqual(r[3:], ["1", "cave/b.ds1", "0", "0", "0", "0", "0"])
        fd.force(t, "11=OTHER\\X.DS1")
        self.assertEqual(t.rows[1][3:5], ["1", "other/x.ds1"])
        fd.force(table(), "c.ds1")  # a unique ds1 name alone

    def test_errors(self):
        for sel, text in (("Cave Map=zz.ds1", "not a variant"), ("nothing=a.ds1", "no lvlprest row"),
                          ("b.ds1", "matches 2 rows"), ("Cave Map=", "want"), ("=", "want")):
            with self.assertRaises(fd.ForceError, msg=sel) as e:
                fd.force(table(), sel)
            self.assertIn(text, str(e.exception))

    def test_missing_column(self):
        t = fd.Table.parse("lvlprest", "Name\tLevelId\r\nx\t1\r\n")
        with self.assertRaises(fd.ForceError):
            fd.force(t, "x=a.ds1")

    def test_force_again_uses_the_original(self):
        orig, t = table(), table()
        fd.force(t, "Cave Map=a.ds1")
        self.assertIn("-> cave/c.ds1", fd.force(t, "Cave Map=c.ds1", orig))
        with self.assertRaises(fd.ForceError):  # without the original, c.ds1 is gone
            u = table()
            fd.force(u, "Cave Map=a.ds1")
            fd.force(u, "Cave Map=c.ds1")


class OnDisk(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name).as_posix()
        self.cfg = tc.Config({"game": {"install_dir": f"{t}/i", "slots_dir": f"{t}/s", "slot_count": 3},
                              "mod": {"folder": "MyMod"}, "runs": {"dir": f"{t}/runs"},
                              "saves": {"root": f"{t}/saves"}}, base_dir=self.tmp.name)
        self.path = Path(self.cfg.slot_dir(2)) / fd.rel_path("MyMod")
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(table_text().encode("latin-1"))
        gs.acquire(self.cfg, 2, "lane", pid=0)
        p = mock.patch.object(gs, "slot_processes", return_value=[])
        p.start()
        self.addCleanup(p.stop)

    def test_apply_and_reset(self):
        original = self.path.read_bytes()
        report = fd.apply(self.path, ["Cave Map=b.ds1"])
        self.assertEqual(len(report), 1)
        self.assertNotEqual(self.path.read_bytes(), original)
        self.assertTrue(self.path.with_name("lvlprest.txt" + fd.BACKUP_SUFFIX).is_file())
        fd.apply(self.path, ["Cave Map=c.ds1"])  # again, against the saved original
        self.assertIn("restored", fd.reset(self.path))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertIn("nothing to reset", fd.reset(self.path))

    def test_bad_selector_writes_nothing(self):
        original = self.path.read_bytes()
        with self.assertRaises(fd.ForceError):
            fd.apply(self.path, ["Cave Map=a.ds1", "Cave Map=zz.ds1"])
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(self.path.with_name("lvlprest.txt" + fd.BACKUP_SUFFIX).exists())

    def test_guard(self):
        self.assertEqual(fd.lvlprest_path(self.cfg, 2, owner="lane"), self.path)
        for slot, owner in ((1, "lane"), (2, "someone-else"), (3, "lane")):
            with self.assertRaises(fd.ForceError, msg=(slot, owner)):
                fd.lvlprest_path(self.cfg, slot, owner=owner)

    def test_game_running_refused(self):
        with mock.patch.object(gs, "slot_processes", return_value=[(1, "D2R.exe")]):
            with self.assertRaises(fd.ForceError):
                fd.lvlprest_path(self.cfg, 2, owner="lane")

    def test_mod_folder_from_mod_json(self):
        proj = Path(self.tmp.name) / "proj"
        proj.mkdir()
        (proj / "mod.json").write_text(json.dumps({"name": "OtherMod"}), "utf-8")
        self.assertEqual(fd.mod_folder(self.cfg, str(proj)), "OtherMod")
        self.assertEqual(fd.mod_folder(self.cfg), "MyMod")
        self.assertIn("OtherMod", str(fd.lvlprest_path(self.cfg, 2, str(proj), owner="lane")))
        with self.assertRaises(fd.ForceError):
            fd.mod_folder(self.cfg, str(proj / "nope"))


if __name__ == "__main__":
    unittest.main()
