"""Sin editor abierto: abre L_FactoryDemo, rehace SM_Parking (reimport_parking_mesh.py), corre
apply_elevators.py, guarda y cierra.

UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/run_elevator_setup.py -unattended -nosound
"""
import json
import runpy
from pathlib import Path
import unreal

folder = Path(__file__).resolve().parent
try:
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir L_FactoryDemo")
    runpy.run_path(str(folder / "reimport_parking_mesh.py"), run_name="__main__")
    runpy.run_path(str(folder / "apply_elevators.py"), run_name="__main__")
    docs = folder.parent / "Docs"
    if all(json.loads((docs / n).read_text(encoding="utf-8")).get("passed") for n in ("parking_reimport.json", "elevators.json")):
        if not unreal.EditorLoadingAndSavingUtils.save_current_level():
            unreal.log_error("[ELEVATOR_SETUP] No se pudo guardar el nivel")
finally:
    unreal.SystemLibrary.quit_editor()
