"""Stage a built mod as the installed mod folder, then package it as a player release (issue #7).

    py -3 release/stage.py --game DIR [--root PROJECT] [--version V] [--out dist] [--config release.toml]

Run it after the project's whole build (data merged, `modkit build`, plugins built, companions fetched). It
  1. folds changelog.d/*.md into the changelog in memory and checks the `### <version> (<date>)` section exists,
  2. checks the game image (D2RLoader.exe's PE timestamp against game.image_timestamp, when the config sets one) and the
     item type ids of out/data (plugin-template/tools/item_type_ids.py, unless stage.item_type_check = false),
  3. lays the mod folder out in <out>/.stage-mod/<name>/ (a folder this tool creates and removes, nothing else) as `modkit install` does: out/data, modinfo, loader metadata and
     config, the companions (release/companions.py overlay, the vanilla tables they read from DIR), the built plugins and the
     project's LICENSE/NOTICE/COPYING files (LEGAL_FILES, those that exist) at the mod folder's root,
  4. runs release/package_release.py with the config, and replaces its notes with the changelog section alone (or the --notes / stage.notes file, which also goes into the catalog manifest).
The fragments are deleted only when the whole run succeeded; any failure leaves the changelog and fragments as they were.

Everything a mod decides is in release.toml (see release.example.toml, [stage]): which plugins to ship, where they are
built, whether companions are installed, whether the official D2RLoader.exe of --game is pinned in the catalog.
The version defaults to mod.json's.

--extra-plugin PATH[@SOURCE] (repeatable) ships one more prebuilt plugin DLL from outside the build folder, such as a
sibling project's current build, and adds the line "<name>: <SOURCE>, sha256 <hash>" (SOURCE optional: where it was
built from) to the release notes, so the release stays traceable to that file.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import struct
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
TOOLKIT = HERE.parent
sys.path.insert(0, str(HERE))
import changelog as cl  # noqa: E402
import companions as comp  # noqa: E402
import release_config  # noqa: E402


LEGAL_FILES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "NOTICE", "NOTICE.md", "NOTICE.txt", "COPYING")  # copied when present
STAGE_DIR = ".stage-mod"  # under --out; never a name a project or a user uses for their own files


class ReleaseError(Exception):
    pass


def pe_timestamp(exe: Path) -> int:
    """The PE header's TimeDateStamp of a Windows executable (identifies the game image, not its version label)."""
    with open(exe, "rb") as f:
        head = f.read(4096)
    if head[:2] != b"MZ":
        raise ReleaseError(f"{exe} is not a Windows executable")
    pe = struct.unpack_from("<I", head, 0x3C)[0]
    if head[pe:pe + 4] != b"PE\0\0":
        raise ReleaseError(f"{exe} has no PE header")
    return struct.unpack_from("<I", head, pe + 8)[0]


def check_game_image(cfg: dict, exe: Path) -> None:
    """Refuse a D2RLoader.exe whose image differs from game.image_timestamp: plugins check the loader's image, and the game's
    own D2R.exe on disk is encrypted, so its header says nothing about the engine addresses."""
    want = str(cfg["game"].get("image_timestamp") or "")
    if not want:
        return
    got = pe_timestamp(exe)
    if got != int(want, 0):
        raise ReleaseError(f"{exe} has image timestamp 0x{got:08x}, the config expects {want} (build {cfg['game']['build']}): "
                           "plugins are tied to one game image; use the tested game or update the config after re-checking addresses")


