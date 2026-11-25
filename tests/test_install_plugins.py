"""tools/install_plugins.ps1 on a fake test slot and fake plugin DLLs in a temp dir (no game, no modkit build)."""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "install_plugins.ps1"
POWERSHELL = (shutil.which("powershell") or shutil.which("pwsh")) if os.name == "nt" else None  # the script is Windows-only: py -3, backslash paths
sys.path[:0] = [str(ROOT), str(ROOT / "testing")]
import game_slots as gs  # noqa: E402
import testing_config as tc  # noqa: E402


def exe_with_version(major, minor, build=0):
    """A stub with just a VS_FIXEDFILEINFO after the UTF-16 key, enough for release/publish_release.exe_version."""
    ms, ls = (major << 16) | minor, build << 16
    return (b"MZ" + "VS_VERSION_INFO".encode("utf-16-le") + b"\0\0" + bytes.fromhex("bd04effe")
            + struct.pack("<III", 0x10000, ms, ls))


@unittest.skipUnless(POWERSHELL, "install_plugins.ps1 is Windows-only (py -3 launcher, backslash paths) and needs PowerShell")
class InstallPluginsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        t = self.tmp.as_posix()
        self.cfg = tc.Config({"game": {"install_dir": f"{t}/install", "slots_dir": f"{t}/slots", "slot_count": 3},
                              "mod": {"folder": "MyMod"}, "saves": {"root": f"{t}/saves"},
                              "runs": {"dir": f"{t}/runs"}}, base_dir=str(self.tmp))
        self.config_path = self.tmp / "testing.json"
        self.config_path.write_text(json.dumps(self.cfg.data))
        self.game = Path(self.cfg.slot_dir(2))
        self.game.mkdir(parents=True)
        (self.game / "D2R.exe").write_bytes(exe_with_version(3, 3, 12345))
        gs.acquire(self.cfg, 2, "lane", pid=0)
        self.project = self.tmp / "proj"
        build = self.project / "plugin" / "build" / "Release"
        build.mkdir(parents=True)
        (self.project / "mod.json").write_text(json.dumps({"name": "MyMod"}))
        for n in ("one", "two"):
            (build / f"{n}.dll").write_bytes(n.encode())
        self.plugins = self.game / "mods" / "MyMod" / "d2rloader" / "plugins"
        self.plugins.mkdir(parents=True)
        self.global_plugins = self.game / "d2rloader" / "plugins"
        self.global_plugins.mkdir(parents=True)
        self.backup = self.tmp / "backup"

    def run_script(self, *extra, game=None, run="lane"):
        env = {**os.environ, "MODKIT_TESTING_CONFIG": str(self.config_path)}
        env.pop("MODKIT_RUN", None)
        if run:
            env["MODKIT_RUN"] = run
        return subprocess.run(
            [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), "-Game",
             str(game or self.game), "-Project", str(self.project), "-Plugins", "one,two",
             "-BackupDir", str(self.backup), *extra],
            capture_output=True, text=True, env=env)

    def test_installs_mod_scoped_and_quarantines_strays_without_deleting(self):
        (self.plugins / "stray.dll").write_bytes(b"stray")
        (self.plugins / "keepme.txt").write_text("keep")
        (self.plugins / "one-off.txt").write_text("")      # D2RLoader's per-plugin toggle
        (self.plugins / "one.log").write_text("log")       # the plugin's own data file
        (self.global_plugins / "one.dll").write_bytes(b"old")   # our DLL game-wide: would load with every mod
        (self.global_plugins / "foreign.dll").write_bytes(b"foreign")  # not ours: not this script's business
        r = self.run_script("-Keep", "keepme.txt")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.plugins / "one.dll").read_bytes(), b"one")
        self.assertEqual((self.plugins / "two.dll").read_bytes(), b"two")
        self.assertFalse((self.plugins / "stray.dll").exists())
        for kept in ("keepme.txt", "one-off.txt", "one.log"):
            self.assertTrue((self.plugins / kept).exists(), kept)
        self.assertFalse((self.global_plugins / "one.dll").exists())
        self.assertTrue((self.global_plugins / "foreign.dll").exists())
        self.assertFalse((self.game / "d2rloader" / "plugins" / "two.dll").exists())
        moved = list(self.backup.rglob("stray.dll"))
        self.assertEqual(len(moved), 1)
        self.assertEqual(moved[0].read_bytes(), b"stray")
        self.assertEqual(list(self.backup.rglob("one.dll"))[0].read_bytes(), b"old")  # moved, not deleted

    def test_stale_plugin_not_in_mod_json_is_replaced(self):
        (self.plugins / "one.dll").write_bytes(b"stale")   # left by an earlier run; mod.json does not list "one"
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.plugins / "one.dll").read_bytes(), b"one")

    def test_unusable_mod_name_is_refused_before_any_change(self):
        for bad in ("", "a/b", "a\\b", ".."):
            with self.subTest(name=bad):
                (self.project / "mod.json").write_text(json.dumps({"name": bad}))
                (self.plugins / "stray.dll").write_bytes(b"stray")
                r = self.run_script()
                self.assertNotEqual(r.returncode, 0, r.stdout)
                self.assertIn("no usable name", r.stdout + r.stderr)
                self.assertTrue((self.plugins / "stray.dll").exists())
                self.assertFalse((self.plugins / "one.dll").exists())
        (self.project / "mod.json").write_text(json.dumps({}))   # no name at all
        self.assertNotEqual(self.run_script().returncode, 0)

    def test_keep_extras_leaves_strays_in_the_mod_folder(self):
        (self.plugins / "stray.dll").write_bytes(b"stray")
        r = self.run_script("-KeepExtras")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.plugins / "stray.dll").exists())
        self.assertFalse(self.backup.exists())

    def test_missing_dll_or_game_stops_before_changing_anything(self):
        (self.project / "plugin" / "build" / "Release" / "two.dll").unlink()
        (self.plugins / "stray.dll").write_bytes(b"stray")
        r = self.run_script()
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.plugins / "one.dll").exists())
        self.assertTrue((self.plugins / "stray.dll").exists())
        (self.game / "D2R.exe").unlink()
        self.assertNotEqual(self.run_script().returncode, 0)

    def assert_untouched(self):
        self.assertFalse((self.plugins / "one.dll").exists())
        self.assertTrue((self.plugins / "stray.dll").exists())
        self.assertFalse(self.backup.exists())

    def test_slot_lock_not_held_refuses_before_any_change(self):
        (self.plugins / "stray.dll").write_bytes(b"stray")
        for run in (None, "other-lane"):
            r = self.run_script(run=run)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("not locked", r.stdout + r.stderr)
            self.assert_untouched()

    def test_not_a_test_slot_is_refused(self):
        real = Path(self.cfg.data["game"]["install_dir"])
        (real / "mods" / "MyMod" / "d2rloader" / "plugins").mkdir(parents=True)
        (real / "D2R.exe").write_bytes(exe_with_version(3, 3))
        r = self.run_script(game=real)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not a test slot", r.stdout + r.stderr)
        self.assertFalse((real / "mods" / "MyMod" / "d2rloader" / "plugins" / "one.dll").exists())

    def test_wrong_game_version_is_refused_build_number_is_ignored(self):
        (self.plugins / "stray.dll").write_bytes(b"stray")
        (self.game / "D2R.exe").write_bytes(exe_with_version(3, 2, 33))
        r = self.run_script()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("3.3", r.stdout + r.stderr)
        self.assert_untouched()
        (self.game / "D2R.exe").write_bytes(exe_with_version(3, 3, 60000))  # any 3.3 build passes
        self.assertEqual(self.run_script().returncode, 0)

    def test_no_version_resource_only_warns(self):
        (self.game / "D2R.exe").write_bytes(b"MZ")
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("no version resource", r.stdout + r.stderr)
        self.assertTrue((self.plugins / "one.dll").exists())


if __name__ == "__main__":
    unittest.main()
