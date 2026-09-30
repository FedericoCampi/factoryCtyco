"""Editor Python: las flechas dejan de mover al personaje (29/09); ahora mueven la camara (FactoryCameraComponent).

Saca Up/Down/Left/Right de IA_Move en /Game/Input/IMC_Default (quedan WASD y el joystick). Respaldo del asset en
Saved/Respaldos/2026-09-29_flechas. Con -unattended cierra. Informe: Docs/free_arrow_keys.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
report = {"passed": False}
try:
    imc = unreal.load_asset("/Game/Input/IMC_Default")
    mappings = list(imc.get_editor_property("mappings"))
    before = [(m.action.get_name() if m.action else None, str(m.key.export_text())) for m in mappings]
    imc.modify()
    imc.set_editor_property("mappings", [m for m in mappings if str(m.key.export_text()) not in ("Up", "Down", "Left", "Right")])
    after = [(m.action.get_name() if m.action else None, str(m.key.export_text())) for m in imc.get_editor_property("mappings")]
    if any(k in ("Up", "Down", "Left", "Right") for _, k in after):
        raise RuntimeError("Quedaron flechas")
    if not unreal.EditorAssetLibrary.save_loaded_asset(imc, False):
        raise RuntimeError("No se pudo guardar IMC_Default")
    report.update(passed=True, before=before, after=after)
except Exception as error:
    report["error"] = str(error)
finally:
    (project / "Docs/free_arrow_keys.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
