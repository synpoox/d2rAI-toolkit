# Tests tools\worktree_remove.ps1 inside a throwaway repository (own bare origin, clone and scratch junction targets).
# It never touches the toolkit's own worktrees or any real cache.
#   powershell -ExecutionPolicy Bypass -File tests\tools\worktree_remove_test.ps1
$ErrorActionPreference = 'Stop'
$script = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'tools\worktree_remove.ps1'
$scratch = Join-Path ([IO.Path]::GetTempPath()) ("wtr-test-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory $scratch | Out-Null
function G { $ErrorActionPreference = 'Continue'; & git -c user.name=t -c user.email=t@example.invalid @args 2>&1 | Out-Null }
$origin = Join-Path $scratch 'origin.git'; $repo = Join-Path $scratch 'clone'
G init -q --bare -b main $origin
G clone -q $origin $repo
G -C $repo commit -q --allow-empty -m base
G -C $repo branch -M main
G -C $repo push -q -u origin main
$fail = 0
function Check([string]$name, [bool]$ok) { if ($ok) { Write-Host "PASS $name" } else { Write-Host "FAIL $name"; $script:fail++ } }
function Run([string[]]$a) {
    $ErrorActionPreference = 'Continue'
    $out = & powershell -NoProfile -ExecutionPolicy Bypass -File $script @a 2>&1 | Out-String
    [pscustomobject]@{ Code = $LASTEXITCODE; Out = $out }
}
function NewWt([string]$name, [string]$start = 'origin/main') {
    $p = Join-Path $scratch $name
    & git -C $repo worktree add -q -b "scratch/$name" $p $start
    $p
}

try {
    # Refusals
    $main = ((& git -C $repo worktree list --porcelain | Select-Object -First 1) -replace '^worktree ', '')
    $r = Run @('-Path', $main); Check 'refuses main checkout' ($r.Code -ne 0 -and $r.Out -match 'main checkout')
    $r = Run @('-Path', $scratch); Check 'refuses non-worktree' ($r.Code -ne 0 -and $r.Out -match 'not a worktree')
    $wt = NewWt 'dirty'
    Set-Content (Join-Path $wt 'untracked.txt') 'x'
    $r = Run @('-Path', $wt)
    Check 'refuses dirty worktree and lists it' ($r.Code -ne 0 -and $r.Out -match 'untracked.txt' -and (Test-Path $wt))
    $r = Run @('-Path', $wt, '-Force'); Check '-Force removes dirty worktree' ($r.Code -eq 0 -and -not (Test-Path $wt))
    & git -C $repo branch -D scratch/dirty | Out-Null

    # Junctions: top-level and nested, targets must survive.
    $target = Join-Path $scratch 'target'; New-Item -ItemType Directory $target | Out-Null
    Set-Content (Join-Path $target 'keep.txt') 'keep'
    $target2 = Join-Path $scratch 'target2'; New-Item -ItemType Directory $target2 | Out-Null
    Set-Content (Join-Path $target2 'keep2.txt') 'keep2'
    $wt = NewWt 'links'
    G -C $wt commit -q --allow-empty -m scratch
    New-Item -ItemType Junction -Path (Join-Path $wt 'cache-data') -Target $target | Out-Null
    New-Item -ItemType Directory (Join-Path $wt 'sub\deep') -Force | Out-Null
    New-Item -ItemType Junction -Path (Join-Path $wt 'sub\deep\nested') -Target $target2 | Out-Null
    $r = Run @('-Path', $wt, '-DeleteBranch')  # no -Force: junctions alone do not make a worktree dirty
    Write-Host $r.Out
    Check 'removal succeeds' ($r.Code -eq 0)
    Check 'worktree is gone' (-not (Test-Path $wt))
    Check 'junction target survives' (Test-Path (Join-Path $target 'keep.txt'))
    Check 'nested junction target survives' (Test-Path (Join-Path $target2 'keep2.txt'))
    Check 'nested junction reported' ($r.Out -match 'unlinked .*nested')
    Check 'worktree no longer listed' (-not ((& git -C $repo worktree list) -match 'links'))
    Check 'unmerged branch kept' ($r.Out -match 'kept branch' -and (& git -C $repo branch --list 'scratch/links'))

    # Junction plus a real untracked file: still refused, nothing unlinked.
    $wt = NewWt 'linkdirty'
    New-Item -ItemType Junction -Path (Join-Path $wt 'cache-data') -Target $target | Out-Null
    Set-Content (Join-Path $wt 'real-work.txt') 'x'
    $r = Run @('-Path', $wt)
    Check 'junction plus untracked file is refused and lists only the file' ($r.Code -ne 0 -and $r.Out -match 'real-work.txt' -and $r.Out -notmatch '\?\? cache-data' -and (Test-Path (Join-Path $wt 'cache-data\keep.txt')))
    cmd /c rmdir (Join-Path $wt 'cache-data')
    & git -C $repo worktree remove --force $wt

    # Submodule with a junction inside it, removed from a relative path.
    $subOrigin = Join-Path $scratch 'sub.git'; $subSrc = Join-Path $scratch 'subsrc'
    G init -q --bare -b main $subOrigin
    G clone -q $subOrigin $subSrc
    G -C $subSrc commit -q --allow-empty -m subbase
    G -C $subSrc branch -M main
    G -C $subSrc push -q -u origin main
    G -C $repo -c protocol.file.allow=always submodule add -q $subOrigin libsub
    G -C $repo commit -q -m 'add submodule'
    G -C $repo push -q origin main
    $wt = NewWt 'withsub'
    G -C $wt -c protocol.file.allow=always submodule update --init -q
    New-Item -ItemType Junction -Path (Join-Path $wt 'libsub\cache-data') -Target $target | Out-Null
    $r = Run @('-Path', $wt, '-Force')
    Write-Host $r.Out
    Check 'worktree with an initialized submodule is removed' ($r.Code -eq 0 -and -not (Test-Path $wt))
    Check 'junction inside the submodule leaves its target intact' (Test-Path (Join-Path $target 'keep.txt'))

    # Relative -Path resolves against the caller's directory.
    $wt = NewWt 'relative'
    $oldCwd = [Environment]::CurrentDirectory
    Push-Location $scratch; [Environment]::CurrentDirectory = $scratch
    try { $r = Run @('-Path', '.\relative') } finally { Pop-Location; [Environment]::CurrentDirectory = $oldCwd }
    Check 'relative path is resolved against the current directory' ($r.Code -eq 0 -and -not (Test-Path $wt))

    # Locked: refused before anything is touched, and not unlocked.
    $wt = NewWt 'locked'
    New-Item -ItemType Junction -Path (Join-Path $wt 'cache-data') -Target $target | Out-Null
    & git -C $repo worktree lock --reason 'live agent' $wt
    $r = Run @('-Path', $wt)
    Check 'refuses locked worktree' ($r.Code -ne 0 -and $r.Out -match 'locked')
    Check 'locked worktree untouched (junction kept, still locked)' ((Test-Path (Join-Path $wt 'cache-data\keep.txt')) -and ((& git -C $repo worktree list --porcelain) -match '^locked'))
    & git -C $repo worktree unlock $wt
    cmd /c rmdir (Join-Path $wt 'cache-data')
    & git -C $repo worktree remove --force $wt

    # Nested worktree: refused, both stay.
    $outer = NewWt 'outer'
    $inner = Join-Path $outer 'inner'
    & git -C $repo worktree add -q -b scratch/inner $inner origin/main
    $r = Run @('-Path', $outer)
    Check 'refuses a target containing another worktree' ($r.Code -ne 0 -and $r.Out -match 'contains another worktree' -and (Test-Path $inner))
    & git -C $repo worktree remove --force $inner
    & git -C $repo worktree remove --force $outer

    # Branch rule: tip in origin/main -> deleted; tip with a commit past it and no merged PR -> kept.
    $wt = NewWt 'merged'
    $r = Run @('-Path', $wt, '-DeleteBranch')
    Check 'branch whose tip is in origin/main is deleted' ($r.Code -eq 0 -and $r.Out -match 'deleted local branch' -and -not (& git -C $repo branch --list 'scratch/merged'))
    $wt = NewWt 'ahead'
    G -C $wt commit -q --allow-empty -m 'after merge'
    $r = Run @('-Path', $wt, '-DeleteBranch')
    Check 'branch with a commit past origin/main is kept' ($r.Code -eq 0 -and $r.Out -match 'kept branch' -and (& git -C $repo branch --list 'scratch/ahead'))
} finally {
    & git -C $repo worktree prune
    foreach ($b in (& git -C $repo branch --list 'scratch/*' --format '%(refname:short)')) { & git -C $repo branch -D $b | Out-Null }
    cmd /c rmdir /s /q $scratch 2>$null
}
if ($fail) { Write-Host "$fail failed"; exit 1 } else { Write-Host 'all passed' }
