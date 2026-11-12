"""Tests for shared/classic_import's 1.09d datasets and generators (run: python -m unittest discover tests).

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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modkit.tsv import Table  # noqa: E402
from shared.classic_import import extract, gen_109d_map as G, gen_109d_monster_ai as AI  # noqa: E402

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
        self.assertNotRegex(text, r"#\d+|PR #|\.md\b|[A-Za-z]:[\\/]|Users")
        terms = Path.home() / ".d2r-modkit" / "private_terms.txt"  # the same list tools/check_public.py reads
        if terms.is_file():
            for line in terms.read_text(encoding="utf-8").splitlines():
                word = line.split("#", 1)[0].strip().lower()
                if word:
                    self.assertNotIn(word, text.lower(), "a private term (not printed) is in the map")

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

    def test_a_verified_ai_with_another_1_09d_think_fails(self):
        with self.assertRaises(G.GenError):
            AI.rows({"1": ("Skeleton", 1)}, [(0, 0, 0), (1, 0, 0x12345)], [(0, 0, 0)] * 3, ["None", "Idle", "Skeleton"])

    def test_the_expansion_separator_must_line_up(self):
        d2r = tab("monstats", "Id	AI", "a	Skeleton", "b	Skeleton", "Expansion	", "c	Zombie", "d	Idle", "e	Npc")
        with self.assertRaises(G.GenError):
            AI.pairing(tab("monstats", *self.T9), d2r)

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


if __name__ == "__main__":
    unittest.main()
