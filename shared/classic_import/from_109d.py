"""The 1.09d reference tables as 1.13c-shaped tables, through the column-map stage, and back.

    py -3 -m shared.classic_import.from_109d --install <1.09d folder> --patch-113c <1.13c Patch_D2.mpq> <out folder>

forward() runs the column map (data/109d-to-113c-column-map.json) with this module's recode, moved and restructure
functions; back() turns the 1.13c-shaped tables into 1.09d's layout again. back(forward(t)) is t except the map's drop
columns (the tests check it on the real tables). Every recode is a function with an exact inverse, or a lookup whose
inverse is the reversed lookup: a lookup that sends two 1.09d values to one 1.13c value fails when it is reversed, so a
lossy recode cannot pass. A blank cell means "1.09d has no value here"; a merge keeps D2R's own value for it.

The hooks (the project passes its own map or tables to override the defaults):
  * x16 SrcDam / SrcDamage (1.09d eighths -> 1.13c 128ths), `times16` and `by16`
  * a reference by row number -> the referenced row's name (`refs`, `Lookup`): skills, states, missiles, monsters, colors
  * `STATE_FOO` / `STATS_FOO` / `ESOUND_FOO` -> `foo` (`strip`)
  * the monster AI: 1.09d's `BaseId` is NOT a row; it is the index of the monster's record in D2Game's AI table. It becomes
    D2R's `AI` through data/109d-monster-ai.tsv (`AiTable`), the 1.09d value is kept in `*BaseId 1.09d`, and 1.13c's own
    BaseId stays blank. 1.10 moved the AIParam slots, so `AIParam1` is a whole-row recode (`ai_hooks`): an AI with a
    verified slot map (the table's param_slots) gets each 1.09d slot in its D2R slot on all three difficulties, a slot with
    no D2R home goes to `*AIParam 1.09d` ("P5=3"); an AI without a verified map keeps the plain copy (AIParamN -> aipN) and is
    listed by `unverified_ais`. AIParam2-5 are put back from the aip cells and the comment column.
  * `carry_copies`: a name 1.09d repeats in one header (armor mindam/maxdam, automap Type2, chartemplate SkillName) goes out
    as another copy of its target.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Callable

from modkit.tsv import Table

from . import column_map as stage
from . import gen_109d_map as G

DATA = Path(__file__).resolve().parent / "data"
MAP_FILE = DATA / "109d-to-113c-column-map.json"
AI_FILE = DATA / "109d-monster-ai.tsv"
BASE_COMMENT = "*BaseId 1.09d"
PARAM_COMMENT = "*AIParam 1.09d"


def load_map(path: Path | None = None) -> dict:
    """The committed 1.09d -> 1.13c column map."""
    return json.loads((path or MAP_FILE).read_text(encoding="utf-8"))


def parse_slots(text: str) -> dict[int, int] | None:
    """A param_slots cell: "1>1 2>3" -> {1: 1, 2: 3}; "none" -> {} (verified: 1.09d reads none); "" or "unverified" -> None."""
    if text in ("", "unverified"):
        return None
    if text == "none":
        return {}
    try:
        slots = {int(a): int(b) for a, b in (x.split(">") for x in text.split())}
    except ValueError:
        raise stage.MapError(f"param_slots {text!r} is not 'N>M ...', 'none' or 'unverified'") from None
    if len(set(slots.values())) != len(slots):
        raise stage.MapError(f"param_slots {text!r} sends two slots to one")
    return slots


class AiTable:
    """data/109d-monster-ai.tsv: a 1.09d BaseId -> D2R AI, and each AI's AIParam slot map (None = unverified)."""

    def __init__(self, rows: list[dict[str, str]]):
        self.of_base = {r["base_id"]: r["d2r_ai"] for r in rows}
        self.slots: dict[str, dict[int, int] | None] = {}
        for r in rows:
            if r["d2r_ai"]:
                got = parse_slots(r["param_slots"])
                if self.slots.setdefault(r["d2r_ai"], got) != got:
                    raise stage.MapError(f"AI {r['d2r_ai']}: two rows give it different slot maps")

    @classmethod
    def parse(cls, text: str) -> "AiTable":
        lines = text.replace("\r\n", "\n").split("\n")
        header = lines[0].split("\t")
        return cls([dict(zip(header, l.split("\t"))) for l in lines[1:] if l])

    def ai(self, base_id: str) -> str:
        """D2R's AI for a 1.09d BaseId ("" for a blank BaseId or the unused record 0)."""
        if base_id == "":
            return ""
        if base_id not in self.of_base:
            raise stage.MapError(f"BaseId {base_id!r} is not a record of 1.09d's AI table")
        return self.of_base[base_id]

    def slot_map(self, ai: str) -> dict[int, int] | None:
        return self.slots.get(ai)


