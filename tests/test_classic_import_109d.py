"""Tests for shared/classic_import's 1.09d datasets, generator and converter (run: python -m unittest discover tests).

Synthetic data only. The tests that rebuild the committed datasets from the game files run when the inputs are on the
machine, named by environment variables (never stored in the repo): D2_109D_INSTALL (the 1.09d folder), D2_113C_PATCH
(1.13c's Patch_D2.mpq), D2R_EXCEL (D2R's data/global/excel/base) and D2R_IMAGE (a memory-layout dump of build 93847).
"""
from __future__ import annotations

import json
import os
import struct
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modkit.tsv import Table  # noqa: E402
from shared.classic_import import column_map as stage, extract, from_109d as C  # noqa: E402
from shared.classic_import import gen_109d_map as G, gen_109d_monster_ai as AI  # noqa: E402

PKG = Path(__file__).resolve().parent.parent / "shared" / "classic_import"


def env_path(name: str) -> Path | None:
    v = os.environ.get(name)
    return Path(v) if v and Path(v).exists() else None


def tab(name: str, *lines: str) -> Table:
    return Table.parse(name, "\n".join(lines) + "\n")


def rec(head: bytes, types: list[int], tail: bytes, wide: bool, pad: bytes = b"") -> bytes:
    return head + pad + (struct.pack(f"<{len(types)}H", *types) if wide else bytes(types)) + tail


class WidenTests(unittest.TestCase):
    def test_accepts_the_same_record_with_types_widened(self):
        old = rec(b"name", [50, 45, 0, 0xFF], b"\x03\x00", wide=False)
        new = rec(b"name", [50, 45, 0, 0xFFFF], b"\x03\x00", wide=True, pad=b"\x00")
        self.assertTrue(G.widened(old, new + b"\x00\x00", 4, 5, 4))

    def test_rejects_data_where_the_padding_should_be(self):
        old = rec(b"name", [50, 45], b"\x03", wide=False)
        new = rec(b"name", [50, 45], b"\x03", wide=True, pad=b"\x01")
        self.assertFalse(G.widened(old, new, 4, 5, 2))

    def test_rejects_a_changed_value(self):
        old = rec(b"name", [50, 45], b"\x03", wide=False)
        new = rec(b"name", [50, 45], b"\x04", wide=True)
        self.assertFalse(G.widened(old, new, 4, 4, 2))

    def test_rejects_a_changed_type(self):
        old = rec(b"name", [50, 45], b"\x03", wide=False)
        new = rec(b"name", [50, 46], b"\x03", wide=True)
        self.assertFalse(G.widened(old, new, 4, 4, 2))

    def test_records_split_a_bin_into_equal_records(self):
        data = struct.pack("<I", 2) + b"aabb"
        self.assertEqual(G.records(data), [b"aa", b"bb"])
        with self.assertRaises(G.GenError):
            G.records(struct.pack("<I", 2) + b"aab")


