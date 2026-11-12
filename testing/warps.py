"""Warp lines for in-game checks: `cheat goto <levelId>,<x>,<y>` for a DS1 map's reference spots (centre, waypoints,
boss-like monster presets), worked out from the extracted game or mod data, so a check or a person can land on the
preset under test. `warps_doc` makes one markdown doc for a list of levels.

    python testing/warps.py --data DIR --level 144                  # every variant of the level's lvlprest rows
    python testing/warps.py --data DIR --level 144 --ds1 v2.ds1     # one variant
    python testing/warps.py --data DIR --level 144 --level 145 --out warps.md   # a doc, one heading per level
    (--boss-word WORD, repeatable, replaces the default words that mark a monster preset as boss-like)

This module is the generic core. What is specific to one mod stays in that mod's wrapper: the nearest walkable tile
to a spot, the HD-preset filter, and grouping the doc per act. DS1 versions 4 to 18 are read (D2R ships 18).

DIR is a data folder holding global/excel/*.txt and global/tiles/** (an extracted game, or a build's data folder).
`cheat goto` takes absolute world subtile coordinates (knowledge/cheat-commands.md): for a DS1 tile
`x = OffsetX*5 + tileX*5 + 2` (OffsetX, OffsetY from levels.txt), and for an HD preset position `x = OffsetX*5 + hdX/2`.
A level with a negative offset is placed at random by the generator: it has no fixed origin, only in-map tiles. A level
with several DS1 variants rolls one per game: pin it first with testing/force_ds1.py (E10, a separate change).
Standard library only.
"""
from __future__ import annotations

import argparse
import os
import struct
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # the toolkit root, for modkit
from modkit.tsv import Table  # noqa: E402

# Default words that mark a monpreset name as boss-like (substring, lower case); pass your own to replace them.
BOSSY = ("boss", "unique", "diablo", "baal", "mephisto", "andariel", "duriel", "izual", "hephasto", "countess",
         "summoner", "nihlathak", "bloodraven", "radament", "griswold", "smith")


def subtile(offset: int, tile: int) -> int:
    """Absolute subtile coordinate of a DS1 tile: its origin offset (tiles) *5 + tile*5, plus 2 to stand mid-tile."""
    return offset * 5 + tile * 5 + 2


def hd_subtile(offset: int, hd: float) -> int:
    """Absolute subtile coordinate of an HD preset position (10 units per tile, 2 per subtile)."""
    return int(offset * 5 + hd / 2)


def selector(ds1: str) -> str:
    """The force_ds1.py selector of a DS1: its file name, lower case."""
    return ds1.replace("\\", "/").rsplit("/", 1)[-1].lower()


def norm(path: str) -> str:
    return path.replace("\\", "/").strip().lower()


def goto(level: int, x: int | None = None, y: int | None = None) -> str:
    return f"cheat goto {level}" if x is None or y is None else f"cheat goto {level},{x},{y}"


# ------------------------------------------------------------------------------------------------------------- DS1

def ds1_header(data: bytes) -> tuple[int, int, int, int, int, int, int, int]:
    """(version, width, height, act 0-4, tag type, offset of the tile layers, wall layers, floor layers). Width and
    height count tiles. Reads a DS1 as the game's loader does, versions 4 to 18; older ones raise ValueError."""
    version, width, height = struct.unpack_from("<3i", data, 0)
    if version < 4:
        raise ValueError(f"DS1 version {version} not supported (version < 4)")
    o, act, tag = 12, 0, 0
    if version >= 8:
        act = min(struct.unpack_from("<i", data, o)[0], 4)
        o += 4
    if version >= 10:
        tag = struct.unpack_from("<i", data, o)[0]
        o += 4
    if version >= 3:
        files = struct.unpack_from("<i", data, o)[0]
        o += 4
        for _ in range(files):
            o = data.index(b"\0", o) + 1
    if 9 <= version <= 13:
        o += 8
    walls, floors = 1, 1
    if version >= 4:
        walls = struct.unpack_from("<i", data, o)[0]
        o += 4
        if version >= 16:
            floors = struct.unpack_from("<i", data, o)[0]
            o += 4
    return version, width + 1, height + 1, act, tag, o, walls, floors


