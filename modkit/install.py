"""Install a built mod into the game: <game>/mods/<Name>/ (D2R folder mod + D2RLoader files).

    <game>/mods/<Name>/
      <Name>.mpq/modinfo.json         {"name": "<Name>", "savepath": "<Name>/"}  (own save folder)
      <Name>.mpq/data/...             the project's out/data (only files the mod changes)
      modinfo.json                    a copy (D2RLoader's guide layout)
      d2rloader/metadata.json         D2RLoader mod metadata (+ "namespace" when mod.json has one: namespaced strings)
      d2rloader/config/d2rloader.toml [d2rcore.save_format] mode = "extended" when mod.json extendedSaves
      d2rloader/plugins/*.dll         mod.json "plugins" (built D2RLoader plugins; mod-scoped)

On reinstall <Name>.mpq/data is made a copy of out/data writing only the files that changed (sync), so swapping a
test slot between builds takes seconds. Saves live in Saved Games and are never touched. Install only while
the game is closed, and restart the game fully afterwards. Without plugins or extended saves the mod also runs
on plain D2R: D2R.exe -mod <Name> -txt.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def game_running() -> bool:
    out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    return "d2r.exe" in out or "d2rloader.exe" in out


def sync(src: Path, dest: Path) -> int:
    """Make dest a copy of src, writing only the files whose size or modified time differ (robocopy's rule: reading
    both copies to compare costs more than copying) and removing the rest. Returns the files written."""
    want = {p.relative_to(src) for p in src.rglob("*") if p.is_file()}
    dest.mkdir(parents=True, exist_ok=True)
    for p in sorted(dest.rglob("*"), reverse=True):  # deepest first, so a folder is empty once its files are gone
        if p.is_file() and p.relative_to(dest) not in want:
            p.unlink()
        elif p.is_dir() and not any(p.iterdir()):
            p.rmdir()
    written = 0
    for rel in sorted(want):
        s, d = src / rel, dest / rel
        if d.is_file() and (d.stat().st_size, d.stat().st_mtime_ns) == (s.stat().st_size, s.stat().st_mtime_ns):
            continue  # copy2 keeps the time, and modkit build keeps it for the files it copies
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
        written += 1
    return written


def configured_slot(game: Path) -> int | None:
    """The test slot number (2 and up) when `game` is a slot folder of the testing config (testing/README.md), else
    None. No config, or one that does not load, means no slots."""
    import sys
    testing = str(Path(__file__).resolve().parent.parent / "testing")
    if testing not in sys.path:
        sys.path.insert(0, testing)
    try:
        import testing_config as tc
        path = tc.find_config_path()
        n = tc.load(path).slot_of_dir(str(game)) if path else None
    except Exception:  # noqa: BLE001  a broken testing config must not stop a plain install
        return None
    return n if n and n > 1 else None


def install(project: Path, game: Path, savepath: str | None = None, check_running: bool = True) -> str:
    """savepath overrides mod.json's (a test slot keeps its own save folder). check_running=False lets a caller that
    checked only the target folder's game (testing/slot_install.py) install while other copies of the game run."""
    project = Path(project)
    mod = json.loads((project / "mod.json").read_text("utf-8"))
    name = mod["name"]
    src = project / "out" / "data"
    if not src.exists():
        raise FileNotFoundError(f"{src} missing: run modkit build first")
    if not (game / "D2R.exe").exists():
        raise FileNotFoundError(f"{game} is not a D2R folder")
    slot = None if savepath else configured_slot(game)
    if slot:
        raise RuntimeError(f"{game} is test slot {slot}: install with testing/slot_install.py --slot {slot}, which "
                           "keeps the slot's own savepath")
    if check_running and game_running():
        raise RuntimeError("D2R / D2RLoader is running: close the game before installing")
    root = game / "mods" / name
    mpq = root / f"{name}.mpq"
    written = sync(src, mpq / "data")
    modinfo = json.dumps({"name": name, "savepath": savepath or mod.get("savepath", f"{name}/")}, indent=2)
    for target in (mpq / "modinfo.json", root / "modinfo.json"):
        target.write_text(modinfo, encoding="utf-8")

    d2rl = root / "d2rloader"
    for sub in ("config", "plugins", "patches"):
        (d2rl / sub).mkdir(parents=True, exist_ok=True)
    meta = {"schemaVersion": 1,
            "metadata": {"name": mod.get("title", name), "modVersion": mod.get("version", "0.1.0"),
                         "author": mod.get("author", ""), "description": mod.get("description", ""),
                         "website": mod.get("website", "")}}
    if mod.get("namespace"):  # opts in to D2RLoader string namespaces (knowledge/strings.md): top level, by schemaVersion
        meta["namespace"] = mod["namespace"]
    (d2rl / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    plugins = []
    for p in mod.get("plugins", []):
        dll = (project / p).resolve()
        if not dll.exists():
            raise FileNotFoundError(f"plugin {dll} missing: build it first (plugin-template/build.ps1)")
        shutil.copy2(dll, d2rl / "plugins" / dll.name)
        plugins.append(dll.name)
    toml = d2rl / "config" / "d2rloader.toml"
    if mod.get("extendedSaves") and not toml.exists():  # never overwrite a config someone edited
        toml.write_text('[d2rcore.save_format]\nmode = "extended"\n', encoding="utf-8")
    files = sum(1 for p in (mpq / "data").rglob("*") if p.is_file())
    return (f"installed {files} files -> {root} ({written} written, the rest unchanged)"
            + (f"; plugins: {', '.join(plugins)}" if plugins else ""))
