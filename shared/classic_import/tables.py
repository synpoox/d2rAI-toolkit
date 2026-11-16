"""The tables with no id list: merge/tables.json names each table the merge takes over from D2R (#5).

    {"<table>": {"rows": "name" | "position" | [column, ...], "source_only_rows": "append" | "leave out",
                 "repeats": "pair" | "replace group", "d2r_columns": [column, ...], "move": {...}, "cells": {...},
                 "only_rows": [row key, ...]}, ...}   (defaults first)

A source row merges onto the D2R row of the same name (lower case; a repeated name pairs by its order, #1, #2, ...):
D2R's columns take the source's value where the source has the column (or ids.RENAME_MAP renames it:
ids.source_columns), and keep D2R's value otherwise, comment columns (*...) included. D2R-only rows keep their place and numbers. Source-only rows append
after D2R's last row, D2R-only columns blank; "leave out" drops them. "rows": "position" pairs rows by their place
instead, for tables whose row number is the id and whose name columns differ between the games (shrines); a list of
columns pairs rows by those columns' values (hireling: Version, Id, Difficulty, Level). "move": {column: {source
value: mod value}} renumbers the source's rows before pairing, for ids D2R gave other rows; a moved row appends even
under "leave out" and takes the source's d2r_columns too, as D2R has no row of that meaning. "repeats": "replace group"
puts the source's whole group of a repeated name where D2R's group was, for lists the game reads in order (monequip: a
monster's gear by level). "d2r_columns" keep D2R's values where the games give a column different meanings (objects
Token: D2R's graphics). "cells": {row key: {column: value}} sets single cells after the merge, where one row needs a
value neither game's column gives it; cells are spelled as the mod holds them. "only_rows": [row key, ...] merges
only those source rows; every other row stays D2R's and source-only rows are left out.

A project with table-specific steps (its own checks or rewrites after a merge) keeps its own rule kind and calls
check_options and merge_table; `rule` is the plain one.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from pathlib import Path

from . import ids
from .ids import Spell, Table

OPTIONS = {"rows": ("name", "position"), "source_only_rows": ("append", "leave out"),
           "repeats": ("pair", "replace group")}
LISTS = ("rows", "d2r_columns", "only_rows")  # options that may be a list
DICTS = ("move", "cells")  # options that are a dict


def row_keys(t: Table, rows: str | list[str] = "name") -> list[str]:
    """Each row's key, as the merge and the gate pair rows: its name, its number, or its key columns' values joined
    by "/"; a repeated key gets #2, #3, ... in order. Compare keys in lower case."""
    # shortcut: repeats pair by order, so one inserted repeat shifts the rest; key rows by content if a table needs it
    if rows == "position":
        return [str(i) for i in range(len(t.rows))]
    ix = [0] if rows == "name" else [[c.lower() for c in t.header].index(c.lower()) for c in rows]
    out, seen = [], set()
    for r in t.rows:
        k, n = "/".join(r[i] for i in ix), 1
        while (key := k if n == 1 else f"{k}#{n}").lower() in seen:
            n += 1
        seen.add(key.lower())
        out.append(key)
    return out


def regroup(src: Table, d2r: Table) -> Table:
    """D2R's table with each group of a name the source also has cut or padded (blank rows) to the source's length,
    in place."""
    want: dict[str, int] = {}
    for r in src.rows:
        want[r[0].lower()] = want.get(r[0].lower(), 0) + 1
    out, done = [], set()
    for r in d2r.rows:
        k = r[0].lower()
        if k not in want:
            out.append(r)
        elif k not in done:
            done.add(k)
            group = [g for g in d2r.rows if g[0].lower() == k][:want[k]]
            out += group + [[r[0]] + [""] * (len(d2r.header) - 1) for _ in range(want[k] - len(group))]
    return Table.of(d2r.header, out, d2r.newline)


def check_options(table: str, opts: dict) -> None:
    """Refuse an option tables.json doesn't know, so a typo never silently merges with the default."""
    bad = [f"{k}: {v}" for k, v in opts.items() if v not in OPTIONS.get(k, ())
           and not (k in LISTS and isinstance(v, list)) and not (k in DICTS and isinstance(v, dict))]
    if bad:
        raise ValueError(f"{table}: unknown option {', '.join(bad)} (options: {OPTIONS}, lists: {LISTS}, "
                         f"dicts: {DICTS})")


