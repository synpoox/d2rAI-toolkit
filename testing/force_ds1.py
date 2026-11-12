"""Test-only: pin a level to one DS1 variant in a game slot's INSTALLED lvlprest.txt, so a warp lands on the preset under
test (a level with several DS1 variants rolls one per game).

    MODKIT_RUN=<lane> python testing/force_ds1.py --slot 4 [--project DIR] "Dark Temple Map=DarktempleV2.ds1" 200=v3.ds1
    MODKIT_RUN=<lane> python testing/force_ds1.py --slot 4 darktemplev2.ds1        # a DS1 name alone: the row that holds it
    MODKIT_RUN=<lane> python testing/force_ds1.py --slot 4 --reset

A selector matches lvlprest rows by Name (case-insensitive), by LevelId (a number), or, with no `=`, by DS1 file name.
The DS1 (path or bare file name, either slash) must be one of that row's variants (File1..File<Files>). The row gets
Files=1, File1=<ds1>, File2..File6=0. The first change saves the slot's original as lvlprest.txt.force-ds1.orig next to
it; --reset puts it back. Only the installed slot copy is touched, never a build's out/ folder or a cache, so built data
never sees a forced variant. Reinstalling the slot also undoes it.

The mod folder is read from the project's mod.json (`name`; --project DIR, default the testing config's mod.folder). The
installed file is <slot>/mods/<folder>/<folder>.mpq/data/global/excel/lvlprest.txt. Like slot_install.py it needs the
testing config, the slot lock held by MODKIT_RUN, and the slot's game stopped (D2R reads lvlprest at launch); it refuses
slot 1.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))  # the toolkit root, for modkit
import game_slots  # noqa: E402
import release_install  # noqa: E402
import testing_config as tc  # noqa: E402
from modkit.tsv import Table  # noqa: E402

BACKUP_SUFFIX = ".force-ds1.orig"
COLUMNS = ("Name", "LevelId", "Files", *[f"File{i}" for i in range(1, 7)])


class ForceError(Exception):
    pass


def rel_path(folder: str) -> Path:
    return Path("mods") / folder / f"{folder}.mpq" / "data" / "global" / "excel" / "lvlprest.txt"


def mod_folder(cfg: tc.Config, project: str | None = None) -> str:
    """The mod folder name: the project's mod.json `name`, else the testing config's mod.folder."""
    if not project:
        return cfg.mod_folder()
    try:
        return json.loads(Path(project, "mod.json").read_text("utf-8-sig"))["name"]
    except (OSError, ValueError, KeyError) as e:
        raise ForceError(f"cannot read the mod name from {project}/mod.json: {e}") from e


def read_table(path: Path) -> Table:
    return Table.parse("lvlprest", path.read_bytes().decode("latin-1"))


def norm(ds1: str) -> str:
    return ds1.replace("\\", "/").strip().lower()


def variants(t: Table, row: list[str]) -> list[str]:
    """The DS1s the game can roll for a row: File1..File<Files> (at least File1), without the 0 placeholders."""
    n = min(max(int(row[t.col("Files")] or 0), 1), 6)
    out = [row[t.col(f"File{i}")] for i in range(1, n + 1)]
    return [v for v in out if v and v != "0"]


def _match(t: Table, row: list[str], ds1: str) -> str | None:
    """The row's variant that `ds1` names (full path or bare file name), or None."""
    d = norm(ds1)
    return next((v for v in variants(t, row) if norm(v) == d or norm(v).rsplit("/", 1)[-1] == d), None)


