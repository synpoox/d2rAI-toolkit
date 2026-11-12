"""Tests for shared/classic_import/skilldesc.py on synthetic skilldesc tables (no game data)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.classic_import import skilldesc as S  # noqa: E402
from shared.classic_import.ids import Table  # noqa: E402

COLS = [f"{p}{s}{n}" for p, n in [("desc", n) for n in range(1, 6)] + [("dsc3", 1)]
        for s in ("line", "texta", "textb", "calca", "calcb")]
FMT = {"StrSkill18", "StrSkill20", "StrSkill4", "StrSkillDamagePercent", "Damplev"}  # D2R keys with a format code

# a small mapping of the test's own: the project decides these, the toolkit only applies them
MAPPING = S.Mapping(
    lines={
        "51": ("74", "d2r", lambda a, b: (a, "")),
        "2": ("74", "d2r", lambda a, b: (a, "")),
        "63": ("76", "swap", lambda a, b: (a, "")),
        "12": ("36", "d2r", lambda a, b: (a, "25")),
        "19": ("36", "d2r", lambda a, b: (f"({a})*2", "3")),
    },
    fixed={("1", ""): ("36", "StrSkill3", "", "usmc", "256"),
           ("49", "ItemStats1o"): ("75", "StrSkillSmiteDamage", "", "pnma", "pxma")},
    keys={"2": {"StrSkill4": "StrSkillDamagePercent"}},
    builtins={"10": {"fire": "StrSkill5", "mag": "StrSkill39"}, "14": {"": "StrSkill8"}},
    below={"14": "StrSkillPoisonLengthSingular"},
)


def table(*rows: tuple[str, list[list[str]]]) -> Table:
    """skilldesc with each row's lines in order (5 desc lines, then dsc3 line 1); [] is an empty line."""
    text = "\t".join(["skilldesc", *COLS]) + "\n"
    for name, ls in rows:
        text += "\t".join([name, *(c for line in ls for c in (line or [""] * 5))]) + "\n"
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "skilldesc.txt"
        p.write_bytes(text.encode("latin-1"))
        return Table(p)


D2R = table(("grim ward", [["36", "StrSkillRadiusSingular", "StrSkill18", "ln12*2", "3"],
                           ["36", "StrSkillDurationSingular", "StrSkill20", "clc1", "25"],
                           ["74", "StrSkillDamagePercent", "", "ln56", ""], [], [], []]),
            ("bash", [["75", "StrSkill4", "", "edmn", "edmx"], [], [], [], [], ["76", "Damplev", "skillname139", "par8", ""]]))


