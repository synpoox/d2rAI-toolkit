"""Regenerate data/109d-monster-ai.tsv: 1.09d's monster AI (a monstats `BaseId`) paired with D2R's `AI`.

    py -3 -m shared.classic_import.gen_109d_monster_ai --install <1.09d folder> --d2r-excel <D2R excel folder>
                                                       --d2r-image <D2R memory-layout dump> [--out <folder>] [--check]

The inputs can also come from the environment (D2_109D_INSTALL, D2R_EXCEL, D2R_IMAGE) and are never stored in the output.

What the table says
  * 1.09d has no `AI` column. D2Common's monstats loader reads the column `BaseId` as an int: the index of the monster's
    record in D2Game's AI table (RVA 0xebac8, 266 records of 16 bytes {kind, init, think, next}; pointers are absolute,
    image base 0x6fc30000). BaseId is NOT a monstats row number.
  * D2R 93847 has `AI` (a name from monai.txt) and its AI table at RVA 0x2396e90 (155 records of 32 bytes, same fields,
    image base 0x140000000), indexed by the monai row.
  * The monstats rows of the two builds line up one to one (the Expansion separator is row 410 in both), so the AI a
    1.09d monster gets in D2R is the `AI` of the same row. This generator checks that every BaseId maps to exactly one
    D2R AI (it does: 265 BaseIds, 141 distinct AIs) and writes the pair of think functions of each row.

Columns: base_id, monsters_109d (monstats rows using it), d2r_ai, d2r_ai_index, kind_109d, think_109d_rva, kind_d2r,
think_d2r_rva, param_slots. A BaseId no monster uses (0, the empty record) has a blank d2r_ai.

param_slots says where the AI's parameters went (1.10 moved the AIParam slots; see AI_PARAM_SLOTS): "1>1 2>3" = 1.09d
AIParam1 is D2R aip1, AIParam2 is aip3; "none" = verified that 1.09d's think function reads no parameter; "unverified" =
the slots were not read on both builds, so a converter keeps the plain copy (AIParamN -> aipN) and says so.
The image must be a memory-layout dump (section file offsets equal RVAs) of build 93847 (PE stamp 0x6ab3782c; see
knowledge/engine-re.md).
"""
from __future__ import annotations

import argparse
import os
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

from modkit.tsv import Table

from . import extract as extract_mod
from . import gen_109d_map as G

HERE = Path(__file__).resolve().parent
TSV_OUT = HERE / "data" / "109d-monster-ai.tsv"
COLUMNS = ["base_id", "monsters_109d", "d2r_ai", "d2r_ai_index", "kind_109d", "think_109d_rva", "kind_d2r",
           "think_d2r_rva", "param_slots"]
AI_TABLE_109D = (0xEBAC8, 266, 16)   # D2Game.dll 1.09d: RVA, records, record size
AI_TABLE_D2R = (0x2396E90, 155, 32)  # D2R build 93847: RVA, records, record size
D2R_STAMP = 0x6AB3782C               # PE TimeDateStamp of the 93847 dump under D2RLoader 1.3.1

# Verified AI parameter slot maps, {AI: {1.09d AIParamN: D2R aipM}}, read from both think functions (1.09d D2Game.dll
# RVA / D2R RVA). An AI not listed keeps the plain copy and is "unverified". {} = verified that 1.09d reads none.
#   Skeleton   0x93620 / 0x5b43a0: P1 approach %, P2 attack %, P3 idle frames, P4 attack 1 vs 2; D2R aip1, aip3, aip2, aip4
#   Brute      0x8e9c0 / 0x5acc20: same logic, P1 -> aip3, P2 -> aip4
#   Zombie     0x96ec0 / 0x5ba780: P3 (attack 1 vs 2) -> aip4; its other slots are not verified, so they are not carried
#   BloodHawk  0x95810 / 0x5aca20: 1.09d hard-codes its 69 %, 10 % and +-50; D2R reads aip1, aip2, aip5 for them
AI_PARAM_SLOTS: dict[str, dict[int, int]] = {
    "Skeleton": {1: 1, 2: 3, 3: 2, 4: 4},
    "Brute": {1: 3, 2: 4},
    "Zombie": {3: 4},
    "BloodHawk": {},
}