class HashCheckTests(unittest.TestCase):
    def test_a_file_that_is_not_the_recorded_one_stops_the_run(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.mpq"
            p.write_bytes(b"not an archive")
            with self.assertRaises(G.GenError):
                G.checked(p, "0" * 64)
            self.assertEqual(G.checked(p, extract.sha256(p)), p)
            with self.assertRaises(G.GenError):
                G.checked(Path(d) / "missing.mpq", "0" * 64)

    def test_inputs_come_from_arguments_or_the_environment(self):
        keep = {k: os.environ.pop(k, None) for k in ("D2_109D_INSTALL", "D2_113C_PATCH")}
        try:
            with self.assertRaises(G.GenError):
                G.inputs(None, None)
            os.environ["D2_109D_INSTALL"], os.environ["D2_113C_PATCH"] = "a", "b"
            self.assertEqual(G.inputs(None, "c"), (Path("a"), Path("c")))
        finally:
            for k, v in keep.items():
                os.environ.pop(k, None)
                if v is not None:
                    os.environ[k] = v


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads((PKG / "baselines" / "109d.json").read_text(encoding="utf-8"))

    def test_pins_every_archive_and_dll_with_a_sha256(self):
        for group in ("archives", "dlls"):
            self.assertTrue(self.base[group], group)
            for name, h in self.base[group].items():
                self.assertRegex(h, r"^[0-9a-f]{64}$", name)
        for name in ("Patch_D2.mpq", "d2exp.mpq", "d2data.mpq"):
            self.assertIn(name, self.base["archives"])
        self.assertIn("D2Game.dll", self.base["dlls"])

    def test_holds_no_install_path(self):
        text = json.dumps(self.base)
        self.assertNotIn("install", self.base)
        for bad in (":\\\\", ":/", "Users"):
            self.assertNotIn(bad, text)
        self.assertIn("PlugY*", self.base["not_part_of_109d"])
        self.assertTrue(set(self.base["not_part_of_109d"]).isdisjoint(self.base["dlls"]))

    def test_is_a_baseline_file_the_extract_check_reads(self):
        base = dict(self.base, extract={"Patch_D2.mpq": ["*"]})
        import tempfile
        with tempfile.TemporaryDirectory() as d:  # an empty folder: every archive missing, none wrongly accepted
            problems = extract.check(Path(d), base)
        self.assertEqual(len(problems), len(base["archives"]))


class MapDatasetTests(unittest.TestCase):
    def setUp(self):
        self.map = json.loads((PKG / "data" / "109d-to-113c-column-map.json").read_text(encoding="utf-8"))

    def test_holds_no_path_or_mod_text(self):
        text = json.dumps(self.map)
        for bad in (":\\\\", ":/", "Users", "docs/deviations", "orchestrator", "PR #", "d2-patches"):
            self.assertNotIn(bad, text)

    def test_every_column_has_a_known_kind_and_none_is_unmapped(self):
        from shared.classic_import.column_map import KINDS
        for t, e in self.map["tables"].items():
            for c, m in e.get("columns", {}).items():
                self.assertIn(m["kind"], KINDS, f"{t}.{c}")

    def test_the_tsv_lists_the_json(self):
        rows = (PKG / "data" / "109d-to-113c-column-map.tsv").read_text(encoding="utf-8").splitlines()[1:]
        n = sum(max(len(m["to"]), 1) for e in self.map["tables"].values() for m in e.get("columns", {}).values())
        n += sum("restructure" in e for e in self.map["tables"].values())
        self.assertEqual(len(rows), n)

    def test_baseid_is_an_ai_recode_and_not_a_row_number(self):
        m = self.map["tables"]["monstats"]["columns"]
        self.assertEqual(m["BaseId"]["to"], ["AI", "*BaseId 1.09d"])
        self.assertEqual(m["BaseId"]["kind"], "recode")
        self.assertNotIn("BaseId", [x for c in m.values() for x in c["to"]])  # 1.13c's BaseId stays blank

    def test_aiparam1_is_a_whole_row_recode_and_the_rest_have_no_target(self):
        m = self.map["tables"]["monstats"]["columns"]
        self.assertEqual(len(m["AIParam1"]["to"]), 16)
        self.assertEqual(m["AIParam1"]["to"][-1], "*AIParam 1.09d")
        for i in range(2, 6):
            self.assertEqual((m[f"AIParam{i}"]["kind"], m[f"AIParam{i}"]["to"]), ("recode", []))

    def test_value_maps_are_there(self):
        for k in ("skills.anim", "skills.monanim", "monstats.SkillSeq", "armor.sound", "weapons.sound", "misc.sound", "colors"):
            self.assertTrue(self.map["value_maps"][k], k)


# ---- the monster AI table

def pe(base: int, stamp: int, wide: bool, blob_at: int, blob: bytes) -> bytes:
    """A minimal PE (one section of file offset = RVA, as in a memory-layout dump) holding blob at RVA blob_at."""
    opt = 240 if wide else 224
    head = bytearray(0x400)
    head[0:2] = b"MZ"
    struct.pack_into("<I", head, 0x3C, 0x80)
    head[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHI", head, 0x84, 0x8664 if wide else 0x14C, 1, stamp)
    struct.pack_into("<H", head, 0x80 + 20, opt)
    o = 0x80 + 24
    struct.pack_into("<H", head, o, 0x20B if wide else 0x10B)
    if wide:
        struct.pack_into("<Q", head, o + 24, base)
    else:
        struct.pack_into("<I", head, o + 28, base)
    size = blob_at + len(blob)
    struct.pack_into("<8sIIII", head, o + opt, b".rdata", size, 0x400, size, 0x400)
    image = bytes(head).ljust(0x400, b"\0")
    return image + b"\0" * (blob_at - 0x400) + blob if blob_at > 0x400 else image + blob


class AiTableTests(unittest.TestCase):
    def test_reads_32_bit_records_as_rvas(self):
        base, at = 0x6FC30000, 0x1000
        recs = [(0, 0, 0), (1, 0, base + 0x93620), (2, base + 0x100, base + 0x200)]
        blob = b"".join(struct.pack("<IIII", k, i, t, 0) for k, i, t in recs)
        image = pe(base, 1, False, at, blob)
        self.assertEqual(AI.pe_layout(image)[:2], (base, 1))
        self.assertEqual(AI.ai_table(image, (at, 3, 16), wide=False), [(0, 0, 0), (1, 0, 0x93620), (2, 0x100, 0x200)])

    def test_reads_64_bit_records_as_rvas(self):
        base, at = 0x140000000, 0x1000
        blob = b"".join(struct.pack("<QQQQ", k, 0, base + t if t else 0, 0) for k, t in ((0, 0x78D20), (1, 0x5B43A0), (2, 0)))
        image = pe(base, AI.D2R_STAMP, True, at, blob)
        self.assertEqual(AI.pe_layout(image)[:2], (base, AI.D2R_STAMP))
        self.assertEqual(AI.ai_table(image, (at, 3, 32), wide=True), [(0, 0, 0x78D20), (1, 0, 0x5B43A0), (2, 0, 0)])

    def test_an_rva_in_no_section_fails(self):
        with self.assertRaises(G.GenError):
            AI.ai_table(pe(0x6FC30000, 1, False, 0x1000, b"\0" * 16), (0x90000, 1, 16), wide=False)


class PairingTests(unittest.TestCase):
    T9 = ("Class\tBaseId", "a\t1", "b\t1", "c\t2", "Expansion\t", "d\t3")

    def test_pairs_rows_by_position_and_counts_them(self):
        d2r = tab("monstats", "Id\tAI", "a\tSkeleton", "b\tSkeleton", "c\tZombie", "Expansion\t", "d\tIdle", "e\tNpc")
        self.assertEqual(AI.pairing(tab("monstats", *self.T9), d2r),
                         {"1": ("Skeleton", 2), "2": ("Zombie", 1), "3": ("Idle", 1)})

    def test_a_baseid_with_two_d2r_ais_fails(self):
        d2r = tab("monstats", "Id\tAI", "a\tSkeleton", "b\tZombie", "c\tZombie", "Expansion\t", "d\tIdle")
        with self.assertRaises(G.GenError):
            AI.pairing(tab("monstats", *self.T9), d2r)

    def test_rows_follow_the_1_09d_table_and_name_the_d2r_think_function(self):
        t109 = [(0, 0, 0), (1, 0, 0x93620), (1, 0, 0x96EC0), (1, 0, 0)]
        tdr = [(0, 0, 0x78D20), (0, 0, 0x4A3680), (1, 0, 0x5B43A0), (1, 0, 0x5BA780)]
        out = AI.rows({"1": ("Skeleton", 5), "2": ("Zombie", 5), "3": ("Idle", 4)}, t109, tdr,
                      ["None", "Idle", "Skeleton", "Zombie"])
        self.assertEqual(out[0], ["0", "0", "", "", "0", "", "", "", ""])
        self.assertEqual(out[1], ["1", "5", "Skeleton", "2", "1", "0x93620", "1", "0x5b43a0", "1>1 2>3 3>2 4>4"])
        self.assertEqual(out[2][8], "3>4")
        self.assertEqual(out[3], ["3", "4", "Idle", "1", "1", "", "0", "0x4a3680", "unverified"])

    def test_an_unknown_ai_or_a_baseid_past_the_table_fails(self):
        with self.assertRaises(G.GenError):
            AI.rows({"1": ("Nope", 1)}, [(0, 0, 0)] * 2, [(0, 0, 0)], ["None"])
        with self.assertRaises(G.GenError):
            AI.rows({"5": ("None", 1)}, [(0, 0, 0)] * 2, [(0, 0, 0)], ["None"])

    def test_slots_text(self):
        self.assertEqual([AI.slots_text(a) for a in ("", "BloodHawk", "Brute", "Idle")], ["", "none", "1>3 2>4", "unverified"])


class MonsterAiDatasetTests(unittest.TestCase):
    def setUp(self):
        lines = (PKG / "data" / "109d-monster-ai.tsv").read_text(encoding="utf-8").splitlines()
        self.header = lines[0].split("\t")
        self.rows = [dict(zip(self.header, l.split("\t"))) for l in lines[1:]]

    def test_has_a_row_per_record_of_the_1_09d_table(self):
        self.assertEqual(self.header, AI.COLUMNS)
        self.assertEqual([r["base_id"] for r in self.rows], [str(i) for i in range(AI.AI_TABLE_109D[1])])
        self.assertEqual(self.rows[0]["d2r_ai"], "")  # the empty record: no monster uses it

    def test_real_counts(self):
        used = [r for r in self.rows if r["d2r_ai"]]
        self.assertEqual(len(used), 265)
        self.assertEqual(len({r["d2r_ai"] for r in used}), 141)
        self.assertEqual(len({(r["think_109d_rva"], r["think_d2r_rva"]) for r in used}), 146)
        self.assertEqual(sum(int(r["monsters_109d"]) for r in used), 575)  # 1.09d's monstats records

    def test_known_pairs_from_both_think_tables(self):
        by = {r["d2r_ai"]: r for r in self.rows if r["d2r_ai"]}
        self.assertEqual((by["Skeleton"]["think_109d_rva"], by["Skeleton"]["think_d2r_rva"]), ("0x93620", "0x5b43a0"))
        self.assertEqual((by["Brute"]["think_109d_rva"], by["Brute"]["think_d2r_rva"]), ("0x8e9c0", "0x5acc20"))
        self.assertEqual(by["BloodHawk"]["param_slots"], "none")

    def test_slot_maps_in_the_table_are_the_curated_ones(self):
        for r in self.rows:
            self.assertEqual(r["param_slots"], AI.slots_text(r["d2r_ai"]))


# ---- rebuilding from the game files

@unittest.skipUnless(env_path("D2_109D_INSTALL") and env_path("D2_113C_PATCH"), "1.09d install or 1.13c patch not named")
class GeneratedMapTests(unittest.TestCase):
    def test_committed_map_is_what_the_installs_build(self):
        doc, tsv = G.build(G.extract(env_path("D2_109D_INSTALL"), env_path("D2_113C_PATCH")))
        self.assertEqual(json.loads(G.JSON_OUT.read_text(encoding="utf-8")), doc)
        self.assertEqual(G.TSV_OUT.read_text(encoding="utf-8"), tsv)

    def test_widening_proof_holds_on_the_real_bins(self):
        ex = G.extract(env_path("D2_109D_INSTALL"), env_path("D2_113C_PATCH"))  # raises if it does not
        for t in G.AFFIX:
            self.assertEqual(G.count(ex["y109"][f"{t}.bin"]), G.count(ex["y113"][f"{t}.bin"]))


@unittest.skipUnless(env_path("D2_109D_INSTALL") and env_path("D2R_EXCEL") and env_path("D2R_IMAGE"),
                     "1.09d install, D2R excel folder or D2R image not named")
class GeneratedMonsterAiTests(unittest.TestCase):
    def test_committed_table_is_what_the_files_build(self):
        text = AI.build(env_path("D2_109D_INSTALL"), env_path("D2R_EXCEL"), env_path("D2R_IMAGE"))
        self.assertEqual(AI.TSV_OUT.read_text(encoding="utf-8"), text)


# ---- the converter (from_109d): hooks on synthetic tables

class LookupTests(unittest.TestCase):
    def test_a_lookup_that_merges_two_values_cannot_be_reversed(self):
        lk = C.Lookup("t", {"aura": "", "none": ""})
        self.assertEqual(lk.fwd("aura"), "")
        with self.assertRaises(stage.MapError):
            lk.inv("")

    def test_a_lookup_has_no_entry_for_a_stranger(self):
        lk = C.Lookup("t", {"1": "a"})
        with self.assertRaises(stage.MapError):
            lk.fwd("2")
        with self.assertRaises(stage.MapError):
            lk.inv("b")

    def test_references_by_row_number(self):
        lk = C.refs("skills row", ["Attack", "Kick"], "0")
        self.assertEqual([lk.fwd("1"), lk.fwd("0")], ["Kick", ""])
        self.assertEqual([lk.inv("Kick"), lk.inv("")], ["1", "0"])
        with self.assertRaises(stage.MapError):
            lk.fwd("7")

    def test_srcdam_units(self):
        self.assertEqual([C.times16("6"), C.times16("-1"), C.times16(""), C.by16("96")], ["96", "-1", "", "6"])
        with self.assertRaises(stage.MapError):
            C.by16("100")

    def test_strip_and_put_back_a_prefix(self):
        fwd, inv = C.strip("STATE_")
        self.assertEqual((fwd("STATE_FOO"), inv("foo")), ("foo", "STATE_FOO"))
        with self.assertRaises(stage.MapError):
            fwd("state_foo")


class CarryCopiesTests(unittest.TestCase):
    MAP = {"tables": {"armor": {"columns": {"name": {"to": ["name"], "kind": "same"},
                                            "mindam": {"to": ["mindam"], "kind": "same"},
                                            "maxdam": {"to": ["maxdam"], "kind": "rename"}}}}}

    def test_a_repeated_name_goes_out_as_another_copy_of_its_target(self):
        t9 = {"armor": tab("armor", "name\tmindam\tmaxdam\tmindam\tmaxdam", "a\t1\t2\t3\t4", "Expansion", "b\t5\t6\t7\t8")}
        out = {"armor": tab("armor", "name\tmindam\tmaxdam", "a\t1\t2", "", "b\t5\t6")}
        out["armor"].rows[1] = ["Expansion", "", ""]
        C.carry_copies(t9, out, self.MAP)
        self.assertEqual(out["armor"].header, ["name", "mindam", "maxdam", "mindam", "maxdam"])
        self.assertEqual(out["armor"].rows, [["a", "1", "2", "3", "4"], ["Expansion", "", "", "", ""],
                                             ["b", "5", "6", "7", "8"]])


class AiParamTests(unittest.TestCase):
    """BaseId -> AI and the per-AI AIParam slot maps, through the real column-map stage on a one-table map."""

    ROWS = [  # base_id, d2r_ai, param_slots
        {"base_id": "0", "d2r_ai": "", "param_slots": ""},
        {"base_id": "1", "d2r_ai": "Skeleton", "param_slots": "1>1 2>3 3>2 4>4"},
        {"base_id": "2", "d2r_ai": "Zombie", "param_slots": "3>4"},
        {"base_id": "3", "d2r_ai": "Idle", "param_slots": "unverified"},
        {"base_id": "4", "d2r_ai": "BloodHawk", "param_slots": "none"},
        {"base_id": "5", "d2r_ai": "Skeleton", "param_slots": "1>1 2>3 3>2 4>4"},
    ]
    HEADER = "Class\tBaseId\tAIParam1\tAIParam2\tAIParam3\tAIParam4\tAIParam5"

    def setUp(self):
        full = C.load_map()["tables"]["monstats"]["columns"]
        self.map = {"tables": {"monstats": {"columns": {c: full[c] for c in self.HEADER.split("\t")}}}}
        self.ai = C.AiTable(self.ROWS)
        self.recode, self.back_only = C.ai_hooks(self.ai, self.map)

    def forward(self, *rows: str) -> Table:
        t = tab("monstats", self.HEADER, *rows)
        return stage.apply(self.map, {"monstats": t}, recode={k: f for k, (f, _) in self.recode.items()})["monstats"]

    def back(self, out: Table) -> list[list[str]]:
        rows = []
        for n, r in enumerate(out.records()):
            c = dict(zip(out.header, r))
            row = [self.recode["monstats.BaseId"][1](c, n)]
            row.append(self.recode["monstats.AIParam1"][1](c, n))
            row += [self.back_only[f"monstats.AIParam{i}"](c, n) for i in range(2, 6)]
            rows.append(row)
        return rows

    def cells(self, out: Table, n: int = 0) -> dict[str, str]:
        return {c: v for c, v in zip(out.header, out.records()[n]) if v}

    def test_baseid_becomes_the_d2r_ai_and_1_13c_baseid_stays_blank(self):
        out = self.forward("a\t1\t\t\t\t\t")
        self.assertEqual(self.cells(out), {"NameStr": "a", "AI": "Skeleton", "*BaseId 1.09d": "1"})
        self.assertFalse(out.has_col("BaseId"))

    def test_a_verified_ai_gets_its_slots_moved_on_all_difficulties(self):
        c = self.cells(self.forward("a\t1\t50\t30\t20\t40\t"))
        want = {"aip1": "50", "aip3": "30", "aip2": "20", "aip4": "40"}
        self.assertEqual({k: v for k, v in c.items() if k.startswith("aip")},
                         {f"{k}{d}": v for k, v in want.items() for d in ("", "(N)", "(H)")})

    def test_a_slot_with_no_d2r_home_goes_to_the_comment_column(self):
        c = self.cells(self.forward("a\t1\t50\t30\t20\t40\t7"))
        self.assertEqual(c["*AIParam 1.09d"], "P5=7")
        self.assertNotIn("aip5", c)
        c = self.cells(self.forward("a\t2\t1\t2\t3\t4\t5"))  # Zombie: only slot 3 is verified (-> aip4)
        self.assertEqual((c["aip4"], c["*AIParam 1.09d"]), ("3", "P1=1 P2=2 P4=4 P5=5"))
        self.assertNotIn("aip1", c)

    def test_an_ai_that_reads_no_parameter_copies_none(self):
        c = self.cells(self.forward("a\t4\t5\t6\t\t\t"))
        self.assertEqual(c["*AIParam 1.09d"], "P1=5 P2=6")
        self.assertFalse([k for k in c if k.startswith("aip")])

    def test_an_unverified_ai_keeps_the_plain_copy(self):
        c = self.cells(self.forward("a\t3\t10\t20\t\t\t50"))
        self.assertEqual({k: v for k, v in c.items() if k.startswith("aip")},
                         {f"aip{i}{d}": v for i, v in ((1, "10"), (2, "20"), (5, "50")) for d in ("", "(N)", "(H)")})
        self.assertNotIn("*AIParam 1.09d", c)

    def test_blank_and_unused_baseids_give_no_ai(self):
        out = self.forward("a\t\t\t\t\t\t", "b\t0\t\t\t\t\t")
        self.assertEqual([self.cells(out, n).get("AI") for n in (0, 1)], [None, None])
        self.assertEqual(self.back(out), [["", "", "", "", "", ""], ["0", "", "", "", "", ""]])

    def test_a_baseid_past_the_ai_table_fails(self):
        with self.assertRaises(stage.MapError):
            self.forward("a\t266\t\t\t\t\t")

    def test_every_case_comes_back(self):
        rows = ["a\t1\t50\t30\t20\t40\t7", "b\t2\t1\t2\t3\t4\t5", "c\t3\t10\t20\t\t\t50", "d\t4\t5\t6\t\t\t",
                "e\t5\t\t\t\t\t", "f\t\t\t\t\t\t"]
        back = self.back(self.forward(*rows))
        self.assertEqual(back, [r.split("\t")[1:] for r in rows])

    def test_parse_slots_and_the_unverified_list(self):
        self.assertEqual([C.parse_slots(x) for x in ("", "unverified", "none", "1>3 2>4")], [None, None, {}, {1: 3, 2: 4}])
        for bad in ("1>2 3>2", "x"):
            with self.assertRaises(stage.MapError):
                C.parse_slots(bad)
        t9 = {"monstats": tab("monstats", self.HEADER, "a\t1\t1\t\t\t\t", "b\t3\t\t\t\t\t", "c\t3\t5\t\t\t\t", "d\t3\t6\t\t\t\t")}
        self.assertEqual(C.unverified_ais(t9, self.ai), {"Idle": 2})  # Skeleton is verified; one Idle row has no parameter

    def test_the_committed_map_and_table_agree(self):
        ai = C.load_ai_table()
        rec, back = C.ai_hooks(ai, C.load_map())
        self.assertEqual(set(rec), {"monstats.BaseId", "monstats.AIParam1"})
        self.assertEqual(ai.ai("1"), "Skeleton")
        self.assertEqual(ai.slot_map("Skeleton"), {1: 1, 2: 3, 3: 2, 4: 4})
        self.assertEqual(stage.hooks(C.load_map())[0] & {"monstats.BaseId", "monstats.AIParam1"},
                         {"monstats.BaseId", "monstats.AIParam1"})


# ---- the converter on the real tables

# Byte fields in 1.09d's loaders (field type 4: uniqueitems D2Common 0x6fd4fb70, setitems 0x6fd50560), so a blank cell
# loads as 0. The flags come back as 0 where 1.09d left them blank.
BLANK_IS_ZERO = {("uniqueitems", "transform"), ("uniqueitems", "invtransform"), ("uniqueitems", "transformcolor"),
                 ("setitems", "transformcolor")}


def differences(t9: dict, again: dict, column_map: dict) -> list[str]:
    out = []
    for name, src in sorted(t9.items()):
        got = again[name]
        if len(got.rows) != len(src.rows):
            out.append(f"{name}: {len(src.rows)} rows came back as {len(got.rows)}")
            continue
        cols = column_map["tables"][name]["columns"]
        for i, col in enumerate(src.header):
            if not col or cols[col]["kind"] == "drop":  # every copy of a repeated name counts
                continue
            bad, zero = [], (name, col) in BLANK_IS_ZERO
            for n, (a, b) in enumerate(zip(src.rows, got.rows)):
                if not src.is_record(a) and i > 0:  # separator rows ("Expansion") are not records: only their key counts
                    continue
                x, y = (a[i] if i < len(a) else ""), b[i]
                if zero:
                    x, y = x or "0", y or "0"
                if x != y and (x.strip() or y.strip()):  # a whitespace-only cell is a blank one
                    bad.append(f"row {n} {x!r} -> {y!r}")
            if bad:
                k = src.header[:i].count(col)
                out.append(f"{name}.{col}{f' copy {k + 1}' if k else ''}: {len(bad)} cells, e.g. {', '.join(bad[:3])}")
    return out


class DifferencesTests(unittest.TestCase):
    MAP = {"tables": {"t": {"columns": {"a": {"kind": "same"}, "b": {"kind": "drop"}, "z": {"kind": "recode"}}}}}

    def test_reports_a_changed_cell_but_not_a_drop_column_or_a_blank_that_is_zero(self):
        t9 = {"t": tab("t", "a\tb\tz", "1\tx\t", "Expansion", "2\ty\t5")}
        same = {"t": tab("t", "a\tb\tz", "1\t\t", "Expansion", "2\t\t5")}
        self.assertEqual(differences(t9, same, self.MAP), [])
        diff = {"t": tab("t", "a\tb\tz", "1\t\t", "Expansion", "3\t\t5")}
        self.assertEqual(len(differences(t9, diff, self.MAP)), 1)
        short = {"t": tab("t", "a\tb\tz", "1\t\t", "Expansion")}
        self.assertIn("3 rows came back as 2", differences(t9, short, self.MAP)[0])


@unittest.skipUnless(env_path("D2_109D_INSTALL") and env_path("D2_113C_PATCH"), "1.09d install or 1.13c patch not named")
class RoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ex = G.extract(env_path("D2_109D_INSTALL"), env_path("D2_113C_PATCH"))
        cls.t9, cls.t13 = C.tables(ex["y109"]), C.tables(ex["y113"])
        cls.map, cls.ai = C.load_map(), C.load_ai_table()
        cls.out = C.forward(cls.t9, cls.t13)

    def test_109d_comes_back_except_drop_columns(self):
        self.assertEqual(differences(self.t9, C.back(self.out, self.t9, self.t13), self.map), [])

    def test_the_known_conversions(self):
        out, t9, t13 = self.out, self.t9, self.t13
        sk = out["skills"]
        self.assertEqual(sk.get(sk.need("Multiple Shot", "skill"), "SrcDam"), "96")  # 1.09d 6 eighths
        self.assertIn("Angelical Raiment", {r[0] for r in out["sets"].records()})
        skill = {r[sk.col("Id")]: r[0] for r in sk.records()}
        self.assertEqual([skill["311"], skill["312"]], ["mon inferno sentry", "mon death sentry"])  # 1.10's rename
        ms9 = t9["monstats"]
        sentry = ms9.find("Inferno Sentry")
        self.assertEqual(out["monstats"].get(out["monstats"].records()[ms9.records().index(sentry)], "Skill1"), "mon inferno sentry")
        isc, isc13 = out["itemstatcost"], t13["itemstatcost"]
        op13 = {r[isc13.col("ID")]: r[isc13.col("op")] for r in isc13.records()}
        mine = {r[isc.col("ID")]: r[isc.col("op")] for r in isc.records() if r[isc.col("op")]}
        self.assertEqual(len(mine), 77)
        self.assertEqual({k: v for k, v in mine.items() if op13.get(k) and op13[k] != v}, {})  # 1.10's op where it has one
        for name, col in [("armor", "mindam"), ("armor", "maxdam"), ("automap", "Type2"), ("chartemplate", "SkillName")]:
            self.assertEqual(out[name].header.count(col), t13[name].header.count(col), f"{name}.{col}")
        ct = out["chartemplate"].header
        self.assertEqual([ct[i + 1] for i, c in enumerate(ct) if c == "SkillName"], [f"Skill{n}" for n in range(1, 10)])
        ms = out["monstats"]
        self.assertEqual(ms.get(ms.records()[0], "minHP"), t9["monstats"].get(t9["monstats"].records()[0], "MinHP"))

    def test_baseid_is_the_ai_of_the_same_d2r_row_and_1_13c_baseid_is_blank(self):
        ms, ms9 = self.out["monstats"], self.t9["monstats"]
        self.assertFalse(ms.has_col("BaseId"))
        t13 = self.t13["monstats"]
        for r, r9, r13 in zip(ms.records(), ms9.records(), t13.records()):
            self.assertEqual(ms.get(r, "AI"), t13.get(r13, "AI"))  # D2R's AI of the row (checked equal to 1.13c's)
            self.assertEqual(ms.get(r, "*BaseId 1.09d"), ms9.get(r9, "BaseId"))

    def test_aiparams_follow_the_slot_maps(self):
        ms, ms9 = self.out["monstats"], self.t9["monstats"]
        seen = Counter()
        for r, r9 in zip(ms.records(), ms9.records()):
            ai = ms.get(r, "AI")
            p = [ms9.get(r9, f"AIParam{i}") for i in range(1, 6)]
            if ai == "Skeleton":
                got = [ms.get(r, c) for c in ("aip1", "aip3", "aip2", "aip4")]
                self.assertEqual(got, p[:4])
                seen[ai] += 1
            elif ai == "Brute":
                self.assertEqual([ms.get(r, "aip3"), ms.get(r, "aip4")], p[:2])
                seen[ai] += 1
            elif ai == "BloodHawk":
                self.assertEqual([ms.get(r, f"aip{i}") for i in range(1, 6)], [""] * 5)
                seen[ai] += 1
            elif self.ai.slot_map(ai) is None:
                self.assertEqual([ms.get(r, f"aip{i}") for i in range(1, 6)], p)  # the plain copy
        self.assertEqual(set(seen), {"Skeleton", "Brute", "BloodHawk"})

    def test_the_unverified_list_is_not_empty_and_names_no_verified_ai(self):
        un = C.unverified_ais(self.t9, self.ai)
        self.assertTrue(un)
        self.assertTrue(set(un).isdisjoint(AI.AI_PARAM_SLOTS))


if __name__ == "__main__":
    unittest.main()
