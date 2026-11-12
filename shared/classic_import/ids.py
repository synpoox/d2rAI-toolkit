"""Append-only id lists: how a project merges the classic tables a save or D2R's code reads by row number onto D2R's,
and the D2R schema facts that merge needs (#5).

A list, merge/ids-<table>.tsv, has one line per source row (the classic table being ported): `source name <tab> id
<tab> name`, the row's id and key name in the mod. Ids count records as the game does (an `Expansion` row is not one);
a repeated source name is listed as `name#2`. An id of `-` leaves the source row out (a cut area, an unused row);
the third column then says why. An id at or below D2R's last row merges the source row onto that D2R row and keeps
D2R's name, so D2R's own files that name it stay valid (DISPLAY_KEYS tables keep the source's: there the key is the
text the player sees); a higher id appends the row. Lines are only ever added (seed), never renumbered.
A line whose source name starts with `+` is a row the port adds (port_row): `+<id> col=value ...` appends a copy of
the mod's row `<id>` (an earlier one) with those columns set, at the line's id after D2R's rows.

Seeding a new source row picks, in order:
  1. the same id, below `vanilla` (the project's count of rows both games keep from vanilla 1.13c), often renamed on
     one side;
  2. a D2R row of the same name that no other line took (rows both games added after vanilla; not for affixes,
     NO_NAME_MATCH);
  3. the next free id after D2R's last row, under its source name (+ the project's suffix if the mod has that name).

Merging a row (merge_table): D2R's row, with every column the source also has (or RENAME_MAP renames) set to the
source's value (source_columns), spelled by `spell` (quotes gone, references to the id-listed tables renamed,
formulas in D2R's spelling). Columns D2R added keep D2R's value on a D2R row and stay blank on an appended one.
NUM_REFS columns take the mod's ids, ID_COLS and `*Id` columns the row's own. A project's own fixes come in as hooks (spell, fix_row, finish).

The hooks' generic part is here; the values stay the project's and are passed in: make_spell (function numbers to
move), fix_cells (values no table defines), and Finish hooks chained by finishes: derive (DERIVED and the project's
computed columns), stat_display (itemstatcost), missile_funcs, hit_params and props_finish (fix_props, with
property_kinds). context_of gathers the lists, renames, ids (monstats_ids too) and property kinds a merge needs.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, NamedTuple

from modkit.tsv import NEGATIVE

# the key column, when not the first (a 1.13c-shaped qualityitems starts with nummods)
KEY = {"itemtypes": "Code", "weapons": "code", "armor": "code", "misc": "code", "gamble": "code",
       "qualityitems": "mod1code"}
# the key is the string the player sees (or, for qualityitems, a value), so the source's wins on a merged row;
# elsewhere D2R's files name the row by D2R's key
DISPLAY_KEYS = {"uniqueitems", "setitems", "runes", "magicprefix", "magicsuffix", "automagic", "rareprefix",
                "raresuffix", "qualityitems"}
# affix names repeat and say nothing of the row's mods, so a source affix after vanilla never takes a D2R-only one's row
NO_NAME_MATCH = {"magicprefix", "magicsuffix", "automagic", "rareprefix", "raresuffix"}
DUP_NAMES = {"uniqueitems", "runes", "magicprefix", "magicsuffix", "automagic", "rareprefix", "raresuffix",
             "lvlwarp", "objgroup", "lvlprest"}  # keys may repeat
KEY_LIMIT = {"missiles": 31}  # bytes, from D2R's data guide; the other id-listed tables allow 47
LEFT_OUT = -1  # the id read_list gives a `-` line
# 1.13c spells two vendors' columns by their old names
_NPC = {f"{d2r}{s}": f"{c113}{s}" for d2r, c113 in (("Anya", "Drehya"), ("Hratli", "Hralti"))
        for s in ("Min", "Max", "MagicMin", "MagicMax", "MagicLvl")}
# the rename map: D2R column -> 1.13c column, where D2R renamed it (more than letter case). Not the column_map module,
# which maps one classic schema onto another
RENAME_MAP = {"skills": {"localdelay": "delay"}, "missiles": {"EMax": "Emax"}, "weapons": _NPC, "armor": _NPC,
              "misc": _NPC, "uniqueitems": {"spawnable": "enabled"},
              "itemtypes": {"MaxSockets1": "MaxSock1", "MaxSockets2": "MaxSock25", "MaxSockets3": "MaxSock40"},
              "levels": {f"MonLvl{ex}{d}": f"MonLvl{n}{ex}" for n, d in ((1, ""), (2, "(N)"), (3, "(H)")) for ex in ("", "Ex")},
              "monstats": {f"TreasureClass{k}{d}": f"TreasureClass{n}{d}" for d in ("", "(N)", "(H)")
                           for n, k in ((1, ""), (2, "Champ"), (3, "Unique"), (4, "Quest"))},
              "hireling": {f"Resist{e}{lvl}": f"Resist{lvl}" for e in ("Fire", "Cold", "Lightning", "Poison")
                           for lvl in ("", "/Lvl")}}
_SKILL_REFS = ["sumskill1", "sumskill2", "sumskill3", "sumskill4", "sumskill5", "reqskill1", "reqskill2", "reqskill3"]
_MISSILE_REFS = ["ExplosionMissile", "SubMissile1", "SubMissile2", "SubMissile3", "HitSubMissile1", "HitSubMissile2",
                 "HitSubMissile3", "HitSubMissile4", "CltSubMissile1", "CltSubMissile2", "CltSubMissile3",
                 "CltHitSubMissile1", "CltHitSubMissile2", "CltHitSubMissile3", "CltHitSubMissile4"]
# column -> the table whose row it names by key, from D2R's data guide and modkit's EXPLICIT_REFS
REFS = {
    "skills": {**{c: "skills" for c in _SKILL_REFS},
               **{c: "missiles" for c in ["srvmissile", "srvmissilea", "srvmissileb", "srvmissilec", "cltmissile",
                                          "cltmissilea", "cltmissileb", "cltmissilec", "cltmissiled"]},
               **{c: "states" for c in ["aurastate", "auratargetstate", "passivestate", "State1", "State2", "State3"]},
               **{f"aurastat{i}": "itemstatcost" for i in range(1, 7)},
               **{f"passivestat{i}": "itemstatcost" for i in range(1, 6)}},
    "states": {"stat": "itemstatcost", "missile": "missiles", "skill": "skills"},
    "itemstatcost": {c: "itemstatcost" for c in ["op base", "op stat1", "op stat2", "op stat3", "maxstat"]},
    "missiles": {"Skill": "skills", **{c: "missiles" for c in _MISSILE_REFS}},
    "monstats": {**{f"Skill{i}": "skills" for i in range(1, 9)}, "SkillDamage": "skills",
                 **{c: "missiles" for c in ["MissA1", "MissA2", "MissS1", "MissS2", "MissS3", "MissS4", "MissC", "MissSQ"]}},
    "monstats2": {"ResurrectSkill": "skills"},
    "charstats": {"StartSkill": "skills", **{f"Skill {i}": "skills" for i in range(1, 11)}},
    "hireling": {f"Skill{i}": "skills" for i in range(1, 7)},
    "monsounds": {f"CvtSk{i}": "skills" for i in range(1, 4)},
    "skilldesc": {f"descmissile{i}": "missiles" for i in range(1, 4)},
}
# columns holding another id-listed table's row number -> that table (levels' Warp0-7 hold lvlwarp's Id column, not
# a row number)
NUM_REFS = {"levels": {**{f"Vis{i}": "levels" for i in range(8)}, **{f"ObjGrp{i}": "objgroup" for i in range(8)}},
            "lvlprest": {"LevelId": "levels"},
            "objgroup": {f"ID{i}": "objects" for i in range(8)}}
# columns that hold the row's own id, written with the mod's (lvlwarp UniqueId: D2R's, the row number)
ID_COLS = {"levels": "Id", "lvlprest": "Def", "lvlwarp": "UniqueId"}
FORMULAS = {
    "skills": ["prgcalc1", "prgcalc2", "prgcalc3", "auralencalc", "aurarangecalc", *[f"aurastatcalc{i}" for i in range(1, 7)],
               *[f"passivecalc{i}" for i in range(1, 6)], "petmax", *[f"sumsk{i}calc" for i in range(1, 6)], "sumumod",
               "cltcalc1", "cltcalc2", "cltcalc3", "skpoints", "perdelay", "calc1", "calc2", "calc3", "calc4",
               "ToHitCalc", "DmgSymPerCalc", "EDmgSymPerCalc", "ELenSymPerCalc", "localdelay"],
    "missiles": ["SrvCalc1", "CltCalc1", "SHitCalc1", "CHitCalc1", "DmgCalc1", "Range", "DmgSymPerCalc", "EDmgSymPerCalc"],
    "skilldesc": ["ddam calc1", "ddam calc2", *[f"desccalc{ab}{i}" for i in range(1, 7) for ab in "ab"],
                  *[f"dsc2calc{ab}{i}" for i in range(1, 6) for ab in "ab"], *[f"dsc3calc{ab}{i}" for i in range(1, 8) for ab in "ab"]],
}
FORMULA_REF = re.compile(r"\b(skill|miss|stat)\('([^']*)'")
FORMULA_TABLE = {"skill": "skills", "miss": "missiles", "stat": "itemstatcost"}

Line = tuple[str, int, str]  # (source name, id, name in the mod)


class IdError(Exception):
    pass


def ident(names: list[str]) -> list[str]:
    """Names made unique for the id lists: the second 'Sturdy' is 'Sturdy#2'."""
    seen: dict[str, int] = {}
    out = []
    for n in names:
        seen[n.lower()] = seen.get(n.lower(), 0) + 1
        out.append(n if seen[n.lower()] == 1 else f"{n}#{seen[n.lower()]}")
    return out


def port_row(source_name: str) -> tuple[int, dict[str, str]] | None:
    """A port-added line's (row it copies, columns it sets), or None for a source row's line."""
    if not source_name.startswith("+"):
        return None
    like, *sets = source_name[1:].split(" ")  # shortcut: a value can't hold a space; quote values if one ever must
    if not like.isdigit() or not all("=" in kv for kv in sets):
        raise IdError(f"port row '{source_name}': want '+<id> column=value ...'")
    return int(like), dict(kv.split("=", 1) for kv in sets)


def base(name: str) -> str:
    return re.sub(r"#\d+$", "", name)


def list_path(merge_dir: Path, table: str) -> Path:
    return merge_dir / f"ids-{table}.tsv"


def read_list(path: Path) -> list[Line]:
    if not path.exists():
        return []
    out = []
    for n, line in enumerate(path.read_text("utf-8").splitlines(), 1):
        if line and not line.startswith("# "):  # "#2" is the second blank-named row
            parts = line.split("\t")
            if len(parts) != 3 or not (parts[1].isdigit() or parts[1] == "-"):
                raise IdError(f"{path.name} line {n}: want 'source name<tab>id<tab>name' (id '-': left out)")
            out.append((parts[0], LEFT_OUT if parts[1] == "-" else int(parts[1]), parts[2]))
    return out


def seed(table: str, src: list[str], d2r: list[str], existing: list[Line], vanilla: int, suffix: str) -> list[Line]:
    """Lines for the source rows `existing` lacks, by the rules in the module docstring."""
    listed = {p.lower() for p, _, _ in existing}
    taken = {i for _, i, _ in existing}
    names = {n.lower() for _, _, n in existing} | {n.lower() for n in d2r}
    todo = [(i, n) for i, n in enumerate(ident(src)) if n.lower() not in listed]
    out_name = (lambda i, j: src[i]) if table in DISPLAY_KEYS else (lambda i, j: d2r[j])
    new: dict[int, Line] = {}
    for i, n in todo:
        if i < vanilla and i < len(d2r) and i not in taken:
            new[i] = (n, i, out_name(i, i))
            taken.add(i)
    by_name = {} if table in NO_NAME_MATCH else {n.lower(): i for i, n in enumerate(ident(d2r))}
    for i, n in todo:
        j = by_name.get(n.lower())
        if i not in new and j is not None and j not in taken:
            new[i] = (n, j, out_name(i, j))
            taken.add(j)
    next_id = max([len(d2r) - 1, *(i for _, i, _ in existing)]) + 1
    for i, n in todo:
        if i not in new:
            name = src[i] if table in DUP_NAMES or src[i].lower() not in names else f"{src[i]}{suffix}"
            name = name[:KEY_LIMIT.get(table, 47)]  # a clash after cutting fails check(); name that line by hand
            new[i] = (n, next_id, name)
            names.add(name.lower())
            next_id += 1
    return [new[i] for i, _ in todo]


def check(table: str, lines: list[Line], src: list[str], d2r: list[str], source: str = "source",
          seed_hint: str = "seed the list") -> None:
    """The list covers every source row once, matches D2R's names, and appends without gaps. source names the
    source game in messages; seed_hint says how to add the missing lines."""
    f = f"ids-{table}.tsv"
    src = ident(src)
    src_names = {n.lower() for n in src}
    seen: dict[str, str] = {}
    for p, i, n in lines:
        if p.lower() in seen:
            raise IdError(f"{f}: {source} row '{p}' listed twice")
        seen[p.lower()] = n
        port = port_row(p)
        if port:
            if i < len(d2r):
                raise IdError(f"{f}: port row '{p}' must take an id after D2R's rows")
            if port[0] >= i:
                raise IdError(f"{f}: port row '{p}' must copy an earlier row")
        elif p.lower() not in src_names:
            # shortcut: a source row gone after a re-baseline fails; keep its id with a disabled row when that happens
            raise IdError(f"{f}: '{p}' is not a {source} row any more")
        if i == LEFT_OUT:
            continue
        if len(n.encode("latin-1")) > KEY_LIMIT.get(table, 47):
            raise IdError(f"{f}: '{n}' is longer than D2R's {KEY_LIMIT.get(table, 47)} bytes: give it a shorter name")
        if table not in DISPLAY_KEYS and i < len(d2r) and d2r[i] != n:
            raise IdError(f"{f}: id {i} is D2R's '{d2r[i]}', the list says '{n}'")
    missing = [n for n in src if n.lower() not in seen]
    if missing:
        raise IdError(f"{f}: {source} rows with no id ({', '.join(missing[:5])}{', ...' if len(missing) > 5 else ''}): "
                      f"{seed_hint}")
    ids = [i for _, i, _ in lines if i != LEFT_OUT]
    if len(set(ids)) != len(ids):
        raise IdError(f"{f}: an id is listed twice")
    added = sorted(i for i in ids if i >= len(d2r))
    if added != list(range(len(d2r), len(d2r) + len(added))):
        raise IdError(f"{f}: appended ids must run from {len(d2r)} without gaps")
    out_names = [n.lower() for n in [*(n for _, i, n in lines if i >= len(d2r)), *d2r] if n]  # blank: unused rows
    if table not in DUP_NAMES and len(set(out_names)) != len(out_names):
        raise IdError(f"{f}: a name is used twice in the mod")


def renames(lists: dict[str, list[Line]]) -> dict[str, dict[str, str]]:
    """table -> {source name (lower case): mod name} for the rows whose name changes."""
    return {t: {base(p).lower(): n for p, i, n in ls if base(p) != n and i != LEFT_OUT and not port_row(p)}
            for t, ls in lists.items()}


def follow(lines: list[Line], src_keys: list[str], d2r: list[str], src: list[str]) -> list[Line]:
    """Lines for a table whose rows are another table's row for row (objtype: objects): source row k takes the id of
    the other list's line for source row k, and D2R's name on a merged row."""
    if len(src_keys) != len(src):
        raise IdError(f"follow: the source table has {len(src)} rows but the table it follows has {len(src_keys)}; "
                      "the two must match row for row")
    at = {p.lower(): (i, n) for p, i, n in lines}
    out = []
    for key, name in zip(ident(src_keys), ident(src)):
        i, _ = at[key.lower()]
        out.append((name, i, "" if i == LEFT_OUT else d2r[i] if i < len(d2r) else base(name)))
    return out


def fix_formula(text: str) -> str:
    """A 1.13c formula in D2R's spelling: '-"min(a,b)"' -> '0-min(a,b)', 'x*-5' -> 'x*(0-5)'."""
    if re.fullmatch(r"\s*-?\d+\s*", text):
        return text
    # a minus after an operand, spaces allowed ('lvl -1'), is a subtraction, not a negative number
    text = NEGATIVE.sub(lambda m: m[0] if re.search(r"[\w)\]'.]\s*$", text[:m.start()]) else f"(0-{m[1]})", text)
    return "0" + text.lstrip() if text.lstrip().startswith("-") else text