def slots_text(ai: str) -> str:
    """The param_slots cell of an AI."""
    if not ai:
        return ""
    if ai not in AI_PARAM_SLOTS:
        return "unverified"
    return " ".join(f"{a}>{b}" for a, b in sorted(AI_PARAM_SLOTS[ai].items())) or "none"


def pe_layout(image: bytes) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    """(image base, TimeDateStamp, [(virtual address, virtual size, raw offset, raw size)]) of a 32- or 64-bit PE."""
    pe = struct.unpack_from("<I", image, 0x3C)[0]
    if image[pe:pe + 4] != b"PE\0\0":
        raise G.GenError("not a PE file")
    n, stamp = struct.unpack_from("<H", image, pe + 6)[0], struct.unpack_from("<I", image, pe + 8)[0]
    opt = struct.unpack_from("<H", image, pe + 20)[0]
    magic = struct.unpack_from("<H", image, pe + 24)[0]
    base = struct.unpack_from("<Q", image, pe + 48)[0] if magic == 0x20B else struct.unpack_from("<I", image, pe + 52)[0]
    first = pe + 24 + opt
    secs = []
    for i in range(n):
        _, vs, va, rs, ro = struct.unpack_from("<8sIIII", image, first + 40 * i)
        secs.append((va, vs, ro, rs))
    return base, stamp, secs


def file_offset(secs: list[tuple[int, int, int, int]], rva: int) -> int:
    for va, vs, ro, rs in secs:
        if va <= rva < va + max(vs, rs):
            return ro + rva - va
    raise G.GenError(f"RVA {rva:#x} is in no section")


def ai_table(image: bytes, spec: tuple[int, int, int], wide: bool) -> list[tuple[int, int, int]]:
    """[(kind, init rva, think rva)] of an AI table; an RVA of 0 is a null pointer. wide = 64-bit pointers (D2R)."""
    rva, n, size = spec
    base, _, secs = pe_layout(image)
    at = file_offset(secs, rva)
    fmt = "<QQQQ" if wide else "<IIII"
    out = []
    for i in range(n):
        kind, init, think, _ = struct.unpack_from(fmt, image, at + i * size)
        out.append((kind, init - base if init else 0, think - base if think else 0))
    return out


def pairing(t9: Table, d2r: Table) -> dict[str, tuple[str, int]]:
    """{BaseId: (D2R AI, number of 1.09d monstats rows with it)} from the rows of 1.09d's monstats and D2R's monstats.

    Rows pair by position (1.09d's records against the first records of D2R's). A BaseId whose rows get different D2R AIs
    fails: the pairing would not be a function."""
    r9, rr = t9.records(), d2r.records()
    if len(rr) < len(r9):
        raise G.GenError(f"D2R monstats has {len(rr)} records, 1.09d's {len(r9)}")
    b9, ai = t9.col("BaseId"), d2r.col("AI")
    found: dict[str, Counter] = defaultdict(Counter)
    for x, y in zip(r9, rr):
        found[x[b9]][y[ai]] += 1
    out = {}
    for base, c in found.items():
        if len(c) != 1:
            raise G.GenError(f"BaseId {base!r} gets {len(c)} different D2R AIs: {dict(c)}")
        out[base] = (next(iter(c)), sum(c.values()))
    return out


