# Finding the toolkit from a mod project

A mod project lives beside the toolkit (`<repos>/d2rAI-toolkit`, `<repos>/<mod>`), but agents often work in a git
worktree of the mod (`<repos>/<mod>/.claude/worktrees/<name>/`), or in a worktree of the toolkit itself. A
`../d2rAI-toolkit` guess breaks there. Three small finders share one set of rules, so Python, PowerShell and CMake
projects all land on the same folder.

| Language | File | Use |
|---|---|---|
| Python | `tools/toolkit_path.py` | `from toolkit_path import find_toolkit`, or the CLI `py -3 toolkit_path.py` (prints the path) |
| PowerShell | `tools/ToolkitPath.ps1` | dot-source it, then `Find-D2rToolkit` |
| CMake | `cmake/FindD2rToolkit.cmake` | `find_package(D2rToolkit)` sets `D2R_TOOLKIT_DIR` |

## The rules

1. **Environment variable.** If `D2R_TOOLKIT` is set it is used, and it must be a toolkit folder. If it is not, that is
   an error (no silent fallback).
2. **Walk up.** Start at the caller's folder (the current folder by default). At each level, going up to the drive
   root, take that level if it is itself a toolkit (the caller is inside the toolkit or one of its worktrees), else
   take its `d2rAI-toolkit` child if that is a toolkit. First hit wins, so a mod worktree finds the toolkit beside the
   main mod checkout, and a toolkit worktree returns itself.
3. **What a toolkit folder is:** it contains `modkit/` and `tools/toolkit_path.py`.
4. **Version pin** (below): checked after the folder is found.

Nothing found is an error that names the start folder and says to set `D2R_TOOLKIT`.

Relative paths (`--from`, `-From`, a relative `D2R_TOOLKIT`) are relative to the caller's current folder; in
PowerShell that is the PowerShell location (`Set-Location`), not the process folder. In CMake they are relative to
the source folder. The Python finder returns the resolved path (junctions and symlinks followed), PowerShell and
CMake return the path as walked, and CMake uses forward slashes; compare paths after normalising them.

## `toolkit.version`

A text file in the mod project root saying which toolkit commit the mod was built against. Blank lines and lines
starting with `#` are ignored; the first other line is the commit SHA (7 to 40 hex characters; a prefix is fine,
case does not matter) with nothing else on it.

```
# toolkit commit this mod expects
3f9c2ab41d
```

The finders use the nearest `toolkit.version` walking up from the start folder, and compare it with
`git rev-parse HEAD` of the found toolkit (the prefix must match). No `toolkit.version`: no check. The search is
bounded: it is skipped when the start folder is inside the toolkit (a pin belongs to a mod), and it stops at the
first folder that has a `.git` entry (file or folder, so a mod worktree still sees its own committed pin), so a
stray file above the project never applies. A folder named `toolkit.version` is ignored.

A problem is a pin mismatch, a first line that is not a SHA, an unreadable file, or a toolkit whose HEAD cannot be
read (not a git checkout, no `git`). By default it is a **warning** and the path is still returned. To make it an
**error** set `D2R_TOOLKIT_STRICT=1` (also `true`, `yes`, `on`) or pass the flag (`--strict`, `-Strict`,
`-DD2R_TOOLKIT_STRICT=1`); strict is on when either is on. Use strict in CI and releases.

**Writing the file.** All three finders read UTF-8 (with or without a byte-order mark) and UTF-16 with a byte-order
mark, so `echo <sha> > toolkit.version` in Windows PowerShell 5.1 (UTF-16) works. Plain ASCII is still the safest:

```
git -C <toolkit> rev-parse HEAD > toolkit.version                      # Git Bash
git -C <toolkit> rev-parse HEAD | Set-Content -Encoding ascii toolkit.version   # PowerShell
```

## Python

```python
import os, sys
sys.path.insert(0, os.environ["D2R_TOOLKIT"] + "/tools")   # the usual pattern: the variable gets you the finder
from toolkit_path import find_toolkit                      # find_toolkit(start=None, strict=None) -> Path
toolkit = find_toolkit()                                   # raises ToolkitNotFound / PinMismatch
```

Importing the finder needs the toolkit path, so a project with no `D2R_TOOLKIT` set calls the CLI instead (or
vendors the script): `py -3 <toolkit>\tools\toolkit_path.py [--from DIR] [--strict]` prints the path. Exit code 1:
no toolkit; 2: pin problem under `--strict`. Warnings go to stderr.

## PowerShell

```powershell
. "$env:D2R_TOOLKIT\tools\ToolkitPath.ps1"   # or the path you already know
$tk = Find-D2rToolkit                       # -From <dir>, -Strict
```

`Find-D2rToolkit` returns the path, throws when nothing is found (or on a pin problem with `-Strict` or
`D2R_TOOLKIT_STRICT`), and uses `Write-Warning` for a non-strict pin problem. Works in Windows PowerShell 5.1.

## CMake

A module cannot find itself before it is on `CMAKE_MODULE_PATH`, so the mod's `CMakeLists.txt` first locates the
toolkit's `cmake/` folder (the environment variable, else a walk up), then hands off to the module, which finds the
toolkit again, checks the pin and sets `D2R_TOOLKIT_DIR`:

```cmake
if(DEFINED ENV{D2R_TOOLKIT})
  list(APPEND CMAKE_MODULE_PATH "$ENV{D2R_TOOLKIT}/cmake")
else()
  set(_d "${CMAKE_CURRENT_SOURCE_DIR}")
  while(NOT EXISTS "${_d}/d2rAI-toolkit/cmake/FindD2rToolkit.cmake")
    get_filename_component(_p "${_d}" DIRECTORY)
    if(_p STREQUAL _d)
      message(FATAL_ERROR "d2rAI-toolkit not found: set D2R_TOOLKIT")
    endif()
    set(_d "${_p}")
  endwhile()
  list(APPEND CMAKE_MODULE_PATH "${_d}/d2rAI-toolkit/cmake")
endif()
find_package(D2rToolkit REQUIRED)
```

If a project cannot reach the toolkit before configuring, it can instead keep a copy of `FindD2rToolkit.cmake` in its
own `cmake/` folder (the module needs nothing from the toolkit), at the cost of the copy drifting from the toolkit's.

Optional input: `-DD2R_TOOLKIT_FROM=<dir>` sets the start folder (default `CMAKE_CURRENT_SOURCE_DIR`). A pin
problem is `message(WARNING)`, or `FATAL_ERROR` when strict.

## Tests

`tests/test_toolkit_finder.py` builds synthetic folder layouts (mod, mod worktree, toolkit, toolkit worktree) and
runs all three finders against each case: lookup order, worktrees, the environment variable, relative paths after
`Set-Location`, and the pin check (match, mismatch, encodings, bounded walk, strict precedence). The PowerShell and
CMake runs are skipped when those tools are not on PATH.
