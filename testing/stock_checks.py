"""Stock checks that hold for any mod: list `stock_checks` in checks.modules of the testing config to get them.

slot-savepath: every modinfo.json the mod has in the slot names the slot's own save folder in `savepath`. Slot 1 is the
user's own game and keeps the plain mod folder name; every other slot gets its own name (saves.slot_name, default
`<folder>-s<slot>`), so a test character never lands in, or reads from, the user's saves. A slot installed with
slot_install.py gets this right; the check catches a hand-copied or stale slot before a game run writes a save to the
wrong place.
"""
from __future__ import annotations

import json
import os

from game_checks import check


def savepath_problems(cfg, slot: int) -> list[str]:
    """What is wrong with the slot's modinfo files' `savepath`, as short messages; an empty list means all is right."""
    want = cfg.save_name(slot) + "/"
    found, problems = 0, []
    for path in cfg.modinfo_paths(slot):
        if not os.path.isfile(path):
            continue
        found += 1
        try:
            with open(path, encoding="utf-8-sig") as f:
                got = json.load(f).get("savepath")
        except (OSError, ValueError, AttributeError) as e:
            problems.append(f"{path}: cannot read ({e})")
            continue
        if not isinstance(got, str) or got.replace("\\", "/") != want:
            problems.append(f"{path}: savepath is {got!r}, slot {slot} wants {want!r}")
    if not found:
        problems.append(f"no modinfo file in slot {slot}: looked for " + ", ".join(cfg.modinfo_paths(slot)))
    return problems


@check("slot-savepath", tags=["offline", "slot"])
def slot_savepath(ctx):
    """The slot's modinfo.json savepath is the slot's own save folder (never the user's)."""
    problems = savepath_problems(ctx.cfg, ctx.slot)
    assert not problems, "; ".join(problems)
    return f"savepath {ctx.cfg.save_name(ctx.slot)}/"