def rewrite_formula(text: str, ren: dict[str, dict[str, str]]) -> str:
    """Names inside a formula's skill('..'), miss('..') and stat('..') in the mod's names (renames())."""
    return FORMULA_REF.sub(lambda m: f"{m[1]}('{ren.get(FORMULA_TABLE[m[1]], {}).get(m[2].lower(), m[2])}'", text)


class Table:
    """A classic or D2R .txt table as the merges read it: latin-1, its newline kept, every row padded to the header."""
    def __init__(self, path: Path, key: str | None = None):
        text = path.read_bytes().decode("latin-1")  # keeps CRLF, which read_text would turn into LF
        self.newline = "\r\n" if "\r\n" in text else "\n"
        lines = text.split(self.newline)
        while lines and not lines[-1]:
            lines.pop()
        self.header = lines[0].split("\t")
        self.rows = [(line.split("\t") + [""] * len(self.header))[:len(self.header)] for line in lines[1:]]
        self.key = self.header.index(key) if key else 0

    @classmethod
    def of(cls, header: list[str], rows: list[list[str]], newline: str = "\r\n", key: int = 0) -> "Table":
        t = cls.__new__(cls)
        t.header, t.rows, t.newline, t.key = header, rows, newline, key
        return t

    def records(self) -> list[int]:
        """Row positions of the records, numbered as the game numbers them: an `Expansion` row (first column) is not
        one."""
        return [i for i, r in enumerate(self.rows) if r[0] != "Expansion"]

    def names(self) -> list[str]:
        return [self.rows[i][self.key] for i in self.records()]

    def text(self) -> str:
        return self.newline.join("\t".join(r) for r in [self.header, *self.rows]) + self.newline


