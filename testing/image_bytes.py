"""Read bytes of the running game image and compare stock with patched code (read-only, no plugin).

A check for an engine patch should read the code the running game executes, not trust a log line. This opens the game
process read-only, reads the PE time-date stamp of its main module (the value that names a build: 0x6ab3782c is D2R
3.3.0 build 93847 under D2RLoader 1.3.1) and the bytes at RVA spans:

    stamp, (cap, ) = read_image(ctx.game.pids()[0], [(0x4524a5, 5)])
    assert_stamp(stamp, 0x6ab3782c)                       # addresses are build specific: refuse any other image
    state = classify(cap, stock=bytes.fromhex("b932000000"), patched=bytes.fromhex("b94b000000"))  # PATCHED / STOCK / OTHER

The pure parts (pe_stamp, assert_stamp, classify, spans) need no game and no Windows; read_image needs Windows. RVAs and
stamps are parameters: the checks keep their own, or take them from the address registry (rvas_<build>.h).
"""
from __future__ import annotations

import os
import struct
import sys

STOCK, PATCHED, OTHER = "stock", "patched", "other"
HEADER_BYTES = 0x400


def pe_stamp(head: bytes) -> int:
    """The COFF TimeDateStamp of a PE image, from its first bytes (the DOS header points at the PE header)."""
    if len(head) < 0x40 or head[:2] != b"MZ":
        raise ValueError("not a PE image (no MZ header)")
    pe = struct.unpack_from("<I", head, 0x3C)[0]
    if pe + 12 > len(head) or head[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not a PE image (no PE signature in the first bytes)")
    return struct.unpack_from("<I", head, pe + 8)[0]


def assert_stamp(stamp: int, expected: int, what: str = "the addresses") -> None:
    assert stamp == expected, f"game image stamp 0x{stamp:x}, {what} are for 0x{expected:x}"


def classify(got: bytes, stock: bytes, patched: bytes) -> str:
    """STOCK when the bytes are the unpatched code, PATCHED when they are the patch, else OTHER."""
    if got == patched:
        return PATCHED
    if got == stock:
        return STOCK
    return OTHER


def spans(*pairs: tuple[int, bytes]) -> list[tuple[int, int]]:
    """(rva, expected bytes) pairs -> the (rva, size) list read_image takes."""
    return [(rva, len(b)) for rva, b in pairs]


def read_image(pid: int, wanted: list[tuple[int, int]]) -> tuple[int, list[bytes]]:
    """(PE stamp of the process's main module, the bytes at each (rva, size) span). Read-only. Windows only."""
    if sys.platform != "win32":
        raise OSError("reading a game image needs Windows")
    import ctypes
    from ctypes import wintypes
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools.dump_image import PROCESS_QUERY_INFORMATION, PROCESS_VM_READ, k32, psapi, read
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    assert h, f"OpenProcess({pid}) failed ({ctypes.get_last_error()})"
    try:
        mods = (ctypes.c_void_p * 1)()
        needed = wintypes.DWORD()
        assert psapi.EnumProcessModulesEx(h, mods, ctypes.sizeof(mods), ctypes.byref(needed), 0x03), \
            "EnumProcessModulesEx failed"
        base = mods[0]
        stamp = pe_stamp(read(h, base, HEADER_BYTES))
        return stamp, [read(h, base + rva, size) for rva, size in wanted]
    finally:
        k32.CloseHandle(h)
