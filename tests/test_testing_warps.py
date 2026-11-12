"""Tests for testing/warps.py: a synthetic DS1 and tables, no game."""
from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "testing"))

import warps  # noqa: E402


def ds1(w=10, h=8, objects=(), version=18, act=0) -> bytes:
    """A DS1 w x h tiles, no files, one wall and one floor layer, then the given (type, id, x, y) objects."""
    out = struct.pack("<3i", version, w - 1, h - 1) + struct.pack("<i", act) + struct.pack("<i", 0)  # act, tag
    out += struct.pack("<i", 0)  # no file names
    out += struct.pack("<ii", 1, 1)  # walls, floors
    out += bytes(4 * w * h * 4)  # 2 wall grids + 1 floor + 1 shadow (tag 0)
    out += struct.pack("<i", len(objects))
    for kind, oid, x, y in objects:
        out += struct.pack("<5i", kind, oid, x, y, 0)
    return out


def table(name, rows):
    return warps.Table.parse(name, "\r\n".join("\t".join(r) for r in rows) + "\r\n")


class Math(unittest.TestCase):
    def test_subtiles(self):
        self.assertEqual(warps.subtile(2550, 75), 2550 * 5 + 75 * 5 + 2)
        self.assertEqual(warps.hd_subtile(100, 25.0), 512)
        self.assertEqual(warps.selector("data\\global\\Tiles/Cave\\V2.DS1"), "v2.ds1")
        self.assertEqual(warps.goto(144), "cheat goto 144")
        self.assertEqual(warps.goto(144, 5, 6), "cheat goto 144,5,6")


class Reader(unittest.TestCase):
    def test_header_and_objects(self):
        data = ds1(10, 8, [(1, 0, 20, 30), (2, 3, 55, 60)], act=2)
        v, w, h, act, *_ = warps.ds1_header(data)
        self.assertEqual((v, w, h, act), (18, 10, 8, 2))
        self.assertEqual(warps.read_objects(data), [(1, 0, 20, 30, ), (2, 3, 55, 60)])

    def test_reference_spots(self):
        data = ds1(10, 8, [(2, 3, 55, 60), (2, 4, 5, 5), (1, 1, 25, 35), (1, 0, 1, 1)])
        classes = {(1, 3): "Waypoint Portal", (1, 4): "Chest"}
        places = {1: ["Rat", "Mephisto Unique"]}
        self.assertEqual(warps.reference_spots(data, classes),
                         [("centre", 5, 4), ("waypoint", 11, 12)])
        self.assertEqual(warps.reference_spots(data, classes, places),
                         [("centre", 5, 4), ("waypoint", 11, 12), ("monster preset Mephisto Unique", 5, 7)])


class Folder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d = Path(self.tmp.name)
        ex, tiles = d / "global" / "excel", d / "global" / "tiles" / "cave"
        ex.mkdir(parents=True)
        tiles.mkdir(parents=True)

        def put(name, rows):
            (ex / f"{name}.txt").write_bytes(("\r\n".join("\t".join(r) for r in rows) + "\r\n").encode())
        put("levels", [["Name", "Id", "OffsetX", "OffsetY"], ["Cave", "50", "100", "200"], ["Rand", "51", "-1", "-1"]])
        put("lvlprest", [["Name", "LevelId", "Files", "File1", "File2"],
                         ["Cave", "50", "2", "cave/a.ds1", "cave/b.ds1"], ["Rand", "51", "1", "cave/a.ds1", "0"]])
        put("objpreset", [["Index", "Act", "Class"], ["3", "1", "Waypoint"]])
        put("monpreset", [["Act", "Place"], ["1", "Rat"]])
        (tiles / "a.ds1").write_bytes(ds1(10, 8, [(2, 3, 55, 60)]))
        self.d = d

    def test_level_warps(self):
        out = warps.level_warps(self.d, 50, "A.DS1")
        self.assertEqual(out[0], "cave/a.ds1, 10x8 tiles")  # one variant named: no pin hint
        self.assertIn(f"  centre (tile 5,4): cheat goto 50,{warps.subtile(100, 5)},{warps.subtile(200, 4)}", out)
        self.assertIn("  entry: cheat goto 50", out)
        both = warps.level_warps(self.d, 50)
        self.assertIn("pin: force_ds1.py", both[0])
        self.assertIn("DS1 not found", "\n".join(both))  # b.ds1 is absent

    def test_random_origin(self):
        out = "\n".join(warps.level_warps(self.d, 51))
        self.assertIn("origin unknown", out)
        self.assertNotIn("cheat goto", out)

    def test_errors(self):
        with self.assertRaises(ValueError):
            warps.level_warps(self.d, 99)
        with self.assertRaises(ValueError):
            warps.level_warps(self.d, 50, "zz.ds1")
        self.assertEqual(warps.main(["--data", str(self.d), "--level", "99"]), 1)
        self.assertEqual(warps.main(["--data", str(self.d), "--level", "50", "--ds1", "a.ds1"]), 0)


if __name__ == "__main__":
    unittest.main()
