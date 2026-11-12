# Installs a mod's built plugins into a TEST SLOT of the testing config, and optionally the mod project's data. The
# game must be closed. -Game is required and must be a configured test slot (slot 2 and up, MODKIT_TESTING_CONFIG):
# the script never touches slot 1 or the real install (CLAUDE.md rule 8). The slot lock must be held by MODKIT_RUN
# (testing\game_slots.py lock <n> <owner>); this is checked first, on every run, before anything is copied or moved.
#   powershell -ExecutionPolicy Bypass -File tools\install_plugins.ps1 -Game <slot> -Project <mod> -Plugins my-rules,my-ui
#   powershell -ExecutionPolicy Bypass -File tools\install_plugins.ps1 -Game <slot> -Project <mod> -Plugins my-rules -Data
#
# Plugins are mod-scoped: <Game>\mods\<Mod>\d2rloader\plugins\ (<Mod> is mod.json's name), as `modkit install` puts
# them. Each name in -Plugins is taken from <Project>\<BuildDir>\<name>.dll (BuildDir defaults to plugin\build\Release).
# With -Data, `modkit build` runs first and testing\slot_install.py (which calls `modkit install`, and so copies the
# mod.json "plugins" and sets the slot's own savepath) installs the data and those plugins; a -Plugins name that
# mod.json does not list is copied afterwards. Without -Data the DLLs are copied directly.
# The game version must be 3.3 (major.minor, never the build number); a D2R.exe without a version resource only warns.
#
# Strays are MOVED to a backup folder, never deleted: files in the mod's plugin folder that are not ours, and copies of
# OUR DLL names in the game-wide <Game>\d2rloader\plugins (they would load with every mod and hook twice). Ours are the
# -Plugins and mod.json plugins, their <name>-off.txt toggles and <name>.* data files, and anything named in -Keep.
# -KeepExtras leaves other files alone. The backup folder is -BackupDir, else $env:MODKIT_BACKUPS, else
# ~\.d2r-modkit\stray-plugins (outside the slot and the repo; tests always pass -BackupDir). -NoValidate builds past validation errors.
param(
    [Parameter(Mandatory)] [string]$Game,
    [string]$Project = ".",
    [Parameter(Mandatory)] [string[]]$Plugins,
    [string]$BuildDir = "plugin\build\Release",
    [string[]]$Keep = @(),
    [string]$BackupDir = "",
    [switch]$Data,
    [switch]$NoValidate,
    [switch]$KeepExtras
)
$ErrorActionPreference = 'Stop'
$Toolkit = Split-Path $PSScriptRoot -Parent
# with -File a comma list arrives as one string: accept both forms
$Plugins = @($Plugins | ForEach-Object { $_ -split ',' } | Where-Object { $_ })
$Keep = @($Keep | ForEach-Object { $_ -split ',' } | Where-Object { $_ })
$Game = (Resolve-Path -LiteralPath $Game).Path.TrimEnd('\')
$Project = (Resolve-Path -LiteralPath $Project).Path
$exe = Join-Path $Game "D2R.exe"
if (-not (Test-Path -LiteralPath $exe)) { throw "$Game is not a D2R folder" }

# 1. Gate, before anything is changed: a configured test slot (never slot 1 or the real install), the lock held by
#    MODKIT_RUN, no game running in it; then the game version.
$gate = @'
import sys
from pathlib import Path
toolkit = sys.argv[1]
sys.path[:0] = [toolkit, toolkit + "/testing", toolkit + "/release"]
from modkit.install import configured_slot
game = Path(sys.argv[2])
slot = configured_slot(game)
if not slot:
    print(f"refused: {game} is not a test slot (2 and up) of the testing config: set MODKIT_TESTING_CONFIG; this tool never touches slot 1 or the real install")
    sys.exit(2)
import testing_config as tc
import release_install
try:
    release_install.check_slot(tc.load(tc.find_config_path()), slot)
except (release_install.ReleaseError, tc.ConfigError) as e:
    print(f"refused: {e}")
    sys.exit(2)
import publish_release
print(f"slot={slot}")
print(f"version={publish_release.exe_version(game / 'D2R.exe')}")
'@
$out = @($gate | py -3 - $Toolkit $Game)   # via stdin: PowerShell 5.1 strips double quotes from native arguments
if ($LASTEXITCODE -ne 0) { throw ($out -join "`n") }
$slot = ($out | Where-Object { $_ -like 'slot=*' }) -replace '^slot=', ''
$version = ($out | Where-Object { $_ -like 'version=*' }) -replace '^version=', ''
if (-not $version) {
    Write-Warning "$exe has no version resource: cannot check the game version (expected 3.3)"
} else {
    $mm = ($version -split '\.')[0..1] -join '.'
    if ($mm -ne '3.3') { throw "D2R.exe is version ${version}: this toolkit targets 3.3 (major.minor); refusing" }
}

# 2. Exact folder match (slot1 must not match slot10); a process whose path cannot be read counts as maybe running.
$prefix = $Game + '\'
foreach ($p in @(Get-Process D2R, D2RLoader -ErrorAction SilentlyContinue)) {
    if (-not $p.Path) { throw "cannot read the path of process $($p.Name) ($($p.Id)): it may be running from ${Game}; close the game or run elevated" }
    if ($p.Path.StartsWith($prefix, 'OrdinalIgnoreCase')) { throw "the game is running from ${Game}: close it first" }
}

$mod = (Get-Content -LiteralPath (Join-Path $Project "mod.json") -Raw | ConvertFrom-Json)
$modName = $mod.name
if (-not $modName -or $modName -match '[\\/]|\.\.') { throw "mod.json has no usable name (empty, or with a path separator or '..'): $modName" }
$modPlugins = @($mod.plugins | Where-Object { $_ } | ForEach-Object { [IO.Path]::GetFileNameWithoutExtension($_) })
$pluginDir = Join-Path $Game "mods\$modName\d2rloader\plugins"
$globalDir = Join-Path $Game "d2rloader\plugins"
foreach ($name in $Plugins) {
    $dll = Join-Path $Project (Join-Path $BuildDir "$name.dll")
    if (-not (Test-Path -LiteralPath $dll)) { throw "$dll missing: build the plugin first" }
}

# 3. Build before copying DLLs, so a failed build leaves the slot as it was.
if ($Data) {
    Push-Location $Toolkit
    try {
        if ($NoValidate) { py -3 -m modkit build $Project --no-validate } else { py -3 -m modkit build $Project }
        if ($LASTEXITCODE -ne 0) { throw "modkit build failed ($LASTEXITCODE)" }
        py -3 testing\slot_install.py --slot $slot $Project   # runs modkit install: mod.json plugins, the slot's savepath
        if ($LASTEXITCODE -ne 0) { throw "slot_install failed ($LASTEXITCODE)" }
    } finally { Pop-Location }
}
New-Item -ItemType Directory -Force $pluginDir | Out-Null
foreach ($name in $Plugins) {
    $dest = Join-Path $pluginDir "$name.dll"
    if ($Data -and ($modPlugins -contains $name)) { Write-Output "$name.dll installed by modkit install -> $pluginDir"; continue }
    Copy-Item -LiteralPath (Join-Path $Project (Join-Path $BuildDir "$name.dll")) $dest -Force
    Write-Output "installed $name.dll -> $pluginDir"
}

# 4. Strays would make a test run on an unclean install: move, never delete.
$names = @($Plugins) + $modPlugins | Select-Object -Unique
$ours = @($names | ForEach-Object { "$_.dll"; "$_-off.txt" }) + $Keep
function Test-Ours($f) {
    if ($ours -contains $f.Name) { return $true }
    foreach ($n in $names) { if ($f.Name -like "$n.*") { return $true } }   # the plugin's own config and log files
    return $false
}
$strays = @()
if (-not $KeepExtras) {
    $strays += @(Get-ChildItem -LiteralPath $pluginDir -Force | Where-Object { -not (Test-Ours $_) })
}
if (Test-Path -LiteralPath $globalDir) {   # a copy of our DLLs game-wide would load with every mod and hook twice
    $strays += @(Get-ChildItem -LiteralPath $globalDir -Force -File | Where-Object { $_.Extension -eq '.dll' -and ($names | ForEach-Object { "$_.dll" }) -contains $_.Name })
}
if ($strays.Count) {
    if (-not $BackupDir) { $BackupDir = $env:MODKIT_BACKUPS }
    if (-not $BackupDir) { $BackupDir = Join-Path $HOME ".d2r-modkit\stray-plugins" }
    $backup = Join-Path (Join-Path $BackupDir (Get-Date -Format yyyy-MM-dd)) (Split-Path $Game -Leaf)
    New-Item -ItemType Directory -Force $backup | Out-Null
    foreach ($f in $strays) {
        $dest = Join-Path $backup $f.Name
        if (Test-Path -LiteralPath $dest) { $dest = Join-Path $backup "$($f.BaseName)-$(Get-Date -Format HHmmss)$($f.Extension)" }
        Move-Item -LiteralPath $f.FullName $dest
        Write-Output "moved stray $($f.Name) -> $dest"
    }
}
