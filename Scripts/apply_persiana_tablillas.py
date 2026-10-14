"""Editor Python (04/10): persiana de tablillas en la parte de atras del camion.

Importa en /Game/FactoryCtyco/Environments/Camion las piezas de author_truck_shutter.py (SM_CamionPersianaLama, _Zocalo y
_Marco, con sus materiales: colores del camion) y se las pone a cada AFactoryVehiclePath (RearSlatMesh, RearBottomMesh,
RearDoorMesh = marco, RearDoorHeight y RearHeader de camion_persiana_build.json). Borra SM_CamionPersiana (la pared que
se achicaba), que queda sin uso.
Con -unattended abre el mapa, guarda y cierra; con el editor abierto guarda el nivel. Informe: Docs/persiana_tablillas.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SRC = project / "SourceAssets/Camion"
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
DEST = "/Game/FactoryCtyco/Environments/Camion"
PIECES = {"SM_CamionPersianaLama": "camion_persiana_lama", "SM_CamionPersianaZocalo": "camion_persiana_zocalo",
          "SM_CamionPersianaMarco": "camion_persiana_marco"}
OLD = f"{DEST}/SM_CamionPersiana"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
build = json.loads((SRC / "camion_persiana_build.json").read_text(encoding="utf-8"))
report = {"passed": False}


def import_piece(name, file):
    path = f"{DEST}/{name}"
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {path}")
    options = unreal.FbxImportUI()
    options.import_mesh, options.import_as_skeletal = True, False
    options.import_materials, options.import_textures = True, False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes, data.auto_generate_collision = True, False
    data.convert_scene = data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    task = unreal.AssetImportTask()
    task.filename = str(SRC / f"{file}.fbx")
    task.destination_path, task.destination_name = DEST, name
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    return mesh


try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP):
        raise RuntimeError(f"No se pudo abrir {MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    trucks = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.FactoryVehiclePath)]
    for truck in trucks:
        for prop in ("rear_door_mesh", "rear_slat_mesh", "rear_bottom_mesh"):
            truck.set_editor_property(prop, None)
    meshes = {name: import_piece(name, file) for name, file in PIECES.items()}
    sizes = {n: round(m.get_bounding_box().max.z - m.get_bounding_box().min.z, 2) for n, m in meshes.items()}
    if abs(sizes["SM_CamionPersianaLama"] - build["slat_cm"]) > 0.2:
        raise RuntimeError(f"La tablilla mide {sizes['SM_CamionPersianaLama']} cm de alto")
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=False)
    for truck in trucks:
        truck.modify()
        truck.set_editor_property("rear_door_mesh", meshes["SM_CamionPersianaMarco"])
        truck.set_editor_property("rear_slat_mesh", meshes["SM_CamionPersianaLama"])
        truck.set_editor_property("rear_bottom_mesh", meshes["SM_CamionPersianaZocalo"])
        truck.set_editor_property("rear_door_top", unreal.Vector(-95.0, 0.0, 230.0))
        truck.set_editor_property("rear_door_height", build["height_cm"])
        truck.set_editor_property("rear_header", build["header_cm"])
    deleted = lib.does_asset_exist(OLD) and lib.delete_asset(OLD)
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, trucks=[t.get_actor_label() for t in trucks], heights_cm=sizes,
                  materials={n: [str(s.material_slot_name) for s in m.static_materials] for n, m in meshes.items()},
                  old_deleted=bool(deleted))
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[PERSIANA_TABLILLAS] " + report["error"])
finally:
    (project / "Docs/persiana_tablillas.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
