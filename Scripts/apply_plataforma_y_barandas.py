"""Editor Python (con L_FactoryDemo abierto): la plataforma industrial por piezas y la baranda suelta (07/10).

- Importa las piezas de author_plataforma_y_barandas.py (SourceAssets/Plataformas): las de la plataforma en
  /Game/FactoryCtyco/Environments/Plataformas/Industrial y las de la baranda de la escalera en .../Plataformas/Barandas
  (cada grupo comparte el material de su primera pieza). Comprueba el tamano de cada una (importar sobre un nombre que ya
  existio la dejaba al 1 %). El piso y las barandas chocan con su caja UCX; esquinas, columnas, pies y costados con su
  propia malla (se pasa entre las patas).
- `Plataforma_Industrial` (AFactoryPlatform, carpeta Fabrica): 2,48 x 2,49 m, piso a 97,5 cm, en el primer lugar de
  piso libre de SPOTS. `Baranda_1` (AFactoryRailing, estilo Escalera) al lado, de ejemplo. Si ya existen solo se les
  ponen las piezas (se conservan su lugar y medidas).
Guarda el nivel. Informe: Docs/plataforma_y_barandas.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SRC = project / "SourceAssets/Plataformas"
GROUPS = {
    "/Game/FactoryCtyco/Environments/Plataformas/Industrial":
        ["SM_PlataformaPiso", "SM_PlataformaEsquina", "SM_PlataformaColumna", "SM_PlataformaPie", "SM_PlataformaCostado"],
    "/Game/FactoryCtyco/Environments/Plataformas/Barandas": ["SM_BarandaEscaleraTramo", "SM_BarandaEscaleraPoste"],
}
COMPLEX = ("SM_PlataformaEsquina", "SM_PlataformaColumna", "SM_PlataformaPie", "SM_PlataformaCostado")
# piso de la fabrica (z ~0): lugares candidatos para la plataforma (centro); la baranda va 2 m al costado
SPOTS = [(1000, -1300), (1300, -600), (600, -1900), (1500, -1500), (-300, -1700), (1700, 300), (900, 300)]
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False, "piezas": {}, "actores": []}


def import_piece(dest, name, with_materials):
    options = unreal.FbxImportUI()
    options.import_mesh, options.import_as_skeletal = True, False
    options.import_materials = options.import_textures = with_materials
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes, data.auto_generate_collision = True, False
    data.convert_scene = data.convert_scene_unit = True
    data.generate_lightmap_u_vs = data.build_nanite = False
    task = unreal.AssetImportTask()
    task.filename = str(SRC / f"{name}.fbx")
    task.destination_path, task.destination_name = dest, name
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(f"{dest}/{name}")
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    return mesh


def floor_at(world, x, y, ignore):
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 900), unreal.Vector(x, y, -200),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore, unreal.DrawDebugTrace.NONE, True)
    return hit.to_tuple()[4].z if hit else None


def free(world, x, y, hx, hy, ignore):
    """Floor height if the rectangle (x, y) +- (hx, hy) is flat floor near z 0 with nothing on it, else None."""
    zs = [floor_at(world, x + hx * i / 2, y + hy * j, ignore) for i in range(-2, 3) for j in (-1, 0, 1)]
    if any(z is None or abs(z) > 15 for z in zs) or max(zs) - min(zs) > 6:
        return None
    return min(zs)


try:
    build = json.loads((SRC / "plataforma_build.json").read_text(encoding="utf-8"))
    sizes = dict(build["platform"]["pieces"], **build["rail"]["pieces"])
    level = actors.get_all_level_actors()
    for a in level:   # sueltan las piezas antes de borrarlas
        if isinstance(a, unreal.FactoryPlatform):
            for c in (a.deck, a.legs, a.corners, a.feet, a.edges, a.rails, a.posts):
                c.set_static_mesh(None)
        if isinstance(a, unreal.FactoryRailing):
            for c in (a.rails, a.posts):
                c.set_static_mesh(None)
    meshes = {}
    for dest, names in GROUPS.items():
        if lib.does_directory_exist(dest):
            for old in lib.list_assets(dest, recursive=False, include_folder=False):
                lib.delete_asset(old.split(".")[0])
        for i, name in enumerate(names):
            mesh = import_piece(dest, name, i == 0)
            b = mesh.get_bounding_box()
            size = [round(b.max.x - b.min.x, 1), round(b.max.y - b.min.y, 1), round(b.max.z - b.min.z, 1)]
            if abs(size[0] - sizes[name]["size_cm"][0]) > 2:
                raise RuntimeError(f"{name} mide {size} cm (se esperaba {sizes[name]['size_cm']})")
            meshes[name] = mesh
        material = meshes[names[0]].get_material(0)
        for name in names:
            mesh = meshes[name]
            if mesh.get_material(0) != material:
                mesh.set_material(0, material)
            body = mesh.get_editor_property("body_setup")
            body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
                                     if name in COMPLEX else unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
            mesh.set_editor_property("body_setup", body)
            lib.save_loaded_asset(mesh)
            b = mesh.get_bounding_box()
            report["piezas"][name] = {"tamano_cm": [round(b.max.x - b.min.x, 1), round(b.max.y - b.min.y, 1), round(b.max.z - b.min.z, 1)],
                                      "triangulos": mesh.get_num_triangles(0),
                                      "colision": "compleja" if name in COMPLEX else "caja"}
        lib.save_directory(dest, only_if_is_dirty=True, recursive=True)

    P = build["platform"]
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    by = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    plat = by.get("Plataforma_Industrial")
    if plat is None:
        spot = None
        for x, y in SPOTS:   # la plataforma (2,5 m) y la baranda de ejemplo 2 m al costado: 2,5 x 5 m libres
            z = free(world, x, y + 100, 140, 290, [])
            if z is not None:
                spot = unreal.Vector(x, y, z)
                break
        if spot is None:
            spot = unreal.Vector(SPOTS[0][0], SPOTS[0][1], 0)
            report["aviso"] = "ningun lugar libre de la lista: queda en el primero"
        plat = actors.spawn_actor_from_class(unreal.FactoryPlatform, spot, unreal.Rotator())
        plat.set_actor_label("Plataforma_Industrial")
        plat.set_folder_path("Fabrica")
        hx, hy = P["half_cm"]
        for key, value in dict(min_x=-hx, max_x=hx, min_y=-hy, max_y=hy).items():
            plat.set_editor_property(key, value)
    plat.set_editor_property("corner_mesh", meshes["SM_PlataformaEsquina"])
    plat.set_editor_property("foot_mesh", meshes["SM_PlataformaPie"])
    plat.set_editor_property("edge_mesh", meshes["SM_PlataformaCostado"])
    plat.set_editor_property("leg_mesh", meshes["SM_PlataformaColumna"])
    plat.set_editor_property("deck_mesh", meshes["SM_PlataformaPiso"])
    plat.set_editor_property("corner_size", P["corner_cm"])
    plat.set_editor_property("edge_piece_length", P["edge_length_cm"])
    plat.set_editor_property("deck_piece_width", P["deck_cm"])
    plat.set_editor_property("foot_top", P["foot_top_cm"])
    plat.set_editor_property("piece_leg_top", P["column_top_cm"])
    plat.set_editor_property("piece_deck_top", P["deck_top_cm"])
    plat.rebuild()

    rail = by.get("Baranda_1")
    if rail is None:
        loc = plat.get_actor_location()
        rail = actors.spawn_actor_from_class(unreal.FactoryRailing, unreal.Vector(loc.x - 171, loc.y + 230, loc.z), unreal.Rotator())
        rail.set_actor_label("Baranda_1")
        rail.set_folder_path("Fabrica")
    rail.rebuild()

    for a in (plat, rail):
        loc = a.get_actor_location()
        o, e = a.get_actor_bounds(False)
        entry = {"nombre": a.get_actor_label(), "clase": a.get_class().get_name(), "lugar": [round(loc.x), round(loc.y), round(loc.z)],
                 "caja_cm": [round(o.x - e.x), round(o.y - e.y), round(o.z - e.z), round(o.x + e.x), round(o.y + e.y), round(o.z + e.z)]}
        if a == plat:
            entry["piezas"] = {"esquinas": a.corners.get_instance_count(), "columnas": a.legs.get_instance_count(),
                               "pies": a.feet.get_instance_count(), "costados": a.edges.get_instance_count(),
                               "piso": a.deck.get_instance_count()}
            entry["altura_piso_cm"] = round(a.get_editor_property("deck_height"), 1)
        else:
            entry["piezas"] = {"tramos": a.rails.get_instance_count(), "postes": a.posts.get_instance_count()}
        report["actores"].append(entry)
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    pl, rl = report["actores"]
    report["passed"] = pl["piezas"]["esquinas"] == 4 and pl["piezas"]["costados"] == 4 and rl["piezas"]["tramos"] > 0
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[PLATAFORMA] " + report["error"])
finally:
    (project / "Docs/plataforma_y_barandas.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
