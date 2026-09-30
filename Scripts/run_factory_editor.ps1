param([ValidateSet('Build','Test','Ready')][string]$Mode='Build')
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$engineExe='C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor.exe'
$projectFile=Join-Path $projectRoot 'FactoryCtyco.uproject'
$workRoot=Join-Path (Split-Path -Parent $projectRoot) '_factory_demo_work'
if (Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue) { throw 'Ya hay un editor abierto; no se inicia una segunda sesión.' }
$editorArgs=@(('"'+$projectFile+'"'),'-nosplash','-NoLiveCoding','-windowed','-ResX=1440','-ResY=900')
if ($Mode -ne 'Ready') {
    $scriptName=if($Mode -eq 'Build'){'run_factory_build.py'}else{'playtest_factory_demo.py'}
    $scriptFile=(Join-Path $PSScriptRoot $scriptName).Replace('\','/')
    $editorArgs+=('-ExecutePythonScript="'+$scriptFile+'"')
    $editorArgs+='-unattended'
    $editorArgs+='-nosound'
    $editorArgs+=('-abslog="'+(Join-Path $workRoot ($Mode.ToLower()+'.log'))+'"')
    $editorProcess=Start-Process -FilePath $engineExe -ArgumentList $editorArgs -WindowStyle Hidden -PassThru
} else {
    $editorArgs+='/Game/FactoryCtyco/Maps/L_FactoryDemo'
    # Ready is the interactive editor explicitly requested for the user's playtest.
    $editorProcess=Start-Process -FilePath $engineExe -ArgumentList $editorArgs -WindowStyle Normal -PassThru
}
@{mode=$Mode;pid=$editorProcess.Id;project=$projectFile} | ConvertTo-Json -Compress
