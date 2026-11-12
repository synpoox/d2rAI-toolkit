"""tools/install_plugins.ps1 on a fake game folder and fake plugin DLLs in a temp dir (no game, no modkit build)."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "tools" / "install_plugins.ps1"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


@unittest.skipUnless(POWERSHELL, "no PowerShell on this machine")
class InstallPluginsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.game = self.tmp / "game"
        self.game.mkdir()
        (self.game / "D2R.exe").write_bytes(b"MZ")
        self.project = self.tmp / "proj"
        build = self.project / "plugin" / "build" / "Release"
        build.mkdir(parents=True)
        for n in ("one", "two"):
            (build / f"{n}.dll").write_bytes(n.encode())
        self.plugins = self.game / "d2rloader" / "plugins"
        self.plugins.mkdir(parents=True)
        self.backup = self.tmp / "backup"

    def run_script(self, *extra):
        return subprocess.run(
            [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), "-Game", str(self.game),
             "-Project", str(self.project), "-Plugins", "one,two", "-BackupDir", str(self.backup), *extra],
            capture_output=True, text=True)

    def test_installs_plugins_and_quarantines_strays_without_deleting(self):
        (self.plugins / "stray.dll").write_bytes(b"stray")
        (self.plugins / "keepme.txt").write_text("keep")
        r = self.run_script("-Keep", "keepme.txt")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.plugins / "one.dll").read_bytes(), b"one")
        self.assertEqual((self.plugins / "two.dll").read_bytes(), b"two")
        self.assertFalse((self.plugins / "stray.dll").exists())
        self.assertTrue((self.plugins / "keepme.txt").exists())
        moved = [p for p in self.backup.rglob("stray.dll")]
        self.assertEqual(len(moved), 1)
        self.assertEqual(moved[0].read_bytes(), b"stray")

    def test_keep_extras_leaves_strays(self):
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


if __name__ == "__main__":
    unittest.main()
