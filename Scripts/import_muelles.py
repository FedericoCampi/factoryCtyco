"""Editor Python (con L_FactoryDemo abierto): escena de muelles de carga del usuario (03/10).

- Importa SourceAssets/Muelles/SM_Muelles.fbx (author_muelles.py) en /Game/FactoryCtyco/Environments/Muelles con sus
  materiales y texturas. Choca con su propia malla (complex as simple). Borra el asset antes (reimportar encima lo
  dejaba al 1 %).
- Actor `Muelles_Carga` (StaticMeshActor, carpeta Muelles) al norte del estacionamiento, detras de su muro norte (el
  paralelo a la calle de los camiones): el edificio del muelle (lado -Y de la escena) pegado a ese muro, centrado en
  el estacionamiento, y el patio con los tres cajones hacia +Y. El patio queda a la altura del piso del
  estacionamiento (z 10). Para que el usuario lo acomode; si ya existe solo se le cambia la malla (se conserva su
  lugar).
Informe: Docs/muelles_import.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/Muelles"
NAME = "SM_Muelles"
LABEL = "Muelles_Carga"
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}

try:
    build = json.loads((project / "SourceAssets/Muelles/muelles_build.json").read_text(encoding="utf-8"))
    level = actors.get_all_level_actors()
    by = {a.get_actor_label(): a for a in level}
    users = [a for a in level if isinstance(a, unreal.StaticMeshActor) and a.get_actor_label() == LABEL]
    for a in users:
        a.static_mesh_component.set_static_mesh(None)
    path = f"{DEST}/{NAME}"
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
    task.filename = str(project / f"SourceAssets/Muelles/{NAME}.fbx")
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

    actor = users[0] if users else None
    if actor is None:
        # el borde del lado del edificio contra el borde norte del estacionamiento: en Unreal la Y del GLB se invierte,
        # asi que ese borde (la Y maxima del GLB) queda a -max_m de su origen
        parking = by["Parking_Estacionamiento"]
        o, e = parking.get_actor_bounds(False)
        north = o.y + e.y
        spot = unreal.Vector(o.x, north + build["max_m"][1] * 100, 10)
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, spot, unreal.Rotator())
        actor.set_actor_label(LABEL)
        actor.set_folder_path("Muelles")
    for a in users or [actor]:
        a.modify()
        a.static_mesh_component.set_static_mesh(mesh)
        a.static_mesh_component.set_collision_profile_name("BlockAll")
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    loc = actor.get_actor_location()
    o, e = actor.get_actor_bounds(False)
    b = mesh.get_bounding_box()
    report.update(passed=True, actor=LABEL, location=[round(loc.x), round(loc.y), round(loc.z)],
                  bounds_min=[round(o.x - e.x), round(o.y - e.y), round(o.z - e.z)],
                  bounds_max=[round(o.x + e.x), round(o.y + e.y), round(o.z + e.z)],
                  size_cm=[round(b.max.x - b.min.x), round(b.max.y - b.min.y), round(b.max.z - b.min.z)],
                  triangles=mesh.get_num_triangles(0), materials=len(mesh.static_materials),
                  collision=str(mesh.get_editor_property("body_setup").get_editor_property("collision_trace_flag")))
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[MUELLES] " + report["error"])
(project / "Docs/muelles_import.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
