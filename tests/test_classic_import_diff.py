"""Tests for shared/classic_import's table-diff gate (run: python -m unittest discover tests). Synthetic tables, no game
data."""
from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.classic_import import diff, ids  # noqa: E402


def table(*rows: str) -> bytes:
    return "".join("\t".join(c.strip() for c in r.split("|")) + "\r\n" for r in rows).encode("latin-1")


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "d2r/global/excel").mkdir(parents=True)
        self.deviations("")

    def tearDown(self):
        self.tmp.cleanup()

    def excel(self, side: str) -> Path:
        return self.root / side / "global/excel"

    def write(self, side: str, name: str, data: bytes):
        p = self.excel(side) / f"{name}.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def deviations(self, rows: str):
        (self.root / "deviations.md").write_text(
            "# Deviation list\n\n| Deviation | Status | Gate | Work item |\n|---|---|---|---|\n" + rows, "utf-8")

    def gate(self, statuses=("not yet", "approximated", "cut"), **kw):
        return diff.gate(self.excel("src"), self.excel("mod"), self.excel("d2r"), self.root / "deviations.md", statuses,
                         **kw)

    def test_a_missing_d2r_folder_is_an_error_not_unshipped_tables(self):
        with self.assertRaisesRegex(diff.GateError, "no D2R tables"):
            diff.gate(self.excel("src"), self.excel("mod"), self.root / "nowhere", self.root / "deviations.md", ("cut",))

    def test_no_source_tables_is_an_error_not_a_pass(self):
        with self.assertRaisesRegex(diff.GateError, r"no classic tables under .*src.*: extract first"):
            self.gate(source="classic", extract_hint="extract first")

    def test_a_merged_table_equal_to_the_source_passes(self):
        self.write("src", "lvlmaze", table("Name | Id | MonLvl", "Rogue Encampment | 1 | 1"))
        self.write("mod", "lvlmaze", table("Name | Id | MonLvl", "Rogue Encampment | 1 | 1"))
        report = self.gate()
        self.assertTrue(report.ok)
        self.assertEqual(report.open(), [])

    def test_a_changed_cell_is_open_until_the_deviation_list_names_it(self):
        self.write("src", "lvlmaze", table("Name | MonLvl", "Rogue Encampment | 1", "Blood Moor | 2"))
        self.write("mod", "lvlmaze", table("Name | MonLvl", "Rogue Encampment | 1", "Blood Moor | 5"))
        self.assertEqual(self.gate().open(), [("lvlmaze.Blood Moor.MonLvl", "2", "5")])
        self.deviations("| Blood Moor is harder | approximated | `lvlmaze.blood moor.monlvl` | P4 |\n")
        report = self.gate()
        self.assertTrue(report.ok)
        self.assertEqual(report.results[0].covered, 1)

    def test_the_report_counts_deviation_entries_by_the_projects_statuses(self):
        self.write("src", "lvlmaze", table("Name | MonLvl", "Blood Moor | 2"))
        self.write("mod", "lvlmaze", table("Name | MonLvl", "Blood Moor | 5"))
        self.deviations("| Blood Moor is harder | approximated | `lvlmaze.*.monlvl` | P4 |\n"
                        "| Maps | not yet | | P3 |\n| Ladder | not yet | | P6 |\n")
        text = diff.report(self.gate(), "P4")
        self.assertIn("1 table cells on the deviation list", text)
        self.assertIn("Deviation list: 2 not yet, 1 approximated, 0 cut entries", text)
        self.deviations("| Shared stash | kept | `lvlmaze.*.monlvl` | v0.1 |\n")
        text = diff.report(self.gate(statuses=("kept", "cut")), "v0.1")
        self.assertIn("Deviation list: 1 kept, 0 cut entries", text)

    def test_the_report_names_its_commit_and_marks_uncommitted_changes(self):
        git = ["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@example.com",
               "-c", "commit.gpgsign=false"]
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
        subprocess.run([*git, "init", "-q"], check=True, env=env)
        subprocess.run([*git, "add", "deviations.md"], check=True, env=env)
        subprocess.run([*git, "commit", "-qm", "x"], check=True, env=env)
        head = subprocess.run([*git, "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              env=env).stdout.strip()
        self.assertEqual(diff.commit_of(self.root), head)
        self.write("src", "lvlmaze", table("Name | MonLvl", "Blood Moor | 2"))
        self.assertEqual(diff.commit_of(self.root), f"{head}, uncommitted changes")
        text = diff.report(self.gate(), "P4", diff.commit_of(self.root), source="1.09d")
        self.assertTrue(text.startswith(f"Table-diff gate on {head}, uncommitted changes, scope P4: FAIL, 1 open"), text)
        self.assertIn("| Open deviation | 1.09d | Mod |", text)
        self.assertIn("| `lvlmaze.*.*` |  |  |", text)  # no mod or D2R table: the whole table is open

    def test_missing_rows_and_columns_are_deviations_but_d2r_only_rows_are_not(self):
        self.write("src", "lvlmaze", table("Name | *comment | MonLvl | Beta | eol", "Rogue Encampment | x | 1 | 0 | 0",
                                           "Expansion | | | | 0", "Abaddon | | 60 | 1 | 0", "Expansion | | | | 0"))
        self.write("mod", "lvlmaze", table("Name | MonLvl | LevelGroup", "Rogue Encampment | 1 | 3",
                                           "Expansion | | ", "Warlock Keep | 50 | 1", "Expansion | 0 |"))
        self.assertEqual(self.gate().open(), [("lvlmaze.*.Beta", "", ""), ("lvlmaze.Abaddon.*", "", "")])

    def test_an_unmerged_table_is_compared_with_d2rs_and_an_unshipped_one_is_a_deviation(self):
        self.write("src", "monstats", table("Id | Level", "fallen | 2"))
        self.write("d2r", "monstats", table("Id | Level", "fallen | 1"))
        self.write("src", "arena", table("Suicide | PlayerKill", "-10 | 100"))
        report = self.gate()
        self.assertEqual(report.open(), [("arena.*.*", "", ""), ("monstats.fallen.Level", "2", "1")])
        self.assertEqual([r.source for r in report.results], ["none", "D2R"])

    def test_rows_renamed_by_the_id_lists_and_their_rewritten_references_match(self):
        lists = {"skills": [("Teeth", 67, "Teeth_x")]}
        self.write("src", "missiles", table("Missile | Skill | SrvCalc1 | Range",
                                            'teeth | Teeth | skill(\'Teeth\'.blvl)*-2 | "5"'))
        self.write("mod", "missiles", table("Missile | Skill | SrvCalc1 | Range",
                                            "teeth | Teeth_x | skill('Teeth_x'.blvl)*(0-2) | 5"))
        self.write("src", "skills", table("skill | Id | srvmissile", "Teeth | 67 | teeth"))
        self.write("mod", "skills", table("skill | *Id | srvmissile", "Teeth_x | 400 | teeth"))
        self.assertEqual(self.gate(lists=lists).open(), [])
        self.write("mod", "missiles", table("Missile | Skill | SrvCalc1 | Range",
                                            "teeth | Teeth | skill('Teeth_x'.blvl)*(0-2) | 5"))
        self.assertEqual(self.gate(lists=lists).open(), [("missiles.teeth.Skill", "Teeth", "Teeth")])

    def test_tables_merged_by_position_compare_by_position_and_spell_references(self):
        self.write("src", "shrines", table("Shrine Type | Code", "None | 0", "Recharge | 1"))
        self.write("mod", "shrines", table("Name | Code", "None | 0", "Refilling Shrine | 2"))
        self.write("src", "monstats", table("Id | Skill1", "fallen | Teeth"))
        self.write("mod", "monstats", table("Id | Skill1", "fallen | Teeth_x"))
        self.assertEqual(self.gate(lists={"skills": [("Teeth", 67, "Teeth_x")]},
                                   tables_json={"shrines": {"rows": "position"}, "monstats": {}}).open(),
                         [("shrines.*.Shrine Type", "", ""), ("shrines.1.Code", "1", "2")])

    def test_with_no_id_lists_cells_are_still_spelled_as_the_merge_spells_them(self):
        # review of #20: an empty rename map skipped spell, so a fixed formula read as a deviation
        self.write("src", "skills", table("skill | calc1", 'Bash | -"min(a,b)"'))
        self.write("mod", "skills", table("skill | calc1", "Bash | 0-min(a,b)"))
        self.assertEqual(self.gate().open(), [])
        self.assertEqual(self.gate(lists={}).open(), [])
        src = ids.Table.of(["skill", "calc1"], [["Bash", '-"min(a,b)"']])
        mod = ids.Table.of(["skill", "calc1"], [["Bash", "0-min(a,b)"]])
        self.assertEqual(diff.compare("skills", src, mod, {}).open, [])
        self.assertEqual(diff.compare("skills", src, mod).open, [])
        custom = diff.compare("skills", ids.Table.of(["skill", "x"], [["Bash", "1"]]),
                              ids.Table.of(["skill", "x"], [["Bash", "<1>"]]), {}, spell=lambda t, c, v, r: f"<{v}>")
        self.assertEqual(custom.open, [])  # a project's spell runs with no lists too

    def test_a_project_can_name_its_own_reference_columns(self):
        src = ids.Table.of(["code", "missiletype"], [["axe", "fire"]])
        mod = ids.Table.of(["code", "missiletype"], [["axe", "7"]])
        refs = {"weapons": {"missiletype": "missiles"}}
        self.assertEqual(diff.compare("weapons", src, mod, {}).open, [("weapons.axe.missiletype", "fire", "7")])
        self.assertEqual(diff.compare("weapons", src, mod, {}, id_map={"missiles": {"fire": "7"}}, num_refs=refs).open, [])

    def test_a_renamed_column_d2r_split_in_several_is_compared_in_each(self):
        self.write("src", "hireling", table("Hireling | Resist", "Rogue | 5"))
        self.write("mod", "hireling", table("Hireling | ResistFire | ResistCold", "Rogue | 5 | 7"))
        self.assertEqual(self.gate().open(), [("hireling.Rogue.Resist", "5", "7")])

    def test_select_picks_the_tables(self):
        for t in ("skills", "armor", "lvlmaze"):
            self.write("src", t, table("Name | x", "a | 1"))
        self.assertEqual([r.table for r in self.gate(select=lambda t: t != "armor").results], ["lvlmaze", "skills"])

    def test_a_whole_table_row_must_go_once_the_table_is_merged(self):
        self.deviations("| Not merged yet | not yet | `lvlmaze.*` | P4 |\n")
        self.write("src", "lvlmaze", table("Name | MonLvl", "Blood Moor | 2"))
        self.write("d2r", "lvlmaze", table("Name | MonLvl", "Blood Moor | 1"))
        self.assertEqual(self.gate().results[0].covered, 1)
        self.write("mod", "lvlmaze", table("Name | MonLvl", "Blood Moor | 1"))
        with self.assertRaisesRegex(diff.GateError, "lvlmaze.*merged"):
            self.gate()

    def test_a_whole_table_pattern_with_any_wildcard_segments_is_refused_for_a_merged_table(self):
        self.write("src", "lvlmaze", table("Name | MonLvl", "Blood Moor | 2"))
        self.write("d2r", "lvlmaze", table("Name | MonLvl", "Blood Moor | 1"))
        self.write("mod", "lvlmaze", table("Name | MonLvl", "Blood Moor | 1"))
        for pat in ("lvlmaze.*", "lvlmaze.*.*", "lvlmaze.**.*", "lvlmaze.?*", "lvlmaze.*?", "lvlm*", "lvlmaz[e].*", "*.*.*"):
            self.deviations(f"| Whole table | not yet | `{pat}` | P4 |\n")
            with self.assertRaisesRegex(diff.GateError, "merged now", msg=pat):
                self.gate()
        self.deviations("| Narrow | not yet | `lvlmaze.*.monlvl` `lvlmaze.blood moor.*` | P4 |\n"
                        "| Unnamed | not yet | `lvlmaze.*.` | P4 |\n")
        self.gate()

    def test_a_table_the_project_does_not_own_is_d2rs_and_an_edit_to_it_is_open(self):
        self.write("src", "automap", table("Name | Cel1", "1 Town | 0"))
        self.write("d2r", "automap", table("Name | Cel1", "1 Town | 0"))
        self.write("mod", "automap", table("Name | Cel1", "1 Town | 99"))
        res = self.gate(own=lambda name: False, own_label="committed").results[0]
        self.assertEqual((res.source, res.open), ("D2R", [("automap.1 Town.Cel1", "0", "99")]))
        res = self.gate(own=lambda name: name == "automap.txt", own_label="committed").results[0]
        self.assertEqual(res.source, "committed", "an owned table is labelled")
        self.deviations("| Own | approximated | `automap.*` | P4 |\n")
        with self.assertRaisesRegex(diff.GateError, "merged now"):
            self.gate(own=lambda name: False)
        self.deviations("| Own | approximated | `automap.1 town.cel1` | P4 |\n")
        self.assertEqual(self.gate(own=lambda name: False).open(), [])

    def test_excels_quote_marks_are_not_data(self):
        self.write("src", "lvlmaze", table("Name | MonLvl", 'Blood Moor | "2"'))
        self.write("mod", "lvlmaze", table("Name | MonLvl", "Blood Moor | 2"))
        self.assertEqual(self.gate().open(), [])

    def test_item_tables_are_read_as_the_merge_writes_them(self):
        # repeated affix names: matched by the id list, not by name (D2R's own Virulent sits at 0)
        lists = {"magicprefix": [("Virulent", 1, "Virulent"), ("Virulent#2", 2, "Virulent")]}
        self.write("src", "magicprefix", table("Name | level", "Virulent | 5", "Virulent | 9"))
        self.write("mod", "magicprefix", table("Name | level", "Virulent | 92", "Virulent | 5", "Virulent | 9"))
        # renamed columns (ids.RENAME_MAP), and a repeated column whose first holds the values
        self.write("src", "armor", table("name | code | DrehyaMax | mindam | mindam", "Buckler | buc | 3 | 1 | 0"))
        self.write("mod", "armor", table("name | code | AnyaMax | mindam", "Buckler | buc | 3 | 1"))
        # a table merged row by row keeps D2R's names; Excel's quote marks are not part of a cube recipe's name
        self.write("src", "gems", table("name | code", "Saphire | gsb"))
        self.write("mod", "gems", table("name | code", "Sapphire | gsb"))
        self.write("src", "cubemain", table("description | output", '"rings, three" | amu'))
        self.write("mod", "cubemain", table("description | output", "rings, three | amu"))
        args = {"by_row": ("gems",), "list_paired": ("magicprefix",)}
        self.assertEqual(self.gate(lists=lists, compare_args=lambda t: args).open(), [])

    def test_a_projects_fixes_and_level_ids_are_applied_before_comparing(self):
        # the project's fix_row and fix (a function number it moves), and NUM_REFS in the mod's ids
        self.write("src", "skills", table("skill | srvdofunc", "Bolt | 188"))
        self.write("mod", "skills", table("skill | srvdofunc", "Bolt | 16"))
        self.write("src", "lvlprest", table("Name | LevelId", "Den | 3"))
        self.write("mod", "lvlprest", table("Name | LevelId", "Den | 4"))

        def fix(name, header, want, src_header, src_row):
            if name == "skills":
                want[header.index("srvdofunc")] = "16" if src_row[1] == "188!" else want[1]

        args = {"fix_row": lambda t, h, r: [*r[:1], *(v + "!" for v in r[1:])] if t == "skills" else r, "fix": fix,
                "id_map": {"levels": {"3": "4"}}}
        self.assertEqual(self.gate(compare_args=lambda t: args).open(), [])
        self.assertEqual(self.gate().open(), [("lvlprest.Den.LevelId", "3", "4"), ("skills.Bolt.srvdofunc", "188", "16")])

    def test_every_deviation_row_has_a_known_status(self):
        self.deviations("| Something | maybe | `lvlmaze.*.*` | P4 |\n")
        with self.assertRaisesRegex(diff.GateError, "maybe"):
            self.gate()

    def test_a_separate_gate_table_covers_its_rows_and_must_name_a_listed_row(self):
        self.write("src", "lvlmaze", table("Name | MonLvl", "Blood Moor | 2"))
        self.write("mod", "lvlmaze", table("Name | MonLvl", "Blood Moor | 5"))
        status = "# Deviation list\n\n| Deviation | Status | Why | Work item |\n|---|---|---|---|\n" \
                 "| Blood Moor is harder | approximated | why | P4 |\n\n| Deviation | Gate |\n|---|---|\n"
        (self.root / "deviations.md").write_text(status + "| Blood Moor is harder | `lvlmaze.*.monlvl` |\n", "utf-8")
        report = self.gate()
        self.assertTrue(report.ok)
        self.assertIn("1 approximated", diff.report(report, "P4"))
        (self.root / "deviations.md").write_text(status + "| Blood Moor is easier | `lvlmaze.*.monlvl` |\n", "utf-8")
        with self.assertRaisesRegex(diff.GateError, "Blood Moor is easier"):
            self.gate()

    def test_the_report_lists_at_most_shown_deviations(self):
        rows = [f"r{i} | 1" for i in range(diff.SHOWN + 3)]
        self.write("src", "lvlmaze", table("Name | MonLvl", *rows))
        self.write("mod", "lvlmaze", table("Name | MonLvl", *(r.replace("| 1", "| 2") for r in rows)))
        text = diff.report(self.gate(), "all")
        self.assertIn("3 more not shown.", text)
        self.assertEqual(text.count("| `lvlmaze.r"), diff.SHOWN)


class CliTests(unittest.TestCase):
    def run_cli(self, rep_or_exc, argv=("--scope", "a")):
        def run_gate(select):
            if isinstance(rep_or_exc, Exception):
                raise rep_or_exc
            return rep_or_exc
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return diff.cli("gate", {"a": lambda t: True, "b": lambda t: t == "x"}, run_gate, list(argv))

    def test_exit_codes_are_0_clean_1_open_2_broken(self):
        clean = diff.Report([diff.Result("t")], {"cut": 0})
        opened = diff.Report([diff.Result("t", [("t.r.c", "1", "2")])], {"cut": 0})
        self.assertEqual(self.run_cli(clean), 0)
        self.assertEqual(self.run_cli(opened), 1)
        self.assertEqual(self.run_cli(diff.GateError("bad list")), 2)
        self.assertEqual(self.run_cli(ids.IdError("bad id list")), 2)

    def test_an_unknown_scope_is_refused(self):
        with self.assertRaisesRegex(diff.GateError, "scope 'zz' is not one of a, b"):
            diff.scope_of({"a": lambda t: True, "b": lambda t: True}, "zz")

    def test_a_merge_finish_is_applied_as_a_fix(self):
        def finish(header, row, src, own):
            row[header.index("rightskill")] = "0" if src.get("passive") == "1" else "1"
        want = ["Bolt", "9"]
        diff.fix_of(finish)("skills", ["skill", "rightskill"], want, ["skill", "passive"], ["Bolt", "1"])
        self.assertEqual(want, ["Bolt", "0"])
        self.assertIsNone(diff.fix_of(None))


class PairsTests(unittest.TestCase):
    def test_a_left_out_row_has_no_mod_row(self):
        src = ids.Table.of(["Name", "x"], [["A", "1"], ["B", "2"]])
        mod = ids.Table.of(["Name", "x"], [["A", "1"]])
        self.assertEqual(diff.pairs("levels", src, mod, None, {"levels": [("A", 0, "A"), ("B", ids.LEFT_OUT, "cut")]},
                                    list_paired=("levels",)), [("A", ["A", "1"], ["A", "1"]), ("B", ["B", "2"], None)])


if __name__ == "__main__":
    unittest.main()
