"""Schema 3 for the Resurrected launcher: release-manifest.json and feed.json from release/package_release.py, the checks
that refuse what the launcher would reject, and the draft-first publish of github_release.py --assets with a fake gh.
No network. Run: python -m unittest discover tests"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_release_support import RELEASE_DIR, SEVEN, make_mod, needs_7z  # also puts release/ on sys.path

import github_release as gr  # noqa: E402
import package_release as pr  # noqa: E402
import release_config  # noqa: E402

SCRIPT = str(RELEASE_DIR / "package_release.py")
TOML = "d2rloader/config/d2rloader.toml"
FILTER = "d2rloader/config/filter.json"


def catalog_cfg():
    cfg = release_config.defaults()
    cfg["repos"]["github"] = "someone/my-mod"
    cfg["package"]["preserve"] = [TOML, FILTER]
    cfg["catalog"].update(product_id="mymod", upcoming=["project-09"],
                          required_settings=[{"file": TOML, "key": "d2rcore.save_format.mode", "value": "extended"}])
    return cfg


class CatalogBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.cfg = catalog_cfg()
        self.exe = self.tmp / "D2R.exe"
        self.exe.write_bytes(b"MZ not really the game")
        self.src = make_mod(self.tmp / "src", "MyMod", {"global/excel/armor.txt": b"armor\n", "empty.txt": b""})
        (self.src / FILTER).write_text("{}", encoding="utf-8")

    def generate(self, archive=None):
        """(manifest, manifest bytes, feed) for the fake mod folder; `archive` defaults to a stand-in file."""
        if archive is None:
            archive = self.tmp / "MyMod-1.2.3-alpha.7z"
            archive.write_bytes(b"7z stand-in")
        files = pr.file_list(self.src)
        man = pr.catalog_manifest(self.cfg, "1.2.3-alpha", files, archive, pr.empty_dirs(self.src),
                                  [pr.game_build(self.cfg, self.exe)], "Patch notes.")
        b = pr.json_bytes(man)
        return man, b, pr.catalog_feed(self.cfg, man, b, pr.asset_url(self.cfg, "1.2.3-alpha", pr.CATALOG_MANIFEST))


class GenerationTests(CatalogBase):
    def test_manifest_has_the_launcher_shape(self):
        man, b, feed = self.generate()
        self.assertEqual(pr.catalog_problems(man, feed, b), [])
        self.assertEqual(set(man), pr.MANIFEST_KEYS)
        self.assertNotIn("loader", man)  # link-only loader: no installer pin
        self.assertEqual((man["schema_version"], man["product_id"], man["release_id"], man["status"]),
                         (3, "mymod", "mymod-1.2.3-alpha", "alpha"))
        self.assertEqual(man["install_root"], "mods/MyMod")
        self.assertEqual(man["archive"]["url"],
                         "https://github.com/someone/my-mod/releases/download/v1.2.3-alpha/MyMod-1.2.3-alpha.7z")
        self.assertEqual((man["archive"]["file_count"], man["archive"]["total_size"]),
                         (len(man["files"]), sum(f["size"] for f in man["files"])))
        own = {f["path"]: f["ownership"] for f in man["files"]}
        self.assertEqual({p for p, o in own.items() if o == "shipped_default"}, {TOML, FILTER})
        self.assertEqual(own["MyMod.mpq/data/empty.txt"], "managed")
        self.assertEqual(man["empty_dirs"], ["d2rloader/patches"])
        self.assertEqual(man["compatibility"]["game_builds"], [{
            "build": "3.3.93847", "platform": "windows_x64", "executable": "D2R.exe", "size": self.exe.stat().st_size,
            "sha256": hashlib.sha256(self.exe.read_bytes()).hexdigest()}])
        self.assertEqual(man["compatibility"]["loader_versions"], ["1.3.1-beta"])
        self.assertEqual(man["saves"], {"folder": "MyMod", "save_breaking": False, "incompatibility_notice": None})

    def test_feed_points_at_the_exact_manifest_bytes(self):
        man, b, feed = self.generate()
        self.assertEqual(feed, {"schema_version": 3, "products": [
            {"product_id": "mymod", "availability": "available", "recommended": {
                "release_id": "mymod-1.2.3-alpha",
                "manifest_url": "https://github.com/someone/my-mod/releases/download/v1.2.3-alpha/release-manifest.json",
                "manifest_size": len(b), "manifest_sha256": hashlib.sha256(b).hexdigest()}},
            {"product_id": "project-09", "availability": "upcoming"}]})
        self.assertIn("feed: manifest_size / manifest_sha256 do not match the manifest bytes",
                      pr.catalog_problems(man, feed, b + b" "))

    def test_status_follows_the_version(self):
        self.assertEqual([pr.release_status(v) for v in ("1.0.0", "1.0.0-alpha.2", "1.0.0-beta", "1.0.0-rc1")],
                         ["release", "alpha", "beta", "beta"])

    def test_save_breaking_release_carries_its_notice(self):
        self.cfg["catalog"].update(save_breaking=True, incompatibility_notice="Old characters do not load.")
        man, b, feed = self.generate()
        self.assertEqual(man["saves"]["incompatibility_notice"], "Old characters do not load.")
        self.assertEqual(pr.catalog_problems(man, feed, b), [])
        self.cfg["catalog"]["incompatibility_notice"] = ""
        man, b, feed = self.generate()
        self.assertTrue(any("incompatibility_notice" in p for p in pr.catalog_problems(man, feed, b)))


class RefusalTests(CatalogBase):
    def refused(self, change, expect, feed_change=None):
        man, b, feed = self.generate()
        man = copy.deepcopy(man)
        change(man)
        if feed_change:
            feed_change(feed)
        problems = pr.catalog_problems(man, feed, pr.json_bytes(man) if feed_change is None else b)
        if feed_change is None:  # keep the feed in step so only the change itself is reported
            feed = pr.catalog_feed(self.cfg, man, pr.json_bytes(man), pr.asset_url(self.cfg, "1.2.3-alpha", "release-manifest.json"))
            problems = pr.catalog_problems(man, feed, pr.json_bytes(man))
        self.assertTrue(any(expect in p for p in problems), f"{expect!r} not in {problems}")

    def file(self, man, path):
        return next(f for f in man["files"] if f["path"] == path)

    def test_placeholder_hashes_and_sizes(self):
        armor = "MyMod.mpq/data/global/excel/armor.txt"
        self.refused(lambda m: self.file(m, armor).update(sha256="0" * 64), "placeholder")
        self.refused(lambda m: self.file(m, armor).update(sha256=""), "placeholder")
        self.refused(lambda m: self.file(m, armor).update(sha256="ABC"), "placeholder")
        self.refused(lambda m: self.file(m, armor).update(size=0), "only an empty file has the empty hash")
        self.refused(lambda m: self.file(m, "MyMod.mpq/data/empty.txt").update(size=3), "only an empty file has the empty hash")
        self.refused(lambda m: m["archive"].update(size=0), "archive.size is 0")
        self.refused(lambda m: m["compatibility"]["game_builds"][0].update(sha256=None), "game_builds[0].sha256")

    def test_urls_must_be_public_https(self):
        for url in ("http://github.com/a/b.7z", "https://github.com:8443/a.7z", "https://127.0.0.1/a.7z", "https://localhost/a",
                    "https://intranet/a.7z", "https://user" + "@github.com/a.7z", "https://github.com/a/../b.7z",
                    "https://github.com/a/%2E%2E/b.7z", "https://github.com/a b.7z"):
            self.refused(lambda m: m["archive"].update(url=url), "archive.url")

    def test_unsafe_and_conflicting_paths(self):
        for bad, why in (("../x", "component"), ("/abs", "absolute"), ("C:/x", "drive"), ("a\\b", "backslash"),
                         ("CON.txt", "device"), ("lpt1", "device"), ("x.", "trailing"), ("x ", "trailing"),
                         ("PROGRA~1/x", "8.3"), ("a|b", "forbidden"), ("a//b", "component")):
            self.refused(lambda m: self.file(m, "MyMod.mpq/data/empty.txt").update(path=bad), why)
        self.refused(lambda m: m["files"].append({**m["files"][0], "path": m["files"][0]["path"].upper()}), "duplicate path")
        self.refused(lambda m: m["empty_dirs"].append(TOML), "duplicate path")
        self.refused(lambda m: m["empty_dirs"].append(f"{TOML}/inner"), "lies under")

    def test_counts_must_match_the_files(self):
        self.refused(lambda m: m["archive"].update(file_count=m["archive"]["file_count"] + 1), "archive.file_count")
        self.refused(lambda m: m["archive"].update(total_size=m["archive"]["total_size"] - 1), "archive.total_size")
        self.refused(lambda m: m.update(files=[]), "files is empty")

    def test_no_commands_unknown_keys_or_loader_pin(self):
        self.refused(lambda m: m.update(launch_arguments="-txt"), "argument")
        self.refused(lambda m: m["saves"].update(on_install_hook="x"), "hook")
        self.refused(lambda m: m.update(loader={"installer_version": "v0.1.0"}), "unknown ['loader']")
        self.refused(lambda m: m.update(schemaVersion=2), "unknown ['schemaVersion']")

    def test_settings_point_at_shipped_defaults(self):
        self.refused(lambda m: m["compatibility"]["required_settings"][0].update(file="MyMod.mpq/modinfo.json"),
                     "not a shipped_default")
        self.refused(lambda m: m["saves"].update(loader_save_format={"file": "nope.toml", "key": "k", "value": "v"}),
                     "saves.loader_save_format.file")
        self.refused(lambda m: m["compatibility"]["required_settings"][0].update(key=""), "key is empty")

    def test_identity_and_compatibility_fields(self):
        self.refused(lambda m: m.update(product_id="My Mod"), "product_id")
        self.refused(lambda m: m.update(release_date="2026-13-01"), "release_date")
        self.refused(lambda m: m.update(status="stable"), "status")
        self.refused(lambda m: m.update(min_launcher_version="1.0"), "min_launcher_version")
        self.refused(lambda m: m.update(install_root="MyMod"), "install_root")
        self.refused(lambda m: m.update(release_notes=" "), "release_notes is empty")
        self.refused(lambda m: m["compatibility"].update(game_builds=[]), "game_builds is empty")
        self.refused(lambda m: m["compatibility"].update(loader_versions=["v1.3.1"]), "loader version")
        self.refused(lambda m: m["saves"].update(folder="a/b"), "saves.folder")

    def test_feed_rules(self):
        self.refused(lambda m: None, "upcoming 'project-09' carries",
                     lambda f: f["products"][1].update(recommended=f["products"][0]["recommended"]))
        self.refused(lambda m: None, "feed recommends 'other-1.0.0'",
                     lambda f: f["products"][0]["recommended"].update(release_id="other-1.0.0"))
        self.refused(lambda m: None, "duplicated", lambda f: f["products"].append(dict(f["products"][1])))
        self.refused(lambda m: None, "manifest_url",
                     lambda f: f["products"][0]["recommended"].update(manifest_url="http://github.com/m.json"))

    def test_archive_listing_must_equal_files_and_empty_dirs(self):
        man, _, _ = self.generate()
        files = {f["path"]: f["size"] for f in man["files"]}
        folders = {"d2rloader", "d2rloader/config", "d2rloader/patches", "MyMod.mpq", "MyMod.mpq/data",
                   "MyMod.mpq/data/global", "MyMod.mpq/data/global/excel"}

        def listing(f=files, d=folders, outside=(), top="MyMod"):
            return pr._archive_listing_problems((f, d, list(outside), top), man["files"], man["empty_dirs"], "MyMod")
        self.assertEqual(listing(), [])
        self.assertIn("7z holds stray.txt, which files does not list", listing(dict(files, **{"stray.txt": 1})))
        short = {k: v for k, v in files.items() if k != TOML}
        self.assertIn(f"files lists {TOML}, which the 7z does not hold", listing(short))
        self.assertTrue(any("B in the 7z" in p for p in listing(dict(files, **{TOML: files[TOML] + 1}))))
        self.assertTrue(any("empty folders" in p for p in listing(d=folders - {"d2rloader/patches"})))
        self.assertTrue(any("outside the top folder" in p for p in listing(outside=["x"])))
        self.assertIn("the 7z's top folder is 'Other', install_root names 'MyMod'", listing(top="Other"))

    def test_size_caps(self):
        man, b, feed = self.generate()
        self.assertTrue(any("over the launcher's" in p for p in pr.catalog_problems(man, feed, b + b" " * pr.MAX_MANIFEST)))
        self.assertTrue(any("the feed is" in p for p in
                            pr.catalog_problems(man, feed, b, feed_bytes=b" " * (pr.MAX_FEED + 1))))


@needs_7z
class PackageTests(CatalogBase):
    def write_config(self, **catalog):
        cat = {**self.cfg["catalog"], **catalog, "game_exe": self.exe.as_posix()}
        lines = ['[repos]', 'github = "someone/my-mod"', '[package]', f'preserve = ["{TOML}", "{FILTER}"]', '[catalog]']
        lines += [f"{k} = {json.dumps(v)}" for k, v in cat.items() if not isinstance(v, (list, dict))]
        lines += [f'upcoming = {json.dumps(cat["upcoming"])}',
                  "required_settings = [" + ", ".join(
                      f'{{file = "{s["file"]}", key = "{s["key"]}", value = "{s["value"]}"}}' for s in cat["required_settings"]) + "]"]
        p = self.tmp / "release.toml"
        p.write_text("\n".join(lines).replace("False", "false").replace("True", "true") + "\n", encoding="utf-8")
        notes = self.tmp / "notes.md"
        notes.write_text("Patch notes.\n", encoding="utf-8")
        return ["--config", str(p), "--notes", str(notes)]

    def run_main(self, *args):
        return subprocess.run([sys.executable, "-I", SCRIPT, *args], capture_output=True, text=True, cwd=self.tmp)

    def test_main_writes_a_valid_manifest_and_feed(self):
        out = self.tmp / "dist"
        r = self.run_main(*self.write_config(), "--mod-dir", str(self.src), "--version", "1.2.3-alpha", "--out", str(out))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["MyMod-1.2.3-alpha.7z", "RELEASE_NOTES-1.2.3-alpha.md",
                         "SHA256SUMS", "downloader-manifest.json", "feed.json", "release-manifest.json"])
        b = (out / "release-manifest.json").read_bytes()
        man, feed = json.loads(b), json.loads((out / "feed.json").read_bytes())
        seven = out / "MyMod-1.2.3-alpha.7z"
        self.assertEqual(pr.catalog_problems(man, feed, b, seven), [])
        self.assertEqual((man["archive"]["size"], man["archive"]["sha256"]), (seven.stat().st_size, pr.sha256(seven)))
        self.assertEqual(man["release_notes"], "Patch notes.")
        sums = gr.read_sums(out / "SHA256SUMS")  # exactly the GitHub release assets
        self.assertEqual(sums, {n: pr.sha256(out / n) for n in ("release-manifest.json", "feed.json", seven.name)})
        self.assertEqual(json.loads((out / "downloader-manifest.json").read_text())["schemaVersion"], 2)

    def test_main_refuses_and_writes_nothing(self):
        out = self.tmp / "dist"
        args = self.write_config(required_settings=[{"file": "MyMod.mpq/modinfo.json", "key": "k", "value": "v"}])
        r = self.run_main(*args, "--mod-dir", str(self.src), "--version", "1.2.3", "--out", str(out))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("not a shipped_default", r.stdout)
        self.assertEqual([p.name for p in out.iterdir()], [])
        cfg = self.write_config()
        r = self.run_main(*cfg[:2], "--game-exe", str(self.tmp / "missing.exe"), "--mod-dir", str(self.src),
                          "--version", "1.2.3", "--out", str(out))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("D2R.exe", r.stdout)

    def test_incomplete_build_has_no_launcher_files(self):
        out = self.tmp / "dist"
        r = self.run_main(*self.write_config(), "--mod-dir", str(self.src), "--version", "1.2.3", "--incomplete", "--out", str(out))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((out / "release-manifest.json").exists() or (out / "feed.json").exists())


class FakeGh:
    """Records gh calls; `release download` copies from `served` (default: what was uploaded)."""

    def __init__(self, existing=None, fail=None, latest=""):
        self.calls, self.uploaded, self.existing, self.fail, self.served = [], {}, existing, fail, None
        self.latest = latest

    def __call__(self, args):
        self.calls.append(args)
        verb = " ".join(args[:2])
        ok = lambda out="": subprocess.CompletedProcess(args, 0, out, "")  # noqa: E731
        if verb == self.fail:
            return subprocess.CompletedProcess(args, 1, "", "HTTP 502")
        if verb == "release view" and args[2] == "-R":  # no tag: the Latest release
            return ok(self.latest) if self.latest else subprocess.CompletedProcess(args, 1, "", "release not found")
        if verb == "release view":
            return ok(self.existing) if self.existing is not None else subprocess.CompletedProcess(args, 1, "", "not found")
        if verb == "release upload":
            for p in args[3:args.index("-R")]:
                self.uploaded[Path(p).name] = Path(p).read_bytes()
        if verb == "release download":
            dest = Path(args[args.index("-D") + 1])
            dest.mkdir(parents=True, exist_ok=True)
            for name, data in (self.served or self.uploaded).items():
                (dest / name).write_bytes(data)
        return ok()

    def verbs(self):
        return [" ".join(c[:2]) for c in self.calls]


class PublishBase(CatalogBase):
    """A packaged dist/ (the 7z, release-manifest.json, feed.json, SHA256SUMS) to publish with a fake gh."""

    def setUp(self):
        super().setUp()
        self.dist = self.tmp / "dist"
        self.dist.mkdir()
        mod = pr.stage(self.src, self.tmp / "stage" / "MyMod")
        seven = self.dist / "MyMod-1.2.3.7z"
        pr.write_7z(mod, seven)
        man = pr.catalog_manifest(self.cfg, "1.2.3", pr.file_list(mod), seven, pr.empty_dirs(mod),
                                  [pr.game_build(self.cfg, self.exe)], "Patch notes.")
        b = pr.json_bytes(man)
        (self.dist / "release-manifest.json").write_bytes(b)
        (self.dist / "feed.json").write_bytes(pr.json_bytes(
            pr.catalog_feed(self.cfg, man, b, pr.asset_url(self.cfg, "1.2.3", "release-manifest.json"))))
        (self.dist / "SHA256SUMS").write_text("".join(f"{pr.sha256(self.dist / n)}  {n}\n" for n in
                                                      (seven.name, "release-manifest.json", "feed.json")), encoding="utf-8")
        self.log = []

    def publish(self, gh, dry_run=False, **kw):
        kw.setdefault("skip_launcher_validation", True)
        return gr.publish_assets(self.cfg, "1.2.3", self.dist, dry_run=dry_run, gh=gh, log=self.log.append, **kw)

    def rewrite(self, change):
        """Change the manifest, then make the feed and SHA256SUMS consistent with it again."""
        man = json.loads((self.dist / "release-manifest.json").read_bytes())
        change(man)
        b = pr.json_bytes(man)
        (self.dist / "release-manifest.json").write_bytes(b)
        (self.dist / "feed.json").write_bytes(pr.json_bytes(
            pr.catalog_feed(self.cfg, man, b, pr.asset_url(self.cfg, "1.2.3", "release-manifest.json"))))
        (self.dist / "SHA256SUMS").write_text("".join(f"{pr.sha256(self.dist / n)}  {n}\n" for n in
                                                      ("MyMod-1.2.3.7z", "release-manifest.json", "feed.json")), encoding="utf-8")


@needs_7z
class PublishTests(PublishBase):
    def test_draft_upload_verify_then_public(self):
        gh = FakeGh()
        url = self.publish(gh)
        self.assertEqual(url, "https://github.com/someone/my-mod/releases/tag/v1.2.3")
        self.assertEqual(gh.verbs(), ["release view", "release view", "release create", "release upload", "release download",
                                      "release edit"])
        self.assertIn("--draft", gh.calls[2])
        self.assertNotIn("--prerelease", gh.calls[2])
        self.assertEqual(set(gh.uploaded), {"MyMod-1.2.3.7z", "release-manifest.json", "feed.json", "SHA256SUMS"})
        self.assertEqual(gh.calls[-1][-2:], ["--draft=false", "--latest"])

    def test_bad_download_leaves_the_draft(self):
        gh = FakeGh()
        gh.served = {n: (self.dist / n).read_bytes() for n in ("MyMod-1.2.3.7z", "release-manifest.json", "SHA256SUMS")}
        gh.served["feed.json"] = b"{}"
        with self.assertRaises(gr.PublishFailed) as e:
            self.publish(gh)
        self.assertIn("stays a draft", str(e.exception))
        self.assertNotIn("release edit", gh.verbs())

    def test_failed_upload_leaves_the_draft(self):
        gh = FakeGh(fail="release upload")
        with self.assertRaises(gr.PublishFailed):
            self.publish(gh)
        self.assertNotIn("release edit", gh.verbs())

    def test_a_public_release_is_never_touched(self):
        gh = FakeGh(existing="false")
        with self.assertRaises(gr.PublishFailed) as e:
            self.publish(gh)
        self.assertIn("already has a public release", str(e.exception))
        self.assertEqual(gh.verbs(), ["release view"])

    def test_an_existing_draft_is_reused(self):
        gh = FakeGh(existing="true")
        self.publish(gh)
        self.assertEqual(gh.verbs(), ["release view", "release view", "release upload", "release download", "release edit"])

    def test_dry_run_checks_but_sends_nothing(self):
        gh = FakeGh()
        self.publish(gh, dry_run=True, skip_launcher_validation=False)  # a dry run does not need the validator
        self.assertEqual(gh.verbs(), ["release view", "release view"])  # read-only
        self.assertTrue(any(line.startswith("would run: gh release create v1.2.3") for line in self.log))

    def test_local_problems_stop_before_gh(self):
        (self.dist / "feed.json").write_bytes(b'{"schema_version": 3, "products": []}')
        gh = FakeGh()
        with self.assertRaises(gr.PublishFailed) as e:
            self.publish(gh)
        self.assertIn("sha256 does not match SHA256SUMS", str(e.exception))
        self.assertEqual(gh.calls, [])

    def test_dry_run_refuses_a_public_tag(self):
        with self.assertRaises(gr.PublishFailed):
            self.publish(FakeGh(existing="false"), dry_run=True)

    def test_archive_must_match_the_manifest(self):
        self.rewrite(lambda m: m["archive"].update(size=m["archive"]["size"] + 1))
        with self.assertRaises(gr.PublishFailed) as e:
            self.publish(FakeGh())
        self.assertIn("not archive.size / archive.sha256", str(e.exception))
        self.rewrite(lambda m: m["archive"].update(size=m["archive"]["size"] - 1, sha256="ab" * 32))
        with self.assertRaises(gr.PublishFailed) as e:
            self.publish(FakeGh())
        self.assertIn("not archive.size / archive.sha256", str(e.exception))

    def test_top_folder_must_be_the_install_root(self):
        self.rewrite(lambda m: m.update(install_root="mods/Other"))
        gh = FakeGh()
        with self.assertRaises(gr.PublishFailed) as e:
            self.publish(gh)
        self.assertIn("install_root names 'Other'", str(e.exception))
        self.assertEqual(gh.calls, [])

    def test_sums_must_list_exactly_the_assets(self):
        with open(self.dist / "SHA256SUMS", "a", encoding="utf-8") as f:
            f.write(f"{'ab' * 32}  RELEASE_NOTES-1.2.3.md\n")
        with self.assertRaises(gr.PublishFailed) as e:
            self.publish(FakeGh())
        self.assertIn("SHA256SUMS lists", str(e.exception))

    def test_a_real_run_needs_the_launcher_validator(self):
        with mock.patch.dict(os.environ, {gr.VALIDATOR_ENV: ""}):
            gh = FakeGh()
            with self.assertRaises(gr.PublishFailed) as e:
                self.publish(gh, skip_launcher_validation=False)
        self.assertIn("--skip-launcher-validation", str(e.exception))
        self.assertEqual(gh.calls, [])

    def test_an_older_version_does_not_take_latest(self):
        gh = FakeGh(latest="v1.3.0")
        with self.assertRaises(gr.PublishFailed) as e:
            self.publish(gh)
        self.assertIn("older than the current Latest v1.3.0", str(e.exception))
        self.assertNotIn("release create", gh.verbs())
        self.publish(FakeGh(latest="v1.3.0"), allow_older=True)
        self.publish(FakeGh(latest="v1.2.3-rc1"))  # a pre-release of this version is older

    def test_missing_gh_is_a_clean_error(self):
        with mock.patch.object(subprocess, "run", side_effect=FileNotFoundError("gh")):
            with self.assertRaises(gr.PublishFailed) as e:
                gr.gh_runner(["release", "view"])
        self.assertIn("cannot run gh", str(e.exception))

    def test_the_launcher_validator_can_refuse(self):
        with mock.patch.dict(os.environ, {gr.VALIDATOR_ENV: str(self.tmp / "no-such-validate-release.exe")}):
            with self.assertRaises(gr.PublishFailed) as e:
                self.publish(FakeGh())
        self.assertIn(gr.VALIDATOR_ENV, str(e.exception))


# ------------------------------------------------------------------- one shared catalog feed for every product
FEED_REPO, FEED_TAG = "someone/launcher", "catalog"
FEED_URL = f"https://github.com/{FEED_REPO}/releases/download/{FEED_TAG}/feed.json"


def other_product(release="other-2.0.0"):
    return {"product_id": "other", "availability": "available",
            "recommended": {"release_id": release, "manifest_url": "https://github.com/someone/other/releases/download/"
                            "v2.0.0/release-manifest.json", "manifest_size": 10, "manifest_sha256": "cd" * 32}}


def shared_feed_now(*extra):
    return {"schema_version": 3, "products": [other_product(), *extra,
                                              {"product_id": "project-09", "availability": "upcoming"}]}


class SharedFeedTests(CatalogBase):
    def setUp(self):
        super().setUp()
        self.cfg["catalog"].update(feed_url=FEED_URL, feed_repo=FEED_REPO, feed_tag=FEED_TAG)

    def test_without_a_current_feed_it_is_the_per_release_feed(self):
        man, b, feed = self.generate()
        self.assertEqual(pr.catalog_feed(self.cfg, man, b, "https://x.example.org/m.json", None),
                         pr.catalog_feed(self.cfg, man, b, "https://x.example.org/m.json"))
        self.assertEqual([p["product_id"] for p in feed["products"]], ["mymod", "project-09"])

    def test_merge_keeps_every_other_product(self):
        man, b, _ = self.generate()
        url = pr.asset_url(self.cfg, "1.2.3-alpha", pr.CATALOG_MANIFEST)
        feed = pr.catalog_feed(self.cfg, man, b, url, shared_feed_now())
        self.assertEqual([p["product_id"] for p in feed["products"]], ["other", "mymod", "project-09"])
        self.assertEqual(feed["products"][0], other_product())
        self.assertEqual(pr.catalog_problems(man, feed, b, None, pr.json_bytes(feed)), [])
        # an older release of this product is replaced where it stood
        old = {**other_product("mymod-1.0.0"), "product_id": "mymod"}
        feed = pr.catalog_feed(self.cfg, man, b, url, {"schema_version": 3, "products": [old, other_product()]})
        self.assertEqual([p["product_id"] for p in feed["products"]], ["mymod", "other", "project-09"])
        self.assertEqual(feed["products"][0]["recommended"]["release_id"], "mymod-1.2.3-alpha")
        # an upcoming product becomes available in its place; upcoming is not listed twice
        self.cfg["catalog"]["upcoming"] = ["project-09", "other"]
        feed = pr.catalog_feed(self.cfg, man, b, url, {"schema_version": 3, "products": [
            {"product_id": "mymod", "availability": "upcoming"}, {"product_id": "project-09", "availability": "upcoming"}]})
        self.assertEqual([(p["product_id"], p["availability"]) for p in feed["products"]],
                         [("mymod", "available"), ("project-09", "upcoming"), ("other", "upcoming")])

    def test_read_feed(self):
        self.assertEqual(pr.read_feed(self.tmp / "none.json"), (None, None))
        good = self.tmp / "feed.json"
        good.write_bytes(pr.json_bytes(shared_feed_now()))
        self.assertEqual(pr.read_feed(good), (shared_feed_now(), good.read_bytes()))
        for bad in (b"not json", b'{"schema_version": 3, "products": "x"}',
                    pr.json_bytes({"schema_version": 3, "products": [{"product_id": "a", "availability": "upcoming",
                                                                     "recommended": {}}]})):
            good.write_bytes(bad)
            with self.assertRaises(ValueError):
                pr.read_feed(good)
        import urllib.error

        def gone(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
        self.assertEqual(pr.read_feed(FEED_URL, opener=gone), (None, None))

    def test_config_needs_the_feed_release_with_the_url(self):
        for cat, ok in (({"feed_url": FEED_URL, "feed_repo": FEED_REPO, "feed_tag": FEED_TAG}, True),
                        ({"feed_url": FEED_URL}, False), ({"feed_repo": FEED_REPO, "feed_tag": FEED_TAG}, False),
                        ({"feed_url": "http://x.example.org/feed.json", "feed_repo": FEED_REPO, "feed_tag": FEED_TAG}, False)):
            cfg = release_config.defaults()
            cfg["catalog"].update(cat)
            if ok:
                release_config.validate(cfg)
            else:
                with self.assertRaises(release_config.ConfigError):
                    release_config.validate(cfg)


class SharedFeedPackageTests(CatalogBase):
    write_config, run_main = PackageTests.write_config, PackageTests.run_main

    def test_main_merges_into_the_shared_feed_and_sums_only_the_release_assets(self):
        out, now = self.tmp / "dist", self.tmp / "now.json"
        now.write_bytes(pr.json_bytes(shared_feed_now()))
        args = self.write_config(feed_url=FEED_URL, feed_repo=FEED_REPO, feed_tag=FEED_TAG)
        r = self.run_main(*args, "--mod-dir", str(self.src), "--version", "1.2.3", "--out", str(out), "--feed-in", str(now))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        feed = json.loads((out / "feed.json").read_bytes())
        self.assertEqual([p["product_id"] for p in feed["products"]], ["other", "mymod", "project-09"])
        self.assertEqual(set(gr.read_sums(out / "SHA256SUMS")), {"MyMod-1.2.3.7z", "release-manifest.json"})

    def test_a_bad_current_feed_stops_before_packaging(self):
        out, now = self.tmp / "dist", self.tmp / "now.json"
        now.write_bytes(b"{}")
        args = self.write_config(feed_url=FEED_URL, feed_repo=FEED_REPO, feed_tag=FEED_TAG)
        r = self.run_main(*args, "--mod-dir", str(self.src), "--version", "1.2.3", "--out", str(out), "--feed-in", str(now))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("the shared feed", r.stdout)
        self.assertFalse(out.exists() and any(out.iterdir()))


class SharedGh(FakeGh):
    """FakeGh for two repositories: the product's (someone/my-mod) and the one whose `catalog` release holds the feed."""

    def __init__(self, feed=None, home="false true", **kw):
        super().__init__(**kw)
        self.feed, self.home, self.public = feed, home, False

    def __call__(self, args):
        repo = args[args.index("-R") + 1]
        verb = " ".join(args[:2])
        if repo != FEED_REPO:
            if verb == "release edit":
                self.public = True
            if verb == "release view" and args[2] != "-R" and self.public:
                self.calls.append(args)
                return subprocess.CompletedProcess(args, 0, "false", "")
            return super().__call__(args)
        self.calls.append(args)
        ok = lambda out="": subprocess.CompletedProcess(args, 0, out, "")  # noqa: E731
        if verb == "release view":
            return ok(self.home) if self.home else subprocess.CompletedProcess(args, 1, "", "release not found")
        if verb == "release download":
            if self.feed is None:
                return subprocess.CompletedProcess(args, 1, "", "no assets match the file pattern")
            dest = Path(args[args.index("-D") + 1])
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "feed.json").write_bytes(self.feed)
        if verb == "release upload":
            self.feed = Path(args[3]).read_bytes()
        return ok()

    def feed_calls(self):
        return [" ".join(c[:2]) for c in self.calls if c[c.index("-R") + 1] == FEED_REPO]


