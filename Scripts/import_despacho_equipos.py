"""Editor Python (con L_FactoryDemo abierto): los cuatro modelos del usuario en la escena del despacho (07/10).

- Importa SourceAssets/DespachoEquipos/<SM>.fbx (author_despacho_equipos.py) en
  /Game/FactoryCtyco/Environments/DespachoEquipos/<carpeta> con sus materiales y texturas (una carpeta cada uno: todos
  traen Image_0.. y Material_0 y se pisarian). Chocan con su propia malla (complex as simple): las pasarelas se caminan.
  Borra los assets antes (reimportar encima lo dejaba al 1 %).
- Actores (StaticMeshActor, carpeta Despacho) en el primer lugar libre de SPOTS, en el estacionamiento (dentro de
  Escena_Despacho), apoyados en el piso, para que el usuario los acomode. Si ya existen solo se les cambia la malla
  (se conserva su lugar).
Informe: Docs/despacho_equipos.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
ROOT = "/Game/FactoryCtyco/Environments/DespachoEquipos"
# malla: (actor, carpeta del contenido)
MODELS = {
    "SM_Flejadora": ("Flejadora", "Flejadora"),
    "SM_EscanerRayosX": ("Escaner_RayosX", "EscanerRayosX"),
    "SM_PasarelaVerde": ("Pasarela_Verde", "PasarelaVerde"),
    "SM_PasarelaLElevada": ("Pasarela_L_Elevada", "PasarelaLElevada"),
    "SM_TunelRechazo": ("Tunel_Rechazo", "TunelRechazo"),
    "SM_TolvasGemelas": ("Tolvas_Gemelas", "TolvasGemelas"),   # 08/10, en el patio de los muelles
}
# para importar solo algunos, definir ONLY = ["SM_..."] antes de correr el script (las pasarelas ya son por piezas:
# apply_pasarelas_nuevas_modular.py; volver a importarlas pondria otra vez la malla fija)
ONLY = globals().get("ONLY") or list(MODELS)
# el estacionamiento (piso a z 10): la franja libre del medio, entre las cintas de carga y las maquinas de despacho
SPOTS = [(-3800, -100), (-3400, -100), (-4200, 100), (-3000, -250), (-3600, 250), (-4300, -100), (-3200, 200),
         (-3600, -900), (-4400, 200), (-4000, -600)]
FLOOR_Z = 10.0
# 08/10: las tolvas van al patio de los muelles (y 1000..3700), a los costados de los tres cajones de los camiones; el
# piso del patio no esta a FLOOR_Z, se toma el del rayo del centro
SPOTS_BY = {"SM_TolvasGemelas": [(-2200, 1900), (-2200, 2500), (-5000, 1900), (-5000, 2500), (-2200, 1500)]}
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False, "equipos": []}


def import_mesh(name, folder):
    dest = f"{ROOT}/{folder}"
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
    task.filename = str(project / f"SourceAssets/DespachoEquipos/{name}.fbx")
    task.destination_path, task.destination_name = dest, name
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(dest, only_if_is_dirty=True, recursive=True)
    mesh = unreal.load_asset(f"{dest}/{name}")
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    body = mesh.get_editor_property("body_setup")
    body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    mesh.set_editor_property("body_setup", body)
    lib.save_loaded_asset(mesh)
    return mesh


def free_floor(world, x, y, half, floor_z=FLOOR_Z):
    """Si en el rectangulo (x, y) +- half hay solo piso a floor_z: rayos de arriba abajo en una grilla. (07/10: con el
    modelo del estacionamiento ignorado, la flejadora quedo adentro de una pieza suya de 1,45 m.)"""
    for i in range(5):
        for j in range(3):
            px, py = x + half.x * (i / 2 - 1), y + half.y * (j - 1)
            hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(px, py, 900), unreal.Vector(px, py, -100),
                                                         unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
            if not hit or abs(hit.to_tuple()[4].z - floor_z) > 8:
                return False
    return True


try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    level = actors.get_all_level_actors()
    taken = []
    for name, (label, folder) in MODELS.items():
        if name not in ONLY:
            continue
        users = [a for a in level if isinstance(a, unreal.StaticMeshActor) and a.get_actor_label() == label]
        for a in users:
            a.static_mesh_component.set_static_mesh(None)
        mesh = import_mesh(name, folder)
        b = mesh.get_bounding_box()
        size = b.max - b.min
        actor = users[0] if users else None
        if actor is None:
            half = unreal.Vector(size.x / 2 + 30, size.y / 2 + 30, size.z / 2)
            spot = None
            spots = SPOTS_BY.get(name, SPOTS)
            for x, y in spots:
                if any(abs(x - tx) < (size.x + tsx) / 2 + 60 and abs(y - ty) < (size.y + tsy) / 2 + 60 for tx, ty, tsx, tsy in taken):
                    continue
                floor_z = FLOOR_Z
                if name in SPOTS_BY:
                    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 900), unreal.Vector(x, y, -300),
                                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
                    floor_z = hit.to_tuple()[4].z if hit else FLOOR_Z
                if free_floor(world, x, y, half, floor_z):
                    spot = unreal.Vector(x, y, floor_z)
                    break
            if spot is None:
                x, y = spots[len(taken) % len(spots)]
                spot = unreal.Vector(x, y, FLOOR_Z)
                report.setdefault("avisos", []).append(f"{label}: sin lugar libre, queda en ({x}, {y})")
            taken.append((spot.x, spot.y, size.x, size.y))
            actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, spot, unreal.Rotator())
            actor.set_actor_label(label)
            actor.set_folder_path("Muelles" if name in SPOTS_BY else "Despacho")
        for a in users or [actor]:
            a.modify()
            a.static_mesh_component.set_static_mesh(mesh)
            a.static_mesh_component.set_collision_profile_name("BlockAll")
        loc = actor.get_actor_location()
        report["equipos"].append({
            "actor": label, "malla": mesh.get_path_name().split(".")[0], "lugar": [round(loc.x), round(loc.y), round(loc.z)],
            "tamano_cm": [round(size.x), round(size.y), round(size.z)], "escena": str(unreal.FactorySceneZone.scene_of(actor)),
            "triangulos": mesh.get_num_triangles(0), "materiales": len(mesh.static_materials)})
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = len(report["equipos"]) == len(ONLY) and all(e["escena"] == "Despacho" for e in report["equipos"])
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[DESPACHO_EQUIPOS] " + report["error"])
(project / "Docs/despacho_equipos.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
