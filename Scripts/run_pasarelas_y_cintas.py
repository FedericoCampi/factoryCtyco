"""Sin editor abierto (03/10): pasarelas y arreglo de cintas.

Antes: blender -b --factory-startup -P Scripts/author_pasarelas.py
Abre L_FactoryDemo, corre import_pasarelas.py y apply_fix_cintas_curva_y_puente.py (cada uno guarda el nivel) y cierra.
Prueba en Play: Scripts/playtest_pasarelas_y_cintas.py (con el editor abierto: el que se abre con -ExecutePythonScript
se cierra solo al terminar el script, sin llegar a jugar).

UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/run_pasarelas_y_cintas.py -unattended -nosound
"""
import json
import runpy
from pathlib import Path
import unreal

folder = Path(__file__).resolve().parent
docs = folder.parent / "Docs"
try:
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir L_FactoryDemo")
    for script, out in (("import_pasarelas.py", "pasarelas.json"), ("apply_fix_cintas_curva_y_puente.py", "fix_cintas_curva_y_puente.json")):
        runpy.run_path(str(folder / script), run_name="__main__")
        if not json.loads((docs / out).read_text(encoding="utf-8")).get("passed"):
            unreal.log_error(f"[PASARELAS_Y_CINTAS] {script} fallo: ver Docs/{out}")
            break
finally:
    unreal.SystemLibrary.quit_editor()
