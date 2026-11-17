"""release/companions.py on synthetic zips: no network, no game. Run: python -m unittest discover tests"""
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "release"))
import companions  # noqa: E402

ITEM_RANGES = "[d2rcore.items]\nitem_stat_ranges = true\n"
TABLES = ["armor", "weapons", "misc", "itemtypes", "skills", "itemstatcost"]


def make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


class CompanionTests(unittest.TestCase):
    def project(self, tmp: Path, zipped: bytes, sha=None, **entry) -> Path:
        (tmp / "companions").mkdir()
        (tmp / "companions" / "filter.json").write_text('{"version": 3, "rules": []}')
        manifest = {"config": ["companions/config/", "companions/filter.json"],
                    "companions": [{"name": "X", "repo": "o/r", "tag": "t", "asset": "x.zip",
                                    "sha256": sha or hashlib.sha256(zipped).hexdigest(),
                                    "files": {"d2rloader/plugins/x.dll": "d2rloader/plugins/x.dll",
                                              "Other.mpq/data/sfx/": "Mod.mpq/data/sfx/"}, **entry}]}
        self.write_manifest(tmp, manifest)
        return tmp

    @staticmethod
    def write_manifest(root: Path, manifest: dict):
        (root / "companions" / "manifest.json").write_text(json.dumps(manifest))

    def test_unpacks_only_listed_files(self):
        zipped = make_zip({"d2rloader/plugins/x.dll": b"dll", "Other.mpq/data/sfx/a.flac": b"a",
                           "Other.mpq/data/global/excel/sounds.txt": b"not ours"})
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp), zipped)
            written = companions.fetch(root, download=lambda *a: zipped)
            out = root / "generated" / "companions"
            self.assertEqual(sorted(written), ["Mod.mpq/data/sfx/a.flac", "d2rloader/config/filter.json",
                                               "d2rloader/plugins/x.dll"])
            self.assertEqual((out / "d2rloader/plugins/x.dll").read_bytes(), b"dll")
            self.assertFalse((out / "Other.mpq").exists())

    def test_commit_entry_takes_the_raw_file(self):
        dll = b"raw dll"
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp), b"")
            self.write_manifest(root, {"companions": [{"name": "Y", "repo": "o/r", "commit": "abc", "asset": "release/y.dll",
                                                       "sha256": hashlib.sha256(dll).hexdigest(),
                                                       "files": {"release/y.dll": "d2rloader/plugins/y.dll"}}]})
            calls = []
            written = companions.fetch(root, download=lambda *a: calls.append(a) or dll)
            self.assertEqual(calls, [("o/r", "abc", "release/y.dll", True)])
            self.assertEqual(written, ["d2rloader/plugins/y.dll"])  # no "config" key: the default folder is empty/missing
            self.assertEqual((root / "generated/companions/d2rloader/plugins/y.dll").read_bytes(), dll)

    def test_our_configs_replace_the_zip_defaults(self):
        zipped = make_zip({"d2rloader/plugins/x.dll": b"dll", "Other.mpq/data/sfx/a": b"", "config/x.toml": b"theirs"})
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp), zipped)
            manifest = json.loads((root / "companions" / "manifest.json").read_text())
            manifest["companions"][0]["files"]["config/x.toml"] = "d2rloader/config/x.toml"
            self.write_manifest(root, manifest)
            (root / "companions" / "config").mkdir()
            (root / "companions" / "config" / "x.toml").write_text("ours")
            written = companions.fetch(root, download=lambda *a: zipped)
            self.assertEqual((root / "generated/companions/d2rloader/config/x.toml").read_text(), "ours")
            self.assertEqual(written.count("d2rloader/config/x.toml"), 1)

    def test_bare_release_asset_is_one_file(self):
        mpq = b"bare mpq"
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp), b"")
            self.write_manifest(root, {"companions": [{"name": "Z", "repo": "o/r", "tag": "1.0", "asset": "z.mpq",
                                                       "sha256": hashlib.sha256(mpq).hexdigest(),
                                                       "files": {"z.mpq": "d2rloader/plugins/z.mpq"}}]})
            written = companions.fetch(root, download=lambda *a: mpq)
            self.assertEqual(written, ["d2rloader/plugins/z.mpq"])
            self.assertEqual((root / "generated/companions/d2rloader/plugins/z.mpq").read_bytes(), mpq)

    def test_url_entry_downloads_that_url(self):
        zipped = make_zip({"d2rloader/plugins/x.dll": b"hub dll"})
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp), b"")
            self.write_manifest(root, {"companions": [{"name": "H", "url": "https://hub.example.com/releases/1/download",
                                                       "asset": "h.zip", "sha256": hashlib.sha256(zipped).hexdigest(),
                                                       "files": {"d2rloader/plugins/x.dll": "d2rloader/plugins/h.dll"}}]})
            calls = []
            written = companions.fetch(root, download=lambda *a, **k: calls.append((a, k)) or zipped)
            self.assertEqual(calls, [((None, None, "h.zip"), {"url": "https://hub.example.com/releases/1/download"})])
            self.assertIn("d2rloader/plugins/h.dll", written)
            self.assertEqual((root / "generated/companions/d2rloader/plugins/h.dll").read_bytes(), b"hub dll")

    def test_refuses_a_hash_mismatch_or_missing_file(self):
        for zipped, sha, msg in [(make_zip({"d2rloader/plugins/x.dll": b"1", "Other.mpq/data/sfx/a": b""}), "0" * 64,
                                  "SHA-256"),
                                 (make_zip({"d2rloader/plugins/x.dll": b"1"}), None, "no Other.mpq/data/sfx/")]:
            with self.subTest(msg), tempfile.TemporaryDirectory() as tmp:
                root = self.project(Path(tmp), zipped, sha)
                with self.assertRaisesRegex(companions.CompanionError, msg):
                    companions.fetch(root, download=lambda *a: zipped)
                self.assertFalse((root / "generated" / "companions").exists())

    def test_manifest_problems_are_refused(self):
        bad = [({"files": {"a": "../escape.dll"}}, "relative path"), ({"files": {"a": "/abs.dll"}}, "relative path"),
               ({"files": {}}, "files"), ({"sha256": "abc"}, "sha256")]
        for change, msg in bad:
            with self.subTest(msg), tempfile.TemporaryDirectory() as tmp:
                root = self.project(Path(tmp), b"zip")
                manifest = json.loads((root / "companions" / "manifest.json").read_text())
                manifest["companions"][0].update(change)
                self.write_manifest(root, manifest)
                with self.assertRaisesRegex(companions.CompanionError, msg):
                    companions.load_manifest(root)

    def test_zip_entry_cannot_leave_the_mod_folder(self):
        zipped = make_zip({"pack/../../evil.dll": b"x"})
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp), zipped, files={"pack/": "d2rloader/plugins/"})
            with self.assertRaisesRegex(companions.CompanionError, "leave the mod folder"):
                companions.fetch(root, download=lambda *a: zipped)

    def test_backslash_destinations_cannot_escape(self):
        for dst in ["..\\escape.dll", "\\abs.dll", "a\\..\\..\\x", "C:\\abs.dll", "C:abs.dll"]:
            with self.subTest(dst), tempfile.TemporaryDirectory() as tmp:
                root = self.project(Path(tmp), b"zip")
                manifest = json.loads((root / "companions" / "manifest.json").read_text())
                manifest["companions"][0]["files"] = {"a": dst}
                self.write_manifest(root, manifest)
                with self.assertRaisesRegex(companions.CompanionError, "relative path"):
                    companions.load_manifest(root)

    def test_zip_entry_with_backslashes_cannot_leave_the_mod_folder(self):
        zipped = make_zip({"pack/..\\..\\evil.dll": b"x"})
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp), zipped, files={"pack/": "d2rloader/plugins/"})
            with self.assertRaisesRegex(companions.CompanionError, "leave the mod folder"):
                companions.fetch(root, download=lambda *a: zipped)
            self.assertFalse((root / "generated" / "evil.dll").exists())
            self.assertFalse((root / "generated" / "companions").exists())

    def test_bad_filter_table_names_and_sources_are_refused(self):
        bad = [({"filter_tables": ["..\\x"]}, "filter_tables"), ({"filter_tables": ["a/b"]}, "filter_tables"),
               ({"tag": None}, "tag"), ({"repo": None}, "repo"), ({"commit": "abc"}, "exactly one"),
               ({"game": "3.3.1"}, "major.minor")]
        for change, msg in bad:
            with self.subTest(msg), tempfile.TemporaryDirectory() as tmp:
                root = self.project(Path(tmp), b"zip")
                manifest = json.loads((root / "companions" / "manifest.json").read_text())
                for k, v in change.items():
                    if v is None:
                        manifest["companions"][0].pop(k)
                    else:
                        manifest["companions"][0][k] = v
                self.write_manifest(root, manifest)
                with self.assertRaisesRegex(companions.CompanionError, msg):
                    companions.load_manifest(root)
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp), b"zip")
            manifest = json.loads((root / "companions" / "manifest.json").read_text())
            manifest["companions"] = ["nope"]
            self.write_manifest(root, manifest)
            with self.assertRaisesRegex(companions.CompanionError, "object"):
                companions.load_manifest(root)

    def project_manifest_sha(self, root: Path, blob: bytes):
        manifest = json.loads((root / "companions" / "manifest.json").read_text())
        manifest["companions"][0]["sha256"] = hashlib.sha256(blob).hexdigest()
        self.write_manifest(root, manifest)

    def test_corrupt_zip_keeps_the_old_tree_and_leaves_no_temp(self):
        good = make_zip({"d2rloader/plugins/x.dll": b"dll", "Other.mpq/data/sfx/a.flac": b"a"})
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp), good)
            companions.fetch(root, download=lambda *a: good)
            bad = b"not a zip"
            self.project_manifest_sha(root, bad)
            with self.assertRaisesRegex(companions.CompanionError, "BadZipFile"):
                companions.fetch(root, download=lambda *a: bad)
            self.assertTrue((root / "generated" / "companions" / "d2rloader" / "plugins" / "x.dll").is_file())
            self.assertFalse((root / "generated" / "companions.tmp").exists())

    def test_d2rloader_toml_cannot_be_a_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp), b"zip")
            manifest = json.loads((root / "companions" / "manifest.json").read_text())
            manifest["config"] = ["companions/d2rloader.toml"]
            self.write_manifest(root, manifest)
            with self.assertRaisesRegex(companions.CompanionError, "d2rloader.toml"):
                companions.load_manifest(root)
            manifest["config"] = ["companions/config/"]
            self.write_manifest(root, manifest)
            (root / "companions" / "config").mkdir()
            (root / "companions" / "config" / "D2RLoader.toml").write_text("x")
            blob = make_zip({"d2rloader/plugins/x.dll": b"dll", "Other.mpq/data/sfx/a.flac": b"a"})
            self.project_manifest_sha(root, blob)
            with self.assertRaisesRegex(companions.CompanionError, "d2rloader.toml"):
                companions.fetch(root, download=lambda *a: blob)

    def test_game_version_check(self):
        info = "Branch!STRING:0|Active!DEC:1|Version!STRING:0\nus|0|2.9.11111.0\nus|1|3.3.93847.0\n"
        manifest = {"game": "3.3", "companions": [{"name": "A"}, {"name": "B", "game": "3.4"}]}
        warned = []
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp)
            (game / ".build.info").write_text(info)
            self.assertEqual(companions.game_version(game), "3.3")
            companions.check_game(game, {"game": "3.3", "companions": [{"name": "A"}]}, warned.append)
            with self.assertRaisesRegex(companions.CompanionError, r"game is 3\.3.*B \(built for 3\.4\)"):
                companions.check_game(game, manifest, warned.append)
            companions.check_game(game, {"companions": [{"name": "A"}]}, warned.append)  # no game field: no check
            self.assertEqual(warned, [])
            (game / ".build.info").write_text(info.replace("3.3.93847.0", "3.4.12345.0"))
            with self.assertRaisesRegex(companions.CompanionError, "game is 3.4"):
                companions.check_game(game, {"game": "3.3", "companions": [{"name": "A"}]}, warned.append)

    def test_unreadable_game_version_warns_and_goes_on(self):
        warned = []
        with tempfile.TemporaryDirectory() as tmp:
            companions.check_game(Path(tmp), {"game": "3.3", "companions": [{"name": "A"}]}, warned.append)
        self.assertEqual(len(warned), 1)
        self.assertIn("A", warned[0])

    def test_overlay_applies_loader_settings_once_and_keeps_others(self):
        zipped = make_zip({"d2rloader/plugins/x.dll": b"dll", "Other.mpq/data/sfx/a.flac": b"a"})
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp), zipped, loader_settings={"d2rcore.items": {"item_stat_ranges": True}})
            companions.fetch(root, download=lambda *a: zipped)
            mod = root / "game" / "mods" / "Mod"
            toml = mod / "d2rloader" / "config" / "d2rloader.toml"
            toml.parent.mkdir(parents=True)
            toml.write_text('[d2rcore.save_format]\nmode = "extended"')
            companions.overlay(root, mod)
            companions.overlay(root, mod)
            self.assertEqual(toml.read_text(), '[d2rcore.save_format]\nmode = "extended"\n' + ITEM_RANGES)
            self.assertTrue((mod / "d2rloader" / "config" / "filter.json").is_file())
            # the loader's own template: section present, key commented out
            toml.write_text("[d2rcore.items]\n# item_stat_ranges = false\n\n[d2rcore.stash]\n")
            companions.overlay(root, mod)
            self.assertEqual(toml.read_text(), ITEM_RANGES + "# item_stat_ranges = false\n\n[d2rcore.stash]\n")
            # a player's own value stays, and a key of another section does not count
            toml.write_text("[d2rcore.items]\nitem_stat_ranges = false\n")
            companions.overlay(root, mod)
            self.assertEqual(toml.read_text(), "[d2rcore.items]\nitem_stat_ranges = false\n")
            toml.write_text("[d2rcore.other]\nitem_stat_ranges = false\n")
            companions.overlay(root, mod)
            self.assertEqual(toml.read_text(), "[d2rcore.other]\nitem_stat_ranges = false\n" + ITEM_RANGES)

    def test_install_removes_only_dropped_companion_files(self):
        zipped = make_zip({"d2rloader/plugins/x.dll": b"dll", "Other.mpq/data/sfx/a.flac": b"a"})
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp), zipped)
            companions.fetch(root, download=lambda *a: zipped)
            mod = root / "game" / "mods" / "Mod"
            plugins = mod / "d2rloader" / "plugins"
            companions.overlay(root, mod, prune=True)
            (plugins / "foreign.dll").write_bytes(b"other")  # not ours: never touched
            # the manifest drops the companion; a second one stays
            gone_zip = make_zip({"d2rloader/plugins/y.dll": b"y"})
            manifest = json.loads((root / "companions" / "manifest.json").read_text())
            manifest["companions"] = [dict(manifest["companions"][0], asset="y.zip", sha256=hashlib.sha256(gone_zip).hexdigest(),
                                           files={"d2rloader/plugins/y.dll": "d2rloader/plugins/y.dll"})]
            self.write_manifest(root, manifest)
            companions.fetch(root, download=lambda *a: gone_zip)
            self.assertEqual(companions.overlay(root, mod, prune=True),
                             ["Mod.mpq/data/sfx/a.flac", "d2rloader/plugins/x.dll"])
            self.assertEqual(sorted(p.name for p in plugins.iterdir()), ["foreign.dll", "y.dll"])
            self.assertEqual(companions.overlay(root, mod, prune=True), [])
            # without a record (an older install) or without prune (the stager) nothing is deleted
            (plugins / "x.dll").write_bytes(b"old")
            (mod / companions.RECORD).unlink()
            self.assertEqual(companions.overlay(root, mod, prune=True), [])
            self.assertTrue((plugins / "x.dll").is_file())

    def test_overlay_copies_project_files_into_the_mod_folder(self):
        zipped = make_zip({"d2rloader/plugins/x.dll": b"dll", "Other.mpq/data/sfx/a.flac": b"a"})
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp), zipped)
            companions.fetch(root, download=lambda *a: zipped)
            manifest = json.loads((root / "companions" / "manifest.json").read_text())
            manifest["project_files"] = {"companions/x/sig.txt": "{mod}.mpq/data/x/sig.txt"}
            self.write_manifest(root, manifest)
            mod = root / "game" / "mods" / "Mod"
            with self.assertRaises(companions.CompanionError):  # the source is not there yet
                companions.overlay(root, mod)
            (root / "companions" / "x").mkdir()
            (root / "companions" / "x" / "sig.txt").write_text("rows")
            companions.overlay(root, mod)
            self.assertEqual((mod / "Mod.mpq" / "data" / "x" / "sig.txt").read_text(), "rows")

    def test_project_files_must_stay_inside_the_project_and_the_mod_folder(self):
        zipped = make_zip({"d2rloader/plugins/x.dll": b"dll", "Other.mpq/data/sfx/a.flac": b"a"})
        for src, dst in (("../x.txt", "a.txt"), ("a.txt", "../x.txt"), ("a.txt", "C:/x.txt"), ("/a.txt", "a.txt")):
            with tempfile.TemporaryDirectory() as tmp:
                root = self.project(Path(tmp), zipped)
                manifest = json.loads((root / "companions" / "manifest.json").read_text())
                manifest["project_files"] = {src: dst}
                self.write_manifest(root, manifest)
                with self.assertRaises(companions.CompanionError, msg=(src, dst)):
                    companions.load_manifest(root)

    def test_no_loader_settings_leaves_the_config_alone(self):
        zipped = make_zip({"d2rloader/plugins/x.dll": b"dll", "Other.mpq/data/sfx/a.flac": b"a"})
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(Path(tmp), zipped)
            companions.fetch(root, download=lambda *a: zipped)
            mod = root / "game" / "mods" / "Mod"
            companions.overlay(root, mod)
            self.assertFalse((mod / "d2rloader" / "config" / "d2rloader.toml").exists())

    def test_settings_values_are_written_as_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            toml = Path(tmp) / "d2rloader.toml"
            companions.apply_settings(toml, {"a.b": {"on": True, "off": False, "n": 3, "s": 'x"y'}})
            self.assertEqual(toml.read_text(), '[a.b]\non = true\noff = false\nn = 3\ns = "x\\"y"\n')

    def test_filter_tables_union_and_fill(self):
        manifest = {"companions": [{"filter_tables": ["armor", "misc"]}, {}, {"filter_tables": ["misc", "skills"]}]}
        self.assertEqual(companions.filter_tables(manifest), ["armor", "misc", "skills"])
        with tempfile.TemporaryDirectory() as tmp:
            excel = Path(tmp) / "excel"
            excel.mkdir()
            (excel / "armor.txt").write_bytes(b"ours")
            filled = companions.fill_tables(excel, lambda rel: rel.encode(), TABLES)
            self.assertEqual(filled, [t for t in TABLES if t != "armor"])
            self.assertEqual((excel / "armor.txt").read_bytes(), b"ours")
            self.assertEqual((excel / "misc.txt").read_bytes(), b"data/global/excel/misc.txt")
            self.assertEqual(companions.fill_tables(excel, lambda rel: b"", []), [])

    def test_example_manifest_loads(self):
        example = Path(__file__).resolve().parent.parent / "release" / "companions.example.json"
        data = json.loads(example.read_text("utf-8"))
        self.assertEqual(len(companions.filter_tables(data)), 6)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "companions").mkdir()
            (Path(tmp) / "companions" / "manifest.json").write_text(example.read_text("utf-8"))
            self.assertEqual(len(companions.load_manifest(Path(tmp))["companions"]), 4)


if __name__ == "__main__":
    unittest.main()
