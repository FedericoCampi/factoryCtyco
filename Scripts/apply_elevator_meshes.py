"""Editor Python (con L_FactoryDemo abierto): pone el modelo del usuario en los dos ascensores.

Importa SourceAssets/Ascensor/SM_AscensorEstructura.fbx (con UCX en los postes) y
SM_AscensorPiso.fbx en /Game/FactoryCtyco/Environments/Ascensor. En cada AFactoryElevator:
Platform = piso (baja y sube), Crown = estructura (fija, con colision), sin postes ni anillo
basicos. No guarda el nivel. Informe: Docs/elevator_meshes.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/Ascensor"
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}


def import_mesh(name):
    path = f"{DEST}/{name}"
    elevators = [a for a in actors.get_all_level_actors() if a.get_class().get_name() == "FactoryElevator"]
    for e in elevators:  # soltar referencias antes de borrar
        for comp in e.get_components_by_class(unreal.StaticMeshComponent):
            if comp.static_mesh and comp.static_mesh.get_path_name().startswith(path + "."):
                comp.set_static_mesh(None)
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
    task = unreal.AssetImportTask()
    task.filename = str(project / f"SourceAssets/Ascensor/{name}.fbx")
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
    build = json.loads((project / "SourceAssets/Ascensor/elevator_build.json").read_text())
    frame, floor = import_mesh("SM_AscensorEstructura"), import_mesh("SM_AscensorPiso")
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)
    size = frame.get_bounding_box()
    height = size.max.z - size.min.z
    if abs(height - build["SM_AscensorEstructura"]["size_m"][2] * 100) > 5:
        raise RuntimeError(f"Altura inesperada de la estructura: {height:.1f} cm")
    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(frame)
    done = []
    for e in [a for a in actors.get_all_level_actors() if a.get_class().get_name() == "FactoryElevator"]:
        for comp in e.get_components_by_class(unreal.StaticMeshComponent):
            name = comp.get_name()
            if name == "Platform":
                comp.set_static_mesh(floor)
                comp.set_relative_scale3d(unreal.Vector(1, 1, 1))
            elif name == "Crown":
                comp.set_static_mesh(frame)
                comp.set_relative_location(unreal.Vector(0, 0, -57), False, False)  # travesano al ras: apply_elevator_sink.py
                comp.set_relative_scale3d(unreal.Vector(1, 1, 1))
                comp.set_collision_profile_name("BlockAll")
            else:  # postes y anillo basicos
                comp.set_static_mesh(None)
                comp.set_collision_profile_name("NoCollision")
        e.set_editor_property("interaction_radius", 75.0)
        done.append(e.get_actor_label())
    report.update(passed=True, elevators=done, frame_height_cm=round(height, 1), frame_collisions=hulls,
                  floor=floor.get_path_name(), frame=frame.get_path_name())
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[ELEVATOR_MESHES] {error}")
(project / "Docs/elevator_meshes.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
