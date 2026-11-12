"""Fetch the pinned companion plugins of a mod and install them with it.

    py -3 release/companions.py fetch   [--root PROJECT] [--manifest FILE]
    py -3 release/companions.py install --game DIR [--root PROJECT] [--manifest FILE]

A companion is a community plugin (or its data) that a mod ships next to its own. The manifest, by default
<project>/companions/manifest.json, pins each one by SHA-256 (release.example.companions.json shows the schema):

  fetch downloads each entry (a GitHub release asset; with `commit` in place of `tag`, the file at that path in the
  repo at that commit; with `url` and no `repo`, that URL, such as a D2RLoader Hub download link; a release asset that
  is not a .zip is one file too), refuses one whose SHA-256 differs from the manifest, and unpacks only the files the
  entry lists into the git-ignored <project>/generated/companions/, laid out as the installed mod folder. Then the
  project's own settings for the companions are copied over whatever the zips put there (manifest "config", default
  ["companions/config/"]). No companion binary is ever committed.

  install runs the toolkit's `modkit install`, copies generated/companions/ over <game>/mods/<Name>/, applies each
  entry's `loader_settings` to d2rloader/config/d2rloader.toml and copies the vanilla tables that the entries'
  `filter_tables` name when the build did not ship them (from the game's own files, through modkit.base.Base).

Per-entry options (all optional; nothing about one mod is written into this script):
  files            zip path (or asset path) -> path in the installed mod folder; a key ending in "/" is a folder
  filter_tables    vanilla tables the plugin reads from <mod>.mpq/data/global/excel/ (it logs a missing directory
                   without them); the union over all entries is copied from the game when the build lacks them
  loader_settings  {"section.name": {"key": value}} written into d2rloader.toml unless the key is set already
                   (by the project or by the player); for example {"d2rcore.items": {"item_stat_ranges": true}}

Python 3.12+, standard library only (install also needs modkit, from this toolkit).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable

TOOLKIT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = "companions/manifest.json"
DEFAULT_CONFIG = ["companions/config/"]
USER_AGENT = "d2r-toolkit-companions"


class CompanionError(Exception):
    pass


def github_download(repo: str | None, ref: str | None, asset: str, raw: bool = False, url: str | None = None) -> bytes:
    """A release asset of tag `ref`, with raw the file at path `asset` in the repo at commit `ref`, or the file at url."""
    url = url or (f"https://raw.githubusercontent.com/{repo}/{ref}/{urllib.parse.quote(asset)}" if raw else
                  f"https://github.com/{repo}/releases/download/{urllib.parse.quote(ref)}/{urllib.parse.quote(asset)}")
    # some hosts (a Cloudflare-fronted hub) refuse urllib's default User-Agent with a 403
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as r:
        return r.read()


def load_manifest(root: Path, manifest: Path | None = None) -> dict:
    path = Path(manifest) if manifest else Path(root) / DEFAULT_MANIFEST
    try:
        data = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError) as e:
        raise CompanionError(f"{path}: {e}")
    if not isinstance(data.get("companions"), list):
        raise CompanionError(f"{path}: needs a \"companions\" list")
    for c in data["companions"]:
        name = c.get("name", "?")
        if not isinstance(c.get("files"), dict) or not c["files"]:
            raise CompanionError(f"{name}: needs a non-empty \"files\" map")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", str(c.get("sha256", ""))):
            raise CompanionError(f"{name}: sha256 must be 64 hex characters")
        if not c.get("asset"):
            raise CompanionError(f"{name}: needs an \"asset\"")
        for dst in c["files"].values():
            p = PurePosixPath(dst)
            if p.is_absolute() or ".." in p.parts or re.match(r"^[A-Za-z]:", dst):
                raise CompanionError(f"{name}: {dst!r} must be a relative path inside the mod folder")
    return data


def filter_tables(manifest: dict) -> list[str]:
    """The vanilla tables any entry's `filter_tables` names, in first-seen order."""
    seen: dict[str, None] = {}
    for c in manifest["companions"]:
        for t in c.get("filter_tables", []):
            seen.setdefault(t)
    return list(seen)


