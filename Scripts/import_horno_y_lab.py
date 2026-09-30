"""Editor Python (con L_FactoryDemo abierto; sirve con el editor abierto): horno de fundicion y laboratorio (30/09).

- /Game/FactoryCtyco/Environments/HornoFundicion/SM_HornoFundicion (author_horno_fundicion.py): actor `Horno_Fundicion`
  (StaticMeshActor, carpeta Fabrica) en un lugar libre del piso de la fabrica, para que el usuario lo ubique.
- /Game/FactoryCtyco/Environments/Lab1/SM_Lab1 (author_lab_scene.py), con colision "complex as simple" (la propia malla):
  actor `Lab1_Escena` (carpeta Lab1) al este de la fabrica, sobre el piso de afuera, para que el usuario lo ubique.
Si los actores ya existen solo se les cambia la malla (se conserva la posicion ajustada a mano). Borra los assets
antes de importar: reimportar encima dejaba las mallas al 1 %. Guarda assets y nivel.
Informe: Docs/horno_y_lab_import.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}
FURNACE_SPOTS = [(0, -500), (0, 500), (-500, -500), (500, -500), (-500, 500), (500, 500)]   # piso de la fabrica
LAB_SPOT = unreal.Vector(3800, 0, 0)   # al este de la fabrica y del ascensor, sobre Piso_Exterior


def import_fbx(fbx, dest, name, users):
    path = f"{dest}/{name}"
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
    task.filename = str(fbx)
    task.destination_path = dest
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(dest, only_if_is_dirty=True, recursive=True)   # materiales y texturas
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    return mesh


def size_cm(mesh):
    b = mesh.get_bounding_box()
    return [round(b.max.x - b.min.x), round(b.max.y - b.min.y), round(b.max.z - b.min.z)]


def place(label, folder, mesh, spot, users):
    actor = users[0] if users else None
    if actor is None:
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, spot, unreal.Rotator())
        actor.set_actor_label(label)
        actor.set_folder_path(folder)
    for a in users or [actor]:
        a.modify()
        a.static_mesh_component.set_static_mesh(mesh)
        a.static_mesh_component.set_collision_profile_name("BlockAll")
    loc = actor.get_actor_location()
    return [round(loc.x), round(loc.y), round(loc.z)]


def free_spot(world, half):
    """El primer lugar de FURNACE_SPOTS sin nada que choque encima del piso."""
    for x, y in FURNACE_SPOTS:
        hits = unreal.SystemLibrary.box_overlap_actors(world, unreal.Vector(x, y, 110), unreal.Vector(half[0], half[1], 90),
                                                       [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2], None, [])
        if isinstance(hits, tuple):
            hits = hits[-1]
        hits = [h for h in hits or [] if h.get_actor_label() not in ("SceneRobot_Fabrica",)]
        if not hits:
            return unreal.Vector(x, y, 0)
    return unreal.Vector(*FURNACE_SPOTS[0], 0)


try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(".")[0] != "/Game/FactoryCtyco/Maps/L_FactoryDemo":
        raise RuntimeError("Abrir L_FactoryDemo en el editor antes de correr el script")
    report["dirty_before"] = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    level = actors.get_all_level_actors()
    users = lambda prefix: [a for a in level if isinstance(a, unreal.StaticMeshActor) and a.get_actor_label().startswith(prefix)]

    horno_build = json.loads((project / "SourceAssets/HornoFundicion/horno_build.json").read_text(encoding="utf-8"))
    horno = import_fbx(project / "SourceAssets/HornoFundicion/SM_HornoFundicion.fbx", "/Game/FactoryCtyco/Environments/HornoFundicion",
                       "SM_HornoFundicion", users("Horno_Fundicion"))
    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(horno)
    if hulls != 1 or abs(size_cm(horno)[2] - horno_build["height_m"] * 100) > 3:
        raise RuntimeError(f"Horno inesperado: {hulls} colisiones, {size_cm(horno)} cm")
    half = [horno_build["size_m"][0] * 50 + 20, horno_build["size_m"][1] * 50 + 20]
    report["horno"] = {"size_cm": size_cm(horno), "collisions": hulls, "triangles": horno.get_num_triangles(0),
                       "materials": [str(m.material_slot_name) for m in horno.static_materials],
                       "location": place("Horno_Fundicion", "Fabrica", horno, free_spot(world, half), users("Horno_Fundicion"))}

    lab = import_fbx(project / "SourceAssets/Lab1/SM_Lab1.fbx", "/Game/FactoryCtyco/Environments/Lab1", "SM_Lab1", users("Lab1_Escena"))
    body = lab.get_editor_property("body_setup")
    body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    lab.set_editor_property("body_setup", body)
    if not lib.save_loaded_asset(lab, False):
        raise RuntimeError("No se pudo guardar SM_Lab1")
    report["lab"] = {"size_cm": size_cm(lab), "triangles": lab.get_num_triangles(0), "materials": len(lab.static_materials),
                     "collision": str(lab.get_editor_property("body_setup").get_editor_property("collision_trace_flag")),
                     "location": place("Lab1_Escena", "Lab1", lab, LAB_SPOT, users("Lab1_Escena"))}

    # el piso del laboratorio y el del horno se pisan (rayo hacia abajo)
    def floor(x, y):
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 1000), unreal.Vector(x, y, -300),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, False)
        return (round(hit.to_tuple()[4].z, 1), hit.to_tuple()[9].get_actor_label()) if hit else None
    report["floor_probe"] = {"lab_centro": floor(LAB_SPOT.x + 150, LAB_SPOT.y + 150), "lab_borde": floor(LAB_SPOT.x - 900, LAB_SPOT.y)}

    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = True
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[HORNO_LAB] " + report["error"])
(project / "Docs/horno_y_lab_import.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