def source_columns(table: str, src_header: list[str], d2r_header: list[str]) -> list[int | None]:
    """For each D2R column, the source column that fills it, or None: the one RENAME_MAP names for it, else the one of
    the same name, letter case aside. A repeated source column's first holds the values (armor's mindam, maxdam); an
    unnamed one (weapons) fills nothing. Every merge and the gate match columns with this."""
    at: dict[str, int] = {}
    for i, c in enumerate(src_header):
        if c:
            at.setdefault(c.lower(), i)
    renamed = {d.lower(): s.lower() for d, s in RENAME_MAP.get(table, {}).items()}
    return [at.get(renamed.get(c.lower(), c.lower())) for c in d2r_header]


def spell(table: str, col: str, v: str, ren: dict[str, dict[str, str]]) -> str:
    """A source cell as the mod's column `col` holds it: quotes gone, references renamed, formulas in D2R's spelling.
    A project with more to fix (function numbers D2R reuses for its own) passes its own spell to the merges."""
    v = v.replace('"', "")
    if col in REFS.get(table, {}):
        return ren.get(REFS[table][col], {}).get(v.lower(), v)
    if col in FORMULAS.get(table, []):
        return rewrite_formula(fix_formula(v), ren)
    return v


Spell = Callable[[str, str, str, dict[str, dict[str, str]]], str]
FixRow = Callable[[str, list[str], list[str]], list[str]]  # (table, source header, source row) -> fixed copy
# (mod header, merged row, source row by column name, D2R's row at that id or None): a project's own fixes, in place
Finish = Callable[[list[str], list[str], dict[str, str], "list[str] | None"], None]


