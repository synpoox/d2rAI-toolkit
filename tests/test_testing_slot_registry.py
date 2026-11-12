"""Tests for testing/slot_registry.py and the owner check in game_slots lock. No game."""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "testing"))

import game_slots as gs  # noqa: E402
import slot_registry as sr  # noqa: E402
import testing_config as tc  # noqa: E402

TABLE = '[owners]\n"2" = "toolkit"\n"3" = "mod-a"\n"4-5" = "mod-b"\n'


class Parse(unittest.TestCase):
    def test_ranges_and_singles(self):
        r = sr.parse({"owners": {"2": "t", "4-6": "b"}})
        self.assertEqual(r.owners, {2: "t", 4: "b", 5: "b", 6: "b"})
        self.assertEqual(r.slots_of("b"), [4, 5, 6])

    def test_bad_tables(self):
        for bad in ({"owners": {"x": "a"}}, {"owners": {"3-2": "a"}}, {"owners": {"1": "a"}},
                    {"owners": {"2": "a", "2-3": "b"}}, {"owners": {"2": ""}}, {"slots": {}}):
            with self.assertRaises(sr.RegistryError, msg=bad):
                sr.parse(bad)

    def test_refusal(self):
        r = sr.parse({"owners": {"2": "t"}}, "f")
        self.assertIsNone(r.refusal(2, "t"))
        self.assertIsNone(r.refusal(3, None))  # unowned
        self.assertIn("not to 'x'", r.refusal(2, "x"))
        self.assertIn("--project", r.refusal(2, None))

    def test_candidates_own_first(self):
        r = sr.parse({"owners": {"2": "t", "3": "m"}})
        self.assertEqual(r.candidates([2, 3, 4], "m"), [3, 4])
        self.assertEqual(r.candidates([2, 3, 4], None), [4])


class Files(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "slots.toml")

    def test_missing_default_is_none(self):
        with mock.patch.object(sr, "DEFAULT_FILE", self.path):  # the default path, not the environment variable
            self.assertIsNone(sr.load(env={}))

    def test_missing_env_file_is_error(self):
        with self.assertRaises(sr.RegistryError):
            sr.load(env={sr.ENV_FILE: self.path})

    def test_project_names_are_stripped(self):
        r = sr.parse({"owners": {"2": "mod-a"}})
        self.assertIsNone(r.refusal(2, " mod-a "))
        self.assertEqual(r.candidates([2, 3], "mod-a "), [2, 3])
        self.assertEqual(sr.env_project({sr.ENV_PROJECT: " mod-a "}), "mod-a")
        self.assertIsNone(sr.env_project({sr.ENV_PROJECT: "  "}))

    def test_registry_error_is_a_config_error(self):
        import testing_config as tc
        self.assertTrue(issubclass(sr.RegistryError, tc.ConfigError))

    def test_missing_explicit_is_error(self):
        with self.assertRaises(sr.RegistryError):
            sr.load(self.path)

    def test_load_and_env(self):
        Path(self.path).write_text(TABLE, encoding="utf-8")
        self.assertEqual(sr.load(env={sr.ENV_FILE: self.path}).owner_of(5), "mod-b")

    def test_broken_file_is_error(self):
        Path(self.path).write_text("[owners\n", encoding="utf-8")
        with self.assertRaises(sr.RegistryError):
            sr.load(self.path)


class Lock(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name).as_posix()
        self.cfg = tc.Config({"game": {"install_dir": f"{t}/i", "slots_dir": f"{t}/s", "slot_count": 6},
                              "runs": {"dir": f"{t}/runs"}}, base_dir=self.tmp.name)
        self.reg = sr.parse({"owners": {"2": "toolkit", "3": "mod-a", "4-5": "mod-b"}}, "table")

    def test_owner_may_lock(self):
        self.assertTrue(gs.acquire(self.cfg, 3, "lane", pid=0, registry=self.reg, project="mod-a")[0])

    def test_other_project_refused_and_nothing_locked(self):
        ok, msg = gs.acquire(self.cfg, 3, "lane", pid=0, registry=self.reg, project="mod-b")
        self.assertFalse(ok)
        self.assertIn("belongs to project 'mod-a'", msg)
        self.assertIsNone(gs.lock_info(self.cfg, 3))

    def test_no_project_refused_on_owned_slot(self):
        self.assertFalse(gs.acquire(self.cfg, 2, "lane", pid=0, registry=self.reg)[0])

    def test_unowned_slot_free_for_all(self):
        self.assertTrue(gs.acquire(self.cfg, 6, "lane", pid=0, registry=self.reg)[0])

    def test_no_registry_changes_nothing(self):
        self.assertTrue(gs.acquire(self.cfg, 3, "lane", pid=0)[0])

    def test_any_takes_own_then_unowned(self):
        ok, _, slot = gs.acquire_wait(self.cfg, "any", "l1", pid=0, registry=self.reg, project="mod-b")
        self.assertEqual((ok, slot), (True, 4))
        ok, _, slot = gs.acquire_wait(self.cfg, "any", "l2", pid=0, registry=self.reg, project="mod-b")
        self.assertEqual(slot, 5)
        ok, _, slot = gs.acquire_wait(self.cfg, "any", "l3", pid=0, registry=self.reg, project="mod-b")
        self.assertEqual(slot, 6)  # own slots are held: the unowned one, never another project's
        ok, msg, slot = gs.acquire_wait(self.cfg, "any", "l4", pid=0, registry=self.reg, project="mod-b")
        self.assertFalse(ok)

    def test_any_without_project_skips_owned(self):
        ok, _, slot = gs.acquire_wait(self.cfg, "any", "l1", pid=0, registry=self.reg)
        self.assertEqual(slot, 6)

    def test_refusal_is_not_queued(self):
        slept = []
        ok, _, _ = gs.acquire_wait(self.cfg, 3, "l", wait_s=60, sleep=slept.append, registry=self.reg, project="x")
        self.assertFalse(ok)
        self.assertEqual(slept, [])

    def test_ensure_lock_checks_too(self):
        self.assertFalse(gs.ensure_lock(self.cfg, 3, "l", registry=self.reg, project="x")[0])

    def test_cli(self):
        t = Path(self.tmp.name)
        conf, table = t / "c.json", t / "slots.toml"
        import json
        conf.write_text(json.dumps({"game": {"install_dir": f"{t.as_posix()}/i", "slots_dir": f"{t.as_posix()}/s",
                                             "slot_count": 6}, "runs": {"dir": f"{t.as_posix()}/runs"}}), "utf-8")
        table.write_text(TABLE, encoding="utf-8")

        def run(*argv):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                    mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop(sr.ENV_PROJECT, None)
                os.environ.pop("MODKIT_RUN", None)
                rc = gs.main(["--config", str(conf), "--slots-file", str(table), *argv])
            return rc, out.getvalue() + err.getvalue()

        rc, text = run("lock", "3", "lane")
        self.assertEqual(rc, 2)
        self.assertIn("mod-a", text)
        rc, text = run("lock", "3", "lane", "--project", "mod-b")
        self.assertEqual(rc, 2)
        rc, _ = run("lock", "3", "lane", "--project", "mod-a")
        self.assertEqual(rc, 0)
        rc, text = run("lock", "any", "lane2", "--project", "mod-b")
        self.assertEqual((rc, "slot 4" in text), (0, True))
        Path(table).write_text("[owners\n", encoding="utf-8")
        rc, text = run("lock", "6", "lane3")
        self.assertEqual(rc, 2)  # a broken table fails closed


if __name__ == "__main__":
    unittest.main()
