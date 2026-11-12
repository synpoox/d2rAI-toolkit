"""Tests for shared/classic_import/hd_entries.py on synthetic tables (no game data)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.classic_import import hd_entries as H  # noqa: E402
from shared.classic_import.ids import Table  # noqa: E402


def table(text: str) -> Table:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "t.txt"
        p.write_bytes(text.replace("|", "\t").encode("latin-1"))
        return Table(p)


def write_excel(root: Path, name: str, text: str) -> None:
    (root / "global" / "excel").mkdir(parents=True, exist_ok=True)
    (root / "global" / "excel" / name).write_bytes(text.replace("|", "\t").encode("latin-1"))


# --- missiles ---

M_D2R = "Missile|CelFile\r\nthrowaxe|MissileHandAxe\r\nancient throwing axe|MissileHandAxe\r\nbighead1|BigHead\r\n" \
        "shock field on ground|Expansion\\ShockField\r\n"
M_MODELS = {"dependencies": {}, "throwaxe": "missile_hand_axe", "ancient_throwing_axe": "missile_hand_axe",
            "bighead_1": "bighead_lightning_missile", "shock_field_on_ground": "expansion_shock_field"}
# D2R's rows, then the source's: a CelFile match (folder prefix differs), source-only art, a name D2R would underscore
M_SRC = M_D2R + "splitthrowaxe|MissileHandAxe\r\nsrcChargedGround|expansion\\shockfield\r\nalphabolts|AlphaBolt\r\n" \
                "betablizz1|betablizz\r\nA3 Merc fireball|BigHead\r\n"
M_LIKES = {"alphabolts": "bighead1", "betablizz1": "shock field on ground"}


class MissileEntriesTests(unittest.TestCase):
    def test_celfile_match_and_lines(self):
        self.assertEqual(H.missile_entries(table(M_SRC), table(M_D2R), M_MODELS, M_LIKES), {
            "splitthrowaxe": "missile_hand_axe", "srcchargedground": "expansion_shock_field",
            "srcChargedGround": "expansion_shock_field",  # capitals: both spellings (JSON keys are case-sensitive)
            "a_3_merc_fireball": "bighead_lightning_missile", "A_3_Merc_fireball": "bighead_lightning_missile",
            "alphabolts": "bighead_lightning_missile", "betablizz_1": "expansion_shock_field"})

    def test_missile_key(self):
        self.assertEqual(H.missile_key("bighead1"), "bighead_1")
        self.assertEqual(H.missile_key("Bomb In Air"), "bomb_in_air")
        self.assertEqual(H.missile_key("Zap1", lower=False), "Zap_1")

    def test_refusals(self):
        cases = [
            ({"alphabolts": "bighead1"}, r"no HD model for 1 new missiles.*betablizz1 \(betablizz\)"),
            (M_LIKES | {"splitthrowaxe": "bighead1"}, "'splitthrowaxe' has a CelFile match"),
            (M_LIKES | {"throwaxe": "bighead1"}, "not new: throwaxe"),
            (M_LIKES | {"alphabolts": "nope"}, "'nope' has no missiles.json entry"),
        ]
        for likes, msg in cases:
            with self.subTest(msg), self.assertRaisesRegex(H.MissileHdError, msg):
                H.missile_entries(table(M_SRC), table(M_D2R), M_MODELS, likes)
        with self.assertRaisesRegex(H.MissileHdError, "already has 'bighead_1'"):
            H.missile_entries(table(M_D2R + "bighead_1|BigHead\r\n"), table(M_D2R), M_MODELS, {})
        with self.assertRaisesRegex(H.MissileHdError, "already has 'Zap_1'"):  # the own-spelling key is checked too
            H.missile_entries(table(M_D2R + "Zap1|BigHead\r\n"), table(M_D2R), M_MODELS | {"Zap_1": "x"}, {})


class MissileRuleTests(unittest.TestCase):
    def test_rule_writes_d2r_map_plus_new_missiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            d2r, out, src = Path(tmp) / "d2r", Path(tmp) / "out", Path(tmp) / "src"
            rule = Path(tmp) / "missiles-hd.tsv"
            write_excel(d2r, "missiles.txt", M_D2R)
            write_excel(out, "missiles.txt", M_SRC)
            (d2r / H.HD_MISSILES).parent.mkdir(parents=True)
            (d2r / H.HD_MISSILES).write_text(json.dumps(M_MODELS), "utf-8")
            rule.write_text("# missile\tlike\nalphabolts\tbighead1\nbetablizz1\tshock field on ground\n", "utf-8")
            sprites = src / "global" / "missiles"
            sprites.mkdir(parents=True)
            (sprites / "betablizz.dcc").write_bytes(b"dcc")
            (sprites / "unused.dcc").write_bytes(b"x")
            H.apply_missiles(rule, src, d2r, out)
            written = json.loads((out / H.HD_MISSILES).read_text("utf-8"))
            # legacy mode: the source's own DCC for a row that uses it, nothing else
            self.assertEqual([p.name for p in (out / "global" / "missiles").iterdir()], ["betablizz.dcc"])
            self.assertEqual((out / "global" / "missiles" / "betablizz.dcc").read_bytes(), b"dcc")
        self.assertEqual(list(written)[:len(M_MODELS)], list(M_MODELS))  # D2R's entries first
        self.assertEqual(written["splitthrowaxe"], "missile_hand_axe")
        self.assertEqual(len(written), len(M_MODELS) + 7)


# --- monsters ---

N_D2R = "Id|BaseId|Code\r\nskeleton1|skeleton1|SK\r\nsk_archer1|sk_archer1|SK\r\nsk_archer2|sk_archer1|SK\r\n" \
        "baalclone|baalclone|BA\r\nfamiliar|familiar|FI\r\nExpansion||\r\n"
N_MODELS = {"skeleton1": "skeleton1", "sk_archer1": "sk_archer1", "sk_archer2": "sk_archer1", "baalclone": "baal"}
# D2R's rows, then the source's: a clone (mixed-case Id, lower-case Code) drawn as its BaseId, not as the Code's most
# common model; a new base drawn as its Code's; a BaseId with other art drawn as its own Code's; source-only codes
N_SRC = N_D2R + "skeletonIce|skeleton1|sk\r\nnecroarcher|necroarcher|SK\r\nshadow|skeleton1|BA\r\n" \
                "AlphaTheMad|summoner|$4\r\nBeta|beta|!8\r\nbonemage|bonemage|SK\r\n"
N_LIKES = {"alphathemad": "baalclone", "beta": "skeleton1", "bonemage": "skeleton1"}
N_RULE = "# monster\tlike\nAlphaTheMad\tbaalclone\nbeta\tskeleton1\nbonemage\tskeleton1\n"


class MonsterEntriesTests(unittest.TestCase):
    def test_baseid_code_and_lines(self):
        self.assertEqual(H.monster_entries(table(N_SRC), table(N_D2R), N_MODELS, N_LIKES), {
            "skeletonIce": "skeleton1", "necroarcher": "sk_archer1", "shadow": "baal", "AlphaTheMad": "baal",
            "Beta": "skeleton1", "bonemage": "skeleton1"})  # D2R's lookup is case-sensitive: the source's spelling

    def test_refusals(self):
        cases = [
            ({"alphathemad": "baalclone", "bonemage": "skeleton1"}, r"no HD model for 1 new monsters.*Beta \(!8\)"),
            (N_LIKES | {"skeletonice": "skeleton1"}, "'skeletonIce' gets skeleton1 anyway"),
            (N_LIKES | {"necroarcher": "sk_archer2"}, "'necroarcher' gets sk_archer1 anyway"),
            (N_LIKES | {"skeleton1": "baalclone"}, "not new: skeleton1"),
            (N_LIKES | {"beta": "nope"}, "'nope' has no monsters.json entry"),
        ]
        for likes, msg in cases:
            with self.subTest(msg), self.assertRaisesRegex(H.MonsterHdError, msg):
                H.monster_entries(table(N_SRC), table(N_D2R), N_MODELS, likes)
        with self.assertRaisesRegex(H.MonsterHdError, "already has 'skeleton2'"):
            H.monster_entries(table(N_D2R + "skeleton2|skeleton1|SK\r\n"), table(N_D2R),
                              N_MODELS | {"skeleton2": "skeleton1"}, {})

    def test_tie_needs_a_line(self):
        d2r = N_D2R + "colossal1|colossal1|0D\r\nancientbarb1|ancientbarb1|0D\r\n"
        models = N_MODELS | {"colossal1": "colossal1", "ancientbarb1": "ancientbarb1"}
        src = d2r + "ancientbarbboss1|ancientbarbboss1|0D\r\n"
        with self.assertRaisesRegex(H.MonsterHdError, r"ancientbarbboss1 \(0D, tie: colossal1 or ancientbarb1\)"):
            H.monster_entries(table(src), table(d2r), models, {})
        self.assertEqual(H.monster_entries(table(src), table(d2r), models, {"ancientbarbboss1": "ancientbarb1"}),
                         {"ancientbarbboss1": "ancientbarb1"})


class MonsterRuleTests(unittest.TestCase):
    def test_rule_writes_d2r_map_plus_new_monsters(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, d2r, out, rule = (Path(tmp) / n for n in ("src", "d2r", "out", "monsters-hd.tsv"))
            write_excel(d2r, "monstats.txt", N_D2R)
            write_excel(src, "monstats.txt", N_SRC)
            (d2r / H.HD_MONSTERS).parent.mkdir(parents=True)
            (d2r / H.HD_MONSTERS).write_text(json.dumps(N_MODELS), "utf-8")
            rule.write_text(N_RULE, "utf-8")
            H.apply_monsters(rule, src, d2r, out)
            written = json.loads((out / H.HD_MONSTERS).read_text("utf-8"))
        self.assertEqual(list(written)[:len(N_MODELS)], list(N_MODELS))  # D2R's entries first
        self.assertEqual(written["skeletonIce"], "skeleton1")
        self.assertNotIn("skeletonice", written)
        self.assertEqual(len(written), len(N_MODELS) + 6)


# --- objects ---

O_D2R = "Class\tName\r\nPortalPermanent\tPortal\r\n"
O_PERMANENT = '{"dependencies": {"particles": [{"path": "red.particles"}]}, "vfx": "red.particles"}'


def run_objects(rule: str, merged: str) -> Path:
    tmp = Path(tempfile.mkdtemp())
    d2r, out = tmp / "d2r", tmp / "out"
    for root, text in ((d2r, O_D2R), (out, merged)):
        (root / "global" / "excel").mkdir(parents=True)
        (root / "global" / "excel" / "objects.txt").write_text(text, "latin-1")
    (d2r / "hd" / "objects" / "vfx_only").mkdir(parents=True)
    (d2r / "hd" / "objects" / "objects.json").write_text('{"portal_permanent": {"asset_path": "vfx_only"}}')
    (d2r / "hd" / "objects" / "vfx_only" / "portal_permanent.json").write_text(O_PERMANENT)
    (tmp / "rule.tsv").write_text(rule)
    H.apply_objects(tmp / "rule.tsv", tmp, d2r, out)
    return out / "hd" / "objects"


class ObjectTests(unittest.TestCase):
    def test_new_object_copies_like(self):
        hd = run_objects("# class\tlike\nsrcportal_grey\tportal_permanent\n",
                         O_D2R + "srcportal_grey\tsrcportal_grey\r\n")
        self.assertEqual(json.loads((hd / "objects.json").read_text())["srcportal_grey"], {"asset_path": "vfx_only"})
        self.assertEqual((hd / "vfx_only" / "srcportal_grey.json").read_text(), O_PERMANENT)

    def test_particles_column_swaps_the_effect(self):
        hd = run_objects("srcportal_gold\tportal_permanent\tgold.particles\n", O_D2R + "srcportal_gold\tx\r\n")
        self.assertEqual((hd / "vfx_only" / "srcportal_gold.json").read_text(), O_PERMANENT.replace("red", "gold"))

    def test_camel_class_gets_d2r_key(self):
        hd = run_objects("AlphaChest\tportal_permanent\n", O_D2R + "AlphaChest\tAlphaChest\r\n")
        self.assertEqual(json.loads((hd / "objects.json").read_text())["alpha_chest"], {"asset_path": "vfx_only"})
        self.assertTrue((hd / "vfx_only" / "alpha_chest.json").is_file())
        self.assertEqual([H.object_key(c) for c in ("PortalPermanent", "Chest1B", "TownAct3GidBInnAltar",
                                                    "SpecialChest100")],
                         ["portal_permanent", "chest_1_b", "town_act_3_gid_b_inn_altar", "special_chest_100"])

    def test_bad_lines_fail(self):
        with self.assertRaisesRegex(H.ObjectHdError, "not a source-only"):
            run_objects("PortalPermanent\tportal_permanent\n", O_D2R)
        with self.assertRaisesRegex(H.ObjectHdError, "no D2R object json"):
            run_objects("xsrc\tnope\n", O_D2R + "xsrc\txsrc\r\n")
        with self.assertRaisesRegex(H.ObjectHdError, "line 1: want"):
            run_objects("onlyone\n", O_D2R)


# --- overlays ---

V_D2R = "overlay|Filename|Character\r\nbattleorders|BattleOrders|common\r\nteleport|Teleport|sorceress\r\n"
# the merged table: D2R's rows, then the source's appended ones with the blank Character the table merge leaves them
V_MERGED = V_D2R + "teleport_debuff|teleport_debuff|\r\nAlphaEvent|Extra\\GolemCast|\r\nsrc_t8_aura|aurared|\r\n"
V_RULE = "# overlay\tlike\nteleport_debuff\tteleport\nalphaevent\tbattleorders\nsrc_t8_aura\tbattleorders\n"


def setup_overlays(tmp: Path, rule: str = V_RULE) -> tuple[Path, Path, Path]:
    d2r, out, path = tmp / "d2r", tmp / "out", tmp / "vfx-overlays.tsv"
    for root, text in ((d2r, V_D2R), (out, V_MERGED)):
        write_excel(root, "overlay.txt", text)
    for folder, name in (("common", "battleorders"), ("sorceress", "teleport")):
        (d2r / H.HD_OVERLAYS / folder).mkdir(parents=True, exist_ok=True)
        (d2r / H.HD_OVERLAYS / folder / f"{name}.json").write_text(
            json.dumps({"type": "OverlayDefinition", "name": name}))
    path.write_text(rule, "utf-8")
    return d2r, out, path


class OverlayTests(unittest.TestCase):
    def test_new_rows_get_the_like_folder_and_a_copied_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            d2r, out, rule = setup_overlays(Path(tmp))
            H.apply_overlays(rule, Path(tmp) / "src", d2r, out)
            rows = (out / "global" / "excel" / "overlay.txt").read_text("latin-1").splitlines()
            self.assertEqual(rows[3:], ["teleport_debuff\tteleport_debuff\tsorceress",
                                        "AlphaEvent\tExtra\\GolemCast\tcommon", "src_t8_aura\taurared\tcommon"])
            self.assertEqual(rows[:3], V_D2R.replace("|", "\t").splitlines())  # D2R's rows untouched
            # the file name keeps the source's spelling (JSON keys and names are case-sensitive)
            copied = json.loads((out / H.HD_OVERLAYS / "common" / "AlphaEvent.json").read_text("utf-8"))
            self.assertEqual(copied, {"type": "OverlayDefinition", "name": "AlphaEvent"})
            self.assertTrue((out / H.HD_OVERLAYS / "sorceress" / "teleport_debuff.json").is_file())
            # D2R's file name splits a letter from a digit (its own doubledamage1 is doubledamage_1.json)
            copied = json.loads((out / H.HD_OVERLAYS / "common" / "src_t_8_aura.json").read_text("utf-8"))
            self.assertEqual(copied["name"], "src_t_8_aura")

    def test_refusals(self):
        cases = [
            ("# x\nteleport_debuff\tteleport\nsrc_t8_aura\tteleport\n",
             r"no HD overlay for 1 new overlays.*AlphaEvent"),
            (V_RULE + "battleorders\tteleport\n", "not new: battleorders"),
            (V_RULE.replace("alphaevent\tbattleorders", "alphaevent\tnope"), "'nope' has no D2R overlay json"),
            ("teleport_debuff\n", "line 1: want 'overlay<tab>like'"),
        ]
        for rule, msg in cases:
            with self.subTest(msg), tempfile.TemporaryDirectory() as tmp:
                d2r, out, path = setup_overlays(Path(tmp), rule)
                with self.assertRaisesRegex(H.OverlayHdError, msg):
                    H.apply_overlays(path, Path(tmp) / "src", d2r, out)


if __name__ == "__main__":
    unittest.main()