def force(t: Table, selector: str, orig: Table | None = None) -> str:
    """Pin the row `selector` names to its DS1 in table t, in place; returns the report line. `orig` is the slot's
    original table: a DS1 is checked against the row's original variants, so a forced level can be forced again."""
    key, eq, ds1 = selector.partition("=")
    key, ds1 = key.strip(), ds1.strip()
    if not eq:  # a DS1 name alone
        key, ds1 = "", key
    if not ds1:
        raise ForceError(f"'{selector}': want <name or LevelId>=<ds1 file>, or a ds1 file name alone")
    for c in COLUMNS:
        if not t.has_col(c):
            raise ForceError(f"lvlprest.txt has no {c} column")
    name_i, id_i = t.col("Name"), t.col("LevelId")
    if orig is not None and len(orig.rows) != len(t.rows):
        orig = None
    src = {id(r): (orig.rows[i] if orig else r) for i, r in enumerate(t.rows)}  # the row whose variants count
    if not key:
        rows = [r for r in t.rows if _match(t, src[id(r)], ds1)]
    elif key.isdigit():
        rows = [r for r in t.rows if r[id_i] == str(int(key))]
    else:
        rows = [r for r in t.rows if r[name_i].lower() == key.lower()]
    if not rows:
        raise ForceError(f"'{selector}': no lvlprest row matches '{key or ds1}'")
    hit = [r for r in rows if _match(t, src[id(r)], ds1)]
    if not hit:
        have = "; ".join(f"{r[name_i]}: {', '.join(variants(t, src[id(r)])) or 'none'}" for r in rows)
        raise ForceError(f"'{ds1}' is not a variant of '{key}'. Its variants: {have}")
    if len(hit) > 1:
        raise ForceError(f"'{selector}' matches {len(hit)} rows ({', '.join(r[name_i] for r in hit)}); name the row")
    r = hit[0]
    want, before = _match(t, src[id(r)], ds1), variants(t, src[id(r)])
    r[t.col("Files")] = "1"
    r[t.col("File1")] = want
    for i in range(2, 7):
        r[t.col(f"File{i}")] = "0"
    return f"{r[name_i]} (LevelId {r[id_i]}): {len(before)} variants [{', '.join(before)}] -> {want}"


def lvlprest_path(cfg: tc.Config, slot: int, project: str | None = None, owner: str | None = None) -> Path:
    """The slot's installed lvlprest.txt, after the slot guard: not slot 1, the lock held by MODKIT_RUN, no game
    running in the slot (D2R reads lvlprest at launch)."""
    try:
        n = release_install.check_slot(cfg, slot, owner)
    except release_install.ReleaseError as e:
        raise ForceError(str(e)) from e
    return Path(cfg.slot_dir(n)) / rel_path(mod_folder(cfg, project))


def apply(path: Path, selectors: list[str]) -> list[str]:
    if not path.is_file():
        raise ForceError(f"{path} not found: install the slot first")
    t = read_table(path)
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    orig = read_table(backup) if backup.is_file() else None  # already forced: the original row says what may be forced
    report = [force(t, s, orig) for s in selectors]  # raises before anything is written
    if not backup.exists():
        shutil.copyfile(path, backup)
    path.write_bytes(t.text().encode("latin-1"))
    return report


def reset(path: Path) -> str:
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    if not backup.is_file():
        return f"nothing to reset: no {backup.name} beside {path.name}"
    shutil.copyfile(backup, path)
    backup.unlink()
    return f"restored {path}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tc.add_config_arg(ap)
    ap.add_argument("selectors", nargs="*", help="<lvlprest Name or LevelId>=<ds1 file>, or a ds1 file name alone")
    ap.add_argument("--slot", type=int, default=tc.env_slot(), help="game slot number (default MODKIT_SLOT)")
    ap.add_argument("--project", help="mod project folder: its mod.json name is the mod folder (default mod.folder)")
    ap.add_argument("--reset", action="store_true", help="restore the slot's original lvlprest.txt")
    a = ap.parse_args(argv)
    try:
        if a.slot is None:
            raise ForceError("no slot: pass --slot N or set MODKIT_SLOT")
        path = lvlprest_path(tc.load(a.config), a.slot, a.project)
        if a.reset:
            if a.selectors:
                raise ForceError("--reset takes no selectors")
            print(reset(path))
        elif not a.selectors:
            raise ForceError("give at least one selector, or --reset")
        else:
            print("\n".join(apply(path, a.selectors)))
            print(f"wrote {path}\nTest-only: run with --reset when the check is done.")
    except (ForceError, tc.ConfigError, game_slots.SlotError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
