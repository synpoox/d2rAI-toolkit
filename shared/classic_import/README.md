# classic_import: the shared classic-import package

Python code for projects that read classic Diablo II data (LoD `.mpq` archives and their `.txt` tables) to build a
D2R mod: the generic part of a classic port's pipeline ([#5](https://github.com/synpoox/d2rAI-toolkit/issues/5)). Only
generic code goes in here: a project's own rules, fixes and command lines stay in the project.

| Module | What it is |
| --- | --- |
| `mpq.py` | Read-only classic (v1) MPQ reader: `Archive(path).read(name)`, encrypted tables, zlib, bzip2 and PKWARE implode. No dependencies |
| `extract.py` | `extract(install, out, baseline_file)`: checks every archive against the baseline file's SHA-256s, then extracts the files its `extract` patterns name (format in the module docstring). Skips a current extract. `extract_shared(install, out, baseline_file, cache_root, own_folder)` does it under a lock and makes `out` a junction (symlink) to one extract per baseline stamp under the cache root, so worktrees share it |
| `merge.py` | The merge driver: `check_extract(out, baseline_file)` refuses a stale extract; `merge(rules, rules_dir, data, d2r, generated)` applies each rule file by its rule kind and leaves no `generated/` when a rule fails. `run(...)` adds the project lock, the rule cache and merge slot (`rule_cache`, `slots_home`, `policy` from `cache_setup()`), the output check (`check_output(gen, required, minimum)`: a partial tree is rebuilt once with no cache, then fails) and `prune_cache`. The project passes its rules map in; `base_key` and `rule_key` build the cache keys |
| `cache.py` | The machine-wide rule cache for a merge, opt-in (`MODKIT_SHARED_CACHE` names its root; with it unset nothing is cached): `rule(cache, key, roots, run, policy)` replays a rule's recorded writes when the hash of its code and of every file it read is unchanged (`key`, `sources`, `toolkit_sources`; Python is hashed by its AST), with single-flight key locks, CI scopes (`MODKIT_CI_SCOPE`: `main` or `pr-<n>`, via `ci_policy`), a merge-slot cap (`Slots`, `merge_slots`; `MODKIT_MERGE_SLOTS`, `MODKIT_CI_RESERVED`) and size pruning (`prune`; `cap_bytes()` reads `MODKIT_CACHE_GB`) |
| `cache_verify.py` | `py -3 -m shared.classic_import.cache_verify <fresh> <cached>`: compares two merged trees by SHA-256 and names every file that differs (exit 0 identical, 1 differ). Run it after a fresh merge and a cache-replaying one to catch a rule key that misses an input |
| `ids.py` | Append-only id lists (`merge/ids-<table>.tsv`) for the tables a save or D2R's code reads by row number: `read_list`, `seed` (same id below the project's vanilla count, then same name, then append), `check`, `renames`, `follow`, `seed_lists`; the id-list merge `merge_table` (project fixes come in as hooks: `spell`, `fix_row`, `finish`, `d2r_columns`, `add_columns`, `num_refs`), `ids_of`, and the rule kind `apply` (with `followers=FOLLOWERS` it also writes objtype after objects; opt-in); the generic hooks, fed the project's values: `make_spell` (function numbers to move), `fix_cells` (values no table defines), and the Finish hooks `finishes`, `derive` (`DERIVED`), `stat_display`, `missile_funcs`, `hit_params`, `props_finish` / `fix_props` with `property_kinds`; `monstats_ids`, `left_out_of`, and `context_of`, which gathers a merge's `Context` (lists, renames, ids, property kinds); the classic `Table` reader; and the D2R schema facts a merge onto D2R needs (key columns, `RENAME_MAP`, the rename map of the 1.13c columns D2R renamed, and `source_columns`, the one column matching every merge and the gate use; `REFS`, `NUM_REFS`, `FORMULAS`, key limits). Format and rules in the module docstring. `entry_key(level name)` is a level's `LevelEntry` string key and `fix_levels(levels, first, last_type)` gives the source-only levels one and a `LevelType` D2R has (knowledge/tables.md, "New levels"). `PROPS` includes `monprop`, so its property columns get the same property fixes as the item tables. |
| `column_map.py` | The column-map stage: `apply(column_map, tables, recode, moved, restructure)` converts classic tables (`modkit.tsv.Table`) from one classic schema to another with the project's column map (format and kinds in the module docstring); `row_name(table, column)` turns references by row number into row names. A column the map doesn't cover, an unknown kind or a missing function fails the run |
| `tables.py` | The tables with no id list (`merge/tables.json`): `merge_table` merges a table onto D2R's by name, by position or by key columns, with `source_only_rows`, `repeats`, `d2r_columns`, `move`, `cells` and `only_rows`; `check_options`; `row_keys`; the hireling and sound helpers `monster_numbers`, `hire_descs`, `hire_keys`, `sound_names`, `unknown_sounds`; and the rule kind `rule` (hireling merges last, `hooks` run a project's table-specific step before a table is written, `spell` spells every cell, default `ids.spell`). Format in the module docstring |
| `items.py` | The item tables with no id list, the cube and the HD item pictures: `merge_keyed`, `merge_cube` (the project's engine rules come in as `fixes`/`after` functions of the cube table; `count_each_input` is one), `block_drops` (never-dropping items), `item_pictures` (the project passes its upscaler in), `hd_items`, `borrow_pictures`, `ground_models`, and the rule kind `apply` (bind the `Context`, vanilla counts and fixes with `functools.partial`). Format in the module docstring. `apply(..., merge_args=...)` takes the options for the table merges (`spell`, `fix_row`, `source`, `finish`) as a dict or a function of the table name, and `picture_folder` names the folder the upscaled pictures go under (default `src`). `hd_items(..., neutral_model=...)` takes, per table, the asset a new code with no picture of its own draws on the ground; a stack (base code plus `s`) or an item sharing a D2R item's `flippyfile` draws that item's model. |
| `diff.py` | The table-diff gate: `gate(src_excel, mod_excel, d2r_excel, deviation_list, ...)` compares every source table with the mod's (or D2R's, not merged yet) by table, row and column name and returns a `Report` of the deviations the deviation list doesn't name; `report()` writes it as markdown, `commit_of()` names the commit. `fix_of` turns a merge's finish hook into the gate's `fix`; `cli(prog, scopes, run_gate)` is the command line (exit 0 pass, 1 open, 2 broken list). The project picks the tables (`select`), names its deviation statuses (`statuses`, required) and passes its fixes (`compare_args`). `gate(..., own=, own_label=)` says which merged tables the project owns (the others are D2R's, so an edit shows as a deviation), and `strict_whole_table=True` refuses every deviation pattern that covers a whole merged table (`whole_table(pattern, table)`: `t.*.*`, `t*`), not only `t.*`. |
| `skilldesc.py` | skilldesc's description lines moved onto D2R's line functions after the table merge: `clashes` finds the lines D2R would print wrongly (a classic text plus D2R's format code), `rewrite(t, d2r, fmt, mapping, elements, strings)` rewrites them by the project's `Mapping` (classic function -> D2R function, whole-line fixes, key renames, built-in labels; passed in, format in the module docstring) and fails on a line the mapping cannot place; `texts`, `formatted`, `hide_off_tree` |
| `hd_entries.py` | The HD looks of the rows a port adds, as rule kinds with one `name<tab>like` line per row whose art D2R lacks: `apply_missiles` (missiles.json by `CelFile`), `apply_monsters` (monsters.json by `BaseId` and `Code`), `apply_objects` (objects.json plus a stand-in json, optional particles swap) and `apply_overlays` (the new rows' `Character` and stand-in jsons). A new row with no model, or a line for a row that is not new, fails the merge. `copy_sequence_state(sm, new_skill, src_skill, name, suffix)` copies a skill's sequence state for a new skill (knowledge/hd-graphics.md). |
| `standins.py` | Stand-ins for engine rules a port has not built: a rule file of `table<tab>row<tab>from<tab>columns<tab>rule` lines sets a merged row's function columns from D2R's row (`=`, a name, or `-` to blank), then `check` fails when a source row keeps a function number the project lists in `only` (passed in: `{table: {column: numbers}}`, built with `nums`). The rule kind is `functools.partial(standins.apply, only=ONLY)` |

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

A project's deviation list keeps each section's count in its heading (`### Cut (3)`): `py -3 tools/check_deviations.py docs/deviations.md` fails when a count drifts from its table. `templates/baseline.example.json` is the baseline file `extract` reads, values stripped.

A project that caches merges by a hash of their inputs must include `shared/classic_import` in that hash.

### Record the toolkit commit

A project records the toolkit commit it was tested with, as for `shared/plugin-common` (its README, "Record the
toolkit commit"): put the commit in the project's README or baseline notes and bump it on purpose, after its own
tests pass against the newer toolkit. The whole package (`mpq`, `extract`, `merge`, `column_map`, `ids`, `tables`,
`diff`) needs the toolkit commit that merges [#5](https://github.com/synpoox/d2rAI-toolkit/issues/5) or later.

## Tests

`python -m unittest discover tests` from the toolkit root runs `tests/test_classic_import_*.py` (synthetic data: no game
files needed).
