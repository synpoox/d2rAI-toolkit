"""Tests for shared/classic_import/cache.py: the machine-wide rule cache (keys, locks, replay, scopes, merge slots).
Synthetic files only (run: python -m unittest discover tests)."""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.classic_import import cache as rule_cache  # noqa: E402


def cache_env(cache: Path):
    """os.environ with the cache root at cache, and without GITHUB_ACTIONS, which turns the cache off (the unit job)."""
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"}
    return mock.patch.dict(os.environ, {**env, "MODKIT_SHARED_CACHE": str(cache)}, clear=True)


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


class LockTests(unittest.TestCase):
    def test_a_second_holder_waits_for_the_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, got = Path(tmp) / "x.lock", threading.Event()

            def second():
                with redirect_stdout(io.StringIO()), rule_cache.lock(path, poll=0.05):
                    got.set()

            with rule_cache.lock(path):
                t = threading.Thread(target=second)
                t.start()
                self.assertFalse(got.wait(0.5))  # held: the second run waits
            self.assertTrue(got.wait(5))  # released: it goes on
            t.join()
            with rule_cache.lock(path):  # free again once both are done
                pass


class DeadHolderTests(unittest.TestCase):
    def test_a_killed_holder_frees_the_lock_and_is_named_while_it_runs(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.lock"
            code = ("import sys, time, pathlib; sys.path.insert(0, sys.argv[1]); from shared.classic_import import cache as rule_cache\n"
                    "with rule_cache.lock(pathlib.Path(sys.argv[2])):\n print('held', flush=True); time.sleep(60)")
            p = subprocess.Popen([sys.executable, "-c", code, str(ROOT), str(path)],
                                 stdout=subprocess.PIPE, text=True)
            try:
                self.assertEqual(p.stdout.readline().strip(), "held")
                self.assertRegex(rule_cache.holder(path), rf"^pid {p.pid} \(running, holding since \d\d:\d\d:\d\d\)$")
            finally:
                p.kill()
                p.wait()
            self.assertRegex(rule_cache.holder(path), rf"^pid {p.pid} \(gone, ")
            start = time.time()
            with rule_cache.lock(path, poll=0.05):  # the kernel dropped the dead holder's lock: no wait
                pass
            self.assertLess(time.time() - start, 5)
            self.assertRegex(rule_cache.holder(path), rf"^pid {os.getpid()} \(running", "the last holder is recorded")


class KeyTests(unittest.TestCase):
    def test_key_follows_content_paths_and_extra_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            write(tmp / "merge" / "a.tsv", "1")
            write(tmp / "tools" / "t.py", "x")
            write(tmp / "stamp", "s")
            paths = [tmp / "merge", tmp / "tools", tmp / "stamp", tmp / "missing"]
            k = rule_cache.key(paths, "d2r")
            self.assertEqual(rule_cache.key(paths, "d2r"), k)
            write(tmp / "tools" / "__pycache__" / "t.pyc", "junk")
            self.assertEqual(rule_cache.key(paths, "d2r"), k, "__pycache__ is not an input")
            self.assertNotEqual(rule_cache.key(paths, "other d2r"), k)
            write(tmp / "merge" / "a.tsv", "2")
            self.assertNotEqual(rule_cache.key(paths, "d2r"), k)
            write(tmp / "merge" / "a.tsv", "1")
            (tmp / "merge" / "a.tsv").rename(tmp / "merge" / "b.tsv")
            self.assertNotEqual(rule_cache.key(paths, "d2r"), k, "a renamed file changes the key")
            (tmp / "merge" / "b.tsv").rename(tmp / "merge" / "a.tsv")
            write(tmp / "missing", "")
            self.assertNotEqual(rule_cache.key(paths, "d2r"), k, "a new file changes the key")


RUNS: list[str] = []


def rule_b(rule, classic, d2r, out):  # reads a.txt; its rule names a file to add
    RUNS.append("b")
    write(out / "b.txt", (out / "a.txt").read_text() + rule.read_text())
    if rule.read_text() == "zz":
        write(out / "zz.txt", "")
    (out / "old.txt").unlink(missing_ok=True)


class RuleCacheTests(unittest.TestCase):
    def test_a_removed_file_is_removed_again_on_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cache, root = tmp / "cache", tmp / "wt"
            write(root / "merge" / "b.tsv", "b")
            out = root / "generated" / "data"
            RUNS.clear()
            for _ in range(2):
                write(out / "a.txt", "A")
                write(out / "old.txt", "stale")
                with redirect_stdout(io.StringIO()):
                    rule_cache.rule(cache, "k", {"p": root}, lambda: rule_b(root / "merge" / "b.tsv", None, None, out))
                self.assertFalse((out / "old.txt").exists())
                self.assertEqual((out / "b.txt").read_text(), "Ab")
            self.assertEqual(RUNS, ["b"], "the second is a replay")

    def test_a_run_that_writes_outside_generated_is_not_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cache, root = tmp / "cache", tmp / "wt"
            out = root / "generated" / "data"
            out.mkdir(parents=True)
            runs = []

            def art():  # as a tool does for a frame with no art yet: a PNG into merge/art
                runs.append(1)
                write(root / "merge" / "art" / f"x{len(runs)}.png", "png")
                write(out / "a.txt", "A")

            for _ in range(2):
                with redirect_stdout(io.StringIO()) as so:
                    self.assertFalse(rule_cache.rule(cache, "k", {"p": root}, art))
                self.assertIn("not cached", so.getvalue())
            self.assertEqual(len(runs), 2, "never replayed")
            self.assertFalse(list(cache.rglob("manifest.json")))

    def test_sources_follow_imports_beside_the_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            write(tmp / "m_one.py", "import os\nfrom m_two import f\ndef g(): pass\ndef main():\n    import m_three\n")
            write(tmp / "m_two.py", "import m_one\ndef f(): pass\n")
            write(tmp / "m_three.py", "")
            sys.path.insert(0, str(tmp))
            try:
                import m_one
                self.assertEqual(rule_cache.sources(m_one.g), [tmp / "m_one.py", tmp / "m_two.py"])
            finally:
                sys.path.remove(str(tmp))
                for m in ("m_one", "m_two"):
                    sys.modules.pop(m, None)

    def test_prune_drops_least_recently_used_until_under_the_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            for i, n in enumerate(["rules/k/old", "rules/k/new", "rules/j/fresh", "rules-pr/pr-7/k/mine"]):
                write(cache / n / "files" / "f", "x" * 100)
                write(cache / n / "manifest.json", json.dumps({"bytes": 100}))
                if n != "rules/j/fresh":
                    t = time.time() - 3600 * (4 - i)
                    os.utime(cache / n, (t, t))
            gone = [p.relative_to(cache).as_posix() for p in rule_cache.prune(cache, 250)]
            self.assertEqual(gone, ["rules/k/old", "rules/k/new"], "oldest first, until the rest fit")
            self.assertTrue((cache / "rules/j/fresh").is_dir(), "used in the last 15 minutes: kept over the cap")
            self.assertTrue((cache / "rules-pr/pr-7/k/mine").is_dir())
            self.assertEqual([p.relative_to(cache).as_posix() for p in rule_cache.prune(cache, 0, keep_s=0)],
                             ["rules-pr/pr-7/k/mine", "rules/j/fresh"], "the PR scratch folders count too")


class RaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cache, self.root = self.tmp / "cache" / "rules", self.tmp / "root"
        (self.root / "generated").mkdir(parents=True)

    def keep(self, name="out.txt", where="data/global/excel"):
        def run():
            write(self.root / "generated" / where / name, "x")
        with redirect_stdout(io.StringIO()):
            self.assertFalse(rule_cache.rule(self.cache, "k", {"p": self.root}, run))
        return next(self.cache.glob("k/*"))

    def test_an_evict_or_prune_during_a_replay_leaves_a_run_not_a_crash(self):
        entry = self.keep()
        real, hit = shutil.copy2, []

        def copy_then_lose_the_entry(src, dst, *a, **k):
            if not hit:  # another run deletes the entry between two files of this replay
                hit.append(1)
                rule_cache.evict([entry])
            return real(src, dst, *a, **k)

        runs = []
        with mock.patch.object(shutil, "copy2", copy_then_lose_the_entry), redirect_stdout(io.StringIO()):
            replayed = rule_cache.rule(self.cache, "k", {"p": self.root}, lambda: runs.append(1) or write(
                self.root / "generated" / "data/global/excel/out.txt", "x"))
        self.assertTrue(hit)
        self.assertFalse(replayed, "the entry was gone: the rule ran")
        self.assertEqual(runs, [1])
        self.assertTrue((self.root / "generated/data/global/excel/out.txt").is_file())

    def test_evict_and_prune_rename_before_deleting_and_sweep_leftovers(self):
        entry = self.keep()
        dead = entry.with_name(entry.name + ".dead.1")
        stale = entry.with_name("x.tmp9")
        for d in (dead, stale):
            write(d / "f", "x")
            for q in (d, d / "f"):
                os.utime(q, (time.time() - 7200,) * 2)
        self.assertEqual(rule_cache.prune(self.cache.parent, 10**9), [])
        self.assertFalse(dead.exists() or stale.exists(), "stale leftovers swept")
        self.assertTrue(entry.is_dir())
        rule_cache.evict([entry])
        self.assertFalse(entry.exists() or list(self.cache.glob("k/*")))
        rule_cache.evict([entry])  # already gone: no error

    def test_a_replay_skips_other_runs_tmp_folders_with_a_truncated_manifest(self):
        entry = self.keep()
        for name in ("zz.tmp123", "zz.dead.123"):  # a keep mid-write sorts among the entries
            write(self.cache / "k" / name / "manifest.json", '{"reads": ')
        (entry / "manifest.json").write_text('{"reads": ', "utf-8")  # and a damaged real entry
        runs = []
        with redirect_stdout(io.StringIO()):
            replayed = rule_cache.rule(self.cache, "k", {"p": self.root}, lambda: runs.append(1) or write(
                self.root / "generated" / "data/global/excel/out.txt", "x"))
        self.assertFalse(replayed)
        self.assertEqual(runs, [1], "ran the rule, no JSONDecodeError")

    def test_prune_survives_a_leftover_vanishing_and_spares_a_busy_one(self):
        entry = self.keep()
        busy = entry.with_name("busy.tmp7")
        write(busy / "deep/f", "x")
        os.utime(busy, (time.time() - 7200,) * 2)  # its own mtime is old, a file in it is new
        ghost = entry.with_name("ghost.tmp8")
        write(ghost / "f", "x")
        real = rule_cache._newest

        def vanish(p):
            if p == ghost:
                shutil.rmtree(p)
            return real(p)
        with mock.patch.object(rule_cache, "_newest", vanish):
            rule_cache.prune(self.cache.parent, 10**9)
        self.assertTrue(busy.is_dir() and entry.is_dir())

    def test_delete_that_is_refused_keeps_the_entry_and_is_not_counted_freed(self):
        entry = self.keep()
        with mock.patch.object(os, "rename", side_effect=PermissionError), redirect_stdout(io.StringIO()) as out:
            self.assertFalse(rule_cache._delete(entry))
        self.assertIn("in use", out.getvalue())
        self.assertTrue(entry.is_dir())

    def test_touches_counts_removed_files_and_folders(self):
        for field in ("removed", "rmdirs"):
            e = self.cache / field
            write(e / "manifest.json", json.dumps({"files": [], "removed": [], "rmdirs": [], field: ["data/global/excel/a"]}))
            self.assertTrue(rule_cache.touches(e, "data/global/excel/"))

    def test_evict_touching_spares_entries_the_check_does_not_read(self):
        tables, other = self.keep("a.txt"), None
        self.root2 = self.root
        with redirect_stdout(io.StringIO()):
            rule_cache.rule(self.cache, "k2", {"p": self.root}, lambda: write(self.root / "generated/data/global/x.bin", "x"))
        other = next(self.cache.glob("k2/*"))
        rule_cache.evict([tables, other], "data/global/excel/")
        self.assertFalse(tables.exists())
        self.assertTrue(other.is_dir())


class ToolkitKeyTests(unittest.TestCase):
    """A rule's key takes the toolkit modules its code imports, not the whole toolkit."""

    def kit(self, tmp: Path) -> Path:
        kit = tmp / "kit"
        for f in ("modkit/__init__.py", "modkit/base.py", "modkit/dc6.py", "modkit/other.py", "modkit/hd.py",
                  "shared/classic_import/__init__.py", "shared/classic_import/extract.py",
                  "shared/classic_import/ids.py"):
            write(kit / f, "")
        write(kit / "modkit/base.py", "from . import dc6\n")
        return kit

    def rule(self, tmp: Path, line: str):
        write(tmp / "tk_rule.py", line + "\ndef go(): pass\ndef main():\n    from modkit import other\n")
        sys.path.insert(0, str(tmp))
        self.addCleanup(sys.path.remove, str(tmp))
        self.addCleanup(lambda: [sys.modules.pop(m) for m in [m for m in sys.modules if m.startswith("tk_")]])
        import tk_rule
        return tk_rule.go

    def key(self, fn, kit, tmp):
        files = rule_cache.sources(fn)
        return rule_cache.key(files + rule_cache.toolkit_sources(kit, files), "r")

    def test_only_the_modules_a_rule_imports_change_its_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            kit = self.kit(tmp)
            fn = self.rule(tmp, "def modkit():\n    from modkit import base\n    return base\n")
            before = self.key(fn, kit, tmp)
            names = {p.relative_to(kit).as_posix() for p in rule_cache.toolkit_sources(kit, rule_cache.sources(fn))}
            self.assertEqual(names, {"modkit/__init__.py", "modkit/base.py", "modkit/dc6.py"})  # base's relative import too
            for unrelated in ("modkit/other.py", "modkit/hd.py", "shared/classic_import/ids.py"):  # main() is no import
                write(kit / unrelated, "X = 1\n")
                self.assertEqual(self.key(fn, kit, tmp), before, unrelated)
            for used in ("modkit/base.py", "modkit/dc6.py", "modkit/__init__.py"):
                write(kit / used, (kit / used).read_text() + "EDIT = 1\n")
                after = self.key(fn, kit, tmp)
                self.assertNotEqual(after, before, used)
                before = after






class PackageKeyTests(unittest.TestCase):
    def test_editing_any_module_of_a_package_changes_its_rules_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            write(tmp / "pk_top.py", "from pk_pkg.apply import go\n")
            write(tmp / "pk_pkg" / "__init__.py", "")
            write(tmp / "pk_pkg" / "apply.py", "from .other import f\ndef go(): pass\n")
            write(tmp / "pk_pkg" / "other.py", "def f(): pass\n")
            write(tmp / "pk_pkg" / "passes" / "__init__.py", "")
            write(tmp / "pk_pkg" / "passes" / "found.py", "x = 1\n")  # found by discovery, imported by no one
            sys.path.insert(0, str(tmp))
            try:
                import pk_top
                paths = rule_cache.sources(pk_top.go)
                self.assertEqual({p.relative_to(tmp).as_posix() for p in paths},
                                 {"pk_pkg/__init__.py", "pk_pkg/apply.py", "pk_pkg/other.py",
                                  "pk_pkg/passes/__init__.py", "pk_pkg/passes/found.py"})
                before = rule_cache.key(paths)
                write(tmp / "pk_pkg" / "passes" / "found.py", "x = 2\n")
                self.assertNotEqual(rule_cache.key(rule_cache.sources(pk_top.go)), before)
            finally:
                sys.path.remove(str(tmp))
                for m in [m for m in sys.modules if m.startswith("pk_")]:
                    sys.modules.pop(m)

    def test_package_imports_under_tools_enter_the_key(self):
        forms = {"absolute_from": "from pk2_pkg.consts import X\n", "import_dotted": "import pk2_pkg.consts\n",
                 "from_package": "from pk2_pkg import consts\n"}
        for name, line in forms.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                write(tmp / "pk2_rule.py", line + "def go(): pass\n")
                write(tmp / "pk2_pkg" / "__init__.py", "")
                write(tmp / "pk2_pkg" / "consts.py", "X = 1\n")
                sys.path.insert(0, str(tmp))
                try:
                    import pk2_rule
                    before = rule_cache.key(rule_cache.sources(pk2_rule.go))
                    write(tmp / "pk2_pkg" / "consts.py", "X = 2\n")
                    self.assertNotEqual(rule_cache.key(rule_cache.sources(pk2_rule.go)), before)
                finally:
                    sys.path.remove(str(tmp))
                    for m in [m for m in sys.modules if m.startswith("pk2_")]:
                        sys.modules.pop(m)

    def test_module_files_resolves_every_import_form(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for f in ("pk3_a/__init__.py", "pk3_a/deep.py", "pk3_a/sub/__init__.py", "pk3_a/sub/mod.py"):
                write(tmp / f, "")
            rel = lambda fs: sorted(f.relative_to(tmp).as_posix() for f in fs)
            self.assertEqual(rel(rule_cache.module_files(tmp, "pk3_a.deep", [])), ["pk3_a/deep.py"])
            self.assertEqual(rel(rule_cache.module_files(tmp, "pk3_a", ["deep", "sub", "nope"])),
                             ["pk3_a/__init__.py", "pk3_a/deep.py", "pk3_a/sub/__init__.py"])
            # from .. import deep, written in pk3_a/sub/mod.py: the folder two levels up is pk3_a's, module empty
            self.assertEqual(rel(rule_cache.module_files(tmp / "pk3_a", "", ["deep"])), ["pk3_a/__init__.py", "pk3_a/deep.py"])
            self.assertEqual(rel(rule_cache.module_files(tmp / "pk3_a", "sub.mod", [])), ["pk3_a/sub/mod.py"])




class MergeSlotTests(unittest.TestCase):
    """The machine-wide cap on concurrent merges: a counting semaphore of OS-locked slot files."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "merge-slots"

    def test_the_cap_holds_with_one_more_worker_than_slots(self):
        live, peak, lock = [0], [0], threading.Lock()

        def worker():
            with redirect_stderr(io.StringIO()), rule_cache.Slots(self.dir, 3, poll=0.01):
                with lock:
                    live[0] += 1
                    peak[0] = max(peak[0], live[0])
                time.sleep(0.15)
                with lock:
                    live[0] -= 1
        ts = [threading.Thread(target=worker) for _ in range(4)]
        [t.start() for t in ts]
        [t.join(30) for t in ts]
        self.assertEqual(peak[0], 3)
        self.assertEqual(live[0], 0)

    def test_spare_slots_leave_one_slot_free_and_come_from_the_holders_own_pool(self):
        held = rule_cache.Slots(self.dir, 4, poll=0.01)
        held.acquire()
        spares = rule_cache.spare_slots(9)
        self.addCleanup(lambda: [s.release() for s in spares])
        held.release()
        self.assertEqual(len(spares), 2)  # 4 slots: the holder's, two spares, one left free for an arriving merge
        probe = rule_cache.Slots(self.dir, 4)
        self.assertTrue(probe.try_acquire())
        probe.release()
        self.assertEqual({s.n for s in spares}, {4})

    def test_spare_slots_are_none_without_a_held_slot_and_clone_is_unheld(self):
        self.assertEqual(rule_cache.spare_slots(3), [])
        a = rule_cache.Slots(self.dir, 2, "x", 0.5)
        a.acquire()
        self.addCleanup(a.release)
        c = a.clone()
        self.assertEqual((c.folder, c.n, c.what, c.poll, c.f), (a.folder, 2, "x", 0.5, None))

    def test_a_waiter_says_it_is_queued_once_and_takes_the_slot_a_release_frees(self):
        a = rule_cache.Slots(self.dir, 1, poll=0.01)
        a.acquire()
        buf, got = io.StringIO(), []

        def wait():
            with redirect_stderr(buf):
                b = rule_cache.Slots(self.dir, 1, poll=0.01)
                b.acquire()
                got.append(b)
        t = threading.Thread(target=wait)
        t.start()
        time.sleep(0.2)
        self.assertEqual(got, [])
        a.release()
        t.join(10)
        self.assertEqual(len(got), 1)
        got[0].release()
        self.assertEqual(buf.getvalue().count("queued: 1/1 slots busy"), 1)

    def test_a_killed_holder_frees_its_slot(self):
        code = ("import sys, time; sys.path.insert(0, sys.argv[1]); from shared.classic_import import cache as rule_cache; from pathlib import Path\n"
                "s = rule_cache.Slots(Path(sys.argv[2]), 1); s.acquire(); print('held', flush=True); time.sleep(60)")
        p = subprocess.Popen([sys.executable, "-c", code, str(ROOT), str(self.dir)],
                             stdout=subprocess.PIPE, text=True)
        self.addCleanup(p.kill)
        self.assertEqual(p.stdout.readline().strip(), "held")
        s = rule_cache.Slots(self.dir, 1)
        self.assertIsNone(s._try(0), "held by the child")
        p.kill()
        p.wait(10)
        deadline, f = time.time() + 10, None
        while time.time() < deadline and not (f := s._try(0)):
            time.sleep(0.05)
        self.assertTrue(f, "the OS dropped the dead holder's lock")
        f.close()

    def test_ci_shares_the_agents_cap_and_names_itself_when_it_waits(self):
        home = Path(self.tmp.name)
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "MODKIT_SHARED_CACHE": str(home), "MODKIT_MERGE_SLOTS": "1"}):
            self.assertEqual(rule_cache.slot_home(), home)
            first, second = rule_cache.merge_slots(home), rule_cache.merge_slots(home)
            self.assertEqual(first.folder, home / "merge-slots")  # where the agents' merges count
            first.acquire()
            self.addCleanup(first.release)
            second.poll, buf = 0.01, io.StringIO()

            def wait():
                with redirect_stderr(buf):
                    second.acquire()
            t = threading.Thread(target=wait, daemon=True)
            t.start()
            time.sleep(0.3)
            self.assertIn("CI merge queued: 1/1 slots busy", buf.getvalue())
            first.release()
            t.join(10)
            self.assertIsNotNone(second.f)
            second.release()
        with mock.patch.dict(os.environ, {"MODKIT_SHARED_CACHE": str(home / "none")}):
            self.assertIsNone(rule_cache.slot_home())

    def test_an_agents_spare_slots_never_reach_the_ci_reserve_and_a_clone_keeps_the_pool(self):
        held = rule_cache.Slots(self.dir, 5, poll=0.01, reserved=2)  # agent pool: slots 0-2
        held.acquire()
        self.addCleanup(held.release)
        c = held.clone()
        self.assertEqual((c.reserved, c.ci, c.n, c.f), (2, False, 5, None))
        spares = rule_cache.spare_slots(9)
        self.addCleanup(lambda: [x.release() for x in spares])
        self.assertEqual(len(spares), 1)  # holder + 1 spare + 1 free of the 3-slot pool
        ci = rule_cache.Slots(self.dir, 5, reserved=2, ci=True)
        for i in (3, 4):  # both reserved slots are free to take
            f = ci._try(i)
            self.assertIsNotNone(f)
            f.close()
        free = [i for i in range(3) if (f := ci._try(i)) and not f.close()]
        self.assertEqual(len(free), 1)

    def test_agents_never_hold_a_reserved_slot_and_ci_can(self):
        agents = [rule_cache.Slots(self.dir, 4, poll=0.01, reserved=2) for _ in range(3)]
        agents[0].acquire()
        agents[1].acquire()
        self.addCleanup(agents[0].release)
        self.addCleanup(agents[1].release)
        buf, got = io.StringIO(), []

        def wait():
            with redirect_stderr(buf):
                agents[2].acquire()
                got.append(1)
        t = threading.Thread(target=wait, daemon=True)
        t.start()
        time.sleep(0.3)
        self.assertEqual(got, [], "the third agent waits though two slots are free")
        self.assertIn("merge queued: 2/2 slots busy", buf.getvalue())
        self.assertIn("reserved for CI", buf.getvalue())
        ci = [rule_cache.Slots(self.dir, 4, poll=0.01, reserved=2, ci=True) for _ in range(2)]
        for c in ci:
            c.acquire()
            self.addCleanup(c.release)
        self.assertEqual(sorted(int(c.f.name.rsplit(".", 1)[1]) for c in ci), [2, 3])
        self.assertEqual(got, [])
        agents[0].release()
        t.join(10)
        self.assertEqual(got, [1])
        agents[2].release()

    def test_ci_takes_any_slot_when_all_are_busy_but_one(self):
        agents = [rule_cache.Slots(self.dir, 3, poll=0.01, reserved=1) for _ in range(2)]
        for a in agents:
            a.acquire()
            self.addCleanup(a.release)
        ci = rule_cache.Slots(self.dir, 3, poll=0.01, reserved=1, ci=True)
        ci.acquire()
        self.addCleanup(ci.release)
        self.assertTrue(ci.f.name.endswith("slot.2"))
        later = rule_cache.Slots(self.dir, 3, poll=0.01, reserved=1, ci=True)
        self.assertEqual(later._order(), [2, 1, 0])
        self.assertEqual(agents[0]._order(), [0, 1])

    def test_reserving_everything_still_leaves_agents_one_slot(self):
        self.assertEqual(rule_cache.Slots(self.dir, 2, reserved=5)._order(), [0])
        self.assertEqual(rule_cache.Slots(self.dir, 3)._order(), [0, 1, 2])

    def test_the_reserve_comes_from_the_environment(self):
        home = Path(self.tmp.name)
        with mock.patch.dict(os.environ, {"MODKIT_MERGE_SLOTS": "5", "MODKIT_CI_RESERVED": "1", "GITHUB_ACTIONS": ""}):
            s = rule_cache.merge_slots(home)
            self.assertEqual((s.reserved, s.ci, s._order()), (1, False, [0, 1, 2, 3]))
        with mock.patch.dict(os.environ, {"MODKIT_MERGE_SLOTS": "5", "GITHUB_ACTIONS": "true"}):
            os.environ.pop("MODKIT_CI_RESERVED", None)
            s = rule_cache.merge_slots(home)
            self.assertEqual((s.reserved, s.ci), (2, True))
        with mock.patch.dict(os.environ, {"MODKIT_MERGE_SLOTS": "5", "MODKIT_CI_RESERVED": "x", "GITHUB_ACTIONS": ""}):
            self.assertEqual(rule_cache.merge_slots(home).reserved, 2)

    def test_the_cap_comes_from_the_environment(self):
        with mock.patch.dict(os.environ, {"MODKIT_MERGE_SLOTS": "2"}):
            self.assertEqual(rule_cache.merge_slots(Path(self.tmp.name)).n, 2)
        with mock.patch.dict(os.environ, {"MODKIT_MERGE_SLOTS": ""}):
            self.assertEqual(rule_cache.merge_slots(Path(self.tmp.name)).n, 4)


class SingleFlightTests(unittest.TestCase):
    """Two merges that miss one rule key together run the rule once."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cache = self.tmp / "rules"
        self.runs: list[str] = []
        self.roots = []
        for n in ("one", "two"):
            write(self.tmp / n / "merge" / "r.tsv", "same")  # equal inputs: one's entry is two's hit
            self.roots.append(self.tmp / n)

    def rule_for(self, i, before=None, slots=None, seconds=0.0):
        root = self.roots[i]

        def work():
            if before:
                before()
            self.runs.append(root.name)
            (root / "merge" / "r.tsv").read_text()
            time.sleep(seconds)
            write(root / "generated" / "data" / "a.txt", "A")
        return rule_cache.rule(self.cache, "k", {"p": root}, work, slots=slots)  # callers capture stdout (it is per process)

    def test_the_second_merge_waits_and_replays_with_the_same_bytes(self):
        res = {}
        ts = [threading.Thread(target=lambda i=i: res.__setitem__(i, self.rule_for(i, seconds=1.0))) for i in (0, 1)]
        with redirect_stdout(io.StringIO()) as so:
            ts[0].start()
            time.sleep(0.4)
            ts[1].start()
            [t.join(30) for t in ts]
        self.assertEqual(self.runs, ["one"], "the rule ran once")
        self.assertEqual((res[0], res[1]), (False, True))
        self.assertIn("waited for another run", so.getvalue())
        a = [(r / "generated" / "data" / "a.txt").read_bytes() for r in self.roots]
        self.assertEqual(a[0], a[1], "the same bytes with and without the wait")

    def test_a_holder_that_dies_hands_the_rule_to_the_waiter(self):
        lockfile = self.tmp / "rules.locks" / "k.local"
        code = ("import sys, time; sys.path.insert(0, sys.argv[1]); from shared.classic_import import cache as rule_cache; from pathlib import Path\n"
                "with rule_cache.lock(Path(sys.argv[2])):\n    print('held', flush=True); time.sleep(60)")
        p = subprocess.Popen([sys.executable, "-c", code, str(ROOT), str(lockfile)],
                             stdout=subprocess.PIPE, text=True)
        self.addCleanup(p.kill)
        self.assertEqual(p.stdout.readline().strip(), "held")
        res = []
        t = threading.Thread(target=lambda: res.append(self.rule_for(1)))
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            t.start()
            time.sleep(1.5)
            self.assertEqual(self.runs, [], "waiting on the live holder")
            p.kill()
            p.wait(10)
            t.join(30)
        self.assertEqual(self.runs, ["two"], "the holder died with nothing kept: the waiter runs the rule itself")
        self.assertEqual(res, [False])

    def test_a_merge_holding_the_only_slot_does_not_deadlock_on_a_key_lock(self):
        folder = self.tmp / "slots"
        a, b = rule_cache.Slots(folder, 1, poll=0.01), rule_cache.Slots(folder, 1, poll=0.01)
        b.acquire()  # merge two holds the only slot (an earlier rule ran)
        started, res = threading.Event(), {}

        def holder():  # merge one: holds the key lock, then needs the slot to run
            with redirect_stderr(io.StringIO()):
                res[0] = self.rule_for(0, before=lambda: (started.set(), a.acquire()), slots=a)
            a.release()

        def waiter():  # merge two: needs the key lock one holds, while holding the slot one waits for
            started.wait(10)
            time.sleep(0.2)
            res[1] = self.rule_for(1, slots=b)
        ts = [threading.Thread(target=holder), threading.Thread(target=waiter)]
        with redirect_stdout(io.StringIO()):
            [t.start() for t in ts]
            [t.join(20) for t in ts]
        self.assertFalse(any(t.is_alive() for t in ts), "deadlock: each waits for what the other holds")
        self.assertEqual(self.runs, ["one"])
        self.assertTrue(res[1], "two replays what one kept")
        self.assertIsNone(b.f, "and gave its slot up while it waited")


class CiPolicyTests(unittest.TestCase):
    """The gate replays rules without letting a PR's code write what main's code replays."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.cache = self.home / "rules"
        self.root = self.home / "wt"
        self.out = self.root / "generated" / "data"
        self.root.mkdir()
        self.runs: list[str] = []

    def go(self, policy, text="v"):
        def work():
            self.runs.append(text)
            write(self.out / "a.txt", text)
        with redirect_stdout(io.StringIO()):
            return rule_cache.rule(self.cache, "k", {"p": self.root}, work, policy)

    def test_scope_picks_the_policy(self):
        for scope, want in (("main", ("main", None, True)), ("pr-12", ("pr", self.home / "rules-pr" / "pr-12", True))):
            with mock.patch.dict(os.environ, {"MODKIT_CI_SCOPE": scope}):
                p = rule_cache.ci_policy(self.home)
                self.assertEqual((p.origin, p.scratch, p.write), want)
                self.assertEqual(p.trusted, frozenset({"main"}))
        for scope in ("", "pr-", "pr-1/../x", "pr-1x", "other"):
            with mock.patch.dict(os.environ, {"MODKIT_CI_SCOPE": scope}):
                self.assertIsNone(rule_cache.ci_policy(self.home), f"{scope!r}: no cache, merge fresh")

    def test_a_pr_replays_mains_entries_and_never_writes_the_shared_folder(self):
        main = rule_cache.Policy("main", frozenset({"main"}))
        pr = rule_cache.Policy("pr", frozenset({"main"}), self.home / "rules-pr" / "pr-7")
        self.assertFalse(self.go(main, "m"))
        shutil.rmtree(self.root / "generated")  # a merge starts from an empty generated/
        self.assertTrue(self.go(pr, "p"), "main's entry replays in a PR")
        self.assertEqual(self.runs, ["m"])
        shared = sorted(self.cache.rglob("manifest.json"))
        write(self.root / "x", "")
        # a rule whose inputs differ: a PR run is kept in the scratch folder only
        (self.root / "merge").mkdir()
        def other():
            self.runs.append("p")
            write(self.out / "a.txt", "p")
        with redirect_stdout(io.StringIO()):
            rule_cache.rule(self.cache, "k2", {"p": self.root}, other, pr)
            self.assertTrue(rule_cache.rule(self.cache, "k2", {"p": self.root}, other, pr), "the PR replays its own")
        self.assertEqual(sorted(self.cache.rglob("manifest.json")), shared, "the shared folder is untouched")
        self.assertTrue(list((self.home / "rules-pr" / "pr-7" / "k2").glob("*/manifest.json")))
        with redirect_stdout(io.StringIO()):
            self.assertFalse(rule_cache.rule(self.cache, "k2", {"p": self.root}, other,
                                            rule_cache.Policy("pr", frozenset({"main"}), self.home / "rules-pr" / "pr-8")),
                             "another PR does not read it")
            self.assertFalse(rule_cache.rule(self.cache, "k2", {"p": self.root}, other, main), "nor does main")

    def test_main_replays_only_entries_main_kept(self):
        self.assertFalse(self.go(rule_cache.Policy()), "an agent's local merge keeps an entry")
        main = rule_cache.Policy("main", frozenset({"main"}))
        shutil.rmtree(self.root / "generated")
        self.assertFalse(self.go(main), "main does not replay a local entry: runs fresh")
        shutil.rmtree(self.root / "generated")
        self.assertTrue(self.go(main), "but replays its own")
        shutil.rmtree(self.root / "generated")
        self.assertTrue(self.go(rule_cache.Policy()), "agents replay anything")
        # an entry from before origins (no key) is not main's either
        for m in self.cache.rglob("manifest.json"):
            d = json.loads(m.read_text("utf-8"))
            d.pop("origin")
            m.write_text(json.dumps(d), "utf-8")
        shutil.rmtree(self.root / "generated")
        self.assertFalse(self.go(main))

    def test_a_run_without_a_scope_keeps_nothing(self):
        self.assertFalse(self.go(rule_cache.Policy(write=False)))
        shutil.rmtree(self.root / "generated")
        self.assertFalse(self.go(rule_cache.Policy(write=False)))
        self.assertEqual(self.runs, ["v", "v"])
        self.assertFalse(self.cache.exists())

    def test_a_pr_gate_evicts_only_its_own_scratch_entries(self):
        shared, mine = self.cache / "k" / "e1", self.home / "rules-pr" / "pr-7" / "k" / "e2"
        pr = rule_cache.Policy("pr", frozenset({"main"}), self.home / "rules-pr" / "pr-7")
        self.assertEqual(rule_cache.own([shared, mine], pr), [mine])
        self.assertEqual(rule_cache.own([shared, mine], rule_cache.Policy("main", frozenset({"main"}))), [shared, mine])

    def test_the_main_gate_does_not_wait_on_an_agent_run_it_cannot_replay(self):
        lock = self.home / "rules.locks" / "k.local"
        with rule_cache.lock(lock):  # an agent's run of the key
            t0 = time.time()
            self.assertFalse(self.go(rule_cache.Policy("main", frozenset({"main"}))))
            self.assertLess(time.time() - t0, 5)
        self.assertEqual(self.runs, ["v"])

    def test_sweep_drops_stale_pr_folders_empty_key_folders_and_old_locks(self):
        old = time.time() - 10 * 86400
        for n in ("rules-pr/pr-1/k/e", "rules-pr/pr-2/k/e"):
            write(self.home / n / "manifest.json", "{}")
        for n in ("rules-pr/pr-1", "rules-pr/pr-1/k", "rules-pr/pr-1/k/e", "rules-pr/pr-1/k/e/manifest.json"):
            os.utime(self.home / n, (old, old))
        (self.home / "rules" / "empty").mkdir(parents=True)
        write(self.home / "rules.locks" / "old.main", "")
        write(self.home / "rules.locks" / "new.main", "")
        os.utime(self.home / "rules.locks" / "old.main", (old, old))
        rule_cache.sweep(self.home)
        self.assertFalse((self.home / "rules-pr" / "pr-1").exists())
        self.assertTrue((self.home / "rules-pr" / "pr-2" / "k" / "e").is_dir())
        self.assertFalse((self.home / "rules" / "empty").exists())
        self.assertFalse((self.home / "rules.locks" / "old.main").exists())
        self.assertTrue((self.home / "rules.locks" / "new.main").exists())

    def test_prune_counts_the_pr_scratch_folders(self):
        cache = self.home
        for n in ("rules/k/old", "rules-pr/pr-3/k/e"):
            write(cache / n / "files" / "f", "x" * 100)
            write(cache / n / "manifest.json", json.dumps({"bytes": 100}))
            os.utime(cache / n, (time.time() - 7200, time.time() - 7200))
        gone = rule_cache.prune(cache, 100)
        self.assertEqual([p.relative_to(cache).as_posix() for p in gone], ["rules/k/old"], "oldest first, scratch counted")
        self.assertEqual(len(rule_cache.prune(cache, 0)), 1)



class AstKeyTests(unittest.TestCase):
    """A Python source is keyed by its AST without docstrings; anything else by its bytes."""
    def key_of(self, name: str, text: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / name
            p.write_text(text)
            return rule_cache.key([p])

    BASE = '"""Module doc."""\nLIMIT = 3\n\n\nclass C:\n    """Doc."""\n    x = 1\n\n\ndef f(a):\n    """Doc."""\n    return a + LIMIT\n'

    def test_docstring_comment_and_blank_line_edits_keep_the_key(self):
        edited = ('# a comment\n"""A different module doc."""\n\nLIMIT = 3  # trailing\n\n\n\nclass C:\n    """Other."""\n'
                  '    x = 1\n\n\ndef f(a):\n    # note\n    """Longer doc\n    over lines."""\n    return a + LIMIT\n')
        self.assertEqual(self.key_of("m.py", self.BASE), self.key_of("m.py", edited))

    def test_removing_a_docstring_keeps_the_key(self):
        bare = 'LIMIT = 3\n\n\nclass C:\n    x = 1\n\n\ndef f(a):\n    return a + LIMIT\n'
        self.assertEqual(self.key_of("m.py", self.BASE), self.key_of("m.py", bare))

    def test_a_code_edit_changes_the_key(self):
        base = self.key_of("m.py", self.BASE)
        self.assertNotEqual(base, self.key_of("m.py", self.BASE.replace("LIMIT = 3", "LIMIT = 4")))
        self.assertNotEqual(base, self.key_of("m.py", self.BASE.replace("a + LIMIT", "a - LIMIT")))

    def test_a_string_that_is_not_a_docstring_counts(self):
        a = self.key_of("m.py", "x = 1\n'note'\ny = 2\n")
        self.assertNotEqual(a, self.key_of("m.py", "x = 1\n'other'\ny = 2\n"))

    def test_a_syntax_error_falls_back_to_bytes(self):
        self.assertNotEqual(self.key_of("m.py", "def f(:\n"), self.key_of("m.py", "def f(:  # c\n"))

    def test_other_files_stay_byte_hashed(self):
        self.assertNotEqual(self.key_of("m.txt", self.BASE), self.key_of("m.txt", self.BASE + "# c\n"))

    def test_an_edit_in_place_is_seen_despite_the_digest_memo(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "m.py"
            p.write_text("A = 1\n")
            before = rule_cache.key([p])
            p.write_text("A = 2\n")  # same size; the time moves on
            os.utime(p, ns=(1, p.stat().st_mtime_ns + 10**9))
            self.assertNotEqual(before, rule_cache.key([p]))

    def test_sources_key_ignores_a_docstring_edit_in_a_rule_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = Path(tmp) / "ruleprobe893.py"
            m.write_text('"""v1"""\ndef rule(*a):\n    """v1"""\n    return 1\n')
            sys.path.insert(0, tmp)
            try:
                import importlib
                mod = importlib.import_module("ruleprobe893")
                k1 = rule_cache.key(rule_cache.sources(mod.rule))
                m.write_text('# c\n"""v2"""\ndef rule(*a):\n    """v2 longer"""\n    return 1\n')
                k2 = rule_cache.key(rule_cache.sources(mod.rule))
                m.write_text('def rule(*a):\n    return 2\n')
                k3 = rule_cache.key(rule_cache.sources(mod.rule))
            finally:
                sys.path.remove(tmp)
                sys.modules.pop("ruleprobe893", None)
            self.assertEqual(k1, k2)
            self.assertNotEqual(k1, k3)
