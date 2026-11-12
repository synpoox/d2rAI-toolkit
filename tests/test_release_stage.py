"""release/stage.py and release/changelog.py on a synthetic project: no game, no 7-Zip, no network.
Run: python -m unittest discover tests"""
import hashlib
import json
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

    def test_restaging_starts_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp) / "p")
            stale = Path(tmp) / "stage/Mod/Mod.mpq/data/old.txt"
            stale.parent.mkdir(parents=True)
            stale.write_text("old")
            stage.stage(root, Path(tmp) / "stage", config(), read=lambda rel: b"")
            self.assertFalse(stale.exists())


class GuardTests(unittest.TestCase):
    def test_game_image_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = pe_exe(Path(tmp) / "D2R.exe", 0x6AB3782C)
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
    def run_main(self, run, with_fragment=True, version_section=True):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "p"
        root.mkdir()
        log = RELEASE_LOG if version_section else LOG.replace("Unreleased", "Soon")
        (root / "changelog.d").mkdir()
        (root / "CHANGELOG.md").write_text(log, "utf-8")
        (root / "mod.json").write_text('{"name": "M", "version": "0.2.0"}', "utf-8")
        (root / "release.toml").write_text('[stage]\nitem_type_check = false\n', "utf-8")
        if with_fragment:
            (root / "changelog.d" / "1-a.md").write_text("#### Items\n- X.\n", "utf-8")
        game = Path(tmp.name) / "game"
        game.mkdir()
        with mock.patch.object(stage, "stage", return_value=root / "mod"), \
                mock.patch.dict(sys.modules, {"modkit": mock.MagicMock(), "modkit.base": mock.MagicMock()}), \
                mock.patch.object(stage.subprocess, "run", side_effect=run):
            code = stage.main(["--game", str(game), "--root", str(root), "--out", str(root / "dist")])
        return root, code, log

    def assert_restored(self, root, log):
        self.assertEqual((root / "CHANGELOG.md").read_text("utf-8"), log)
        self.assertEqual([f.name for f in (root / "changelog.d").iterdir()], ["1-a.md"])

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


class ConfigTests(unittest.TestCase):
    def test_stage_defaults_and_plugin_names(self):
        cfg = release_config.defaults()
        self.assertEqual(cfg["stage"]["plugins"], [])
        self.assertEqual(cfg["repos"]["fragments"], "changelog.d")
        cfg["stage"]["plugins"] = ["bad.dll"]
        with self.assertRaises(release_config.ConfigError):
            release_config.validate(cfg)


if __name__ == "__main__":
    unittest.main()
