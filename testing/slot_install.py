#!/usr/bin/env python
"""Install a built mod project into a test slot, keeping the slot's own save folder.

  MODKIT_RUN=<lane> python testing/slot_install.py [--config F] --slot N PROJECT

`modkit install` writes the project's savepath into both modinfo.json files, so a slot installed with it would play
on the project's save folder instead of its own. This runs `modkit install` into slot N with savepath
`<saves.slot_name>/` (for example `MyMod-s2/`), on a fresh install and on every reinstall, and (with
loader.set_default_mod, as `game_slots.py setup` does) makes the slot's loader start this mod.

Refuses: slot 1, a slot not locked by MODKIT_RUN, a slot whose game runs, and a project whose mod.json name is not
mod.folder. Games in other slots may keep running (plain `modkit install` refuses while any game runs).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))  # the toolkit root, for modkit
import game_slots  # noqa: E402
import release_install  # noqa: E402
import testing_config as tc  # noqa: E402
from modkit.install import install as modkit_install  # noqa: E402


def install(cfg: tc.Config, n: int, project: str, owner: str | None = None) -> str:
    n = release_install.check_slot(cfg, n, owner)  # slot 1, lock held by MODKIT_RUN, no game running in the slot
    game_slots.guard_writable(cfg, n)
    name = json.loads(Path(project, "mod.json").read_text("utf-8"))["name"]
    if name != cfg.mod_folder():
        raise game_slots.SlotError(f"{project} is mod {name!r} but mod.folder is {cfg.mod_folder()!r}")
    savepath = cfg.save_name(n) + "/"
    msg = modkit_install(Path(project), Path(cfg.slot_dir(n)), savepath=savepath, check_running=False)
    if cfg["loader"]["set_default_mod"]:  # as setup does: the slot launches the mod just installed
        game_slots.set_loader_value(cfg, n, cfg["loader"]["default_mod_key"], cfg.mod_folder())
    os.makedirs(cfg.save_dir(n), exist_ok=True)
    return f"{msg}; savepath {savepath}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    tc.add_config_arg(ap)
    ap.add_argument("--slot", type=int, default=tc.env_slot(), help="slot number (default MODKIT_SLOT)")
    ap.add_argument("project", help="mod project folder (built: out/data exists)")
    a = ap.parse_args(argv)
    if a.slot is None:
        print("no slot: pass --slot N or set MODKIT_SLOT", file=sys.stderr)
        return 2
    try:
        print(install(tc.load(a.config), a.slot, a.project))
    except (tc.ConfigError, game_slots.SlotError, release_install.ReleaseError, FileNotFoundError,
            RuntimeError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