def merge_table(table: str, src: Table, d2r: Table, lines: list[Line], ren: dict[str, dict[str, str]],
                ids: dict[str, dict[str, str]] | None = None, *, spell: Spell = spell, fix_row: FixRow | None = None,
                finish: Finish | None = None, d2r_columns: tuple[str, ...] = (), add_columns: tuple[str, ...] = (),
                source: str = "the source's", num_refs: dict[str, dict[str, str]] | None = None
                ) -> tuple[Table, list[str]]:
    """The mod's table, and the source columns it drops. ids: table -> {source row number: mod id} (ids_of), for
    NUM_REFS columns (num_refs: the project's own map in NUM_REFS' shape, default NUM_REFS). fix_row fixes a source
    row (a copy) before the merge reads it; finish fixes each merged source row before its key and id columns are
    set (chain several with `finishes`); d2r_columns keep D2R's value on a merged row; add_columns are columns D2R's
    file lacks but its loader reads, added when the source has them. `source` names the source in messages."""
    num_refs = NUM_REFS if num_refs is None else num_refs
    added = [c for c in dict.fromkeys(add_columns) if c not in d2r.header and c in src.header]
    if added:  # a copy: the caller's D2R table stays as it was
        d2r = Table.of(d2r.header + added, [r + [""] * len(added) for r in d2r.rows], d2r.newline, d2r.key)
    cols = list(enumerate(source_columns(table, src.header, d2r.header)))
    used = {i for _, i in cols if i is not None}
    dropped = [c for i, c in enumerate(src.header) if i not in used and c.lower() not in ("id", "eol")]
    fix = fix_row or (lambda t, h, r: list(r))
    src_rows = {p.lower(): [v.replace('"', "") for v in fix(table, src.header, src.rows[k])]
                for p, k in zip(ident(src.names()), src.records())}
    id_cols = [j for j, c in enumerate(d2r.header) if c.lower() == "*id" or c == ID_COLS.get(table)]
    nums = {j: num_refs[table][c] for j, c in enumerate(d2r.header) if c in num_refs.get(table, {})}
    keep = {j for j, c in enumerate(d2r.header) if c in d2r_columns}
    out = [list(r) for r in d2r.rows]
    recs = d2r.records()
    appended: list[list[str]] = []
    for p, i, n in sorted((line for line in lines if line[1] != LEFT_OUT), key=lambda line: line[1]):
        row = out[recs[i]] if i < len(recs) else [""] * len(d2r.header)
        if i >= len(recs):
            out.append(row)
            appended.append(row)
        port = port_row(p)
        if port:
            like, sets = port
            row[:] = out[recs[like]] if like < len(recs) else appended[like - len(recs)]
            for c, v in sets.items():
                if c not in d2r.header:
                    raise IdError(f"ids-{table}.tsv: port row '{p}': {table} has no column '{c}'")
                row[d2r.header.index(c)] = v
        else:
            pr = src_rows[p.lower()]
            for j, k in cols:
                if k is None or (j in keep and i < len(recs)):
                    continue
                row[j] = spell(table, d2r.header[j], pr[k], ren)
                if j in nums and row[j]:
                    if row[j] not in (ids or {}).get(nums[j], {}):
                        raise IdError(f"{table} '{n}': {d2r.header[j]} names {source} {nums[j]} row {row[j]}, "
                                      "which has no id")
                    row[j] = ids[nums[j]][row[j]]
            if finish:
                finish(d2r.header, row, dict(zip(src.header, pr)), d2r.rows[recs[i]] if i < len(recs) else None)
        row[d2r.key] = n
        for j in id_cols:
            row[j] = str(i)
    return Table.of(d2r.header, out, d2r.newline, d2r.key), dropped


