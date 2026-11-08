"""Tests for shared/classic_import's id lists (run: python -m unittest discover tests). Synthetic names, no game data."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.classic_import import ids  # noqa: E402


class SeedTests(unittest.TestCase):
    def test_vanilla_by_id_then_name_then_append(self):
        # 0: same; 1: a rework of a vanilla row (and its old name re-added later); 2+: added after vanilla
        src = ["Attack", "Cold Enchant", "MonLeap", "New Skill", "Frozen Armor"]
        d2r = ["Attack", "Frozen Armor", "Interact", "MonLeap", "Cold Enchant"]
        self.assertEqual(ids.seed("t", src, d2r, [], vanilla=2, suffix="_old"), [
            ("Attack", 0, "Attack"), ("Cold Enchant", 1, "Frozen Armor"), ("MonLeap", 3, "MonLeap"),
            ("New Skill", 5, "New Skill"), ("Frozen Armor", 6, "Frozen Armor_old")])

    def test_only_appends_for_new_rows_and_skips_port_rows_ids(self):
        existing = [("A", 0, "A"), ("B", 2, "B")]
        self.assertEqual(ids.seed("t", ["A", "B", "C"], ["A", "X"], existing, 0, "_x"), [("C", 3, "C")])
        self.assertEqual(ids.seed("magicprefix", ["A", "B", "C"], ["A", "X"], [("A", 0, "A"), ("+0 x=1", 2, "A")], 2, "_x"),
                         [("B", 1, "B"), ("C", 3, "C")])

    def test_display_keys_keep_the_source_name_and_affixes_never_match_by_name(self):
        self.assertEqual(ids.seed("uniqueitems", ["Shako"], ["Harlequin Crest"], [], 1, "_x"), [("Shako", 0, "Shako")])
        self.assertEqual(ids.seed("magicprefix", ["A", "Sturdy"], ["A", "Sturdy"], [], 1, "_x"),
                         [("A", 0, "A"), ("Sturdy", 2, "Sturdy")])


class CheckTests(unittest.TestCase):
    def test_accepts_a_good_list_with_a_port_row(self):
        ids.check("t", [("A", 0, "A"), ("B", 2, "B")], ["A", "B"], ["A", "X"])
        ids.check("magicprefix", [("A", 0, "A"), ("B", 2, "B"), ("+0 x=1", 3, "A")], ["A", "B"], ["A", "X"])

    def test_refusals(self):
        for lines, src, msg in [
                ([("A", 0, "A")], ["A", "B"], "rows with no id \\(B\\): seed the list$"),
                ([("A", 0, "A"), ("B", 3, "B")], ["A", "B"], "without gaps"),
                ([("A", 0, "Q"), ("B", 2, "B")], ["A", "B"], "D2R's 'A'"),
                ([("A", 0, "A"), ("B", 2, "X")], ["A", "B"], "used twice"),
                ([("A", 0, "A"), ("Z", 2, "Z")], ["A"], "not a source row"),
                ([("A", 0, "A"), ("+0 x=1", 1, "A")], ["A"], "after D2R's rows"),
                ([("A", 0, "A"), ("+3 x=1", 2, "A")], ["A"], "earlier row"),
                ([("A", 0, "A"), ("+0 x", 2, "A")], ["A"], "want"),
                ([("A", 0, "A"), ("B", 2, "x" * 48)], ["A", "B"], "longer than D2R's 47 bytes")]:
            with self.subTest(msg), self.assertRaisesRegex(ids.IdError, msg):
                ids.check("t", lines, src, ["A", "X"])

    def test_messages_name_the_source_and_the_seed_command(self):
        with self.assertRaisesRegex(ids.IdError, r"^ids-t.tsv: 1.09d rows with no id \(B\): run seed$"):
            ids.check("t", [("A", 0, "A")], ["A", "B"], ["A"], source="1.09d", seed_hint="run seed")


class ListTests(unittest.TestCase):
    def test_read_list_left_out_lines_and_bad_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = ids.list_path(Path(tmp), "skills")
            p.write_text("# source name\tid\tname\nA\t0\tA\n#2\t-\tcut\n", "utf-8")
            self.assertEqual(ids.read_list(p), [("A", 0, "A"), ("#2", ids.LEFT_OUT, "cut")])
            p.write_text("A\tx\tA\n", "utf-8")
            with self.assertRaisesRegex(ids.IdError, "ids-skills.tsv line 1: want"):
                ids.read_list(p)
        self.assertEqual(ids.read_list(Path(tmp) / "missing.tsv"), [])

    def test_renames_and_follow(self):
        lines = [("Old", 0, "New"), ("Same", 1, "Same"), ("Cut", ids.LEFT_OUT, "why"), ("+0 a=1", 2, "Copy"),
                 ("Dup#2", 3, "Dup2")]
        self.assertEqual(ids.renames({"skills": lines}), {"skills": {"old": "New", "dup": "Dup2"}})
        self.assertEqual(ids.follow([("a", 0, "A"), ("b", 2, "b"), ("c", ids.LEFT_OUT, "")], ["a", "b", "c"],
                                    ["typeA"], ["ta", "tb", "tc"]), [("ta", 0, "typeA"), ("tb", 2, "tb"), ("tc", -1, "")])


class FormulaTests(unittest.TestCase):
    def test_fix_formula(self):
        for src, want in [("-min(par5 + lvl,60)", "0-min(par5 + lvl,60)"), ("blvl * -50", "blvl * (0-50)"),
                          ("-1 * par5", "(0-1) * par5"), ("-5", "-5"), ("skill('X'.blvl)-3", "skill('X'.blvl)-3"),
                          ("min((par5 + lvl -1), par6)", "min((par5 + lvl -1), par6)"), ("(0 - 2) * -2", "(0 - 2) * (0-2)")]:
            self.assertEqual(ids.fix_formula(src), want)

    def test_rewrite_formula(self):
        ren = {"skills": {"old": "New"}, "missiles": {}, "itemstatcost": {"s": "S2"}}
        self.assertEqual(ids.rewrite_formula("skill('Old'.blvl)+stat('s'.accr)+miss('m'.ln12)", ren),
                         "skill('New'.blvl)+stat('S2'.accr)+miss('m'.ln12)")
        self.assertEqual(ids.rewrite_formula("skill('Old'.blvl)", {}), "skill('Old'.blvl)")  # no skills list


def table(text: str, key: str | None = None) -> ids.Table:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "t.txt"
        p.write_bytes(text.replace("|", "\t").encode("latin-1"))
        return ids.Table(p, key)


NO_RENAMES = {t: {} for t in ("skills", "missiles", "states", "itemstatcost")}


class MergeTableTests(unittest.TestCase):
    def test_overlay_refs_formulas_and_appends(self):
        d2r = table("skill|*Id|reqskill1|calc1|localdelay|srvstopfunc\r\n"
                    "Attack|0||1|0|\r\nFrozen Armor|1||2|0|7\r\n")
        src = table("skill|Id|reqskill1|calc1|delay|general\r\n"
                    "Attack|0||5|0|x\r\nCold Enchant|1|Attack|skill('New Skill'.blvl)|3|\r\n"
                    "New Skill|2|Cold Enchant|skill('Cold Enchant'.lvl)|0|\r\n")
        lines = [("Attack", 0, "Attack"), ("Cold Enchant", 1, "Frozen Armor"), ("New Skill", 2, "New Skill")]
        merged, dropped = ids.merge_table("skills", src, d2r, lines, ids.renames({"skills": lines}))
        self.assertEqual(dropped, ["general"])
        self.assertEqual(merged.rows, [
            ["Attack", "0", "", "5", "0", ""],
            ["Frozen Armor", "1", "Attack", "skill('New Skill'.blvl)", "3", "7"],  # D2R-only srvstopfunc kept
            ["New Skill", "2", "Frozen Armor", "skill('Frozen Armor'.lvl)", "0", ""],
        ])
        self.assertTrue(merged.text().endswith("\r\n"))

    def test_quotes_dropped_and_formulas_in_d2rs_spelling(self):
        d2r = table("skill|calc1|passive\nA|1|0\n")
        src = table('skill|calc1|passive\nA|-"min(lvl,5)"|1\nB|"max(1, 2)"|0\n')
        merged, _ = ids.merge_table("skills", src, d2r, [("A", 0, "A"), ("B", 1, "B")], NO_RENAMES)
        self.assertEqual(merged.rows, [["A", "0-min(lvl,5)", "1"], ["B", "max(1, 2)", "0"]])
        self.assertTrue(merged.text().endswith("\n") and "\r" not in merged.text())

    def test_port_row_copies_an_earlier_row_with_columns_set(self):
        d2r = table("Name|itype1|itype2|rare\r\nSturdy|shld||1\r\nDevil's|amul|circ|1\r\n")
        src = table("Name|itype1|itype2|rare\r\nSturdy|helm||1\r\nNew|ring||\r\n")
        lines = [("Sturdy", 0, "Sturdy"), ("New", 2, "New"), ("+1 itype1=tors itype2= rare=3", 3, "Devil's")]
        merged = ids.merge_table("magicprefix", src, d2r, lines, {})[0]
        self.assertEqual(merged.rows, [["Sturdy", "helm", "", "1"], ["Devil's", "amul", "circ", "1"],
                                       ["New", "ring", "", ""], ["Devil's", "tors", "", "3"]])
        with self.assertRaisesRegex(ids.IdError, "no column 'itype9'"):
            ids.merge_table("magicprefix", src, d2r, [*lines[:2], ("+1 itype9=x", 3, "Devil's")], {})

    def test_add_columns_d2r_loads_but_its_file_lacks(self):
        d2r = table("name|code\r\nArrows|aqv\r\nKey|key\r\n")
        src = table("name|code|auto prefix\r\nArrows|aqv|321\r\nKey|key|\r\n")
        merged, dropped = ids.merge_table("misc", src, d2r, [("Arrows", 0, "Arrows"), ("Key", 1, "Key")], {},
                                          add_columns=("auto prefix",))
        self.assertEqual((merged.header, dropped), (["name", "code", "auto prefix"], []))
        self.assertEqual(merged.rows, [["Arrows", "aqv", "321"], ["Key", "key", ""]])

    def test_expansion_rows_and_display_keys(self):
        # setitems: the source renamed a vanilla row, inserted one mid-table and appended one; D2R added one
        d2r = table("index|*ID|set\nTorch|0|A\nExpansion||\nCow Horns|1|B\nWarlock Hood|2|W\n")
        src = table("index|set\nSpire|A\nExpansion|\nDeath Band|K\nCow Horns|B\nNew One|N\n")
        lines = ids.seed("setitems", src.names(), d2r.names(), [], vanilla=1, suffix="_x")
        self.assertEqual(lines, [("Spire", 0, "Spire"), ("Death Band", 3, "Death Band"), ("Cow Horns", 1, "Cow Horns"),
                                 ("New One", 4, "New One")])
        ids.check("setitems", lines, src.names(), d2r.names())
        merged, _ = ids.merge_table("setitems", src, d2r, lines, {})
        self.assertEqual(merged.rows, [["Spire", "0", "A"], ["Expansion", "", ""], ["Cow Horns", "1", "B"],
                                       ["Warlock Hood", "2", "W"], ["Death Band", "3", "K"], ["New One", "4", "N"]])

    def test_key_column_repeated_and_unnamed_columns_and_column_map(self):
        self.assertEqual(ids.seed("itemtypes", table("ItemType|Code\nNone|\nMap|map\n", "Code").names(),
                                  table("ItemType|Code\nNone|none\nWarlock|warl\n", "Code").names(), [], 1, "_x"),
                         [("", 0, "none"), ("map", 2, "map")])
        armor = ids.merge_table("armor", table("code|DrehyaMax|nameable|mindam|mindam\nxyz|3|1|5|0\n"),
                                table("code|AnyaMax|Nameable|mindam\n"), [("xyz", 0, "xyz")], {})[0]
        self.assertEqual(armor.rows, [["xyz", "3", "1", "5"]])  # a repeated column: the first holds the values
        weapons = ids.merge_table("weapons", table("code||speed\nxyz|15|-10\n"), table("code|speed|UICatOverride\n"),
                                  [("xyz", 0, "xyz")], {})[0]
        self.assertEqual(weapons.rows, [["xyz", "-10", ""]])  # the source's unnamed column fills no D2R column

    def test_add_columns_leaves_the_callers_table_as_it_was(self):
        d2r = table("name|code\nKey|key\n")
        merged, _ = ids.merge_table("misc", table("name|code|auto prefix\nKey|key|9\n"), d2r, [("Key", 0, "Key")], {},
                                    add_columns=("auto prefix", "auto prefix"))
        self.assertEqual((merged.header, merged.rows), (["name", "code", "auto prefix"], [["Key", "key", "9"]]))
        self.assertEqual((d2r.header, d2r.rows), (["name", "code"], [["Key", "key"]]))

    def test_left_out_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "ids-levels.tsv"
            p.write_text("# source name\tid\tname\nA\t0\tA\nPvp Map\t-\tcut: PvP\nB\t2\tB\n", "utf-8")
            lines = ids.read_list(p)
        ids.check("levels", lines, ["A", "Pvp Map", "B"], ["A", "X"])
        merged, _ = ids.merge_table("levels", table("Name|Id\nA|0\nPvp Map|1\nB|2\n"), table("Name|Id\nA|0\nX|1\n"),
                                    lines, ids.renames({"levels": lines}))
        self.assertEqual(merged.rows, [["A", "0"], ["X", "1"], ["B", "2"]])

    def test_numeric_references_id_columns_and_d2r_columns(self):
        # the source's level 3 appends at 4 (D2R took 3): its Vis, a preset's LevelId and the Id columns follow it
        id_map = {"levels": {"0": "0", "1": "1", "3": "4"}, "objgroup": {"0": "0", "2": "5"}}
        lv = ids.merge_table("levels", table("Name|Id|Vis0|ObjGrp0\nNull|0|0|0\nTown|1|3|0\nNew|3|1|2\n"),
                             table("Name|Id|Vis0|ObjGrp0\nNull|0|0|0\nTown|1|0|0\n"),
                             [("Null", 0, "Null"), ("Town", 1, "Town"), ("New", 4, "New")], {}, id_map)[0]
        self.assertEqual(lv.rows[1:], [["Town", "1", "4", "0"], ["New", "4", "1", "5"]])
        pr = ids.merge_table("lvlprest", table("Name|Def|LevelId\nNew 1|7|3\n"), table("Name|Def|LevelId\n"),
                             [("New 1", 9, "New 1")], {}, id_map)[0]
        self.assertEqual(pr.rows, [["New 1", "9", "4"]])
        with self.assertRaisesRegex(ids.IdError, "Vis0 names the source's levels row 2, which has no id"):
            ids.merge_table("levels", table("Name|Vis0\nA|2\n"), table("Name|Vis0\n"), [("A", 0, "A")], {}, id_map)
        ob = ids.merge_table("objects", table("Name|Token|SizeX\nchest|C1|3\nnew|N1|2\n"),
                             table("Class|Name|*ID|Token|SizeX\nChest1|chest|0|hd1|1\n"),
                             [("chest", 0, "Chest1"), ("new", 1, "new")], {}, d2r_columns=("Token",))[0]
        self.assertEqual(ob.rows, [["Chest1", "chest", "0", "hd1", "3"], ["new", "new", "1", "N1", "2"]])

    def test_a_projects_hooks_fix_rows_before_and_after(self):
        seen = []

        def finish(header, row, src, own):
            seen.append((src["calc1"], own))
            row[header.index("calc1")] += "!"

        merged = ids.merge_table("skills", table("skill|calc1\nA|1\nB|2\n"), table("skill|calc1\nA|9\n"),
                                 [("A", 0, "A"), ("B", 1, "B")], NO_RENAMES,
                                 fix_row=lambda t, h, r: [v.replace("2", "3") for v in r], finish=finish,
                                 spell=lambda t, c, v, ren: f"<{v}>")[0]
        self.assertEqual(merged.rows, [["A", "<1>!"], ["B", "<3>!"]])  # the key is the list's name, after the hooks
        self.assertEqual(seen, [("1", ["A", "9"]), ("3", None)])


class SourceColumnsTests(unittest.TestCase):
    def test_the_rename_map_wins_then_the_same_name_first_occurrence_unnamed_none(self):
        # skills: D2R's localdelay is 1.13c's delay, even where the source also has a localdelay column
        self.assertEqual(ids.source_columns("skills", ["skill", "localdelay", "Delay", "", "x", "X"],
                                            ["Skill", "localdelay", "x", "", "new"]), [0, 2, 4, None, None])
        self.assertEqual(ids.source_columns("hireling", ["Hireling", "Resist"], ["ResistFire", "ResistCold"]), [1, 1])

    def test_the_merges_and_the_gate_pair_the_same_columns(self):
        from shared.classic_import import diff, tables
        src = table("skill|localdelay|delay\nA|1|2\n")
        d2r = table("skill|localdelay\nA|0\n")
        by_ids = ids.merge_table("skills", src, d2r, [("A", 0, "A")], {})[0].rows
        by_tables = tables.merge_table("skills", src, d2r, {}).rows
        self.assertEqual(by_ids, by_tables)
        self.assertEqual(by_ids, [["A", "2"]])
        # the gate reads the same pairing: the cell matches, and the unread localdelay is a dropped column
        self.assertEqual(diff.compare("skills", src, ids.Table.of(d2r.header, by_ids)).open,
                         [("skills.*.localdelay", "", "")])


class ListFileTests(unittest.TestCase):
    def test_seed_lists_appends_and_apply_writes_the_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for side, names in (("src", ["A", "B"]), ("d2r", ["A"])):
                for t in ("skills", "levels"):
                    p = root / side / "global" / "excel" / f"{t}.txt"
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text("name\tVis0\n" + "".join(f"{n}\t{'1' if t == 'levels' else ''}\n" for n in names),
                                 "latin-1")
            (root / "merge").mkdir()
            args = (root / "merge", ["skills", "levels"], root / "src", root / "d2r", {"skills": 1}, "_x")
            self.assertEqual(ids.seed_lists(*args), {"skills": 2, "levels": 2})
            self.assertEqual(ids.seed_lists(*args), {"skills": 0, "levels": 0})
            self.assertEqual(ids.read_list(root / "merge" / "ids-skills.tsv"), [("A", 0, "A"), ("B", 1, "B")])
            out = root / "out"
            for t in ("skills", "levels"):
                ids.apply(root / "merge" / f"ids-{t}.tsv", root / "src", root / "d2r", out, ["skills", "levels"])
            self.assertEqual((out / "global/excel/skills.txt").read_text("latin-1"), "name\tVis0\nA\t\nB\t\n")
            # Vis0 holds the source's level 1, which is the mod's 1
            self.assertEqual((out / "global/excel/levels.txt").read_text("latin-1"), "name\tVis0\nA\t1\nB\t1\n")
            (root / "merge" / "ids-skills.tsv").write_text("A\t0\tA\n", "utf-8")
            with self.assertRaisesRegex(ids.IdError, "rows with no id"):
                ids.apply(root / "merge" / "ids-skills.tsv", root / "src", root / "d2r", out, ["skills"])


if __name__ == "__main__":
    unittest.main()
