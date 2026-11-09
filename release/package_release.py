"""Package a finished mod folder as a player release: a .7z for manual installs and the manifest the downloader reads.

The script does not build anything. You give it the finished mod folder (the folder that goes into <D2R>\\mods\\<folder>)
and it writes into dist/:

  <Folder>-<version>.7z        the archive for manual installs: solid LZMA2 7z (-mx7) with the mod folder at the top,
                               no time stamps and fixed file times, so it is reproducible with a given 7-Zip build.
                               7-Zip is required; without it the run stops before it changes anything.
  downloader-manifest.json     schemaVersion 2 for the self-hosted downloader: the release's metadata and every file with
                               size and sha256 (docs/release.md "Release manifest"); publish_release.py uploads it to the
                               download host as releases/<v>/release-manifest.json
  release-manifest.json        with [catalog] set: schema 3 for the Resurrected launcher (see "Schema 3" below)
  feed.json                    with [catalog] set: the schema 3 feed that recommends this release
  RELEASE_NOTES-<version>.md   a skeleton to fill in: requirements and install steps
  SHA256SUMS                   sha256 of the 7z(s), the manifest and the notes; with [catalog] only of the GitHub assets (7z, manifest, feed)
  <Folder>-<version>-nexus.7z  with --nexus: the same mod folder plus <Folder>/INSTALL.txt (install steps for players who
                               download by hand or with a mod manager), for an upload to Nexus Mods (docs/distribution.md)

downloader-manifest.json, schemaVersion 2 (the publisher adds objectsBase and launcher, the server adds archive.path):

  schemaVersion  2                         name         mod.name              version   as given
  pluginVersion  --plugin-version (opt.)   released     date, SOURCE_DATE_EPOCH honoured
  complete       false for --incomplete    modFolder    mod.folder            saveFolder mod.save_folder
  d2r            {build, version[, imageTimestamp]}      the game build the release was made for
  d2rloader      {version, url, size, sha256, signerThumbprint}   the pinned loader (informational: never downloaded)
  launch         {default_mod, launch_arguments}         what the downloader writes into the loader config
  preserve       files a player edits; never overwritten after the first install (package.preserve)
  archive        {format: "7z", name, size, sha256}      the manual download (the server rebuilds it, same bytes)
  emptyDirs      folders that exist but hold no file     fileCount, totalSize   counts over files[]
  files          [{path, size, sha256}] sorted by path   path is relative to the mod folder, "/" separators
  launcherMin    downloader.min_version (opt.)           older downloaders are told to update first

Schema 3 (release-manifest.json and feed.json, written only when catalog.product_id is set; the wire format is the
launcher's docs/specs/release-manifest.md). Everything is checked against the launcher's rules before a file is written,
including the 7z's own entry list against files + empty_dirs; one problem and the run stops with nothing written. The
archive URL is https://github.com/<repos.github>/releases/download/v<version>/<7z>, so publish with
`github_release.py --assets dist` (draft first, verified, then public). Inputs: the [catalog] config, --game-exe (the
real D2R.exe the release was tested with: its size and sha256 go in compatibility.game_builds) and --notes (the patch
notes text; default: the version's section of repos.changelog). An --incomplete build writes neither file.
With catalog.feed_url (one catalog feed shared by several products) feed.json is the shared feed as it is now
(catalog.feed_url, or --feed-in FILE) with this release merged in, every other product kept, and SHA256SUMS covers only
the 7z and the manifest; github_release.py --assets merges it again into the live feed once the release is public.

Nothing else goes in: no test harness files, saves or logs (the run stops if one is in the folder; the patterns are
package.forbidden in the config). The folder you give is never changed: it is copied to dist/stage/ first.

  py -3 release/package_release.py --mod-dir path/to/MyMod --version 1.0.0 [--config release.toml]
        [--plugin build/mymod-core.dll [--plugin-version 1.0.0]] [--game-extract DIR] [--incomplete] [--nexus] [--out dist]
        [--game-exe "C:/Program Files (x86)/Diablo II Resurrected/D2R.exe"] [--notes notes.md]

--plugin DLL        copy a plugin DLL into <mod>/<package.plugin_dir>/ (it is checked: a DLL that contains one of
                    package.plugin_forbidden_strings is refused, and with --plugin-version it must carry that version text)
--game-extract DIR  the game's own files, extracted (DIR/data/... or DIR/...): a mod file that is a byte copy of the
                    same path there is left out of the release, because the game reads its own copy anyway
--incomplete        a CI package without the game data: the manifest says complete=false and the 7z is named
                    <Folder>-<version>-incomplete.7z. Publishing it to the stable channel is refused.
--nexus             also write <Folder>-<version>-nexus.7z: players extract it into <D2R>\\mods\\ and read INSTALL.txt
"""
import argparse
import copy
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_config  # noqa: E402

SCHEMA = 2  # 2: the 7z ("archive") replaced the zip; the downloader installs from it or from the objects
STAMP = (2026, 1, 1, 0, 0, 0)  # the staged files' mtime
# 7z: LZMA2, one solid block, multithreaded. No time stamps go in the archive (-mtm/-mtc/-mta off) and the staged files get
# STAMP as mtime anyway; the same input gives the same bytes with the same 7-Zip build.
SEVENZ_ARGS = ["a", "-t7z", "-m0=lzma2", "-mx=7", "-ms=on", "-mmt=on", "-mtm=off", "-mtc=off", "-mta=off", "-bd", "-y"]
SEVENZ_NAMES = ("7z", "7zz", "7za", "7zr")
NO_7Z = ("no 7-Zip found (Program Files\\7-Zip\\7z.exe, or 7z / 7zz / 7za / 7zr on PATH). A release is a .7z only: install "
         "7-Zip (https://www.7-zip.org; Debian / Ubuntu: apt install 7zip) and run again")

DOWNLOADER_MANIFEST = "downloader-manifest.json"  # schema 2; the host's name for it stays release-manifest.json
CATALOG_MANIFEST = "release-manifest.json"  # schema 3, the launcher's asset name
FEED = "feed.json"
CATALOG_SCHEMA = 3
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
LOADER_PAGE = "https://d2rloader.net/download.html"  # the launcher links here; schema 3 carries no installer pin

FORBIDDEN = re.compile("|".join(f"(?:{p})" for p in release_config.DEFAULT_FORBIDDEN), re.I)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def forbidden_regex(patterns=None):
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.I) if patterns else FORBIDDEN


def forbidden_files(mod: Path, patterns=None) -> list:
    """Paths (relative, '/') in the folder that must not ship. `patterns`: regular expressions, default the built-in list."""
    rx = forbidden_regex(patterns)
    return [p.relative_to(mod).as_posix() for p in sorted(mod.rglob("*")) if p.is_file() and rx.search(p.relative_to(mod).as_posix())]


def file_list(mod: Path) -> list:
    return [{"path": p.relative_to(mod).as_posix(), "size": p.stat().st_size, "sha256": sha256(p)}
            for p in sorted(mod.rglob("*"), key=lambda q: q.relative_to(mod).as_posix()) if p.is_file()]


