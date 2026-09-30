"""Editor Python: L_FactoryDemo_Completo, el mapa con todo construido (28/09).

Copia L_FactoryDemo y en la copia desbloquea todo (saca las etiquetas "Bloqueado" y su grupo) y borra el
relleno ("Relleno": el rincon de basura). Sirve de referencia de como queda el nivel con todas las mejoras.
Con -unattended guarda y cierra. Informe: Docs/complete_backup.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
MAP, BACKUP = "/Game/FactoryCtyco/Maps/L_FactoryDemo", "/Game/FactoryCtyco/Maps/L_FactoryDemo_Completo"
lib = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False}
try:
    if lib.does_asset_exist(BACKUP):
        lib.delete_asset(BACKUP)
    if not lib.duplicate_asset(MAP, BACKUP) or not lib.save_asset(BACKUP, only_if_is_dirty=False):
        raise RuntimeError("No se pudo copiar el mapa")
    if not levels.load_level(BACKUP):
        raise RuntimeError("No se pudo abrir la copia")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    report["unlocked"], report["removed"] = [], []
    for actor in actors.get_all_level_actors():
        names = [str(t) for t in actor.tags]
        if "Relleno" in names:
            report["removed"].append(actor.get_actor_label())
            actors.destroy_actor(actor)
        elif "Bloqueado" in names:
            actor.modify()
            actor.tags = [t for t in actor.tags if str(t) != "Bloqueado"]
            report["unlocked"].append(actor.get_actor_label())
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar la copia")
    report["passed"] = True
except Exception as error:
    report["error"] = str(error)
finally:
    (project / "Docs/complete_backup.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    unreal.SystemLibrary.quit_editor()
