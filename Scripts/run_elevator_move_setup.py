"""Sin editor abierto (30/09): pozo de Ascensor_Fabrica en su lugar nuevo y cintas fijas de la fabrica.

Antes: blender -b --factory-startup -P Scripts/author_arena_edit.py (con el centro en elevator_holes.py).
1. reimport_arena_mesh.py: SM_SceneRobot con el agujero nuevo y el viejo cerrado.
2. apply_elevator_move.py: abre Piso_Exterior bajo la parte del ascensor que queda afuera de la losa.
3. apply_factory_belts.py: Cinta_Fabrica_N en lugar de los contornos turquesa.
Guarda el nivel si todo paso y cierra.

UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/run_elevator_move_setup.py -unattended -nosound
"""
import json
import runpy
from pathlib import Path
import unreal

folder = Path(__file__).resolve().parent
docs = folder.parent / "Docs"
steps = {"reimport_arena_mesh.py": "arena_reimport.json", "apply_elevator_move.py": "elevator_move.json",
         "apply_factory_belts.py": "factory_belts.json"}
try:
    for name in steps.values():
        (docs / name).unlink(missing_ok=True)
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir L_FactoryDemo")
    for script in steps:
        runpy.run_path(str(folder / script), run_name="__main__")
    if all(json.loads((docs / n).read_text(encoding="utf-8")).get("passed") for n in steps.values()):
        if not unreal.EditorLoadingAndSavingUtils.save_current_level():
            unreal.log_error("[ELEVATOR_MOVE_SETUP] No se pudo guardar el nivel")
    else:
        unreal.log_error("[ELEVATOR_MOVE_SETUP] Algun paso fallo: el nivel no se guardo")
finally:
    unreal.SystemLibrary.quit_editor()
