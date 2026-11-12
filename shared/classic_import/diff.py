"""The table-diff gate: compare a project's merged tables to the source baseline by table, row and column name (#5).

gate() reads the source's tables (the extract), the mod's (generated/; D2R's own table where generated/ has none yet)
and the project's deviation list, and returns a Report: every deviation the list doesn't name is open. report() turns
it into markdown for a PR. A project keeps its own command line (scopes, paths, exit codes) and passes its own fixes.

The deviation list is a markdown file. A table with a Deviation and a Status column holds entries (Status one of the
project's `statuses`, which the project always names); a table with a Gate column holds patterns
(`table.row.column` in backticks, fnmatch, lower case). A Gate row in a table without Status names its entry by Deviation.
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import ids
from .ids import Table
from .tables import row_keys

SHOWN = 200  # open deviations listed in the report; the counts cover the rest
# (table, mod header, the source row in the mod's spelling (changed in place), source header, source row)
Fix = Callable[[str, list[str], list[str], list[str], list[str]], None]


class GateError(Exception):
    pass


@dataclass
class Result:
    table: str
    open: list[tuple[str, str, str]] = field(default_factory=list)  # (table.row.column, source value, mod value)
    covered: int = 0  # deviations the deviation list names
    source: str = "merged"  # the mod's table: merged (generated/), D2R (not merged yet) or none


@dataclass
class Report:
    results: list[Result]
    entries: dict[str, int] = field(default_factory=dict)  # deviation list entries by status, whatever the selection

    @property
    def ok(self) -> bool:
        return not self.open()

    def open(self) -> list[tuple[str, str, str]]:
        return [d for r in self.results for d in r.open]


def same(a: str, b: str) -> bool:
    return a == b or {a, b} == {"", "0"}  # the loader reads a blank number as 0


def keyed(rows: list[list[str]], key: int = 0) -> dict[str, list[str]]:
    """Rows by lower-case key (Excel's quote marks dropped); a repeated key (Expansion) gets #2, #3, ... in order."""
    out: dict[str, list[str]] = {}
    for r in rows:
        k, n = r[key].replace('"', "").lower(), 1
        while (k if n == 1 else f"{k}#{n}") in out:
            n += 1
        out[k if n == 1 else f"{k}#{n}"] = r
    return out


def pairs(name: str, src: Table, mod: Table, ren: dict[str, dict[str, str]] | None, lists: dict[str, list[ids.Line]],
          rows: str | list[str] = "name", by_row: tuple[str, ...] = (), list_paired: tuple[str, ...] = ()
          ) -> list[tuple[str, list[str], list[str] | None]]:
    """(row label, source row, mod row or None) as the merge placed them: a `by_row` table row by row, a
    `list_paired` table with an id list by its list, a tables.json table by its `rows` (tables.row_keys), the rest by
    key (renamed by `ren`)."""
    if rows != "name":
        mod_rows = {k.lower(): r for k, r in zip(row_keys(mod, rows), mod.rows)}
        return [(k, pr, mod_rows.get(k.lower())) for k, pr in zip(row_keys(src, rows), src.rows)]
    if name in by_row or (name in list_paired and lists.get(name)):
        where = ({p.lower(): i for p, i, _ in lists[name]} if name not in by_row else
                 {p.lower(): k for k, p in enumerate(ids.ident(src.names()))})
        recs = mod.records()
        return [(p, src.rows[k], mod.rows[recs[where[p.lower()]]] if 0 <= where.get(p.lower(), len(recs)) < len(recs)
                 else None) for p, k in zip(ids.ident(src.names()), src.records())]  # LEFT_OUT: no mod row
    row_ren = ren.get(name, {}) if ren else {}
    mod_rows = keyed(mod.rows, mod.key)
    out = []
    for k, pr in keyed(src.rows, src.key).items():
        name_ = pr[src.key].replace('"', "")
        repeat = k[len(name_):]  # "#n" on a repeated name
        out.append((name_ + repeat, pr, mod_rows.get(row_ren.get(name_.lower(), name_).lower() + repeat)))
    return out


def compare(name: str, src: Table, mod: Table, ren: dict[str, dict[str, str]] | None = None,
            lists: dict[str, list[ids.Line]] | None = None, rows: str | list[str] = "name", *,
            id_map: dict[str, dict[str, str]] | None = None, by_row: tuple[str, ...] = (),
            list_paired: tuple[str, ...] = (), fix_row: ids.FixRow | None = None, fix: Fix | None = None,
            spell: ids.Spell = ids.spell) -> Result:
    """Deviations of `mod` from `src`: missing columns (table.*.col), missing rows (table.row.*), changed cells.
    The source's comment columns and eol are not data; a column D2R keeps only as a comment (*Id) is the row's
    position, and a repeated column is read once, as the merge reads it. The source's rows, columns and cells are read
    in the mod's spelling: columns matched as the merges match them (ids.source_columns), rows renamed by `ren`
    (ids.renames), cells spelled by `spell`, fixed by the
    project's `fix_row` and `fix`, and NUM_REFS and ID_COLS columns in the mod's ids (`id_map`, ids.ids_of). `rows`
    pairs a tables.json table's rows as its merge did. Excel's quote marks are not data."""
    res = Result(name)
    def data(i: int) -> bool:
        return not src.header[i].startswith("*") and src.header[i].lower() != "eol"
    to_src = ids.source_columns(name, src.header, mod.header)
    # the key column is the row's name, matched as the key; a renamed column D2R split in several is compared in each
    cols = [(src.header[i], i, j) for j, i in enumerate(to_src)
            if i is not None and data(i) and (i != src.key or rows != "name")]
    used, mod_cols, lower = set(to_src), {c.lower() for c in mod.header}, [c.lower() for c in src.header]
    for i, c in enumerate(src.header):
        repeat = c and lower.index(c.lower()) < i  # read once, as the merge reads it
        if i not in used and data(i) and not repeat and f"*{c.lower()}" not in mod_cols:
            res.open.append((f"{name}.*.{c}", "", ""))
    for row, pr, mr in pairs(name, src, mod, ren, lists or {}, rows, by_row, list_paired):
        if mr is None:
            res.open.append((f"{name}.{row}.*", "", ""))
            continue
        want, pr = list(mr), (fix_row(name, src.header, pr) if fix_row else pr)
        for _, i, j in cols:
            want[j] = spell(name, mod.header[j], pr[i], ren or {})  # as the merge spells it, lists or none
        if fix:
            fix(name, mod.header, want, src.header, pr)
        for j, c in enumerate(mod.header):  # level tables' row numbers, in the mod's ids
            t = ids.NUM_REFS.get(name, {}).get(c) or (name if ids.ID_COLS.get(name) == c else None)
            if id_map and t:
                want[j] = id_map.get(t, {}).get(want[j], want[j])
        res.open += [(f"{name}.{row}.{c}", pr[i], mr[j]) for c, i, j in cols if not same(want[j], mr[j])]
    return res


def deviations(path: Path, statuses: tuple[str, ...]) -> tuple[list[str], dict[str, int]]:
    """The deviation list's Gate patterns and its entry count by status (format in the module docstring). Fails on a
    status not in `statuses` and on a Gate row that names no entry."""
    patterns, cols, entries = [], None, dict.fromkeys(statuses, 0)
    listed, named = set(), []
    for line in path.read_text("utf-8").splitlines():
        if not line.startswith("|") or set(line) <= set("|-: "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if "Deviation" in cells and ("Gate" in cells or "Status" in cells):
            cols = {c: i for i, c in enumerate(cells)}
            continue
        if cols is None:
            continue
        if "Status" in cols:
            status = cells[cols["Status"]]
            if status not in statuses:
                raise GateError(f"{path.name}: status {status!r} is not one of {', '.join(statuses)}: {line}")
            entries[status] += 1
            listed.add(cells[cols["Deviation"]])
        elif "Gate" in cols:
            named.append(cells[cols["Deviation"]])
        if "Gate" in cols:
            patterns += [p.lower() for p in re.findall(r"`([^`]+)`", cells[cols["Gate"]])]
    if unknown := [d for d in named if d not in listed]:
        raise GateError(f"{path.name}: Gate patterns for rows not on the list: {unknown}")
    return patterns, entries


def triage(res: Result, patterns: list[str]) -> Result:
    """Moves the deviations the deviation list names from open to covered."""
    kept = [d for d in res.open if not any(fnmatch.fnmatchcase(d[0].lower(), p) for p in patterns)]
    res.covered += len(res.open) - len(kept)
    res.open = kept
    return res


def gate(src_excel: Path, mod_excel: Path, d2r_excel: Path, deviation_list: Path, statuses: tuple[str, ...],
         select: Callable[[str], bool] = lambda table: True, lists: dict[str, list[ids.Line]] | None = None,
         tables_json: dict | None = None,
         compare_args: Callable[[str], dict] = lambda table: {}, source: str = "source",
         extract_hint: str = "run the extract") -> Report:
    """Compare every source table `select` picks with the mod's: the merged one in mod_excel, else D2R's (not merged
    yet), else none (a deviation of the whole table). `statuses` are the project's deviation statuses, in the order
    the report counts them (no default: each project names its own). `lists` are the project's id lists, `tables_json` its
    tables.json (for each table's `rows`); compare_args(table) gives that table's extra compare() arguments (id_map,
    by_row, list_paired, fix_row, fix, spell). A deviation list pattern for a whole merged table fails the run."""
    if not d2r_excel.is_dir():  # else every unmerged table would read as unshipped
        raise GateError(f"no D2R tables under {d2r_excel}: run `modkit fetch` or pass the D2R data root")
    patterns, entries = deviations(deviation_list, statuses)
    if not any(src_excel.glob("*.txt")):  # else the gate compares nothing and passes
        raise GateError(f"no {source} tables under {src_excel}: {extract_hint}")
    lists = lists or {}
    ren = ids.renames(lists)
    results = []
    for p in sorted(p for p in src_excel.glob("*.txt") if select(p.stem.lower())):
        found = next(((s, f / p.name) for s, f in (("merged", mod_excel), ("D2R", d2r_excel)) if (f / p.name).is_file()),
                     None)
        if found is None:
            res = Result(p.stem, [(f"{p.stem}.*.*", "", "")], source="none")
        else:
            key = ids.KEY.get(p.stem)
            rows = (tables_json or {}).get(p.stem, {}).get("rows", "name") if found[0] == "merged" else "name"
            res = compare(p.stem, Table(p, key), Table(found[1], key), ren, lists, rows, **compare_args(p.stem))
            res.source = found[0]
            if found[0] == "merged" and f"{p.stem.lower()}.*" in patterns:
                raise GateError(f"{deviation_list.name} still covers all of {p.stem}, which is merged now: narrow its "
                                "row")
        results.append(triage(res, patterns))
    return Report(results, entries)


def fix_of(finish: ids.Finish | None) -> Fix | None:
    """A merge's `finish` hook (ids.finishes, ids.props_finish, ...) as the `fix` compare() takes, so the gate spells a
    source row exactly as the merge fixed it. The D2R row a finish may read is not known here (None), as for a row
    the merge appended."""
    if finish is None:
        return None
    return lambda table, header, want, src_header, src_row: finish(header, want, dict(zip(src_header, src_row)), None)


def scope_of(scopes: dict[str, Callable[[str], bool]], name: str) -> Callable[[str], bool]:
    """The `select` of a named scope; an unknown scope is a GateError."""
    if name not in scopes:
        raise GateError(f"scope {name!r} is not one of {', '.join(scopes)}")
    return scopes[name]


def cli(prog: str, scopes: dict[str, Callable[[str], bool]], run_gate: Callable[[Callable[[str], bool]], Report],
        argv: list[str] | None = None, root: Path | None = None, source: str = "Source", description: str = "") -> int:
    """A project's gate command line: `--scope NAME` picks a table selection of `scopes`, `run_gate(select)` returns the
    Report (the project calls gate() with its paths, id lists and compare_args). Prints the markdown report; exit 0 when
    nothing is open, 1 when something is, 2 when the deviation list, an id list or the scope is broken."""
    ap = argparse.ArgumentParser(prog=prog, description=description)
    ap.add_argument("--scope", required=True, choices=list(scopes))
    a = ap.parse_args(argv)
    try:
        rep = run_gate(scope_of(scopes, a.scope))
    except (GateError, ids.IdError) as e:
        print(f"{prog}: {e}", file=sys.stderr)
        return 2
    print(report(rep, a.scope, commit_of(root) if root else "", source))
    return 0 if rep.ok else 1


def escape_pipes(v: str) -> str:
    return v.replace("|", r"\|")


def commit_of(root: Path) -> str:
    """`root`'s short commit id, marked when its working tree has uncommitted changes, so a stale report shows."""
    def git(*args: str) -> str:
        try:
            return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True).stdout.strip()
        except OSError:  # git is not installed
            return ""
    head = git("rev-parse", "--short", "HEAD") or "no git commit"
    return f"{head}, uncommitted changes" if git("status", "--porcelain") else head


def report(rep: Report, scope: str, commit: str = "", source: str = "Source") -> str:
    """The gate's result as markdown, for pasting into the PR; the first line names the commit it ran on."""
    opened = rep.open()
    lines = [f"Table-diff gate{f' on {commit}' if commit else ''}, scope {scope}: {'pass' if rep.ok else 'FAIL'}, "
             f"{len(opened)} open, {sum(r.covered for r in rep.results)} table cells on the deviation list",
             "Deviation list: " + ", ".join(f"{n} {s}" for s, n in rep.entries.items()) + " entries "
             "(the cell count is large because one entry can cover a whole table)", "",
             "| Table | Mod table | Open | On the deviation list |", "|---|---|---|---|"]
    lines += [f"| {r.table} | {r.source} | {len(r.open)} | {r.covered} |" for r in rep.results]
    if opened:
        lines += ["", f"| Open deviation | {source} | Mod |", "|---|---|---|"]
        lines += [f"| `{k}` | {escape_pipes(a)} | {escape_pipes(b)} |" for k, a, b in opened[:SHOWN]]
        if len(opened) > SHOWN:
            lines += ["", f"{len(opened) - SHOWN} more not shown."]
    return "\n".join(lines)
