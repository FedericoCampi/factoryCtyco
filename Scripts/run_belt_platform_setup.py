"""Sin editor abierto (30/09): cintas de la fabrica sobre su plataforma.

Antes: blender -b --factory-startup -P Scripts/author_belt_platform.py
       Scripts/build_runtime_visuals.ps1 -Install   (el plugin con BaseMesh/BaseHeight)
Abre L_FactoryDemo, corre apply_belt_platform.py, guarda el nivel si paso y cierra.

UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/run_belt_platform_setup.py -unattended -nosound
"""
import json
import runpy
from pathlib import Path
import unreal

folder = Path(__file__).resolve().parent
report = folder.parent / "Docs" / "belt_platform.json"
try:
    report.unlink(missing_ok=True)
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir L_FactoryDemo")
    runpy.run_path(str(folder / "apply_belt_platform.py"), run_name="__main__")
    result = json.loads(report.read_text(encoding="utf-8"))
    if result.get("passed"):
        result["level_saved"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
        report.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
        if not result["level_saved"]:
            unreal.log_error("[BELT_PLATFORM_SETUP] No se pudo guardar el nivel")
    else:
        unreal.log_error("[BELT_PLATFORM_SETUP] Fallo: el nivel no se guardo")
finally:
    unreal.SystemLibrary.quit_editor()
