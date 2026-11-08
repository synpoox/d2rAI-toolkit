"""Convert classic tables between classic schemas with a column map (#8). The map is the project's; this applies it.

    {"tables": {"<table>": {"columns": {"<source column>": {"to": [<target>, ...], "kind": "<kind>",
                                                             "transform": "<what the project's function does>"}},
                            "restructure": "<note>"}}}       # optional; other keys (value maps, notes) are the project's

Kinds, by what they do with a source column's value:
  same, rename  writes it to the one target column
  split         copies it to every target column
  recode        writes recode["<table>.<column>"](value, row) to every target, or a list with one value per target. row
                is the source row by column name. A recode with no targets needs no function
  moved         targets are "<other table>.<column>"; moved["<table>.<other table>"] = (key column, key(record, row))
                names the other table's row, made if missing. record is the source record number
  drop          has no target
  restructure   restructure["<table>"](source, converted) returns the tables that replace it; converted holds the
                other kinds' columns. A table with a "restructure" note needs a function too

Tables are modkit.tsv.Table; separator rows ("Expansion") stay in place and are not records, and a repeated column name
is its first copy. These fail with MapError
instead of passing: a source column the map doesn't cover, a map column the table lacks, an unknown kind, a missing or
stale function, and two columns giving one cell different values. row_name() is the recode for references by row
number.
"""
from __future__ import annotations

from typing import Callable

from modkit.tsv import Table

KINDS = ("same", "rename", "split", "recode", "moved", "drop", "restructure")


class MapError(ValueError):
    pass


def row_name(table: Table, column: str, none: tuple[str, ...] = ("",)) -> Callable[[str, dict], str]:
    """A recode: a record number in table -> that record's column. A value in none (e.g. "0", "-1") -> blank."""
    i = table.col(column)
    names = [r[i] for r in table.records()]

    def recode(value: str, row: dict) -> str:
        if value in none:
            return ""
        n = int(value) if value.isdigit() else -1
        if not 0 <= n < len(names):
            raise MapError(f"{table.name} has no record {value!r}")
        return names[n]
    return recode


def hooks(column_map: dict) -> tuple[set[str], set[str], set[str]]:
    """The recode, moved and restructure keys the map needs functions for."""
    rec, mov, res = set(), set(), set()
    for t, e in column_map["tables"].items():
        if "restructure" in e:
            res.add(t)
        for c, m in e.get("columns", {}).items():
            if m["kind"] == "recode" and m["to"]:
                rec.add(f"{t}.{c}")
            elif m["kind"] == "moved":
                mov |= {f"{t}.{x.split('.', 1)[0]}" for x in m["to"]}
            elif m["kind"] == "restructure":
                res.add(t)
    return rec, mov, res


