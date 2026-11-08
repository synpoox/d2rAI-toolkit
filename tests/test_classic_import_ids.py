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
        with self.assertRaisesRegex(ids.IdError, r"^ids-t.tsv: PD2 rows with no id \(B\): run seed$"):
            ids.check("t", [("A", 0, "A")], ["A", "B"], ["A"], source="PD2", seed_hint="run seed")


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


if __name__ == "__main__":
    unittest.main()
