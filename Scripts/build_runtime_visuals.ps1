param(
    [switch]$Install,
    [string]$EngineRoot = 'C:\Program Files\Epic Games\UE_5.6'
)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$workRoot = Join-Path $projectRoot 'Saved\VisualPolishWork'
$sourcePlugin = Join-Path $projectRoot 'Plugins\FactoryCtycoRuntime'
$hostRoot = Join-Path $workRoot 'HostProject'
$hostPlugin = Join-Path $hostRoot 'Plugins\FactoryCtycoRuntime'
$runRoot = Join-Path $workRoot ('Build-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$dotnet = Join-Path $EngineRoot 'Engine\Binaries\ThirdParty\DotNet\8.0.300\win-x64\dotnet.exe'
$ubt = Join-Path $EngineRoot 'Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.dll'

function Assert-EditorClosed {
    if (Get-Process -Name UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) {
        throw 'Close Unreal Editor before installing FactoryCtycoRuntime binaries. Compilation without -Install is safe while the editor is open.'
    }
}

function Write-ChangedText([string]$Path, [string]$Value) {
    if (!(Test-Path -LiteralPath $Path) -or [IO.File]::ReadAllText($Path) -ne $Value) {
        [IO.File]::WriteAllText($Path, $Value, (New-Object Text.UTF8Encoding($false)))
    }
}

function Source-Snapshot {
    $result = @{}
    $files = @(Get-ChildItem -LiteralPath (Join-Path $sourcePlugin 'Source') -Recurse -File)
    $files += Get-Item -LiteralPath (Join-Path $sourcePlugin 'FactoryCtycoRuntime.uplugin')
    foreach ($file in $files) {
        $relative = $file.FullName.Substring($sourcePlugin.Length + 1)
        $result[$relative] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    }
    return $result
}

if ($Install) { Assert-EditorClosed }
foreach ($required in @($dotnet, $ubt, (Join-Path $sourcePlugin 'FactoryCtycoRuntime.uplugin'))) {
    if (!(Test-Path -LiteralPath $required)) { throw ('Missing build input: ' + $required) }
}
New-Item -ItemType Directory -Force -Path $runRoot,$hostPlugin | Out-Null
$sourceHashes = Source-Snapshot
foreach ($relative in $sourceHashes.Keys) {
    $source = Join-Path $sourcePlugin $relative
    $destination = Join-Path $hostPlugin $relative
    $same = (Test-Path -LiteralPath $destination) -and ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -eq $sourceHashes[$relative])
    if (!$same) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }
}
# Keep the stable host directory for incremental compilation. Archive removed
# source files instead of deleting them or leaving them in the compiler's scan.
foreach ($file in @(Get-ChildItem -LiteralPath (Join-Path $hostPlugin 'Source') -Recurse -File)) {
    $relative = $file.FullName.Substring($hostPlugin.Length + 1)
    if (!$sourceHashes.ContainsKey($relative)) {
        $resolved = [IO.Path]::GetFullPath($file.FullName)
        if (!$resolved.StartsWith($hostRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe source archive path.' }
        $archive = [IO.Path]::GetFullPath((Join-Path (Join-Path $runRoot 'archived-source') $relative))
        if (!$archive.StartsWith($runRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe archive destination.' }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $archive) | Out-Null
        Move-Item -LiteralPath $resolved -Destination $archive
    }
}
$hostProject = Join-Path $hostRoot 'HostProject.uproject'
Write-ChangedText $hostProject '{ "FileVersion": 3, "Plugins": [ { "Name": "FactoryCtycoRuntime", "Enabled": true } ] }'
$manifest = Join-Path $runRoot 'Manifest-UnrealEditor-Win64-Development.xml'
$log = Join-Path $runRoot 'build.log'
$ubtArgs = @($ubt,'UnrealEditor','Win64','Development',('-Project=' + $hostProject),('-plugin=' + (Join-Path $hostPlugin 'FactoryCtycoRuntime.uplugin')),'-noubtmakefiles',('-manifest=' + $manifest),'-nohotreload','-NoLiveCoding',('-log=' + (Join-Path $runRoot 'ubt.log')))
Write-Host ('Compiling FactoryCtycoRuntime; logs: ' + $runRoot)
& $dotnet @ubtArgs 2>&1 | Tee-Object -FilePath $log
if ($LASTEXITCODE -ne 0) { throw ('FactoryCtycoRuntime build failed. See ' + $log) }

$builtBinaries = Join-Path $hostPlugin 'Binaries\Win64'
$fileNames = @('UnrealEditor-FactoryCtycoRuntime.dll','UnrealEditor-FactoryCtycoRuntime.pdb','UnrealEditor.modules')
foreach ($name in $fileNames) {
    if (!(Test-Path -LiteralPath (Join-Path $builtBinaries $name))) { throw ('Build product missing: ' + $name) }
}
$engineModules = Get-Content -LiteralPath (Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor.modules') -Raw | ConvertFrom-Json
$pluginModules = Get-Content -LiteralPath (Join-Path $builtBinaries 'UnrealEditor.modules') -Raw | ConvertFrom-Json
if ($pluginModules.BuildId -ne $engineModules.BuildId) { throw 'BuildId differs from installed editor; refusing to install.' }
$currentHashes = Source-Snapshot
if ($currentHashes.Count -ne $sourceHashes.Count) { throw 'Source changed during compilation; rerun before installing.' }
foreach ($relative in $sourceHashes.Keys) {
    if ($currentHashes[$relative] -ne $sourceHashes[$relative]) { throw ('Source changed during compilation: ' + $relative) }
}

$result = [ordered]@{ built = $true; installed = $false; run = $runRoot; binaries = $builtBinaries; build_id = $pluginModules.BuildId }
if ($Install) {
    Assert-EditorClosed
    $liveBinaries = Join-Path $sourcePlugin 'Binaries\Win64'
    $backup = Join-Path $runRoot 'previous-binaries'
    New-Item -ItemType Directory -Force -Path $backup,$liveBinaries | Out-Null
    foreach ($name in $fileNames) {
        $liveFile = Join-Path $liveBinaries $name
        if (Test-Path -LiteralPath $liveFile) { Copy-Item -LiteralPath $liveFile -Destination (Join-Path $backup $name) }
    }
    try {
        Assert-EditorClosed
        foreach ($name in $fileNames) {
            Copy-Item -LiteralPath (Join-Path $builtBinaries $name) -Destination (Join-Path $liveBinaries $name) -Force
        }
        $result.installed = $true
        $result.backup = $backup
    } catch {
        foreach ($name in $fileNames) {
            $backupFile = Join-Path $backup $name
            if (Test-Path -LiteralPath $backupFile) { Copy-Item -LiteralPath $backupFile -Destination (Join-Path $liveBinaries $name) -Force }
        }
        throw
    }
}
$result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runRoot 'result.json') -Encoding UTF8
Write-ChangedText (Join-Path $workRoot 'latest-build.txt') $runRoot
$result | ConvertTo-Json -Compress