def object_list(data: bytes) -> tuple[int, int, int, int]:
    """(act 0-4, offset of the object count, object count, bytes per object)."""
    version, width, height, act, tag, o, walls, floors = ds1_header(data)
    o += (2 * walls + floors + 1 + (tag in (1, 2))) * width * height * 4
    if version < 2:
        return act, o, 0, 0
    return act, o, struct.unpack_from("<i", data, o)[0], 20 if version > 5 else 16


def read_objects(data: bytes) -> list[tuple[int, int, int, int]]:
    """A DS1's objects: (type, id, x, y), x and y in subtiles of the DS1 (5 per tile)."""
    _act, at, count, size = object_list(data)
    return [struct.unpack_from("<4i", data, at + 4 + k * size) for k in range(count)]


def object_classes(objpreset: Table) -> dict[tuple[int, int], str]:
    """objpreset.txt: (act, object id) -> class name, as the waypoint lookup reads it. Columns: index, act, class."""
    return {(int(r[1]), int(r[0])): r[2] for r in objpreset.rows if r[0].isdigit() and r[1].isdigit()}


def monster_places(monpreset: Table) -> dict[int, list[str]]:
    """monpreset.txt: act -> the preset names in index order. Columns: act, name."""
    out: dict[int, list[str]] = {}
    for r in monpreset.rows:
        if r[0].isdigit():
            out.setdefault(int(r[0]), []).append(r[1])
    return out


