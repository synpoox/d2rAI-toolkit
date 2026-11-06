# Run a Ghidra script from tools/ghidra_scripts against the analysed D2R project, or a PD2 one (read-only, no
# re-analysis), and print its output lines.
#   powershell -ExecutionPolicy Bypass -File tools/ghidra_query.ps1 <Script.java> [-Ghidra <dir>] [-Work <dir>]
#              [-Project D2R|PD2] [-Program <name>] [args...]
#   e.g.  tools/ghidra_query.ps1 Decompile.java 0x3e3f60      (writes <Work>\decomp\0x3e3f60.c)
#         tools/ghidra_query.ps1 Decompile.java -Project PD2 -Program D2Game.dll 0x6fc5e0a0
# -Ghidra: Ghidra install dir (env MODKIT_GHIDRA, default the newest C:\ghidra*\ or C:\ghidra\ghidra*\ install)
# -Work:   projects/dumps dir (env MODKIT_GHIDRA_WORK, default C:\ghidra-work); the project is
#          <Work>\project\D2R.gpr made by ghidra_analyze.ps1, the program the newest <Work>\D2RLoader_*_dump.exe.
# -Project PD2: <Work>\pd2-project\PD2.gpr instead (Project Diablo 2's DLLs); -Program picks one of its programs
#          (default ProjectDiablo.dll). -Program also overrides the D2R dump.
# Full Ghidra output: <Work>\query.log. The project must not be open in the Ghidra GUI (it is locked then).
param([Parameter(Mandatory = $true, Position = 0)][string]$Script,
      [string]$Ghidra = "",
      [string]$Work = "",
      [ValidateSet("D2R", "PD2")][string]$Project = "D2R",
      [string]$Program = "",
      [Parameter(ValueFromRemainingArguments = $true)][string[]]$ScriptArgs)
$ErrorActionPreference = 'Stop'
if (-not $Ghidra) { $Ghidra = if ($env:MODKIT_GHIDRA) { $env:MODKIT_GHIDRA } else { (@(Get-ChildItem "C:\ghidra*", "C:\ghidra\ghidra*" -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path (Join-Path $_.FullName "support\analyzeHeadless.bat") } | Sort-Object Name -Descending | ForEach-Object FullName) + "C:\ghidra")[0] } }
if (-not $Work) { $Work = if ($env:MODKIT_GHIDRA_WORK) { $env:MODKIT_GHIDRA_WORK } else { "C:\ghidra-work" } }
$headless = Join-Path $Ghidra "support\analyzeHeadless.bat"
# Keep settings (and the OSGi script cache) in the work dir: the default roaming folder can fail in Felix.
$env:_JAVA_OPTIONS = "-Dapplication.settingsdir=$(Join-Path $Work 'settings')"
if (-not (Test-Path $headless)) { throw "Ghidra not found: $headless (set -Ghidra or MODKIT_GHIDRA)" }
if ($Project -eq "PD2") {
    $projDir = Join-Path $Work "pd2-project"
    if (-not (Test-Path (Join-Path $projDir "PD2.gpr"))) { throw "no PD2 project in $projDir" }
    if (-not $Program) { $Program = "ProjectDiablo.dll" }
} else {
    $projDir = Join-Path $Work "project"
    if (-not (Test-Path (Join-Path $projDir "D2R.gpr"))) { throw "no D2R project in $projDir; run tools/ghidra_analyze.ps1 first" }
    if (-not $Program) {
        $dump = Get-ChildItem $Work -Filter "D2RLoader_*_dump.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if (-not $dump) { throw "no D2RLoader_*_dump.exe in $Work" }
        $Program = $dump.Name
    }
}
$log = Join-Path $Work "query.log"
$env:GHIDRA_HEADLESS_MAXMEM = "6G"
$argLine = @("`"$projDir`"", $Project, "-process", $Program, "-noanalysis", "-readOnly",
             "-scriptPath", "`"$(Join-Path $PSScriptRoot 'ghidra_scripts')`"", "-postScript", $Script) + $ScriptArgs
$p = Start-Process -FilePath $headless -ArgumentList $argLine -NoNewWindow `
    -Wait -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.err"
Get-Content $log | Where-Object { $_ -match "\.java> " } | ForEach-Object { $_ -replace '^.*?\.java> ', '' -replace '\s+\(GhidraScript\)\s*$', '' }
Get-Content $log | Where-Object { $_ -match "ERROR|Exception" } | Select-Object -First 5
exit $p.ExitCode
