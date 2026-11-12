"""The slot-to-owner table: which project may lock which game slot.

Several projects share one machine and one set of game slots. The table that says whose slot is whose is machine
config, never a repo file: it lives in `~/.d2r-modkit/slots.toml` (or the file named by --slots-file / the environment
variable MODKIT_SLOTS_FILE). `game_slots.py lock` reads it and refuses to lock a slot another project owns.

Format (a slot number or a range as the key, a project name as the value; names are free text, compared as written):

    # ~/.d2r-modkit/slots.toml
    [owners]
    "2"   = "toolkit"        # the toolkit's own tests
    "3"   = "mod-a"
    "4-6" = "mod-b"          # a range, both ends included
    # slots not listed belong to nobody: any project may lock them

A caller says which project it is with `--project NAME` or the environment variable MODKIT_PROJECT. With a table
present, `lock N` on a slot owned by another project, or with no project given, is refused; `lock any` takes only a
slot the project owns, else an unowned one (the project's own first). With no table file nothing is enforced (the old
behaviour). A table that cannot be read or parsed refuses every lock instead of being skipped.

This module only reads a file and compares names. It never touches a game or a lock.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import testing_config as tc  # noqa: E402

ENV_FILE = "MODKIT_SLOTS_FILE"
ENV_PROJECT = "MODKIT_PROJECT"
DEFAULT_FILE = os.path.join("~", ".d2r-modkit", "slots.toml")


class RegistryError(tc.ConfigError):
    """The slot table is unreadable or wrong."""


@dataclass
class SlotRegistry:
    owners: dict[int, str] = field(default_factory=dict)
    source: str | None = None

    def owner_of(self, n: int) -> str | None:
        return self.owners.get(int(n))

    def slots_of(self, project: str) -> list[int]:
        return sorted(n for n, o in self.owners.items() if o == project)

    def refusal(self, n: int, project: str | None) -> str | None:
        """Why project may not lock slot N (None: it may)."""
        project = (project or "").strip() or None
        owner = self.owner_of(n)
        if owner is None or owner == project:
            return None
        if not project:
            return (f"slot {n} belongs to project {owner!r} in the slot table ({self.source}); say which project you "
                    f"are with --project NAME or MODKIT_PROJECT")
        return f"slot {n} belongs to project {owner!r} in the slot table ({self.source}), not to {project!r}"

    def candidates(self, slots: list[int], project: str | None) -> list[int]:
        """The slots of `slots` this project may take, its own first, then the unowned ones."""
        project = (project or "").strip() or None
        own = [s for s in slots if project and self.owner_of(s) == project]
        free = [s for s in slots if self.owner_of(s) is None]
        return own + [s for s in free if s not in own]


def parse(data: dict, source: str | None = None) -> SlotRegistry:
    owners_raw = data.get("owners", {})
    if not isinstance(owners_raw, dict):
        raise RegistryError("[owners] must be a table of slot (or range) = project name")
    unknown = [k for k in data if k != "owners"]
    if unknown:
        raise RegistryError(f"unknown section(s) {unknown}: the table has only [owners]")
    owners: dict[int, str] = {}
    for key, project in owners_raw.items():
        m = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+))?\s*", str(key))
        if not m:
            raise RegistryError(f"bad slot key {key!r}: use a number (\"3\") or a range (\"4-8\")")
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        if lo > hi:
            raise RegistryError(f"bad range {key!r}: the first slot is after the last")
        if not isinstance(project, str) or not project.strip():
            raise RegistryError(f"slot {key!r}: the project must be a non-empty name")
        for n in range(lo, hi + 1):
            if n < 2:
                raise RegistryError(f"slot {n}: slot 1 is the user's own game and has no owner entry")
            if n in owners:
                raise RegistryError(f"slot {n} is listed twice")
            owners[n] = project.strip()
    return SlotRegistry(owners, source)


def default_path(env: dict | None = None) -> str:
    env = os.environ if env is None else env
    return os.path.expanduser(env.get(ENV_FILE) or DEFAULT_FILE)


def load(path: str | None = None, env: dict | None = None) -> SlotRegistry | None:
    """The slot table, or None when there is no file (nothing is enforced then). A file that exists but cannot be
    read or parsed raises RegistryError."""
    p = os.path.expanduser(path) if path else default_path(env)
    if not os.path.isfile(p):
        explicit = bool(path) or bool((os.environ if env is None else env).get(ENV_FILE))
        if explicit:
            raise RegistryError(f"slot table {p} not found")
        return None
    try:
        import tomllib
        with open(p, "rb") as f:
            data = tomllib.loads(f.read().decode("utf-8-sig"))
    except Exception as e:  # OSError, UnicodeDecodeError, TOMLDecodeError
        raise RegistryError(f"slot table {p} is not valid: {e}") from e
    return parse(data, p)


def env_project(env: dict | None = None) -> str | None:
    return ((os.environ if env is None else env).get(ENV_PROJECT) or "").strip() or None
