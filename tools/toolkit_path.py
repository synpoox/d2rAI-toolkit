"""Find the d2rAI-toolkit checkout from a mod project, and check the mod's `toolkit.version` pin.

Rules (identical in ToolkitPath.ps1 and cmake/FindD2rToolkit.cmake; see docs/toolkit-finder.md):
  1. $D2R_TOOLKIT, if set, must be a toolkit folder.
  2. Else walk up from the start folder. At each level, that level is the answer if it is itself a toolkit
     (the caller is inside the toolkit or one of its worktrees); else its `d2rAI-toolkit` child is.
  3. A toolkit folder has `modkit/` and `tools/toolkit_path.py`.
  4. Pin: the nearest `toolkit.version` walking up from the start folder; its first line that is not blank or
     a `#` comment is a commit SHA (7-40 hex characters, prefix allowed). It must match `git rev-parse HEAD` of
     the toolkit. A problem is a warning on stderr, or an error with --strict / D2R_TOOLKIT_STRICT=1.
     No toolkit.version, no check.

CLI: `py -3 toolkit_path.py [--from DIR] [--strict]` prints the path. Exit 1: no toolkit; exit 2: pin problem
under strict.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

TOOLKIT_DIRNAME = "d2rAI-toolkit"
PIN_FILE = "toolkit.version"
_SHA = re.compile(r"[0-9a-fA-F]{7,40}")


class ToolkitNotFound(Exception):
    pass


class PinMismatch(Exception):
    pass


def is_toolkit(d: Path) -> bool:
    return (d / "modkit").is_dir() and (d / "tools" / "toolkit_path.py").is_file()


def _levels(start: Path):
    yield start
    yield from start.parents


def find_toolkit_dir(start: Path | None = None, env: dict | None = None) -> Path:
    """Rules 1-3: the toolkit folder, or ToolkitNotFound."""
    env = os.environ if env is None else env
    start = Path(start or Path.cwd()).resolve()
    given = env.get("D2R_TOOLKIT")
    if given:
        p = Path(given)
        if is_toolkit(p):
            return p.resolve()
        raise ToolkitNotFound(f"D2R_TOOLKIT={given} is not a toolkit folder (needs modkit/ and tools/toolkit_path.py)")
    for level in _levels(start):
        for cand in (level, level / TOOLKIT_DIRNAME):
            if is_toolkit(cand):
                return cand
    raise ToolkitNotFound(f"{TOOLKIT_DIRNAME} not found from {start}: set D2R_TOOLKIT or put {TOOLKIT_DIRNAME} "
                          f"beside the project (or a parent folder of it)")


def _head(toolkit: Path) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(toolkit), "rev-parse", "HEAD"], capture_output=True, text=True)
    except OSError:
        return None
    out = r.stdout.strip()
    return out.lower() if r.returncode == 0 and out else None


def check_pin(start: Path, toolkit: Path) -> str | None:
    """Rule 4: a problem message, or None when the pin matches or there is no pin."""
    for level in _levels(Path(start).resolve()):
        f = level / PIN_FILE
        if f.is_file():
            break
    else:
        return None
    pin = next((s for s in (ln.strip() for ln in f.read_text(encoding="utf-8").splitlines())
                if s and not s.startswith("#")), "")
    if not _SHA.fullmatch(pin):
        return f"{f}: the first non-comment line must be a commit SHA (7-40 hex characters)"
    head = _head(toolkit)
    if head is None:
        return f"{f} pins {pin} but HEAD of {toolkit} could not be read"
    if not head.startswith(pin.lower()):
        return f"{f} pins {pin} but toolkit {toolkit} is at {head}"
    return None


def strict_from_env(env: dict | None = None) -> bool:
    return (os.environ if env is None else env).get("D2R_TOOLKIT_STRICT", "").lower() in ("1", "true", "yes", "on")


def find_toolkit(start: Path | None = None, strict: bool | None = None, env: dict | None = None) -> Path:
    """The toolkit folder. A pin problem warns on stderr, or raises PinMismatch when strict."""
    start = Path(start or Path.cwd())
    toolkit = find_toolkit_dir(start, env)
    problem = check_pin(start, toolkit)
    if problem:
        if strict_from_env(env) if strict is None else strict:
            raise PinMismatch(problem)
        print(f"warning: {problem}", file=sys.stderr)
    return toolkit


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Print the d2rAI-toolkit folder for a mod project.")
    ap.add_argument("--from", dest="start", default=None, help="start folder (default: current folder)")
    ap.add_argument("--strict", action="store_true", help="a pin problem is an error (or set D2R_TOOLKIT_STRICT=1)")
    a = ap.parse_args(argv)
    try:
        print(find_toolkit(Path(a.start) if a.start else None, True if a.strict else None))
    except ToolkitNotFound as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except PinMismatch as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