def reference_spots(data: bytes, classes: dict[tuple[int, int], str],
                    places: dict[int, list[str]] | None = None,
                    boss_words: tuple[str, ...] = BOSSY) -> list[tuple[str, int, int]]:
    """A DS1's reference spots as (label, x, y), x and y in subtiles of the DS1 (add OffsetX*5 / OffsetY*5 for the
    world): the centre tile's middle, then in object order each waypoint and, when `places` (act -> monpreset names)
    is given, each monster preset whose name holds one of `boss_words`. Objects keep their exact subtile."""
    _v, w, h, dact, *_ = ds1_header(data)
    spots = [("centre", (w // 2) * 5 + 2, (h // 2) * 5 + 2)]
    for kind, oid, x, y in read_objects(data):
        if kind == 2 and "waypoint" in classes.get((dact + 1, oid), "").lower():
            spots.append(("waypoint", x, y))
        if places is not None and kind == 1 and oid < len(places.get(dact + 1, [])) and any(
                s in places[dact + 1][oid].lower() for s in boss_words):
            spots.append((f"monster preset {places[dact + 1][oid]}", x, y))
    return spots


# ----------------------------------------------------------------------------------------------------- a data folder

def excel(data_dir: Path, name: str) -> Table:
    return Table.parse(name, (Path(data_dir) / "global" / "excel" / f"{name}.txt").read_bytes().decode("latin-1"))


def level_origin(levels: Table, level: int) -> tuple[int, int]:
    """(OffsetX, OffsetY) of a level in levels.txt."""
    row = levels.find(str(level), "Id")
    if row is None:
        raise ValueError(f"levels.txt has no level {level}")
    return int(levels.get(row, "OffsetX") or 0), int(levels.get(row, "OffsetY") or 0)


def level_files(lvlprest: Table, level: int) -> list[str]:
    """Every DS1 file the level's lvlprest rows can roll (File1..File<Files>, without the 0 placeholders)."""
    out = []
    for r in lvlprest.rows:
        if r[lvlprest.col("LevelId")] != str(level):
            continue
        n = min(max(int(r[lvlprest.col("Files")] or 0), 1), 6)
        out += [r[lvlprest.col(f"File{i}")] for i in range(1, n + 1) if r[lvlprest.col(f"File{i}")] not in ("", "0")]
    return out


def ds1_warp_lines(level: int, ox: int, oy: int, data: bytes, classes, places=None,
                   boss_words: tuple[str, ...] = BOSSY) -> list[str]:
    """The text lines for one DS1: size, then a goto line per reference spot (in-map tiles when the origin is random)."""
    _v, w, h, *_ = ds1_header(data)
    fixed = ox >= 0 and oy >= 0
    lines = [f"{w}x{h} tiles"]
    seen = set()
    for label, x, y in reference_spots(data, classes, places, boss_words):
        if (x, y) in seen:
            continue
        seen.add((x, y))
        if fixed:
            lines.append(f"{label} (tile {x // 5},{y // 5}, subtile {x},{y}): {goto(level, ox * 5 + x, oy * 5 + y)}")
        else:
            lines.append(f"{label}: tile {x // 5},{y // 5} (in-map; origin unknown)")
    lines.append(f"entry: {goto(level)}")
    return lines


def level_warps(data_dir: Path, level: int, only: str | None = None,
                boss_words: tuple[str, ...] = BOSSY) -> list[str]:
    """Report lines for every DS1 variant of a level (or the one whose file name is `only`)."""
    data_dir = Path(data_dir)
    ox, oy = level_origin(excel(data_dir, "levels"), level)
    files = level_files(excel(data_dir, "lvlprest"), level)
    if only:
        files = [f for f in files if selector(f) == selector(only)]
    if not files:
        raise ValueError(f"no DS1 for level {level}" + (f" named {only}" if only else ""))
    classes = object_classes(excel(data_dir, "objpreset"))
    places = monster_places(excel(data_dir, "monpreset"))
    out = []
    for f in files:
        path = data_dir / "global" / "tiles" / norm(f)
        pin = f" (pin: testing/force_ds1.py --slot <N> \"{selector(f)}\")" if len(files) > 1 else ""
        if not path.is_file():
            out.append(f"{f}: DS1 not found under {data_dir / 'global' / 'tiles'}, skipped")
            continue
        head, *rest = ds1_warp_lines(level, ox, oy, path.read_bytes(), classes, places, boss_words)
        out.append(f"{f}{pin}, {head}")
        out += [f"  {line}" for line in rest]
    return out


def warps_doc(data_dir: Path, levels: list[int], only: str | None = None,
              boss_words: tuple[str, ...] = BOSSY) -> str:
    """Markdown for a list of levels: one `## <levels.txt Name> (<Id>)` heading each, then its warp lines in a code
    block. `only` limits every level to the DS1 variant of that file name."""
    names = excel(Path(data_dir), "levels")
    out = ["# Warps (`cheat goto`)", ""]
    for level in levels:
        row = names.find(str(level), "Id")
        if row is None:
            raise ValueError(f"levels.txt has no level {level}")
        out += [f"## {names.get(row, 'Name')} ({level})", "", "```"]
        out += level_warps(data_dir, level, only, boss_words)
        out += ["```", ""]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", required=True, help="data folder with global/excel and global/tiles")
    ap.add_argument("--level", type=int, required=True, action="append", help="levels.txt Id (repeatable)")
    ap.add_argument("--ds1", help="only the variant with this file name")
    ap.add_argument("--boss-word", action="append", help="name part marking a boss-like monster preset (repeatable; "
                    "replaces the defaults)")
    ap.add_argument("--out", help="write a markdown doc (one heading per level) to this file")
    a = ap.parse_args(argv)
    words = tuple(w.lower() for w in a.boss_word) if a.boss_word else BOSSY
    try:
        if a.out:
            Path(a.out).write_text(warps_doc(Path(a.data), a.level, a.ds1, words), encoding="utf-8")
            print(f"wrote {a.out}")
        elif len(a.level) > 1:
            print(warps_doc(Path(a.data), a.level, a.ds1, words))
        else:
            print("\n".join(level_warps(Path(a.data), a.level[0], a.ds1, words)))
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
