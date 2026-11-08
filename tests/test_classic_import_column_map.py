"""Tests for shared/classic_import's column-map stage (run: python -m unittest discover tests). Synthetic tables."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modkit.tsv import Table  # noqa: E402
from shared.classic_import import column_map as cm  # noqa: E402


def tab(name: str, *lines: str) -> Table:
    return Table.parse(name, "\n".join(lines) + "\n")


def col(to, kind) -> dict:
    return {"to": to if isinstance(to, list) else [to], "kind": kind}


def rows(t: Table) -> list[list[str]]:
    return [t.header] + t.rows


class KindTests(unittest.TestCase):
    def test_same_rename_split_and_drop(self):  # and a repeated column (1.09d armor's mindam) reads as its first
        m = {"tables": {"t": {"columns": {"a": col("a", "same"), "b": col("B", "rename"),
                                          "c": col(["c1", "c2"], "split"), "d": col([], "drop")}}}}
        out = cm.apply(m, {"t": tab("t", "a\tb\tc\td\tb", "x\t1\t2\t3\t9", "Expansion", "y\t4\t5\t6\t9")})
        self.assertEqual(rows(out["t"]), [["a", "B", "c1", "c2"], ["x", "1", "2", "2"], ["Expansion", "", "", ""],
                                          ["y", "4", "5", "5"]])

    def test_recode_with_a_row_name_lookup(self):
        skills = tab("skills", "skill\tid", "Attack\t0", "Expansion", "Kick\t1")
        m = {"tables": {"missiles": {"columns": {
            "name": col("name", "same"), "Skill": col("Skill", "recode"), "lvl": col(["lo", "hi"], "recode"),
            "flag": col([], "recode")}}}}
        src = tab("missiles", "name\tSkill\tlvl\tflag", "arrow\t1\t3\t1", "none\t0\t\t0")
        recode = {"missiles.Skill": cm.row_name(skills, "skill", none=("0",)),
                  "missiles.lvl": lambda v, row: [v, str(int(v or 0) * 2) if row["flag"] == "1" else ""]}
        out = cm.apply(m, {"missiles": src}, recode)
        self.assertEqual(rows(out["missiles"]), [["name", "Skill", "lo", "hi"], ["arrow", "Kick", "3", "6"],
                                                 ["none", "", "", ""]], "separator rows are not records")
        src.rows[0][1] = "2"
        with self.assertRaisesRegex(cm.MapError, r"^missiles record 0, Skill: skills has no record '2'$"):
            cm.apply(m, {"missiles": src}, recode)

    def test_moved_makes_or_joins_the_other_tables_rows(self):
        m = {"tables": {"skills": {"columns": {"skill": col("skill", "same"), "desc": col("desc", "same"),
                                               "Page": col("skilldesc.SkillPage", "moved")}},
                        "monstats": {"columns": {"Id": col("Id", "same"), "Size": col("monstats2.SizeX", "moved")}},
                        "monstats2": {"columns": {"Id": col("Id", "same"), "Height": col("Height", "same")}}}}
        out = cm.apply(m, {"skills": tab("skills", "skill\tdesc\tPage", "Attack\tatk\t1", "Kick\tkck\t2"),
                           "monstats": tab("monstats", "Id\tSize", "zombie\t2", "bat\t1"),
                           "monstats2": tab("monstats2", "Id\tHeight", "Bat\t4")},
                       moved={"skills.skilldesc": ("skilldesc", lambda n, row: row["desc"]),
                              "monstats.monstats2": ("Id", lambda n, row: row["Id"])})
        self.assertEqual(rows(out["skilldesc"]), [["skilldesc", "SkillPage"], ["atk", "1"], ["kck", "2"]])
        self.assertEqual(rows(out["monstats2"]), [["Id", "Height", "SizeX"], ["Bat", "4", "1"], ["zombie", "", "2"]])

    def test_restructure_replaces_the_table(self):
        m = {"tables": {"setitems": {"restructure": "one row per set -> sets + setitems", "columns": {
                 "Name": col(["sets.name", "set"], "restructure"), "Item1": col("item", "restructure")}},
             "hireling": {"restructure": "rows doubled", "columns": {"Hireling": col("Hireling", "same"),
                                                                     "Chance1": col("ChancePerLvl1", "rename")}}}}

        def sets(src, conv):
            self.assertEqual(conv.header, [])
            return {"sets": Table("sets", ["name"], [[r[0]] for r in src.rows]),
                    "setitems": Table("setitems", ["item", "set"], [[r[1], r[0]] for r in src.rows])}

        def doubled(src, conv):
            return {"hireling": Table("hireling", ["Version"] + conv.header,
                                      [[v] + r for v in ("0", "100") for r in conv.rows])}

        out = cm.apply(m, {"setitems": tab("setitems", "Name\tItem1", "Angelic\tsbr"),
                           "hireling": tab("hireling", "Hireling\tChance1", "Rogue\t5")},
                       restructure={"setitems": sets, "hireling": doubled})
        self.assertEqual(rows(out["sets"]), [["name"], ["Angelic"]])
        self.assertEqual(rows(out["setitems"]), [["item", "set"], ["sbr", "Angelic"]])
        self.assertEqual(rows(out["hireling"]), [["Version", "Hireling", "ChancePerLvl1"], ["0", "Rogue", "5"],
                                                 ["100", "Rogue", "5"]])
        self.assertEqual(set(out), {"sets", "setitems", "hireling"})


class FailureTests(unittest.TestCase):
    M = {"tables": {"t": {"columns": {"a": col("a", "same"), "b": col("b", "recode")}}}}

    def fails(self, msg: str, m: dict | None = None, t: Table | None = None, **hooks) -> None:
        hooks.setdefault("recode", {"t.b": lambda v, row: v})
        with self.assertRaisesRegex(cm.MapError, msg):
            cm.apply(m or self.M, {"t": t or tab("t", "a\tb", "1\t2")}, **hooks)

    def test_a_column_the_map_does_not_cover(self):
        self.fails(r"^t: columns the map doesn't cover: c$", t=tab("t", "a\tb\tc", "1\t2\t3"))

    def test_a_map_column_the_table_lacks(self):
        self.fails(r"^t: map columns not in the table: b$", t=tab("t", "a", "1"))

    def test_an_unknown_kind(self):
        self.fails(r"^t.a: kind 'unmapped' is not one of same, ",
                   {"tables": {"t": {"columns": {"a": col([], "unmapped"), "b": col([], "drop")}}}}, recode={})

    def test_a_table_not_in_the_map(self):
        with self.assertRaisesRegex(cm.MapError, r"^u: not a source table"):
            cm.apply(self.M, {"u": tab("u", "a", "1")})

    def test_missing_and_stale_functions(self):
        self.fails(r"^t.b: recode needs a function$", recode={})
        self.fails(r"^recode functions the map has no use for: t.a$", recode={"t.a": str, "t.b": str})
        self.fails(r"^t.a: moved to 'x.a' needs a key function",
                   {"tables": {"t": {"columns": {"a": col("x.a", "moved"), "b": col([], "drop")}}}}, recode={})
        self.fails(r"^t: restructure needs a function$",
                   {"tables": {"t": {"restructure": "", "columns": {"a": col("a", "same"), "b": col([], "drop")}}}},
                   recode={})

    def test_two_columns_giving_one_cell_different_values(self):
        m = {"tables": {"isc": {"columns": {"Percent": col("op", "recode"), "PerLevel": col("op", "recode")}}}}
        recode = {"isc.Percent": lambda v, row: "13" if v == "1" else "",
                  "isc.PerLevel": lambda v, row: "2" if v == "1" else ""}
        out = cm.apply(m, {"isc": tab("isc", "Percent\tPerLevel", "1\t0", "0\t1", "0\t0")}, recode)
        self.assertEqual(rows(out["isc"]), [["op"], ["13"], ["2"], [""]])
        with self.assertRaisesRegex(cm.MapError, r"^isc record 0: op gets '13' from Percent and '2' from PerLevel$"):
            cm.apply(m, {"isc": tab("isc", "Percent\tPerLevel", "1\t1")}, recode)


if __name__ == "__main__":
    unittest.main()
