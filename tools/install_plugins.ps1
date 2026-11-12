# Installs a mod's built plugins into a D2R folder (a test slot or a frozen install copy), and optionally the mod
# project's data. The game must be closed. Never run it against a game folder you have not named: -Game is required.
#   powershell -ExecutionPolicy Bypass -File tools\install_plugins.ps1 -Game <slot> -Project <mod> -Plugins my-rules,my-ui
#   powershell -ExecutionPolicy Bypass -File tools\install_plugins.ps1 -Game <slot> -Project <mod> -Plugins my-rules -Data
#
# Plugins are game-wide: <Game>\d2rloader\plugins\. Each name in -Plugins is copied from
# <Project>\<BuildDir>\<name>.dll (BuildDir defaults to plugin\build\Release). Files in that folder that are neither
# those plugins nor named in -Keep are strays (third-party plugins, other mods' companions): they are MOVED to a
# backup folder, never deleted, so a test runs on a clean install. -KeepExtras leaves them alone (a slot set up on
# purpose). The backup folder is -BackupDir, else $env:MODKIT_BACKUPS, else ~\.d2r-modkit\stray-plugins.
#
# -Data builds and installs the project's data with this toolkit's `modkit build` and `modkit install`, then puts back
# each modinfo.json savepath, because modkit install resets it (a slot would otherwise play other saves). A test slot
# of the testing config installs through testing\slot_install.py instead (modkit install refuses slots): set
# MODKIT_TESTING_CONFIG, and MODKIT_RUN to the owner of the slot lock. -NoValidate builds past validation errors.
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
$Game = (Resolve-Path -LiteralPath $Game).Path
$Project = (Resolve-Path -LiteralPath $Project).Path
if (-not (Test-Path -LiteralPath (Join-Path $Game "D2R.exe"))) { throw "$Game is not a D2R folder" }
if (Get-Process D2R, D2RLoader -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path.StartsWith($Game, 'OrdinalIgnoreCase') }) {
    throw "the game is running from ${Game}: close it first"
}

$pluginDir = Join-Path $Game "d2rloader\plugins"
New-Item -ItemType Directory -Force $pluginDir | Out-Null
foreach ($name in $Plugins) {
    $dll = Join-Path $Project (Join-Path $BuildDir "$name.dll")
    if (-not (Test-Path -LiteralPath $dll)) { throw "$dll missing: build the plugin first" }
}
foreach ($name in $Plugins) {
    Copy-Item -LiteralPath (Join-Path $Project (Join-Path $BuildDir "$name.dll")) $pluginDir -Force
    Write-Output "installed $name.dll -> $pluginDir"
}

# Strays would make a test run on an unclean install: move, never delete.
$ours = @($Plugins | ForEach-Object { "$_.dll" }) + $Keep
$strays = @(Get-ChildItem -LiteralPath $pluginDir -Force | Where-Object { $ours -notcontains $_.Name })
if ($strays.Count -and -not $KeepExtras) {
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

if ($Data) {
    $mod = (Get-Content -LiteralPath (Join-Path $Project "mod.json") -Raw | ConvertFrom-Json).name
    $root = Join-Path $Game "mods\$mod"
    $modinfos = @((Join-Path $root "modinfo.json"), (Join-Path $root "$mod.mpq\modinfo.json"))
    $saved = @{}
    foreach ($f in $modinfos) { if (Test-Path -LiteralPath $f) { $saved[$f] = (Get-Content -LiteralPath $f -Raw | ConvertFrom-Json).savepath } }
    Push-Location $Toolkit
    try {
        if ($NoValidate) { py -3 -m modkit build $Project --no-validate } else { py -3 -m modkit build $Project }
        if ($LASTEXITCODE -ne 0) { throw "modkit build failed ($LASTEXITCODE)" }
        # modkit install refuses a test slot of the testing config, so a slot goes through slot_install.py, which sets
        # the slot's own savepath and needs the slot lock held by MODKIT_RUN.
        $slot = py -3 -c "import sys; from pathlib import Path; from modkit.install import configured_slot; print(configured_slot(Path(sys.argv[1])) or '')" $Game
        if ($LASTEXITCODE -ne 0) { throw "reading the testing config failed ($LASTEXITCODE)" }
        if ($slot) {
            if (-not $env:MODKIT_RUN) { throw "$Game is test slot ${slot}: set MODKIT_RUN to the owner of its lock (testing\game_slots.py lock $slot <owner>)" }
            py -3 testing\slot_install.py --slot $slot $Project
            if ($LASTEXITCODE -ne 0) { throw "slot_install failed ($LASTEXITCODE)" }
            $saved = @{}  # slot_install wrote the slot's savepath
        } else {
            py -3 -m modkit --game $Game install $Project
            if ($LASTEXITCODE -ne 0) { throw "modkit install failed ($LASTEXITCODE)" }
        }
    } finally { Pop-Location }
    foreach ($f in $saved.Keys) {
        $info = Get-Content -LiteralPath $f -Raw | ConvertFrom-Json
        $info.savepath = $saved[$f]
        [IO.File]::WriteAllText($f, ($info | ConvertTo-Json))  # UTF-8 without a BOM, as modkit writes it
        Write-Output "savepath kept: $($saved[$f]) in $f"
    }
}