def empty_dirs(mod: Path) -> list:
    """Folders with nothing in them (for example d2rloader/patches): listed in the manifest, so the server builds the same 7z."""
    return sorted(p.relative_to(mod).as_posix() for p in mod.rglob("*") if p.is_dir() and not any(p.iterdir()))


def find_7z():
    """The 7-Zip command line: 7-Zip\\7z.exe under Program Files, else 7z / 7zz / 7za / 7zr on PATH. None when there is none."""
    for var in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(var)
        exe = Path(base) / "7-Zip" / "7z.exe" if base else None
        if exe and exe.is_file():
            return str(exe)
    for name in SEVENZ_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


def fix_mtimes(mod: Path) -> None:
    """Every file and folder of the staged copy gets STAMP as its mtime."""
    t = time.mktime(STAMP + (0, 0, -1))
    for p in [mod, *mod.rglob("*")]:
        os.utime(p, (t, t))


def write_7z(mod: Path, out: Path, sevenzip=None) -> None:
    """Solid LZMA2 7z of the folder, its own name as the top folder (empty folders kept). Sets the folder's file times to
    STAMP. Raises RuntimeError when there is no 7-Zip or it fails; nothing is left behind then."""
    mod, out = Path(mod), Path(out)
    exe = sevenzip or find_7z()
    if not exe:
        raise RuntimeError(NO_7Z)
    fix_mtimes(mod)
    out.unlink(missing_ok=True)  # `7z a` would add to an existing archive
    r = subprocess.run([exe, *SEVENZ_ARGS, str(out.resolve()), mod.name], cwd=mod.parent, capture_output=True, text=True,
                       errors="replace")
    if r.returncode != 0 or not out.is_file():
        out.unlink(missing_ok=True)
        raise RuntimeError(f"7-Zip failed ({r.returncode}): {(r.stdout + r.stderr).strip()[-600:]}")


def check_release_plugin(dll: Path, version=None, forbidden_strings=()) -> list:
    """Problems of a plugin DLL for a release: none of `forbidden_strings` inside it (a test harness must be compiled
    out), and, when `version` is given, that version text followed by a NUL byte (the plugin carries its own version)."""
    b = Path(dll).read_bytes()
    problems = []
    for s in forbidden_strings:
        if s.encode() in b:
            problems.append(f"{dll} contains {s!r} (a release build must compile the test harness out)")
    if version and version.encode() + b"\0" not in b:
        problems.append(f"{dll} does not carry the version {version}")
    return problems


def drop_game_copies(mod: Path, extract: Path, data_dir: str, keep=()) -> int:
    """Remove mod files that are byte copies of the game's own: same path under `extract` (`extract/data` when it has a
    data folder). `data_dir` is where those files sit inside the mod folder. -> number removed."""
    data = mod.joinpath(*data_dir.split("/"))
    base = extract / "data" if (extract / "data").is_dir() else extract
    if not base.is_dir() or not data.is_dir():
        return 0
    keep = {k.lower() for k in keep}
    n = 0
    for p in sorted(data.rglob("*")):
        rel = p.relative_to(data).as_posix()
        if not p.is_file() or rel.lower() in keep:
            continue
        twin = base.joinpath(*rel.split("/"))
        if twin.is_file() and twin.stat().st_size == p.stat().st_size and twin.read_bytes() == p.read_bytes():
            p.unlink()
            n += 1
    return n


def stage(mod_dir: Path, stage_dir: Path, plugin: Path = None, plugin_dir="d2rloader/plugins") -> Path:
    """Copy the finished mod folder to stage_dir (named like the mod folder), then the plugin DLL in. -> the staged folder."""
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    shutil.copytree(mod_dir, stage_dir)
    if plugin is not None:
        dest = stage_dir.joinpath(*plugin_dir.split("/"))
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(plugin, dest / plugin.name)
    return stage_dir


def archive_name(cfg: dict, version: str, complete=True) -> str:
    return f"{cfg['mod']['folder']}-{version}{'' if complete else '-incomplete'}.7z"


def released() -> str:
    """The packaging date, YYYY-MM-DD; SOURCE_DATE_EPOCH honoured."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    day = datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc).date() if epoch else datetime.date.today()
    return day.isoformat()


def manifest(cfg: dict, version: str, files: list, archive_path: Path, complete: bool, dirs=(), plugin_version="") -> dict:
    """The release manifest, schemaVersion 2. archive_path: the .7z. The downloader installs from the objects
    (docs/release.md), the 7z is the manual download. publish_release.py adds objectsBase and launcher; the server's
    ingest adds archive.path and replaces archive by the 7z it builds."""
    mod, game = cfg["mod"], cfg["game"]
    d2r = {"build": str(game["build"]), "version": game["version"]}
    if game.get("image_timestamp"):
        d2r["imageTimestamp"] = game["image_timestamp"]
    man = {
        "schemaVersion": SCHEMA,
        "name": mod["name"],
        "version": version,
        "released": released(),
        "complete": complete,  # false: an --incomplete build (no game data); not for players
        "d2r": d2r,
        "d2rloader": dict(cfg["d2rloader"]),
        "launch": dict(cfg["launch"]),
        "modFolder": mod["folder"],  # the paths below are relative to <D2R>/mods/<modFolder>/
        "saveFolder": mod["save_folder"],
        "preserve": list(cfg["package"]["preserve"]),
        "archive": {"format": "7z", "name": archive_path.name, "size": archive_path.stat().st_size,
                    "sha256": sha256(archive_path)},  # the manual download
        "emptyDirs": list(dirs),  # folders the 7z holds although no file is in them
        "fileCount": len(files),
        "totalSize": sum(f["size"] for f in files),
        "files": files,
    }
    if plugin_version:
        man["pluginVersion"] = plugin_version
    if cfg["downloader"].get("min_version"):
        man["launcherMin"] = cfg["downloader"]["min_version"]
    return man


# ------------------------------------------------------------------------------------- schema 3 (the Resurrected launcher)
def release_tag(version: str) -> str:
    return f"v{version}"


def asset_url(cfg: dict, version: str, name: str) -> str:
    """Where a GitHub release asset of this version is downloaded from."""
    return f"https://github.com/{cfg['repos']['github']}/releases/download/{release_tag(version)}/{name}"


def release_status(version: str) -> str:
    """alpha for an -alpha version, beta for any other pre-release (-beta, -rc1), release otherwise."""
    pre = version.partition("-")[2].lower()
    return "alpha" if "alpha" in pre else "beta" if pre else "release"


def game_build(cfg: dict, exe: Path) -> dict:
    """compatibility.game_builds entry from the real D2R.exe: its bytes identify the build, not the version label."""
    major_minor = ".".join(str(cfg["game"]["version"]).split(".")[:2])
    return {"build": f"{major_minor}.{cfg['game']['build']}", "platform": "windows_x64", "executable": exe.name,
            "size": exe.stat().st_size, "sha256": sha256(exe)}


def loader_builds(cfg: dict) -> list:
    """compatibility.loader_builds from catalog.loader_files: each official loader file pinned by version and bytes."""
    out = []
    for e in cfg["catalog"]["loader_files"]:
        f = Path(e["path"])
        out.append({"version": e.get("version") or cfg["d2rloader"]["version"], "file": f.name,
                    "size": f.stat().st_size, "sha256": sha256(f)})
    return out


def setting(s: dict) -> dict:
    return {"file": s.get("file", ""), "key": s.get("key", ""), "value": s.get("value", "")}


def previous_defaults(earlier) -> dict:
    """{upper-cased path: [sha256, ...]} of every shipped_default in the earlier published manifests `earlier`: each
    one's own hash and the previous_default_sha256 it carries, so one earlier manifest brings the whole history."""
    out = {}
    for man in earlier:
        for f in man.get("files") or []:
            if f.get("ownership") != "shipped_default":
                continue
            known = out.setdefault(str(f["path"]).upper(), [])
            for h in [*(f.get("previous_default_sha256") or []), f["sha256"]]:
                if h not in known:
                    known.append(h)
    return out