def fetch(root: Path, download: Callable[..., bytes] = github_download, manifest: Path | None = None) -> list[str]:
    """Rebuild root/generated/companions/ and return the files written (mod-folder relative)."""
    root = Path(root)
    data = load_manifest(root, manifest)
    dest = root / "generated" / "companions"
    if dest.exists():
        shutil.rmtree(dest)
    written = []
    for c in data["companions"]:
        raw = "commit" in c
        if "url" in c:
            blob = download(None, None, c["asset"], url=c["url"])
        else:
            blob = download(c["repo"], c["commit"], c["asset"], True) if raw else download(c["repo"], c["tag"], c["asset"])
        got = hashlib.sha256(blob).hexdigest()
        if got != c["sha256"].lower():
            shutil.rmtree(dest, ignore_errors=True)
            raise CompanionError(f"{c['asset']}: SHA-256 {got} differs from the manifest")
        if raw or not c["asset"].endswith(".zip"):  # one file: files maps the asset path to its place in the mod folder
            if c["asset"] not in c["files"]:
                shutil.rmtree(dest, ignore_errors=True)
                raise CompanionError(f"{c['asset']}: \"files\" has no entry for the asset itself")
            rel = c["files"][c["asset"]]
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            (dest / rel).write_bytes(blob)
            written.append(rel)
            continue
        zf = zipfile.ZipFile(io.BytesIO(blob))
        names = [n for n in zf.namelist() if not n.endswith("/")]
        for src, dst in c["files"].items():
            # a key ending in / copies the folder's files, else one file
            picked = [n for n in names if n.startswith(src)] if src.endswith("/") else [n for n in names if n == src]
            if not picked:
                shutil.rmtree(dest, ignore_errors=True)
                raise CompanionError(f"{c['asset']}: no {src} in the zip")
            for n in picked:
                rel = dst + n[len(src):] if src.endswith("/") else dst
                if ".." in PurePosixPath(rel).parts:
                    shutil.rmtree(dest, ignore_errors=True)
                    raise CompanionError(f"{c['asset']}: {n} would leave the mod folder")
                (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                (dest / rel).write_bytes(zf.read(n))
                written.append(rel)
    config = dest / "d2rloader" / "config"
    config.mkdir(parents=True, exist_ok=True)
    # the project's settings for the companions, over any default a zip put there
    for spec in data.get("config", DEFAULT_CONFIG):
        p = root / spec
        files = sorted(f for f in p.glob("*") if f.is_file()) if spec.endswith("/") else ([p] if p.is_file() else [])
        for f in files:
            shutil.copy2(f, config / f.name)
            written.append(f"d2rloader/config/{f.name}")
    return list(dict.fromkeys(written))


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    return json.dumps(str(v))


def _section_span(text: str, section: str) -> tuple[int, int] | None:
    """(start of the line after the header, start of the next header or end) of [section], or None."""
    m = re.search(rf"^\[{re.escape(section)}\][ \t]*(?:#.*)?\r?\n?", text, re.M)
    if not m:
        return None
    nxt = re.search(r"^\[", text[m.end():], re.M)
    return m.end(), m.end() + nxt.start() if nxt else len(text)


def apply_settings(toml: Path, settings: dict) -> None:
    """Add `key = value` for each {section: {key: value}} entry that d2rloader.toml does not set already. The loader
    writes its sections with the keys commented out; a new key goes straight under its header."""
    text = toml.read_text("utf-8") if toml.exists() else ""
    for section, keys in settings.items():
        for key, value in keys.items():
            span = _section_span(text, section)
            line = f"{key} = {_toml_value(value)}\n"
            if span and re.search(rf"^\s*{re.escape(key)}\s*=", text[span[0]:span[1]], re.M):
                continue  # set already, by the project or by the player
            if span:
                at = span[0]  # under the header, or under the last key already set in the section
                for m in re.finditer(r"^[ \t]*[A-Za-z0-9_.\"-]+[ \t]*=.*\n?", text[span[0]:span[1]], re.M):
                    at = span[0] + m.end()
                head = text[:at] if text[:at].endswith("\n") else text[:at] + "\n"
                text = head + line + text[at:]
            else:
                text += ("\n" if text and not text.endswith("\n") else "") + f"[{section}]\n{line}"
    toml.parent.mkdir(parents=True, exist_ok=True)
    toml.write_text(text, encoding="utf-8")


def overlay(root: Path, mod_dir: Path, manifest: Path | None = None) -> None:
    """Copy generated/companions/ over an installed mod folder and apply the entries' loader settings."""
    root = Path(root)
    src = root / "generated" / "companions"
    if not src.is_dir():
        raise CompanionError(f"{src} missing: run companions.py fetch")
    shutil.copytree(src, mod_dir, dirs_exist_ok=True)
    merged: dict[str, dict] = {}
    for c in load_manifest(root, manifest)["companions"]:
        for section, keys in c.get("loader_settings", {}).items():
            merged.setdefault(section, {}).update(keys)
    if merged:
        apply_settings(Path(mod_dir) / "d2rloader" / "config" / "d2rloader.toml", merged)


def fill_tables(excel: Path, read: Callable[[str], bytes], tables: list[str]) -> list[str]:
    """Copy each of `tables` missing from excel/ from read("data/global/excel/<t>.txt"); return those copied."""
    missing = [t for t in tables if not (excel / f"{t}.txt").exists()]
    if missing:
        excel.mkdir(parents=True, exist_ok=True)
    for t in missing:
        (excel / f"{t}.txt").write_bytes(read(f"data/global/excel/{t}.txt"))
    return missing


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["fetch", "install"])
    ap.add_argument("--game", type=Path, help="D2R folder for install")
    ap.add_argument("--root", type=Path, default=Path.cwd(), help="the mod project folder (default: the current folder)")
    ap.add_argument("--manifest", type=Path, help=f"the manifest (default: <root>/{DEFAULT_MANIFEST})")
    a = ap.parse_args(argv)
    try:
        if a.command == "fetch":
            print(f"generated/companions rebuilt: {len(fetch(a.root, manifest=a.manifest))} files")
        else:
            if not a.game:
                ap.error("install needs --game")
            sys.path.insert(0, str(TOOLKIT))
            from modkit.install import install
            from modkit.base import Base
            print(install(a.root, a.game))
            name = json.loads((a.root / "mod.json").read_text("utf-8"))["name"]
            overlay(a.root, a.game / "mods" / name, a.manifest)
            tables = filter_tables(load_manifest(a.root, a.manifest))
            excel = a.game / "mods" / name / f"{name}.mpq" / "data" / "global" / "excel"
            filled = fill_tables(excel, Base(a.game).bytes, tables) if tables else []
            if filled:
                print(f"vanilla tables added for the companions: {', '.join(filled)}")
            print(f"companions copied into {a.game / 'mods' / name}")
    except CompanionError as e:
        print(f"companions: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
