"""Regenerate the 1.09d -> 1.13c excel column map (data/109d-to-113c-column-map.json and .tsv) from the game files.

    py -3 -m shared.classic_import.gen_109d_map --install <1.09d folder> --patch-113c <1.13c Patch_D2.mpq> [--out <folder>]
    py -3 -m shared.classic_import.gen_109d_map --install ... --patch-113c ... --check     # compare with the committed map

The two paths can also come from the environment (D2_109D_INSTALL, D2_113C_PATCH); they are never stored in the output.
Never hand-edit the map: change a curated rule in `build` and rerun.

Sources and proofs:
  * The 1.09d install is checked against baselines/109d.json (SHA-256 of Patch_D2.mpq, d2exp.mpq and d2data.mpq) and
    1.13c's Patch_D2.mpq against PATCH_113C below; a mismatch stops the run. Excel files are read as the game does: the
    first archive of the stack (patch, then d2exp, then d2data) that has the file wins.
  * 1.13c's base MPQs are 1.09d's, byte for byte, so only its patch is read.
  * 1.13c ships automagic, rareprefix and raresuffix only as .bin. `widened` proves each record is the 1.09d .txt
    compiled with the item-type slots widened from bytes to words (the only change 1.10 made), so the 1.09d .txt
    columns are also 1.13c's.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

from . import extract as extract_mod
from . import mpq

HERE = Path(__file__).resolve().parent
BASELINE_FILE = HERE / "baselines" / "109d.json"
PATCH_113C = "b976e7847dda696f54198a9477819f96579c4894f54381c72afb4937e919e0a9"  # 1.13c Patch_D2.mpq
EXCEL = "data\\global\\excel\\"
JSON_OUT, TSV_OUT = HERE / "data" / "109d-to-113c-column-map.json", HERE / "data" / "109d-to-113c-column-map.tsv"
# No listfile names the excel folder, so every known table name is probed as .txt and .bin.
KNOWN = """aiparms arena armtype armor automagic automap belts bodylocs books charstats chartemplate colors compcode composit
cubemain cubemod cubetype difficultylevels elemtypes events experience gamble gems hiredesc hireling hitclass inventory itemratio
itemstatcost itemtypes leveldefs levels lowqualityitems lvlmaze lvlprest lvlsub lvltypes lvlwarp magicprefix magicsuffix misc
misscalc missiles monai monequip monitempercent monlvl monmode monname monplace monpreset monprop monseq monsounds monstats
monstats2 montype monumod npc objects objgroup objmode objtype objpreset overlay pettype playerclass plrmode plrtype properties qualityitems
rareprefix raresuffix runes setitems sets shrines skillcalc skilldesc skills soundenviron sounds states storepage superuniques
treasureclass treasureclassex uniqueappellation uniqueitems uniqueprefix uniquesuffix uniquetitle weaponclass weapons
wanderingmon skilltree misscode itemscode""".split()
# 1.13c's patch ships only .bin for these: table -> (item-type slot offset in a 1.09d record, in a 1.13c record, slot count:
# itype1-7 + etypes). 1.10 widened the slots from bytes to words; nothing else in the record changed.
AFFIX = {"automagic": (105, 106, 12), "rareprefix": (16, 16, 11), "raresuffix": (16, 16, 11)}


class GenError(RuntimeError):
    """An input that is not the pinned one, or a file the proof does not hold for."""


def baseline() -> dict:
    return json.loads(BASELINE_FILE.read_text(encoding="utf-8"))


def checked(path: Path, want: str) -> Path:
    if not path.is_file():
        raise GenError(f"{path.name}: not found in {path.parent}")
    got = extract_mod.sha256(path)
    if got != want:
        raise GenError(f"{path.name}: SHA-256 {got} is not the recorded {want}")
    return path


def stack(paths: list[Path]) -> dict[str, bytes]:
    """Excel files by name, read as the game does: the first archive (highest priority) that has a file wins."""
    arcs = [mpq.Archive(p) for p in paths]
    names = {f"{k}.{e}" for k in KNOWN for e in ("txt", "bin")}
    for a in arcs:
        try:
            names |= {n.lower().replace("/", "\\").split("\\")[-1] for n in a.names() if "excel" in n.lower()}
        except KeyError:  # no listfile
            pass
    out = {}
    for n in sorted(names):
        for a in arcs:
            if a.has(EXCEL + n):
                out[n] = a.read(EXCEL + n)
                break
    return out


def records(data: bytes) -> list[bytes]:
    n = count(data)
    if not n or (len(data) - 4) % n:
        raise GenError(f"a .bin of {len(data)} bytes does not hold {n} equal records")
    size = (len(data) - 4) // n
    return [data[4 + i * size:4 + (i + 1) * size] for i in range(n)]


def widened(old: bytes, new: bytes, at_old: int, at_new: int, n: int) -> bool:
    """True if `new` is `old` with its n byte slots at at_old stored as words at at_new (0xFF = none = 0xFFFF), padding aside."""
    if any(new[at_old:at_new]):
        return False
    words = struct.pack(f"<{n}H", *(0xFFFF if v == 0xFF else v for v in old[at_old:at_old + n]))
    a, b = old[:at_old] + words + old[at_old + n:], new[:at_old] + new[at_new:]
    k = min(len(a), len(b))
    return a[:k] == b[:k] and not a[k:].strip(b"\0") and not b[k:].strip(b"\0")


def extract(install: Path, patch_113c: Path) -> dict[str, dict[str, bytes]]:
    """The excel files of both stacks, by name, after the hash checks and the affix widening proof."""
    a = baseline()["archives"]
    base = [checked(install / n, a[n]) for n in ("d2exp.mpq", "d2data.mpq")]
    y109 = stack([checked(install / "Patch_D2.mpq", a["Patch_D2.mpq"])] + base)
    # 1.13c's base MPQs are 1.09d's, byte for byte, so only its patch differs.
    y113 = stack([checked(patch_113c, PATCH_113C)] + base)
    for t, (o9, o13, n) in AFFIX.items():
        old, new = records(y109[f"{t}.bin"]), records(y113[f"{t}.bin"])
        if len(old) != len(new) or not all(widened(x, y, o9, o13, n) for x, y in zip(old, new)):
            raise GenError(f"1.13c {t}.bin is no longer 1.09d's {t}.txt compiled: find 1.13c's real {t}.txt")
    return {"y109": y109, "y113": y113}


def count(data: bytes | None) -> int | None:
    return struct.unpack_from("<I", data)[0] if data else None


def build(EX: dict[str, dict[str, bytes]]) -> tuple[dict, str]:
    """The map (JSON document, TSV text) from extract()'s tables."""
    def load(v, t):
        d = EX[v].get(f"{t}.txt")
        if d is None: return None
        ls = d.decode("latin-1").replace("\r", "").split("\n")
        h = [x.strip() for x in ls[0].split("\t")]
        rows = [[c.strip() for c in l.split("\t")] for l in ls[1:] if l.strip()]
        return h, rows

    T109 = sorted(n[:-4] for n in EX["y109"] if n.endswith(".txt"))
    T113 = sorted(n[:-4] for n in EX["y113"] if n.endswith(".txt"))


    # Curated entries: table -> {1.09d column: (targets, kind, transform)}; a target "t.c" lives in another 1.13c table.
    # kinds: rename, split (one 1.09d value feeds several 1.13c columns), moved (other table), recode (same column,
    # value encoding changed), drop (no 1.13c home), restructure (row layout changed; transform says how).
    R = defaultdict(dict)
    def cur(t, col, to, kind, tr=""): R[t][col] = (to if isinstance(to, list) else ([to] if to else []), kind, tr)

    DMG = ("1.09d has 3 skill-level brackets (2-8, 9-16, 17+: D2Common 0x6fda4100 adds LevDam1 per level up to 8, LevDam2 to 16, LevDam3 "
           "after); 1.10+ has 5 (2-8, 9-16, 17-22, 23-28, 29+) and split min/max: copy bracket 3 into 4 and 5, so every level sums the same")
    for t, pfx in (("skills", ""), ("missiles", "")):
        for i in (1, 2, 3):
            cur(t, f"LevDam{i}", [f"MinLevDam{i}", f"MaxLevDam{i}"] + ([f"MinLevDam{j}" for j in (4, 5)] + [f"MaxLevDam{j}" for j in (4, 5)] if i == 3 else []), "split", DMG)
    cur("skills", "SrcDam", "SrcDam", "recode", "units: 1.09d eighths (8 = 100% weapon damage), 1.13c 128ths (128 = 100%): multiply by 16. Code: 1.09d D2Common "
        "0x6fda4185 and 0x6fdac0b1 (weapon damage * SrcDam >> 3), D2R 0x14028cd09 (>> 7)")
    cur("missiles", "SrcDamage", "SrcDamage", "recode", "units: eighths -> 128ths, multiply by 16 (-1 kept)")
    for i in (1, 2, 3):
        cur("skills", f"ELev{i}", [f"EMinLev{i}", f"EMaxLev{i}"] + ([f"EMinLev{j}" for j in (4, 5)] + [f"EMaxLev{j}" for j in (4, 5)] if i == 3 else []), "split", DMG)
        cur("missiles", f"ELev{i}", [f"MinELev{i}", f"MaxELev{i}"] + ([f"MinELev{j}" for j in (4, 5)] + [f"MaxELev{j}" for j in (4, 5)] if i == 3 else []), "split", DMG)
    for i in range(1, 7):
        cur("skills", f"Param{i} Description", f"*Param{i} Description", "rename", "comment column")
    cur("missiles", "Param1 Comment", "*param1 desc", "rename", "comment column")
    cur("missiles", "Param2 Comment", "*param2 desc", "rename", "comment column")
    for t in ("skills", "missiles"):
        for c in ("Open", "Beta"): cur(t, c, None, "drop", "dev bookkeeping flag")
    cur("missiles", "Skill", "Skill", "recode", "1.09d skills row number -> skills name (resolve via 1.09d skills.txt)")
    cur("missiles", "Missile", "Missile", "restructure", "row key: the 1.13c name of the missile in the same record (1.13c lower-cases and renames "
        "some, and keeps 1.09d's duplicate names apart); 1.09d's Id column restarts at 0 after record 384, so records pair by position")
    for c in ("Done", "What's left? - code", "What's Left - art", "effect", "leveleffect", "ClassReq", "Monster"):
        cur("skills", c, None, "drop", "comment/bookkeeping; no 1.13c column (ClassReq/Monster were editor flags)")
    cur("skills", "isaura", "aura", "rename", "")
    cur("skills", "leftskl", "leftskill", "rename", "")
    cur("skills", "SearchMonsterNear", "SearchEnemyNear", "rename", "")
    cur("skills", "SelectDead", "TargetCorpse", "rename", "best guess, unverified (all 0 in 1.09d)")
    cur("skills", "Shiver", None, "drop", "no 1.13c column; shiver behaviour is hardcoded/derived in 1.10+")
    cur("skills", "caster state", None, "drop", "empty in 1.09d")
    for i in range(1, 7):
        cur("skills", f"itemclass{i}", None, "drop",
            "1.09d weapon-class codes (bow, 1hs, !bw, xxx = none); 1.13c's itypea/b item types were rewritten per skill, so no value "
            "table exists: D2R's restrictions stay")
    for c in ("SkillPage", "SkillRow", "SkillColumn", "IconCel"):
        cur("skills", c, f"skilldesc.{c}", "moved", "row: skilldesc named by 1.13c's skills.skilldesc for the skill (else its name); a name an earlier skill took gets ' #<Id>'")
    cur("skills", "anim", ["anim", "*anim 1.09d"], "recode", "value_maps['skills.anim']: 1.09d mode words -> plrmode codes. Several words share a code "
        "(a1/attack, aura/none), so the 1.09d word also goes to the comment column")
    cur("skills", "monanim", ["monanim", "*monanim 1.09d"], "recode", "value_maps['skills.monanim']: 1.09d mode words -> monmode codes; a1/attack share A1, "
        "so the 1.09d word also goes to the comment column")
    for i in (1, 2, 3):
        cur("skills", f"State{i}", f"State{i}", "recode", "1.09d states row number (0 = none) -> states name")
    cur("skills", "skill", "skill", "recode", "row key: 1.13c's name of the same record (same Id). 1.10 renamed 311 inferno sentry -> "
        "mon inferno sentry and 312 death sentry -> mon death sentry, which differ from the assassin's Inferno/Death Sentry only "
        "in case; every reference to a skill (row number or name) takes the 1.13c name too")
    cur("skills", "reqskill1", "reqskill1", "recode", "same encoding (skill name), renamed as skills.skill")

    # monstats: graphics columns moved to monstats2, AI/element/resist renames, absolute stats kept as is
    ABS = ("1.09d absolute value, kept as is: D2R reads this column as a monlvl percent, so a port must apply it as an absolute value "
           "in its own monster-init code. A percent cannot hold it: monlvl bases exceed 100, so one percent step is more than one point")
    MS2 = {"SizeX": "SizeX", "SizeY": "SizeY", "Height": "Height", "OverlayHeight": "OverlayHeight", "MeleeRng": "MeleeRng",
           "BaseW": "BaseW", "HitClass": "HitClass", "TotalPieces": "TotalPieces", "PixHeight": "pixHeight",
           "NoMap": "noMap", "NoOverlays": "noOvly", "IsSel": "isSel", "IsSel2": "alSel", "NeverSel": "noSel",
           "CorpseSel": "corpseSel", "IsAtt": "isAtt", "IsCritter": "critter", "Bleed": "Bleed", "Shadow": "Shadow",
           "Light": "Light", "NoUniqueShift": "noUniqueShift", "CompositeDeath": "compositeDeath", "LightR": "light-r",
           "LightG": "light-g", "LightB": "light-b", "Soft": "soft", "Heart": "Heart", "BodyPart": "BodyPart",
           "Restore": "restore", "DeadCollision": "deadCol", "UnflatDead": "unflatDead", "BloodLocal": "localBlood",
           "NoGfxHitTest": "noGfxHitTest", "HitTestTop": "htTop", "HitTestLeft": "htLeft", "HitTestWidth": "htWidth",
           "HitTestHeight": "htHeight", "AutomapCel": "automapCel", "ObjectCollision": "objCol", "Inert": "inert",
           "eSpawnCol": "spawnCol", "eLarge": "large", "eSmall": "small"}
    for p in "HD TR LG RA LA RH LH SH S1 S2 S3 S4 S5 S6 S7 S8".split(): MS2[p] = p
    for m, c in zip("DH N W GH A1 A2 B C S1 S2 S3 S4 DD KB SQ RN".split(), "DT NU WL GH A1 A2 BL SC S1 S2 S3 S4 DD KB SQ RN".split()):
        MS2[f"Mode{m}"] = f"m{c}"
    for m, c in (("A1Move", "A1mv"), ("A2Move", "A2mv"), ("S1Move", "S1mv"), ("S2Move", "S2mv"), ("S3Move", "S3mv"), ("S4Move", "S4mv"), ("Cmove", "SCmv")):
        MS2[m] = c
    for k, v in MS2.items(): cur("monstats", k, f"monstats2.{v}", "moved", "row: monstats2 named by monstats.MonStatsEx (= monstats Id)")
    cur("monstats", "Class", "NameStr", "rename", "1.09d display name; 1.13c NameStr is a string-table key (values match 99.6%)")
    cur("monstats", "Descriptor", "DescStr", "rename", "")
    cur("monstats", "Type", None, "drop", "comment: 1.09d's monstats loader (D2Common 0x6fd5ad40) has no Type field (Class, Descriptor, BaseId, ...)")
    cur("monstats", "BaseId", ["AI", "*BaseId 1.09d"], "recode",
        "NOT a monstats row: 1.09d has no AI column, BaseId is the index of the monster's record in D2Game's AI table (266 records, 0-265). "
        "recode: BaseId -> D2R's AI name through data/109d-monster-ai.tsv (that table paired with D2R's, gen_109d_monster_ai.py). Several BaseIds "
        "share one D2R AI, so the 1.09d value also goes to the comment column. 1.13c's own BaseId column (a monster id) gets nothing")
    cur("monstats", "PopulateId", None, "drop", "1.09d row index of the populate chain; 1.13c uses NextInClass/hcIdx")
    cur("monstats", "namco", None, "drop", "comment")
    for c in ("Spawned", "Beta", "ClientOnly", "CanStealFrom", "SpawnComponents", "Switch"):
        cur("monstats", c, None, "drop", "no 1.13c column")
    cur("monstats", "IsNPC", "npc", "rename", "")
    cur("monstats", "DeathDamage", "deathDmg", "rename", "")
    for a, b in (("eLUndead", "lUndead"), ("eHUndead", "hUndead"), ("eDemon", "demon"), ("eFlying", "flying"),
                 ("eOpenDoors", "opendoors"), ("eBoss", "boss")):
        cur("monstats", a, b, "rename", "")
    cur("monstats", "eMagicUsing", None, "drop", "no 1.13c column")
    AIP = [f"aip{i}{d}" for i in range(1, 6) for d in ("", "(N)", "(H)")]
    cur("monstats", "AIParam1", AIP + ["*AIParam 1.09d"], "recode",
        "WHOLE ROW (reads AIParam1-5 and BaseId): 1.10 moved the AI parameter slots, so a plain copy is wrong (a Skeleton's attack chance is "
        "AIParam2 in 1.09d and aip3 in D2R). For an AI with a verified slot map (data/109d-monster-ai.tsv, param_slots) each 1.09d slot goes to "
        "its D2R slot, on all three difficulties; a slot with no D2R home goes to the comment column and the other D2R slots stay blank (D2R keeps "
        "its own). An AI with no verified map keeps the plain copy (AIParamN -> aipN, aipN(N), aipN(H)) and is listed unverified in the table")
    for i in range(2, 6):
        cur("monstats", f"AIParam{i}", None, "recode", "no target of its own: read by the AIParam1 whole-row recode, put back from the aip cells and the comment column")
    cur("monstats", "Comment", None, "drop", "comment (5 duplicate columns)")
    for i in range(1, 6):
        cur("monstats", f"Skill{i}", f"Skill{i}", "recode", "1.09d skills row number -> skills name")
        cur("monstats", f"Skill{i}Seq", [f"Sk{i}mode", f"*Skill{i}Seq 1.09d"], "recode", "value_maps['monstats.SkillSeq'] (all 5 slots pooled): 1.09d hardcoded sequence "
            "number -> monmode code or monseq sequence name, the most common pair; incomplete, so the number also goes to the comment column")
        cur("monstats", f"Skill{i}Lvl", f"Sk{i}lvl", "rename", "")
    for m in "A1 A2 S1 S2 S3 S4 C SQ".split():
        cur("monstats", f"Miss{m}", [f"Miss{m}", "*invalid refs 1.09d"], "recode", "1.09d missiles row number (65535 = none) -> missiles name "
            "(blank = none). A number past the last missile (one cell: VH MissA1 65536, a dword, so no missile) is blank too, and goes to the comment column")
    for e, n in (("Damage", "Dm"), ("Magic", "Ma"), ("Fire", "Fi"), ("Light", "Li"), ("Cold", "Co"), ("Poison", "Po")):
        for d in ("", "(N)", "(H)"):
            cur("monstats", f"{e}Resist{d}", f"Res{n}{d}", "rename", "")
    for a in ("A1", "A2", "S1"):
        for d in ("", "(N)", "(H)"):
            cur("monstats", f"{a}ToHit{d}", f"{a}TH{d}", "rename", ABS)
    for c in ("ElMode", "ElType"):
        cur("monstats", c, c.replace("El", "El1"), "rename", "1.13c has 3 element slots; 1.09d's one goes in slot 1")
    for c in ("ElPct", "ElMinD", "ElMaxD", "ElDur"):
        n = c.replace("El", "El1"); cur("monstats", c, [n, f"{n}(N)", f"{n}(H)"], "split", "1.09d single value for all difficulties: copy")
    cur("monstats", "ElOver", None, "drop", "element overlay; no 1.13c column")
    for c in ("MinHP", "MaxHP", "AC", "Exp", "A1MinD", "A1MaxD", "A2MinD", "A2MaxD", "S1MinD", "S1MaxD"):
        for d in ("", "(N)", "(H)"):
            tgt = {"MinHP": "minHP", "MaxHP": "maxHP"}.get(c, c) if d == "" else c
            cur("monstats", f"{c}{d}", f"{tgt}{d}", "same" if tgt == c + d else "rename", ABS)
    cur("monstats", "SpawnPctBonus", None, "drop", "no 1.13c column")
    cur("monstats", "ToBlock", ["ToBlock", "ToBlock(N)", "ToBlock(H)"], "split", "copy per difficulty")

    # montype: same file name, unrelated content
    for c in "DT NU WL GH A1 A2 BL SC S1 S2 S3 S4 DD KB SQ RN".split():
        cur("montype", f"{c}_Dir", f"monstats2.d{c}", "moved", "1.09d montype.txt is a per-monster direction table (row = monstats row); 1.13c montype.txt is a type hierarchy")
    cur("montype", "Name", None, "drop", "row label (= monstats Class)"); cur("montype", "Token", None, "drop", "= monstats Code")

    # levels
    for i in range(1, 26):
        cur("levels", f"M{i}", [f"mon{i}", f"nmon{i}", "*unused M 1.09d"] if i <= 10 else [], "recode" if i <= 10 else "drop",
            "1.09d monstats row number -> monstats Id; 1.09d has one list, so nmon (NM/Hell list) gets a copy; M11-25 unused (max Mtot 8). "
            "A slot past Mtot is left blank and its 1.09d value goes to the comment column (one cell: Mephisto 3 M3; assumed unused, unverified)")
        cur("levels", f"U{i}", f"umon{i}" if i <= 10 else None, "recode" if i <= 10 else "drop", "monstats row number -> Id; U11-25 unused")
        cur("levels", f"S{i}", None, "drop", "1.09d 'spawned' list, 3 non-zero cells in the whole file; no 1.13c column")
    for i in range(1, 6):
        for a, b in (("C", "cmon"), ("CA", "cpct"), ("CD", "camt")):
            cur("levels", f"{a}{i}", f"{b}{i}" if i <= 4 else None, ("recode" if a == "C" else "rename") if i <= 4 else "drop",
                ("critter monstats row number -> Id" if a == "C" else "") + ("; slot 5 unused in 1.09d" if i == 5 else ""))
    cur("levels", "Mtot", None, "drop", "count of M columns; 1.13c NumMon is a different setting (how many types spawn)")
    cur("levels", "Utot", None, "drop", "count of U columns")
    for c in ("SizeX", "SizeY", "MonDen", "MonUMin", "MonUMax"):
        cur("levels", c, [c, f"{c}(N)", f"{c}(H)"], "split", "1.10 made these per difficulty: copy")

    # items
    for t in ("armor", "weapons", "misc"):
        cur(t, "sound", ["dropsound", "usesound"], "recode", f"value_maps['{t}.sound']: 1.09d item sound-class number -> sounds name")
    cur("misc", "namco", "*name", "rename", "comment column")
    cur("uniqueitems", "name", "index", "rename", "row key")
    cur("uniqueitems", "completed", "enabled", "rename", "")
    cur("uniqueitems", "beta", None, "drop", "")
    cur("uniqueitems", "Level", "lvl", "rename", ""); cur("uniqueitems", "LevelReq", "lvl req", "rename", "")
    cur("uniqueitems", "type", "*type", "rename", "comment column")
    cur("uniqueitems", "transform", None, "recode", "flag; folded into chrtransform (blank when 0)")
    cur("uniqueitems", "transformcolor", "chrtransform", "recode", "colors.txt row number -> colors code (value_maps['colors'])")
    cur("uniqueitems", "invtransform", "invtransform", "recode", "0/1 flag -> colors code (same as chrtransform when 1)")
    for i in range(1, 11):
        for a, b in (("Code", "prop"), ("Param", "par"), ("Min", "min"), ("Max", "max")):
            cur("uniqueitems", f"ItemMod{i}{a}", f"{b}{i}", "rename", "")
    cur("uniqueitems", "End", "*eol", "rename", "")
    cur("setitems", "*", None, "restructure",
        "1.09d: one row per SET with Item1-6 blocks. 1.13c: sets.txt (one row per set: name, version, level, PCode2a-5b, FCode1-8) + setitems.txt (one row per item: index=ItemN Suffix, set=Name, item=ItemN, rarity, lvl, lvl req, cost mult/add, add func=ItemN Add, prop1-2 <- INCode1-2, aprop1a-5a <- INCodeA-E). PCodeN -> sets PCodeNa; FCodeN -> sets FCodeN.")
    RS = "restructure"
    cur("setitems", "Name", ["sets.name", "set"], RS, "set name -> sets row key and every item row's set")
    cur("setitems", "version", "sets.version", RS, ""); cur("setitems", "level", ["sets.level", "lvl"], RS, "set level; items take it as lvl")
    cur("setitems", "NumItems", None, "drop", "derived (count of item blocks)")
    cur("setitems", "transform", None, RS, "flag; folded into chrtransform")
    cur("setitems", "transformcolor", "chrtransform", RS, "colors row number -> colors code, on every item row of the set")
    for n in range(1, 7):
        for a, b in (("", "item"), (" Suffix", "index"), (" Rarity", "rarity"), (" Add", "add func"), (" Lvlreq", "lvl req"),
                     (" LvlReq", "lvl req"), (" cost mult", "cost mult"), (" cost add", "cost add")):
            if f"Item{n}{a}" in load("y109", "setitems")[0]: cur("setitems", f"Item{n}{a}", b, RS, f"item {n}'s own setitems row")
        for i, (a, b) in enumerate((("Code", "prop"), ("Param", "par"), ("Min", "min"), ("Max", "max"))):
            for k in (1, 2): cur("setitems", f"I{n}{a}{k}", f"{b}{k}", RS, f"item {n}'s row; always-on property")
            for j, L in enumerate("ABCDE", 1):
                cur("setitems", f"I{n}{a}{L}", f"a{b}{j}a", RS, f"item {n}'s row; add func 2: bonus with {j + 1} set items worn; add func 1: with the set's other item {j} (in set order) "
                    "(1.09d D2Common 0x6fd97030, D2R 0x1403d62c0 and 0x1403d3670)")
    for k in range(2, 6):
        for a in ("Code", "Param", "Min", "Max"): cur("setitems", f"P{a}{k}", f"sets.P{a}{k}a", RS, f"partial set bonus at {k} items")
    for k in range(1, 7):
        for a in ("Code", "Param", "Min", "Max"): cur("setitems", f"F{a}{k}", f"sets.F{a}{k}", RS, "full set bonus")
    cur("books", "SpellOffset", "pSpell", "rename", "1.09d values are 0 (function hardcoded): take 1.13c's")
    cur("books", "SkillScrollOffset", "ScrollSkill", "rename", "1.09d 0 -> 1.13c skill name; take 1.13c's")
    cur("books", "SkillBookOffset", "BookSkill", "rename", "as ScrollSkill")
    cur("hireling", "*", None, "restructure", "1.13c doubles the rows: Version 0 (classic) and Version 100 (expansion). 1.09d's 60 rows are one set; they become the Version 100 rows (and Version 0 if classic is kept)")
    for i in range(1, 7): cur("hireling", f"ChancePerLevel{i}", f"ChancePerLvl{i}", "rename", "")
    cur("inventory", "gridRows", "gridX", "rename", "values identical (1.09d header was mislabelled)")
    cur("inventory", "gridCols", "gridY", "rename", "values identical")
    cur("itemstatcost", "Stat", "Stat", "recode", "row key: STATS_FOO -> foo; rows match by ID; several 1.09d multi-slot stats (class skill points 83-87/179-180, SINGLESKILL1-3, SKILLONATTACK1-3 ..., CHARGED_SKILL0-9) collapse into one 1.13c stat + param")
    cur("itemstatcost", "Save Bits", ["1.09-Save Bits"], "rename", "1.13c keeps 1.09's item save layout in '1.09-Save Bits' (identical values by ID); its own 'Save Bits' differs for some stats")
    cur("itemstatcost", "Save Add", ["1.09-Save Add"], "rename", "as Save Bits")
    cur("itemstatcost", "Percent", "op", "recode", "Percent=1 -> op 13 (percent of op stat1)")
    cur("itemstatcost", "Target Stat", "op stat1", "recode", "1.09d stat ID (-1 none) -> stat name")
    cur("itemstatcost", "PerLevel", "op", "recode", "PerLevel=1 -> op 2 (value * clvl >> op param)")
    cur("itemstatcost", "PerLevelShift", "op param", "rename", "")
    cur("itemstatcost", "ByTime", "op", "recode", "ByTime=1 -> op 6 (by time of day)")
    cur("itemstatcost", "ItemSpecific", "itemspecific", "rename", "case")
    for c, d in (("Done", "*done"), ("Description", "*desc"), ("Param", "*param"), ("Min", "*min"), ("Max", "*max"), ("Additional Notes", "*notes")):
        cur("properties", c, d, "rename", "comment column")
    cur("properties", "ModFuncOffset", None, "drop", "comment column: 1.09d's properties loader (D2Common 0x6fd482c0, field table "
        "{'code', type 0x10} then 'end' at 0x6fdc5404) reads only 'code', and the names in this column (ARMORCLASS, "
        "FASTESTATTACKRATE...) are in none of D2Common, D2Game or Fog. 1.09d binds each property to a function in code; "
        "D2R's func1-7/stat1-7 for the code stay, not compared")
    cur("sounds", "Handle", "Sound", "recode", "row key: ESOUND_FOO -> foo")
    cur("states", "state", "state", "recode", "row key: STATE_FOO -> foo; every other states column is new (hardcoded in 1.09d)")
    cur("superuniques", "Class", "Class", "recode", "1.09d monstats row number -> monstats Id")
    cur("treasureclassex", "SumDrop", None, "drop", "spreadsheet calc column"); cur("treasureclassex", "Better", None, "drop", "spreadsheet calc column")
    cur("cubemain", "start day", None, "drop", "unused date gate"); cur("cubemain", "stop day", None, "drop", "unused date gate")
    cur("cubemain", "weekday", None, "drop", "unused date gate"); cur("cubemain", "term", "*eol", "rename", "")
    cur("difficultylevels", "ExtraUniqueMonsters", None, "drop", "1.09d only; no 1.13c column")
    cur("charstats", "StartSkill", "StartSkill", "recode", "1.09d skills row number (0 = none) -> skill name")
    cur("monmode", "Name", "name", "rename", "case"); cur("overlay", "Overlay", "overlay", "rename", "case/row key style changed")
    for t in ("uniqueappellation", "uniqueprefix", "uniquesuffix", "uniquetitle"):
        for i in range(1, 37): cur(t, f"MonType{i}", None, "drop", "1.09d restricted name parts to monster types; 1.13c has no restriction")

    # value maps derived from row pairs (1.09d value -> most common 1.13c value)
    def vmap(t, a, b, key=None, more=()):  # more: further (1.09d, 1.13c) column pairs pooled into the same map
        h1, r1 = load("y109", t); h2, r2 = load("y113", t); c = defaultdict(Counter)
        if key:
            k2 = {r[h2.index(key[1])].lower(): r for r in r2}
            pairs = [(r, k2.get(r[h1.index(key[0])].lower())) for r in r1]
        else:
            pairs = list(zip(r1, r2))
        for x, y in pairs:
            if y is None: continue
            for a1, b1 in ((a, b), *more):
                va = x[h1.index(a1)] if h1.index(a1) < len(x) else ""; vb = y[h2.index(b1)] if h2.index(b1) < len(y) else ""
                c[va][vb] += 1
        return {k: {"to": v.most_common(1)[0][0], "agree": round(v.most_common(1)[0][1] / sum(v.values()), 2), "n": sum(v.values())} for k, v in sorted(c.items())}
    VM = {"skills.anim": vmap("skills", "anim", "anim", ("skill", "skill")),
          "skills.monanim": vmap("skills", "monanim", "monanim", ("skill", "skill")),
          "monstats.SkillSeq": vmap("monstats", "Skill1Seq", "Sk1mode", more=[(f"Skill{i}Seq", f"Sk{i}mode") for i in range(2, 6)]),
          **{f"{t}.sound": vmap(t, "sound", "dropsound", ("code", "code")) for t in ("armor", "weapons", "misc")}}
    hc, rc = load("y113", "colors"); VM["colors"] = {str(i): r[hc.index("Code")] if "Code" in hc else r for i, r in enumerate(rc)}

    tables, tsv = {}, ["table\tcolumn_109d\ttable_113c\tcolumn_113c\tkind\ttransform"]
    for t in sorted(set(T109) | set(T113)):
        a, b = load("y109", t), load("y113", t)
        e = {"in": [v for v, x in (("1.09d", a), ("1.13c", b)) if x], "rows": {v: count(EX[k].get(f"{t}.bin")) for v, k in (("1.09d", "y109"), ("1.13c", "y113"))}}
        if a and b:
            h1, h2 = a[0], b[0]; lo2 = {x.lower(): x for x in h2}; cols = {}
            for col in dict.fromkeys(h1):
                if not col: continue
                if col in R[t]: to, kind, tr = R[t][col]
                elif col in h2: to, kind, tr = [col], "same", ""
                elif col.lower() in lo2: to, kind, tr = [lo2[col.lower()]], "rename", "case only"
                else: to, kind, tr = [], "unmapped", "REVIEW: no rule"
                cols[col] = {"to": to, "kind": kind, **({"transform": tr} if tr else {})}
                for x in (to or [""]):
                    tt, cc = (x.split(".", 1) if "." in x and x.split(".", 1)[0] in T113 else (t if x else "", x))
                    tsv.append(f"{t}\t{col}\t{tt}\t{cc}\t{kind}\t{tr}")
            if "*" in R[t]:
                e["restructure"] = R[t]["*"][2]; tsv.append(f"{t}\t*\t{t}\t*\trestructure\t{R[t]['*'][2]}")
            fed = {x for c in cols.values() for x in c["to"] if "." not in x}
            e["new_in_113c"] = [c for c in h2 if c and c not in fed]
            e["columns"] = cols
        tables[t] = e
    for t, col in [(t, c) for t in R for c in R[t]]:
        assert t in tables and (col == "*" or col in tables[t].get("columns", {})), (t, col)  # every curated rule names a real 1.09d column
    doc = {"about": "1.09d -> 1.13c excel column map, generated by shared/classic_import/gen_109d_map.py. 'to' entries 't.c' live in another 1.13c table.",
           "sources": {"1.09d": "a 1.09d install checked against baselines/109d.json: Patch_D2.mpq > d2exp.mpq > d2data.mpq",
                       "1.13c": "1.13c's Patch_D2.mpq (SHA-256 pinned in gen_109d_map.py) > 1.09d's d2exp.mpq > d2data.mpq (1.13c's base MPQs are 1.09d's, byte for byte). automagic, rareprefix and raresuffix: 1.13c ships only .bin, compiled from the d2exp.mpq .txt (checked record by record; 1.10 only widened the item-type slots)"},
           "tables": tables, "value_maps": VM}
    return doc, "\n".join(tsv) + "\n"


