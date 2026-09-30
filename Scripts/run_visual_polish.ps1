param([ValidateSet('Assets','VisualTest','Regression','MCP')][string]$Mode = 'VisualTest')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$workRoot = Join-Path $projectRoot 'Saved\VisualPolishWork'
$engineExe = 'C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor.exe'
if (Get-Process -Name UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) {
    throw 'Hay un editor abierto; terminar esa sesión antes de iniciar la verificación.'
}
New-Item -ItemType Directory -Force -Path $workRoot | Out-Null
$scriptName = switch ($Mode) {
    'Assets' { 'polish_factory_visuals.py' }
    'VisualTest' { 'playtest_factory_visuals.py' }
    'Regression' { 'playtest_factory_demo.py' }
}
if ($Mode -eq 'Regression') {
    $backup = Join-Path $workRoot ('Regression-before-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Force -Path $backup | Out-Null
    foreach ($name in @('factory_demo_playtest.json','factory_demo_completed.png','factory_demo_build_mode.png')) {
        $path = Join-Path (Join-Path $projectRoot 'Docs') $name
        if (Test-Path -LiteralPath $path) { Copy-Item -LiteralPath $path -Destination $backup }
    }
}
$log = Join-Path $workRoot ($Mode.ToLower() + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$editorArgs = @(
    ('"' + (Join-Path $projectRoot 'FactoryCtyco.uproject') + '"'),
    '-nosplash','-NoLiveCoding','-windowed','-ResX=1440','-ResY=900','-unattended','-nosound',
    ('-abslog="' + $log + '"')
)
if ($Mode -ne 'MCP') {
    $editorArgs += ('-ExecutePythonScript="' + (Join-Path $PSScriptRoot $scriptName).Replace('\','/') + '"')
}
$editorProcess = Start-Process -FilePath $engineExe -ArgumentList $editorArgs -WindowStyle Hidden -PassThru
@{ mode = $Mode; pid = $editorProcess.Id; log = $log } | ConvertTo-Json -Compress
