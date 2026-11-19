"""release/stage.py and release/changelog.py on a synthetic project: no game, no 7-Zip, no network.
Run: python -m unittest discover tests"""
import hashlib
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "release"))
import changelog as cl  # noqa: E402
import release_config  # noqa: E402
import stage  # noqa: E402

LOG = ("# Changelog\n\n### Unreleased\n\n#### Maps\n\n- A.\n\n#### Items\n\n- B.\n\n"
       "### 0.1.0 (2026-01-01)\n\n#### Maps\n\n- Old.\n")
RELEASE_LOG = LOG.replace("Unreleased", "0.2.0 (2026-02-01)")

SKELETON = "# Mod 1.0.0\n\n## Changes\n\n- TODO\n\n## Checksums\n\nSee SHA256SUMS.\n"


def pe_exe(path: Path, stamp: int) -> Path:
    """A minimal 'PE' header with the given TimeDateStamp."""
    head = bytearray(0x100)
    head[:2] = b"MZ"
    struct.pack_into("<I", head, 0x3C, 0x80)
    head[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<I", head, 0x80 + 8, stamp)
    path.write_bytes(bytes(head))
    return path


class FoldTests(unittest.TestCase):
    def test_a_fragment_joins_its_categorys_bullets_in_unreleased_only(self):
        out = cl.fold(LOG, "0.2.0", ["#### Maps\n- C.\n"])
        self.assertIn("#### Maps\n\n- A.\n- C.\n\n#### Items\n\n- B.\n\n### 0.1.0", out)
        self.assertIn("- Old.\n", out)

    def test_a_new_category_is_added_at_the_end_of_the_section(self):
        out = cl.fold(LOG, "0.2.0", ["#### Skills\n- D.\n", "- E.\n"])
        self.assertIn("- B.\n\n#### Skills\n\n- D.\n- E.\n\n### 0.1.0", out)

    def test_a_renamed_section_takes_the_fragments_and_a_missing_one_fails(self):
        self.assertIn("- C.\n", cl.fold(RELEASE_LOG, "0.2.0", ["#### Maps\n- C.\n"]))
        with self.assertRaises(cl.ChangelogError):
            cl.fold(LOG.replace("Unreleased", "Soon"), "0.2.0", ["- C.\n"])

    def test_the_versions_section_wins_over_an_unreleased_one(self):
        both = "### Unreleased\n\n- Soon.\n\n" + RELEASE_LOG.split("# Changelog\n\n", 1)[1]
        out = cl.fold("# Changelog\n\n" + both, "0.2.0", ["#### Maps\n- C.\n"])
        self.assertEqual(cl.notes_section(out, "0.2.0").count("- C."), 1)
        self.assertNotIn("- C.", out.split("### 0.2.0")[0])

    def test_the_changelog_is_never_its_own_fragment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CHANGELOG.md").write_text(LOG, "utf-8")
            (root / "x.md").write_text("- Z.\n", "utf-8")
            self.assertEqual([f.name for f in cl.fragment_files(root, ".", "CHANGELOG.md")], ["x.md"])

    def test_the_command_line_folds_and_reports_a_missing_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "changelog.d").mkdir()
            (root / "CHANGELOG.md").write_text(LOG, "utf-8")
            (root / "changelog.d" / "1.md").write_text("- Z.\n", "utf-8")
            self.assertEqual(cl.main(["fold", "--root", str(root), "--version", "v0.2.0"]), 0)
            self.assertIn("- Z.", (root / "CHANGELOG.md").read_text("utf-8"))
            self.assertEqual(list((root / "changelog.d").iterdir()), [])
            (root / "CHANGELOG.md").write_text("# nothing\n", "utf-8")
            (root / "changelog.d" / "2.md").write_text("- Y.\n", "utf-8")
            self.assertEqual(cl.main(["fold", "--root", str(root), "--version", "0.2.0"]), 1)
            self.assertTrue((root / "changelog.d" / "2.md").exists())

    def test_folding_fragments_deletes_them_in_file_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "changelog.d").mkdir()
            (root / "CHANGELOG.md").write_text(LOG, "utf-8")
            (root / "changelog.d" / "2-b.md").write_text("#### Items\n- Y.\n", "utf-8")
            (root / "changelog.d" / "1-a.md").write_text("#### Items\n- X.\n", "utf-8")
            (root / "changelog.d" / ".gitkeep").write_text("", "utf-8")
            (root / "changelog.d" / "README.md").write_text("not a fragment", "utf-8")
            self.assertEqual(cl.fold_fragments(root, "0.2.0"), 2)
            self.assertIn("- B.\n- X.\n- Y.\n", (root / "CHANGELOG.md").read_text("utf-8"))
            self.assertEqual(sorted(f.name for f in (root / "changelog.d").iterdir()), [".gitkeep", "README.md"])
            self.assertEqual(cl.fold_fragments(root, "0.2.0"), 0)

    def test_pending_changes_nothing_on_disk_and_honours_other_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frag").mkdir()
            (root / "LOG.md").write_text(LOG, "utf-8")
            (root / "frag" / "1.md").write_text("- Z.\n", "utf-8")
            text, files = cl.pending(root, "0.2.0", "LOG.md", "frag")
            self.assertIn("- Z.", text)
            self.assertEqual(len(files), 1)
            self.assertEqual((root / "LOG.md").read_text("utf-8"), LOG)


