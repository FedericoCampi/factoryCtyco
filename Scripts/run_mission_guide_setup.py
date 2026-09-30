"""Sin editor: materiales de la guía y del contorno, y el actor Guia_Mision en L_FactoryDemo (29/09).

UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript="<proyecto>/Scripts/run_mission_guide_setup.py" -unattended -nosound
(con barras /). Requiere FactoryCtycoRuntime instalado (Scripts/build_runtime_visuals.ps1 -Install).
"""
from pathlib import Path
import unreal

scripts = Path(unreal.Paths.project_dir()).resolve() / "Scripts"
for name in ("make_guide_materials.py", "apply_mission_guide.py"):
    exec(compile((scripts / name).read_text(encoding="utf-8"), str(scripts / name), "exec"), {"__name__": "__main__"})
