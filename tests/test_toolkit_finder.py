"""Tests for the toolkit finder: tools/toolkit_path.py, tools/ToolkitPath.ps1 and cmake/FindD2rToolkit.cmake.

Every case runs on synthetic temp folders against all three finders (the .ps1 and .cmake ones are skipped when
Windows PowerShell or cmake is not on PATH), so the three are held to identical behaviour.
Run: python -m unittest discover tests
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import toolkit_path as tp  # noqa: E402

PWSH = shutil.which("powershell")
CMAKE = shutil.which("cmake")
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]


def make_toolkit(d: Path) -> None:
    (d / "modkit").mkdir(parents=True, exist_ok=True)
    (d / "tools").mkdir(parents=True, exist_ok=True)
    (d / "tools" / "toolkit_path.py").write_text("", encoding="utf-8")


def git_commit(d: Path) -> str:
    subprocess.run(GIT + ["init", "-q"], cwd=d, check=True)
    subprocess.run(GIT + ["commit", "-q", "--allow-empty", "-m", "x"], cwd=d, check=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=d, check=True, capture_output=True, text=True).stdout.strip()


def run_py(start, env: dict, strict: bool, cwd=None):
    args = [sys.executable, str(ROOT / "tools" / "toolkit_path.py"), "--from", str(start)] + (["--strict"] if strict else [])
    r = subprocess.run(args, capture_output=True, text=True, env=env, cwd=cwd)
    return r.returncode, r.stdout.strip(), r.stderr


def run_ps(start, env: dict, strict: bool, cwd=None):
    # cwd is set with Set-Location only: the process folder stays where it was, as in a real session.
    cmd = (f"{f'Set-Location ' + repr(str(cwd)) + '; ' if cwd else ''}"
           f". '{ROOT / 'tools' / 'ToolkitPath.ps1'}'; try {{ $p = Find-D2rToolkit -From '{start}'"
           f"{' -Strict' if strict else ''} -WarningVariable w -WarningAction SilentlyContinue; "
           f"if ($w) {{ [Console]::Error.WriteLine(($w | Out-String)) }}; $p }} "
           f"catch {{ [Console]::Error.WriteLine($_.Exception.Message); exit 1 }}")
    r = subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-Command", cmd], capture_output=True, text=True, env=env)
    lines = r.stdout.strip().splitlines()  # the function's result is the last line; a warning text may precede it
    return r.returncode, (lines[-1] if lines else ""), "\n".join(lines[:-1]) + r.stderr


def run_cmake(start: Path, env: dict, strict: bool, cwd=None):
    with tempfile.TemporaryDirectory() as t:
        (Path(t) / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.16)\nproject(t NONE)\n"
            f'list(APPEND CMAKE_MODULE_PATH "{(ROOT / "cmake").as_posix()}")\n'
            "find_package(D2rToolkit REQUIRED)\nmessage(STATUS \"RESULT=${D2R_TOOLKIT_DIR}\")\n", encoding="utf-8")
        args = [CMAKE, "-S", t, "-B", str(Path(t) / "b"), f"-DD2R_TOOLKIT_FROM={start.as_posix()}"]
        if strict:
            args.append("-DD2R_TOOLKIT_STRICT=1")
        r = subprocess.run(args, capture_output=True, text=True, env=env)
    out = ""
    for line in r.stdout.splitlines():
        if "RESULT=" in line:
            out = line.split("RESULT=", 1)[1].strip()
    return (0 if r.returncode == 0 else 1), out, " ".join((r.stderr + r.stdout).split())  # cmake wraps long lines


RUNNERS = {"python": run_py}
if PWSH:
    RUNNERS["powershell"] = run_ps
if CMAKE and shutil.which("git"):
    RUNNERS["cmake"] = run_cmake


class Layout(unittest.TestCase):
    """<root>/repos/{d2rAI-toolkit, mod}, a mod worktree, and a toolkit worktree."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.repos = self.root / "repos"
        self.toolkit = self.repos / "d2rAI-toolkit"
        make_toolkit(self.toolkit)
        self.mod = self.repos / "mod"
        self.wt = self.mod / ".claude" / "worktrees" / "feat" / "src"
        self.wt.mkdir(parents=True)
        self.tk_wt = self.toolkit / ".claude" / "worktrees" / "lane"
        make_toolkit(self.tk_wt)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("D2R_TOOLKIT")}

    def each(self, start, strict=False, env=None, cwd=None):
        """Run every finder; yield (name, rc, path, stderr). With cwd, relative paths resolve against it
        (python: process folder; PowerShell: Set-Location only; cmake resolves against its source folder, skipped)."""
        for name, fn in RUNNERS.items():
            if cwd and name == "cmake":
                continue
            rc, out, err = fn(start, self.env if env is None else env, strict, **({"cwd": cwd} if cwd else {}))
            yield name, rc, out, err

    def assertPath(self, expected: Path, start, **kw):
        for name, rc, out, err in self.each(start, **kw):
            with self.subTest(finder=name):
                self.assertEqual(rc, 0, err)
                self.assertEqual(Path(out).resolve(), expected.resolve())


