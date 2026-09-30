"""Sin editor abierto (28/09): entrada oeste del camion y botoneras sueltas, todo junto.

1. reimport_parking_mesh.py: SM_Parking con la puerta sur cerrada, el vano oeste abierto y la calzada.
2. apply_truck_loop.py: Camion_Loop con el recorrido recto (oeste -> este).
3. Piso_Exterior_Oeste: copia del piso de afuera, 100 m al oeste, para que la calzada y el camion
   no queden sobre el vacio (Piso_Exterior termina en el muro oeste del estacionamiento).
4. apply_belt_buttons.py: Botonera_CintaN donde estaban las botoneras (requiere FactoryCtycoRuntime instalado).
Guarda el nivel si todo paso y cierra. Informe: Docs/truck_entrance_setup.json.

Antes: Scripts/build_runtime_visuals.ps1 -Install (con el editor cerrado).
UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/run_truck_entrance_setup.py -unattended -nosound
"""
import json
import runpy
from pathlib import Path
import unreal

folder = Path(__file__).resolve().parent
docs = folder.parent / "Docs"
report = {"passed": False}


def west_backdrop():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level = actors.get_all_level_actors()
    base = next(a for a in level if a.get_actor_label() == "Piso_Exterior")
    copy = next((a for a in level if a.get_actor_label() == "Piso_Exterior_Oeste"), None)
    origin, extent = base.get_actor_bounds(False)
    spot = base.get_actor_location() - unreal.Vector(extent.x * 2, 0, 0)
    if copy is None:
        copy = actors.spawn_actor_from_class(unreal.StaticMeshActor, spot, base.get_actor_rotation())
        copy.set_actor_label("Piso_Exterior_Oeste")
        copy.set_folder_path(str(base.get_folder_path()))
    copy.set_actor_scale3d(base.get_actor_scale3d())
    copy.set_actor_location(spot, False, False)
    src, dst = base.static_mesh_component, copy.static_mesh_component
    dst.set_static_mesh(src.static_mesh)
    for slot, material in enumerate(src.get_materials()):
        dst.set_material(slot, material)
    dst.set_collision_profile_name(src.get_collision_profile_name())
    return [round(v) for v in (spot.x, spot.y, spot.z)]


try:
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir L_FactoryDemo")
    runpy.run_path(str(folder / "reimport_parking_mesh.py"), run_name="__main__")
    runpy.run_path(str(folder / "apply_truck_loop.py"), run_name="__main__")
    report["backdrop_west"] = west_backdrop()
    runpy.run_path(str(folder / "apply_belt_buttons.py"), run_name="__main__")
    steps = ("parking_reimport.json", "truck_loop.json", "belt_buttons.json")
    report["steps"] = {n: json.loads((docs / n).read_text(encoding="utf-8")) for n in steps}
    if all(r.get("passed") for r in report["steps"].values()):
        if not unreal.EditorLoadingAndSavingUtils.save_current_level():
            raise RuntimeError("No se pudo guardar el nivel")
        report["passed"] = True
    else:
        report["error"] = "Algun paso fallo: el nivel no se guardo"
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[TRUCK_ENTRANCE] {error}")
finally:
    (docs / "truck_entrance_setup.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    unreal.SystemLibrary.quit_editor()
