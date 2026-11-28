import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from modkit import knowledge, lane
from modkit.__main__ import main
from tools import context_budget


class KnowledgeTests(unittest.TestCase):
    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["knowledge", *args])
        return code, out.getvalue(), err.getvalue()

    def test_get_returns_verbatim_source_and_a_continuation(self):
        args = ("get", "d2r-93847-addresses", "--section", "Header coverage", "--max-bytes", "4200")
        code, output, error = self.cli(*args)
        self.assertEqual(code, 0, error)
        self.assertLessEqual(len(output.encode()), 4200)
        hit, = json.loads(output)["results"]
        source = knowledge.ROOT / hit["source"]
        lines = source.read_text(encoding="utf-8").splitlines()
        self.assertEqual(hit["text"], "\n".join(lines[hit["start_line"] - 1:hit["end_line"]]))
        self.assertEqual(hit["source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertIn("Build 93847 only", hit["provenance"])
        self.assertEqual(hit["next_line"], hit["end_line"] + 1)
        code, output, error = self.cli(*args, "--start-line", str(hit["next_line"]))
        self.assertEqual(code, 0, error)
        self.assertEqual(json.loads(output)["results"][0]["start_line"], hit["next_line"])

    def test_search_and_exact_symbol_preserve_evidence(self):
        code, output, error = self.cli("search", "renderer pool", "--limit", "2")
        self.assertEqual(code, 0, error)
        self.assertEqual(output, self.cli("search", "renderer pool", "--limit", "2")[1])
        hits = json.loads(output)["results"]
        self.assertTrue(any("renderer pool" in hit["text"].casefold() for hit in hits))
        code, output, error = self.cli("address", "--symbol", "ClientFindUnit")
        self.assertEqual(code, 0, error)
        hit, = json.loads(output)["results"]
        self.assertIn("0x9a5d0", hit["text"])
        self.assertTrue(hit["text"].rstrip().endswith("| R |"))
        self.assertIn("**R** read from the dumped image", hit["table_context"])
        self.assertEqual(self.cli("address", "--symbol", "NoSuchSymbol")[0], 1)
        self.assertEqual(self.cli("get", "../CLAUDE", "--section", "Rules")[0], 2)

    def test_index_ignores_fenced_headings_and_distinguishes_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text("# Guide\n\n## Same\n~~~md\n## Example\n~~~\n## Same\n", encoding="utf-8")
            self.assertEqual([s.slug for s in knowledge.sections(path)], ["guide", "same", "same-1"])


class LaneTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "mod"
        self.toolkit = Path(tmp.name) / "toolkit"
        for repo in (self.root, self.toolkit):
            repo.mkdir()
            self.git(repo, "init", "-q", "-b", "main")
            self.git(repo, "config", "user.name", "Test Fixture")
            self.git(repo, "config", "user.email", "fixture@users.noreply.github.com")
            self.git(repo, "commit", "-q", "--allow-empty", "-m", "initial")
        scanner = self.toolkit / "tools/check_public.py"
        scanner.parent.mkdir()
        scanner.write_bytes((knowledge.ROOT / "tools/check_public.py").read_bytes())
        self.git(self.toolkit, "add", ".")
        self.git(self.toolkit, "commit", "-qm", "scanner")
        (self.root / "toolkit.version").write_text(lane.git(self.toolkit, "rev-parse", "HEAD"))
        (self.root / ".d2r-project.toml").write_text('[project]\nrepo = "example/mod"\n')
        (self.root / "allowed.txt").write_text("old")
        (self.root / "outside.txt").write_text("outside")
        self.git(self.root, "add", ".")
        self.git(self.root, "commit", "-qm", "project")
        self.git(self.root, "update-ref", "refs/remotes/origin/main", "HEAD")
        self.git(self.root, "switch", "-qc", "ticket/42-example")
        self.manifest = Path(tmp.name) / "manifest.json"
        self.evidence = Path(tmp.name) / "evidence.json"
        self.pr = Path(tmp.name) / "pr.json"
        self.manifest.write_text(json.dumps({
            "issue": 42, "allowed_paths": ["allowed.txt", "changelog.d/"],
            "player_visible": True, "required_checks": ["fixture"],
        }))

    @staticmethod
    def git(root, *args):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)

    def problems(self, command):
        args = argparse.Namespace(cmd=command, issue=42, manifest=self.manifest, evidence=self.evidence,
                                  pr=self.pr, owner=None, slot=None)
        with patch.object(lane, "TOOLKIT", self.toolkit), patch.object(lane, "find_toolkit_dir",
                                                                       return_value=self.toolkit):
            return lane.inspect(self.root, args)

    def test_preflight_detects_scope_changes_even_if_unstaged_content_matches_base(self):
        self.assertEqual(self.problems("preflight"), [])
        (self.root / "outside.txt").write_text("staged")
        self.git(self.root, "add", "outside.txt")
        (self.root / "outside.txt").write_text("outside")
        (self.root / "untracked.txt").write_text("new")
        self.assertEqual(self.problems("preflight"),
                         ["outside scope: outside.txt", "outside scope: untracked.txt"])
        (self.root / "toolkit.version").write_text("0000000")
        self.assertTrue(any("pins" in issue for issue in self.problems("preflight")))

    def test_delivery_requires_current_pr_and_acceptance_results_and_fragment(self):
        (self.root / "allowed.txt").write_text("new")
        self.git(self.root, "commit", "-qam", "lane")
        self.evidence.write_text('{"head": "old", "checks": {"fixture": {"status": "skipped"}}}')
        self.pr.write_text('{"headRefOid": "old", "body": "Closes #420"}')
        problems = self.problems("verify-lane")
        for expected in ("changelog.d", "current commit", "passed acceptance evidence", "PR must be open",
                         "PR body must open"):
            self.assertTrue(any(expected in problem for problem in problems), problems)
        fragment = self.root / "changelog.d/42.md"
        fragment.parent.mkdir()
        fragment.write_text("- Updated example.\n")
        self.git(self.root, "add", ".")
        self.git(self.root, "commit", "-qm", "fragment")
        head = lane.git(self.root, "rev-parse", "HEAD")
        self.evidence.write_text(json.dumps({
            "head": head, "checks": {"fixture": {"status": "passed", "evidence": "fixture output"}},
        }))
        self.pr.write_text(json.dumps({
            "headRefOid": head, "headRefName": "ticket/42-example", "baseRefName": "main",
            "state": "OPEN", "repository": "example/mod", "body": "Closes #42\n\nScope and proof.",
        }))
        self.assertEqual(self.problems("verify-lane"), [])


class ContextDocsTests(unittest.TestCase):
    def test_skill_links_resolve(self):
        skills = sorted((knowledge.ROOT / ".claude/skills").glob("*/SKILL.md"))
        self.assertEqual(len(skills), 15)
        for path in skills:
            with self.subTest(path=path.parent.name):
                source = path.read_text(encoding="utf-8")
                self.assertIn("reference.md", source)
                for link in re.findall(r"\]\(([^ )]+)\)", source):
                    dest, _, slug = link.partition("#")
                    target = path.parent / dest
                    self.assertTrue(target.exists(), link)
                    if slug:
                        anchors = {s.slug for s in knowledge.sections(target)}
                        self.assertIn(slug, anchors, link)

    def test_duplicate_check_normalizes_bullets_and_markup(self):
        line = "Check the current branch and confirm the issue before editing any files."
        self.assertEqual(len(context_budget.duplicates({"a": "- **" + line + "**",
                                                        "b": "1. " + line.lower()}.items())), 1)
