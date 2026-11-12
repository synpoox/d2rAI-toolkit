"""Read the client's units from a running D2R game, read-only and without a plugin: what is alive now, by unit type.

    from unit_probe import UnitProbe, MONSTER, MISSILE, bursts
    with UnitProbe.for_slot(cfg, 2) as probe:   # slot 2+, locked by MODKIT_RUN; never slot 1
        probe.units(MONSTER)                  # {unit id: monstats row} of the monsters alive on the client
        probe.missiles()                  # {unit id: missiles.txt row}
        bursts(probe, row=5, seconds=3.0) # sizes of the groups of missiles of that row that appeared together

`for_slot` is the only public way to attach: it refuses slot 1 (the user's own game), requires the slot lock to be held
by MODKIT_RUN, and takes the pid from the slot's own process list. The addresses below are copies of the registry
(shared/plugin-common/src/rvas_93847*.h, knowledge/d2r-93847-addresses.md); tests/test_testing_unit_probe.py fails when
they differ.

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


class ProbeError(Exception):
    """The probe was refused (slot rules) or cannot attach."""

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
    """Read-only view of one game's client units. Make one with `UnitProbe.for_slot(cfg, n)`; close it (or use `with`)."""

    def __init__(self, *_a, **_k):
        raise TypeError("use UnitProbe.for_slot(cfg, n): attaching to a bare pid could read the user's own game")

    @classmethod
    def for_slot(cls, cfg, n: int, owner: str | None = None) -> "UnitProbe":
        """Attach to the game running in test slot `n`. Refuses slot 1, a slot the lock of which is not held by
        `owner` (default: MODKIT_RUN), and a slot without a running game; the pid comes from the slot's own processes."""
        import game_slots
        import testing_config as tc
        n = cfg.check_slot_number(n)
        if cfg.is_slot_one(n):
            raise ProbeError(game_slots.SLOT1_MSG)
        owner = owner or tc.env_run()
        info = game_slots.lock_info(cfg, n)
        if not owner or info is None or info.owner != owner:
            raise ProbeError(f"slot {n} is not locked by MODKIT_RUN={owner!r}: "
                             f"python testing/game_slots.py lock {n} <lane>, then MODKIT_RUN=<lane>")
        procs = game_slots.slot_processes(cfg, n)
        if not procs:
            raise ProbeError(f"slot {n} has no running game")
        pid = next((p for p, name in procs if name.lower() == "d2r.exe"), procs[0][0])
        return cls._attach(pid)

    @classmethod
    def _attach(cls, pid: int) -> "UnitProbe":
        """UNSAFE: attaches to any process id with no slot check. Only for_slot (and tests) may call it."""
        self = object.__new__(cls)
        self._open(pid)
        return self

    def __enter__(self) -> "UnitProbe":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def _open(self, pid: int) -> None:
        import ctypes
        import ctypes.wintypes as wt
        self.h = None
        self._ct, self._wt = ctypes, wt
        self._k32 = k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
        k32.OpenProcess.restype = wt.HANDLE
        k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                          ctypes.POINTER(ctypes.c_size_t)]
        k32.ReadProcessMemory.restype = wt.BOOL
        k32.CloseHandle.argtypes = [wt.HANDLE]
        k32.CloseHandle.restype = wt.BOOL
        psapi.EnumProcessModulesEx.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), wt.DWORD]
        psapi.EnumProcessModulesEx.restype = wt.BOOL
        self.h = k32.OpenProcess(0x0410, False, pid)  # QUERY_INFORMATION | VM_READ
        if not self.h:
            raise OSError(f"OpenProcess({pid}) failed: {ctypes.get_last_error()}")
        try:
            mods, need = (ctypes.c_void_p * 1)(), wt.DWORD()
            if not psapi.EnumProcessModulesEx(self.h, mods, ctypes.sizeof(mods), ctypes.byref(need), 3):  # LIST_MODULES_ALL
                raise OSError(f"EnumProcessModulesEx failed: {ctypes.get_last_error()}")
            self.base = mods[0]
            stamp = struct.unpack("<I", self.read(self.base + self.u32(self.base + 0x3c) + 8, 4))[0]
            if stamp != IMAGE_STAMP:
                raise RuntimeError(f"image stamp {stamp:#x}, the probe knows {IMAGE_STAMP:#x} (build 93847) only")
        except BaseException:
            self.close()
            raise

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


def bursts(probe, row: int, seconds: float, gap: float = 0.25, clock: Callable[[], float] = time.monotonic,
           sleep: Callable[[float], None] = time.sleep) -> list[int]:
    """Watch `seconds`; missiles of `row` first seen within `gap` of each other form one burst. Burst sizes.
    `clock` and `sleep` are injectable so a test needs no real time."""
    seen: dict[int, float] = {}
    end = clock() + seconds
    while clock() < end:
        now = clock()
        for uid, r in probe.missiles().items():
            if r == row and uid not in seen:
                seen[uid] = now
        sleep(0.005)
    return burst_sizes(seen, gap)