def load_ai_table(path: Path | None = None) -> AiTable:
    """The committed BaseId -> D2R AI pairing."""
    return AiTable.parse((path or AI_FILE).read_text(encoding="utf-8"))


def ai_hooks(ai: AiTable, column_map: dict) -> tuple[dict[str, tuple[Callable, Callable]], dict[str, Callable]]:
    """(recode, back_only) for monstats.BaseId and AIParam1-5. recode[k] = (fwd(value, row), inv(converted row, n))."""
    to = column_map["tables"]["monstats"]["columns"]["AIParam1"]["to"]
    if len(to) != 16 or to[-1] != PARAM_COMMENT:
        raise stage.MapError("the map's monstats.AIParam1 is not 15 aip cells and the comment column")

    def base_fwd(v: str, row: dict) -> list[str]:
        return [ai.ai(v), v]

    def param_fwd(v: str, row: dict) -> list[str]:
        slots = ai.slot_map(ai.ai(row["BaseId"]))
        cells, extra = dict.fromkeys(to, ""), []
        for i in range(1, 6):
            p = row[f"AIParam{i}"]
            if p == "":
                continue
            dest = i if slots is None else slots.get(i)
            if dest is None:
                extra.append(f"P{i}={p}")
                continue
            for d in ("", "(N)", "(H)"):
                cells[f"aip{dest}{d}"] = p
        cells[PARAM_COMMENT] = " ".join(extra)
        return [cells[t] for t in to]

    def param_inv(c: dict, n: int, i: int) -> str:
        slots = ai.slot_map(ai.ai(c[BASE_COMMENT]))
        if slots is None:
            return c[f"aip{i}"]
        if i in slots:
            return c[f"aip{slots[i]}"]
        return dict(x.split("=") for x in c[PARAM_COMMENT].split()).get(f"P{i}", "")

    recode = {"monstats.BaseId": (base_fwd, lambda c, n: c[BASE_COMMENT]),
              "monstats.AIParam1": (param_fwd, lambda c, n: param_inv(c, n, 1))}
    back_only = {f"monstats.AIParam{i}": (lambda c, n, i=i: param_inv(c, n, i)) for i in range(2, 6)}
    return recode, back_only


def unverified_ais(t9: dict[str, Table], ai: AiTable) -> dict[str, int]:
    """The D2R AIs of 1.09d's monsters whose AIParam slots are not verified on both builds, each with the number of
    monstats rows that have an AIParam value (those rows got the plain copy)."""
    t = t9["monstats"]
    cols = [t.col(f"AIParam{i}") for i in range(1, 6)]
    n: Counter = Counter()
    for r in t.records():
        name = ai.ai(r[t.col("BaseId")])
        if name and ai.slot_map(name) is None and any(r[c] for c in cols):
            n[name] += 1
    return dict(sorted(n.items()))


def tables(files: dict[str, bytes]) -> dict[str, Table]:
    """Every .txt of an extract() version as a Table, by table name."""
    return {n[:-4]: Table.parse(n[:-4], d.decode("latin-1")) for n, d in files.items() if n.endswith(".txt")}


