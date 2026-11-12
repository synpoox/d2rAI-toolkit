"""Tests for shared/classic_import/standins.py on synthetic tables (no game data)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.classic_import import standins as S  # noqa: E402
from shared.classic_import.ids import Table  # noqa: E402

ONLY = {
    "skills": {"srvdofunc": S.nums(153, range(155, 157), 167), "cltdofunc": S.nums(97, range(100, 104))},
    "missiles": {"pSrvDoFunc": S.nums(38, 40)},
    "misc": {"pSpell": S.nums(13)},
}


def table(text: str) -> Table:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "t.txt"
        p.write_bytes(text.replace("|", "\t").encode("latin-1"))
        return Table(p)


D2R = "skill|srvdofunc|cltdofunc\r\nAttack|1|1\r\nLeap|77|43\r\nTeleport|27|\r\n"
# the merged table: Leap took the source's 153/97, two source rows were appended
MOD = "skill|srvdofunc|cltdofunc\r\nAttack|1|1\r\nLeap|153|97\r\nTeleport|27|\r\nBlink|155|\r\nForce Move|167|103\r\n"


class NumsTests(unittest.TestCase):
    def test_nums(self):
        self.assertEqual(S.nums(3, range(5, 8)), {"3", "5", "6", "7"})


class ApplyLinesTests(unittest.TestCase):
    def test_from_own_row_named_row_or_blank(self):
        mod = table(MOD)
        S.apply_lines("skills", mod, table(D2R), [
            ("Leap", "=", ["srvdofunc", "cltdofunc"], "Leap"),
            ("Blink", "Teleport", ["srvdofunc"], "Teleport"),
            ("Force Move", "-", ["srvdofunc", "cltdofunc"], "Force Move")])
        self.assertEqual([r[1:] for r in mod.rows], [["1", "1"], ["77", "43"], ["27", ""], ["27", ""], ["", ""]])

    def test_refusals(self):
        cases = [
            (("Nope", "-", ["srvdofunc"], "r"), "no row 'Nope'"),
            (("Blink", "=", ["srvdofunc"], "r"), "'Blink' is not a D2R row"),
            (("Blink", "Nope", ["srvdofunc"], "r"), "no D2R row 'Nope'"),
            (("Blink", "-", ["srvdofnc"], "r"), "no column 'srvdofnc'"),
            (("Twice", "-", ["srvdofunc"], "r"), "'Twice' names 2 rows"),
        ]
        for line, msg in cases:
            with self.subTest(msg), self.assertRaisesRegex(S.StandinError, msg):
                S.apply_lines("skills", table(MOD + "Twice|1|\r\nTwice|2|\r\n"), table(D2R), [line])


class CheckTests(unittest.TestCase):
    def test_a_listed_number_left_fails_d2r_own_rows_pass(self):
        d2r = table(D2R + "Death Mark|155|\r\n")
        mod = table(MOD.replace("Blink", "Death Mark|155|\r\nBlink"))
        with self.assertRaisesRegex(S.StandinError, r"Leap srvdofunc 153.*Blink srvdofunc 155.*no stand-in"):
            S.check("skills", mod, d2r, ONLY)
        S.apply_lines("skills", mod, d2r, [("Leap", "=", ["srvdofunc", "cltdofunc"], "r"),
                                         ("Blink", "Teleport", ["srvdofunc"], "r"),
                                         ("Force Move", "-", ["srvdofunc", "cltdofunc"], "r")])
        S.check("skills", mod, d2r, ONLY)  # Death Mark keeps D2R's own 155

    def test_a_table_not_in_only_is_not_checked(self):
        S.check("skills", table(MOD), table(D2R), {})


class RuleTests(unittest.TestCase):
    def test_rule_file_edits_the_generated_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for root, skills in [("d2r", D2R), ("out", MOD)]:
                (tmp / root / "global" / "excel").mkdir(parents=True)
                (tmp / root / "global" / "excel" / "skills.txt").write_bytes(skills.replace("|", "\t").encode())
                (tmp / root / "global" / "excel" / "missiles.txt").write_bytes(b"Missile\tpSrvDoFunc\r\nx\t1\r\n")
            rule = tmp / "standins.tsv"
            rule.write_text("# table\trow\tfrom\tcolumns\trule\n"
                            "skills\tLeap\t=\tsrvdofunc,cltdofunc\tLeap\n"
                            "skills\tBlink\tTeleport\tsrvdofunc\tTeleport\n"
                            "skills\tForce Move\t-\tsrvdofunc, cltdofunc\tForce Move\n", "utf-8")
            run = partial(S.apply, only=ONLY)
            run(rule, tmp / "src", tmp / "d2r", tmp / "out")
            self.assertEqual((tmp / "out" / "global" / "excel" / "skills.txt").read_bytes(),
                             b"skill\tsrvdofunc\tcltdofunc\r\nAttack\t1\t1\r\nLeap\t77\t43\r\nTeleport\t27\t\r\n"
                             b"Blink\t27\t\r\nForce Move\t\t\r\n")
            # a table no rule merges yet (misc): its lines wait, D2R's own table is built
            rule.write_text("misc\tBook\tTome\tpSpell\tUnlimited books\n", "utf-8")
            run(rule, tmp / "src", tmp / "d2r", tmp / "out")
            self.assertFalse((tmp / "out" / "global" / "excel" / "misc.txt").exists())
            rule.write_text("skills\tLeap\t=\n", "utf-8")
            with self.assertRaisesRegex(S.StandinError, "line 1: want"):
                run(rule, tmp / "src", tmp / "d2r", tmp / "out")
            rule.write_text("skils\tLeap\t=\tsrvdofunc\tLeap\n", "utf-8")
            with self.assertRaisesRegex(S.StandinError, "no stand-ins for table skils"):
                run(rule, tmp / "src", tmp / "d2r", tmp / "out")


if __name__ == "__main__":
    unittest.main()