class NotesTests(unittest.TestCase):
    LOGS = "### 0.2.0 (2026-12-01)\n\n- Newer.\n\n### 0.1.0-alpha (2026-11-05)\n\n- First line.\n- Second line.\n"

    def test_takes_only_the_versions_section(self):
        self.assertEqual(cl.notes_section(self.LOGS, "0.1.0-alpha"), "- First line.\n- Second line.")
        self.assertEqual(cl.notes_section(self.LOGS, "0.2.0"), "- Newer.")

    def test_refuses_a_version_without_a_section(self):
        with self.assertRaises(cl.ChangelogError):
            cl.notes_section(self.LOGS, "0.1.0")  # a prefix of 0.1.0-alpha must not match
        with self.assertRaises(cl.ChangelogError):
            cl.notes_section("### Unreleased\n\n- x\n", "0.1.0-alpha")

    def test_finish_notes_lists_only_the_changes_and_keeps_sums_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            (dist / "M-1.0.0.7z").write_bytes(b"7z")
            (dist / "RELEASE_NOTES-1.0.0.md").write_text(SKELETON)
            (dist / "SHA256SUMS").write_text(f"{'0' * 64}  M-1.0.0.7z\n{'0' * 64}  RELEASE_NOTES-1.0.0.md\n")
            stage.finish_notes(dist, "1.0.0", "#### Items\n\n- A change.\n")
            self.assertEqual((dist / "RELEASE_NOTES-1.0.0.md").read_text(), "#### Items\n\n- A change.\n")
            for line in (dist / "SHA256SUMS").read_text().splitlines():
                digest, name = line.split("  ")
                self.assertEqual(digest, hashlib.sha256((dist / name).read_bytes()).hexdigest(), name)


def config(**stage_over):
    cfg = release_config.defaults()
    cfg["mod"]["folder"] = "Mod"
    cfg["stage"].update({"plugins": ["one", "two"], **stage_over})
    return cfg


