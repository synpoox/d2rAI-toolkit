# Find the d2rAI-toolkit checkout from a mod project, and check the mod's toolkit.version pin.
# Same rules as tools/toolkit_path.py and cmake/FindD2rToolkit.cmake; see docs/toolkit-finder.md.
#   . <toolkit>\tools\ToolkitPath.ps1 ; $tk = Find-D2rToolkit            # or: Find-D2rToolkit -From <dir> -Strict
# Returns the path. Throws if no toolkit is found, or on a pin problem with -Strict / D2R_TOOLKIT_STRICT=1
# (otherwise a pin problem is a warning).

function Test-D2rToolkitDir([string]$Dir) {
    (Test-Path -LiteralPath (Join-Path $Dir 'modkit') -PathType Container) -and
    (Test-Path -LiteralPath (Join-Path $Dir 'tools\toolkit_path.py') -PathType Leaf)
}

function Find-D2rToolkit {
    param([string]$From = (Get-Location).Path, [switch]$Strict)
    $start = [System.IO.Path]::GetFullPath($From)
    $strictOn = $Strict -or (@('1', 'true', 'yes', 'on') -contains "$env:D2R_TOOLKIT_STRICT".ToLower())

    $toolkit = $null
    if ($env:D2R_TOOLKIT) {
        if (-not (Test-D2rToolkitDir $env:D2R_TOOLKIT)) {
            throw "D2R_TOOLKIT=$($env:D2R_TOOLKIT) is not a toolkit folder (needs modkit/ and tools/toolkit_path.py)"
        }
        $toolkit = [System.IO.Path]::GetFullPath($env:D2R_TOOLKIT)
    } else {
        for ($lv = $start; $lv; $lv = Split-Path -Parent $lv) {
            foreach ($c in @($lv, (Join-Path $lv 'd2rAI-toolkit'))) {
                if (Test-D2rToolkitDir $c) { $toolkit = $c; break }
            }
            if ($toolkit) { break }
        }
        if (-not $toolkit) {
            throw "d2rAI-toolkit not found from ${start}: set D2R_TOOLKIT or put d2rAI-toolkit beside the project (or a parent folder of it)"
        }
    }

    $pinFile = $null
    for ($lv = $start; $lv; $lv = Split-Path -Parent $lv) {
        $f = Join-Path $lv 'toolkit.version'
        if (Test-Path -LiteralPath $f -PathType Leaf) { $pinFile = $f; break }
    }
    if ($pinFile) {
        $pin = @(Get-Content -LiteralPath $pinFile | ForEach-Object { $_.Trim() } |
                 Where-Object { $_ -and -not $_.StartsWith('#') })[0]
        $problem = $null
        if (-not $pin -or $pin -notmatch '^[0-9a-fA-F]{7,40}$') {
            $problem = "${pinFile}: the first non-comment line must be a commit SHA (7-40 hex characters)"
        } else {
            $head = $null
            try { $head = (& git -C $toolkit rev-parse HEAD 2>$null); if ($LASTEXITCODE -ne 0) { $head = $null } } catch { $head = $null }
            if (-not $head) { $problem = "$pinFile pins $pin but HEAD of $toolkit could not be read" }
            else {
                $head = "$head".Trim().ToLower()
                if (-not $head.StartsWith($pin.ToLower())) { $problem = "$pinFile pins $pin but toolkit $toolkit is at $head" }
            }
        }
        if ($problem) {
            if ($strictOn) { throw $problem }
            Write-Warning $problem
        }
    }
    $toolkit
}