def apply(column_map: dict, tables: dict[str, Table], recode: dict[str, Callable] | None = None,
          moved: dict[str, tuple[str, Callable]] | None = None,
          restructure: dict[str, Callable] | None = None) -> dict[str, Table]:
    """The source tables (by name) converted to the target schema, by name. Tables the map only moves columns into
    are made with the key column and those columns."""
    recode, moved, restructure = recode or {}, moved or {}, restructure or {}
    needed = hooks(column_map)
    for given, wanted, what in zip((recode, moved, restructure), needed, ("recode", "moved", "restructure")):
        if stale := sorted(set(given) - wanted):
            raise MapError(f"{what} functions the map has no use for: {', '.join(stale)}")
    out: dict[str, Table] = {}
    moves: dict[str, list] = {}  # other table -> [(key column, key, column, value, source)]

    def add(table: Table) -> None:
        if table.name in out:
            raise MapError(f"{table.name}: made twice")
        out[table.name] = table

    for name, src in tables.items():
        entry = column_map["tables"].get(name)
        if entry is None or "columns" not in entry:
            raise MapError(f"{name}: not a source table in the column map")
        cols = entry["columns"]
        if missing := [c for c in cols if c not in src.header]:
            raise MapError(f"{name}: map columns not in the table: {', '.join(missing)}")
        if uncovered := [c for c in src.header if c and c not in cols]:
            raise MapError(f"{name}: columns the map doesn't cover: {', '.join(uncovered)}")
        plan, seen = [], set()
        for i, c in enumerate(src.header):
            if not c or c in seen:  # a repeated column name reads as its first, as Table.col does
                continue
            seen.add(c)
            kind, to = cols[c]["kind"], cols[c]["to"]
            where = f"{name}.{c}"
            if kind not in KINDS:
                raise MapError(f"{where}: kind {kind!r} is not one of {', '.join(KINDS)}")
            if kind in ("same", "rename") and len(to) != 1:
                raise MapError(f"{where}: {kind} needs one target, has {len(to)}")
            if kind == "recode" and to and where not in recode:
                raise MapError(f"{where}: recode needs a function")
            if kind == "moved":
                for x in to:
                    if "." not in x or f"{name}.{x.split('.', 1)[0]}" not in moved:
                        raise MapError(f"{where}: moved to {x!r} needs a key function for {name}.<other table>")
            plan.append((i, c, kind, to))
        if name in needed[2] and name not in restructure:
            raise MapError(f"{name}: restructure needs a function")

        header = list(dict.fromkeys(x for _, _, k, to in plan if k in ("same", "rename", "split", "recode") for x in to))
        conv, n = Table(name, header, []), -1
        for row in src.rows:
            if not src.is_record(row):
                conv.rows.append(([row[0]] + [""] * (len(header) - 1)) if header else [])
                continue
            n += 1
            d, cells, by = dict(zip(src.header, row)), {}, {}

            def put(target: str, value: str, c: str) -> None:
                if value == "":
                    return
                if cells.get(target, "") not in ("", value):
                    raise MapError(f"{name} record {n}: {target} gets {cells[target]!r} from {by[target]} "
                                   f"and {value!r} from {c}")
                cells[target], by[target] = value, c

            for i, c, kind, to in plan:
                v = row[i] if i < len(row) else ""
                if kind in ("same", "rename", "split"):
                    for x in to:
                        put(x, v, c)
                elif kind == "recode" and to:
                    try:
                        r = recode[f"{name}.{c}"](v, d)
                    except MapError as e:
                        raise MapError(f"{name} record {n}, {c}: {e}") from None
                    vals = r if isinstance(r, list) else [r] * len(to)
                    if len(vals) != len(to):
                        raise MapError(f"{name}.{c}: recode gave {len(vals)} values for {len(to)} targets")
                    for x, y in zip(to, vals):
                        put(x, y, c)
                elif kind == "moved":
                    for x in to:
                        other, col = x.split(".", 1)
                        key_col, key = moved[f"{name}.{other}"]
                        moves.setdefault(other, []).append((key_col, key(n, d), col, v, f"{name}.{c}"))
            conv.rows.append([cells.get(x, "") for x in header])
        if name in restructure:
            for t in restructure[name](src, conv).values():
                add(t)
        else:
            add(conv)

    for other, ms in moves.items():
        t = out.get(other) or Table(other, [ms[0][0]], [])
        new = [c for c in dict.fromkeys(c for _, _, c, _, _ in ms) if not t.has_col(c)]
        out[other] = t = Table(other, t.header + new, [r + [""] * len(new) for r in t.rows])
        index = {}
        for key_col, key, col, v, where in ms:
            if not t.has_col(key_col):
                raise MapError(f"{where}: {other} has no key column {key_col!r}")
            if not key:
                raise MapError(f"{where}: no {other} row key")
            k = (key_col.lower(), key.lower())
            if k not in index:
                index[k] = t.find(key, key_col) or t.append({key_col: key})
            row = index[k]
            if v != "" and t.get(row, col) not in ("", v):
                raise MapError(f"{other} {key_col} {key!r}: {col} gets {t.get(row, col)!r} and {v!r} from {where}")
            if v != "":
                t.set(row, col, v)
    return out
