# modkit patch operations

A patch is a JSON file in `<project>/patches/` holding `{"ops": [...]}`. Patches apply in file-name order (use
numbered names: `010-skills.json`, `020-stash.json`), each op in order, on top of the pristine game files and the
project's `files/data/` copies, then its optional git-ignored `generated/data/` copies, then the `gameCopies` of `mod.json`
(`{"data/global/chars/am/": "data/global/monsters/am/"}`: the game's files under the first prefix are written under
the second; both keys start with `data/` and end with `/`, `\` is read as `/`; a file the project already supplies is
kept; no game files under the first prefix, or no game install, fails the build). `modkit build` reports the
first failing op with its file and index.

Paths are game paths (`data/global/...`, `data/hd/...`). Table names are file names without `.txt`
(`skills`, `skilldesc`, `missiles`, `weapons`, `treasureclassex`, ...). Unless an op says otherwise, table ops
apply to both banks, `excel/` (what D2R plays) and `excel/base/` (the Classic/LoD bank), when the table exists
there; pass `"bank": "excel"` or `"bank": "base"` to limit it.

## Tables

| op | fields | effect |
|---|---|---|
| `set` | `table`, `key` (+ `column` to match another column) or `where: {col: value}`, `set: {col: value}` | change cells of existing rows |
| `clone_row` | `table`, `from`, `key`, `set` | copy a row under a new key, appended (new ID), then override |
| `add_row` | `table`, `values` | append a new row |
| `delete_row` | `table`, `key` | remove a row: keyed tables only; in indexed tables it shifts every later ID (knowledge/tables.md) |

Formula cells: bare negative numbers inside formulas are rewritten to `(0-N)` (D2R's parser rejects `-N`).
Plain numbers stay as they are.

## Strings

| op | fields | effect |
|---|---|---|
| `string` | `key`, `text` (str, or `{lang: text}`), `file` (default `item-modifiers.json`), `allLanguages` (default true), `force` | set a string key, or add it with a fresh ID; changing printf placeholders of an existing key is refused unless `force` (D2R formats some keys itself) |

## UI

| op | fields | effect |
|---|---|---|
| `layout` | `file` (layout name or game path), `widget`, `field` + `value` and/or `set: {field: value}`, `occurrence`, `replace: [[old, new]]` | edit a layout widget's fields (rect, cellCount, filename, textStrings, ...) or replace text |
| `panel` | `png`, `name` (`mymod/stash`), `layout`, `replaceImage` (str or list), `size` (default 1162 x 1507) | new panel background sprite + switch the layout's image reference to `PANEL\mymod\stash` |
| `sprite` | `png`, `to` (game path ending `.sprite`), `size`, `frames`, `lowend` | any PNG as an HD sprite (+ half-size `.lowend`) |

## HD looks

| op | fields | effect |
|---|---|---|
| `missile_hd` | `missile`, `like` (vanilla missile) or `model` | missiles.json entry: without one a new missile is invisible in HD |
| `item_hd` | `code` / `unique` / `set`, `asset`, optional `png` + `table` + `cells` | inventory picture: points the item at an existing asset, or converts a PNG to one (98 px per cell) |
| `hd_sequence` | `skill`, `like`, optional `class` | HD body animation for a sequence (anim `SQ`) skill, copied from a skill that has one |
| `json` | `file`, `path` (list of keys / indexes), `value` | set any value in any JSON game file |
| `copy` | `from` (project file), `to` (game path) | ship a file as it is (sounds, models, anything prepared elsewhere) |

## Skills

`skill` builds a whole skill (skills + skilldesc rows, strings, tree slot, icon, missiles, states, HD
animation). Its fields are documented at the top of `modkit/skill.py` and in `.claude/skills/d2r-skill/SKILL.md`.
New class skills: each class has exactly 30, and saves keep one byte per class skill. Without
`"extendedSaves": true` in mod.json (D2RLoader's extended save format) the op refuses to add a 31st, so
rework an existing skill with `replace` instead.

## Validation errors and their causes

`modkit build` validates the merged tables and prints only the first errors on the console; keep the full list (the
build's validation report) and sort it by cause, because a fresh port of a large classic mod reports well over a hundred
and most share a few causes. The causes seen, with what to do:

| Error kind | Cause | Fix |
|---|---|---|
| Code with the wrong case (`Deep-Wounds` where the table has `deep-wounds`) | The classic engine (1.13c) looks property and other codes up in any case; the check reports it | Normalise the case in the mod's row. Evidence is the classic reading, not a D2R run |
| A name that no row defines (a missile, skill, overlay, property or stat) | The source mod names a row its own tables lack too, or a typo (`fireexplode` for `fire_explode`, `dblue` for `dblu`) | If the source also lacked the row, the classic engine probably found none (unchecked unless you read the classic engine's lookup for that column) and the effect was silently absent: keep that (drop the value) or add the row on purpose. A typo is a bug of the source that shows in the source's game too: fix it only deliberately |
| A property code in a stat column (`dmg-min` in `stat1`) | A property code is not a stat; no itemstatcost row matches | The stat was dropped in the source: drop it, or use the real stat |
| A text field read as a raw code (`bonechips` in a 4-byte `alternategfx`) | The column holds a 4-byte code, not a name | Use the 4-byte code the source's engine really read |
| Value outside the column's list (`ItemTgtDo` 10, `ItemTarget` 5) | D2R allows only the listed values; the classic engine read a plain number | Use a listed value that gives the old result |
| Formula too long | D2R's formula limit is 255 bytes | Shorten, or move the sum into a second column or a plugin |
| Formula names a skill or parameter that does not exist | `skill('Name'.blvl)` with an unknown name, or a parameter number a skill does not have | What the classic engine computed is unchecked: fix the name, then test the numbers in game |
| A note in a numeric column | The source left text where a number is expected | Replace with a number |
| A treasure class used before it is defined | D2R needs a treasure class defined above the rows that use it | Reorder the table |
| String key missing from every string table | A name column points to a key no table has; the game shows the fallback string ("An evil force") | Add the key to the strings |
| Sound or other row from a table the port does not merge yet | A gap of the port, not of the source | Merge that table |

**Rule: a change that fixes a validation error is not merged until an in-game test shows it works and breaks nothing
else** (the hardest difficulty with a high-level character, not just a start-up). Unit tests, a diff against the
previous build and CI do not show what D2R does with the data; a fix that is only "the error is gone" can change
behaviour the source relied on. Record each fix with its cause class (keeps the source's behaviour, a source bug fixed
on purpose, or unchecked).

## Not ops (do these elsewhere)

- Engine behaviour that no table column can express (a new skill function, a new cube condition, new calc codes,
  more level types): a D2RLoader plugin, from `plugin-template/` (knowledge/engine-re.md).
- Character saves for testing: `modkit save-info` / `save-set` (knowledge/saves.md).
