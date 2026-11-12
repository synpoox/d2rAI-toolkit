"""Tests for testing/unit_probe.py: a fake process memory, no game."""
from __future__ import annotations

import os
import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "testing"))

import game_slots as gs  # noqa: E402
import testing_config as tc  # noqa: E402
import unit_probe as up  # noqa: E402

SRC = ROOT / "shared" / "plugin-common" / "src"
KNOWLEDGE = ROOT / "knowledge" / "d2r-93847-addresses.md"

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
        class Clock:
            now = 0.0

            def __call__(self):
                return self.now

            def sleep(self, dt):
                self.now += dt

        clock = Clock()

        class Fake:
            def missiles(self):  # a burst of two from t=0.05, and an unrelated row
                return {1: 5, 2: 5, 3: 9} if clock.now >= 0.05 else {}
        self.assertEqual(up.bursts(Fake(), 5, 0.2, clock=clock, sleep=clock.sleep), [2])
        self.assertGreaterEqual(clock.now, 0.2)


def header_text() -> str:
    """The per-build header(s) without comments: rvas_93847.h plus rvas_93847/*.h (before and after the split)."""
    files = [SRC / "rvas_93847.h", *sorted((SRC / "rvas_93847").glob("*.h"))]
    return "\n".join(re.sub(r"//[^\n]*", "", f.read_text(encoding="utf-8")) for f in files if f.is_file())


def header_value(name: str):
    m = re.search(rf"\b{name}\s*=\s*(0x[0-9a-fA-F]+)", header_text())
    return int(m.group(1), 16) if m else None


class Registry(unittest.TestCase):
    """The probe holds copies of the registry's values; they must not drift (two homes, one fact)."""

    def test_addresses_equal_the_header(self):
        self.assertEqual(up.IMAGE_STAMP, header_value("ImageStamp"))
        self.assertEqual(up.CLIENT_UNITS, header_value("ClientUnits"))
        self.assertEqual(up.CLIENT_MISSILES, header_value("ClientMissiles"))

    def test_unit_offsets_equal_the_header_once_it_has_them(self):
        want = {"UnitType": up.UNIT_TYPE, "UnitClassId": up.UNIT_CLASS, "UnitIdField": up.UNIT_ID,
                "UnitMode": up.UNIT_MODE, "UnitListNext": up.UNIT_NEXT}
        found = {k: header_value(k) for k in want}
        split = (SRC / "rvas_93847" / "offsets.h").is_file()  # after the split every offset is in the registry
        for name, mine in want.items():
            with self.subTest(name=name):
                if found[name] is None and not split:
                    continue  # not in the registry yet: nothing to compare
                self.assertEqual(mine, found[name])

    def test_both_rvas_have_knowledge_rows(self):
        keyed = set()
        for line in KNOWLEDGE.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\|([^|]*)\|", line)
            if m:
                keyed.update(int(h, 16) for h in re.findall(r"`(0x[0-9a-fA-F]+)`", m.group(1)))
        self.assertIn(up.CLIENT_UNITS, keyed)
        self.assertIn(up.CLIENT_MISSILES, keyed)


def make_cfg(tmp: str) -> tc.Config:
    t = Path(tmp).as_posix()
    data = {"game": {"install_dir": f"{t}/install", "slots_dir": f"{t}/slots", "slot_count": 3},
            "mod": {"folder": "MyMod", "name": "My Mod", "plugin_dlls": ["my-plugin.dll"]},
            "saves": {"root": f"{t}/saves"}, "runs": {"dir": f"{t}/runs"}}
    return tc.Config(data, base_dir=tmp)


class ForSlot(unittest.TestCase):
    """Slot rules, with a temp config only: nothing here opens a process or touches a game folder."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.cfg = make_cfg(tmp.name)
        patch = mock.patch.dict(os.environ, {"MODKIT_RUN": "lane-a"})
        patch.start()
        self.addCleanup(patch.stop)
        attach = mock.patch.object(up.UnitProbe, "_attach", side_effect=AssertionError("must not attach"))
        self.attach = attach.start()
        self.addCleanup(attach.stop)

    def test_slot_one_is_refused(self):
        with mock.patch.object(gs, "slot_processes", return_value=[(99, "D2R.exe")]):
            with self.assertRaises(up.ProbeError) as e:
                up.UnitProbe.for_slot(self.cfg, 1)
        self.assertEqual(str(e.exception), gs.SLOT1_MSG)

    def test_an_unlocked_slot_is_refused(self):
        with mock.patch.object(gs, "slot_processes", return_value=[(99, "D2R.exe")]):
            with self.assertRaisesRegex(up.ProbeError, "not locked by MODKIT_RUN='lane-a'"):
                up.UnitProbe.for_slot(self.cfg, 2)

    def test_another_owners_lock_is_refused(self):
        self.assertTrue(gs.acquire(self.cfg, 2, "lane-b")[0])
        with mock.patch.object(gs, "slot_processes", return_value=[(99, "D2R.exe")]):
            with self.assertRaisesRegex(up.ProbeError, "not locked by MODKIT_RUN='lane-a'"):
                up.UnitProbe.for_slot(self.cfg, 2)
            with mock.patch.dict(os.environ, {}, clear=True), self.assertRaises(up.ProbeError):
                up.UnitProbe.for_slot(self.cfg, 2)  # no MODKIT_RUN at all

    def test_a_locked_slot_without_a_game_is_refused(self):
        self.assertTrue(gs.acquire(self.cfg, 2, "lane-a")[0])
        with mock.patch.object(gs, "slot_processes", return_value=[]):
            with self.assertRaisesRegex(up.ProbeError, "no running game"):
                up.UnitProbe.for_slot(self.cfg, 2)

    def test_the_pid_comes_from_the_slots_own_processes(self):
        self.assertTrue(gs.acquire(self.cfg, 2, "lane-a")[0])
        self.attach.side_effect = lambda pid: ("attached", pid)
        with mock.patch.object(gs, "slot_processes", return_value=[(7, "loader.exe"), (42, "D2R.exe")]) as sp:
            self.assertEqual(up.UnitProbe.for_slot(self.cfg, 2), ("attached", 42))
        sp.assert_called_once_with(self.cfg, 2)

    def test_a_bare_pid_cannot_construct_one(self):
        with self.assertRaises(TypeError):
            up.UnitProbe(1234)

    def test_the_context_manager_closes_the_handle(self):
        probe = object.__new__(up.UnitProbe)
        probe.h = 5
        probe._k32 = mock.Mock()
        with probe:
            pass
        probe._k32.CloseHandle.assert_called_once_with(5)
        self.assertIsNone(probe.h)


if __name__ == "__main__":
    unittest.main()
