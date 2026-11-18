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

    def test_port_rows_may_share_text_but_not_ids(self):
        ids.check("t", [("A", 0, "A"), ("+0 x=1", 2, "B"), ("+0 x=1", 3, "C")], ["A"], ["A", "X"])
        with self.assertRaisesRegex(ids.IdError, "listed twice"):
            ids.check("t", [("A", 0, "A"), ("A", 2, "B")], ["A"], ["A", "X"])

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

    def test_port_row_quoted_columns_and_copy_of_a_port_row(self):
        self.assertEqual(ids.port_row("+3 a=1 \"Send Bits=11\" b=it's c="), (3, {"a": "1", "Send Bits": "11", "b": "it's", "c": ""}))
        self.assertEqual(ids.port_row(r"+2 x=a\b"), (2, {"x": r"a\b"}))
        with self.assertRaisesRegex(ids.IdError, "unclosed"):
            ids.port_row('+1 "a=1')
        d2r = table("name|Send Bits|Add\r\nA|1|0\r\n")
        src = table("name|Send Bits|Add\r\nA|1|0\r\n")
        lines = [("A", 0, "A"), ('+0 "Send Bits=11" Add=5', 1, "B"), ('+1 "Send Bits=12"', 2, "C")]
        merged = ids.merge_table("t", src, d2r, lines, {})[0]
        self.assertEqual(merged.rows, [["A", "1", "0"], ["B", "11", "5"], ["C", "12", "5"]])

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

    def test_apply_writes_the_follower_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {"src": {"objects": "Name\nchest\nwell\nnew\n", "objtype": "Name\nChest\nWell\nNew\n"},
                     "d2r": {"objects": "Name\nchest\nwell\n", "objtype": "Name\nCasket\nWell\n"}}
            for side, tables in files.items():
                for t, text in tables.items():
                    p = root / side / "global" / "excel" / f"{t}.txt"
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(text, "latin-1")
            (root / "merge").mkdir()
            (root / "merge" / "ids-objects.tsv").write_text("chest\t0\tchest\nwell\t1\twell\nnew\t2\tnew\n", "utf-8")
            rule = root / "merge" / "ids-objects.tsv"
            ids.apply(rule, root / "src", root / "d2r", root / "out", ["objects"])
            self.assertFalse((root / "out/global/excel/objtype.txt").exists())  # opt-in: a project may have its own
            ids.apply(rule, root / "src", root / "d2r", root / "out", ["objects"], followers=ids.FOLLOWERS)
            # objtype follows objects row for row: D2R's names on merged rows, the source's on the appended one
            self.assertEqual((root / "out/global/excel/objtype.txt").read_text("latin-1"), "Name\nCasket\nWell\nNew\n")
            (root / "src/global/excel/objtype.txt").write_text("Name\nChest\n", "latin-1")
            with self.assertRaisesRegex(ids.IdError, "match row for row"):
                ids.apply(rule, root / "src", root / "d2r", root / "out", ["objects"], followers=ids.FOLLOWERS)


def table(text: str, key: str | None = None) -> ids.Table:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "t.txt"
        p.write_bytes(text.replace("|", "\t").encode("latin-1"))
        return ids.Table(p, key)


class TableReaderTests(unittest.TestCase):
    def test_keeps_crlf_or_lf_and_pads_short_rows(self):
        t = table("a|b|c\r\nx|1\r\ny|2|3|4\r\n\r\n")
        self.assertEqual((t.newline, t.rows), ("\r\n", [["x", "1", ""], ["y", "2", "3"]]))
        self.assertEqual(t.text(), "a\tb\tc\r\nx\t1\t\r\ny\t2\t3\r\n")
        self.assertEqual(table("a\nx\n").text(), "a\nx\n")

    def test_expansion_rows_are_not_records_and_the_key_column(self):
        t = table("Name|Code\nA|a\nExpansion|\nB|b\n", "Code")
        self.assertEqual((t.records(), t.names()), ([0, 2], ["a", "b"]))


