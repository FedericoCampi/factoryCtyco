"""Editor Python: ascensores con cabina fija y piso que sube y baja (28/09).

Reimporta SM_Ascensor2Cabina (ahora sin piso, 5 colisiones) e importa SM_Ascensor2Piso (el piso, con su
colision) desde SourceAssets/Ascensor2 (author_elevator2.py), y se los pone a los dos AFactoryElevator
(componentes Cabin y Platform). No toca el resto (tubo, techo, puertas, lugar). Con -unattended abre el
mapa, guarda y cierra. Informe: Docs/elevator_platform.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SRC = project / "SourceAssets/Ascensor2"
DEST = "/Game/FactoryCtyco/Environments/Ascensor2"
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
report = {"passed": False}


def import_mesh(name):
    path = f"{DEST}/{name}"
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {name}")
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = True
    options.import_textures = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.one_convex_hull_per_ucx = True
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    data.generate_lightmap_u_vs = False
    data.build_nanite = False
    task = unreal.AssetImportTask()
    task.filename = str(SRC / f"{name}.fbx")
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    return mesh


try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP):
        raise RuntimeError(f"No se pudo abrir {MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    elevators = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.FactoryElevator)]
    if len(elevators) < 2:
        raise RuntimeError(f"Se esperaban 2 ascensores, hay {len(elevators)}")
    for e in elevators:  # soltar referencias antes de borrar y reimportar
        e.get_editor_property("cabin").set_static_mesh(None)
        e.get_editor_property("platform").set_static_mesh(None)
    cabin, floor = import_mesh("SM_Ascensor2Cabina"), import_mesh("SM_Ascensor2Piso")
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)
    sms = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    hulls = {"cabina": sms.get_convex_collision_count(cabin), "piso": sms.get_convex_collision_count(floor)}
    if hulls != {"cabina": 5, "piso": 1}:
        raise RuntimeError(f"Colisiones inesperadas {hulls}")
    done = []
    for e in elevators:
        e.modify()
        e.get_editor_property("cabin").set_static_mesh(cabin)
        e.get_editor_property("platform").set_static_mesh(floor)
        done.append({"label": e.get_actor_label(), "stop": e.get_editor_property("stop_name"),
                     "z": round(e.get_actor_location().z, 1)})
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, collisions=hulls, elevators=sorted(done, key=lambda d: d["z"]))
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[ELEVATOR_PLATFORM] {error}")
finally:
    (project / "Docs/elevator_platform.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
