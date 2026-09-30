"""Editor Python: reimporta solo SM_Parking desde parking_unreal.fbx, sin tocar el nivel.

Sirve cuando cambia author_parking_scene.py: el actor Parking_Estacionamiento conserva su
posicion y el nivel no se guarda. Borra y vuelve a crear el asset: reimportar encima reutiliza
datos guardados y dejaba la malla al 1% (metros tomados como centimetros). Informe: Docs/parking_reimport.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
report = {"passed": False}
try:
    build = json.loads((project / "SourceAssets/Parking/parking_build.json").read_text())
    path = "/Game/FactoryCtyco/Environments/Parking/SM_Parking"
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = next(a for a in actors.get_all_level_actors() if a.get_actor_label() == "Parking_Estacionamiento")
    actor.static_mesh_component.set_static_mesh(None)
    if unreal.EditorAssetLibrary.does_asset_exist(path) and not unreal.EditorAssetLibrary.delete_asset(path):
        raise RuntimeError("No se pudo borrar SM_Parking")
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
    task.filename = str(project / "SourceAssets/Parking/parking_unreal.fbx")
    task.destination_path = "/Game/FactoryCtyco/Environments/Parking"
    task.destination_name = "SM_Parking"
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    actor.static_mesh_component.set_static_mesh(mesh)
    box = mesh.get_bounding_box()
    (bx0, by0, _), (bx1, by1, _) = build["bounds_m"]
    expected = (bx0 * 100, -by1 * 100, max(bx1, 11.9) * 100, -by0 * 100)
    got = (box.min.x, box.min.y, box.max.x, box.max.y)
    if any(abs(a - b) > 2 for a, b in zip(got, expected)):
        raise RuntimeError(f"Medidas inesperadas {got}, se esperaba {expected}")
    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(mesh)
    if hulls != build["ucx"]:
        raise RuntimeError(f"Se esperaban {build['ucx']} colisiones; hay {hulls}")
    unreal.EditorAssetLibrary.save_directory("/Game/FactoryCtyco/Environments/Parking", only_if_is_dirty=True, recursive=True)
    report.update(passed=True, triangles=mesh.get_num_triangles(0), convex_collisions=hulls,
                  bounds_cm=[round(v, 1) for v in got])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[PARKING_REIMPORT] {error}")
(project / "Docs/parking_reimport.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