class Lookup:
    """A recode by table: fwd raises on a value it has no entry for, inv on a value two entries share."""

    def __init__(self, name: str, table: dict[str, str]):
        self.name, self.table, self._inv = name, table, None

    def fwd(self, v: str) -> str:
        if v not in self.table:
            raise stage.MapError(f"{self.name}: no entry for {v!r}")
        return self.table[v]

    def inv(self, v: str) -> str:
        if self._inv is None:
            self._inv = {}
            for a, b in self.table.items():
                if b in self._inv:
                    raise stage.MapError(f"{self.name}: {self._inv[b]!r} and {a!r} both become {b!r}")
                self._inv[b] = a
        if v not in self._inv:
            raise stage.MapError(f"{self.name}: nothing becomes {v!r}")
        return self._inv[v]


def refs(name: str, names: list[str], none: str | None) -> Lookup:
    """A reference by record number -> the referenced record's (converted) name; `none` (e.g. "0") -> blank."""
    t = {str(i): n for i, n in enumerate(names)}
    if none is not None:
        t[none] = ""
    return Lookup(name, t)


def strip(prefix: str) -> tuple[Callable, Callable]:
    """STATE_FOO -> foo and back."""
    def fwd(v: str) -> str:
        if not v.startswith(prefix) or v != v.upper():
            raise stage.MapError(f"{v!r} is not {prefix}<UPPER>")
        return v[len(prefix):].lower()
    return fwd, lambda v: prefix + v.upper()


def times16(v: str) -> str:
    return v if v in ("", "-1") else str(int(v) * 16)


