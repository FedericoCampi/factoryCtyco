"""Editor Python: calle a lo largo del recorrido de los camiones (28/09).

Importa SM_CalleTramo (SourceAssets/Calle, author_road.py) en /Game/FactoryCtyco/Environments/Calle y se lo pone a
Camion_Recorrido (RoadMesh): la calle se dibuja a lo largo de su linea y la sigue al mover los puntos.
Con -unattended abre el mapa, guarda y cierra. Informe: Docs/road.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST, NAME = "/Game/FactoryCtyco/Environments/Calle", "SM_CalleTramo"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
report = {"passed": False}
try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir el mapa")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    truck = next(a for a in actors.get_all_level_actors() if a.get_actor_label() == "Camion_Recorrido")
    truck.set_editor_property("road_mesh", None)
    if lib.does_asset_exist(f"{DEST}/{NAME}"):
        lib.delete_asset(f"{DEST}/{NAME}")
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = True
    options.import_textures = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.convert_scene = True
    data.convert_scene_unit = True
    task = unreal.AssetImportTask()
    task.filename = str(project / "SourceAssets/Calle" / f"{NAME}.fbx")
    task.destination_path = DEST
    task.destination_name = NAME
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(f"{DEST}/{NAME}")
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("No se importo la calle")
    lib.save_directory(DEST, only_if_is_dirty=False, recursive=True)
    truck.modify()
    truck.set_editor_property("road_mesh", mesh)   # la construccion del actor tiende la calle
    pieces = len(truck.get_components_by_class(unreal.SplineMeshComponent))
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, mesh=mesh.get_path_name(), pieces=pieces)
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[ROAD] {error}")
finally:
    (project / "Docs/road.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
