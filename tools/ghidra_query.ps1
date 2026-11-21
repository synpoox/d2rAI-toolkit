# Run a Ghidra script from tools/ghidra_scripts against the analysed D2R project, or another named project from a
# config file (read-only, no re-analysis), and print its output lines.
#   powershell -ExecutionPolicy Bypass -File tools/ghidra_query.ps1 <Script.java> [-Ghidra <dir>] [-Work <dir>]
#              [-Project <name>] [-Program <name>] [args...]
#   e.g.  tools/ghidra_query.ps1 Decompile.java 0x3e3f60      (writes <Work>\decomp\0x3e3f60.c)
#         tools/ghidra_query.ps1 Decompile.java -Project mymod -Program Game.dll 0x6fc5e0a0
# -Ghidra: Ghidra install dir (env MODKIT_GHIDRA, default the newest C:\ghidra*\ or C:\ghidra\ghidra*\ install)
# -Work:   projects/dumps dir (env MODKIT_GHIDRA_WORK, default C:\ghidra-work); the D2R project is
#          <Work>\project\D2R.gpr made by ghidra_analyze.ps1, the program the newest <Work>\D2RLoader_*_dump.exe.
# -Project D2R (default) is built in and needs no config (a config entry named D2R is ignored; a warning
#          is printed when the config is read for another project).
#          Any other name is looked up in a JSON config file:
#          env MODKIT_GHIDRA_PROJECTS, default ~/.d2r-modkit/ghidra_projects.json (outside the repo). Format, a name
#          mapped to either a .gpr path or an object with the path and an optional default program:
#            { "mymod": "C:/ghidra-work/mymod-project/mymod.gpr",
#              "other": { "gpr": "D:/re/other.gpr", "program": "Game.dll" } }
#          The Ghidra project name is the .gpr file name without its extension. A leading ~ in the .gpr path
#          means the home folder; any other relative path is taken relative to -Work.
#          -Program picks the program inside the project (default: the entry's "program";
#          for D2R the newest dump). Names are case-insensitive.
# -Log:    the full Ghidra output file (default <Work>\query-logs\<script>-<time>-<pid>.log, one per run, so agents
#          querying at the same time never overwrite each other's output; logs older than a day are deleted).
# Ghidra lets one process open a project at a time: a query that finds it locked waits and retries (up to
# -LockWaitSeconds, default 600), so concurrent queries run one after another instead of failing.
# The project must not be open in the Ghidra GUI (it is locked then).
param([Parameter(Mandatory = $true, Position = 0)][string]$Script,
      [string]$Ghidra = "",
      [string]$Work = "",
      [string]$Project = "D2R",
      [string]$Program = "",
      [string]$Log = "",
      [int]$LockWaitSeconds = 600,
      [Parameter(ValueFromRemainingArguments = $true)][string[]]$ScriptArgs)