def shipped_file(f: dict, previous: dict) -> dict:
    """A shipped_default files[] entry; previous_default_sha256 lists the earlier releases' other hashes (launcher #134)."""
    prev = [h for h in previous.get(f["path"].upper(), []) if h != f["sha256"]]
    return {**f, "ownership": "shipped_default", **({"previous_default_sha256": prev} if prev else {})}


def catalog_manifest(cfg: dict, version: str, files: list, archive_path: Path, dirs, game_builds: list, notes: str,
                     previous: dict = None) -> dict:
    """The release manifest, schema 3 (the launcher's docs/specs/release-manifest.md). Files in package.preserve are
    shipped_default, every other file is managed. No loader installer pin: the launcher links to LOADER_PAGE.
    `previous`: previous_defaults() of the earlier published manifests, so the launcher tells an older release's
    untouched default from a player edit."""
    mod, cat = cfg["mod"], cfg["catalog"]
    preserve = {p.upper() for p in cfg["package"]["preserve"]}
    previous = previous or {}
    breaking = bool(cat["save_breaking"])
    saves = {"folder": str(mod["save_folder"]).strip("/"), "save_breaking": breaking,
             "incompatibility_notice": (cat["incompatibility_notice"] or "") if breaking else None}
    if cat.get("loader_save_format"):
        saves["loader_save_format"] = setting(cat["loader_save_format"])
    return {
        "schema_version": CATALOG_SCHEMA,
        "product_id": cat["product_id"],
        "release_id": f"{cat['product_id']}-{version}",
        "display_version": version,
        "release_date": released(),
        "status": release_status(version),
        "release_notes": notes,
        "min_launcher_version": cat["min_launcher_version"],
        "install_root": f"mods/{mod['folder']}",
        "archive": {"url": asset_url(cfg, version, archive_path.name), "format": "7z", "size": archive_path.stat().st_size,
                    "sha256": sha256(archive_path), "file_count": len(files), "total_size": sum(f["size"] for f in files)},
        "files": [shipped_file(f, previous) if f["path"].upper() in preserve else {**f, "ownership": "managed"}
                  for f in files],
        "empty_dirs": list(dirs),
        "compatibility": {
            "game_builds": game_builds,
            "loader_versions": list(cat["loader_versions"] or [cfg["d2rloader"]["version"]]),
            "loader_builds": loader_builds(cfg),
            "required_settings": [setting(s) for s in cat["required_settings"]],
        },
        "saves": saves,
    }


def catalog_feed(cfg: dict, man: dict, man_bytes: bytes, manifest_url: str, current: dict = None) -> dict:
    """feed.json, schema 3: this product recommends this release; catalog.upcoming are listed without artifacts.

    `current`: the shared catalog feed as it is now (catalog.feed_url). Every other product keeps its entry and its
    place; this product's entry is replaced where it was (an upcoming product becomes available) or added at the end;
    catalog.upcoming adds the IDs the feed does not list yet. Without it the feed lists only this product and
    catalog.upcoming."""
    mine = {"product_id": man["product_id"], "availability": "available",
            "recommended": {"release_id": man["release_id"], "manifest_url": manifest_url, "manifest_size": len(man_bytes),
                            "manifest_sha256": hashlib.sha256(man_bytes).hexdigest()}}
    products = [copy.deepcopy(p) for p in (current or {}).get("products") or []]
    at = next((i for i, p in enumerate(products) if p.get("product_id") == mine["product_id"]), None)
    if at is None:
        products.insert(next((i for i, p in enumerate(products) if p.get("availability") == "upcoming"), len(products))
                        if current else 0, mine)
    else:
        products[at] = mine
    listed = {p.get("product_id") for p in products}
    products += [{"product_id": p, "availability": "upcoming"} for p in cfg["catalog"]["upcoming"] if p not in listed]
    return {"schema_version": CATALOG_SCHEMA, "products": products}


def shared_feed(cfg: dict) -> bool:
    """True when the products share one catalog feed (catalog.feed_url) instead of a feed.json on each release."""
    return bool(cfg["catalog"].get("feed_url"))


def read_feed(src, opener=None):
    """The shared catalog feed now: (feed dict, its bytes), or (None, None) when it does not exist yet (HTTP 404, or no
    such file). `src`: a local file or an https:// URL. Raises ValueError for a feed the launcher would refuse."""
    src = str(src)
    if src.startswith("https://"):
        import urllib.error
        import urllib.request
        from github_release import USER_AGENT
        try:
            with (opener or urllib.request.urlopen)(urllib.request.Request(src, headers={"User-Agent": USER_AGENT}),
                                                    timeout=60) as r:
                data = r.read(MAX_FEED + 1)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, None
            raise ValueError(f"{src}: HTTP {e.code}")
        except OSError as e:
            raise ValueError(f"{src}: {e}")
    else:
        p = Path(src)
        if not p.is_file():
            return None, None
        data = p.read_bytes()
    if len(data) > MAX_FEED:
        raise ValueError(f"{src}: over the launcher's {MAX_FEED} B")
    try:
        feed = json.loads(data)
    except ValueError as e:
        raise ValueError(f"{src}: not JSON: {e}")
    bad = feed_problems(feed) if isinstance(feed, dict) else ["not a JSON object"]
    if bad:
        raise ValueError(f"{src}: the current feed is not valid: " + "; ".join(bad[:10]))
    return feed, data


def read_manifest(src, opener=None, size=None, sha=None) -> dict:
    """An earlier published release-manifest.json: a local file or an https:// URL. `size`/`sha` (a feed pointer's
    manifest_size/manifest_sha256) must match when given. Raises ValueError when it cannot be read or used."""
    src = str(src)
    if src.startswith("https://"):
        import urllib.request
        from github_release import USER_AGENT
        try:
            with (opener or urllib.request.urlopen)(urllib.request.Request(src, headers={"User-Agent": USER_AGENT}),
                                                    timeout=60) as r:
                data = r.read(MAX_MANIFEST + 1)
        except OSError as e:
            raise ValueError(f"{src}: {e}")
    else:
        try:
            data = Path(src).read_bytes()
        except OSError as e:
            raise ValueError(f"{src}: {e}")
    if len(data) > MAX_MANIFEST:
        raise ValueError(f"{src}: over the launcher's {MAX_MANIFEST} B")
    if (size is not None and len(data) != size) or (sha is not None and hashlib.sha256(data).hexdigest() != sha):
        raise ValueError(f"{src}: not the bytes the feed pins")
    try:
        man = json.loads(data)
    except ValueError as e:
        raise ValueError(f"{src}: not JSON: {e}")
    if not isinstance(man, dict) or not isinstance(man.get("files"), list):
        raise ValueError(f"{src}: not a release manifest")
    return man