def merge_table(table: str, src: Table, d2r: Table, ren: dict[str, dict[str, str]],
                rows: str | list[str] = "name", source_only_rows: str = "append", repeats: str = "pair",
                d2r_columns: tuple[str, ...] = (), move: dict[str, dict[str, str]] | None = None,
                cells: dict[str, dict[str, str]] | None = None, only_rows: list[str] | None = None,
                spell: Spell = ids.spell) -> Table:
    """D2R's table with the source's rows merged in, by the table's tables.json options (see the module docstring).
    `ren` is ids.renames of the project's id lists; `spell` spells a source cell as the mod holds it."""
    if only_rows is not None:
        keep, full = {k.lower() for k in only_rows}, src
        src = Table.of(full.header, [r for r, k in zip(full.rows, row_keys(full, rows)) if k.lower() in keep],
                       full.newline)
        if missing := keep - {k.lower() for k in row_keys(src, rows)}:
            raise ValueError(f"{table} only_rows: the source has no row {', '.join(sorted(missing))}")
        source_only_rows = "leave out"
    kept = {c.lower() for c in d2r_columns}
    cols = [(j, None if c.startswith("*") else s, c.lower() in kept)
            for (j, c), s in zip(enumerate(d2r.header), ids.source_columns(table, src.header, d2r.header))]
    moved = set()
    if move:
        src = Table.of(list(src.header), [list(r) for r in src.rows], src.newline)
        for c, m in move.items():
            j = [h.lower() for h in src.header].index(c.lower())
            for i, r in enumerate(src.rows):
                if r[j] in m:
                    r[j] = m[r[j]]
                    moved.add(i)
    if repeats == "replace group":
        d2r = regroup(src, d2r)
    out = [list(r) for r in d2r.rows]
    where = {k.lower(): i for i, k in enumerate(row_keys(d2r, rows))}
    for i, k in enumerate(row_keys(src, rows)):
        if k.lower() in where:
            row = out[where[k.lower()]]
        elif source_only_rows == "leave out" and i not in moved:
            continue
        else:
            row = [""] * len(d2r.header)
            out.append(row)
        for j, s, keep_d2r in cols:
            if s is not None and (not keep_d2r or i in moved):
                row[j] = spell(table, d2r.header[j], src.rows[i][s], ren)
    merged = Table.of(d2r.header, out, d2r.newline)
    where = {k.lower(): i for i, k in enumerate(row_keys(merged, rows))}
    head = {c.lower(): j for j, c in enumerate(d2r.header)}
    for k, vals in (cells or {}).items():
        if k.lower() not in where:
            raise ValueError(f"{table} cells: no row {k}")
        for c, v in vals.items():
            if c.lower() not in head:
                raise ValueError(f"{table} cells: no column {c}")
            out[where[k.lower()]][head[c.lower()]] = v
    return merged


def monster_numbers(src_data: Path, out_data: Path) -> dict[str, str]:
    """The source's monster number -> the merged monstats' number of the same monster (the game skips `Expansion`
    rows). Empty without a source monstats; a source monstats without a merged one is an error."""
    files = [ids.excel(d) / "monstats.txt" for d in (src_data, out_data)]
    if not files[0].is_file():
        return {}
    if not files[1].is_file():
        raise ValueError("hireling names monstats rows: merge monstats (an id list or merge/tables.json) before it")
    merged = {n.lower(): i for i, n in enumerate(Table(files[1]).names())}
    return {str(i): str(merged[n.lower()]) for i, n in enumerate(Table(files[0]).names()) if n.lower() in merged}


def hire_descs(src_data: Path) -> dict[str, str]:
    """The source's hiredesc code -> its description (English)."""
    f = ids.excel(src_data) / "hiredesc.txt"
    return {r[1].lower(): r[0] for r in Table(f).rows if r[1]} if f.is_file() else {}


def hire_keys(src_data: Path, d2r_data: Path, own_prefix: str = "hiredesc_", d2r_prefix: str = "strhirespecial"
              ) -> dict[str, str]:
    """The source's hiredesc code -> the string key a hireling row names: D2R's hire string of the same English text
    (a key starting with `d2r_prefix` in its ui.json), else `<own_prefix><code>`, whose text the project's strings
    rule reads from the source."""
    ui = d2r_data / "local/lng/strings/ui.json"
    d2r = {}
    if ui.is_file():
        d2r = {e["enUS"]: e["Key"] for e in json.loads(ui.read_text("utf-8-sig")) if e["Key"].startswith(d2r_prefix)}
    return {code: d2r.get(text, f"{own_prefix}{code}") for code, text in hire_descs(src_data).items()}