$ErrorActionPreference = 'Stop'
if (-not $Ghidra) { $Ghidra = if ($env:MODKIT_GHIDRA) { $env:MODKIT_GHIDRA } else { (@(Get-ChildItem "C:\ghidra*", "C:\ghidra\ghidra*" -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path (Join-Path $_.FullName "support\analyzeHeadless.bat") } | Sort-Object Name -Descending | ForEach-Object FullName) + "C:\ghidra")[0] } }
if (-not $Work) { $Work = if ($env:MODKIT_GHIDRA_WORK) { $env:MODKIT_GHIDRA_WORK } else { "C:\ghidra-work" } }
$headless = Join-Path $Ghidra "support\analyzeHeadless.bat"
# Keep settings (and the OSGi script cache) in the work dir: the default roaming folder can fail in Felix.
$env:_JAVA_OPTIONS = "-Dapplication.settingsdir=$(Join-Path $Work 'settings')"
if (-not (Test-Path $headless)) { throw "Ghidra not found: $headless (set -Ghidra or MODKIT_GHIDRA)" }
if ($Project -ne "D2R") {
    $cfg = if ($env:MODKIT_GHIDRA_PROJECTS) { $env:MODKIT_GHIDRA_PROJECTS } else { Join-Path $HOME ".d2r-modkit\ghidra_projects.json" }
    if (-not (Test-Path $cfg)) { throw "unknown project '$Project': no config file $cfg (see the header of this script)" }
    $entry = $null
    $props = (Get-Content $cfg -Raw | ConvertFrom-Json).PSObject.Properties
    if ($props | Where-Object { $_.Name -ieq "D2R" }) { Write-Warning "${cfg}: an entry named D2R is ignored; the built-in D2R project is always used for -Project D2R" }
    foreach ($prop in $props) { if ($prop.Name -ieq $Project) { $entry = $prop.Value } }
    if ($null -eq $entry) { throw "project '$Project' is not listed in $cfg" }
    $gpr = if ($entry -is [string]) { $entry } else { $entry.gpr }
    if (-not $gpr) { throw "project '$Project' in $cfg has no .gpr path" }
    if ($gpr -match '^~([\\/]|$)') { $gpr = Join-Path $HOME $gpr.Substring(1).TrimStart('\', '/') }
    if (-not [IO.Path]::IsPathRooted($gpr)) { $gpr = Join-Path $Work $gpr }
    if (-not (Test-Path $gpr)) { throw "no Ghidra project file $gpr (project '$Project' in $cfg)" }
    $projDir = Split-Path -Parent $gpr
    $projName = [IO.Path]::GetFileNameWithoutExtension($gpr)
    if (-not $Program -and $entry -isnot [string] -and $entry.program) { $Program = $entry.program }
    if (-not $Program) { throw "project '$Project': pass -Program or give the config entry a 'program'" }
} else {
    $projDir = Join-Path $Work "project"
    $projName = "D2R"
    if (-not (Test-Path (Join-Path $projDir "D2R.gpr"))) { throw "no D2R project in $projDir; run tools/ghidra_analyze.ps1 first" }
    if (-not $Program) {
        $dump = Get-ChildItem $Work -Filter "D2RLoader_*_dump.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if (-not $dump) { throw "no D2RLoader_*_dump.exe in $Work" }
        $Program = $dump.Name
    }
}
$log = $Log
if (-not $log) {
    $logDir = Join-Path $Work "query-logs"
    New-Item -ItemType Directory -Force $logDir | Out-Null
    Get-ChildItem $logDir -File -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-1) } |
        Remove-Item -Force -ErrorAction SilentlyContinue
    $log = Join-Path $logDir ("{0}-{1:yyyyMMdd-HHmmss}-{2}.log" -f [IO.Path]::GetFileNameWithoutExtension($Script), (Get-Date), $PID)
}
$env:GHIDRA_HEADLESS_MAXMEM = "6G"
$argLine = @("`"$projDir`"", "`"$projName`"", "-process", "`"$Program`"", "-noanalysis", "-readOnly",
             "-scriptPath", "`"$(Join-Path $PSScriptRoot 'ghidra_scripts')`"", "-postScript", $Script) + $ScriptArgs
$deadline = (Get-Date).AddSeconds($LockWaitSeconds)
while ($true) {
    $p = Start-Process -FilePath $headless -ArgumentList $argLine -NoNewWindow `
        -Wait -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.err"
    if (-not (Select-String -Path $log -Pattern "Unable to lock project" -Quiet) -or (Get-Date) -gt $deadline) { break }
    Write-Host "ghidra_query: project locked by another query, retrying in 5 s"
    Start-Sleep -Seconds 5
}
Get-Content $log | Where-Object { $_ -match "\.java> " } | ForEach-Object { $_ -replace '^.*?\.java> ', '' -replace '\s+\(GhidraScript\)\s*$', '' }
Get-Content $log | Where-Object { $_ -match "ERROR|Exception" } | Select-Object -First 5
exit $p.ExitCode