class LookupOrder(Layout):
    def test_sibling_of_mod(self):
        self.assertPath(self.toolkit, self.mod)

    def test_mod_worktree_finds_sibling_at_any_level(self):
        self.assertPath(self.toolkit, self.wt)

    def test_inside_toolkit_returns_toolkit_root(self):
        self.assertPath(self.toolkit, self.toolkit / "modkit")

    def test_inside_toolkit_worktree_returns_that_worktree(self):
        self.assertPath(self.tk_wt, self.tk_wt / "modkit")

    def test_env_var_wins(self):
        other = self.root / "elsewhere"
        make_toolkit(other)
        self.assertPath(other, self.wt, env={**self.env, "D2R_TOOLKIT": str(other)})

    def test_env_var_invalid_is_error_not_fallback(self):
        env = {**self.env, "D2R_TOOLKIT": str(self.root / "nope")}
        for name, rc, out, err in self.each(self.wt, env=env):
            with self.subTest(finder=name):
                self.assertNotEqual(rc, 0)
                self.assertIn("not a toolkit folder", err)

    def test_not_found(self):
        lone = self.root / "lonely" / "mod"
        lone.mkdir(parents=True)
        for name, rc, out, err in self.each(lone):
            with self.subTest(finder=name):
                self.assertNotEqual(rc, 0)
                self.assertIn("not found", err)

    def test_folder_named_like_toolkit_but_not_one_is_skipped(self):
        fake = self.root / "other" / "d2rAI-toolkit"
        fake.mkdir(parents=True)
        (self.root / "other" / "mod").mkdir()
        for name, rc, out, err in self.each(self.root / "other" / "mod"):
            with self.subTest(finder=name):
                self.assertNotEqual(rc, 0)