class StageTests(unittest.TestCase):
    def project(self, root: Path) -> Path:
        root.mkdir()
        (root / "mod.json").write_text(json.dumps({"name": "Mod", "title": "The Mod", "version": "1.0.0",
                                                   "extendedSaves": True}))
        (root / "out/data/global/excel").mkdir(parents=True)
        (root / "out/data/global/excel/skills.txt").write_text("ours")
        comp = root / "generated/companions"
        (comp / "d2rloader/plugins").mkdir(parents=True)
        (comp / "d2rloader/plugins/x.dll").write_bytes(b"companion")
        (comp / "d2rloader/config").mkdir()
        (comp / "d2rloader/config/filter.json").write_text("{}")
        (root / "companions").mkdir()
        (root / "companions/manifest.json").write_text(json.dumps({"companions": [{
            "name": "X", "repo": "o/r", "tag": "t", "asset": "x.zip", "sha256": "0" * 64, "files": {"a": "d2rloader/plugins/x.dll"},
            "filter_tables": ["armor", "skills"], "loader_settings": {"d2rcore.items": {"item_stat_ranges": True}}}]}))
        build = root / "plugin/build/Release"
        build.mkdir(parents=True)
        for name in ("one", "two"):
            (build / f"{name}.dll").write_bytes(name.encode())
        return root

    def test_lays_out_the_installed_mod_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp) / "p")
            mod = stage.stage(root, Path(tmp) / "stage", config(companions=True),
                              read=lambda rel: b"vanilla " + rel.encode())
            self.assertEqual(mod.name, "Mod")
            excel = mod / "Mod.mpq/data/global/excel"
            self.assertEqual((excel / "skills.txt").read_text(), "ours")
            self.assertEqual((excel / "armor.txt").read_bytes(), b"vanilla data/global/excel/armor.txt")
            for f in ("modinfo.json", "Mod.mpq/modinfo.json"):
                self.assertEqual(json.loads((mod / f).read_text()), {"name": "Mod", "savepath": "Mod/"})
            self.assertEqual(json.loads((mod / "d2rloader/metadata.json").read_text())["metadata"]["modVersion"], "1.0.0")
            toml = (mod / "d2rloader/config/d2rloader.toml").read_text()
            self.assertIn('mode = "extended"', toml)
            self.assertIn("item_stat_ranges = true", toml)
            self.assertEqual(sorted(p.name for p in (mod / "d2rloader/plugins").iterdir()), ["one.dll", "two.dll", "x.dll"])

    def test_namespace_from_mod_json_goes_to_the_top_level_of_the_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp) / "p")
            plain = stage.stage(root, Path(tmp) / "s1", config(), read=lambda rel: b"v")
            self.assertNotIn("namespace", json.loads((plain / "d2rloader/metadata.json").read_text()))
            mj = json.loads((root / "mod.json").read_text())
            (root / "mod.json").write_text(json.dumps({**mj, "namespace": "mymod"}))
            mod = stage.stage(root, Path(tmp) / "s2", config(), read=lambda rel: b"v")
            meta = json.loads((mod / "d2rloader/metadata.json").read_text())
            self.assertEqual(meta["namespace"], "mymod")
            self.assertEqual(meta["schemaVersion"], 1)
            self.assertNotIn("namespace", meta["metadata"])

    def test_refuses_an_invalid_or_reserved_namespace(self):
        for ns in ("my mod", "d2r", "d2rloader", "", 5, "x" * 257):
            with self.subTest(ns=ns), tempfile.TemporaryDirectory() as tmp:
                root = self.project(Path(tmp) / "p")
                mj = json.loads((root / "mod.json").read_text())
                (root / "mod.json").write_text(json.dumps({**mj, "namespace": ns}))
                with self.assertRaises(stage.ReleaseError):
                    stage.stage(root, Path(tmp) / "s", config(), read=lambda rel: b"v")

    def test_legal_files_of_the_project_root_ship_at_the_mod_folder_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp) / "p")
            self.assertEqual([p.name for p in stage.stage(root, Path(tmp) / "s0", config()).glob("[LNC]*")], [])
            (root / "LICENSE").write_text("MIT")
            (root / "NOTICE.md").write_text("notice")
            mod = stage.stage(root, Path(tmp) / "s1", config())
            self.assertEqual((mod / "LICENSE").read_text(), "MIT")
            self.assertEqual((mod / "NOTICE.md").read_text(), "notice")
            self.assertFalse((mod / "COPYING").exists())

    def test_without_companions_only_the_plugins_ship(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp) / "p")
            (root / "generated/companions").rename(root / "generated/gone")
            mod = stage.stage(root, Path(tmp) / "stage", config(), read=None)
            self.assertEqual(sorted(p.name for p in (mod / "d2rloader/plugins").iterdir()), ["one.dll", "two.dll"])
            self.assertFalse((mod / "Mod.mpq/data/global/excel/armor.txt").exists())

    def test_refuses_a_missing_plugin_or_missing_companions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp) / "p")
            (root / "plugin/build/Release/two.dll").unlink()
            with self.assertRaises(stage.ReleaseError):
                stage.stage(root, Path(tmp) / "stage", config(), read=lambda rel: b"")
            (root / "plugin/build/Release/two.dll").write_bytes(b"2")
            (root / "generated/companions").rename(root / "generated/gone")
            with self.assertRaises(stage.ReleaseError):
                stage.stage(root, Path(tmp) / "stage", config(companions=True), read=lambda rel: b"")

    def test_refuses_an_unsafe_or_mismatched_name_before_deleting_anything(self):
        for name in ("..", ".", "", "../x", "a/b", "a\\b", "C:x", "/abs"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = self.project(Path(tmp) / "p")
                (root / "mod.json").write_text(json.dumps({"name": name, "version": "1.0.0"}))
                out = Path(tmp) / "out"
                (out / "mod").mkdir(parents=True)
                keep = out / "keep.txt"
                keep.write_text("x")
                with self.assertRaises(stage.ReleaseError):
                    stage.stage(root, out / "mod", config(), read=None)
                self.assertTrue(keep.exists())
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp) / "p")
            cfg = config()
            cfg["mod"]["folder"] = "Other"
            with self.assertRaisesRegex(stage.ReleaseError, "is mod 'Mod' but mod.folder is 'Other'"):
                stage.stage(root, Path(tmp) / "stage", cfg, read=None)

    def test_restaging_starts_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp) / "p")
            stale = Path(tmp) / "stage/Mod/Mod.mpq/data/old.txt"
            stale.parent.mkdir(parents=True)
            stale.write_text("old")
            stage.stage(root, Path(tmp) / "stage", config(), read=lambda rel: b"")
            self.assertFalse(stale.exists())