def sound_names(src_data: Path, d2r_data: Path) -> dict[str, str]:
    """The source's sound names D2R's sounds table (which ships as it is) lacks -> the D2R sound playing the same
    file, else blank: no sound until the source's own WAVs are ported. A monsounds name past the table crashes the
    client."""
    files = [ids.excel(d) / "sounds.txt" for d in (src_data, d2r_data)]
    if not all(f.is_file() for f in files):
        return {}
    src, d2r = Table(files[0]), Table(files[1])
    fcol = [c.lower() for c in d2r.header].index("filename")
    by_file: dict[str, str] = {}
    for r in d2r.rows:
        by_file.setdefault(r[fcol].lower(), r[0])
    scol = [c.lower() for c in src.header].index("filename")
    names = {r[0].lower() for r in d2r.rows}
    return {r[0].lower(): by_file.get(r[scol].lower().replace("/", "\\").removesuffix(".wav") + ".flac", "")
            for r in src.rows if r[0].lower() not in names}


def unknown_sounds(monsounds: Table, d2r_data: Path, sound_cols: Iterable[str] = ids.SOUND_COLS) -> list[str]:
    """The merged monsounds cells ("<row> <column> <sound>") naming a sound D2R's sounds table lacks."""
    f = ids.excel(d2r_data) / "sounds.txt"
    if not f.is_file():
        return []
    names = {r[0].lower() for r in Table(f).rows}
    want = {c.lower() for c in sound_cols}
    cols = [(j, c) for j, c in enumerate(monsounds.header) if c.lower() in want]
    return [f"{r[0]} {c} {r[j]}" for r in monsounds.rows for j, c in cols if r[j] and r[j].lower() not in names]


def extra_renames(src_data: Path, d2r_data: Path, out_data: Path, hireling: bool) -> dict[str, dict[str, str]]:
    """The renames this module adds to the id lists' (ids.renames): "sound" always, and "monster" and "hiredesc" when
    `hireling` is merged. rule() spells cells with them; pass the same map to diff.gate(renames=...) so the gate reads
    the source as the merge did. Only monsounds' sound columns follow "sound" (missiles, skills and states name sounds
    too, and are not renamed yet)."""
    ren = {"sound": sound_names(src_data, d2r_data)}
    if hireling:
        ren.update(monster=monster_numbers(src_data, out_data), hiredesc=hire_keys(src_data, d2r_data))
    return ren


Hook = Callable[[Table, Table], None]  # (merged, D2R's table): edit the merged table, or raise ValueError


def rule(rule_file: Path, src_data: Path, d2r_data: Path, out_data: Path, tables: list[str] | None = None,
         hooks: dict[str, Hook] | None = None, spell: Spell = ids.spell) -> None:
    """The merge driver's rule kind for merge/tables.json: merge each table it names. `tables` are the project's
    id-listed tables (bound with functools.partial), whose renames the cells' references follow. The source's sounds
    D2R lacks are renamed to D2R's sound of the same file ("sound"); `hireling` merges last, as it names monstats
    rows by their merged number ("monster") and hiredesc codes by string key ("hiredesc"). `hooks` maps a table to a
    function run on its merged table before it is written, for the table-specific steps a project keeps (e.g. the
    skilldesc rewrite). `spell` spells every cell (ids.make_spell: function numbers D2R reuses). A monsounds row naming a sound D2R's table lacks fails the merge."""
    cfg = json.loads(rule_file.read_text("utf-8"))
    ren = ids.renames({t: ids.read_list(ids.list_path(rule_file.parent, t)) for t in tables or ()})
    ren.update(extra_renames(src_data, d2r_data, out_data, False))
    for table, opts in sorted(cfg.items(), key=lambda kv: (kv[0] == "hireling", kv[0])):
        if table == "hireling":  # after monstats is merged
            ren.update(extra_renames(src_data, d2r_data, out_data, True))
        check_options(table, opts)
        d2r = Table(ids.excel(d2r_data) / f"{table}.txt")
        merged = merge_table(table, Table(ids.excel(src_data) / f"{table}.txt"), d2r, ren, spell=spell, **opts)
        if table in (hooks or {}):
            hooks[table](merged, d2r)
        if table == "monsounds" and (bad := unknown_sounds(merged, d2r_data)):
            raise ValueError(f"monsounds names sounds D2R's sounds table lacks (the client crashes): {'; '.join(bad)}")
        ids.write(table, merged, out_data)
