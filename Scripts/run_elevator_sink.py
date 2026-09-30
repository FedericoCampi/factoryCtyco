"""Sin editor abierto: corre apply_elevator_sink.py sobre L_FactoryDemo y cierra.

UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/run_elevator_sink.py -unattended -nosound
"""
from pathlib import Path
import unreal

try:
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir L_FactoryDemo")
    exec((Path(__file__).resolve().parent / "apply_elevator_sink.py").read_text(encoding="utf-8"))
finally:
    unreal.SystemLibrary.quit_editor()