class ExtraPluginTests(unittest.TestCase):
    project = StageTests.project

    def test_an_extra_plugin_ships_and_leaves_a_traceable_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp) / "p")
            extra = Path(tmp) / "side.dll"
            extra.write_bytes(b"side")
            dll, source = stage.parse_extra_plugin(f"{extra}@sibling abc123")
            self.assertEqual((dll, source), (extra, "sibling abc123"))
            mod = stage.stage(root, Path(tmp) / "stage", config(), extra_plugins=[dll])
            self.assertEqual((mod / "d2rloader/plugins/side.dll").read_bytes(), b"side")
            self.assertEqual(stage.extra_plugin_note(dll, source),
                             f"side: sibling abc123, sha256 {hashlib.sha256(b'side').hexdigest()}")
            self.assertTrue(stage.extra_plugin_note(dll, "").startswith("side: sha256 "))

    def test_an_extra_plugin_must_be_an_existing_dll(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.txt").write_text("x")
            for spec in (str(Path(tmp) / "missing.dll"), str(Path(tmp) / "a.txt")):
                with self.assertRaises(stage.ReleaseError):
                    stage.parse_extra_plugin(spec)

    def test_an_at_sign_in_the_path_is_not_the_source_separator(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "me@home"
            folder.mkdir()
            (folder / "side.dll").write_bytes(b"s")
            self.assertEqual(stage.parse_extra_plugin(f"{folder / 'side.dll'}@src @1"), (folder / "side.dll", "src @1"))
            self.assertEqual(stage.parse_extra_plugin(str(folder / "side.dll")), (folder / "side.dll", ""))

    def test_an_extra_plugin_may_not_reuse_a_plugin_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp) / "p")
            same = Path(tmp) / "ONE.dll"
            same.write_bytes(b"other")
            with self.assertRaisesRegex(stage.ReleaseError, "two plugins"):
                stage.stage(root, Path(tmp) / "stage", config(), extra_plugins=[same])

    def test_with_loader_pins_the_game_loader_in_the_catalog(self):
        text = '[d2rloader]\r\nversion = "1.2"\r\n[catalog]\r\nloader_versions = ["1.2"]\r\n'
        conf = stage.tomllib.loads(stage.with_loader(text, Path("C:/g/D2RLoader.exe")))
        self.assertEqual(conf["catalog"]["loader_files"], [{"path": "C:/g/D2RLoader.exe", "version": "1.2"}])
        self.assertEqual(conf["catalog"]["loader_versions"], ["1.2"])
        commented = stage.tomllib.loads(stage.with_loader('[d2rloader]\nversion = "1"\n[catalog]  # pins\nx = 1\n', Path("x.exe")))
        self.assertEqual(commented["catalog"]["loader_files"], [{"path": "x.exe", "version": "1"}])
        for bad in ('[d2rloader]\nversion = "1"\n', '[catalog]\n',
                    '[d2rloader]\nversion = "1"\n[catalog]\nloader_files = []\n',
                    '[d2rloader]\nversion = "1"\ncatalog = {product_id = "x"}\n',
                    '[d2rloader]\nversion = "1"\ncatalog.product_id = "x"\n'):
            with self.assertRaises(stage.ReleaseError):
                stage.with_loader(bad, Path("x.exe"))


