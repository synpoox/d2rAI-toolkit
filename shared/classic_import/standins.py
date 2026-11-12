"""Stand-ins: engine rules a port has not built yet point at the closest D2R function.

A rule file (the project's `merge/standins.tsv`) has one line per row: `table <tab> row <tab> from <tab> columns <tab>
rule`. It sets the listed function columns of a merged row (its source name) from `from`: `=` is D2R's own row at that
id, a name is that D2R row, `-` blanks them. `rule` names the project's rule the line stands in for (the project keeps
each as a "not yet" row on its deviation list). Delete a row's line when its rule is built.

`only` is the project's list of function numbers a source row must not keep, because D2R's slot is empty, past the
table's end, or holds a different function: {table: {column: {number, ...}}}. It is passed in, never part of the
toolkit. After the lines are applied every merged row is checked against it: a source row that keeps one of those
numbers and has no line fails the merge, so no unbuilt function reaches the game unnoticed. A D2R row that has the same
value at the same position is D2R's own and passes. `nums(...)` builds the number sets from numbers and ranges.

    standins.apply is a rule kind: bind `only` with functools.partial(standins.apply, only=ONLY).
"""
from __future__ import annotations

from pathlib import Path

from .ids import Table, excel

Only = dict[str, dict[str, set[str]]]
Line = tuple[str, str, list[str], str]


def nums(*spans: int | range) -> set[str]:
    """{"3", "5", "6", "7"} from nums(3, range(5, 8))."""
    return {str(n) for s in spans for n in (s if isinstance(s, range) else [s])}


class StandinError(ValueError):
    pass


def apply_lines(table: str, mod: Table, d2r: Table, lines: list[Line]) -> None:
    """Set each line's columns in the merged table `mod`."""
    rows = {r[0].lower(): r for r in mod.rows}
    d2r_rows = {r[0].lower(): r for r in d2r.rows}
    for name, src, cols, _rule in lines:
        row = rows.get(name.lower())
        if row is None:
            raise StandinError(f"{table}: no row '{name}' in the merged table")
        n = sum(r[0].lower() == name.lower() for r in mod.rows)
        if n > 1:
            raise StandinError(f"{table}: '{name}' names {n} rows")
        if src == "=":
            # shortcut: matches D2R's row by position and fails on a name mismatch; name the D2R row if a table's order drifts
            i = mod.rows.index(row)
            if i >= len(d2r.rows) or d2r.rows[i][0].lower() != name.lower():
                raise StandinError(f"{table}: '{name}' is not a D2R row, so '=' has nothing to copy: name a D2R row")
            from_row = d2r.rows[i]
        elif src == "-":
            from_row = None
        elif src.lower() in d2r_rows:
            from_row = d2r_rows[src.lower()]
        else:
            raise StandinError(f"{table}: no D2R row '{src}'")
        for c in cols:
            if c not in mod.header or c not in d2r.header:
                raise StandinError(f"{table}: no column '{c}'")
            row[mod.header.index(c)] = from_row[d2r.header.index(c)] if from_row else ""


def check(table: str, mod: Table, d2r: Table, only: Only) -> None:
    """No source row keeps a number of `only`. A D2R row with its own value is not the source's."""
    left = []
    for c, bad in only.get(table, {}).items():
        if c not in mod.header:
            continue
        if c not in d2r.header:
            raise StandinError(f"{table}: no column '{c}' in D2R's table")
        j, k = mod.header.index(c), d2r.header.index(c)
        for i, r in enumerate(mod.rows):
            if r[j] in bad and not (i < len(d2r.rows) and d2r.rows[i][k] == r[j]):
                left.append(f"{r[0]} {c} {r[j]}")
    if left:
        raise StandinError(f"{table}: {', '.join(left)}: no stand-in; add a stand-in line")


def read_lines(path: Path) -> dict[str, list[Line]]:
    """table -> lines of the rule file."""
    out: dict[str, list[Line]] = {}
    for n, line in enumerate(path.read_text("utf-8").splitlines(), 1):
        if line and not line.startswith("#"):
            parts = line.split("\t")
            if len(parts) != 5 or not all(parts):
                raise StandinError(f"line {n}: want 'table<tab>row<tab>from<tab>columns<tab>rule'")
            t, row, src, cols, rule = parts
            out.setdefault(t, []).append((row, src, [c.strip() for c in cols.split(",")], rule))
    return out


def apply(rule: Path, src_data: Path, d2r_data: Path, out_data: Path, only: Only) -> None:
    """Rule kind for the stand-ins file: edit the tables the id and item rules wrote, then check them against `only`."""
    lines = read_lines(rule)
    if unknown := sorted(set(lines) - set(only)):
        raise StandinError(f"no stand-ins for table {', '.join(unknown)}: add it to the project's `only` list")
    for t in sorted(set(lines) | set(only)):
        path = excel(out_data) / f"{t}.txt"
        if not path.is_file():  # D2R's own table is built, so no source row needs a stand-in yet
            if t in lines:
                print(f"  standins: {t}.txt is not merged yet; its {len(lines[t])} lines wait for the rule that merges it")
            continue
        mod, d2r = Table(path), Table(excel(d2r_data) / f"{t}.txt")
        apply_lines(t, mod, d2r, lines.get(t, []))
        check(t, mod, d2r, only)
        path.write_bytes(mod.text().encode("latin-1"))