# --- hooks for merge_table: the generic part of a 1.13c-based port's fixes; the values are the project's ---

# tables whose rows hold item properties (code, [cube: chance,] param, min, max columns): fix_props
PROPS = {"uniqueitems", "setitems", "sets", "runes", "magicprefix", "magicsuffix", "automagic", "cubemain", "gems",
         "qualityitems"}
# tables written by the rule of the table they follow row for row (follow): objtype's rows are objects'
FOLLOWERS = {"objects": "objtype"}
# D2R columns computed from the source row (the column dict a Finish gets), where D2R's own rows hold the value
# but a 1.13c table has no such column. A function returns None to leave the cell as it is. skills rightskill: D2R
# sets it to "not passive" on its class skills only (its non-class, monster skills hold 0), so a non-class source row
# keeps the cell; setitems spawnable and the itemtypes socket level thresholds: the value D2R gives (nearly) every
# one of its own rows (D2R 3.3 build 93847, knowledge/porting-classic-mods.md). Pass a table's entry to derive().
DERIVED = {"skills": {"rightskill": lambda src: None if not src.get("charclass") else
                      "0" if src.get("passive") == "1" else "1"},
           "setitems": {"spawnable": lambda src: "1"},
           "itemtypes": {"MaxSocketsLevelThreshold1": lambda src: "25", "MaxSocketsLevelThreshold2": lambda src: "40"}}
# itemstatcost's description strings and the display columns that print them (stat_display)
STAT_STRINGS, STAT_DISPLAY = ("descstrpos", "descstrneg"), ("descfunc", "descval")

Funcs = dict[str, dict[str, dict[str, str]]]  # table -> column -> {source function number: the mod's}


