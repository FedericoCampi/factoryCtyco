"""Sin editor abierto: los ascensores suben por dentro de la jaula (TravelDepth -180) y guarda.

UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/run_elevator_travel.py -unattended -nosound
"""
import json
from pathlib import Path
import unreal

report = {"passed": False}
try:
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir L_FactoryDemo")
    done = []
    for e in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if e.get_class().get_name() == "FactoryElevator":
            e.set_editor_property("travel_depth", -180.0)
            done.append([e.get_actor_label(), e.get_editor_property("travel_depth")])
    if len(done) != 2:
        raise RuntimeError(f"Se esperaban 2 ascensores: {done}")
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, elevators=done)
except Exception as error:
    report["error"] = str(error)
finally:
    (Path(__file__).resolve().parent.parent / "Docs/elevator_travel.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    unreal.SystemLibrary.quit_editor()
