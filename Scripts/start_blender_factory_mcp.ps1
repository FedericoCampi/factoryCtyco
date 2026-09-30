param(
    [string]$BlenderExe = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$workRoot = Join-Path $projectRoot 'Saved\VisualPolishWork\BlenderMCP'
$bootstrap = Join-Path $PSScriptRoot 'blender_factory_mcp_bootstrap.py'
$addon = Join-Path $workRoot 'runtime\blender_mcp\bundled\addon.py'
$pidFile = Join-Path $workRoot 'blender.pid'
foreach ($required in @($BlenderExe,$bootstrap,$addon)) {
    if (!(Test-Path -LiteralPath $required)) { throw ('Missing Blender MCP input: ' + $required) }
}
if (Test-Path -LiteralPath $pidFile) {
    $managedId = 0
    if ([int]::TryParse(([IO.File]::ReadAllText($pidFile).Trim()), [ref]$managedId)) {
        $managed = Get-Process -Id $managedId -ErrorAction SilentlyContinue
        if ($managed -and $managed.ProcessName -eq 'blender' -and $managed.Path -eq $BlenderExe) {
            @{pid=$managed.Id;host='127.0.0.1';port=9876;hidden=$true;already_running=$true} | ConvertTo-Json -Compress
            exit 0
        }
    }
}
if (Get-Process -Name blender -ErrorAction SilentlyContinue) {
    throw 'A separate Blender session is open. It was left untouched; close it before starting the dedicated factory MCP session.'
}
$scratch = Join-Path $workRoot 'scratch'
$configuration = Join-Path $workRoot 'blender-config'
New-Item -ItemType Directory -Force -Path $workRoot,$scratch,$configuration | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$stdout = Join-Path $workRoot ('blender-' + $stamp + '.stdout.log')
$stderr = Join-Path $workRoot ('blender-' + $stamp + '.stderr.log')
# These are child-process environment settings, restored immediately afterwards.
# They contain Blender's recent-file list, autosave and temporary state locally.
$previousEnvironment = @{}
$childEnvironment = @{
    'TEMP'=$scratch
    'TMP'=$scratch
    'BLENDER_USER_CONFIG'=$configuration
    'BLENDER_MCP_DISABLE_TELEMETRY'='1'
    'DISABLE_TELEMETRY'='true'
}
try {
    foreach ($name in $childEnvironment.Keys) {
        $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $childEnvironment[$name], 'Process')
    }
    $process = Start-Process -FilePath $BlenderExe -WorkingDirectory $projectRoot -ArgumentList @('--factory-startup','--python',('"' + $bootstrap + '"')) -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
} finally {
    foreach ($name in $previousEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], 'Process')
    }
}
[IO.File]::WriteAllText($pidFile, [string]$process.Id)
$result = @{pid=$process.Id;host='127.0.0.1';port=9876;hidden=$true;already_running=$false;stdout=$stdout;stderr=$stderr}
$result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $workRoot 'launch.json') -Encoding UTF8
$result | ConvertTo-Json -Compress
