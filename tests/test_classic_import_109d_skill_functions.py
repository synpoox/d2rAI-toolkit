"""Tests for shared/classic_import/data/109d-skill-functions.tsv (run: python -m unittest discover tests).

The table pairs every 1.09d skill and missile function with D2R's, one row per function:

    kind          skill or missile
    id            the record's Id in the 1.09d table (skills.txt / missiles.txt)
    name_109d     the record's name in 1.09d
    name_d2r      the same record's name in D2R
    function      srv_start, srv_use, srv_do, srv_hit, clt_start, clt_do, clt_hit ("-" = none on either build)
    addr_109d     the function's virtual address in the 1.09d DLL ("-" = none)
    d2r_column    the D2R column that names it (srvstfunc, pSrvDoFunc, ...; "-" = none)
    d2r_index     the function number in that column ("-" = none)
    rva_d2r       the D2R 93847 function's RVA ("-" = none)
    pair_verdict  same, different or unresolved: the two functions compared
    evidence      what the verdict rests on (helper overlap, calls only one build makes)
    item_verdict  the verdict for items that use the function

The data is derived (names, numbers, addresses); the tests check its shape.
"""
from __future__ import annotations

import re
import unittest
from collections import Counter
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "shared" / "classic_import" / "data" / "109d-skill-functions.tsv"
HEADER = ["kind", "id", "name_109d", "name_d2r", "function", "addr_109d", "d2r_column", "d2r_index", "rva_d2r",
          "pair_verdict", "evidence", "item_verdict"]
FUNCTIONS = {"-", "srv_start", "srv_use", "srv_do", "srv_hit", "clt_start", "clt_do", "clt_hit"}
VERDICTS = {"same", "different", "unresolved"}


class SkillFunctionTableTests(unittest.TestCase):
    def setUp(self):
        lines = PATH.read_text(encoding="utf-8").splitlines()
        self.header = lines[0].split("\t")
        self.rows = [dict(zip(self.header, l.split("\t"))) for l in lines[1:]]

    def test_header_and_row_count(self):
        self.assertEqual(self.header, HEADER)
        self.assertEqual(len(self.rows), 2088)
        self.assertTrue(all(len(r) == len(HEADER) for r in self.rows))
        self.assertEqual(Counter(r["kind"] for r in self.rows), {"skill": 655, "missile": 1433})

    def test_cells_have_the_documented_form(self):
        for r in self.rows:
            where = f"{r['kind']} {r['id']} {r['function']}"
            self.assertIn(r["function"], FUNCTIONS, where)
            self.assertRegex(r["id"], r"^\d+$", where)
            self.assertRegex(r["addr_109d"], r"^(-|0x6f[0-9a-f]{6})$", where)
            self.assertRegex(r["d2r_index"], r"^(-|\d+)$", where)
            self.assertRegex(r["rva_d2r"], r"^(-|0x[0-9a-f]+)$", where)
            self.assertIn(r["pair_verdict"], VERDICTS, where)
            self.assertIn(r["item_verdict"], VERDICTS, where)

    def test_a_d2r_function_has_both_an_index_and_an_rva(self):
        for r in self.rows:  # a column can be named with no function behind it ("code on 1.09d only")
            self.assertEqual(r["d2r_index"] == "-", r["rva_d2r"] == "-", str(r))
            if r["d2r_index"] != "-":
                self.assertNotEqual(r["d2r_column"], "-", str(r))

    def test_a_row_is_not_listed_twice(self):
        keys = [(r["kind"], r["id"], r["function"]) for r in self.rows]
        self.assertEqual(len(keys), len(set(keys)))

    def test_holds_no_path_or_mod_text(self):
        text = PATH.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"[A-Za-z]:[\\/]|Users|resurrected|deviations|orchestr", text, re.I))


if __name__ == "__main__":
    unittest.main()
