"""Tests for shared/classic_import's cached merge (merge.run), its output check and the shared extract (run: python -m
unittest discover tests). Synthetic data only."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.classic_import import cache, extract as ex, merge as mg  # noqa: E402

RUNS: list[str] = []


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def rule_a(rule, data, d2r, out):  # its rule file, upper-cased
    RUNS.append("a")
    write(out / "global" / "excel" / "a.txt", rule.read_text().upper())


def rule_b(rule, data, d2r, out):  # reads what rule_a wrote, and a D2R table
    RUNS.append("b")
    write(out / "global" / "excel" / "b.txt",
          (out / "global" / "excel" / "a.txt").read_text() + rule.read_text() + (d2r / "global" / "excel" / "e.txt").read_text())


class OneFile:  # an archive holding data\x.txt
    def __init__(self, path): pass
    def names(self): return ["data\\x.txt"]
    def read(self, name): return b"x"


def env_without_ci(cache_root: Path | None = None):
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_ACTIONS", "MODKIT_SHARED_CACHE")}
    if cache_root:
        env["MODKIT_SHARED_CACHE"] = str(cache_root)
    return mock.patch.dict(os.environ, env, clear=True)


class CheckOutputTests(unittest.TestCase):
    def test_names_missing_tables_and_a_short_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen = Path(tmp)
            self.assertIsNone(mg.check_output(gen), "no requirements: every tree passes")
            self.assertIn("lacks monstats.txt", mg.check_output(gen, ("monstats.txt",)))
            write(gen / "global" / "excel" / "monstats.txt", "")
            self.assertIsNone(mg.check_output(gen, ("monstats.txt",)))
            self.assertIn("1 tables, fewer than 2", mg.check_output(gen, ("monstats.txt",), 2))


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "wt"
        self.d2r = Path(self.tmp.name) / "d2r"
        self.cache = Path(self.tmp.name) / "cache"
        self.cache.mkdir()
        write(self.root / "baseline.json", "{}")
        write(self.root / "extracted" / "baseline.json", ex.stamp(b"{}").decode())
        (self.root / "extracted" / "data").mkdir()
        write(self.root / "merge" / "a.tsv", "x")
        write(self.root / "merge" / "b.tsv", "b")
        write(self.d2r / "global" / "excel" / "e.txt", "1")
        self.rules = {"a.tsv": rule_a, "b.tsv": rule_b}

    def run_merge(self, **kw):
        RUNS.clear()
        with env_without_ci(self.cache), redirect_stdout(io.StringIO()) as so:
            applied = mg.run(self.rules, self.root / "merge", self.root / "extracted" / "data", self.d2r,
                             self.root / "generated", self.root / "baseline.json", self.root / "extracted",
                             rule_cache=self.cache / "rules", **kw)
        return applied, sorted(RUNS), so.getvalue()

    def out(self, name: str) -> str:
        return (self.root / "generated" / "data" / "global" / "excel" / name).read_text()

    def test_a_rule_reruns_exactly_when_its_code_or_what_it_read_changed(self):
        applied, ran, _ = self.run_merge()
        self.assertEqual((applied, ran), (["a.tsv", "b.tsv"], ["a", "b"]))
        self.assertEqual((self.out("a.txt"), self.out("b.txt")), ("X", "Xb1"))
        applied, ran, so = self.run_merge()
        self.assertEqual(ran, [], "nothing changed: every rule replays")
        self.assertIn("2 of 2 rules replayed", so)
        self.assertEqual(self.out("b.txt"), "Xb1")
        write(self.root / "merge" / "b.tsv", "c")
        self.assertEqual(self.run_merge()[1], ["b"], "only the changed rule")
        write(self.root / "merge" / "a.tsv", "y")
        self.assertEqual(self.run_merge()[1], ["a", "b"], "b read the a.txt a changed")
        self.assertEqual(self.out("b.txt"), "Yc1")
        write(self.d2r / "global" / "excel" / "e.txt", "2")
        self.assertEqual(self.run_merge()[1], ["b"], "a changed D2R table reruns the rule that read it")
        self.assertEqual(self.out("b.txt"), "Yc2")
        write(self.root / "baseline.json", '{"v": 2}')
        write(self.root / "extracted" / "baseline.json", '{"v": 2}')
        self.assertEqual(self.run_merge()[1], ["a", "b"], "another baseline file: every rule reruns")

    def test_without_a_cache_every_rule_runs_and_a_stale_extract_is_refused(self):
        RUNS.clear()
        with env_without_ci(), redirect_stdout(io.StringIO()):
            args = (self.rules, self.root / "merge", self.root / "extracted" / "data", self.d2r, self.root / "generated",
                    self.root / "baseline.json", self.root / "extracted")
            for _ in range(2):
                mg.run(*args)
            self.assertEqual(RUNS, ["a", "b", "a", "b"])
            write(self.root / "baseline.json", '{"other": 1}')
            with self.assertRaises(mg.MergeError):
                mg.run(*args)

    def test_a_partial_output_is_rebuilt_once_then_fails(self):
        with self.assertRaises(mg.MergeError) as e:
            self.run_merge(required=("monstats.txt",))
        self.assertIn("not whole after a rebuild", str(e.exception))
        self.assertIn("lacks monstats.txt", str(e.exception))
        self.assertEqual(sorted(RUNS), ["a", "a", "b", "b"], "the cached run, then the rebuild")

    def test_a_run_waits_for_another_run_in_the_same_project(self):
        got = []
        with cache.lock(self.root / "merge.lock"):
            import threading
            t = threading.Thread(target=lambda: got.append(self.run_merge()[0]))
            t.start()
            t.join(0.5)
            self.assertTrue(t.is_alive(), "held: the second run waits")
        t.join(30)
        self.assertEqual(got, [["a.tsv", "b.tsv"]])

    def test_base_key_follows_stamps_d2r_and_cache_format(self):
        stamp = [self.root / "baseline.json"]
        before = mg.base_key(stamp, mg.KIT, self.d2r)
        self.assertEqual(mg.base_key(stamp, mg.KIT, self.d2r), before)
        self.assertNotEqual(mg.base_key(stamp, mg.KIT, self.d2r / "other"), before)
        with mock.patch.object(cache, "CACHE_FORMAT", cache.CACHE_FORMAT + 1):
            self.assertNotEqual(mg.base_key(stamp, mg.KIT, self.d2r), before)
        write(self.root / "baseline.json", "changed")
        self.assertNotEqual(mg.base_key(stamp, mg.KIT, self.d2r), before)

    def test_cache_setup_uses_the_ci_scope_only_on_ci(self):
        with env_without_ci(self.cache):
            self.assertEqual(mg.cache_setup(), (self.cache, cache.Policy()))
        with env_without_ci():
            self.assertEqual(mg.cache_setup(), (None, cache.Policy()))
        env = {"GITHUB_ACTIONS": "true", "MODKIT_SHARED_CACHE": str(self.cache), "MODKIT_CI_SCOPE": "pr-5"}
        with mock.patch.dict(os.environ, env):
            root, policy = mg.cache_setup()
        self.assertEqual(root, self.cache)
        self.assertEqual(policy.origin, "pr")

    def test_prune_cache_follows_the_cap_variable(self):
        entry = self.cache / "rules" / "k" / "old"
        write(entry / "f", "x" * 100)
        write(entry / "manifest.json", json.dumps({"bytes": 100}))
        os.utime(entry, (1, 1))
        with mock.patch.dict(os.environ, {"MODKIT_CACHE_GB": "0"}):
            self.assertEqual(mg.prune_cache(self.cache), [entry])


class ExtractSharedTests(unittest.TestCase):
    def test_out_is_a_link_to_the_extract_for_its_stamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "cache").mkdir()
            out = tmp / "wt" / "data-out"
            out.parent.mkdir()
            (tmp / "a.mpq").write_bytes(b"A")
            pinned = {"archives": {"a.mpq": ex.sha256(tmp / "a.mpq")}, "extract": {"a.mpq": ["*"]}}
            for i, base in enumerate([pinned, {**pinned, "v": 2}]):
                (tmp / "b.json").write_text(json.dumps(base))
                with mock.patch.object(ex.mpq, "Archive", OneFile), redirect_stdout(io.StringIO()):
                    self.assertEqual(ex.extract_shared(tmp, out, tmp / "b.json", tmp / "cache"), 0)
                self.assertTrue(cache.is_link(out))
                self.assertEqual((out / "data" / "x.txt").read_bytes(), b"x")
                self.assertEqual(len(list((tmp / "cache" / "extract").iterdir())), i + 1, "one extract per stamp")
            self.assertTrue((tmp / "cache" / "extract.lock").is_file())
            os.rmdir(out) if os.name == "nt" else out.unlink()

    def test_a_named_out_or_no_cache_extracts_in_place_and_a_real_folder_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "a.mpq").write_bytes(b"A")
            (tmp / "b.json").write_text(json.dumps({"archives": {"a.mpq": ex.sha256(tmp / "a.mpq")},
                                                    "extract": {"a.mpq": ["*"]}}))
            with mock.patch.object(ex.mpq, "Archive", OneFile), redirect_stdout(io.StringIO()) as so:
                (tmp / "cache").mkdir()
                for name, kw in (("own", {"cache_root": tmp / "cache", "own_folder": True}), ("none", {}),
                                 ("real", {"cache_root": tmp / "cache"})):
                    out = tmp / name
                    if name == "real":
                        write(out / "keep", "")
                    self.assertEqual(ex.extract_shared(tmp, out, tmp / "b.json", **kw), 0)
                    self.assertFalse(cache.is_link(out), name)
                    self.assertTrue((out / "data" / "x.txt").is_file(), name)
            self.assertIn("is a folder, not the shared extract", so.getvalue())
            self.assertFalse((tmp / "cache" / "extract").exists())


if __name__ == "__main__":
    unittest.main()
