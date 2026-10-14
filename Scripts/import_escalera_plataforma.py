"""Editor Python (con L_FactoryDemo abierto): escalera industrial con plataforma elevada (03/10).

- Importa SourceAssets/EscaleraPlataforma/SM_EscaleraPlataforma.fbx (author_escalera_plataforma.py) en
  /Game/FactoryCtyco/Environments/EscaleraPlataforma con sus materiales y texturas. Choca con su propia malla (complex as
  simple): se sube por los escalones y se camina arriba de la plataforma. Borra el asset antes (reimportar encima lo
  dejaba al 1 %).
- Actor `Escalera_Plataforma` (StaticMeshActor, carpeta Fabrica) en el primer lugar libre de SPOTS (piso de la
  fabrica), para que el usuario lo ubique. Si ya existe solo se le cambia la malla (se conserva su lugar).
Informe: Docs/escalera_plataforma.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/EscaleraPlataforma"
NAME = "SM_EscaleraPlataforma"
LABEL = "Escalera_Plataforma"
SPOTS = [(0, -300), (300, -300), (-200, 100), (300, 100), (0, -900), (1200, -300)]
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}

try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    level = actors.get_all_level_actors()
    users = [a for a in level if isinstance(a, unreal.StaticMeshActor) and a.get_actor_label() == LABEL]
    for a in users:
        a.static_mesh_component.set_static_mesh(None)
    path = f"{DEST}/{NAME}"
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {path}")
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
    task.filename = str(project / f"SourceAssets/EscaleraPlataforma/{NAME}.fbx")
    task.destination_path, task.destination_name = DEST, NAME
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {NAME}")
    body = mesh.get_editor_property("body_setup")
    body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    mesh.set_editor_property("body_setup", body)
    lib.save_loaded_asset(mesh)
    b = mesh.get_bounding_box()
    half = unreal.Vector((b.max.x - b.min.x) / 2 + 20, (b.max.y - b.min.y) / 2 + 20, (b.max.z - b.min.z) / 2)
    actor = users[0] if users else None
    if actor is None:
        ignore = [a for a in level if a.get_actor_label().startswith("SceneRobot")]
        spot = unreal.Vector(*SPOTS[0], 0)
        for x, y in SPOTS:
            hits = unreal.SystemLibrary.box_overlap_actors(world, unreal.Vector(x, y, half.z + 10), half,
                                                           [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2], None, ignore)
            if isinstance(hits, tuple):
                hits = hits[-1]
            if not hits:
                spot = unreal.Vector(x, y, 0)
                break
        hit = unreal.SystemLibrary.line_trace_single(world, spot + unreal.Vector(0, 0, 400), spot - unreal.Vector(0, 0, 200),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
        if hit:
            spot.z = hit.to_tuple()[4].z
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, spot, unreal.Rotator())
        actor.set_actor_label(LABEL)
        actor.set_folder_path("Fabrica")
    for a in users or [actor]:
        a.modify()
        a.static_mesh_component.set_static_mesh(mesh)
        a.static_mesh_component.set_collision_profile_name("BlockAll")
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    loc = actor.get_actor_location()
    report.update(passed=True, actor=LABEL, location=[round(loc.x), round(loc.y), round(loc.z)],
                  size_cm=[round(b.max.x - b.min.x), round(b.max.y - b.min.y), round(b.max.z - b.min.z)],
                  triangles=mesh.get_num_triangles(0), materials=len(mesh.static_materials),
                  collision=str(mesh.get_editor_property("body_setup").get_editor_property("collision_trace_flag")))
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[ESCALERA] " + report["error"])
(project / "Docs/escalera_plataforma.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