def by16(v: str) -> str:
    if v in ("", "-1"):
        return v
    if int(v) % 16:
        raise stage.MapError(f"{v} is not a whole number of eighths")
    return str(int(v) // 16)


class Hooks:
    """The recode, moved and restructure functions for one pair of 1.09d and 1.13c table sets, and their inverses.

    recode[k] = (fwd(value, row) -> value or [value per target], inv(converted row, record) -> 1.09d value)."""

    def __init__(self, t9: dict[str, Table], t13: dict[str, Table], column_map: dict, ai: AiTable):
        self.t13, self.map, self.ai = t13, column_map, ai
        vmap = lambda key: Lookup(key, {a: b["to"] for a, b in column_map["value_maps"][key].items()})  # noqa: E731
        names = lambda t, c: [r[t.col(c)] for r in t.records()]  # noqa: E731
        ids = names(t13["monstats"], "Id")[:len(t9["monstats"].records())]  # 1.09d monstats rows pair with 1.13c's by index
        m9, m13 = t9["missiles"], t13["missiles"]
        # 1.09d missile records pair with 1.13c's by position; 1.13c's names are unique where 1.09d has duplicates
        missile_by_record = [r[0] for r in m13.records()][:len(m9.records())]
        self.missile_names = missile_by_record
        if len(set(missile_by_record)) != len(missile_by_record):
            raise stage.MapError("1.13c missile names are not unique")
        self.missile_back = dict(zip(missile_by_record, (r[0] for r in m9.records())))  # 1.13c name -> 1.09d name
        sk9, sk13 = t9["skills"], t13["skills"]
        # 1.09d skills records pair with 1.13c's by position (same Id); 1.10 renamed some (311 inferno sentry -> mon
        # inferno sentry, 312 death sentry), so every reference by row or name takes 1.13c's name of the record
        if names(sk9, "Id") != names(sk13, "Id")[:len(sk9.records())]:
            raise stage.MapError("1.09d skills Ids do not pair with 1.13c's by position")
        skill_names = names(sk13, "skill")[:len(sk9.records())]
        if len(set(names(sk9, "skill"))) != len(skill_names) or len(set(skill_names)) != len(skill_names):
            raise stage.MapError("skill names are not unique")
        skill_rename = Lookup("skills name", dict(zip(names(sk9, "skill"), skill_names)))
        self.skill_names = skill_names
        state_fwd, state_inv = strip("STATE_")
        states = [state_fwd(v) for v in names(t9["states"], "state")]
        stat_fwd, stat_inv = strip("STATS_")
        isc = t9["itemstatcost"]
        stats = {r[isc.col("ID")]: stat_fwd(r[0]) for r in isc.records()}
        colors = names(t13["colors"], "Code")
        L = {
            "skill": refs("skills row", skill_names, "0"),
            "state": refs("states row", states, "0"),
            "missile": refs("missiles row", missile_by_record, "65535"),
            "monster": refs("monstats row", ids, None),
            "critter": refs("monstats row", ids, "0"),
            "stat": Lookup("itemstatcost ID", {**stats, "-1": ""}),
            "color": refs("colors row", colors, None),
            "anim": vmap("skills.anim"), "monanim": vmap("skills.monanim"), "seq": vmap("monstats.SkillSeq"),
            **{t: vmap(f"{t}.sound") for t in ("armor", "weapons", "misc")},
        }
        self.lookups = L
        OPS = {"Percent": ("13", "5"), "PerLevel": ("2", "4", "5"), "ByTime": ("6", "7")}
        item_local = {k for k, v in stats.items() if v in ("armorclass", "maxdamage")}  # scale with the item's base

        def op(v: str, row: dict) -> str:
            # 1.09d's flags -> 1.10's op for them. No flag -> blank (D2R keeps its op).
            p, lvl, t = (row[c] == "1" for c in OPS)
            if p + lvl + t == 0:
                return ""
            local = row["Target Stat"] in item_local
            if t and not (p or lvl):
                return "7" if local and "PERCENT" in row["Stat"] else "6"
            if lvl:
                return "5" if p else "4" if local else "2"
            if p:
                return "13"
            raise stage.MapError(f"stat {row['ID']}: flags {[row[c] for c in OPS]} have no op")

        R: dict[str, tuple[Callable, Callable]] = {}
        self.back_only: dict[str, Callable] = {}

        def lk(key: str, lookup: Lookup, target: str | None = None, keep: str | None = None):
            target = target or key.split(".", 1)[1]
            if keep:
                R[key] = (lambda v, row: [lookup.fwd(v), v], lambda c, n: c[keep])
            else:
                R[key] = (lambda v, row: lookup.fwd(v), lambda c, n: lookup.inv(c[target]))

        lk("charstats.StartSkill", L["skill"])
        isc_fwd = {"Stat": (lambda v, row: stat_fwd(v), lambda c, n: stat_inv(c["Stat"])),
                   "Target Stat": (lambda v, row: L["stat"].fwd(v), lambda c, n: L["stat"].inv(c["op stat1"]))}
        for k, f in isc_fwd.items():
            R[f"itemstatcost.{k}"] = f
        for c, codes in OPS.items():
            R[f"itemstatcost.{c}"] = (op, lambda conv, n, codes=codes: "1" if conv["op"] in codes else "")
        for i in range(1, 11):
            R[f"levels.M{i}"] = (lambda v, row, i=i: [self._mon(row, "Mtot", i, v)] * 2 + [self._unused(row)],
                                 lambda c, n, i=i: self._mon_back(c, i))
            R[f"levels.U{i}"] = (lambda v, row, i=i: self._mon(row, "Utot", i, v),
                                 lambda c, n, i=i: L["monster"].inv(c[f"umon{i}"]) if c[f"umon{i}"] else "0")
        for i in range(1, 5):
            lk(f"levels.C{i}", L["critter"], f"cmon{i}")
        for t in ("armor", "weapons", "misc"):
            R[f"{t}.sound"] = (lambda v, row, t=t: L[t].fwd(v), lambda c, n, t=t: L[t].inv(c["dropsound"]))
        lk("missiles.Skill", L["skill"])
        R["missiles.SrcDamage"] = (lambda v, row: times16(v), lambda c, n: by16(c["SrcDamage"]))
        ai_recode, ai_back = ai_hooks(ai, column_map)
        R.update(ai_recode)
        self.back_only.update(ai_back)
        MISS = [f"Miss{m}" for m in "A1 A2 S1 S2 S3 S4 C SQ".split()]

        def invalid(row: dict) -> str:
            """"MissA1=65536 ..." for the Miss columns naming no missile (past the last row)."""
            return " ".join(f"{c}={row[c]}" for c in MISS if row[c] not in L["missile"].table)

        def miss_back(c: dict, col: str) -> str:
            bad = dict(x.split("=") for x in c["*invalid refs 1.09d"].split())
            return bad[col] if col in bad else L["missile"].inv(c[col])

        for col in MISS:
            R[f"monstats.{col}"] = (lambda v, row: [L["missile"].fwd(v) if v in L["missile"].table else "", invalid(row)],
                                    lambda c, n, col=col: miss_back(c, col))
        for i in range(1, 6):
            lk(f"monstats.Skill{i}", L["skill"])
            lk(f"monstats.Skill{i}Seq", L["seq"], f"Sk{i}mode", keep=f"*Skill{i}Seq 1.09d")
        lk("skills.anim", L["anim"], keep="*anim 1.09d")
        lk("skills.monanim", L["monanim"], keep="*monanim 1.09d")
        R["skills.skill"] = (lambda v, row: skill_rename.fwd(v), lambda c, n: skill_rename.inv(c["skill"]))
        R["skills.reqskill1"] = (lambda v, row: skill_rename.fwd(v) if v else "",
                                 lambda c, n: skill_rename.inv(c["reqskill1"]) if c["reqskill1"] else "")
        for i in (1, 2, 3):
            lk(f"skills.State{i}", L["state"])
        R["skills.SrcDam"] = (lambda v, row: times16(v), lambda c, n: by16(c["SrcDam"]))
        snd_fwd, snd_inv = strip("ESOUND_")
        R["sounds.Handle"] = (lambda v, row: snd_fwd(v), lambda c, n: snd_inv(c["Sound"]))
        R["states.state"] = (lambda v, row: state_fwd(v), lambda c, n: state_inv(c["state"]))
        lk("superuniques.Class", L["monster"])
        # uniqueitems: transform=1 tints the item with transformcolor (a blank number is row 0); invtransform=1 the
        # inventory picture too. 1.13c: chrtransform/invtransform name the colour, blank = no tint.
        tint = lambda row: L["color"].fwd(row["transformcolor"] or "0") if row["transform"] == "1" else ""  # noqa: E731
        R["uniqueitems.transformcolor"] = (lambda v, row: tint(row),
                                           lambda c, n: L["color"].inv(c["chrtransform"]) if c["chrtransform"] else "")
        R["uniqueitems.invtransform"] = (lambda v, row: tint(row) if v == "1" else "",
                                         lambda c, n: "1" if c["invtransform"] else "0")
        self.recode = R
        self.back_only["uniqueitems.transform"] = lambda c, n: "1" if c["chrtransform"] else "0"

        s13 = t13["skills"]
        desc13 = {r[s13.col("skill")].lower(): r[s13.col("skilldesc")] for r in s13.records()}
        # skilldesc row per 1.09d skills record: 1.13c's skilldesc for the skill (else the skill name, lower-case); a
        # name a previous record already took (monster copies such as DiabWall share firestorm) gets " #<Id>"
        desc_keys, taken = [], set()
        for r, name in zip(sk9.records(), skill_names):
            k = desc13.get(name.lower()) or name.lower()
            if k in taken:
                k = f"{k} #{r[sk9.col('Id')]}"
            if k in taken:
                raise stage.MapError(f"skills {r[0]!r}: skilldesc key {k!r} is taken twice")
            taken.add(k)
            desc_keys.append(k)
        self.moved = {"monstats.monstats2": ("Id", lambda n, row: ids[n]),
                      "montype.monstats2": ("Id", lambda n, row: ids[n]),
                      "skills.skilldesc": ("skilldesc", lambda n, row: desc_keys[n])}
        self.moved_back = {"monstats.monstats2": lambda n, c: ids[n], "montype.monstats2": lambda n, c: ids[n],
                           "skills.skilldesc": lambda n, c: desc_keys[n]}
        self.restructure = {"setitems": self.sets, "hireling": self.hireling, "missiles": self.missiles}
        self.colors = L["color"]

    def _mon(self, row: dict, total: str, i: int, v: str) -> str:
        # M1..M10 / U1..U10 past Mtot / Utot are unused: blank (a U slot past Utot must be 0; M ones go to _unused)
        n = int(row[total] or 0)
        if i > n:
            if v not in ("", "0") and total != "Mtot":
                raise stage.MapError(f"slot {i} past {total} {n} holds {v}")
            return ""
        return self.lookups["monster"].fwd(v)

    @staticmethod
    def _unused(row: dict) -> str:
        """"M3=134 ..." for the M1-M10 slots past Mtot that are not 0: values 1.09d holds but does not spawn."""
        n = int(row["Mtot"] or 0)
        return " ".join(f"M{i}={row[f'M{i}']}" for i in range(n + 1, 11) if row[f"M{i}"] not in ("", "0"))

    def _mon_back(self, c: dict, i: int) -> str:
        unused = dict(x.split("=") for x in c["*unused M 1.09d"].split())
        if f"M{i}" in unused:
            return unused[f"M{i}"]
        return self.lookups["monster"].inv(c[f"mon{i}"]) if c[f"mon{i}"] else "0"

    # ---- restructures
    SET_ITEM = (("", "item"), (" Suffix", "index"), (" Rarity", "rarity"), (" Add", "add func"), (" Lvlreq", "lvl req"),
                (" LvlReq", "lvl req"), (" cost mult", "cost mult"), (" cost add", "cost add"))
    PROP = (("Code", "prop"), ("Param", "par"), ("Min", "min"), ("Max", "max"))

    def set_columns(self, header: list[str], n: int) -> list[tuple[str, str]]:
        """(1.09d column, 1.13c setitems column) of item n's block."""
        out = [(f"Item{n}{a}", b) for a, b in self.SET_ITEM if f"Item{n}{a}" in header]
        for a, b in self.PROP:
            out += [(f"I{n}{a}{k}", f"{b}{k}") for k in (1, 2)]
            out += [(f"I{n}{a}{L}", f"a{b}{j}a") for j, L in enumerate("ABCDE", 1)]
        return out

    def set_columns_set(self) -> list[tuple[str, str]]:
        out = [(f"P{a}{k}", f"P{a}{k}a") for k in range(2, 6) for a, _ in self.PROP]
        return out + [(f"F{a}{k}", f"F{a}{k}") for k in range(1, 7) for a, _ in self.PROP]

    def sets(self, src: Table, conv: Table) -> dict[str, Table]:
        h13s, h13i = self.t13["sets"].header, self.t13["setitems"].header
        sets, items = Table("sets", list(h13s), []), Table("setitems", list(h13i), [])
        for row in src.rows:
            d = dict(zip(src.header, row))
            if not src.is_record(row):
                sets.rows.append([row[0]] + [""] * (len(h13s) - 1))
                items.rows.append([row[0]] + [""] * (len(h13i) - 1))
                continue
            sets.append({"index": d["Name"], "name": d["Name"], "version": d["version"], "level": d["level"],
                         **{b: d[a] for a, b in self.set_columns_set()}})
            tint = self.colors.fwd(d["transformcolor"] or "0") if d["transform"] == "1" else ""
            for n in range(1, 7):
                cols = self.set_columns(src.header, n)
                vals = {b: d[a] for a, b in cols}
                if not vals["item"]:
                    if any(v.strip() for v in vals.values()):
                        raise stage.MapError(f"set {d['Name']}: empty item {n} has values")
                    continue
                items.append({**vals, "set": d["Name"], "lvl": d["level"], "chrtransform": tint})
        return {"sets": sets, "setitems": items}

    def missiles(self, src: Table, conv: Table) -> dict[str, Table]:
        names, rows = iter(self.missile_names), []
        for row, crow in zip(src.rows, conv.rows):
            rows.append([row[0] if not src.is_record(row) else next(names)] + crow)
        return {"missiles": Table("missiles", ["Missile"] + conv.header, rows)}

    def hireling(self, src: Table, conv: Table) -> dict[str, Table]:
        # 1.09d's 60 rows are one set: they become 1.13c's expansion rows (Version 100); D2R keeps its classic ones
        return {"hireling": Table("hireling", ["Version"] + conv.header, [["100"] + r for r in conv.rows])}

    def sets_back(self, out: dict[str, Table], header: list[str]) -> list[list[str]]:
        sets, items = out["sets"], out["setitems"]
        rows = []
        for srow in sets.rows:
            if not sets.is_record(srow):
                rows.append([srow[0]] + [""] * (len(header) - 1))
                continue
            s = dict(zip(sets.header, srow))
            d = {c: "" for c in header}
            d.update(Name=s["name"], version=s["version"], level=s["level"])
            d.update({a: s[b] for a, b in self.set_columns_set()})
            mine = [dict(zip(items.header, r)) for r in items.records() if r[items.col("set")] == s["index"]]
            for n, it in enumerate(mine, 1):
                d.update({a: it[b] for a, b in self.set_columns(header, n)})
            tint = mine[0]["chrtransform"] if mine else ""
            d["transform"] = "1" if tint else "0"
            d["transformcolor"] = self.colors.inv(tint) if tint else ""
            rows.append([d[c] for c in header])
        return rows


COPYABLE = ("same", "rename")


def nth(header: list[str], col: str, k: int) -> int | None:
    """Position of the k-th copy (from 0) of col in header."""
    at = [i for i, c in enumerate(header) if c == col]
    return at[k] if k < len(at) else None


def carry_copies(t9: dict[str, Table], out: dict[str, Table], column_map: dict) -> None:
    """A name 1.09d repeats in one header (armor mindam/maxdam, automap Type2, chartemplate SkillName x9) is one map
    entry, and the stage reads only its first copy. 1.13c repeats the same names in the same places, so every later
    copy goes out as another copy of its target, after the column it follows in 1.09d."""
    for name, src in t9.items():
        cols, o = column_map["tables"][name]["columns"], out.get(name)
        for i, col in enumerate(src.header):
            if not col or src.header.index(col) == i or cols[col]["kind"] == "drop":
                continue
            m = cols[col]
            if m["kind"] not in COPYABLE or len(m["to"]) != 1 or o is None:
                raise stage.MapError(f"{name}.{col}: a repeated {m['kind']} column has no copy rule")
            pos = 0
            for p in range(i - 1, -1, -1):
                pm = cols.get(src.header[p])
                if pm and pm["kind"] != "drop" and pm["to"]:
                    at = nth(o.header, pm["to"][0], src.header[:p].count(src.header[p]))
                    if at is not None:
                        pos = at + 1
                        break
            o.header.insert(pos, m["to"][0])
            for srow, orow in zip(src.rows, o.rows):
                orow[len(orow):pos] = [""] * (pos - len(orow))
                orow.insert(pos, (srow[i] if i < len(srow) else "") if src.is_record(srow) else "")


def forward(t9: dict[str, Table], t13: dict[str, Table], column_map: dict | None = None,
            ai: AiTable | None = None) -> dict[str, Table]:
    """The 1.09d tables in 1.13c's schema. column_map and ai default to the committed data/ files."""
    column_map, ai = column_map or load_map(), ai or load_ai_table()
    h = Hooks(t9, t13, column_map, ai)
    rec = {k: f for k, (f, _) in h.recode.items()}
    out = stage.apply(column_map, t9, recode=rec, moved=h.moved, restructure=h.restructure)
    carry_copies(t9, out, column_map)
    return out


def back(out: dict[str, Table], t9: dict[str, Table], t13: dict[str, Table], column_map: dict | None = None,
         ai: AiTable | None = None) -> dict[str, Table]:
    """1.13c-shaped tables (forward's output) in 1.09d's layout again: every column the map keeps, drop columns
    blank. t9 gives only the layout (headers) and the lookups' domains; no cell of it is copied."""
    column_map, ai = column_map or load_map(), ai or load_ai_table()
    h = Hooks(t9, t13, column_map, ai)
    res = {}
    for name, src in t9.items():
        cols = column_map["tables"][name]["columns"]
        if name == "setitems":
            res[name] = Table(name, src.header, h.sets_back(out, src.header))
            continue
        conv = out[name]
        crows = conv.rows
        if name == "hireling":
            conv = Table(name, conv.header[1:], [r[1:] for r in crows])
            crows = conv.rows
        rows, n = [], -1
        for i, crow in enumerate(crows):
            # a table with no columns left (montype) has empty rows: its separators are where 1.09d's are
            sep = not src.is_record(src.rows[i]) if not crow else not conv.is_record(crow)
            if sep:
                rows.append([crow[0] if crow else src.rows[i][0]] + [""] * (len(src.header) - 1))
                continue
            n += 1
            c = {}
            for hc, v in zip(conv.header, crow):
                c.setdefault(hc, v)  # a repeated name: its first copy; carry_copies' later ones are read by position
            row = []
            for j, col in enumerate(src.header):
                m, k_ = cols.get(col), f"{name}.{col}"
                if not col or m is None or m["kind"] == "drop":
                    row.append("")
                elif (k := src.header[:j].count(col)) and m["kind"] in COPYABLE:
                    at = nth(conv.header, m["to"][0], k)
                    row.append(crow[at] if at is not None and at < len(crow) else "")
                elif m["kind"] in ("same", "rename", "split"):
                    row.append(c[m["to"][0]])
                elif m["kind"] == "recode":
                    k = f"{name}.{col}"
                    row.append(h.back_only[k](c, n) if k in h.back_only else h.recode[k][1](c, n))
                elif m["kind"] == "restructure" and k_ == "missiles.Missile":
                    row.append(h.missile_back[c["Missile"]])
                elif m["kind"] == "moved":
                    other, oc = m["to"][0].split(".", 1)
                    key_col, _ = h.moved[f"{name}.{other}"]
                    o = out[other]
                    r = o.find(h.moved_back[f"{name}.{other}"](n, c), key_col)
                    row.append(o.get(r, oc) if r is not None else "")
                else:
                    raise stage.MapError(f"{name}.{col}: kind {m['kind']} has no inverse")
            rows.append(row)
        res[name] = Table(name, src.header, rows)
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", type=Path, help="folder for the 1.13c-shaped tables (game data: never commit them)")
    ap.add_argument("--install", help="the 1.09d folder (or D2_109D_INSTALL)")
    ap.add_argument("--patch-113c", help="1.13c's Patch_D2.mpq (or D2_113C_PATCH)")
    args = ap.parse_args(argv)
    try:
        ex = G.extract(*G.inputs(args.install, args.patch_113c))
        t9, t13 = tables(ex["y109"]), tables(ex["y113"])
        ai = load_ai_table()
        out = forward(t9, t13, ai=ai)
    except (G.GenError, stage.MapError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    written = 0
    for name, t in sorted(out.items()):
        if t.header:  # 1.09d montype moves wholly into monstats2; an empty file would replace 1.13c's unrelated montype
            (args.out / f"{name}.txt").write_bytes(t.text().encode("latin-1"))
            written += 1
    print(f"{written} tables -> {args.out}")
    un = unverified_ais(t9, ai)
    print(f"AIParam slots unverified (plain copy) for {len(un)} AIs: " + ", ".join(f"{a} ({n})" for a, n in un.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