class GuardTests(unittest.TestCase):
    def test_game_image_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = pe_exe(Path(tmp) / "D2RLoader.exe", 0x6AB3782C)
            self.assertEqual(stage.pe_timestamp(exe), 0x6AB3782C)
            cfg = release_config.defaults()
            stage.check_game_image(cfg, exe)  # no timestamp in the config: no check
            cfg["game"]["image_timestamp"] = "0x6ab3782c"
            stage.check_game_image(cfg, exe)
            cfg["game"]["image_timestamp"] = "0x11111111"
            with self.assertRaisesRegex(stage.ReleaseError, "game image"):
                stage.check_game_image(cfg, exe)
            (Path(tmp) / "x.exe").write_bytes(b"nope")
            with self.assertRaises(stage.ReleaseError):
                stage.pe_timestamp(Path(tmp) / "x.exe")

    def test_item_type_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            stage.check_item_types(data)  # no itemtypes.txt: nothing to check
            excel = data / "global" / "excel"
            excel.mkdir(parents=True)
            (excel / "itemtypes.txt").write_text("ItemType\tCode\nNone\tnone\n", encoding="latin-1")
            with self.assertRaisesRegex(stage.ReleaseError, "item type ids"):
                stage.check_item_types(data)


class MainTests(unittest.TestCase):
    def run_main(self, run, with_fragment=True, version_section=True, args=(), cwd=None, mod_name="M", changelog=True,
                 prepare=None, out_dir="dist"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "p"
        root.mkdir()
        log = RELEASE_LOG if version_section else LOG.replace("Unreleased", "Soon")
        (root / "changelog.d").mkdir()
        self.root = root
        self.log = log
        if changelog:
            (root / "CHANGELOG.md").write_text(log, "utf-8")
        (root / "mod.json").write_text(json.dumps({"name": mod_name, "version": "0.2.0"}), "utf-8")
        (root / "release.toml").write_text('[mod]\nfolder = "M"\n[stage]\nitem_type_check = false\n', "utf-8")
        if with_fragment:
            (root / "changelog.d" / "1-a.md").write_text("#### Items\n- X.\n", "utf-8")
        if prepare:
            prepare(root)
        game = Path(tmp.name) / "game"
        game.mkdir()
        if cwd:
            old = os.getcwd()
            os.chdir(cwd)
            self.addCleanup(os.chdir, old)
        with mock.patch.object(stage, "stage", return_value=root / "mod") as staged, \
                mock.patch.dict(sys.modules, {"modkit": mock.MagicMock(), "modkit.base": mock.MagicMock()}), \
                mock.patch.object(stage.subprocess, "run", side_effect=run):
            code = stage.main(["--game", str(game), "--root", str(root), "--out", str(root / out_dir), *args])
        self.staged = staged
        return root, code, log

    def assert_restored(self, root, log):
        self.assertEqual((root / "CHANGELOG.md").read_text("utf-8"), log)
        self.assertEqual([f.name for f in (root / "changelog.d").iterdir()], ["1-a.md"])

    def test_loader_from_game_and_extra_plugins_reach_package_release(self):
        seen = {}
        side = tempfile.TemporaryDirectory()
        self.addCleanup(side.cleanup)
        dll = Path(side.name) / "x.dll"
        dll.write_bytes(b"x")

        def run(cmd, **k):
            seen["config"] = Path(cmd[cmd.index("--config") + 1]).read_text("utf-8")
            return mock.Mock(returncode=3)

        def prepare(root):
            (root / "release.toml").write_text('[mod]\nfolder = "M"\n[stage]\nitem_type_check = false\n'
                                               'loader_from_game = true\n[d2rloader]\nversion = "9.9"\n[catalog]\n', "utf-8")
        root, code, log = self.run_main(run, prepare=prepare, args=["--extra-plugin", f"{dll}@src"])
        self.assertIn('version = "9.9"', seen["config"])
        self.assertIn("D2RLoader.exe", seen["config"])
        self.assertEqual([str(p.name) for p in self.staged.call_args.args[-1]], ["x.dll"])

    def test_a_notes_file_reaches_package_release_by_flag_or_config(self):
        seen = []
        side = tempfile.TemporaryDirectory()
        self.addCleanup(side.cleanup)
        flag = Path(side.name) / "n.md"
        flag.write_text("short\n", "utf-8")

        def run(cmd, **k):
            seen.append(cmd)
            return mock.Mock(returncode=3)

        def prepare(root):
            (root / "0.2.0.md").write_text("cfg\n", "utf-8")
            (root / "release.toml").write_text(
                '[mod]\nfolder = "M"\n[stage]\nitem_type_check = false\nnotes = "{version}.md"\n', "utf-8")
        self.run_main(run, prepare=prepare)
        self.assertEqual(Path(seen[-1][seen[-1].index("--notes") + 1]).name, "0.2.0.md")
        self.run_main(run, prepare=prepare, args=["--notes", str(flag)])
        self.assertEqual(Path(seen[-1][seen[-1].index("--notes") + 1]).name, "n.md")
        self.run_main(run)
        self.assertNotIn("--notes", seen[-1])

    def test_the_extra_plugin_note_reaches_the_release_notes(self):
        side = tempfile.TemporaryDirectory()
        self.addCleanup(side.cleanup)
        dll = Path(side.name) / "x.dll"
        dll.write_bytes(b"x")

        def run(cmd, **k):
            out = Path(cmd[cmd.index("--out") + 1])
            (out / "RELEASE_NOTES-0.2.0.md").write_text(SKELETON)
            (out / "SHA256SUMS").write_text(f"{'0' * 64}  RELEASE_NOTES-0.2.0.md\n")
            return mock.Mock(returncode=0)
        root, code, log = self.run_main(run, args=["--extra-plugin", f"{dll}@src 1"])
        self.assertEqual(code, 0)
        notes = (root / "dist" / "RELEASE_NOTES-0.2.0.md").read_text("utf-8")
        self.assertIn(f"x: src 1, sha256 {hashlib.sha256(b'x').hexdigest()}", notes)

    def test_a_missing_version_section_changes_nothing(self):
        root, code, log = self.run_main(lambda *a, **k: mock.Mock(returncode=0), version_section=False)
        self.assertEqual(code, 1)
        self.assert_restored(root, log)

    def test_a_failing_package_release_restores_the_changelog_and_keeps_fragments(self):
        seen = []

        def run(*a, **k):
            seen.append(True)
            return mock.Mock(returncode=3)
        root, code, log = self.run_main(run)
        self.assertEqual((code, seen), (3, [True]))
        self.assert_restored(root, log)

    def test_a_raising_package_release_restores_the_changelog_and_propagates(self):
        with self.assertRaises(FileNotFoundError):
            self.run_main(FileNotFoundError("no python"))
        self.assert_restored(self.root, self.log)

    def test_runs_package_release_in_the_project_from_any_folder(self):
        seen = []

        def run(cmd, **k):
            seen.append((k.get("cwd"), cmd[cmd.index("--out") + 1], cmd[cmd.index("--config") + 1]))
            return mock.Mock(returncode=3)
        elsewhere = tempfile.TemporaryDirectory()
        self.addCleanup(elsewhere.cleanup)
        root, code, log = self.run_main(run, cwd=elsewhere.name)
        self.assertEqual(len(seen), 1)
        cwd, out, config_path = seen[0]
        self.assertEqual(Path(cwd).resolve(), root.resolve())
        self.assertTrue(Path(out).is_absolute() and Path(config_path).is_absolute())

    def test_a_leading_v_in_the_version_is_dropped_and_a_bad_version_refused_early(self):
        seen = []

        def run(cmd, **k):
            seen.append(cmd[cmd.index("--version") + 1])
            return mock.Mock(returncode=3)
        self.run_main(run, args=["--version", "v0.2.0"])
        self.assertEqual(seen, ["0.2.0"])
        root, code, log = self.run_main(run, args=["--version", "banana"])
        self.assertEqual((code, seen), (1, ["0.2.0"]))
        self.assert_restored(root, log)

    def test_bad_inputs_are_clean_errors(self):
        ok = lambda *a, **k: mock.Mock(returncode=0)  # noqa: E731
        root, code, log = self.run_main(ok, changelog=False)  # no changelog
        self.assertEqual(code, 1)
        for name in ("..", "Other"):  # unsafe name, name != mod.folder: nothing staged
            root, code, log = self.run_main(ok, mod_name=name)
            self.assertEqual(code, 1)
            self.staged.assert_not_called()
            self.assert_restored(root, log)

    def test_a_broken_mod_json_is_a_clean_error(self):
        root, code, log = self.run_main(lambda *a, **k: mock.Mock(returncode=0))
        (root / "mod.json").write_text("{not json", "utf-8")
        self.assertRaises(stage.ReleaseError, stage.read_mod_json, root)
        with mock.patch.object(stage, "read_mod_json", side_effect=stage.ReleaseError("bad")):
            code = stage.main(["--game", str(root), "--root", str(root)])
        self.assertEqual(code, 1)

    def test_the_staged_copy_is_removed_after_success(self):
        def run(cmd, **k):
            out = Path(cmd[cmd.index("--out") + 1])
            (out / stage.STAGE_DIR / "M").mkdir(parents=True, exist_ok=True)
            (out / "RELEASE_NOTES-0.2.0.md").write_text(SKELETON)
            (out / "SHA256SUMS").write_text(f"{'0' * 64}  RELEASE_NOTES-0.2.0.md\n")
            return mock.Mock(returncode=0)
        root, code, log = self.run_main(run)
        self.assertEqual(code, 0)
        self.assertFalse((root / "dist" / stage.STAGE_DIR).exists())

    def test_a_failed_run_keeps_a_users_dist_mod_folder(self):
        def prepare(root):
            (root / "dist" / "mod").mkdir(parents=True)
            (root / "dist" / "mod" / "user.txt").write_text("mine")
        for run, version_section in ((lambda *a, **k: mock.Mock(returncode=3), True),
                                     (lambda *a, **k: mock.Mock(returncode=0), False)):  # fails late / before staging
            root, code, log = self.run_main(run, version_section=version_section, prepare=prepare)
            self.assertNotEqual(code, 0)
            self.assertEqual((root / "dist" / "mod" / "user.txt").read_text(), "mine")
            self.assertFalse((root / "dist" / stage.STAGE_DIR).exists())

    def test_out_set_to_the_project_never_touches_its_mod_folder(self):
        def prepare(root):
            (root / "mod").mkdir()
            (root / "mod" / "keep.txt").write_text("project")
        for run, version_section in ((lambda *a, **k: mock.Mock(returncode=3), True),
                                     (lambda *a, **k: mock.Mock(returncode=0), False)):
            root, code, log = self.run_main(run, version_section=version_section, prepare=prepare, out_dir=".")
            self.assertNotEqual(code, 0)
            self.assertEqual((root / "mod" / "keep.txt").read_text(), "project")
            self.assertFalse((root / stage.STAGE_DIR).exists())

    def test_a_stale_stage_folder_is_replaced_and_the_staging_goes_there(self):
        def prepare(root):
            (root / "dist" / stage.STAGE_DIR).mkdir(parents=True)
            (root / "dist" / stage.STAGE_DIR / "old.txt").write_text("stale")
        root, code, log = self.run_main(lambda *a, **k: mock.Mock(returncode=3), prepare=prepare)
        self.assertEqual(self.staged.call_args[0][1], root / "dist" / stage.STAGE_DIR)
        self.assertFalse((root / "dist" / stage.STAGE_DIR).exists())

    def test_success_folds_then_deletes_the_fragments_and_writes_the_notes(self):
        def run(cmd, **k):
            out = Path(cmd[cmd.index("--out") + 1])
            out.mkdir(parents=True, exist_ok=True)
            (out / "RELEASE_NOTES-0.2.0.md").write_text(SKELETON)
            (out / "SHA256SUMS").write_text(f"{'0' * 64}  RELEASE_NOTES-0.2.0.md\n")
            return mock.Mock(returncode=0)
        root, code, log = self.run_main(run)
        self.assertEqual(code, 0)
        self.assertIn("- X.", (root / "CHANGELOG.md").read_text("utf-8"))
        self.assertEqual(list((root / "changelog.d").iterdir()), [])
        self.assertIn("- X.", (root / "dist" / "RELEASE_NOTES-0.2.0.md").read_text())


class FoldCliConfigTests(unittest.TestCase):
    def project(self, tmp, toml=None):
        root = Path(tmp)
        (root / "CHANGELOG.md").write_text(RELEASE_LOG, "utf-8")
        if toml is not None:
            (root / "release.toml").write_text(toml, "utf-8")
        return root

    def test_defaults_come_from_release_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(tmp, '[repos]\nfragments = "notes.d"\nchangelog = "docs/LOG.md"\n')
            (root / "docs").mkdir()
            (root / "docs" / "LOG.md").write_text(RELEASE_LOG, "utf-8")
            (root / "notes.d").mkdir()
            (root / "notes.d" / "1.md").write_text("- Z.\n", "utf-8")
            self.assertEqual(cl.main(["fold", "--root", str(root), "--version", "0.2.0"]), 0)
            self.assertIn("- Z.", (root / "docs" / "LOG.md").read_text("utf-8"))
            self.assertFalse((root / "notes.d" / "1.md").exists())

    def test_fragments_option_must_be_a_folder_below_the_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(tmp, "")
            (root.parent / "outside").mkdir(exist_ok=True)
            (root.parent / "outside" / "1.md").write_text("- Z.\n", "utf-8")
            for bad in ("..", "../outside", "/abs", "C:x", ".", ""):
                with self.subTest(bad=bad):
                    self.assertEqual(cl.main(["fold", "--root", str(root), "--version", "0.2.0", "--fragments", bad]), 1)
            self.assertTrue((root.parent / "outside" / "1.md").exists())

    def test_a_broken_release_toml_is_a_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(tmp, "[repos\n")
            self.assertEqual(cl.main(["fold", "--root", str(root), "--version", "0.2.0"]), 1)


class ConfigTests(unittest.TestCase):
    def test_fragments_must_be_a_folder_below_the_project(self):
        for bad in (".", "", "../x", "a/../..", "/abs", "C:/x"):
            cfg = release_config.defaults()
            cfg["repos"]["fragments"] = bad
            with self.subTest(bad=bad), self.assertRaises(release_config.ConfigError):
                release_config.validate(cfg)
        cfg = release_config.defaults()
        cfg["repos"].update({"changelog": "docs/CHANGELOG.md", "fragments": "docs"})
        with self.assertRaises(release_config.ConfigError):
            release_config.validate(cfg)
        cfg["repos"]["fragments"] = "docs/changelog.d"
        release_config.validate(cfg)

    def test_stage_defaults_and_plugin_names(self):
        cfg = release_config.defaults()
        self.assertEqual(cfg["stage"]["plugins"], [])
        self.assertEqual(cfg["repos"]["fragments"], "changelog.d")
        cfg["stage"]["plugins"] = ["bad.dll"]
        with self.assertRaises(release_config.ConfigError):
            release_config.validate(cfg)


if __name__ == "__main__":
    unittest.main()