def rows(pair: dict[str, tuple[str, int]], t109: list[tuple[int, int, int]], tdr: list[tuple[int, int, int]],
         ai_names: list[str]) -> list[list[str]]:
    """The table's rows, one per record of 1.09d's AI table, in BaseId order."""
    index = {n: i for i, n in enumerate(ai_names)}
    if "" in pair or any(not b.isdigit() or int(b) >= len(t109) for b in pair):
        raise G.GenError(f"a BaseId is not a record of the {len(t109)}-record AI table: {sorted(pair)[:5]}")
    hexa = lambda v: f"{v:#x}" if v else ""  # noqa: E731
    out = []
    for base in range(len(t109)):
        ai, n = pair.get(str(base), ("", 0))
        if ai and ai not in index:
            raise G.GenError(f"D2R AI {ai!r} is not in monai.txt")
        k9, _, think9 = t109[base]
        kd, _, thinkd = tdr[index[ai]] if ai else (None, 0, 0)
        out.append([str(base), str(n), ai, str(index[ai]) if ai else "", str(k9), hexa(think9),
                    "" if kd is None else str(kd), hexa(thinkd), slots_text(ai)])
    return out


def tsv_text(table_rows: list[list[str]]) -> str:
    return "\n".join("\t".join(r) for r in [COLUMNS] + table_rows) + "\n"


def build(install: Path, d2r_excel: Path, d2r_image: Path) -> str:
    """The table's TSV text from the 1.09d install (hash-checked), D2R's monstats.txt and monai.txt and the D2R dump."""
    base = G.baseline()
    dll = G.checked(install / "D2Game.dll", base["dlls"]["D2Game.dll"])
    a = base["archives"]
    paths = [G.checked(install / n, a[n]) for n in ("Patch_D2.mpq", "d2exp.mpq", "d2data.mpq")]
    files = G.stack(paths)
    t9 = Table.parse("monstats", files["monstats.txt"].decode("latin-1"))
    d2r = Table.parse("monstats", (d2r_excel / "monstats.txt").read_bytes().decode("latin-1"))
    monai = Table.parse("monai", (d2r_excel / "monai.txt").read_bytes().decode("latin-1"))
    names = [r[0] for r in monai.records()]
    if len(names) != AI_TABLE_D2R[1]:
        raise G.GenError(f"monai.txt has {len(names)} records, D2R's AI table {AI_TABLE_D2R[1]}")
    image = d2r_image.read_bytes()
    stamp = pe_layout(image)[1]
    if stamp != D2R_STAMP:
        raise G.GenError(f"the D2R image is stamp {stamp:#x}, not build 93847's {D2R_STAMP:#x}")
    t109 = ai_table(dll.read_bytes(), AI_TABLE_109D, wide=False)
    tdr = ai_table(image, AI_TABLE_D2R, wide=True)
    return tsv_text(rows(pairing(t9, d2r), t109, tdr, names))


def summary(text: str) -> str:
    recs = [l.split("\t") for l in text.splitlines()[1:]]
    used = [r for r in recs if r[2]]
    pairs = {(r[5], r[7]) for r in used}
    return (f"{len(recs)} records, {len(used)} BaseIds used, {len({r[2] for r in used})} distinct D2R AIs, "
            f"{len(pairs)} distinct think-function pairs")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--install", help="the 1.09d folder (or D2_109D_INSTALL)")
    ap.add_argument("--d2r-excel", help="D2R's data/global/excel/base folder (or D2R_EXCEL)")
    ap.add_argument("--d2r-image", help="a memory-layout dump of D2R build 93847 (or D2R_IMAGE)")
    ap.add_argument("--out", type=Path, help="write the table here instead of data/")
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if the committed table differs")
    args = ap.parse_args(argv)
    got = [args.install or os.environ.get("D2_109D_INSTALL"), args.d2r_excel or os.environ.get("D2R_EXCEL"),
           args.d2r_image or os.environ.get("D2R_IMAGE")]
    try:
        if not all(got):
            raise G.GenError("needs --install, --d2r-excel and --d2r-image (or D2_109D_INSTALL, D2R_EXCEL, D2R_IMAGE)")
        text = build(*map(Path, got))
    except G.GenError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(summary(text))
    if args.check:
        same = TSV_OUT.read_text(encoding="utf-8") == text
        print("committed table is current" if same else "committed table differs")
        return 0 if same else 1
    out = args.out / TSV_OUT.name if args.out else TSV_OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