@needs_7z
class SharedFeedPublishTests(PublishBase):
    def setUp(self):
        super().setUp()
        self.cfg["catalog"].update(feed_url=FEED_URL, feed_repo=FEED_REPO, feed_tag=FEED_TAG)
        self.rewrite(lambda m: None)
        (self.dist / "SHA256SUMS").write_text("".join(f"{pr.sha256(self.dist / n)}  {n}\n" for n in
                                                      ("MyMod-1.2.3.7z", "release-manifest.json")), encoding="utf-8")

    def rewrite(self, change):
        super().rewrite(change)
        sums = self.dist / "SHA256SUMS"
        sums.write_text("".join(line + "\n" for line in sums.read_text("utf-8").splitlines() if "feed.json" not in line),
                        encoding="utf-8")

    def test_product_release_first_then_the_shared_feed(self):
        gh = SharedGh(feed=pr.json_bytes(shared_feed_now()))
        self.publish(gh)
        self.assertEqual(set(gh.uploaded), {"MyMod-1.2.3.7z", "release-manifest.json", "SHA256SUMS"})  # no feed.json
        verbs = [" ".join(c[:2]) + " " + c[c.index("-R") + 1] for c in gh.calls]
        self.assertLess(verbs.index("release edit someone/my-mod"), verbs.index(f"release upload {FEED_REPO}"))
        feed = json.loads(gh.feed)
        self.assertEqual([p["product_id"] for p in feed["products"]], ["other", "mymod", "project-09"])
        self.assertEqual(feed["products"][0], other_product())
        b = (self.dist / "release-manifest.json").read_bytes()
        self.assertEqual(feed["products"][1]["recommended"]["manifest_sha256"], hashlib.sha256(b).hexdigest())
        upload = next(c for c in gh.calls if c[:2] == ["release", "upload"] and FEED_REPO in c)
        self.assertIn("--clobber", upload)

    def test_the_first_product_starts_the_feed(self):
        gh = SharedGh(feed=None)
        self.publish(gh)
        self.assertEqual([p["product_id"] for p in json.loads(gh.feed)["products"]], ["mymod", "project-09"])

    def test_the_feed_release_must_exist_and_never_be_latest(self):
        for home, why in (("", "create it once"), ("false false", "pre-release"), ("true true", "pre-release")):
            gh = SharedGh(feed=None, home=home)
            with self.assertRaises(gr.PublishFailed) as e:
                gr.publish_feed(self.cfg, "1.2.3", self.dist, gh=gh, log=self.log.append, release_public=False)
            self.assertIn(why, str(e.exception))
            self.assertNotIn("release upload", gh.feed_calls())

    def test_the_feed_never_points_at_a_draft(self):
        gh = SharedGh(feed=None)
        with self.assertRaises(gr.PublishFailed) as e:
            gr.publish_feed(self.cfg, "1.2.3", self.dist, gh=gh, log=self.log.append)
        self.assertIn("is not public", str(e.exception))
        self.assertEqual(gh.feed_calls(), [])

    def test_a_published_release_id_never_changes_in_the_feed(self):
        mine = {**other_product("mymod-1.2.3"), "product_id": "mymod"}
        gh = SharedGh(feed=pr.json_bytes(shared_feed_now(mine)))
        with self.assertRaises(gr.PublishFailed) as e:
            gr.publish_feed(self.cfg, "1.2.3", self.dist, gh=gh, log=self.log.append, release_public=False)
        self.assertIn("never changes", str(e.exception))
        self.assertNotIn("release upload", gh.feed_calls())

    def test_an_older_release_does_not_replace_a_newer_one(self):
        newer = {**other_product("mymod-1.3.0"), "product_id": "mymod"}
        gh = SharedGh(feed=pr.json_bytes(shared_feed_now(newer)))
        with self.assertRaises(gr.PublishFailed) as e:
            gr.publish_feed(self.cfg, "1.2.3", self.dist, gh=gh, log=self.log.append, release_public=False)
        self.assertIn("newer than 1.2.3", str(e.exception))
        self.assertTrue(gr.publish_feed(self.cfg, "1.2.3", self.dist, gh=gh, log=self.log.append, release_public=False, allow_older=True))

    def test_publishing_the_same_feed_again_changes_nothing(self):
        gh = SharedGh(feed=pr.json_bytes(shared_feed_now()))
        self.assertTrue(gr.publish_feed(self.cfg, "1.2.3", self.dist, gh=gh, log=self.log.append, release_public=False))
        self.assertFalse(gr.publish_feed(self.cfg, "1.2.3", self.dist, gh=gh, log=self.log.append, release_public=False))
        self.assertEqual(gh.feed_calls().count("release upload"), 1)

    def test_dry_run_checks_but_sends_nothing(self):
        gh = SharedGh(feed=pr.json_bytes(shared_feed_now()))
        self.publish(gh, dry_run=True, skip_launcher_validation=False)
        self.assertNotIn("release upload", [" ".join(c[:2]) for c in gh.calls])
        self.assertTrue(any("kept: other, project-09" in line for line in self.log), self.log)
        self.assertTrue(any(line.startswith(f"would run: gh release upload {FEED_TAG}") for line in self.log), self.log)


if __name__ == "__main__":
    unittest.main()
