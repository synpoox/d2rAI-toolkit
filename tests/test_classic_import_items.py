"""Tests for shared/classic_import/items.py (run: python -m unittest discover tests). Synthetic tables, no game data."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.classic_import import ids as I, items  # noqa: E402

CTX = I.Context({}, {}, {}, {})


def table(header: str, *rows: str, key: int = 0) -> I.Table:
    return I.Table.of(header.split("|"), [r.split("|") for r in rows], "\r\n", key)


def tsv(header: str, *rows: str) -> bytes:
    return "".join("\t".join(r.split("|")) + "\r\n" for r in (header, *rows)).encode("latin-1")


def write(p: Path, data: bytes | str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))


class RuleTests(unittest.TestCase):
    def test_read_rule_collects_tables_and_no_drop_and_names_bad_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "item-tables.txt"
            p.write_text("# note\nmerge\tweapons\nmerge\tcubemain\nno-drop\tgold\n", "utf-8")
            self.assertEqual(items.read_rule(p, {"weapons": 1}), (["weapons", "cubemain"], {"gold"}))
            for text, msg in (("merge\tbows\n", "no merge rule for table 'bows'"), ("merge\n", "want 'merge")):
                p.write_text(text, "utf-8")
                with self.assertRaisesRegex(I.IdError, msg):
                    items.read_rule(p, {"weapons": 1})

    def test_read_rule_keeps_every_no_drop_field_and_refuses_extra_merge_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "item-tables.txt"
            p.write_text("no-drop\ta\tb\t\tc\nno-drop\td\n", "utf-8")
            self.assertEqual(items.read_rule(p, {}), ([], {"a", "b", "c", "d"}))
            p.write_text("merge\tweapons\textra\n", "utf-8")
            with self.assertRaisesRegex(I.IdError, "line 1: 'merge' takes one table.*extra"):
                items.read_rule(p, {"weapons": 1})


class MergeTests(unittest.TestCase):
    def test_merge_keyed_takes_source_values_keeps_d2r_only_rows_and_appends_new_ones(self):
        src = table("name|code|type", "Hand Axe|hax|axe", "Fresh|new|axe", key=1)
        d2r = table("name|code|type|extra", "Hand Axe d2r|hax|swor|e1", "Bow|bow|bow|e2", key=1)
        merged = items.merge_keyed("weapons", src, d2r, CTX, {"weapons": 1}, " X")
        self.assertEqual([r[1] for r in merged.rows], ["hax", "bow", "new"], "D2R's order, then the new row")
        self.assertEqual(merged.rows[0][2], "axe", "the source's value")
        self.assertEqual(merged.rows[1], ["Bow", "bow", "bow", "e2"], "a D2R-only row is untouched")
        self.assertEqual(merged.dropped, [])

    def test_merge_args_reach_the_table_merge(self):
        src = table("name|code|type", "Hand Axe|hax|axe", key=1)
        d2r = table("name|code|type", "Hand Axe d2r|hax|swor", key=1)
        merged = items.merge_keyed("weapons", src, d2r, CTX, {"weapons": 1}, " X", merge_args={"d2r_columns": ("type",)})
        self.assertEqual(merged.rows[0][2], "swor", "d2r_columns keeps D2R's value")
        self.assertEqual(items.merge_keyed("weapons", src, d2r, CTX, {"weapons": 1}, " X").rows[0][2], "axe")
        shout = items.merge_keyed("weapons", src, d2r, CTX, {"weapons": 1}, " X", merge_args={
            "spell": lambda t, c, v, ren: v.upper(), "finish": lambda h, row, s, own: row.append("f")})
        self.assertEqual(shout.rows[0][:3], ["HAND AXE", "hax", "AXE"], "spell overrides the default")
        cube = items.merge_cube(table("description|numinputs", "a|1"), table("description|numinputs"), CTX,
                                merge_args={"spell": lambda t, c, v, ren: v + "!"})
        self.assertEqual(cube.rows[0][1], "1!")

    def test_merge_args_can_be_per_table(self):
        src = table("name|code|type", "Hand Axe|hax|axe", key=1)
        d2r = table("name|code|type", "Hand Axe d2r|hax|swor", key=1)
        per = lambda t: {"d2r_columns": ("type",)} if t == "weapons" else {}
        self.assertEqual(items.merge_keyed("weapons", src, d2r, CTX, {"weapons": 1}, " X", merge_args=per).rows[0][2], "swor")
        self.assertEqual(items.merge_keyed("armor", src, d2r, CTX, {"armor": 1}, " X", merge_args=per).rows[0][2], "axe")

    def test_by_source_order_ranks_source_rows_first(self):
        src = table("Treasure Class|Picks", "B|1", "A|1")
        d2r = table("Treasure Class|Picks", "A|1", "Z|1", "B|1")
        merged = items.merge_keyed("treasureclassex", src, d2r, CTX, {}, "", by_source_order={"treasureclassex"})
        self.assertEqual([r[0] for r in merged.rows][:2], ["B", "A"])
        self.assertEqual([r[0] for r in merged.rows][2:], ["Z"], "D2R-only rows keep D2R's order after them")

    def test_merge_cube_keeps_source_recipes_then_d2r_only_and_runs_the_fixes(self):
        src = table("description|numinputs|input 1|output|op", "A|1|\"t1,qty=3\"|rare|", "B|1|x|y|5")
        d2r = table("description|numinputs|input 1|output|op", "d2r same as A|1|T1,QTY=3|RARE|", "D2R only|1|k|l|")
        seen = []
        merged = items.merge_cube(src, d2r, CTX, fixes=[lambda c: seen.append(len(c.rows)), items.count_each_input],
                                  after=[lambda c: seen.append(len(c.rows))])
        self.assertEqual(seen, [2, 3], "fixes see the source recipes, after sees the whole cube")
        self.assertEqual([r[0] for r in merged.rows], ["A", "B", "D2R only"])
        self.assertEqual(merged.rows[0][1], "3", "count_each_input: the stack counts as its quantity")

    def test_count_each_input_skips_listed_ops(self):
        cube = table("numinputs|input 1|input 2|op", "1|\"a,qty=2\"|b|", "9|a|b|30", "|a||")
        items.count_each_input(cube, skip_ops=("30",))
        self.assertEqual([r[0] for r in cube.rows], ["3", "9", ""])


class BlockDropsTests(unittest.TestCase):
    def setUp(self):
        self.tc = table("Treasure Class|Picks|NoDrop|Item1|Prob1|Item2|Prob2",
                        "A|1|0|hax|3|bow|7", "B|1|0|hax|5||", "C|1|0|B|2|bow|1", "D|-2|0|hax|1|bow|1")
        self.weapons = table("code|type|spawnable", "hax|axe|1", "bow|bow|1", key=0)
        self.types = table("Code|Equiv1|Equiv2", "axe|swor|", "swor||", "bow||")

    def test_a_blocked_code_moves_its_weight_to_nodrop_and_a_counted_pick_is_removed(self):
        codes = items.block_drops(self.tc, {"weapons": self.weapons}, self.types, {"hax"})
        self.assertEqual(codes, {"hax"})
        rows = {r[0]: r for r in self.tc.rows}
        self.assertEqual(rows["A"][2:], ["3", "bow", "7", "", ""])
        self.assertEqual(rows["D"][1:3], ["-1", "0"], "counted picks: one fewer, NoDrop unchanged")
        self.assertEqual(rows["C"][2:5], ["2", "bow", "1"], "B held only blocked items: it counts as blocked")
        self.assertEqual(self.weapons.rows[0][2], "0", "the item is unspawnable")
        self.assertEqual(self.weapons.rows[1][2], "1")

    def test_a_blocked_type_blocks_its_descendants(self):
        self.assertEqual(items.block_drops(self.tc, {"weapons": self.weapons}, self.types, {"swor"}), {"hax"})


class HdTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.hd = self.root / "hd" / "items"
        write(self.hd / "items.json", json.dumps([{"hax": {"asset": "axe1"}}, {"bow": {"asset": "bow1"}}]))
        write(self.hd / "uniques.json", "[]")
        write(self.hd / "sets.json", "[]")
        self.d2r = {"weapons": table("code|type|invfile", "hax|axe|inv_axe", "bow|bow|inv_bow")}

    def src(self, *rows: str):
        return {"weapons": table("code|type|invfile", *rows)}

    def test_a_wrong_hd_dir_names_the_table(self):
        write(self.hd / "items.json", "[]")
        with self.assertRaisesRegex(I.IdError, "weapons: no D2R row has an items.json entry"):
            items.hd_items(self.hd, self.src("ne1|axe|inv_axe"), self.d2r, [], [])

    def test_new_codes_borrow_pictures_and_uniques_follow_their_base_item(self):
        files = items.hd_items(self.hd, self.src("hax|axe|inv_axe", "ne1|axe|inv_axe", "ne2|bow|inv_unknown"), self.d2r,
                               [("My Unique", "ne1", None, "inv_axe")], [("The Set's Thing", "ne2", None, "x")])
        assets = {k: v["asset"] for e in files["items.json"] for k, v in e.items()}
        self.assertEqual((assets["ne1"], assets["ne2"]), ("axe1", "axe1"), "same invfile; else the table's first")
        self.assertEqual(files["uniques.json"], [{"my_unique": {"normal": "axe1", "uber": "axe1", "ultra": "axe1"}}])
        self.assertEqual(list(files["sets.json"][0]), ["the_sets_thing"])

    def test_own_pictures_set_the_ground_model_and_are_borrowed_from_the_type(self):
        models: dict[str, str] = {}
        files = items.hd_items(self.hd, self.src("ne2|bow|mine"), self.d2r, [], [], {"mine": "src/mine"}, models)
        self.assertEqual(files["items.json"][-1], {"ne2": {"asset": "src/mine"}})
        self.assertEqual(models, {"src/mine": "bow1"})

    def test_ground_models_follow_a_shared_flippyfile_a_stack_and_a_neutral_model(self):
        d2r = {"weapons": table("code|type|invfile|flippyfile", "hax|axe|inv_axe|flip_axe", "bow|bow|inv_bow|flip_bow")}
        head = "code|type|invfile|flippyfile"

        def model(*rows: str, neutral=None) -> dict[str, str]:
            models: dict[str, str] = {}
            items.hd_items(self.hd, {"weapons": table(head, *rows)}, d2r, [], [], {"mine": "src/mine"}, models, None,
                           neutral)
            return models
        self.assertEqual(model("ne1|none|mine|flip_bow", neutral={"weapons": "axe1"}), {"src/mine": "bow1"}, "flippyfile")
        self.assertEqual(model("hax|axe|inv_axe|flip_axe", "haxs|none|mine|flip_axe", neutral={"weapons": "bow1"}),
                         {"src/mine": "axe1"}, "a stack draws its base's model")
        self.assertEqual(model("ne3|none|mine|x", neutral={"weapons": "bow1"}), {"src/mine": "bow1"}, "neutral model")
        self.assertEqual(model("ne3|none|mine|x"), {"src/mine": "axe1"}, "no neutral model: the table's first")

    def test_a_four_letter_code_needs_bit_0x20_in_its_last_letter(self):
        with self.assertRaisesRegex(I.IdError, "bit 0x20"):
            items.hd_items(self.hd, self.src("abcD|axe|inv_axe"), self.d2r, [], [])

    def test_other_table_pictures_are_copied_into_the_borrowing_table(self):
        hd = self.root / "hd"
        write(hd / "global/ui/items/weapon/a1.sprite", "S")
        write(hd / "items/weapon/a1.json", "J")
        out = self.root / "out"
        items.borrow_pictures(hd, out, {("armor", "a1"): "weapons"})
        self.assertEqual((out / "global/ui/items/armor/a1.sprite").read_text(), "S")
        self.assertEqual((out / "items/armor/a1.json").read_text(), "J")
        write(hd / "items/armor/a1.json", "other")
        with self.assertRaisesRegex(I.IdError, "another picture"):
            items.borrow_pictures(hd, out, {("armor", "a1"): "weapons"})

    def test_ground_models_copy_the_stand_in_unit_file_per_table(self):
        write(self.hd / "weapon" / "bow1.json", "UNIT")
        out = self.root / "out"
        items.ground_models(self.hd, out, {"mine": "src/mine", "other": "src/other"}, {"src/mine": "bow1"},
                            {"mine": {"weapons", "misc"}, "other": {"misc"}})
        self.assertEqual((out / "weapon/src/mine.json").read_text(), "UNIT")
        self.assertEqual((out / "misc/src/mine.json").read_text(), "UNIT")
        self.assertFalse((out / "misc/src/other.json").exists(), "a picture without a model gets none")
        with self.assertRaisesRegex(I.IdError, "no unit file"):
            items.ground_models(self.hd, out, {"x": "src/x"}, {"src/x": "nope"}, {"x": {"weapons"}})


class ApplyTests(unittest.TestCase):
    def test_the_rule_kind_merges_the_listed_tables_and_writes_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "src/global/excel/weapons.txt", tsv("name|code|type", "Hand Axe|hax|axe", "Fresh|new|axe"))
            write(root / "d2r/global/excel/weapons.txt", tsv("name|code|type", "Hand Axe|hax|swor"))
            write(root / "merge/item-tables.txt", "merge\tweapons\n")
            with redirect_stdout(io.StringIO()):
                items.apply(root / "merge/item-tables.txt", root / "src", root / "d2r", root / "out", CTX,
                            {"weapons": 1}, " X")
            text = (root / "out/global/excel/weapons.txt").read_bytes().decode("latin-1").split("\r\n")
            self.assertEqual([line.split("\t")[1] for line in text[1:] if line], ["hax", "new"])

    def test_no_drop_with_the_item_tables_merged_runs_the_hd_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for base, code, name in (("src", "new", "Fresh"), ("d2r", "hax", "Axe")):
                write(root / base / "global/excel/weapons.txt",
                      tsv("name|code|type|invfile|spawnable", f"{name}|{code}|axe|inv_a|1", "Bow|bow|bow|inv_b|1"))
                write(root / base / "global/excel/armor.txt", tsv("name|code|type|invfile|spawnable", "Cap|cap|helm|inv_c|1"))
                write(root / base / "global/excel/misc.txt", tsv("name|code|type|invfile|spawnable", "Key|key|key|inv_k|1"))
                for extra in ("uniqueitems", "setitems"):
                    write(root / base / f"global/excel/{extra}.txt", tsv("index|code|invfile"))
                write(root / base / "global/excel/itemtypes.txt", tsv("ItemType|Code|Equiv1|Equiv2", "Axe|axe||", "Bow|bow||"))
                write(root / base / "global/excel/treasureclassex.txt",
                      tsv("Treasure Class|Picks|NoDrop|Item1|Prob1|Item2|Prob2", f"A|1|0|{code}|3|bow|7"))
            ctx = I.Context({"itemtypes": [("Axe", 0, "Axe"), ("Bow", 1, "Bow")], "uniqueitems": [], "setitems": []},
                            {}, {}, {})
            hd = root / "d2r/hd/items"
            write(hd / "items.json", json.dumps([{"hax": {"asset": "a1"}}, {"bow": {"asset": "b1"}},
                                                 {"cap": {"asset": "c1"}}, {"key": {"asset": "k1"}}]))
            write(hd / "uniques.json", "[]")
            write(hd / "sets.json", "[]")
            write(root / "merge/item-tables.txt", "merge\tweapons\nmerge\tarmor\nmerge\tmisc\nmerge\ttreasureclassex\nno-drop\tnew\tbow\n")
            with redirect_stdout(io.StringIO()) as buf:
                items.apply(root / "merge/item-tables.txt", root / "src", root / "d2r", root / "out", ctx,
                            {"weapons": 0, "armor": 0, "misc": 0, "treasureclassex": 0}, " X")
            self.assertIn("never drop: 2 items", buf.getvalue())
            tc = (root / "out/global/excel/treasureclassex.txt").read_bytes().decode("latin-1").split("\r\n")
            self.assertEqual(tc[1].split("\t")[2:4], ["10", ""], "both weights went to NoDrop")
            written = json.loads((root / "out/hd/items/items.json").read_text("utf-8"))
            self.assertIn({"new": {"asset": "a1"}}, written, "the new code borrows the D2R picture")


class PictureFolderTests(unittest.TestCase):
    def test_item_pictures_use_the_given_folder_and_default_to_src(self):
        from unittest import mock
        for kw, folder in (({}, "src"), ({"picture_folder": "mod"}, "mod")):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                write(root / "src/global/items/inv_a.dc6", b"x")
                write(root / "d2r/global/palette/units/pal.dat", b"p")
                written = []
                with mock.patch.object(items.dc6, "palette", return_value=None),                         mock.patch.object(items.dc6, "read", return_value=[None]),                         mock.patch.object(items.dc6, "decode", return_value=(2, 2, b"")),                         mock.patch.object(items.images, "scale", return_value="img"),                         mock.patch.object(items.images, "write_sprite", lambda p, i: written.append(p)):
                    got = items.item_pictures(lambda art, fr: {k: "big" for k in fr}, root, root / "src", root / "d2r",
                                              root / "out", {"inv_a": {"weapons"}}, set(), **kw)
                self.assertEqual(got, {"inv_a": f"{folder}/inv_a"})
                self.assertEqual([p.parent.name for p in written], [folder])


if __name__ == "__main__":
    unittest.main()