class HookTests(unittest.TestCase):
    """The generic hooks a project chains into merge_table, each fed the project's own values."""
    ren = {"skills": {"old": "New Name"}}

    def test_make_spell_moves_function_numbers_but_not_references_or_formulas(self):
        s = ids.make_spell({"skills": {"srvdofunc": {"90": "200"}, "reqskill1": {"old": "x"}}})
        self.assertEqual(s("skills", "srvdofunc", '"90"', {}), "200")
        self.assertEqual(s("skills", "srvdofunc", "91", {}), "91")
        self.assertEqual(s("skills", "reqskill1", "Old", self.ren), "New Name")  # a reference, not a number
        self.assertEqual(s("skills", "calc1", "skill('old'.blvl)*-2", self.ren), "skill('New Name'.blvl)*(0-2)")

    def test_monprop_is_a_property_table_and_fix_levels_keys_the_source_only_levels(self):
        self.assertIn("monprop", ids.PROPS)
        h = ["id", "prop1", "chance1", "par1", "min1", "max1"]  # monprop's property columns get the property fixes
        row = ["m", "Mixed-Case", "5", "old", "1", "2"]
        self.assertEqual(ids.prop_columns(h), [(1, 3)])
        ids.fix_props(h, row, self.ren, {}, {"Mixed-Case": "skill"})
        self.assertEqual(row[3], "New Name")
        self.assertEqual(ids.fix_cells({}, {"Mixed-Case": "mixed-case"})("monprop", h, ["m", "Mixed-Case", "5", "x", "1", "2"])[1],
                         "mixed-case")
        self.assertEqual(ids.entry_key("Graveyard Map (2)"), "EnteringGraveyardMap2")
        t = table("Name|LevelName|LevelEntry|LevelType\nA|Town|EnteringTown|1\nB|Grave Map||7\nC|||1\n")
        ids.fix_levels(t, 1, 3)  # A is D2R's: left alone
        self.assertEqual([r[2:] for r in t.rows], [["EnteringTown", "1"], ["EnteringGraveMap", "0"], ["", "1"]])

    def test_fix_cells(self):
        fix = ids.fix_cells({"misc": {("gfx", "toolong"): {"gfx": "tool", "missing": "x"}}},
                            words={"Mixed-Case": "mixed-case"})
        h = ["code", "gfx"]
        self.assertEqual(fix("misc", h, ["a", '"toolong"']), ["a", "tool"])
        self.assertEqual(fix("misc", h, ["Mixed-Case", "ok"]), ["Mixed-Case", "ok"])  # misc has no properties
        self.assertEqual(fix("uniqueitems", ["index", "prop1", "par1"], ["u", "Mixed-Case", "0"]), ["u", "mixed-case", "0"])
        # only property-code columns are respelled, not a name, an id, a parameter or an item code (D2R 93847 headers)
        M = "Mixed-Case"
        h = ["index", "*ID", "prop1", "par1", "min1", "max1"]
        self.assertEqual(fix("uniqueitems", h, [M] * 6), [M, M, "mixed-case", M, M, M])
        h = ["index", "code", "prop1", "par1"]  # uniqueitems' bare code is an item code
        self.assertEqual(fix("uniqueitems", h, [M] * 4), [M, M, "mixed-case", M])
        h = ["description", "op", "param", "mod 1", "mod 1 chance", "mod 1 param", "mod 1 min", "b mod 2", "b mod 2 chance",
             "b mod 2 param"]
        self.assertEqual(fix("cubemain", h, [M] * 10),
                         [M, M, M, "mixed-case", M, M, M, "mixed-case", M, M])
        h = ["index", "aprop1a", "apar1a", "amin1a", "amax1a", "aprop1b", "apar1b"]
        self.assertEqual(fix("setitems", h, [M] * 7), [M, "mixed-case", M, M, M, "mixed-case", M])
        h = ["index", "PCode2a", "PParam2a", "PMin2a", "PMax2a"]
        self.assertEqual(fix("sets", h, [M] * 5), [M, "mixed-case", M, M, M])

    def test_derive_and_finishes_in_order(self):
        d2r = table("skill|charclass|passive|rightskill|x\nA|ama|0|1|\n")
        src = table("skill|charclass|passive|x\nA|ama|1|\nB|ama|0|\n")
        seen = []
        finish = ids.finishes(ids.derive(ids.DERIVED["skills"]), None,
                              lambda h, row, s, own: seen.append((row[3], own is None)))
        merged, _ = ids.merge_table("skills", src, d2r, [("A", 0, "A"), ("B", 1, "B")], {}, finish=finish)
        self.assertEqual([r[3] for r in merged.rows], ["0", "1"])  # passive: no right-mouse slot
        self.assertEqual(seen, [("0", False), ("1", True)])

    def test_derived_rightskill_leaves_non_class_skills_alone(self):
        d2r = table("skill|charclass|passive|rightskill\nMonSkill||0|0\nD2RMon||0|0\nClassSk|ama|0|1\n")
        src = table("skill|charclass|passive\nMonSkill||\nClassSk|ama|\nNewMon||\n")
        lines = [("MonSkill", 0, "MonSkill"), ("ClassSk", 2, "ClassSk"), ("NewMon", 3, "NewMon")]
        merged, _ = ids.merge_table("skills", src, d2r, lines, {}, finish=ids.derive(ids.DERIVED["skills"]))
        # a merged monster skill keeps D2R's 0, a class skill is set, an appended non-class row stays blank
        self.assertEqual([r[3] for r in merged.rows], ["0", "0", "1", ""])
        self.assertIsNone(ids.DERIVED["skills"]["rightskill"]({"charclass": ""}))

    def test_stat_display_follows_the_string(self):
        d2r = table("Stat|descfunc|descval|descstrpos|descstrneg\nst_a|19||StrA|StrA\nst_a_time|17||StrA|StrA\n"
                    "st_b|19||StrB|StrB\nst_c|19||StrC|StrC\n")
        src = table("Stat|descfunc|descval|descstrpos|descstrneg\nst_a|1|1|StrA|StrA\nst_a_time|17|1|StrA|StrA\n"
                    "st_b|1|1|OwnStr|OwnStr\nst_c|1|1|StrA|StrA\nnew|4|1|StrA|StrA\nnew_time|17|1|StrA|StrA\n"
                    "new_own|1|1|OwnStr|\n")
        names = ["st_a", "st_a_time", "st_b", "st_c", "new", "new_time", "new_own"]
        merged, _ = ids.merge_table("itemstatcost", src, d2r, [(n, i, n) for i, n in enumerate(names)], {},
                                    finish=ids.stat_display(d2r))
        self.assertEqual([r[1:3] for r in merged.rows], [
            ["19", ""], ["17", ""],
            ["1", "1"],   # a string D2R has no row for keeps the source's display
            ["19", ""],   # moved to another D2R string: that string's display
            ["19", ""], ["17", ""],  # appended rows: the D2R row with the same descfunc, else the first
            ["1", "1"]])

    def test_stat_display_keeps_d2r_strings_a_hardcoded_function_reads(self):
        d2r = table("Stat|descfunc|descval|descstrpos|descstrneg\nsk|27||ClassSkill|ClassSkill\nel|19||El|El\n")
        src = table("Stat|descfunc|descval|descstrpos|descstrneg\nsk|27|||\nel||||\n")
        merged, _ = ids.merge_table("itemstatcost", src, d2r, [("sk", 0, "sk"), ("el", 1, "el")], {},
                                    finish=ids.stat_display(d2r))
        self.assertEqual(merged.rows, [["sk", "27", "", "ClassSkill", "ClassSkill"], ["el", "", "", "", ""]])

    def test_missile_funcs_move_the_missile_into_the_column_the_dispatcher_reads(self):
        cols = "skill|srvdofunc|srvmissile|srvmissilea"
        src = table(f"{cols}\nbolt|99||jav\nkept|99|own|jav\nother|5||jav\n")
        merged, _ = ids.merge_table("skills", src, table(f"{cols}\n"), [("bolt", 0, "bolt"), ("kept", 1, "kept"),
                                                                          ("other", 2, "other")], {},
                                    finish=ids.missile_funcs([("srvdofunc", "99", "srvmissile", "srvmissilea")]))
        self.assertEqual(merged.rows, [["bolt", "", "jav", ""], ["kept", "", "own", "jav"], ["other", "5", "", "jav"]])

    def test_missile_funcs_name_a_missing_column(self):
        src = table("skill|srvdofunc|srvmissile\nbolt|99|\n")
        with self.assertRaisesRegex(ids.IdError, "no column srvmissilea"):
            ids.merge_table("skills", src, table("skill|srvdofunc|srvmissile\n"), [("bolt", 0, "bolt")], {},
                            finish=ids.missile_funcs([("srvdofunc", "99", "srvmissile", "srvmissilea")]))

    def test_hit_params_take_the_mods_ids(self):
        cols = "Missile|pSrvHitFunc|sHitPar1|sHitPar3"
        src = table(f"{cols}\ncloud|61|236|500\nnova|5|236|500\n")
        ids_ = {"states": {"236": "282"}, "itemstatcost": {"500": "510"}}
        merged, _ = ids.merge_table("missiles", src, table(f"{cols}\n"), [("cloud", 0, "cloud"), ("nova", 1, "nova")],
                                    {}, finish=ids.hit_params({"61": {"sHitPar1": "states", "sHitPar3": "itemstatcost"}},
                                                              ids_))
        self.assertEqual(merged.rows, [["cloud", "61", "282", "510"], ["nova", "5", "236", "500"]])

    def test_property_params_and_kinds(self):
        props = ids.property_kinds(table("code|func1|stat1\noskill|11||\nhit-skill|19|\nskill-rand|12|\n"
                                         "state|1|state\nres|1|res\nadd-mon|1|my_mon_add\n"), monster_stats="my_mon_")
        self.assertEqual(props, {"oskill": "skill", "hit-skill": "skill", "skill-rand": "skillrange",
                                 "state": "state", "add-mon": "monster"})
        self.assertNotIn("add-mon", ids.property_kinds(table("code|func1|stat1\nadd-mon|1|my_mon_add\n")))
        ids_ = {"skills": {"400": "430", "401": "431"}, "monstats": {"690": "691"}}
        ren = {"skills": {"old": "New Name"}, "states": {"oldstate": "newstate"}}
        cols = "index|*ID|prop1|par1|min1|max1|prop2|par2|min2|max2"
        src = table(f"{cols}\nA|0|oskill|Old|1|1|hit-skill|400|5|3\nB|1|skill-rand|10|400|401|state|oldstate||\n"
                    "C|2|res|400|5|5|add-mon||690|690\n")
        merged, _ = ids.merge_table("uniqueitems", src, table(f"{cols}\n"), [("A", 0, "A"), ("B", 1, "B"), ("C", 2, "C")],
                                    ren, ids_, finish=ids.props_finish(ren, ids_, props))
        self.assertEqual(merged.rows, [
            ["A", "0", "oskill", "New Name", "1", "1", "hit-skill", "430", "5", "3"],
            ["B", "1", "skill-rand", "10", "430", "431", "state", "newstate", "", ""],
            ["C", "2", "res", "400", "5", "5", "add-mon", "", "691", "691"]])
        cube = ["description", "op", "param", "mod 1", "mod 1 chance", "mod 1 param"]
        row = ["r", "10", "500", "oskill", "100", "400"]
        ids.fix_props(cube, row, ren, {"itemstatcost": {"500": "510"}, **ids_}, props)
        self.assertEqual(row, ["r", "10", "510", "oskill", "100", "430"])  # cube: op stat and a chance column

    def test_num_refs_of_the_project(self):
        src = table("code|missiletype\nxyz|12\n")
        merged, _ = ids.merge_table("weapons", src, table("code|missiletype\n"), [("xyz", 0, "xyz")], {},
                                    {"missiles": {"12": "70"}}, num_refs={"weapons": {"missiletype": "missiles"}})
        self.assertEqual(merged.rows, [["xyz", "70"]])
        self.assertEqual(ids.merge_table("weapons", src, table("code|missiletype\n"), [("xyz", 0, "xyz")], {})[0].rows,
                         [["xyz", "12"]])  # not a NUM_REFS column by default

    def test_monstats_ids_and_left_out(self):
        d2r = table("Id|x\nm_a|\nExpansion|\nm_d2r|\nm_b|\n")
        src = table("Id|x\nm_a|\nExpansion|\nm_b|\nm_new1|\nm_new2|\n")
        self.assertEqual(ids.monstats_ids(src, d2r), {"0": "0", "1": "2", "2": "3", "3": "4"})
        with self.assertRaisesRegex(ids.IdError, "source monstats names used twice.*m_a"):
            ids.monstats_ids(table("Id\nm_a\nM_A\n"), d2r)
        with self.assertRaisesRegex(ids.IdError, "D2R monstats names used twice"):
            ids.monstats_ids(src, table("Id\nm_a\nm_a\n"))
        lines = {"levels": [("A", 0, "A"), ("Cut", ids.LEFT_OUT, "cut"), ("B", 2, "B")]}
        self.assertEqual(ids.left_out_of(lines, {"levels": ["A", "Cut", "B"]}), {"levels": {"1": ""}})

    def test_context_of(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {"src": {"skills": "skill\nA\nB\n", "monstats": "Id\nm1\nm2\n",
                             "properties": "code\tfunc1\tstat1\noskill\t11\t\n"},
                     "d2r": {"skills": "skill\nA\n", "monstats": "Id\nm2\n"}}
            for side, tables in files.items():
                for t, text in tables.items():
                    p = root / side / "global" / "excel" / f"{t}.txt"
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(text, "latin-1")
            lists = {"skills": [("A", 0, "A"), ("B", 1, "B_x")], "states": []}
            ctx = ids.context_of(lists, root / "src", root / "d2r")
            self.assertEqual(ctx.ids, {"skills": {"0": "0", "1": "1"}, "monstats": {"0": "1", "1": "0"}})
            self.assertEqual((ctx.ren, ctx.props), ({"skills": {"b": "B_x"}, "states": {}}, {"oskill": "skill"}))
            self.assertEqual(ids.context_of(lists, root / "src").ids, {"skills": {"0": "0", "1": "1"}})


if __name__ == "__main__":
    unittest.main()
