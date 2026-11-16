"""Tests for shared/classic_import's tables.json merge (run: python -m unittest discover tests). Synthetic tables, no
game data."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.classic_import import diff, tables  # noqa: E402


def table(*rows: str) -> bytes:
    return "".join("\t".join(c.strip() for c in r.split("|")) + "\r\n" for r in rows).encode("latin-1")


class TablesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, side: str, name: str, data: bytes):
        p = self.root / side / "global/excel" / f"{name}.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def merge(self, cfg: dict, id_tables: list[str] | None = None) -> dict[str, list[list[str]]]:
        rule = self.root / "tables.json"
        rule.write_text(json.dumps(cfg), "utf-8")
        tables.rule(rule, self.root / "src", self.root / "d2r", self.root / "out", id_tables)
        out = {}
        for p in (self.root / "out/global/excel").glob("*.txt"):
            out[p.stem] = [line.split("\t") for line in p.read_bytes().decode("latin-1").split("\r\n") if line]
        return out

    def test_rows_merge_by_name_keeping_d2r_only_rows_and_columns(self):
        self.write("src", "events", table("event | *desc | x", "hitbymissile | a | 1", "domeleeattack | b | 2",
                                          "dospellcast | c | 3"))
        self.write("d2r", "events", table("event | *description | x | y", "hitbymissile | A | 0 | 7",
                                          "domeleeattack | B | 0 | 8", "death | C | 9 | 9"))
        self.assertEqual(self.merge({"events": {}})["events"], [
            ["event", "*description", "x", "y"],
            ["hitbymissile", "A", "1", "7"],
            ["domeleeattack", "B", "2", "8"],
            ["death", "C", "9", "9"],  # D2R's row keeps its number
            ["dospellcast", "", "3", ""],  # the source's appends after D2R's rows
        ])

    def test_rows_pair_by_position_where_the_first_columns_differ(self):
        self.write("src", "shrines", table("Shrine Type | Code | Arg0", "None | 0 | 0", "Recharge | 1 | 5",
                                           "Booster | 2 | 9"))
        self.write("d2r", "shrines", table("Name | Code | Arg0", "None | 0 | 0", "Refilling Shrine | 1 | 4"))
        self.assertEqual(self.merge({"shrines": {"rows": "position"}})["shrines"], [
            ["Name", "Code", "Arg0"], ["None", "0", "0"], ["Refilling Shrine", "1", "5"], ["", "2", "9"]])

    def test_rows_pair_by_key_columns(self):
        self.write("src", "hireling", table("Hireling | Id | Level | Gold", "Barbarian | 30 | 3 | 1",
                                            "Barbarian | 30 | 25 | 2"))
        self.write("d2r", "hireling", table("Hireling | Id | Level | Gold", "Barbarian | 30 | 25 | 9",
                                            "Barbarian | 30 | 28 | 9"))
        self.assertEqual(self.merge({"hireling": {"rows": ["Id", "Level"], "source_only_rows": "leave out"}})["hireling"],
                         [["Hireling", "Id", "Level", "Gold"], ["Barbarian", "30", "25", "2"],
                          ["Barbarian", "30", "28", "9"]])

    def test_a_repeated_name_can_take_the_sources_whole_group_in_place(self):
        self.write("src", "monequip", table("monster | level | item1", "shadowwarrior | 20 | axe",
                                            "shadowwarrior | 0 | club", "fallen | 0 | sword"))
        self.write("d2r", "monequip", table("monster | level | item1 | x", "shadowwarrior | 0 | dagger | 1",
                                            "zombie | 0 | none | 2", "fallen | 0 | club | 3"))
        self.assertEqual(self.merge({"monequip": {"repeats": "replace group"}})["monequip"], [
            ["monster", "level", "item1", "x"], ["shadowwarrior", "20", "axe", "1"], ["shadowwarrior", "0", "club", ""],
            ["zombie", "0", "none", "2"], ["fallen", "0", "sword", "3"]])

    def test_named_columns_keep_d2rs_values(self):
        self.write("src", "objects", table("Name | Token | Parm0", "Cain Portal | tP | 5", "Trophy | qq | 1"))
        self.write("d2r", "objects", table("Name | Token | Parm0", "Cain Portal | tp | 4"))
        self.assertEqual(self.merge({"objects": {"d2r_columns": ["token"]}})["objects"], [
            ["Name", "Token", "Parm0"], ["Cain Portal", "tp", "5"], ["Trophy", "", "1"]])

    def test_moved_rows_append_with_the_sources_values_even_when_left_out(self):
        self.write("src", "hireling", table("Hireling | Id | Level | HireDesc", "Rogue | 0 | 3 | a",
                                            "Rogue | 0 | 9 | b", "Guard | 30 | 3 | c"))
        self.write("d2r", "hireling", table("Hireling | Id | Level | HireDesc", "Rogue | 0 | 3 | strhire1",
                                            "Desert | 30 | 43 | d"))
        out = self.merge({"hireling": {"rows": ["Id", "Level"], "source_only_rows": "leave out",
                                       "d2r_columns": ["HireDesc"], "move": {"Id": {"30": "39"}}}})
        self.assertEqual(out["hireling"], [
            ["Hireling", "Id", "Level", "HireDesc"], ["Rogue", "0", "3", "strhire1"],
            ["Desert", "30", "43", "d"],  # D2R's own id 30 is kept, the source's Rogue 0/9 left out
            ["Guard", "39", "3", "c"]])  # a moved row takes the source's d2r_columns too

    def test_named_cells_take_the_rules_value(self):
        self.write("src", "monstats", table("Id | NameStr | Level", "roguehire | Dummy | 5", "fallen | Fallen | 2",
                                            "act4hire | dummy | 9"))
        self.write("d2r", "monstats", table("Id | NameStr | Level", "roguehire | Rogue | 1", "fallen | Fallen1 | 1"))
        self.assertEqual(self.merge({"monstats": {"cells": {"RogueHire": {"namestr": "Rogue"},
                                                            "act4hire": {"NameStr": "Ascendant"}}}})["monstats"], [
            ["Id", "NameStr", "Level"], ["roguehire", "Rogue", "5"], ["fallen", "Fallen", "2"],
            ["act4hire", "Ascendant", "9"]])  # a source-only row too; other rows keep the source's NameStr
        with self.assertRaisesRegex(ValueError, "no row nosuch"):
            self.merge({"monstats": {"cells": {"nosuch": {"NameStr": "x"}}}})
        with self.assertRaisesRegex(ValueError, "no column NoCol"):
            self.merge({"monstats": {"cells": {"fallen": {"NoCol": "x"}}}})

    def test_source_only_rows_can_be_left_out(self):
        self.write("src", "levels", table("Name | Id", "Act 1 | 1", "Mesa | 139"))
        self.write("d2r", "levels", table("Name | Id", "Act 1 | 1"))
        self.assertEqual(self.merge({"levels": {"source_only_rows": "leave out"}})["levels"],
                         [["Name", "Id"], ["Act 1", "1"]])

    def test_only_named_rows_merge(self):
        self.write("src", "inventory", table("class | gridX", "Amazon | 10", "Transmogrify Box2 | 4", "Trophy | 10"))
        self.write("d2r", "inventory", table("class | gridX", "Amazon | 9", "Transmogrify Box2 | 3", "Warlock | 10"))
        self.assertEqual(self.merge({"inventory": {"only_rows": ["transmogrify box2"]}})["inventory"], [
            ["class", "gridX"], ["Amazon", "9"], ["Transmogrify Box2", "4"], ["Warlock", "10"]])
        with self.assertRaisesRegex(ValueError, "the source has no row nosuch"):
            self.merge({"inventory": {"only_rows": ["nosuch"]}})

    def test_references_to_id_listed_rows_take_the_mods_names(self):
        (self.root / "ids-skills.tsv").write_text("Teeth\t67\tTeeth_x\n", "utf-8")
        self.write("src", "monstats", table("Id | Skill1", "fallen | Teeth"))
        self.write("d2r", "monstats", table("Id | Skill1", "fallen | Attack"))
        self.assertEqual(self.merge({"monstats": {}}, ["skills"])["monstats"], [["Id", "Skill1"], ["fallen", "Teeth_x"]])

    def test_an_unknown_option_fails(self):
        self.write("src", "levels", table("Name | Id", "Act 1 | 1"))
        self.write("d2r", "levels", table("Name | Id", "Act 1 | 1"))
        for opts in ({"rows": "nmae"}, {"source_only_rows": "drop"}, {"colour": "red"}, {"move": ["x"]}):
            with self.subTest(opts), self.assertRaisesRegex(ValueError, "unknown option"):
                self.merge({"levels": opts})

    def test_source_only_sounds_take_d2rs_sound_of_the_same_file_or_none(self):
        """D2R's sounds table ships as it is, so a source-only sound past it would crash the client."""
        self.write("src", "sounds", table("Sound | Index | FileName", "fallen_shout | 1 | monster\\fallen\\warcry1.wav",
                                          "boss_taunt | 2 | extra\\boss\\taunt.wav"))
        self.write("d2r", "sounds", table("Sound | *Index | FileName", "fallen_warcry_1 | 1 | monster\\fallen\\warcry1.flac"))
        self.write("src", "monsounds", table("Id | Neutral | Taunt", "treasurefallen | fallen_shout | boss_taunt"))
        self.write("d2r", "monsounds", table("Id | Neutral | Taunt", "fallen | fallen_warcry_1 |"))
        self.assertEqual(self.merge({"monsounds": {}})["monsounds"], [
            ["Id", "Neutral", "Taunt"], ["fallen", "fallen_warcry_1", ""], ["treasurefallen", "fallen_warcry_1", ""]])
        self.write("src", "monsounds", table("Id | Neutral | Taunt", "boss | nosuch |"))
        with self.assertRaisesRegex(ValueError, "boss Neutral nosuch"):
            self.merge({"monsounds": {}})

    def test_moved_ids_append_with_the_source_hire_description_and_merged_monster_numbers(self):
        self.write("src", "hiredesc", table("Hireling Description | Code | *EOL", "None |  | 0", "Fire Arrow | farw | 0",
                                            "Dark Order | dkor | 0"))
        self.write("src", "monstats", table("Id | hcIdx", "kashya | 0", "Expansion | ", "tyrael2 | 1", "extrahire | 2"))
        self.write("d2r", "monstats", table("Id | *hcIdx", "kashya | 0", "Expansion | ", "tyrael2 | 1", "warlockhire | ",
                                            "Expansion | "))
        self.write("src", "hireling", table("Hireling | Id | Level | Class | Seller | HireDesc", "Rogue | 0 | 3 | 0 | 0 | farw",
                                            "Rogue | 0 | 9 | 0 | 0 | farw", "Order | 30 | 3 | 2 | 1 | dkor",
                                            "Order | 31 | 3 | 2 | 1 | farw"))
        ui = self.root / "d2r/local/lng/strings/ui.json"
        ui.parent.mkdir(parents=True)
        ui.write_text(json.dumps([{"id": 3371, "Key": "strhirespecial1", "enUS": "Fire Arrow"}]), "utf-8")
        self.write("d2r", "hireling", table("Hireling | Id | Level | Class | Seller | HireDesc", "Rogue | 0 | 3 | 0 | 0 | strhire1",
                                            "Desert | 30 | 43 | 1 | 1 | skillname99"))
        out = self.merge({"monstats": {}, "hireling": {"rows": ["Id", "Level"], "source_only_rows": "leave out",
                                                       "d2r_columns": ["HireDesc"], "move": {"Id": {"30": "39", "31": "40"}}}})
        self.assertEqual(out["hireling"], [
            ["Hireling", "Id", "Level", "Class", "Seller", "HireDesc"], ["Rogue", "0", "3", "0", "0", "strhire1"],
            ["Desert", "30", "43", "1", "1", "skillname99"],  # D2R's own id 30 is kept, the source's Rogue 0/9 left out
            ["Order", "39", "3", "3", "1", "hiredesc_dkor"],  # extrahire follows D2R's warlockhire: monster 3
            ["Order", "40", "3", "3", "1", "strhirespecial1"]])  # D2R's own string for the same text

    def test_the_gate_reads_the_source_as_the_merge_renamed_it(self):
        self.write("src", "hiredesc", table("Hireling Description | Code | *EOL", "Fire Arrow | farw | 0"))
        self.write("src", "monstats", table("Id | hcIdx", "kashya | 0", "extrahire | 2"))
        self.write("d2r", "monstats", table("Id | *hcIdx", "kashya | 0", "warlockhire | ", "x | "))
        self.write("src", "hireling", table("Hireling | Id | Level | Class | Seller | HireDesc",
                                            "Order | 31 | 3 | 1 | 1 | farw"))
        self.write("d2r", "hireling", table("Hireling | Id | Level | Class | Seller | HireDesc",
                                            "Rogue | 0 | 3 | 0 | 0 | strhire1"))
        self.write("src", "sounds", table("Sound | FileName", "own_snd | a/own.wav", "same | b.wav"))
        self.write("d2r", "sounds", table("Sound | FileName", "same | b.flac"))
        self.write("src", "monsounds", table("Id | Attack1 | Weapon1", "zombie | own_snd | same"))
        self.write("d2r", "monsounds", table("Id | Attack1 | Weapon1", "zombie | same | same"))
        cfg = {"monstats": {}, "monsounds": {}, "hireling": {"rows": ["Id", "Level"], "source_only_rows": "append"}}
        self.merge(cfg)
        dev = self.root / "deviations.md"
        dev.write_text("| Deviation | Status | Gate | Work item |\n|---|---|---|---|\n", "utf-8")

        def run(renames):
            return diff.gate(self.root / "src/global/excel", self.root / "out/global/excel",
                             self.root / "d2r/global/excel", dev, ("cut",), select=cfg.__contains__, tables_json=cfg,
                             renames=renames)

        self.assertTrue(run(None).open(), "without the merge's renames the gate sees false deviations")
        ren = tables.extra_renames(self.root / "src", self.root / "d2r", self.root / "out", True)
        self.assertEqual(run(ren).open(), [])

    def test_a_hook_runs_on_the_merged_table_before_it_is_written(self):
        self.write("src", "levels", table("Name | Id", "Act 1 | 1"))
        self.write("d2r", "levels", table("Name | Id", "Act 1 | 1"))
        rule = self.root / "tables.json"
        rule.write_text(json.dumps({"levels": {}}), "utf-8")

        def hook(merged, d2r):
            merged.rows[0][1] = "9"
            self.assertEqual(d2r.rows[0][1], "1")

        tables.rule(rule, self.root / "src", self.root / "d2r", self.root / "out", hooks={"levels": hook})
        self.assertIn(b"Act 1\t9", (self.root / "out/global/excel/levels.txt").read_bytes())

    def test_a_project_spell_spells_every_cell(self):
        self.write("src", "levels", table("Name | Id", "Act 1 | 1"))
        self.write("d2r", "levels", table("Name | Id", "Act 1 | 1"))
        rule = self.root / "tables.json"
        rule.write_text(json.dumps({"levels": {}}), "utf-8")
        tables.rule(rule, self.root / "src", self.root / "d2r", self.root / "out",
                    spell=lambda t, c, v, ren: v + "!" if c == "Id" else v)
        self.assertIn(b"Act 1	1!", (self.root / "out/global/excel/levels.txt").read_bytes())


if __name__ == "__main__":
    unittest.main()
