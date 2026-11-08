# classic_import: the shared classic-import package

Python code for projects that read classic Diablo II data (LoD `.mpq` archives and their `.txt` tables) to build a
D2R mod, moved from pd2-resurrected's pipeline ([#5](https://github.com/synpoox/d2rAI-toolkit/issues/5)); the table
merges and the table-diff gate follow. Only generic code goes in here: a project's own rules stay in
the project.

| Module | What it is |
| --- | --- |
| `mpq.py` | Read-only classic (v1) MPQ reader: `Archive(path).read(name)`, encrypted tables, zlib, bzip2 and PKWARE implode. No dependencies |
| `extract.py` | `extract(install, out, baseline_file)`: checks every archive against the baseline file's SHA-256s, then extracts the files its `extract` patterns name (format in the module docstring). Skips a current extract |
| `merge.py` | The merge driver: `check_extract(out, baseline_file)` refuses a stale extract; `merge(rules, rules_dir, data, d2r, generated)` applies each rule file by its rule kind and leaves no `generated/` when a rule fails |
| `column_map.py` | The column-map stage: `apply(column_map, tables, recode, moved, restructure)` converts classic tables (`modkit.tsv.Table`) from one classic schema to another with the project's column map (format and kinds in the module docstring); `row_name(table, column)` turns references by row number into row names. A column the map doesn't cover, an unknown kind or a missing function fails the run |

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

A project converting tables between classic schemas (resurrected-09: 1.09d to 1.13c) supplies its map and the
functions its `recode`, `moved` and `restructure` columns need:

```python
from shared.classic_import import column_map

out = column_map.apply(the_map, tables_109d,
                       recode={"missiles.Skill": column_map.row_name(tables_109d["skills"], "skill")},
                       moved={"skills.skilldesc": ("skilldesc", lambda record, row: row["skilldesc"])},
                       restructure={"setitems": split_sets})
```

A project that caches merges by a hash of their inputs must include `shared/classic_import` in that hash.

Record the toolkit commit the project was tested with, as for `shared/plugin-common` (its README, "Record the
toolkit commit").

## Tests

`python -m unittest discover tests` from the toolkit root runs `tests/test_classic_import_*.py` (synthetic data: no game
files needed).
