# Finding the toolkit from a mod project

A mod project lives beside the toolkit (`<repos>/d2rAI-toolkit`, `<repos>/<mod>`), but agents often work in a git
worktree of the mod (`<repos>/<mod>/.claude/worktrees/<name>/`), or in a worktree of the toolkit itself. A
`../d2rAI-toolkit` guess breaks there. Three small finders share one set of rules, so Python, PowerShell and CMake
projects all land on the same folder.

| Language | File | Use |
|---|---|---|
| Python | `tools/toolkit_path.py` | `from toolkit_path import find_toolkit`, or the CLI `py -3 toolkit_path.py` (prints the path) |
| PowerShell | `tools/ToolkitPath.ps1` | dot-source it, then `Find-D2rToolkit` |
| CMake | `cmake/FindD2rToolkit.cmake` | `find_package(D2rToolkit REQUIRED)` sets `D2R_TOOLKIT_DIR` |

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

## `toolkit.version`

A text file in the mod project root saying which toolkit commit the mod was built against. Blank lines and lines
starting with `#` are ignored; the first other line is the commit SHA (7 to 40 hex characters; a prefix is fine,
case does not matter). Anything after it is ignored.

```
# toolkit commit this mod expects
3f9c2ab41d
```

The finders use the nearest `toolkit.version` walking up from the start folder, and compare it with
`git rev-parse HEAD` of the found toolkit (the prefix must match). No `toolkit.version`: no check.

A problem is a pin mismatch, a first line that is not a SHA, or a toolkit whose HEAD cannot be read (not a git
checkout, no `git`). By default it is a **warning** and the path is still returned. To make it an **error** set
`D2R_TOOLKIT_STRICT=1` (also `true`, `yes`, `on`) or pass the flag below. Use strict in CI and releases.

To move the pin, check out the commit in the toolkit and write `git rev-parse HEAD` into the file.

## Python

```python
import sys
sys.path.insert(0, "<toolkit>/tools")      # or run the CLI first, see below
from toolkit_path import find_toolkit      # find_toolkit(start=None, strict=None) -> Path
toolkit = find_toolkit()                   # raises ToolkitNotFound / PinMismatch
```

The CLI needs no import: `py -3 <toolkit>\tools\toolkit_path.py [--from DIR] [--strict]` prints the path.
Exit code 1: no toolkit; 2: pin problem under `--strict`. Warnings go to stderr.

A project that has no toolkit path yet can bootstrap with the environment variable (rule 1) and then call the CLI
through it: `py -3 "$env:D2R_TOOLKIT\tools\toolkit_path.py"`.

## PowerShell

```powershell
. "$env:D2R_TOOLKIT\tools\ToolkitPath.ps1"   # or the path you already know
$tk = Find-D2rToolkit                       # -From <dir>, -Strict
```

`Find-D2rToolkit` returns the path, throws when nothing is found (or on a pin problem with `-Strict` or
`D2R_TOOLKIT_STRICT`), and uses `Write-Warning` for a non-strict pin problem. Works in Windows PowerShell 5.1.

## CMake

`FindD2rToolkit.cmake` has no dependency on the toolkit, so a mod can keep a copy in its own `cmake/` folder, or
point at the toolkit's through `D2R_TOOLKIT`:

```cmake
list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")   # where the copy lives
find_package(D2rToolkit REQUIRED)
add_subdirectory("${D2R_TOOLKIT_DIR}/plugin-template" plugin-template)   # for example
```

Optional inputs: `-DD2R_TOOLKIT_FROM=<dir>` sets the start folder (default `CMAKE_CURRENT_SOURCE_DIR`), and
`D2R_TOOLKIT_STRICT` works as an environment variable or a cache variable. A pin problem is `message(WARNING)`, or
`FATAL_ERROR` when strict.

## Tests

`tests/test_toolkit_finder.py` builds synthetic folder layouts (mod, mod worktree, toolkit, toolkit worktree) and
runs all three finders against each case: lookup order, worktrees, the environment variable, and the pin check. The
PowerShell and CMake runs are skipped when those tools are not on PATH.
