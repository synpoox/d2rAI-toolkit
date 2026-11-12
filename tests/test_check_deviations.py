"""Tests for tools/check_deviations.py and templates/baseline.example.json (run: python -m unittest discover tests)."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

import check_deviations as cd  # noqa: E402
from shared.classic_import import extract  # noqa: E402

GOOD = "## A\n### Cut (2)\n\n| h |\n|---|\n| a |\n| b |\n### Not yet (1)\n| h |\n|---|\n| c |\n"


def run(text: str | None) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        path = Path(tmp) / "deviations.md"
        if text is not None:
            path.write_text(text, "utf-8")
        code = cd.main([str(path)])
    return code, out.getvalue(), err.getvalue()


class DeviationCountTests(unittest.TestCase):
    def test_parser(self):
        doc = "## A\n### Cut (2)\n\n| h |\n|---|\n| a |\n| b |\n### Not yet (1)\n| h |\n|---|\n"
        self.assertEqual(cd.heading_counts(doc), [("Cut", 2, 2), ("Not yet", 1, 0)])

    def test_headings_that_match_pass(self):
        code, out, _ = run(GOOD)
        self.assertEqual(code, 0)
        self.assertIn("OK, 2 heading(s)", out)

    def test_a_drifted_count_fails_naming_the_heading(self):
        code, out, _ = run(GOOD.replace("Cut (2)", "Cut (3)"))
        self.assertEqual(code, 1)
        self.assertIn("Cut (3) has 2 rows", out)

    def test_missing_file_or_no_counted_heading(self):
        self.assertEqual(run(None)[0], 2)
        self.assertEqual(run("## Nothing counted\n")[0], 2)


class BaselineTemplateTests(unittest.TestCase):
    def setUp(self):
        self.baseline = json.loads((ROOT / "templates" / "baseline.example.json").read_text("utf-8"))

    def test_has_the_keys_extract_reads_and_no_real_values(self):
        for key in ("install", "archives", "extract"):
            self.assertIn(key, self.baseline)
        values = list(self.baseline["archives"].values()) + list(self.baseline.get("dlls", {}).values())
        self.assertTrue(all(v.startswith("<") for v in values), "hashes are placeholders")
        self.assertTrue(self.baseline["install"].startswith("<"))

    def test_extract_check_sees_a_valid_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            problems = extract.check(Path(tmp), self.baseline)
        # an empty install: every archive is missing, and nothing else is wrong with the file's own shape
        self.assertEqual(len(problems), len(self.baseline["archives"]))
        self.assertTrue(all("missing from" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