class SkilldescTests(unittest.TestCase):
    def test_source_lines_move_onto_d2r_functions(self):
        merged = table(("grim ward", [["1", "", "", "", ""], ["19", "StrSkill18", "", "ln12", ""],
                                      ["12", "StrSkill20", "", "ln34", ""], ["2", "StrSkill4", "StrSkill23", "ln56", ""],
                                      ["6", "StrAttackRating", "", "toht", ""], []]),
                       ("bash", [[], [], [], [], [], ["63", "skillname139", "Damplev", "par8", ""]]))
        self.assertEqual(len(S.clashes(merged, D2R, FMT)), 5)  # all but Attack Rating, which D2R prints fine
        S.rewrite(merged, D2R, FMT, MAPPING)
        self.assertEqual(S.clashes(merged, D2R, FMT), [])
        self.assertEqual(merged.rows[0][1:26], ["36", "StrSkill3", "", "usmc", "256",
                                                "36", "StrSkillRadiusSingular", "StrSkill18", "(ln12)*2", "3",
                                                "36", "StrSkillDurationSingular", "StrSkill20", "ln34", "25",
                                                "74", "StrSkillDamagePercent", "", "ln56", "",
                                                "6", "StrAttackRating", "", "toht", ""])
        self.assertEqual(merged.rows[1][26:], ["76", "Damplev", "skillname139", "par8", ""])

    def test_a_skill_kept_off_the_tree_leaves_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "skilldesc.txt"
            p.write_bytes(b"skilldesc\tSkillPage\tSkillRow\tSkillColumn\nBlade Dance\t3\t0\t0\ntiger strike\t3\t1\t2\n"
                          b"asatemp2\t0\t0\t0\n")
            t = Table(p)
        S.hide_off_tree(t)
        self.assertEqual([r[1:] for r in t.rows], [["0", "0", "0"], ["3", "1", "2"], ["0", "0", "0"]])

    def test_builtin_damage_takes_d2rs_line(self):
        d2r = table(("holy bolt", [["75", "StrSkill39", "", "enma", "exma"], [], [], [], [], []]),
                    ("fire bolt", [["75", "StrSkill5", "", "enma", "exma"], [], [], [], [], []]))
        merged = table(("holy bolt", [["10", "", "", "", ""], [], [], [], [], []]),
                       ("new bolt", [["10", "", "", "", ""], [], [], [], [], []]))
        self.assertEqual(len(S.clashes(merged, d2r, FMT)), 2)
        S.rewrite(merged, d2r, FMT, MAPPING, {"holy bolt": "fire", "new bolt": "fire"})  # D2R's own line beats EType
        self.assertEqual([r[1:6] for r in merged.rows], [["75", "StrSkill39", "", "enma", "exma"],
                                                         ["75", "StrSkill5", "", "enma", "exma"]])

    def test_poison_damage_gets_d2rs_length_line_below_it(self):
        d2r = table(("poison nova", [["36", "StrSkillPoisonLengthSingular", "StrSkill63", "edln", "25"],
                                     ["75", "StrSkill8", "", "enms", "exms"], [], [], [], []]))
        merged = table(("poison nova", [["1", "", "", "", ""], ["14", "", "", "", ""], ["12", "StrSkill20", "", "ln34", ""],
                                        [], [], []]))
        S.rewrite(merged, d2r, FMT | {"StrSkillPoisonLengthSingular", "StrSkill8"}, MAPPING)
        self.assertEqual(merged.rows[0][6:21], ["36", "StrSkillPoisonLengthSingular", "StrSkill63", "edln", "25",
                                                 "75", "StrSkill8", "", "enms", "exms",
                                                 "12", "StrSkill20", "", "ln34", ""])  # moved up a slot

    def test_a_line_with_no_d2r_layout_fails(self):
        merged = table(("new skill", [["47", "StrSkill20", "", "a", "b"], [], [], [], [], []]))  # no mapping for 47
        with self.assertRaisesRegex(ValueError, "new skill descline1 47 StrSkill20"):
            S.rewrite(merged, D2R, FMT, MAPPING)

    def test_an_empty_mapping_places_nothing(self):
        merged = table(("grim ward", [["19", "StrSkill18", "", "ln12", ""], [], [], [], [], []]))
        with self.assertRaisesRegex(ValueError, "grim ward descline1 19"):
            S.rewrite(merged, D2R, FMT, S.Mapping())

    def test_format_codes_d2r_never_uses_in_skilldesc(self):
        # a source function 51 formats "+%d Percent ..."; D2R's classic 51 prints it raw. ItemStats1o is D2R's, unused here
        d2r = table(("holy shield", [["75", "StrSkillSmiteDamage", "", "pnma", "pxma"], [], [], [], [], []]),
                    ("x", [["74", "StrSkillDamagePercent", "", "a", ""], [], [], [], [], []]))
        merged = table(("jav mastery", [["51", "deadlystrikemastery", "", "edmn", ""], [], [], [], [], []]),
                       ("holy shield", [["49", "ItemStats1o", "", "", ""], ["7", "StrWeaponDmg", "", "75", ""],
                                        [], [], [], []]))
        strings = {"deadlystrikemastery": "+%d Percent Critical Strike Multiplier",
                   "ItemStats1o": "Smite Damage: %d to %d",
                   "StrWeaponDmg": "% Weapon Damage"}  # a literal % under a classic function prints fine
        self.assertEqual(len(S.clashes(merged, d2r, FMT, strings)), 2)
        S.rewrite(merged, d2r, FMT, MAPPING, strings=strings)
        self.assertEqual(S.clashes(merged, d2r, FMT, strings), [])
        self.assertEqual([r[1:11] for r in merged.rows],
                         [["74", "deadlystrikemastery", "", "edmn", "", *[""] * 5],
                          ["75", "StrSkillSmiteDamage", "", "pnma", "pxma", "7", "StrWeaponDmg", "", "75", ""]])


    def test_a_copy_rule_with_no_d2r_line_fails_naming_the_line(self):
        merged = table(("only mine", [["19", "OnlyMine", "", "ln12", ""], [], [], [], [], []]))
        mapping = S.Mapping(lines={"19": (None, "copy", None)})
        with self.assertRaisesRegex(ValueError, "only mine descline1 19 OnlyMine"):
            S.rewrite(merged, D2R, FMT, mapping, strings={"OnlyMine": "%d things"})

    def test_a_below_label_d2r_never_prints_fails_naming_the_label(self):
        merged = table(("poison nova", [["14", "", "", "", ""], [], [], [], [], []]))
        mapping = S.Mapping(builtins={"14": {"": "StrSkill8"}}, below={"14": "NoSuchLabel"})
        with self.assertRaisesRegex(ValueError, "poison nova descline1: no D2R line with NoSuchLabel"):
            S.rewrite(merged, D2R, FMT, mapping)

    def test_a_fixed_line_with_no_calc_b_keeps_the_classic_calc_b(self):
        merged = table(("x", [["49", "ItemStats1o", "", "ca", "cb"], [], [], [], [], []]))
        mapping = S.Mapping(fixed={("49", "ItemStats1o"): ("75", "StrSkillSmiteDamage", "", None, None)})
        S.rewrite(merged, D2R, FMT, mapping, strings={"ItemStats1o": "+%d"})
        self.assertEqual(merged.rows[0][1:6], ["75", "StrSkillSmiteDamage", "", "ca", "cb"])

    def test_hide_off_tree_needs_the_skill_columns(self):
        with self.assertRaisesRegex(ValueError, "SkillPage"):
            S.hide_off_tree(D2R)  # the synthetic table has no SkillPage column


class StringsTests(unittest.TestCase):
    def test_texts_and_formatted_read_the_string_files(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            d2r, out = Path(tmp) / "d2r", Path(tmp) / "out"
            for root, rows in ((d2r, [{"Key": "A", "enUS": "Duration: %d seconds"}, {"Key": "B", "enUS": "Plain"}]),
                               (out, [{"Key": "B", "enUS": "Changed"}])):
                (root / "local" / "lng" / "strings").mkdir(parents=True)
                (root / "local" / "lng" / "strings" / "skills.json").write_text(json.dumps(rows), "utf-8")
            self.assertEqual(S.texts(d2r, out), {"A": "Duration: %d seconds", "B": "Changed"})
            self.assertEqual(S.formatted(d2r), {"A"})


if __name__ == "__main__":
    unittest.main()
