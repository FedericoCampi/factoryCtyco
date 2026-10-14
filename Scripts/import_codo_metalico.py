"""Editor Python: codo metalico reforzado con pernos (02/10). Sirve con el editor abierto o sin editor (abre el mapa,
guarda y cierra).

- Importa SourceAssets/CodoMetalico/SM_CodoMetalico.fbx (author_codo_metalico.py) en
  /Game/FactoryCtyco/Environments/CodoMetalico con sus materiales y texturas y la caja de colision UCX (borra el asset
  antes: reimportar encima lo dejaba al 1 %).
- Actor `Codo_Metalico` (StaticMeshActor, carpeta Fabrica) en un lugar libre al lado de Horno_Fundicion, para que el
  usuario lo ubique. Si ya existe solo se le cambia la malla (se conserva la posicion ajustada a mano).
Informe: Docs/codo_metalico_import.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SRC = project / "SourceAssets/CodoMetalico"
DEST = "/Game/FactoryCtyco/Environments/CodoMetalico"
NAME = "SM_CodoMetalico"
LABEL = "Codo_Metalico"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}


def import_fbx(users):
    path = f"{DEST}/{NAME}"
    for a in users:
        a.static_mesh_component.set_static_mesh(None)
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {path}")
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
    task.filename = str(SRC / f"{NAME}.fbx")
    task.destination_path, task.destination_name = DEST, NAME
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)   # materiales y texturas
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {NAME}")
    return mesh


def size_cm(mesh):
    b = mesh.get_bounding_box()
    return [round(b.max.x - b.min.x), round(b.max.y - b.min.y), round(b.max.z - b.min.z)]


def floor_z(world, x, y, ignore):
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 1000), unreal.Vector(x, y, -300),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignore, unreal.DrawDebugTrace.NONE, True)
    return hit.to_tuple()[4].z if hit else 0.0


def free_spot(world, center, half, ignore):
    """Al lado del horno: el primer lugar sin nada que choque encima del piso."""
    for dx, dy in ((450, 0), (-450, 0), (0, 400), (0, -400), (450, 400), (-450, 400), (450, -400), (-450, -400)):
        x, y = center.x + dx, center.y + dy
        z = floor_z(world, x, y, ignore)
        hits = unreal.SystemLibrary.box_overlap_actors(world, unreal.Vector(x, y, z + half[2] + 5), unreal.Vector(*half),
                                                       [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2], None, ignore)
        if isinstance(hits, tuple):
            hits = hits[-1]
        if not hits:
            return unreal.Vector(x, y, z)
    return unreal.Vector(center.x + 450, center.y, floor_z(world, center.x + 450, center.y, ignore))


try:
    if HEADLESS:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(".")[0] != "/Game/FactoryCtyco/Maps/L_FactoryDemo":
        raise RuntimeError("Abrir L_FactoryDemo en el editor antes de correr el script")
    level = actors.get_all_level_actors()
    users = [a for a in level if isinstance(a, unreal.StaticMeshActor) and a.get_actor_label() == LABEL]
    horno = [a for a in level if a.get_actor_label() == "Horno_Fundicion"]
    if len(horno) != 1:
        raise RuntimeError(f"Se esperaba un Horno_Fundicion, hay {len(horno)}")
    horno = horno[0]

    build = json.loads((SRC / "codo_build.json").read_text(encoding="utf-8"))
    mesh = import_fbx(users)
    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(mesh)
    if hulls != 1 or abs(max(size_cm(mesh)) - max(build["size_m"]) * 100) > 3   # abierto arriba: el alto ya no es el del GLB:
        raise RuntimeError(f"Codo inesperado: {hulls} colisiones, {size_cm(mesh)} cm")
    actor = users[0] if users else None
    if actor is None:
        half = [build["size_m"][0] * 50 + 10, build["size_m"][1] * 50 + 10, build["size_m"][2] * 50]
        spot = free_spot(world, horno.get_actor_location(), half, [horno])
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, spot, unreal.Rotator())
        actor.set_actor_label(LABEL)
        actor.set_folder_path("Fabrica")
    actor.modify()
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.static_mesh_component.set_collision_profile_name("BlockAll")
    loc = actor.get_actor_location()
    report["codo"] = {"size_cm": size_cm(mesh), "collisions": hulls, "triangles": mesh.get_num_triangles(0),
                      "materials": [str(m.material_slot_name) for m in mesh.static_materials],
                      "actor": actor.get_actor_label(), "folder": str(actor.get_folder_path()),
                      "location": [round(loc.x), round(loc.y), round(loc.z)]}
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = True
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[CODO_METALICO] " + report["error"])
finally:
    (project / "Docs/codo_metalico_import.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