class Pin(Layout):
    def setUp(self):
        super().setUp()
        self.head = git_commit(self.toolkit)

    def wrong_pin(self) -> str:
        return ("1" if self.head[0] != "1" else "2") + self.head[1:] + "\n"

    def pin(self, text: str, where: Path | None = None, encoding: str = "utf-8"):
        (where or self.mod).mkdir(parents=True, exist_ok=True)
        (where or self.mod).joinpath("toolkit.version").write_bytes(text.encode(encoding))

    def assertStrictOk(self, start=None):
        for name, rc, out, err in self.each(start or self.wt, strict=True):
            with self.subTest(finder=name):
                self.assertEqual(rc, 0, err)

    def assertStrictFails(self, start=None, **kw):
        for name, rc, out, err in self.each(start or self.wt, strict=True, **kw):
            with self.subTest(finder=name):
                self.assertNotEqual(rc, 0, out)

    def test_encodings_all_agree(self):
        # utf-8 BOM (Set-Content -Encoding utf8), utf-16 LE/BE with BOM (PowerShell 5.1 `>`), CRLF, a comment
        for enc in ("utf-8-sig", "utf-16", "utf-16-be"):
            text = "# pinned é\r\n" + self.head + "\r\n"
            self.pin(text if enc != "utf-16-be" else "﻿" + text, encoding=enc)
            with self.subTest(encoding=enc, kind="match"):
                self.assertStrictOk()
            self.pin("# c\r\n" + self.wrong_pin(), encoding=enc)
            with self.subTest(encoding=enc, kind="mismatch"):
                self.assertStrictFails()

    def test_garbage_bytes_are_a_problem_not_a_crash(self):
        (self.mod / "toolkit.version").write_bytes(b"\xff\xfe\x00\x80\xfe\xfe\x01")
        for name, rc, out, err in self.each(self.wt, strict=True):
            with self.subTest(finder=name):
                self.assertNotEqual(rc, 0)
                self.assertIn("commit SHA", err)

    def test_folder_named_toolkit_version_is_skipped(self):
        (self.mod / "toolkit.version").mkdir()
        self.pin(self.wrong_pin(), where=self.repos)  # would apply if the walk went on past the project
        (self.mod / ".git").mkdir()
        self.assertStrictOk()

    def test_walk_stops_at_project_root(self):
        self.pin(self.wrong_pin(), where=self.repos)
        self.assertStrictFails()  # no project marker: the walk reaches the file above
        (self.mod / ".git").write_text("gitdir: elsewhere", encoding="utf-8")  # a worktree has a .git file
        self.assertStrictOk()
        self.pin(self.wrong_pin())  # a pin in the project root itself still counts
        self.assertStrictFails()

    def test_pin_ignored_inside_toolkit(self):
        self.pin(self.wrong_pin(), where=self.toolkit)
        self.assertStrictOk(self.toolkit / "modkit")

    def test_flag_beats_env_zero(self):
        self.pin(self.wrong_pin())
        self.assertStrictFails(env={**self.env, "D2R_TOOLKIT_STRICT": "0"})

    def test_relative_from_uses_the_shell_location(self):
        self.pin(self.wrong_pin())
        self.assertStrictFails("src", cwd=str(self.mod / ".claude" / "worktrees" / "feat"))

    def test_relative_env_var_uses_the_shell_location(self):
        other = self.root / "elsewhere"
        make_toolkit(other)
        rel = os.path.relpath(other, self.mod)
        for name, rc, out, err in self.each(self.wt, env={**self.env, "D2R_TOOLKIT": rel}, cwd=str(self.mod)):
            with self.subTest(finder=name):
                self.assertEqual(rc, 0, err)
                self.assertEqual(Path(out).resolve(), other.resolve())

    def test_no_pin_file_no_check(self):
        for name, rc, out, err in self.each(self.wt, strict=True):
            with self.subTest(finder=name):
                self.assertEqual(rc, 0, err)

    def test_match_full_and_prefix_with_comments(self):
        for text in (self.head + "\n", "# pinned\n\n" + self.head[:9].upper() + "\n"):
            self.pin(text)
            for name, rc, out, err in self.each(self.wt, strict=True):
                with self.subTest(finder=name, pin=text[:12]):
                    self.assertEqual(rc, 0, err)
                    self.assertNotIn("pins", err)

    def test_mismatch_warns_by_default(self):
        self.pin("0" * 7 + self.head[7:20] + "\n" if not self.head.startswith("0000000") else "1234567\n")
        for name, rc, out, err in self.each(self.wt):
            with self.subTest(finder=name):
                self.assertEqual(rc, 0, err)
                self.assertEqual(Path(out).resolve(), self.toolkit.resolve())
                self.assertIn("pins", err)

    def test_mismatch_fails_with_flag(self):
        self.pin("abcdef1\n" if not self.head.startswith("abcdef1") else "1234567\n")
        for name, rc, out, err in self.each(self.wt, strict=True):
            with self.subTest(finder=name):
                self.assertNotEqual(rc, 0)
                self.assertIn("pins", err)

    def test_mismatch_fails_with_env_var(self):
        self.pin("abcdef1\n" if not self.head.startswith("abcdef1") else "1234567\n")
        env = {**self.env, "D2R_TOOLKIT_STRICT": "1"}
        for name, rc, out, err in self.each(self.wt, env=env):
            with self.subTest(finder=name):
                self.assertNotEqual(rc, 0)

    def test_malformed_pin_is_a_problem(self):
        self.pin("# only a comment\nnot-a-sha\n")
        for name, rc, out, err in self.each(self.wt, strict=True):
            with self.subTest(finder=name):
                self.assertNotEqual(rc, 0)
                self.assertIn("commit SHA", err)

    def test_nearest_pin_file_wins(self):
        self.pin("abcdef1\n" if not self.head.startswith("abcdef1") else "1234567\n")  # wrong, in the mod root
        self.pin(self.head + "\n", where=self.wt)  # right, nearer
        for name, rc, out, err in self.each(self.wt, strict=True):
            with self.subTest(finder=name):
                self.assertEqual(rc, 0, err)

    def test_unreadable_head_is_a_problem(self):
        (self.toolkit / ".git").rename(self.toolkit / ".git-off")
        self.pin(self.head + "\n")
        # A parent folder may be a git repo on some machines; only assert when HEAD really is unreadable.
        if subprocess.run(["git", "-C", str(self.toolkit), "rev-parse", "HEAD"], capture_output=True).returncode == 0:
            self.skipTest("temp folder is inside a git repo")
        for name, rc, out, err in self.each(self.wt, strict=True):
            with self.subTest(finder=name):
                self.assertNotEqual(rc, 0)
                self.assertIn("could not be read", err)


class PythonApi(Layout):
    def test_api_raises(self):
        with self.assertRaises(tp.ToolkitNotFound):
            tp.find_toolkit_dir(self.root, env={})
        self.assertEqual(tp.find_toolkit_dir(self.wt, env={}), self.toolkit)

    def test_exit_codes(self):
        lone = self.root / "x"
        lone.mkdir()
        self.assertEqual(tp.main(["--from", str(lone)]), 1)


if __name__ == "__main__":
    unittest.main()