def check_item_types(out_data: Path) -> None:
    """Run the item type id check on the built itemtypes.txt, when there is one."""
    table = out_data / "global" / "excel" / "itemtypes.txt"
    if not table.is_file():
        return
    spec = importlib.util.spec_from_file_location("item_type_ids", TOOLKIT / "plugin-template" / "tools" / "item_type_ids.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    problems = mod.check(mod.read_ids(table.read_text(encoding="latin-1")))
    if problems:
        raise ReleaseError("itemtypes.txt does not keep D2R's item type ids:\n  " + "\n  ".join(problems))


def read_mod_json(root: Path) -> dict:
    """mod.json as a dict; a missing or broken file is a ReleaseError."""
    try:
        mod = json.loads((Path(root) / "mod.json").read_text("utf-8"))
    except (OSError, ValueError) as e:
        raise ReleaseError(f"cannot read {Path(root) / 'mod.json'}: {e}")
    if not isinstance(mod, dict):
        raise ReleaseError(f"{Path(root) / 'mod.json'} is not a JSON object")
    return mod


def check_name(mod: dict, cfg: dict) -> str:
    """mod.json's name as a single plain folder name that equals mod.folder (the folder the release ships)."""
    name = mod.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ReleaseError("mod.json has no name")
    if name in (".", "..") or name != name.strip() or any(c in name for c in "/\\:") or not name.isprintable():
        raise ReleaseError(f"mod.json name {name!r} must be a single plain folder name (no /, \\, : and not . or ..)")
    folder = cfg["mod"]["folder"]
    if name != folder:
        raise ReleaseError(f"mod.json is mod {name!r} but mod.folder is {folder!r}")
    return name


def parse_extra_plugin(spec: str) -> tuple[Path, str]:
    """`PATH` or `PATH@SOURCE` of --extra-plugin as (DLL path, source text)."""
    m = re.fullmatch(r"(.+?\.dll)(?:@(.*))?", spec, flags=re.I | re.S)  # the first `.dll@`: a folder name may hold an @
    p = Path(m.group(1)) if m else Path(spec.partition("@")[0])
    if not m or not p.is_file():
        raise ReleaseError(f"--extra-plugin {spec!r}: no .dll file at {p}")
    return p, (m.group(2) or "").strip()


def extra_plugin_note(dll: Path, source: str) -> str:
    """The release-notes line that records which build of an extra plugin ships: its source, if given, and its SHA-256."""
    where = f"{source}, " if source else ""
    return f"{dll.stem}: {where}sha256 {hashlib.sha256(dll.read_bytes()).hexdigest()}"


def with_loader(text: str, exe: Path) -> str:
    """The release.toml text with catalog.loader_files pointing at `exe` (the official D2RLoader.exe of --game, a machine
    path), pinned at [d2rloader] version. Fails when [catalog] is missing or already sets loader_files."""
    text = text.replace("\r\n", "\n")
    conf = tomllib.loads(text)
    if "catalog" not in conf:
        raise ReleaseError("release.toml has no [catalog] table: stage.loader_from_game needs one")
    if "loader_files" in conf["catalog"]:
        raise ReleaseError("release.toml sets catalog.loader_files and stage.loader_from_game: use one of them")
    version = conf.get("d2rloader", {}).get("version")
    if not version:
        raise ReleaseError("release.toml has no [d2rloader] version to pin the loader at")
    line = f'loader_files = [{{path = "{exe.as_posix()}", version = "{version}"}}]'
    text, n = re.subn(r"^\[catalog\][ \t]*(?:#.*)?$", lambda m: m.group(0) + "\n" + line, text, count=1, flags=re.M)
    if not n:  # [catalog] written as dotted keys or an inline table: no header line to put loader_files under
        raise ReleaseError("release.toml's [catalog] has no plain [catalog] header line: stage.loader_from_game needs one")
    return text


def stage(root: Path, out: Path, cfg: dict, read: Callable[[str], bytes] | None = None,
          extra_plugins: list[Path] = ()) -> Path:
    """Lay out the installed mod folder in out/<name>/ (emptied first), as modkit install and companions install do.
    `extra_plugins` are prebuilt DLLs shipped next to the built ones."""
    root = Path(root)
    s = cfg["stage"]
    mod = read_mod_json(root)
    name = check_name(mod, cfg)  # before anything is deleted: the name is a folder under `out`
    build_dir = root / s["plugin_build_dir"]
    dlls = [build_dir / f"{p}.dll" for p in s["plugins"]]
    names = [d.name.lower() for d in [*dlls, *extra_plugins]]
    for n in sorted({n for n in names if names.count(n) > 1}):
        raise ReleaseError(f"two plugins are named {n}: an extra plugin would overwrite another in the package")
    needed = [root / "out" / "data", *dlls, *extra_plugins]
    if s["companions"]:
        needed.append(root / "generated" / "companions")
    for p in needed:
        if not p.exists():
            raise ReleaseError(f"{p} missing: run the project's build first")
    dest = out / name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(root / "out" / "data", dest / f"{name}.mpq" / "data")
    modinfo = json.dumps({"name": name, "savepath": mod.get("savepath", f"{name}/")}, indent=2)
    for f in (dest / f"{name}.mpq" / "modinfo.json", dest / "modinfo.json"):
        f.write_text(modinfo, encoding="utf-8")
    d2rl = dest / "d2rloader"
    for sub in ("config", "plugins"):
        (d2rl / sub).mkdir(parents=True)
    meta = {"schemaVersion": 1, "metadata": {"name": mod.get("title", name), "modVersion": mod.get("version", ""),
                                              "author": mod.get("author", ""), "description": mod.get("description", ""),
                                              "website": mod.get("website", "")}}
    sys.path.insert(0, str(TOOLKIT))
    from modkit.install import namespace  # this toolkit: one rule for install and stage
    try:
        ns = namespace(mod)  # opts in to D2RLoader string namespaces
    except ValueError as e:
        raise ReleaseError(str(e)) from None
    if ns:
        meta["namespace"] = ns
    (d2rl / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    if mod.get("extendedSaves"):
        (d2rl / "config" / "d2rloader.toml").write_text('[d2rcore.save_format]\nmode = "extended"\n', encoding="utf-8")
    if s["companions"]:
        manifest = root / s["companions_manifest"] if s["companions_manifest"] else None
        comp.overlay(root, dest, manifest)
        tables = comp.filter_tables(comp.load_manifest(root, manifest))
        if tables:
            if read is None:
                raise ReleaseError("the companions read vanilla tables: pass --game")
            comp.fill_tables(dest / f"{name}.mpq" / "data" / "global" / "excel", read, tables)
    for dll in [*dlls, *extra_plugins]:
        shutil.copy2(dll, d2rl / "plugins" / dll.name)
    for f in LEGAL_FILES:  # the package's top folder is the mod folder, so these land at its root, where INSTALL.txt does
        if (root / f).is_file():
            shutil.copy2(root / f, dest / f)
    return dest


def finish_notes(dist: Path, version: str, section: str) -> None:
    """Replace package_release's notes with the changelog section alone, refresh SHA256SUMS.

    Requirements and install steps live in the README, so the release page lists only the changes."""
    notes = dist / f"RELEASE_NOTES-{version}.md"
    if not notes.exists():
        raise ReleaseError(f"package_release wrote no {notes}")
    notes.write_text(section.strip() + "\n", encoding="utf-8", newline="\n")
    sums = dist / "SHA256SUMS"
    names = [line.split("  ", 1)[1] for line in sums.read_text("utf-8").splitlines() if line]
    sums.write_text("".join(f"{hashlib.sha256((dist / n).read_bytes()).hexdigest()}  {n}\n" for n in names),
                    encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", type=Path, required=True, help="D2R folder (game image check, vanilla tables for companions)")
    ap.add_argument("--root", type=Path, default=Path.cwd(), help="the mod project folder (default: the current folder)")
    ap.add_argument("--version", help="release version (default: mod.json's)")
    ap.add_argument("--out", type=Path, help="output folder (default: <root>/<package.dist>)")
    ap.add_argument("--config", type=Path, help="release.toml (default: <root>/release.toml)")
    ap.add_argument("--extra-plugin", action="append", default=[], metavar="PATH[@SOURCE]",
                    help="ship one more prebuilt plugin DLL and record its SHA-256 (and SOURCE) in the notes; repeatable")
    ap.add_argument("--notes", type=Path, metavar="FILE",
                    help="ship this player notes file instead of the changelog section (default: stage.notes, {version} filled in)")
    a = ap.parse_args(argv)
    a.game = a.game.resolve()  # package_release.py runs in the project folder: a relative path would point elsewhere
    root = a.root.resolve()
    config_path = (a.config or root / "release.toml").resolve()
    try:
        cfg = release_config.load(config_path, required=True)
    except release_config.ConfigError as e:
        print(f"release: {e}", file=sys.stderr)
        return 1
    out = (a.out or root / cfg["package"]["dist"]).resolve()
    try:
        return run(a, root, out, config_path, cfg)
    except (cl.ChangelogError, ReleaseError, comp.CompanionError) as e:
        print(f"release: {e}", file=sys.stderr)
        return 1


def run(a, root: Path, out: Path, config_path: Path, cfg: dict) -> int:
    mod_json = read_mod_json(root)
    version = str(a.version or mod_json.get("version") or "").strip().lstrip("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", version):
        raise ReleaseError(f"version {version!r} is not like 1.2.3 or 1.2.3-rc1 (give --version, or set it in mod.json)")
    check_name(mod_json, cfg)
    log = root / cfg["repos"]["changelog"]
    frag = cfg["repos"]["fragments"]
    exe = a.game / "D2R.exe"
    loader = a.game / "D2RLoader.exe"  # the image the plugins check
    extra = [parse_extra_plugin(spec) for spec in a.extra_plugin]
    text, fragments = cl.pending(root, version, cfg["repos"]["changelog"], frag)
    section = cl.notes_section(text, version)  # checked before anything is written or deleted
    a.notes_file = a.notes or (root / cfg["stage"]["notes"].format(version=version) if cfg["stage"]["notes"] else None)
    if a.notes_file:
        if not Path(a.notes_file).is_file():
            raise ReleaseError(f"notes file {a.notes_file} missing")
        section = Path(a.notes_file).read_text("utf-8")  # the section above was still checked to exist
    for dll, source in extra:
        section += "\n\n" + extra_plugin_note(dll, source)
    if loader.is_file():
        check_game_image(cfg, loader)
    elif cfg["game"].get("image_timestamp"):
        raise ReleaseError(f"{loader} missing: the game image cannot be checked")
    if cfg["stage"]["item_type_check"]:
        check_item_types(root / "out" / "data")
    base = []

    def read(rel: str) -> bytes:  # the game storage is opened only when a companion reads vanilla tables
        if not base:
            sys.path.insert(0, str(TOOLKIT))
            from modkit.base import Base  # this toolkit
            base.append(Base(a.game))
        return base[0].bytes(rel)
    work = out / STAGE_DIR  # the tool's own folder: created fresh here, the only thing removed afterwards
    if work.exists():  # left by an interrupted run of this tool
        shutil.rmtree(work)
    work.mkdir(parents=True)
    try:
        return package(a, root, out, config_path, cfg, work, version, section, text, fragments, exe, read,
                       [dll for dll, _ in extra])
    finally:
        shutil.rmtree(work, ignore_errors=True)  # the release assets stay; nothing else under `out` is touched


def package(a, root, out, config_path, cfg, work, version, section, text, fragments, exe, read, extra=()) -> int:
    log = root / cfg["repos"]["changelog"]
    frag = cfg["repos"]["fragments"]
    before = log.read_text("utf-8")
    try:
        mod = stage(root, work, cfg, read, list(extra))
    except OSError as e:  # no game storage, no cache, a locked file
        raise ReleaseError(f"cannot stage the mod folder: {e}")
    folded = bool(fragments)
    if folded:  # package_release reads the changelog, so fold it now; the fragments go only once the release is done
        log.write_text(text, "utf-8", newline="\n")
        print(f"changelog: folded {len(fragments)} fragments from {frag}/")
    done = False
    code = 1
    try:
        try:
            if cfg["stage"]["loader_from_game"]:  # the catalog pins the official loader by hash: a machine path, so a copy
                pinned = work / "release.toml"
                pinned.write_text(with_loader(config_path.read_text("utf-8"), a.game / "D2RLoader.exe"), "utf-8", newline="")
                config_path = pinned
            cmd = [sys.executable, str(HERE / "package_release.py"), "--mod-dir", str(mod), "--version", version,
                   "--config", str(config_path), "--out", str(out)]
            if a.notes_file:
                cmd += ["--notes", str(Path(a.notes_file).resolve())]  # package_release runs in the project folder
            if exe.is_file():
                cmd += ["--game-exe", str(exe)]  # [catalog] (schema 3) pins the game build from it
            code = subprocess.run(cmd, cwd=root).returncode  # its relative paths (changelog, dist) are the project's
            if not code:
                finish_notes(out, version, section)
        except ReleaseError as e:
            print(f"release: {e}", file=sys.stderr)
            code = 1
        done = not code
    finally:
        if folded and not done:  # any failure or interruption leaves the changelog and the fragments as they were
            log.write_text(before, "utf-8", newline="\n")
    if code:
        return code
    for f in fragments:
        f.unlink()
    print(f"notes: {out / f'RELEASE_NOTES-{version}.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
