"""Editor Python (05/10): la conexion de cinta del cajon 1 copiada para los cajones 2 y 3.

El cajon 1 recibe por Cinta_Carga3 (adentro del edificio) -> Cinta_Muelle_5 (cruza el porton 3 hasta el cajon). Las
copia frente a los otros portones, corridas lo que separa los portones (Porton_Muelle_2 -> Cajon_Muelle_3,
Porton_Muelle_1 -> Cajon_Muelle_2), con los mismos ajustes. Las cintas del despacho (Cinta_Carga2, Cinta_Carga) no se
tocan. Si ya existen las copias, las vuelve a hacer. Guarda el nivel.
Informe: Docs/cintas_cajones.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
CHAIN = ["Cinta_Carga3", "Cinta_Muelle_5"]
SOURCE_DOOR = "Porton_Muelle_3"
TARGETS = {"Cajon3": "Porton_Muelle_2", "Cajon2": "Porton_Muelle_1"}
report = {"passed": False, "copias": {}}

try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    by = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    base_x = by[SOURCE_DOOR].get_actor_location().x
    for suffix, door in TARGETS.items():
        dx = by[door].get_actor_location().x - base_x
        for name in CHAIN:
            src = by[name]
            label = f"{name}_{suffix}"
            copy = by.get(label)
            if copy is not None:
                actors.destroy_actor(copy)
            copy = actors.duplicate_actor(src, world, unreal.Vector(dx, 0, 0))
            copy.set_actor_label(label)
            copy.set_folder_path("Muelles")
            p = copy.get_actor_location()
            L = copy.get_editor_property("length") * copy.get_actor_scale3d().x
            e = copy.world_at(L)
            report["copias"][label] = dict(carga=[round(p.x), round(p.y), round(p.z)], punta=[round(e.x), round(e.y), round(e.z)])
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = True
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[CINTAS_CAJONES] " + report["error"])
(project / "Docs/cintas_cajones.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
