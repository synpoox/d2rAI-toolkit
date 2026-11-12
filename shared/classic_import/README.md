# classic_import: the shared classic-import package

Python code for projects that read classic Diablo II data (LoD `.mpq` archives and their `.txt` tables) to build a
D2R mod: the generic part of a classic port's pipeline ([#5](https://github.com/synpoox/d2rAI-toolkit/issues/5)). Only
generic code goes in here: a project's own rules, fixes and command lines stay in the project.

| Module | What it is |
| --- | --- |
| `mpq.py` | Read-only classic (v1) MPQ reader: `Archive(path).read(name)`, encrypted tables, zlib, bzip2 and PKWARE implode. No dependencies |
| `extract.py` | `extract(install, out, baseline_file)`: checks every archive against the baseline file's SHA-256s, then extracts the files its `extract` patterns name (format in the module docstring). Skips a current extract |
| `merge.py` | The merge driver: `check_extract(out, baseline_file)` refuses a stale extract; `merge(rules, rules_dir, data, d2r, generated)` applies each rule file by its rule kind and leaves no `generated/` when a rule fails |
| `ids.py` | Append-only id lists (`merge/ids-<table>.tsv`) for the tables a save or D2R's code reads by row number: `read_list`, `seed` (same id below the project's vanilla count, then same name, then append), `check`, `renames`, `follow`, `seed_lists`; the id-list merge `merge_table` (project fixes come in as hooks: `spell`, `fix_row`, `finish`, `d2r_columns`, `add_columns`), `ids_of`, and the rule kind `apply`; the classic `Table` reader; and the D2R schema facts a merge onto D2R needs (key columns, `RENAME_MAP`, the rename map of the 1.13c columns D2R renamed, and `source_columns`, the one column matching every merge and the gate use; `REFS`, `NUM_REFS`, `FORMULAS`, key limits). Format and rules in the module docstring |
| `column_map.py` | The column-map stage: `apply(column_map, tables, recode, moved, restructure)` converts classic tables (`modkit.tsv.Table`) from one classic schema to another with the project's column map (format and kinds in the module docstring); `row_name(table, column)` turns references by row number into row names. A column the map doesn't cover, an unknown kind or a missing function fails the run |
| `tables.py` | The tables with no id list (`merge/tables.json`): `merge_table` merges a table onto D2R's by name, by position or by key columns, with `source_only_rows`, `repeats`, `d2r_columns`, `move`, `cells` and `only_rows`; `check_options`; `row_keys`; and the plain rule kind `rule`. Format in the module docstring |
| `diff.py` | The table-diff gate: `gate(src_excel, mod_excel, d2r_excel, deviation_list, ...)` compares every source table with the mod's (or D2R's, not merged yet) by table, row and column name and returns a `Report` of the deviations the deviation list doesn't name; `report()` writes it as markdown, `commit_of()` names the commit. The project picks the tables (`select`), names its deviation statuses (`statuses`, required) and passes its fixes (`compare_args`) |

## Data

| File | What it is |
| --- | --- |
| `data/109d-skill-functions.tsv` | Every 1.09d skill and missile function paired with D2R's, one row per function (2,088 rows). **D2R side: build 93847, image base `0x140000000`** (so `FUN_140xxxxxx` in `evidence` is base + `rva_d2r`). **1.09d side:** `addr_109d` is a virtual address at the DLL's default base: server functions are in D2Game.dll (`0x6fc...`), client functions in D2Client.dll (`0x6fa...` / `0x6fb...`); `Ordinal_N` in `evidence` is a 1.09d DLL import by ordinal. Columns: `kind` (skill or missile), `id` (Id in the 1.09d skills.txt / missiles.txt), `name_109d`, `name_d2r`, `function` (srv_start, srv_use, srv_do, srv_hit, clt_start, clt_do, clt_hit; `-` = none), `addr_109d`, `d2r_column` (srvstfunc, srvdofunc, cltstfunc, cltdofunc for skills; pSrvDoFunc, pSrvHitFunc, pCltDoFunc, pCltHitFunc for missiles), `d2r_index` (the function number in that column), `rva_d2r` (that table slot's value; a slot can hold a jmp thunk, as Whirlwind's does), `pair_verdict` (same, different or unresolved), `evidence` (`;`-separated: helper overlap, calls only one build makes), `record_verdict` (the record's worst `pair_verdict`, the same on each of its rows). Shape checked by `tests/test_classic_import_109d_skill_functions.py` |

## Use it from a project

Put the toolkit root on `PYTHONPATH` (as for `modkit`), then:

```python
from shared.classic_import import mpq

data = mpq.Archive(install / "d2data.mpq").read("data\global\excel\skills.txt")
```

A project keeps its own rule kinds and calls the driver:

```python
from shared.classic_import import extract, merge

extract.extract(install, root / "extracted", root / "baseline.json")
merge.check_extract(root / "extracted", root / "baseline.json")
merge.merge({"tables.json": my_tables_rule}, root / "merge", root / "extracted" / "data", d2r_data, root / "generated")
```

A project converting tables between classic schemas (1.09d to 1.13c) supplies its map and the
functions its `recode`, `moved` and `restructure` columns need:

```python
from shared.classic_import import column_map

out = column_map.apply(the_map, tables_109d,
                       recode={"missiles.Skill": column_map.row_name(tables_109d["skills"], "skill")},
                       moved={"skills.skilldesc": ("skilldesc", lambda record, row: row["skilldesc"])},
                       restructure={"setitems": split_sets})
```

The id-listed and tables.json rule kinds, bound to the project's tables (`functools.partial`), and the gate:

```python
from functools import partial
from shared.classic_import import diff, ids, tables

TABLES = ["skills", "missiles", "states", "itemstatcost"]
rules = {"tables.json": partial(tables.rule, tables=TABLES),
         **{f"ids-{t}.tsv": partial(ids.apply, tables=TABLES) for t in TABLES}}
ids.seed_lists(root / "merge", TABLES, extracted_data, d2r_data, vanilla={"skills": 357}, suffix="_09")
lists = {t: ids.read_list(ids.list_path(root / "merge", t)) for t in TABLES}
rep = diff.gate(extracted_data / "global/excel", root / "generated/data/global/excel", d2r_data / "global/excel",
                root / "docs/deviations.md", lists=lists, statuses=("kept", "cut", "not yet"), source="1.09d")
print(diff.report(rep, "all", diff.commit_of(root), source="1.09d"))
```

A project with its own fixes (function numbers D2R reuses, values no table defines) passes them as hooks:
`ids.merge_table(..., spell=my_spell, fix_row=my_fix_row, finish=my_finish)` in its own rule kind, and
`diff.gate(..., compare_args=lambda table: {"spell": my_spell, "fix_row": my_fix_row, "fix": my_fix})` so the gate
reads the source as the merge wrote it.

A project that caches merges by a hash of their inputs must include `shared/classic_import` in that hash.

### Record the toolkit commit

A project records the toolkit commit it was tested with, as for `shared/plugin-common` (its README, "Record the
toolkit commit"): put the commit in the project's README or baseline notes and bump it on purpose, after its own
tests pass against the newer toolkit. The whole package (`mpq`, `extract`, `merge`, `column_map`, `ids`, `tables`,
`diff`) needs the toolkit commit that merges [#5](https://github.com/synpoox/d2rAI-toolkit/issues/5) or later.

## Tests

`python -m unittest discover tests` from the toolkit root runs `tests/test_classic_import_*.py` (synthetic data: no game
files needed).
