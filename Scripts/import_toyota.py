"""Editor Python (con L_FactoryDemo abierto): la Toyota del usuario en el estacionamiento (03/10).

- Importa SourceAssets/Toyota/SM_Toyota.fbx (author_toyota.py) en /Game/FactoryCtyco/Environments/Toyota con su
  material y texturas, y su caja de colision (UCX). Borra el asset antes (reimportar encima lo dejaba al 1 %).
- Actor `Toyota` (StaticMeshActor, carpeta Estacionamiento) en el primer lugar libre de SPOTS (la franja del
  estacionamiento por donde antes pasaba la calle de los camiones), trompa a +X, sobre el piso. Para que el usuario la
  acomode; si ya existe solo se le cambia la malla (se conserva su lugar).
Informe: Docs/toyota_import.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/Toyota"
NAME = "SM_Toyota"
LABEL = "Toyota"
SPOTS = [(-3300, 160), (-3700, 160), (-2950, 160), (-4300, 160), (-3300, -700), (-3000, -1300)]
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}

try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    level = actors.get_all_level_actors()
    users = [a for a in level if isinstance(a, unreal.StaticMeshActor) and a.get_actor_label() == LABEL]
    for a in users:
        a.static_mesh_component.set_static_mesh(None)
    if lib.does_directory_exist(DEST):
        for old in lib.list_assets(DEST, recursive=False, include_folder=False):
            lib.delete_asset(old.split(".")[0])
    options = unreal.FbxImportUI()
    options.import_mesh, options.import_as_skeletal = True, False
    options.import_materials = options.import_textures = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes, data.auto_generate_collision = True, False
    data.convert_scene = data.convert_scene_unit = True
    data.generate_lightmap_u_vs = data.build_nanite = False
    task = unreal.AssetImportTask()
    task.filename = str(project / f"SourceAssets/Toyota/{NAME}.fbx")
    task.destination_path, task.destination_name = DEST, NAME
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)
    mesh = unreal.load_asset(f"{DEST}/{NAME}")
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {NAME}")
    b = mesh.get_bounding_box()
    half = unreal.Vector((b.max.x - b.min.x) / 2 + 30, (b.max.y - b.min.y) / 2 + 30, (b.max.z - b.min.z) / 2)
    actor = users[0] if users else None
    if actor is None:
        ignore = [a for a in level if a.get_actor_label().startswith(("Parking", "Piso", "SceneRobot", "Muelles"))]
        floor_z = 10.0
        spot = None
        for x, y in SPOTS:
            hits = unreal.SystemLibrary.box_overlap_actors(world, unreal.Vector(x, y, floor_z + half.z + 5), half,
                                                           [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2], None, ignore)
            if isinstance(hits, tuple):
                hits = hits[-1]
            if not hits:
                spot = unreal.Vector(x, y, floor_z)
                break
        if spot is None:
            spot = unreal.Vector(SPOTS[0][0], SPOTS[0][1], floor_z)
            report["aviso"] = "ningun lugar libre de la lista: queda en el primero"
        hit = unreal.SystemLibrary.line_trace_single(world, spot + unreal.Vector(0, 0, 300), spot - unreal.Vector(0, 0, 200),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
        if hit:
            spot.z = hit.to_tuple()[4].z
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, spot, unreal.Rotator())
        actor.set_actor_label(LABEL)
        actor.set_folder_path("Estacionamiento")
    for a in users or [actor]:
        a.modify()
        a.static_mesh_component.set_static_mesh(mesh)
        a.static_mesh_component.set_collision_profile_name("BlockAll")
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    loc = actor.get_actor_location()
    geom = mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
    report.update(passed=True, actor=LABEL, location=[round(loc.x), round(loc.y), round(loc.z)],
                  size_cm=[round(b.max.x - b.min.x), round(b.max.y - b.min.y), round(b.max.z - b.min.z)],
                  triangles=mesh.get_num_triangles(0), materials=len(mesh.static_materials),
                  collision=len(geom.get_editor_property("box_elems")) + len(geom.get_editor_property("convex_elems")))
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[TOYOTA] " + report["error"])
(project / "Docs/toyota_import.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
