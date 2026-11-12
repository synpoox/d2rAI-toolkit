"""Read the client's units from a running D2R game, read-only and without a plugin: what is alive now, by unit type.

    from unit_probe import UnitProbe, MONSTER, MISSILE, bursts
    probe = UnitProbe(ctx.game.pids()[0])
    probe.units(MONSTER)                  # {unit id: monstats row} of the monsters alive on the client
    probe.missiles()                      # {unit id: missiles.txt row}
    bursts(probe, row=5, seconds=3.0)     # sizes of the groups of missiles of that row that appeared together

Build 93847 only (PE timestamp 0x6ab3782c, knowledge/d2r-93847-addresses.md): the client keeps each unit type in a
128-bucket hash table (unit id & 0x7f), lists linked through unit +0x158. Players, monsters, objects and items are in
tables of the same shape, 0x400 bytes apart; missiles have their own table. The probe refuses an image it does not
know, and tolerates a list changing under it (a unit freed while walked is skipped). It reads memory with
ReadProcessMemory only: it never writes to the game. Windows is needed to attach; the table walk and the burst
grouping are pure and tested without a game. Standard library only.
"""
from __future__ import annotations

import struct
import time
from typing import Callable

IMAGE_STAMP = 0x6ab3782c       # PE TimeDateStamp of build 93847 (rvas_93847.h ImageStamp)
CLIENT_UNITS = 0x2a23910       # RVA: + type * 0x400: 128 x Unit* each, for players, monsters, objects, items
CLIENT_MISSILES = 0x2a25d10    # RVA: 128 x Unit*
BUCKETS = 128
UNIT_TYPE, UNIT_CLASS, UNIT_ID, UNIT_MODE, UNIT_NEXT = 0x00, 0x04, 0x08, 0x0c, 0x158
PLAYER, MONSTER, OBJECT, MISSILE, ITEM = 0, 1, 2, 3, 4
MONSTER_GONE = (0, 12)         # monmode death and dead: the client keeps corpses in the table
MAX_LIST = 4096                # a broken list must not hang a check

Reader = Callable[[int, int], bytes]  # read(address, n) -> n bytes, OSError when unreadable


def table_address(base: int, kind: int) -> int:
    """Address of the 128-bucket table for a unit type."""
    return base + (CLIENT_MISSILES if kind == MISSILE else CLIENT_UNITS + kind * BUCKETS * 8)


def walk(read: Reader, base: int, kind: int) -> dict[int, int]:
    """unit id -> class row (monstats.txt, missiles.txt, ...) of every client unit of this type alive now. `read` reads
    the game's memory; `base` is the image base."""
    out: dict[int, int] = {}
    for unit in struct.unpack(f"<{BUCKETS}Q", read(table_address(base, kind), BUCKETS * 8)):
        for _ in range(MAX_LIST):
            if not unit:
                break
            try:
                head = read(unit, UNIT_NEXT + 8)
            except OSError:
                break  # freed while we walked it
            found, row, uid, mode = struct.unpack_from("<IIII", head, 0)
            if found == kind and not (kind == MONSTER and mode in MONSTER_GONE):
                out[uid] = row
            unit = struct.unpack_from("<Q", head, UNIT_NEXT)[0]
    return out


def burst_sizes(first_seen: dict[int, float], gap: float = 0.25) -> list[int]:
    """Group units by when each was first seen: ones within `gap` seconds of the previous form a burst. Burst sizes."""
    sizes, last = [], None
    for t in sorted(first_seen.values()):
        if last is None or t - last > gap:
            sizes.append(0)
        sizes[-1] += 1
        last = t
    return sizes


class UnitProbe:
    """Attach (read-only) to the game process `pid` and read its client units."""

    def __init__(self, pid: int):
        import ctypes
        import ctypes.wintypes as wt
        self._ct, self._wt = ctypes, wt
        self._k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        self._k32.OpenProcess.restype = wt.HANDLE
        self._k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                                ctypes.POINTER(ctypes.c_size_t)]
        self.h = self._k32.OpenProcess(0x0410, False, pid)  # QUERY_INFORMATION | VM_READ
        if not self.h:
            raise OSError(f"OpenProcess({pid}) failed: {ctypes.get_last_error()}")
        mods, need = (ctypes.c_void_p * 1)(), wt.DWORD()
        if not psapi.EnumProcessModulesEx(self.h, mods, ctypes.sizeof(mods), ctypes.byref(need), 3):  # LIST_MODULES_ALL
            raise OSError(f"EnumProcessModulesEx failed: {ctypes.get_last_error()}")
        self.base = mods[0]
        stamp = struct.unpack("<I", self.read(self.base + self.u32(self.base + 0x3c) + 8, 4))[0]
        if stamp != IMAGE_STAMP:
            raise RuntimeError(f"image stamp {stamp:#x}, the probe knows {IMAGE_STAMP:#x} (build 93847) only")

    def read(self, addr: int, n: int) -> bytes:
        ct = self._ct
        buf, got = ct.create_string_buffer(n), ct.c_size_t()
        if not self._k32.ReadProcessMemory(self.h, ct.c_void_p(addr), buf, n, ct.byref(got)) or got.value != n:
            raise OSError(f"read {addr:#x} failed")
        return buf.raw

    def u32(self, addr: int) -> int:
        return struct.unpack("<I", self.read(addr, 4))[0]

    def units(self, kind: int) -> dict[int, int]:
        """unit id -> class row of every client unit of this type alive now (dead monsters left out)."""
        return walk(self.read, self.base, kind)

    def missiles(self) -> dict[int, int]:
        """unit id -> missiles.txt row of every client missile alive now."""
        return self.units(MISSILE)

    def close(self) -> None:
        if self.h:
            self._k32.CloseHandle(self.h)
            self.h = None


def bursts(probe, row: int, seconds: float, gap: float = 0.25) -> list[int]:
    """Watch `seconds`; missiles of `row` first seen within `gap` of each other form one burst. Burst sizes."""
    seen: dict[int, float] = {}
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        now = time.monotonic()
        for uid, r in probe.missiles().items():
            if r == row and uid not in seen:
                seen[uid] = now
        time.sleep(0.005)
    return burst_sizes(seen, gap)