def make_spell(funcs: Funcs, refs: dict[str, dict[str, str]] | None = None,
               formulas: dict[str, list[str]] | None = None) -> Spell:
    """A Spell that also moves function numbers: a column in `funcs` (the project's map: function numbers D2R gave
    its own functions move to the free slots the project's plugin fills) takes the mapped value. References
    (`refs`, default REFS) and formulas (`formulas`, default FORMULAS) are spelled as `spell` spells them."""
    refs = REFS if refs is None else refs
    formulas = FORMULAS if formulas is None else formulas

    def spell_funcs(table: str, col: str, v: str, ren: dict[str, dict[str, str]]) -> str:
        v = v.replace('"', "")
        if col in refs.get(table, {}):
            return ren.get(refs[table][col], {}).get(v.lower(), v)
        if col in formulas.get(table, []):
            return rewrite_formula(fix_formula(v), ren)
        return funcs.get(table, {}).get(col, {}).get(v, v)
    return spell_funcs


Fixes = dict[str, dict[tuple[str, str], dict[str, str]]]  # table -> (column, bad value) -> the row's new cells


def is_prop_column(name: str) -> bool:
    """Whether a PROPS-table column holds a property code: prop1, mod 1 code, a1mod2code, ... (not index, *ID, par,
    min or max)."""
    low = name.lower()
    return "par" not in low and bool(re.fullmatch(r"prop\d*|mod ?\d+ ?code|a\d+mod\d+code|\w*code\d*", low))


def fix_cells(fixes: Fixes, words: dict[str, str] | None = None, word_tables: set[str] = PROPS) -> FixRow:
    """A FixRow for values no table defines, which D2R's loader refuses: a source row whose `column` holds `bad`
    (quotes aside) gets the new cells (a column the table lacks is skipped). `words`: cell value -> its spelling in
    the property-code columns (is_prop_column) of every table of `word_tables` (a property code in another letter
    case, say); other columns, such as index and *ID, are left alone."""
    def fix(table: str, header: list[str], row: list[str]) -> list[str]:
        row = list(row)
        if words and table in word_tables:
            row = [words.get(v.replace('"', ""), v) if is_prop_column(c) else v for c, v in zip(header, row)] \
                + row[len(header):]
        for (col, bad), cells in fixes.get(table, {}).items():
            if col in header and row[header.index(col)].replace('"', "") == bad:
                for c, v in cells.items():
                    if c in header:
                        row[header.index(c)] = v
        return row
    return fix


def finishes(*fs: Finish | None) -> Finish:
    """One Finish that runs each of fs in order (None skipped)."""
    todo = [f for f in fs if f]

    def run(header: list[str], row: list[str], src: dict[str, str], own: list[str] | None) -> None:
        for f in todo:
            f(header, row, src, own)
    return run


def derive(columns: dict[str, Callable[[dict[str, str]], str | None]]) -> Finish:
    """A Finish setting each column (that the mod's header has) to fn(source row by column name): DERIVED[table]
    plus the project's own. A function that returns None leaves the cell."""
    def run(header: list[str], row: list[str], src: dict[str, str], own: list[str] | None) -> None:
        for c, fn in columns.items():
            v = fn(src) if c in header else None
            if v is not None:
                row[header.index(c)] = v
    return run


def stat_display(d2r: Table) -> Finish:
    """itemstatcost's Finish (D2R 3.3): D2R's stat strings carry the value's format code ('%+d to Strength'), where
    a 1.13c descfunc and descval print the value before the text. A row whose description strings (STAT_STRINGS)
    are ones D2R's rows use takes those rows' display (STAT_DISPLAY): its own D2R row's when the strings are
    unchanged, else the D2R row with the source's descfunc (bytime rows), else the first. A merged row with no
    strings and its D2R row's descfunc keeps D2R's strings (1.13c's descfunc 27/28 hardcode their text, D2R's read
    it from the strings)."""
    str_cols, desc_cols = ([d2r.header.index(c) for c in cs] for cs in (STAT_STRINGS, STAT_DISPLAY))
    shown: dict[tuple[str, ...], list[list[str]]] = {}
    for r in d2r.rows:
        if any(r[j] for j in str_cols):
            shown.setdefault(tuple(r[j] for j in str_cols), []).append([r[j] for j in desc_cols])

    def run(header: list[str], row: list[str], src: dict[str, str], own: list[str] | None) -> None:
        if own and not any(row[j] for j in str_cols) and row[desc_cols[0]] == own[desc_cols[0]]:
            for j in str_cols:
                row[j] = own[j]
        strs = tuple(row[j] for j in str_cols)
        if strs in shown:
            same = [[own[j] for j in desc_cols]] if own and strs == tuple(own[j] for j in str_cols) else []
            by_func = [d for d in shown[strs] if d[0] == row[desc_cols[0]]]
            for j, v in zip(desc_cols, (same or by_func or shown[strs])[0]):
                row[j] = v
    return run


def missile_funcs(rules: list[tuple[str, str, str, str]]) -> Finish:
    """A Finish for do functions that only create a missile: rules are (function column, function number, missile
    column, fallback column). A row with that number drops it and gets the missile in the missile column (from the
    fallback column when the missile column is blank), which D2R's do dispatcher creates after any do function."""
    def run(header: list[str], row: list[str], src: dict[str, str], own: list[str] | None) -> None:
        for func, number, col, fallback in rules:
            if func in header and row[header.index(func)] == number:
                missing = [c for c in (col, fallback) if c not in header]
                if missing:
                    raise IdError(f"missile_funcs: the table has no column {', '.join(missing)} "
                                  f"(function {number} in {func})")
                f, m, a = header.index(func), header.index(col), header.index(fallback)
                row[f] = ""
                if not row[m]:
                    row[m], row[a] = row[a], ""
    return run


