"""Tests for testing/unit_probe.py: a fake process memory, no game."""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "testing"))

import unit_probe as up  # noqa: E402

BASE = 0x10000000


class Memory:
    """Addresses -> bytes; a read inside a stored block returns that slice, anything else raises OSError."""

    def __init__(self):
        self.blocks: dict[int, bytes] = {}
        self.next_free = 0x50000000

    def put_unit(self, kind, row, uid, mode=0, nxt=0) -> int:
        addr, self.next_free = self.next_free, self.next_free + 0x1000
        body = bytearray(up.UNIT_NEXT + 8)
        struct.pack_into("<IIII", body, 0, kind, row, uid, mode)
        struct.pack_into("<Q", body, up.UNIT_NEXT, nxt)
        self.blocks[addr] = bytes(body)
        return addr

    def put_table(self, kind, heads: dict[int, int]):
        vals = [heads.get(i, 0) for i in range(up.BUCKETS)]
        self.blocks[up.table_address(BASE, kind)] = struct.pack(f"<{up.BUCKETS}Q", *vals)

    def read(self, addr, n):
        for start, data in self.blocks.items():
            if start <= addr and addr + n <= start + len(data):
                return data[addr - start:addr - start + n]
        raise OSError(f"unreadable {addr:#x}")


class Walk(unittest.TestCase):
    def test_table_addresses(self):
        self.assertEqual(up.table_address(BASE, up.PLAYER), BASE + up.CLIENT_UNITS)
        self.assertEqual(up.table_address(BASE, up.MONSTER), BASE + up.CLIENT_UNITS + 0x400)
        self.assertEqual(up.table_address(BASE, up.ITEM), BASE + up.CLIENT_UNITS + 0x1000)
        self.assertEqual(up.table_address(BASE, up.MISSILE), BASE + up.CLIENT_MISSILES)

    def test_lists_are_followed(self):
        m = Memory()
        b = m.put_unit(up.MISSILE, 7, 202)
        a = m.put_unit(up.MISSILE, 7, 101, nxt=b)  # two in one bucket
        c = m.put_unit(up.MISSILE, 9, 303)
        m.put_table(up.MISSILE, {5: a, 6: c})
        self.assertEqual(up.walk(m.read, BASE, up.MISSILE), {101: 7, 202: 7, 303: 9})

    def test_dead_monsters_and_other_types_are_left_out(self):
        m = Memory()
        alive = m.put_unit(up.MONSTER, 3, 1, mode=1)
        dead = m.put_unit(up.MONSTER, 3, 2, mode=12, nxt=alive)
        dying = m.put_unit(up.MONSTER, 3, 4, mode=0, nxt=dead)
        stray = m.put_unit(up.OBJECT, 3, 5, nxt=dying)  # not a monster: skipped, the list goes on
        m.put_table(up.MONSTER, {0: stray})
        self.assertEqual(up.walk(m.read, BASE, up.MONSTER), {1: 3})

    def test_a_freed_unit_stops_the_list(self):
        m = Memory()
        a = m.put_unit(up.MISSILE, 1, 1, nxt=0xdead0000)  # next is unreadable
        m.put_table(up.MISSILE, {0: a})
        self.assertEqual(up.walk(m.read, BASE, up.MISSILE), {1: 1})

    def test_a_loop_does_not_hang(self):
        m = Memory()
        a = m.put_unit(up.MISSILE, 1, 1)
        m.blocks[a] = m.blocks[a][:up.UNIT_NEXT] + struct.pack("<Q", a)  # points at itself
        m.put_table(up.MISSILE, {0: a})
        self.assertEqual(up.walk(m.read, BASE, up.MISSILE), {1: 1})

    def test_unreadable_table_raises(self):
        with self.assertRaises(OSError):
            up.walk(Memory().read, BASE, up.MISSILE)


class Bursts(unittest.TestCase):
    def test_grouping(self):
        seen = {1: 0.0, 2: 0.1, 3: 0.2, 4: 1.0, 5: 1.1, 6: 3.0}
        self.assertEqual(up.burst_sizes(seen, gap=0.25), [3, 2, 1])
        self.assertEqual(up.burst_sizes(seen, gap=5), [6])
        self.assertEqual(up.burst_sizes({}), [])

    def test_watching_a_probe(self):
        class Fake:
            def __init__(self):
                self.calls = 0

            def missiles(self):
                self.calls += 1
                return {1: 5, 2: 5, 3: 9} if self.calls > 2 else {}
        self.assertEqual(up.bursts(Fake(), 5, 0.05), [2])


if __name__ == "__main__":
    unittest.main()
