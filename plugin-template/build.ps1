# Configures and builds the D2RLoader plugin (Visual Studio generator, x64, Release).
#   powershell -ExecutionPolicy Bypass -File build.ps1 [-Source <dir>] [-Name mod-core] [-Mod <mod folder>] [-SoundRows <n>] [-Build <dir>] [-Sdk <dir>] [-Toolkit <dir>] [-Tests]
# Several plugins in one project: pass all their ids to -Name (-Name a,b; under -File the comma list arrives as one string
# and is split here); the first is the template's own plugin id, the project's CMakeLists.txt adds the others with
# modkit_add_plugin(), each with its own MOD and SOUND_ROWS: -Mod and -SoundRows reach only the first plugin. The toolkit is found as docs/toolkit-finder.md says.
# Output: <Build>\Release\<Name>.dll. Copy it to <game>\mods\<Mod>\d2rloader\plugins\.
param(
    [string]$Source = $PSScriptRoot,               # directory holding this CMakeLists.txt
    [string[]]$Name = @("mod-core"),               # DLL names; the first is MODKIT_PLUGIN_NAME (plugin id, console command)
    [string]$Mod = "",                             # MODKIT_MOD_NAME: mods\<Mod> the plugin ships in ("" = no mod check)
    [int]$SoundRows = 0,                           # MODKIT_SOUND_ROWS: rows of the mod's sounds.txt (0 = no new sounds)
    [string]$Build = "",                           # build directory (default <Source>\build)
    [string]$Sdk = "",                             # PluginSDK directory (default <toolkit>\third_party\PluginSDK)
    [string]$Toolkit = "",                         # the d2rAI-toolkit checkout (default: found, see docs/toolkit-finder.md)
    [switch]$Tests                                 # also build the template's tests (MODKIT_BUILD_TESTS=ON) and run ctest -C Release
)
$ErrorActionPreference = 'Stop'
# `powershell -File build.ps1 -Name a,b` passes "a,b" as ONE string: split every element on commas.
$Name = @($Name | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if ($Name.Count -eq 0) { throw "-Name is empty: give at least one plugin id" }
foreach ($n in $Name) { if ($n -notmatch '^[A-Za-z0-9_-]+$') { throw "plugin id '$n' is not valid: use letters, digits, '-' and '_' only" } }
$Source = (Resolve-Path $Source).Path
if (-not $Build) { $Build = Join-Path $Source "build" }
$configure = @("-S", $Source, "-B", $Build, "-A", "x64", "-DMODKIT_PLUGIN_NAME=$($Name[0])", "-DMODKIT_MOD_NAME=$Mod", "-DMODKIT_SOUND_ROWS=$SoundRows")
$tk = if ($Toolkit) { $Toolkit } else { $env:D2R_TOOLKIT }
if ($tk) {
    if (-not (Test-Path -LiteralPath $tk -PathType Container)) { throw "toolkit folder '$tk' does not exist (-Toolkit / D2R_TOOLKIT)" }
    $tk = (Resolve-Path -LiteralPath $tk).Path
    if (-not (Test-Path -LiteralPath (Join-Path $tk "cmake\FindD2rToolkit.cmake"))) { throw "'$tk' is not a d2rAI-toolkit checkout: cmake\FindD2rToolkit.cmake is missing (-Toolkit / D2R_TOOLKIT)" }
}
if ($Toolkit) { $configure += "-DMODKIT_TOOLKIT_DIR=$tk" }
if ($Tests) { $configure += "-DMODKIT_BUILD_TESTS=ON" }
if ($Sdk) { $configure += "-DMODKIT_SDK_DIR=$((Resolve-Path $Sdk).Path)" }
cmake @configure
if ($LASTEXITCODE -ne 0) { throw "cmake configure failed ($LASTEXITCODE)" }
cmake --build $Build --config Release
if ($LASTEXITCODE -ne 0) { throw "cmake build failed ($LASTEXITCODE)" }
if ($Tests) {
    ctest --test-dir $Build -C Release --output-on-failure
    if ($LASTEXITCODE -ne 0) { throw "ctest failed ($LASTEXITCODE)" }
}
foreach ($n in $Name) {
    $dll = Join-Path $Build "Release\$n.dll"
    if (-not (Test-Path $dll)) { throw "build finished but $dll is missing" }
    Write-Output "built: $dll"
}