def hit_params(params: dict[str, dict[str, str]], ids: dict[str, dict[str, str]],
               func_col: str = "pSrvHitFunc") -> Finish:
    """missiles' Finish for hit functions that read parameters as ids: params is {function number (the mod's, after
    spell): {parameter column: the table it names}}; each such cell takes the mod's id (ids: table -> {source id:
    mod id}), or stays."""
    def run(header: list[str], row: list[str], src: dict[str, str], own: list[str] | None) -> None:
        if func_col not in header:
            return
        for col, t in params.get(row[header.index(func_col)], {}).items():
            if col in header:
                j = header.index(col)
                row[j] = ids.get(t, {}).get(row[j], row[j])
    return run


def fix_props(header: list[str], row: list[str], ren: dict[str, dict[str, str]], ids: dict[str, dict[str, str]],
              props: dict[str, str]) -> None:
    """Skill and state parameters of item properties (code, [cube: chance,] param, min, max columns) in the mod's
    names and ids, by name or by source id; and a cube condition's stat (op 3-26 read `param` as an itemstatcost id,
    D2R's data guide). props: property code -> kind (property_kinds)."""
    def remap(table: str, v: str) -> str:
        return ids.get(table, {}).get(v, v) if v.isdigit() else ren.get(table, {}).get(v.lower(), v)
    if "op" in header and "param" in header:
        op, par = header.index("op"), header.index("param")
        if row[op].isdigit() and 3 <= int(row[op]) <= 26:
            row[par] = ids.get("itemstatcost", {}).get(row[par], row[par])
    low = [c.lower() for c in header] + ["", "", ""]
    for j in range(len(header)):
        p = j + 1 if "par" in low[j + 1] else j + 2 if "chance" in low[j + 1] and "par" in low[j + 2] else None
        kind = props.get(row[j]) if p else None
        if kind in ("skill", "state"):
            row[p] = remap(kind + "s", row[p])
        elif kind == "skillrange" and p + 2 < len(header):  # skill-rand: min and max are a range of skill ids
            row[p + 1], row[p + 2] = remap("skills", row[p + 1]), remap("skills", row[p + 2])
        elif kind == "monster" and p + 2 < len(header):
            mon = ids.get("monstats", {})
            row[p + 1], row[p + 2] = mon.get(row[p + 1], row[p + 1]), mon.get(row[p + 2], row[p + 2])


def props_finish(ren: dict[str, dict[str, str]], ids: dict[str, dict[str, str]], props: dict[str, str]) -> Finish:
    """fix_props as a Finish, for the PROPS tables."""
    return lambda header, row, src, own: fix_props(header, row, ren, ids, props)


def property_kinds(properties: Table, monster_stats: str | None = None) -> dict[str, str]:
    """Property code -> what its parameter names: skill (1.13c's skill-event, charged and single-skill functions 11,
    19, 22), skillrange (12, skill-rand: min-max ids) or state (stat1 `state`). monster_stats: a project's stat name
    prefix whose properties roll a monstats id as min-max (kind monster)."""
    h = {c: j for j, c in enumerate(properties.header)}
    kinds = {}
    for r in properties.rows:
        func, stat = r[h["func1"]], r[h["stat1"]]
        kind = "state" if stat == "state" else "skill" if func in ("11", "19", "22") else "skillrange" if func == "12" else ""
        kind = "monster" if monster_stats and stat.startswith(monster_stats) else kind
        if kind:
            kinds[r[0]] = kind
    return kinds


def monstats_ids(src: Table, d2r: Table) -> dict[str, str]:
    """Source monstats id -> the mod's, for monstats merged by name (tables.py): D2R's rows keep their ids, source-only
    rows follow D2R's last."""
    for who, t in (("D2R", d2r), ("source", src)):
        low = [n.lower() for n in t.names()]
        dup = sorted({n for n in low if low.count(n) > 1})
        if dup:  # D2R's last duplicate would win and a source duplicate would reuse the first id
            raise IdError(f"monstats_ids: {who} monstats names used twice (letter case aside): {', '.join(dup)}")
    mod = {n.lower(): i for i, n in enumerate(d2r.names())}
    added = len(d2r.names())
    for n in src.names():
        if n.lower() not in mod:
            mod[n.lower()], added = added, added + 1
    return {str(k): str(mod[n.lower()]) for k, n in enumerate(src.names())}


def left_out_of(lists: dict[str, list[Line]], src_names: dict[str, list[str]]) -> dict[str, dict[str, str]]:
    """table -> {source row number: ""} for the rows the lists leave out (id '-'): for a project hook that blanks a
    reference to a left-out row instead of failing (ids_of gives such rows no id)."""
    out = {}
    for t, names in src_names.items():
        mod = {p.lower(): i for p, i, _ in lists[t]}
        out[t] = {str(k): "" for k, p in enumerate(ident(names)) if mod[p.lower()] == LEFT_OUT}
    return out


class Context(NamedTuple):
    """What merging any id-listed table needs: the id lists, the names they change, source id -> mod id per table,
    and the property kinds (property_kinds)."""
    lists: dict[str, list[Line]]
    ren: dict[str, dict[str, str]]
    ids: dict[str, dict[str, str]]
    props: dict[str, str]


