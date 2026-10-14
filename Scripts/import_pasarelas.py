"""Editor Python (con L_FactoryDemo abierto): las dos pasarelas del usuario (03/10).

- Importa SourceAssets/Pasarelas/SM_PasarelaRecta.fbx y SM_PasarelaL.fbx (author_pasarelas.py) en
  /Game/FactoryCtyco/Environments/Pasarelas/<Recta|L> con sus materiales y texturas (una carpeta cada una: las dos traen
  Image_0..3 y Material_0 y se pisarian). Chocan con su propia malla (complex as
  simple): se camina arriba, como en Escalera_Plataforma. Borra el asset antes (reimportar encima lo dejaba al 1 %).
- Actores `Pasarela_Recta` y `Pasarela_L` (StaticMeshActor, carpeta Fabrica) al lado de Escalera_Plataforma, con su
  piso a la altura del de la plataforma, en el primer lugar libre de SPOTS, para que el usuario las acomode. Si ya
  existen solo se les cambia la malla (se conserva su lugar).
Informe: Docs/pasarelas.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
ROOT = "/Game/FactoryCtyco/Environments/Pasarelas"
MODELS = {"SM_PasarelaRecta": "Pasarela_Recta", "SM_PasarelaL": "Pasarela_L"}
FOLDERS = {"SM_PasarelaRecta": "Recta", "SM_PasarelaL": "L"}
# al oeste y al sur de la plataforma (centro 330, -550; piso de x -6 a 360, y -845 a -270)
SPOTS = [(-500, -550), (-300, -1250), (330, -1250), (-500, -1250), (-500, 150), (1200, -300)]
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False, "pasarelas": []}


def import_mesh(name):
    dest = f"{ROOT}/{FOLDERS[name]}"
    path = f"{dest}/{name}"
    for old in lib.list_assets(dest, recursive=False, include_folder=False) if lib.does_directory_exist(dest) else []:
        if not lib.delete_asset(old.split(".")[0]):
            raise RuntimeError(f"No se pudo borrar {old}")
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
    task.filename = str(project / f"SourceAssets/Pasarelas/{name}.fbx")
    task.destination_path, task.destination_name = dest, name
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(dest, only_if_is_dirty=True, recursive=True)
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    body = mesh.get_editor_property("body_setup")
    body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    mesh.set_editor_property("body_setup", body)
    lib.save_loaded_asset(mesh)
    return mesh


try:
    # lo que quedo suelto en la carpeta comun de una corrida anterior (antes de separar en subcarpetas)
    for old in lib.list_assets(ROOT, recursive=False, include_folder=False) if lib.does_directory_exist(ROOT) else []:
        lib.delete_asset(old.split(".")[0])
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    build = json.loads((project / "SourceAssets/Pasarelas/pasarelas_build.json").read_text(encoding="utf-8"))
    level = actors.get_all_level_actors()
    by = {a.get_actor_label(): a for a in level}
    stairs = by.get("Escalera_Plataforma")
    deck_top = 204.4 + (stairs.get_actor_location().z if stairs else 0.0)
    ignore = [a for a in level if a.get_actor_label().startswith("SceneRobot") or a.get_actor_label().startswith("Piso")]
    taken = []
    for name, label in MODELS.items():
        users = [a for a in level if isinstance(a, unreal.StaticMeshActor) and a.get_actor_label() == label]
        for a in users:
            a.static_mesh_component.set_static_mesh(None)
        mesh = import_mesh(name)
        b = mesh.get_bounding_box()
        size = b.max - b.min
        actor = users[0] if users else None
        if actor is None:
            z = deck_top - build[name]["deck_m"] * 100
            half = unreal.Vector(size.x / 2 + 20, size.y / 2 + 20, size.z / 2)
            spot = None
            for x, y in SPOTS:
                if any(abs(x - tx) < (size.x + tsx) / 2 and abs(y - ty) < (size.y + tsy) / 2 for tx, ty, tsx, tsy in taken):
                    continue
                hits = unreal.SystemLibrary.box_overlap_actors(world, unreal.Vector(x, y, z + half.z), half,
                                                               [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2], None, ignore)
                if isinstance(hits, tuple):
                    hits = hits[-1]
                if not hits:
                    spot = unreal.Vector(x, y, z)
                    break
            if spot is None:
                spot = unreal.Vector(SPOTS[-1][0], SPOTS[-1][1], z)
            taken.append((spot.x, spot.y, size.x, size.y))
            actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, spot, unreal.Rotator())
            actor.set_actor_label(label)
            actor.set_folder_path("Fabrica")
        for a in users or [actor]:
            a.modify()
            a.static_mesh_component.set_static_mesh(mesh)
            a.static_mesh_component.set_collision_profile_name("BlockAll")
        loc = actor.get_actor_location()
        report["pasarelas"].append({
            "actor": label, "malla": mesh.get_path_name().split(".")[0], "lugar": [round(loc.x), round(loc.y), round(loc.z)],
            "tamano_cm": [round(size.x), round(size.y), round(size.z)], "piso_cm": round(loc.z + build[name]["deck_m"] * 100, 1),
            "triangulos": mesh.get_num_triangles(0), "materiales": len(mesh.static_materials),
            "colision": str(mesh.get_editor_property("body_setup").get_editor_property("collision_trace_flag"))})
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = len(report["pasarelas"]) == 2
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[PASARELAS] " + report["error"])
(project / "Docs/pasarelas.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
