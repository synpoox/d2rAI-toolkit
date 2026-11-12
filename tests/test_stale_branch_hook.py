"""The plugin's SessionStart stale-branch hook: warns only when HEAD lacks origin/main, silent otherwise."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "stale_branch.sh"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]


def run(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)


class HooksJson(unittest.TestCase):
    def test_registers_the_script_on_session_start(self):
        data = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        cmd = data["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/hooks/stale_branch.sh", cmd)
        self.assertTrue(HOOK.is_file())


@unittest.skipUnless(shutil.which("sh") and shutil.which("git"), "needs sh and git")
class StaleBranchHook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="stale-hook-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.env = dict(os.environ, D2R_STALE_NO_FETCH="1")

    def hook(self, cwd):
        r = subprocess.run(["sh", str(HOOK)], cwd=cwd, capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def repo(self):
        origin = Path(self.tmp, "origin.git")
        clone = Path(self.tmp, "clone")
        run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], self.tmp)
        run(["git", "clone", "-q", str(origin), str(clone)], self.tmp)
        run(GIT + ["commit", "-q", "--allow-empty", "-m", "base"], clone)
        run(["git", "branch", "-M", "main"], clone)
        run(["git", "push", "-q", "-u", "origin", "main"], clone)
        return clone

    def test_silent_outside_a_repo(self):
        plain = Path(self.tmp, "plain")
        plain.mkdir()
        self.assertEqual(self.hook(plain), "")

    def test_silent_without_origin_main(self):
        solo = Path(self.tmp, "solo")
        solo.mkdir()
        run(["git", "init", "-q"], solo)
        self.assertEqual(self.hook(solo), "")

    def test_silent_when_current(self):
        clone = self.repo()
        self.assertEqual(self.hook(clone), "")
        run(GIT + ["commit", "-q", "--allow-empty", "-m", "ahead"], clone)
        self.assertEqual(self.hook(clone), "")

    def test_warns_when_origin_main_moved_on(self):
        clone = self.repo()
        run(["git", "checkout", "-q", "-b", "lane/x"], clone)
        run(GIT + ["commit", "-q", "--allow-empty", "-m", "lane work"], clone)
        run(["git", "checkout", "-q", "main"], clone)
        run(GIT + ["commit", "-q", "--allow-empty", "-m", "newer main"], clone)
        run(["git", "push", "-q", "origin", "main"], clone)
        run(["git", "checkout", "-q", "lane/x"], clone)
        out = self.hook(clone)
        self.assertIn("WARNING", out)
        self.assertIn("does not contain origin/main", out)


if __name__ == "__main__":
    unittest.main()
