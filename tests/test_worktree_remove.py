"""Runs tests/tools/worktree_remove_test.ps1 (throwaway repository, junction safety). Skipped without PowerShell."""
import shutil
import subprocess
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "tools" / "worktree_remove_test.ps1"


@unittest.skipUnless(shutil.which("powershell") and shutil.which("git"), "needs PowerShell and git")
class WorktreeRemove(unittest.TestCase):
    def test_script_suite(self):
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT)],
                           capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