def recommended_manifest(feed: dict, product_id: str, opener=None):
    """The manifest the feed recommends for `product_id`, checked against its pointer; None when there is none."""
    for p in (feed or {}).get("products") or []:
        rec = p.get("recommended") if p.get("product_id") == product_id else None
        if rec:
            return read_manifest(rec["manifest_url"], opener, rec["manifest_size"], rec["manifest_sha256"])
    return None


def json_bytes(obj) -> bytes:
    return (json.dumps(obj, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def archive_entries(archive: Path, sevenzip=None):
    """The 7z's entries below its top folder: ({path: size} of the files, {path} of the folders, [entries outside it],
    the top folder's name). Raises RuntimeError when 7-Zip cannot list it."""
    exe = sevenzip or find_7z()
    if not exe:
        raise RuntimeError(NO_7Z)
    r = subprocess.run([exe, "l", "-slt", str(archive)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or "\n----------" not in r.stdout.replace("\r", ""):
        raise RuntimeError(f"7-Zip cannot list {archive} ({r.returncode}): {(r.stdout + r.stderr).strip()[-300:]}")
    files, folders, top, outside = {}, set(), None, []
    for block in r.stdout.replace("\r", "").split("\n----------", 1)[1].split("\n\n"):
        props = dict(ln.split(" = ", 1) for ln in block.splitlines() if " = " in ln)
        if "Path" not in props:
            continue
        path = props["Path"].replace("\\", "/")
        is_dir = props.get("Folder") == "+" or "D" in props.get("Attributes", "").split(" ")[0]
        head, _, rel = path.partition("/")
        top = top or head
        if head != top:
            outside.append(path)
        elif rel and is_dir:
            folders.add(rel)
        elif rel:
            files[rel] = int(props.get("Size") or 0)
    return files, folders, outside, top


# The launcher's rules (src-tauri/src/catalog/ and contract/inventory.rs), so nothing it would reject is written.
IDENT_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
SHA_RE = re.compile(r"[0-9a-f]{64}")
VERSION_RE = re.compile(r"\d+\.\d+\.\d+")
SEMVER_RE = re.compile(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?")
DATE_RE = re.compile(r"\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])")
EXECUTABLE_KEYS = ("command", "cmd", "script", "execute", "shell", "hook", "argument")
RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
MAX_MANIFEST = 8 << 20  # the launcher's read limits
MAX_FEED = 1 << 20
MANIFEST_KEYS = {"schema_version", "product_id", "release_id", "display_version", "release_date", "status", "release_notes",
                 "min_launcher_version", "install_root", "archive", "files", "empty_dirs", "compatibility", "saves"}


def path_problem(p) -> str:
    """Why the launcher's RelativePath would refuse `p` ("" when it is fine)."""
    if not isinstance(p, str) or not p:
        return "empty"
    if "\\" in p or p.startswith("/") or ":" in p:
        return "backslash, absolute or drive path"
    for c in p.split("/"):
        if c in ("", ".", ".."):
            return "empty, . or .. component"
        if any(ch < " " or ch in '<>"|?*' for ch in c):
            return "forbidden character"
        if c[-1] in ". ":
            return "trailing dot or space"
        stem = c.split(".")[0].rstrip().upper()
        if stem in RESERVED or re.fullmatch(r"(COM|LPT)[0-9¹²³]", stem):
            return "Windows device name"
        if re.search(r"~\d", c):
            return "8.3 short-name alias"
    return ""


def url_problem(u) -> str:
    """Why the launcher's HTTPS check would refuse `u` ("" when it is fine)."""
    if not isinstance(u, str) or not u.startswith("https://"):
        return "not https://"
    rest = u[len("https://"):]
    m = re.search(r"[/?#]", rest)
    host, path = (rest[:m.start()], rest[m.start():]) if m else (rest, "")
    host = host.lower()
    if (not host or re.search(r"[@:\[\]]", host) or "." not in host or re.fullmatch(r"[\d.]+", host) or host == "localhost"
            or host.endswith(".localhost") or not re.fullmatch(r"[a-z0-9.-]+", host)):
        return "not a public DNS host name (no port, IP, user info or localhost)"
    if any(ch.isspace() or ord(ch) < 32 or 127 <= ord(ch) < 160 for ch in u):
        return "whitespace or control character"
    path = re.split(r"[?#]", path)[0]
    if "%2e" in path.lower() or any(s in (".", "..") for s in path.split("/")):
        return "dot segment in the path"
    return ""


def executable_keys(v, where="") -> list:
    if isinstance(v, dict):
        return [f"{where}{k}" for k in v if any(b in k.lower() for b in EXECUTABLE_KEYS)] + \
            [x for k, sub in v.items() for x in executable_keys(sub, f"{where}{k}.")]
    if isinstance(v, list):
        return [x for i, sub in enumerate(v) for x in executable_keys(sub, f"{where}[{i}].")]
    return []


def verification_problem(field, size, sha, allow_empty=False) -> str:
    """Sizes and hashes must be real: present, not zero (except an empty file with the empty hash), not all zeros."""
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha) or set(sha) == {"0"}:
        return f"{field}.sha256 {sha!r} is missing, not 64 lower-case hex digits or a placeholder"
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        return f"{field}.size {size!r} is missing"
    if size == 0 and not allow_empty:
        return f"{field}.size is 0"
    if (size == 0) != (sha == EMPTY_SHA256):
        return f"{field}: size {size} with sha256 {sha[:12]}... is a placeholder (only an empty file has the empty hash)"
    return ""


def _setting_problems(where, s, shipped) -> list:
    if not isinstance(s, dict) or set(s) != {"file", "key", "value"}:
        return [f"{where}: must be {{file, key, value}}"]
    bad = []
    if path_problem(s["file"]) or str(s["file"]).upper() not in shipped:
        bad.append(f"{where}.file {s['file']!r} is not a shipped_default file of this release (package.preserve)")
    if not str(s["key"]).strip():
        bad.append(f"{where}.key is empty")
    if not isinstance(s["value"], str):
        bad.append(f"{where}.value must be text")
    return bad


def _inventory_problems(files, dirs) -> tuple:
    """(problems, the shipped_default paths upper-cased) of files[] and empty_dirs."""
    bad, shipped = [], set()
    if not files:
        bad.append("files is empty")
    for i, f in enumerate(files):
        where = f"files[{i}] {f.get('path')!r}"
        if set(f) - {"previous_default_sha256"} != {"path", "size", "sha256", "ownership"}:
            bad.append(f"{where}: keys {sorted(f)}")
        if "previous_default_sha256" in f:
            prev = f["previous_default_sha256"]
            if f.get("ownership") != "shipped_default":
                bad.append(f"{where}: previous_default_sha256 is only for a shipped_default")
            elif not isinstance(prev, list) or not prev:
                bad.append(f"{where}: previous_default_sha256 must be a non-empty list")
            else:
                bad += [f"{where}.previous_default_sha256 {h!r} is not 64 lower-case hex digits or is a placeholder"
                        for h in prev if not isinstance(h, str) or not SHA_RE.fullmatch(h) or set(h) == {"0"}]
        if path_problem(f.get("path")):
            bad.append(f"{where}: {path_problem(f.get('path'))}")
        v = verification_problem(where, f.get("size"), f.get("sha256"), allow_empty=True)
        if v:
            bad.append(v)
        if f.get("ownership") not in ("managed", "shipped_default"):
            bad.append(f"{where}: ownership {f.get('ownership')!r} is not managed or shipped_default")
        elif f["ownership"] == "shipped_default":
            shipped.add(str(f.get("path")).upper())
    bad += [f"empty_dirs {d!r}: {path_problem(d)}" for d in dirs if path_problem(d)]
    folded = [str(f.get("path")).upper() for f in files] + [str(d).upper() for d in dirs]
    seen, dup = set(), set()
    for p in folded:
        (dup if p in seen else seen).add(p)
    bad += [f"duplicate path (ignoring case): {p}" for p in sorted(dup)]
    bad += [f"{p} lies under {p[:i]}, which is a file or an empty dir" for p in folded for i in range(len(p))
            if p[i] == "/" and p[:i] in seen]
    return bad, shipped


def _archive_listing_problems(entries, files, dirs, folder) -> list:
    in7z, folders, outside, top = entries
    bad = [f"7z entry outside the top folder: {p}" for p in outside]
    if top != folder:
        bad.append(f"the 7z's top folder is {top!r}, install_root names {folder!r}")
    want = {f.get("path"): f.get("size") for f in files}
    bad += [f"7z holds {p}, which files does not list" for p in sorted(set(in7z) - set(want))]
    bad += [f"files lists {p}, which the 7z does not hold" for p in sorted(set(want) - set(in7z))]
    bad += [f"{p}: {in7z[p]} B in the 7z, {want[p]} in files" for p in sorted(set(in7z) & set(want)) if in7z[p] != want[p]]
    parents = {q[:i] for q in [*in7z, *folders] for i in range(len(q)) if q[i] == "/"}
    empty = set(folders) - parents
    if empty != set(dirs):
        bad.append(f"the 7z's empty folders {sorted(empty)} are not empty_dirs {sorted(dirs)}")
    return bad


def feed_problems(feed) -> list:
    """Everything the launcher would refuse in a feed on its own, whatever product recommends what. [] = good."""
    return _feed_problems(feed, None, None)


def _feed_problems(feed, man, man_bytes) -> list:
    bad = []
    if set(feed) != {"schema_version", "products"} or feed.get("schema_version") != CATALOG_SCHEMA:
        bad.append(f"feed: must be {{schema_version: {CATALOG_SCHEMA}, products}}")
    if not isinstance(feed.get("products"), list) or not all(isinstance(p, dict) for p in feed["products"]):
        return bad + ["feed: products must be a list of objects"]
    ids = [p.get("product_id") for p in feed.get("products") or []]
    bad += [f"feed: product_id {i!r} is duplicated or not a machine ID" for i in ids
            if ids.count(i) > 1 or not IDENT_RE.fullmatch(str(i))]
    mine = None
    for p in feed.get("products") or []:
        if p.get("availability") == "upcoming":
            if set(p) != {"product_id", "availability"}:
                bad.append(f"feed: upcoming {p.get('product_id')!r} carries {sorted(p)}")
        elif p.get("availability") == "available" and set(p) == {"product_id", "availability", "recommended"}:
            r = p["recommended"]
            if set(r) != {"release_id", "manifest_url", "manifest_size", "manifest_sha256"}:
                bad.append(f"feed: recommended keys {sorted(r)}")
            if url_problem(r.get("manifest_url")):
                bad.append(f"feed: manifest_url {r.get('manifest_url')!r}: {url_problem(r.get('manifest_url'))}")
            v = verification_problem("feed manifest", r.get("manifest_size"), r.get("manifest_sha256"))
            if v:
                bad.append(v)
            if man is not None and p.get("product_id") == man.get("product_id"):
                mine = r
        else:
            bad.append(f"feed: product {p.get('product_id')!r} is neither upcoming nor available with a recommended release")
    if man is None:
        return bad
    if mine is None:
        bad.append(f"feed: does not recommend a release of {man.get('product_id')!r}")
    elif mine.get("release_id") != man.get("release_id"):
        bad.append(f"feed recommends {mine.get('release_id')!r}, the manifest is {man.get('release_id')!r}")
    elif man_bytes is not None and (mine.get("manifest_size"), mine.get("manifest_sha256")) != \
            (len(man_bytes), hashlib.sha256(man_bytes).hexdigest()):
        bad.append("feed: manifest_size / manifest_sha256 do not match the manifest bytes")
    return bad


def catalog_problems(man: dict, feed: dict = None, man_bytes: bytes = None, archive: Path = None, feed_bytes: bytes = None,
                     sevenzip=None) -> list:
    """Everything the launcher would refuse in this manifest, plus the feed and the 7z file itself when given: its size
    and sha256 against archive.size / archive.sha256, its top folder against install_root, its entries against files +
    empty_dirs. [] = good."""
    bad = []
    add = bad.append
    if man_bytes is not None and len(man_bytes) > MAX_MANIFEST:
        add(f"the manifest is {len(man_bytes)} B, over the launcher's {MAX_MANIFEST} B")
    if feed_bytes is not None and len(feed_bytes) > MAX_FEED:
        add(f"the feed is {len(feed_bytes)} B, over the launcher's {MAX_FEED} B")
    if set(man) != MANIFEST_KEYS:
        add(f"manifest keys: missing {sorted(MANIFEST_KEYS - set(man))}, unknown {sorted(set(man) - MANIFEST_KEYS)}")
    bad += [f"command, script, hook or argument key: {k}" for k in executable_keys(man) + executable_keys(feed or {})]
    if man.get("schema_version") != CATALOG_SCHEMA:
        add(f"schema_version {man.get('schema_version')!r} is not {CATALOG_SCHEMA}")
    for k in ("product_id", "release_id"):
        if not IDENT_RE.fullmatch(str(man.get(k, ""))):
            add(f"{k} {man.get(k)!r} must be 1-64 of a-z 0-9 . _ - starting with a letter or digit")
    for k in ("display_version", "release_notes"):
        if not str(man.get(k) or "").strip():
            add(f"{k} is empty")
    if not DATE_RE.fullmatch(str(man.get("release_date", ""))):
        add(f"release_date {man.get('release_date')!r} is not YYYY-MM-DD")
    if man.get("status") not in ("alpha", "beta", "release"):
        add(f"status {man.get('status')!r} is not alpha, beta or release")
    if not VERSION_RE.fullmatch(str(man.get("min_launcher_version", ""))):
        add(f"min_launcher_version {man.get('min_launcher_version')!r} is not MAJOR.MINOR.PATCH")
    root = str(man.get("install_root", ""))
    if path_problem(root) or root.count("/") != 1 or root.split("/")[0].lower() != "mods":
        add(f"install_root {root!r} must be mods/<folder>")

    files, dirs = man.get("files") or [], man.get("empty_dirs") or []
    inv, shipped = _inventory_problems(files, dirs)
    bad += inv

    a = man.get("archive") or {}
    if set(a) != {"url", "format", "size", "sha256", "file_count", "total_size"}:
        add(f"archive keys {sorted(a)}")
    if url_problem(a.get("url")):
        add(f"archive.url {a.get('url')!r}: {url_problem(a.get('url'))}")
    if a.get("format") != "7z":
        add(f"archive.format {a.get('format')!r} is not 7z")
    v = verification_problem("archive", a.get("size"), a.get("sha256"))
    if v:
        add(v)
    if a.get("file_count") != len(files):
        add(f"archive.file_count {a.get('file_count')} but files has {len(files)}")
    total = sum(f["size"] for f in files if isinstance(f.get("size"), int))
    if a.get("total_size") != total or total >= 1 << 64:
        add(f"archive.total_size {a.get('total_size')} but the files add up to {total}")

    c = man.get("compatibility") or {}
    if set(c) != {"game_builds", "loader_versions", "loader_builds", "required_settings"}:
        add(f"compatibility keys {sorted(c)}")
    if not c.get("game_builds"):
        add("compatibility.game_builds is empty")
    for i, g in enumerate(c.get("game_builds") or []):
        where = f"compatibility.game_builds[{i}]"
        if set(g) != {"build", "platform", "executable", "size", "sha256"}:
            add(f"{where}: keys {sorted(g)}")
        if not str(g.get("build") or "").strip():
            add(f"{where}.build is empty")
        if g.get("platform") != "windows_x64":
            add(f"{where}.platform {g.get('platform')!r} is not windows_x64")
        if path_problem(g.get("executable")):
            add(f"{where}.executable {g.get('executable')!r}: {path_problem(g.get('executable'))}")
        v = verification_problem(where, g.get("size"), g.get("sha256"))
        if v:
            add(v)
    if not c.get("loader_versions"):
        add("compatibility.loader_versions is empty")
    bad += [f"loader version {v!r} is not MAJOR.MINOR.PATCH[-prerelease]" for v in c.get("loader_versions") or []
            if not SEMVER_RE.fullmatch(str(v))]
    versions, pinned = list(c.get("loader_versions") or []), set()
    for i, lb in enumerate(c.get("loader_builds") or []):
        where = f"compatibility.loader_builds[{i}]"
        if set(lb) != {"version", "file", "size", "sha256"}:
            add(f"{where}: keys {sorted(lb)}")
        if lb.get("version") not in versions:
            add(f"{where}.version {lb.get('version')!r} is not in compatibility.loader_versions")
        if path_problem(lb.get("file")):
            add(f"{where}.file {lb.get('file')!r}: {path_problem(lb.get('file'))}")
        key = (lb.get("version"), str(lb.get("file")).upper())
        if key in pinned:
            add(f"{where}.file {lb.get('file')!r} is pinned twice for {lb.get('version')!r}")
        pinned.add(key)
        v = verification_problem(where, lb.get("size"), lb.get("sha256"))
        if v:
            add(v)
    if pinned:
        bad += [f"loader version {v!r} has no pinned build in compatibility.loader_builds" for v in versions
                if v not in {p[0] for p in pinned}]
    for i, s in enumerate(c.get("required_settings") or []):
        bad += _setting_problems(f"compatibility.required_settings[{i}]", s, shipped)

    sv = man.get("saves") or {}
    if not {"folder", "save_breaking", "incompatibility_notice"} <= set(sv) <= \
            {"folder", "save_breaking", "incompatibility_notice", "loader_save_format"}:
        add(f"saves keys {sorted(sv)}")
    if path_problem(sv.get("folder")) or "/" in str(sv.get("folder")):
        add(f"saves.folder {sv.get('folder')!r} must be one folder name")
    notice = sv.get("incompatibility_notice")
    if not isinstance(sv.get("save_breaking"), bool) or sv.get("save_breaking") != (notice is not None) or \
            (notice is not None and not str(notice).strip()):
        add("saves.incompatibility_notice must be non-empty text exactly when save_breaking is true, else null")
    if sv.get("loader_save_format") is not None:
        bad += _setting_problems("saves.loader_save_format", sv["loader_save_format"], shipped)

    if archive is not None:
        archive = Path(archive)
        if not archive.is_file():
            add(f"no archive at {archive}")
        else:
            if archive.stat().st_size != a.get("size") or sha256(archive) != a.get("sha256"):
                add(f"{archive.name}: its size / sha256 are not archive.size / archive.sha256")
            try:
                bad += _archive_listing_problems(archive_entries(archive, sevenzip), files, dirs, root.partition("/")[2])
            except RuntimeError as e:
                add(str(e))
    if feed is not None:
        bad += _feed_problems(feed, man, man_bytes)
    return bad


def catalog_inputs(cfg: dict, version: str, game_exe=None, notes_file=None) -> tuple:
    """(game_builds, notes text, problems) for schema 3, checked before the long 7z run."""
    problems, builds, notes = [], [], ""
    cat = cfg["catalog"]
    if not IDENT_RE.fullmatch(str(cat["product_id"])):
        problems.append(f"catalog.product_id {cat['product_id']!r} must be 1-64 of a-z 0-9 . _ -")
    repo = str(cfg["repos"]["github"])
    if "your-name" in repo or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        problems.append(f"repos.github {repo!r} is not the GitHub repository the release goes to")
    exe = Path(game_exe or cat["game_exe"] or "-")
    if not exe.is_file():
        problems.append("schema 3 needs the real D2R.exe the release was tested with: --game-exe or catalog.game_exe")
    else:
        builds = [game_build(cfg, exe)]
    loaders = cat["loader_files"]
    if not loaders:
        problems.append("schema 3 needs the official D2RLoader files to pin: catalog.loader_files")
    problems += [f"catalog.loader_files: no file at {e.get('path')!r}" for e in loaders
                 if not Path(str(e.get("path") or "-")).is_file()]
    if notes_file:
        notes = Path(notes_file).read_text("utf-8").strip()
    else:
        from github_release import changelog_section
        try:
            notes = changelog_section(Path(cfg["repos"]["changelog"]).read_text("utf-8"), version)
        except (OSError, SystemExit) as e:
            problems.append(f"no patch notes: --notes FILE, or a '### {version}' section in {cfg['repos']['changelog']} ({e})")
    if not notes and not problems:
        problems.append("the patch notes are empty")
    return builds, notes, problems


UNPACK_7Z = ("Unpack `{archive}` into `<D2R folder>\\mods\\` so that `<D2R folder>\\mods\\{folder}\\{folder}.mpq\\modinfo.json` "
             "exists\n   (Windows 11 opens .7z files; otherwise use 7-Zip, https://www.7-zip.org).")

NOTES = """# {name} {version}

{name} for Diablo II: Resurrected. TODO: one sentence about what this release is.

## Requirements

- Diablo II: Resurrected **build {build}** (D2R {d2rver}).
- D2RLoader **{loader}** ({loader_url}).

## Install

1. Install D2RLoader {loader} into your D2R folder (build {build}).
2. Run `{exe}` ({site}) and choose **Install** (or **Update**). The mod goes into
   `<D2R folder>\\mods\\{folder}`; nothing else is changed.
3. Make {folder} D2RLoader's default mod (once): in D2RLoader's settings, or with
   `default_mod = "{folder}"` in `<D2R folder>\\d2rloader\\config\\d2rloader.toml`. Then start `D2RLoader.exe`.

By hand (offline), into a D2R folder at build {build} that has D2RLoader {loader}:

1. {unpack}
2. Make {folder} the default mod, as in step 3 above.
3. Start `D2RLoader.exe`. Saves go to `Saved Games\\Diablo II Resurrected\\mods\\{folder}\\`.
   To update by hand, remove `mods\\{folder}\\{folder}.mpq\\data` before unpacking the new release, and keep
   `mods\\{folder}\\d2rloader\\config\\d2rloader.toml` if you edited it.

## Changes

- TODO

## Known issues

- TODO

## Checksums

See SHA256SUMS.
"""


def release_notes(cfg: dict, version: str, archive_name_: str) -> str:
    mod = cfg["mod"]
    return NOTES.format(
        name=mod["name"], folder=mod["folder"], version=version, build=cfg["game"]["build"], d2rver=cfg["game"]["version"],
        loader=cfg["d2rloader"]["version"], loader_url=cfg["d2rloader"]["url"], exe=cfg["downloader"]["exe_name"],
        site=cfg["site"]["url"], unpack=UNPACK_7Z.format(archive=archive_name_, folder=mod["folder"]))


NEXUS_INSTALL = r"""{head}
{rule}

Requirements
- Diablo II: Resurrected {d2rver} (made for build {build}).
- {loader_line}

Install
1. Close the game.
2. Extract this archive into <D2R folder>\mods\ (for example
   C:\Program Files (x86)\Diablo II Resurrected\mods\). Afterwards this file is
   <D2R folder>\mods\{folder}\INSTALL.txt and <D2R folder>\mods\{folder}\{folder}.mpq\modinfo.json exists.
   If you see mods\{folder}\{folder}\, you extracted one folder too deep: move it up one level.
3. {start}

Update
- Delete <D2R folder>\mods\{folder}\{folder}.mpq\data, then extract the new version the same way.
  Keep mods\{folder}\d2rloader\config\d2rloader.toml if you changed it.

Uninstall
- Delete <D2R folder>\mods\{folder}\. Your characters stay in
  Saved Games\Diablo II Resurrected\mods\{folder}\.

Modded games are offline games: do not use the mod on Battle.net.
"""

LOADER_NEEDED = "D2RLoader {loader} ({loader_url}): this mod ships an engine plugin and does not run without it."
LOADER_OPTIONAL = "D2RLoader is not needed: this mod is data only."
START_LOADER = ("Start D2RLoader.exe in your D2R folder. The first time, click the gear on the character screen, set\n"
                "   Default Mod to {folder}, Apply, and start D2RLoader again (its first start builds a cache).")
START_PLAIN = ("Start the game with the arguments -mod {folder} -txt (Battle.net: Game Settings, Additional command\n"
               "   line arguments; Steam: Properties, Launch Options).")


def has_plugin(mod: Path, plugin_dir="d2rloader/plugins") -> bool:
    """True when the staged mod folder holds a plugin DLL, i.e. players need D2RLoader."""
    d = Path(mod).joinpath(*plugin_dir.split("/"))
    return d.is_dir() and any(p.suffix.lower() == ".dll" for p in d.iterdir())


def nexus_install_text(cfg: dict, version: str, plugin: bool) -> str:
    """INSTALL.txt of the Nexus archive (CRLF, for Notepad): requirements, install, update and uninstall steps. It does not
    mention the downloader: Nexus Mods does not allow executables that download updates (docs/distribution.md)."""
    mod, loader = cfg["mod"], cfg["d2rloader"]
    head = f"{mod['name']} {version} for Diablo II: Resurrected"
    text = NEXUS_INSTALL.format(
        head=head, rule="=" * len(head), d2rver=cfg["game"]["version"], build=cfg["game"]["build"], folder=mod["folder"],
        loader_line=(LOADER_NEEDED if plugin else LOADER_OPTIONAL).format(loader=loader["version"], loader_url=loader["url"]),
        start=(START_LOADER if plugin else START_PLAIN).format(folder=mod["folder"]))
    return text.replace("\n", "\r\n")


def nexus_archive_name(cfg: dict, version: str) -> str:
    return f"{cfg['mod']['folder']}-{version}-nexus.7z"


def write_nexus_7z(mod: Path, out: Path, cfg: dict, version: str, plugin_dir="d2rloader/plugins", sevenzip=None) -> None:
    """The Nexus Mods archive: the staged mod folder as the top folder, plus <folder>/INSTALL.txt. The INSTALL.txt is
    removed from the stage again, so the manifest and the main 7z never see it."""
    readme = Path(mod) / "INSTALL.txt"
    readme.write_bytes(nexus_install_text(cfg, version, has_plugin(mod, plugin_dir)).encode("utf-8"))
    try:
        write_7z(mod, out, sevenzip)
    finally:
        readme.unlink(missing_ok=True)


def main(argv=None) -> int:
    cfg = release_config.early_config(argv)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    release_config.add_config_arg(ap)
    ap.add_argument("--mod-dir", type=Path, required=True, help="the finished mod folder (what goes into <D2R>/mods/<folder>)")
    ap.add_argument("--version", required=True, help="release version, e.g. 1.0.0 or 1.0.0-rc1")
    ap.add_argument("--plugin", type=Path, help="a release plugin DLL to copy into the mod folder (package.plugin_dir)")
    ap.add_argument("--plugin-version", default="", help="the plugin's own version: must be inside the DLL; goes in the manifest")
    ap.add_argument("--game-extract", type=Path, help="the game's own extracted files: byte copies are left out")
    ap.add_argument("--incomplete", action="store_true", help="a package without game data (CI): complete=false, not for players")
    ap.add_argument("--nexus", action="store_true", help="also write <Folder>-<version>-nexus.7z with INSTALL.txt (Nexus Mods)")
    ap.add_argument("--out", type=Path, help=f"output folder (default package.dist = {cfg['package']['dist']})")
    ap.add_argument("--game-exe", type=Path, help="schema 3: the real D2R.exe the release was tested with (catalog.game_exe)")
    ap.add_argument("--notes", type=Path, help="schema 3: the patch notes text (default: the version's changelog section)")
    ap.add_argument("--previous-manifest", action="append", default=[], metavar="SRC",
                    help="schema 3: an earlier published release-manifest.json (file or https:// URL), repeatable; its "
                         "shipped defaults' hashes go in previous_default_sha256. The shared feed's recommended "
                         "manifest for this product is always read too")
    ap.add_argument("--feed-in", help="schema 3 with catalog.feed_url: the shared feed as it is now, a file or an https:// "
                                      "URL (default catalog.feed_url); this release is merged into it")
    a = ap.parse_args(argv)

    version = a.version.lstrip("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", version):
        print(f"error: bad version {version!r} (expected 1.2.3 or 1.2.3-rc1)")
        return 1
    folder, pkg = cfg["mod"]["folder"], cfg["package"]
    sevenzip = find_7z()
    if not sevenzip:  # before the long part of the run
        print(f"error: {NO_7Z}")
        return 1
    if not a.mod_dir.is_dir() or not any(a.mod_dir.rglob("*")):
        print(f"error: {a.mod_dir} is not a mod folder with files in it")
        return 1
    if not any(a.mod_dir.glob("*.mpq/modinfo.json")) and not (a.mod_dir / "modinfo.json").is_file():
        print(f"warning: {a.mod_dir} has no <name>.mpq/modinfo.json; D2R will not load it as a mod")
    if a.plugin:
        if not a.plugin.is_file():
            print(f"error: no plugin at {a.plugin}")
            return 1
        problems = check_release_plugin(a.plugin, a.plugin_version or None, pkg["plugin_forbidden_strings"])
        if problems:
            print("\n".join(problems))
            return 1
    catalog = bool(cfg["catalog"]["product_id"]) and not a.incomplete  # an --incomplete build is never recommended
    if catalog:
        builds, catalog_notes, problems = catalog_inputs(cfg, version, a.game_exe, a.notes)
        current = None
        if shared_feed(cfg):  # the shared feed now, before the long part of the run
            try:
                current, _ = read_feed(a.feed_in or cfg["catalog"]["feed_url"])
            except ValueError as e:
                problems.append(f"the shared feed: {e} (--feed-in FILE reads a saved copy)")
            if current is None and not problems:
                print(f"note: no shared feed at {a.feed_in or cfg['catalog']['feed_url']} yet: feed.json starts with this product")
        earlier = []
        try:  # earlier published manifests: what the launcher must not mistake for player edits (launcher #134)
            rec = recommended_manifest(current, cfg["catalog"]["product_id"])
            earlier = [*([rec] if rec else []), *(read_manifest(m) for m in a.previous_manifest)]
        except (ValueError, KeyError) as e:
            problems.append(f"an earlier release manifest: {e}")
        previous = previous_defaults(earlier)
        if problems:
            print("error: schema 3 (catalog):\n  " + "\n  ".join(problems))
            return 1
    elif cfg["catalog"]["product_id"]:
        print("note: --incomplete: no release-manifest.json or feed.json (schema 3) for the launcher")

    out = a.out or Path(pkg["dist"])
    out.mkdir(parents=True, exist_ok=True)
    mod = stage(a.mod_dir, out / "stage" / folder, a.plugin, pkg["plugin_dir"])
    if a.game_extract:
        dropped = drop_game_copies(mod, a.game_extract, pkg["data_dir"].format(folder=folder), pkg["keep_identical"])
        if dropped:
            print(f"left out {dropped} files that are byte copies of the game's own ({a.game_extract})")
    bad = forbidden_files(mod, pkg["forbidden"])
    if bad:
        print("refusing to package test or player files: " + ", ".join(bad[:20]))
        shutil.rmtree(out / "stage")
        return 1

    complete = not a.incomplete
    for old in [*out.glob(f"{folder}-*.7z"), *(out / n for n in (CATALOG_MANIFEST, FEED, DOWNLOADER_MANIFEST, "SHA256SUMS"))]:
        old.unlink(missing_ok=True)  # an earlier release must not sit next to this one
    seven_path = out / archive_name(cfg, version, complete)
    t7 = time.time()
    try:
        write_7z(mod, seven_path, sevenzip)
    except RuntimeError as e:
        print(f"error: {e}")
        shutil.rmtree(out / "stage", ignore_errors=True)
        return 1
    t7 = time.time() - t7
    files = file_list(mod)
    dirs = empty_dirs(mod)
    written = []
    if catalog:  # every launcher rule, the 7z's own listing included, before anything else is written
        cman = catalog_manifest(cfg, version, files, seven_path, dirs, builds, catalog_notes, previous)
        cman_bytes = json_bytes(cman)
        cfeed = catalog_feed(cfg, cman, cman_bytes, asset_url(cfg, version, CATALOG_MANIFEST), current)
        problems = catalog_problems(cman, cfeed, cman_bytes, seven_path, json_bytes(cfeed), sevenzip)
        if problems:
            print("error: the launcher would refuse this release; nothing written:\n  " + "\n  ".join(problems[:40]))
            seven_path.unlink(missing_ok=True)
            shutil.rmtree(out / "stage", ignore_errors=True)
            return 1
        (out / CATALOG_MANIFEST).write_bytes(cman_bytes)
        (out / FEED).write_bytes(json_bytes(cfeed))
        written = [out / CATALOG_MANIFEST, out / FEED]
    sums = [seven_path]
    if a.nexus:
        nexus_path = out / nexus_archive_name(cfg, version)
        try:
            write_nexus_7z(mod, nexus_path, cfg, version, pkg["plugin_dir"], sevenzip)
        except RuntimeError as e:
            print(f"error: {e}")
            shutil.rmtree(out / "stage", ignore_errors=True)
            return 1
        sums.append(nexus_path)
    man_path = out / DOWNLOADER_MANIFEST
    man_path.write_text(json.dumps(manifest(cfg, version, files, seven_path, complete, dirs, a.plugin_version),
                                   indent=1) + "\n", encoding="utf-8", newline="\n")
    notes = out / f"RELEASE_NOTES-{version}.md"
    notes.write_text(release_notes(cfg, version, seven_path.name), encoding="utf-8", newline="\n")
    # with [catalog], SHA256SUMS covers exactly the GitHub release assets (github_release.py --assets uploads those);
    # a shared feed (catalog.feed_url) is not one of them: it lives on its own release and changes with every product
    assets = [seven_path, *written[:1]] if shared_feed(cfg) else [seven_path, *written]
    summed = assets if catalog else [*sums, man_path, notes]
    (out / "SHA256SUMS").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in summed),
                                    encoding="utf-8", newline="\n")
    shutil.rmtree(out / "stage")
    print(f"{seven_path.name}: {len(files)} files, {sum(f['size'] for f in files) / 1e6:.0f} MB unpacked, "
          f"{seven_path.stat().st_size / 1e6:.0f} MB as 7z ({t7:.0f} s); "
          f"{', '.join(p.name for p in (*written, man_path, notes))}, SHA256SUMS"
          f"{', ' + sums[1].name if a.nexus else ''} in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
