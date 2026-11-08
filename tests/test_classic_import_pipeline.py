"""Tests for shared/classic_import's extract and merge driver (run: python -m unittest discover tests). Synthetic data."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.classic_import import extract as ex  # noqa: E402
from shared.classic_import import merge as mg  # noqa: E402


class OneFile:  # an archive holding data\x.txt and data\skip.bin
    def __init__(self, path): pass
    def names(self): return [r"data\X.txt", r"data\skip.bin"]
    def read(self, name): return b"x"


class ExtractTests(unittest.TestCase):
    def run_extract(self, tmp: Path, baseline: dict, out: Path | None = None) -> tuple[int, str]:
        (tmp / "b.json").write_text(json.dumps(baseline))
        err = io.StringIO()
        with mock.patch.object(ex.mpq, "Archive", OneFile), redirect_stdout(io.StringIO()), redirect_stderr(err):
            return ex.extract(tmp / "install", out or tmp / "out", tmp / "b.json"), err.getvalue()

    def test_refuses_an_install_that_is_not_the_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "install").mkdir()
            (tmp / "install" / "a.mpq").write_bytes(b"not the baseline")
            rc, err = self.run_extract(tmp, {"archives": {"a.mpq": "0" * 64, "b.mpq": "0" * 64}, "extract": {}})
            self.assertEqual(rc, 1)
            self.assertIn("a.mpq: SHA-256 differs from b.json", err)
            self.assertIn("b.mpq: missing", err)
            self.assertFalse((tmp / "out").exists())

    def test_refuses_a_baseline_with_no_patterns_or_an_unpinned_archive(self):
        for baseline, msg in [({"archives": {}}, 'no "extract" key'),
                              ({"archives": {}, "extract": {"a.mpq": ["*"]}}, "a.mpq, which b.json's archives")]:
            with self.subTest(msg), tempfile.TemporaryDirectory() as tmp:
                rc, err = self.run_extract(Path(tmp), baseline)
                self.assertEqual(rc, 1)
                self.assertIn(msg, err)

    def test_takes_the_patterned_files_lower_case_and_skips_a_current_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "install").mkdir()
            (tmp / "install" / "a.mpq").write_bytes(b"A")
            baseline = {"archives": {"a.mpq": ex.sha256(tmp / "install" / "a.mpq")}, "extract": {"a.mpq": ["data/*.txt"]}}
            self.assertEqual(self.run_extract(tmp, baseline)[0], 0)
            out = tmp / "out"
            self.assertEqual(sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()),
                             ["baseline.json", "data/x.txt"])
            self.assertEqual((out / "baseline.json").read_bytes(), ex.stamp((tmp / "b.json").read_bytes()))
            (out / "keep").write_bytes(b"k")
            self.assertEqual(self.run_extract(tmp, baseline)[0], 0)
            self.assertTrue((out / "keep").exists(), "the same baseline skips the extract")
            baseline["extract"]["a.mpq"].append("data/*.bin")
            self.assertEqual(self.run_extract(tmp, baseline)[0], 0)
            self.assertFalse((out / "keep").exists(), "new patterns extract again")
            self.assertTrue((out / "data" / "skip.bin").is_file())


class MergeTests(unittest.TestCase):
    def project(self, tmp: Path, stamp: bytes | None = b"B") -> Path:
        (tmp / "baseline.json").write_text("B")
        if stamp is not None:
            (tmp / "extracted").mkdir()
            (tmp / "extracted" / "baseline.json").write_bytes(stamp)
        (tmp / "merge").mkdir()
        (tmp / "merge" / "README.md").write_text("notes")
        (tmp / "d2r" / "global" / "excel").mkdir(parents=True)
        return tmp

    def merge(self, root: Path, rules: dict, errors: tuple = ()) -> list[str]:
        return mg.merge(rules, root / "merge", root / "extracted" / "data", root / "d2r", root / "generated", errors)

    def test_refuses_a_missing_or_stale_extract(self):
        for stamp, msg in [(None, "no baseline stamp"), (b"A", "another baseline")]:
            with self.subTest(msg), tempfile.TemporaryDirectory() as tmp:
                root = self.project(Path(tmp), stamp)
                with self.assertRaisesRegex(mg.MergeError, msg):
                    mg.check_extract(root / "extracted", root / "baseline.json")
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp))
            mg.check_extract(root / "extracted", root / "baseline.json")

    def test_rebuilds_generated_and_runs_rules_by_file_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp))
            stale = root / "generated" / "data" / "stale.txt"
            stale.parent.mkdir(parents=True)
            stale.write_text("old")
            (root / "merge" / "b.json").write_text("{}")
            (root / "merge" / "a.tsv").write_text("")
            seen = []
            rule = lambda r, data, d2r, out: seen.append((r.name, data.name, d2r.name, out.name))  # noqa: E731
            self.assertEqual(self.merge(root, {"a.tsv": rule, "b.json": rule}), ["a.tsv", "b.json"])
            self.assertEqual(seen, [("a.tsv", "data", "d2r", "data"), ("b.json", "data", "d2r", "data")])
            self.assertFalse(stale.exists())
            self.assertTrue((root / "generated" / "data").is_dir())

    def test_a_failed_run_leaves_no_generated(self):
        class ProjectError(Exception):
            pass

        def fails(err):
            def rule(r, data, d2r, out):
                (out / "half.txt").write_text("half")
                raise err
            return rule

        for err, msg, kind in [(None, "no rule kind: mystery.json", mg.MergeError),
                               (ValueError("bad row"), "merge/x.json: bad row", mg.MergeError),
                               (ProjectError("bad id"), "^bad id$", mg.MergeError),
                               (KeyError("bug"), "bug", KeyError)]:
            with self.subTest(msg), tempfile.TemporaryDirectory() as tmp:
                root = self.project(Path(tmp))
                (root / "merge" / ("mystery.json" if err is None else "x.json")).write_text("{}")
                rules = {} if err is None else {"x.json": fails(err)}
                with self.assertRaisesRegex(kind, msg):
                    self.merge(root, rules, (ProjectError,))
                self.assertFalse((root / "generated").exists())


if __name__ == "__main__":
    unittest.main()
