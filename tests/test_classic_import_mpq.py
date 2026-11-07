"""Tests for shared/classic_import/mpq.py (run: python -m unittest discover tests). No game files needed."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.classic_import import mpq  # noqa: E402


class MpqTests(unittest.TestCase):
    def test_table_keys(self):
        # the well-known keys every MPQ reader uses for its hash and block tables
        self.assertEqual(mpq.hash_string("(hash table)", 3), 0xC3AF3770)
        self.assertEqual(mpq.hash_string("(block table)", 3), 0xEC83B3A3)

    def test_explode(self):
        # the test vector from zlib's contrib/blast
        self.assertEqual(mpq.explode(bytes.fromhex("00048224258f807f")), b"AIAIAIAIAIAIA")


if __name__ == "__main__":
    unittest.main()
