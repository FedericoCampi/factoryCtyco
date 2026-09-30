"""Editor Python: vuelve a crear SM_SceneRobot desde scene_unreal.fbx, sin tocar el nivel.

El actor SceneRobot_Fabrica conserva su posicion (y lo enganchado a el). Borra el asset y lo
importa limpio: reimportar encima de un asset existente cambiaba la escala (visto en SM_Parking).
Mismas opciones que build_arena.py. Informe: Docs/arena_reimport.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
PATH = "/Game/FactoryCtyco/Environments/SceneRobot/SM_SceneRobot"
lib = unreal.EditorAssetLibrary
report = {"passed": False}
try:
    build = json.loads((project / "SourceAssets/SceneRobot/build.json").read_text(encoding="utf-8"))
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = next(a for a in actors.get_all_level_actors() if a.get_actor_label() == "SceneRobot_Fabrica")
    old = actor.static_mesh_component.static_mesh
    old_box = old.get_bounding_box() if old else None
    actor.static_mesh_component.set_static_mesh(None)
    if lib.does_asset_exist(PATH) and not lib.delete_asset(PATH):
        raise RuntimeError("No se pudo borrar SM_SceneRobot")
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
    data.vertex_color_import_option = unreal.VertexColorImportOption.REPLACE
    task = unreal.AssetImportTask()
    task.filename = str(project / "SourceAssets/SceneRobot/scene_unreal.fbx")
    task.destination_path = PATH.rsplit("/", 1)[0]
    task.destination_name = PATH.rsplit("/", 1)[1]
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(PATH)
    actor.static_mesh_component.set_static_mesh(mesh)
    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(mesh)
    if hulls != build["convex_collision_pieces"]:
        raise RuntimeError(f"Se esperaban {build['convex_collision_pieces']} colisiones; hay {hulls}")
    box = mesh.get_bounding_box()
    got = [box.min.x, box.min.y, box.min.z, box.max.x, box.max.y, box.max.z]
    if old_box:
        was = [old_box.min.x, old_box.min.y, old_box.min.z, old_box.max.x, old_box.max.y, old_box.max.z]
        if any(abs(a - b) > 2 for a, b in zip(got, was)):
            raise RuntimeError(f"Medidas distintas a las anteriores: {got} vs {was}")
    lib.save_directory(PATH.rsplit("/", 1)[0], only_if_is_dirty=True, recursive=True)
    report.update(passed=True, triangles=mesh.get_num_triangles(0), convex_collisions=hulls,
                  bounds_cm=[round(v, 1) for v in got])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[ARENA_REIMPORT] {error}")
(project / "Docs/arena_reimport.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
