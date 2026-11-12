"""Tests for testing/stats.py, testing/save_edit.py and testing/image_bytes.py (pure parts, no game)."""
from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "testing"))
sys.path.insert(0, str(ROOT))

import image_bytes as ib  # noqa: E402
import save_edit as se  # noqa: E402
from stats import assert_rate, count, tolerance_for  # noqa: E402

from modkit.saves import checksum  # noqa: E402


class StatsTest(unittest.TestCase):
    def test_same_seed_same_count(self):
        trial = lambda rng: rng.random() < 0.3  # noqa: E731
        self.assertEqual(count(trial, 5000, seed=1), count(trial, 5000, seed=1))

    def test_fair_rate_passes(self):
        hits = count(lambda rng: rng.randrange(100) < 25, 20000, seed=9)
        self.assertIn("expected 0.2500", assert_rate(hits, 20000, 0.25))

    def test_wrong_rate_fails(self):
        hits = count(lambda rng: rng.randrange(100) < 30, 20000, seed=9)
        with self.assertRaises(AssertionError):
            assert_rate(hits, 20000, 0.25)

    def test_explicit_tolerance(self):
        assert_rate(46, 100, 0.42, tolerance=0.05)
        with self.assertRaises(AssertionError):
            assert_rate(48, 100, 0.42, tolerance=0.05)

    def test_default_tolerance_is_four_sigma(self):
        self.assertAlmostEqual(tolerance_for(0.25, 10000), 4 * (0.25 * 0.75 / 10000) ** 0.5)

    def test_bad_input(self):
        for args in ((5, 0, 0.5), (11, 10, 0.5), (5, 10, 1.5)):
            with self.assertRaises(AssertionError):
                assert_rate(*args)


def fake_save(size: int = 0x200) -> bytearray:
    d = bytearray(size)
    d[:4] = b"\x55\xaa\x55\xaa"
    d[4:6] = struct.pack("<H", 0x69)
    d[6:8] = b"RD"
    d[0x18] = 4
    d[0x1B] = 1
    d[0x98:0x9B] = b"\x80\x00\x00"  # Normal active
    return d


class SaveEditTest(unittest.TestCase):
    def test_unlocked_bytes(self):
        out = se.unlocked(bytes(fake_save()))
        self.assertEqual(out[0x15], 0x0F)
        self.assertEqual(out[0x98:0x9B], b"\x00\x00\x80")
        self.assertEqual(se.unlocked(bytes(fake_save()), "nightmare", 3)[0x98:0x9B], b"\x00\x82\x00")

    def test_bad_arguments(self):
        for args in ((bytes(fake_save()), "hell", 0), (bytes(fake_save()), "hell", 6), (bytes(fake_save()), "x", 1),
                     (b"junk" * 100, "hell", 1)):
            with self.assertRaises(se.SaveEditError):
                se.unlocked(*args)

    def test_file_gets_size_and_checksum(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "c.d2s"
            p.write_bytes(bytes(fake_save()))
            se.unlock_difficulties(p)
            data = p.read_bytes()
            self.assertEqual(struct.unpack_from("<I", data, 8)[0], len(data))
            self.assertEqual(struct.unpack_from("<I", data, 0xC)[0], checksum(data))
            self.assertEqual(data[0x15], 0x0F)
            self.assertEqual(data[0x18], 4)  # the rest is untouched

    def test_missing_file(self):
        with self.assertRaises(se.SaveEditError):
            se.unlock_difficulties("no/such/file.d2s")


class ImageBytesTest(unittest.TestCase):
    @staticmethod
    def head(stamp: int) -> bytes:
        h = bytearray(0x400)
        h[:2] = b"MZ"
        struct.pack_into("<I", h, 0x3C, 0x80)
        h[0x80:0x84] = b"PE\0\0"
        struct.pack_into("<I", h, 0x88, stamp)
        return bytes(h)

    def test_stamp(self):
        self.assertEqual(ib.pe_stamp(self.head(0x6AB3782C)), 0x6AB3782C)
        for bad in (b"", b"ZM" + bytes(0x80), bytes(0x400)):
            with self.assertRaises(ValueError):
                ib.pe_stamp(bad)

    def test_assert_stamp(self):
        ib.assert_stamp(5, 5)
        with self.assertRaises(AssertionError) as e:
            ib.assert_stamp(5, 6)
        self.assertIn("0x5", str(e.exception))

    def test_classify(self):
        self.assertEqual(ib.classify(b"\x01", b"\x01", b"\x02"), ib.STOCK)
        self.assertEqual(ib.classify(b"\x02", b"\x01", b"\x02"), ib.PATCHED)
        self.assertEqual(ib.classify(b"\x03", b"\x01", b"\x02"), ib.OTHER)

    def test_spans(self):
        self.assertEqual(ib.spans((0x10, b"abc"), (0x20, b"z")), [(0x10, 3), (0x20, 1)])


if __name__ == "__main__":
    unittest.main()
