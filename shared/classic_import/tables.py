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


def rule(rule_file: Path, src_data: Path, d2r_data: Path, out_data: Path, tables: list[str] | None = None) -> None:
    """The merge driver's rule kind for merge/tables.json: merge each table it names. `tables` are the project's
    id-listed tables (bound with functools.partial), whose renames the cells' references follow."""
    cfg = json.loads(rule_file.read_text("utf-8"))
    ren = ids.renames({t: ids.read_list(ids.list_path(rule_file.parent, t)) for t in tables or ()})
    for table, opts in sorted(cfg.items()):
        check_options(table, opts)
        merged = merge_table(table, Table(ids.excel(src_data) / f"{table}.txt"),
                             Table(ids.excel(d2r_data) / f"{table}.txt"), ren, **opts)
        ids.write(table, merged, out_data)
