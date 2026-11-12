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
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

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
# monsounds columns naming a sounds row; the source's sounds D2R's table lacks are renamed ("sound"), as D2R's sounds
# table ships as it is
SOUND_COLS = ["Attack1", "Weapon1", "Attack2", "Weapon2", "HitSound", "DeathSound", "Skill1", "Skill2", "Skill3",
              "Skill4", "Footstep", "FootstepLayer", "Neutral", "Init", "Taunt", "Flee"]
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
    # Class and Seller name monstats rows by number, HireDesc a hiredesc code, the SOUND_COLS a sounds row: tables.rule
    # fills the "monster", "hiredesc" and "sound" renames (an absent rename leaves the cell as it is)
    "hireling": {**{f"Skill{i}": "skills" for i in range(1, 7)}, "Class": "monster", "Seller": "monster",
                 "HireDesc": "hiredesc"},
    "monsounds": {**{f"CvtSk{i}": "skills" for i in range(1, 4)}, **{c: "sound" for c in SOUND_COLS}},
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
                source: str = "the source's") -> tuple[Table, list[str]]:
    """The mod's table, and the source columns it drops. ids: table -> {source row number: mod id} (ids_of), for
    NUM_REFS columns. fix_row fixes a source row (a copy) before the merge reads it; finish fixes each merged source
    row before its key and id columns are set; d2r_columns keep D2R's value on a merged row; add_columns are columns
    D2R's file lacks but its loader reads, added when the source has them. `source` names the source in messages."""
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
    nums = {j: NUM_REFS[table][c] for j, c in enumerate(d2r.header) if c in NUM_REFS.get(table, {})}
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


def write(table: str, merged: Table, out_data: Path) -> None:
    dest = excel(out_data) / f"{table}.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(merged.text().encode("latin-1"))


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


def apply(rule: Path, src_data: Path, d2r_data: Path, out_data: Path, tables: list[str]) -> None:
    """The merge driver's rule kind for merge/ids-<table>.tsv: check the project's lists (`tables`, bound with
    functools.partial) and write that table, references to the listed tables renamed and NUM_REFS columns in the
    mod's ids. A project with its own fixes calls merge_table with its hooks instead."""
    table = rule.stem[len("ids-"):]
    lists = lists_for(rule.parent, tables, src_data, d2r_data)
    nums = {t for refs in NUM_REFS.values() for t in refs.values()} & set(tables)
    ids = ids_of(lists, {t: load(src_data, t).names() for t in nums})
    write(table, merge_table(table, load(src_data, table), load(d2r_data, table), lists[table], renames(lists),
                             ids)[0], out_data)
