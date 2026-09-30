"""Editor Python: import the parking FBX and place it west of the factory, door to door.

Source: SourceAssets/Parking/parking_unreal.fbx (built by author_parking_scene.py).
Writes Docs/parking_import.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/Parking"
NAME = "SM_Parking"
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
LOCATION = unreal.Vector(-2303, -410, 0)   # parking east door meets the factory's west door
LABEL = "Parking_Estacionamiento"
library = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
build = json.loads((project / "SourceAssets/Parking/parking_build.json").read_text())
report = {"passed": False}

try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError(f"Open {MAP} first; current level is {world.get_path_name()}")

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
        raise RuntimeError("Parking mesh was not imported")

    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(mesh)
    if hulls != build["ucx"]:
        raise RuntimeError(f"Expected {build['ucx']} collision hulls; got {hulls}")
    # Blender Y maps to Unreal -Y: the asymmetric Y bounds must come out mirrored.
    box = mesh.get_bounding_box()
    (bx0, by0, _), (bx1, by1, _) = build["bounds_m"]
    # The threshold plate reaches 11.9 m, past the parking's own east edge.
    expected = (bx0 * 100, -by1 * 100, max(bx1, 11.9) * 100, -by0 * 100)
    got = (box.min.x, box.min.y, box.max.x, box.max.y)
    if any(abs(a - b) > 2 for a, b in zip(got, expected)):
        raise RuntimeError(f"Unexpected parking bounds {got}, expected {expected}")

    for old in actors.get_all_level_actors():
        if old.get_actor_label() == LABEL:
            actors.destroy_actor(old)
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, LOCATION, unreal.Rotator())
    actor.set_actor_label(LABEL)
    actor.set_folder_path("Environment")
    component = actor.static_mesh_component
    component.set_static_mesh(mesh)
    component.set_mobility(unreal.ComponentMobility.STATIC)
    component.set_collision_profile_name("BlockAll")
    # task.save covers the mesh only; imported materials and textures are saved here.
    library.save_directory(DEST, only_if_is_dirty=True, recursive=True)
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("Could not save the level")
    report.update(passed=True, asset=mesh.get_path_name(), actor=LABEL,
                  location=[LOCATION.x, LOCATION.y, LOCATION.z], convex_collisions=hulls,
                  triangles=mesh.get_num_triangles(0), materials=len(mesh.static_materials),
                  bounds_cm=[round(v, 1) for v in got])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[PARKING_IMPORT] {error}")
(project / "Docs/parking_import.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
