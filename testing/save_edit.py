"""Edit a character save for a game check: unlock difficulties.

A fresh character can only play Normal. A check that needs Hell (level 90+ areas, Hell monsters) opens it in the save
file, with the game CLOSED (the save is read at character select):

    from save_edit import unlock_difficulties
    unlock_difficulties(Path(ctx.cfg.save_dir(ctx.slot)) / "mychar.d2s")        # Hell open and current, act 1

Layout (D2R 3.x .d2s, knowledge/saves.md): byte 0x15 is the progression, 0x0f = every difficulty done; bytes 0x98, 0x99, 0x9a hold the current-location byte of Normal, Nightmare and
Hell: 0x80 = this difficulty is the active one, low bits = act - 1; 0 = not active. The size field, checksum and the
.d2rl sidecar are fixed with modkit.saves.finalize.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # the toolkit root, for modkit
from modkit.saves import finalize  # noqa: E402

PROGRESSION = 0x15
ALL_DONE = 0x0F
DIFFICULTY_BYTES = 0x98  # Normal, Nightmare, Hell
DIFFICULTIES = ("normal", "nightmare", "hell")
ACTIVE = 0x80


class SaveEditError(Exception):
    """The file is not a save this module can edit."""


def unlocked(data: bytes, current: str = "hell", act: int = 1) -> bytes:
    """A copy of the save bytes with every difficulty open and `current` active in `act` (1-5). Size and checksum
    are NOT fixed here (finalize does it when the file is written)."""
    if current not in DIFFICULTIES:
        raise SaveEditError(f"current difficulty must be one of {DIFFICULTIES}, not {current!r}")
    if not 1 <= act <= 5:
        raise SaveEditError(f"act must be 1..5, not {act}")
    if data[:4] != b"\x55\xaa\x55\xaa":
        raise SaveEditError("not a .d2s (bad signature)")
    out = bytearray(data)
    out[PROGRESSION] = ALL_DONE
    for i, name in enumerate(DIFFICULTIES):
        out[DIFFICULTY_BYTES + i] = (ACTIVE | (act - 1)) if name == current else 0
    return bytes(out)


def unlock_difficulties(path: str | Path, current: str = "hell", act: int = 1) -> None:
    """Open every difficulty in the .d2s at `path`, make `current` the active one, and write it back with a correct
    size, checksum and .d2rl sidecar. The game must be closed."""
    path = Path(path)
    if not path.is_file():
        raise SaveEditError(f"no save at {path}")
    finalize(path, bytearray(unlocked(path.read_bytes(), current, act)))