def inputs(install: str | None, patch_113c: str | None) -> tuple[Path, Path]:
    """The two game inputs from arguments or the environment."""
    install = install or os.environ.get("D2_109D_INSTALL")
    patch_113c = patch_113c or os.environ.get("D2_113C_PATCH")
    if not install or not patch_113c:
        raise GenError("needs --install <1.09d folder> and --patch-113c <1.13c Patch_D2.mpq> (or D2_109D_INSTALL and D2_113C_PATCH)")
    return Path(install), Path(patch_113c)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--install", help="the 1.09d folder (or D2_109D_INSTALL)")
    ap.add_argument("--patch-113c", help="1.13c's Patch_D2.mpq (or D2_113C_PATCH)")
    ap.add_argument("--out", type=Path, help="write the map here instead of data/")
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if the committed map differs")
    args = ap.parse_args(argv)
    try:
        doc, tsv = build(extract(*inputs(args.install, args.patch_113c)))
    except GenError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    text = json.dumps(doc, indent=1) + "\n"
    cols = [v for e in doc["tables"].values() for v in e.get("columns", {}).values()]
    un = [(t, c) for t, e in doc["tables"].items() for c, v in e.get("columns", {}).items() if v["kind"] == "unmapped"]
    print("tables", len(doc["tables"]), "tsv rows", tsv.count("\n") - 1, "unmapped", un)
    print(Counter(v["kind"] for v in cols))
    if args.check:
        same = (JSON_OUT.read_text(encoding="utf-8") == text and TSV_OUT.read_text(encoding="utf-8") == tsv)
        print("committed map is current" if same else "committed map differs")
        return 0 if same else 1
    json_out, tsv_out = (args.out / JSON_OUT.name, args.out / TSV_OUT.name) if args.out else (JSON_OUT, TSV_OUT)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(text, encoding="utf-8", newline="\n")
    tsv_out.write_text(tsv, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