def context_of(lists: dict[str, list[Line]], src_data: Path, d2r_data: Path | None = None, *,
               id_tables: tuple[str, ...] = ("skills", "states", "itemstatcost"),
               num_refs: dict[str, dict[str, str]] | None = None, monster_stats: str | None = None) -> Context:
    """The Context of id lists already read and checked (lists_for). ids covers id_tables (the tables item properties
    and hit parameters name by id), the tables num_refs columns name and the ID_COLS tables, each that has a list
    with lines; with D2R's data and a monstats table, monstats too (monstats_ids)."""
    num_refs = NUM_REFS if num_refs is None else num_refs
    want = dict.fromkeys([*id_tables, *(t for refs in num_refs.values() for t in refs.values()), *ID_COLS])
    have = [t for t in want if lists.get(t)]
    ids = ids_of(lists, {t: load(src_data, t).names() for t in have})
    if d2r_data is not None and (excel(d2r_data) / "monstats.txt").is_file() \
            and (excel(src_data) / "monstats.txt").is_file():
        ids["monstats"] = monstats_ids(load(src_data, "monstats"), load(d2r_data, "monstats"))
    props_file = excel(src_data) / "properties.txt"
    props = property_kinds(Table(props_file), monster_stats) if props_file.is_file() else {}
    return Context(lists, renames(lists), ids, props)


def excel(root: Path) -> Path:
    return root / "global" / "excel"


def load(data: Path, table: str) -> Table:
    return Table(excel(data) / f"{table}.txt", KEY.get(table))


def lists_for(merge_dir: Path, tables: list[str], src_data: Path, d2r_data: Path, **check_args: str
              ) -> dict[str, list[Line]]:
    """The project's id lists, each checked against both games' tables (check_args: check's source and seed_hint)."""
    lists = {}
    for t in tables:
        lines = read_list(list_path(merge_dir, t))
        check(t, lines, load(src_data, t).names(), load(d2r_data, t).names(), **check_args)
        lists[t] = lines
    return lists


def ids_of(lists: dict[str, list[Line]], src_names: dict[str, list[str]]) -> dict[str, dict[str, str]]:
    """table -> {source row number: mod id}, for the tables in src_names (a checked list covers every row). Left-out
    rows have none, so a reference to one fails the merge."""
    out = {}
    for t, names in src_names.items():
        mod = {p.lower(): i for p, i, _ in lists[t]}
        out[t] = {str(k): str(mod[p.lower()]) for k, p in enumerate(ident(names)) if mod[p.lower()] != LEFT_OUT}
    return out


def write(table: str, merged: Table, out_data: Path, dropped: list[str] | tuple[str, ...] = (),
          source: str = "source") -> None:
    """Write the merged table under out_data; name the dropped source columns (merge_table's second value), if any."""
    dest = excel(out_data) / f"{table}.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(merged.text().encode("latin-1"))
    if dropped:
        print(f"  {table}: {source} columns D2R has no place for: {', '.join(dropped)}")


def seed_lists(merge_dir: Path, tables: list[str], src_data: Path, d2r_data: Path, vanilla: dict[str, int],
               suffix: str) -> dict[str, int]:
    """Append lines for the source rows the lists lack (seed). Returns lines added per table."""
    added = {}
    for t in tables:
        path = list_path(merge_dir, t)
        existing = read_list(path)
        new = seed(t, load(src_data, t).names(), load(d2r_data, t).names(), existing, vanilla.get(t, 0), suffix)
        if new:
            text = path.read_text("utf-8") if path.exists() else "# source name\tid\tname (append-only)\n"
            path.write_text(text + "".join(f"{p}\t{i}\t{n}\n" for p, i, n in new), "utf-8")
        added[t] = len(new)
    return added


def apply(rule: Path, src_data: Path, d2r_data: Path, out_data: Path, tables: list[str],
          followers: dict[str, str] | None = None) -> None:
    """The merge driver's rule kind for merge/ids-<table>.tsv: check the project's lists (`tables`, bound with
    functools.partial) and write that table, references to the listed tables renamed and NUM_REFS columns in the
    mod's ids. A table in `followers` (opt-in; pass FOLLOWERS: objects -> objtype) also writes the table that follows
    it, when both games have it; a project with its own rule for that table leaves it out. A project with its own fixes calls merge_table with its hooks instead."""
    table = rule.stem[len("ids-"):]
    lists = lists_for(rule.parent, tables, src_data, d2r_data)
    nums = {t for refs in NUM_REFS.values() for t in refs.values()} & set(tables)
    ids = ids_of(lists, {t: load(src_data, t).names() for t in nums})
    ren = renames(lists)
    src_table = load(src_data, table)
    write(table, merge_table(table, src_table, load(d2r_data, table), lists[table], ren, ids)[0], out_data)
    f = (followers or {}).get(table)
    if f and all((excel(d) / f"{f}.txt").is_file() for d in (src_data, d2r_data)):
        src, d2r = load(src_data, f), load(d2r_data, f)
        lines = follow(lists[table], src_table.names(), d2r.names(), src.names())
        write(f, merge_table(f, src, d2r, lines, ren)[0], out_data)
