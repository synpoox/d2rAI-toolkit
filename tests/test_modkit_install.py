"""Tests for modkit/install.py's changed-files-only install (run: python -m unittest discover tests)."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modkit import install as mi  # noqa: E402


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class SyncTests(unittest.TestCase):
    def test_writes_only_what_differs_and_removes_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "src", Path(tmp) / "dest"
            write(src / "a.txt", "same")
            write(src / "sub" / "b.txt", "new")
            dest.mkdir()
            shutil.copy2(src / "a.txt", dest / "a.txt")  # same size and time: kept
            write(dest / "sub" / "b.txt", "old")  # same size, other time: rewritten
            write(dest / "gone" / "c.txt", "stale")
            self.assertEqual(mi.sync(src, dest), 1)
            self.assertEqual((dest / "sub" / "b.txt").read_text(), "new")
            self.assertFalse((dest / "gone").exists())
            self.assertEqual(mi.sync(src, dest), 0)


class InstallTests(unittest.TestCase):
    def test_reinstall_keeps_files_outside_the_mod_and_rewrites_only_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            proj, game = tmp / "proj", tmp / "game"
            write(proj / "mod.json", json.dumps({"name": "M", "plugins": []}))
            write(proj / "out" / "data" / "global" / "excel" / "a.txt", "1")
            write(game / "D2R.exe", "")
            write(game / "data" / "base.txt", "base game")
            with mock.patch.object(mi, "game_running", lambda: False), \
                    mock.patch.object(mi, "configured_slot", lambda g: None):
                self.assertIn("(1 written", mi.install(proj, game))
                data = game / "mods" / "M" / "M.mpq" / "data"
                stamp = (data / "global" / "excel" / "a.txt").stat().st_mtime_ns
                time.sleep(0.05)
                write(proj / "out" / "data" / "b.txt", "2")
                (proj / "out" / "data" / "global" / "excel" / "a.txt").touch()  # a rebuilt file: new time, rewritten
                write(data / "stale.txt", "from an older build")
                self.assertIn("(2 written", mi.install(proj, game))
            self.assertGreater((data / "global" / "excel" / "a.txt").stat().st_mtime_ns, stamp)
            self.assertEqual((data / "b.txt").read_text(), "2")
            self.assertFalse((data / "stale.txt").exists(), "a file the build no longer has is removed")
            self.assertTrue((game / "mods" / "M" / "modinfo.json").is_file())
            self.assertEqual((game / "data" / "base.txt").read_text(), "base game")

    def test_an_unchanged_reinstall_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            proj, game = tmp / "proj", tmp / "game"
            write(proj / "mod.json", json.dumps({"name": "M", "plugins": []}))
            write(proj / "out" / "data" / "a.txt", "1")
            write(game / "D2R.exe", "")
            with mock.patch.object(mi, "game_running", lambda: False), \
                    mock.patch.object(mi, "configured_slot", lambda g: None):
                mi.install(proj, game)
                self.assertIn("(0 written", mi.install(proj, game))


if __name__ == "__main__":
    unittest.main()
