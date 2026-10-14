"""Editor Python (con L_FactoryDemo abierto): las pasarelas nuevas, armadas por piezas como las viejas (07/10).

- Importa las piezas de author_pasarelas_nuevas_modular.py (SourceAssets/Pasarelas/ModularNuevas) con su caja de
  colision (UCX) en /Game/FactoryCtyco/Environments/Pasarelas/ModularNuevas/<Verde|LElevada> (cada modelo trae Image_0..
  y Material_0: en la misma carpeta se pisarian). Las tres de un modelo comparten el material de la primera. Comprueba
  el tamano de cada una (importar sobre un nombre que ya existio la dejaba al 1 %).
- Cambia `Pasarela_Verde` (si todavia es la malla fija) por un AFactoryWalkwayStraight y `Pasarela_L_Elevada` por un
  AFactoryWalkwayL, con las medidas del modelo y en el mismo lugar (el giro se ajusta: la recta del modelo corre a lo
  largo de Y; la L tiene la esquina en +X+Y). Si ya son pasarelas por piezas, solo les pone las piezas (se conservan
  sus medidas). Sus barandas y puntas se mueven con las manijas del viewport y el piso las sigue.
- (07/10) Las patas son una pieza aparte (LegMesh, choca con su propia malla): con DeckHeight o el rombo de altura el
  piso sube o baja y las patas se estiran hasta el suelo, para pasar por debajo. Se conserva la altura que tenga.
Guarda el nivel. Informe: Docs/pasarelas_nuevas_modular.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SRC = project / "SourceAssets/Pasarelas/ModularNuevas"
ROOT = "/Game/FactoryCtyco/Environments/Pasarelas/ModularNuevas"
# modelo: actor, clase, giro que se suma al del actor fijo, medidas (cm, en el espacio del actor nuevo)
WALKS = {
    "Verde": ("Pasarela_Verde", unreal.FactoryWalkwayStraight, 90.0,
              dict(left_rail_y=-51.5, right_rail_y=51.5, start_x=-297.0, end_x=297.0)),
    "LElevada": ("Pasarela_L_Elevada", unreal.FactoryWalkwayL, 180.0,
                 dict(outer_a=-321.5, inner_a=-210.0, outer_b=-325.0, inner_b=-212.0, end_a=341.5, end_b=340.7)),
}
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


try:
    build = json.loads((SRC / "modular_nuevas_build.json").read_text(encoding="utf-8"))
    level = actors.get_all_level_actors()
    by = {a.get_actor_label(): a for a in level}
    # las pasarelas que ya usan estas piezas las sueltan antes de borrarlas
    for model in WALKS:
        for a in level:
            if isinstance(a, unreal.FactoryWalkway) and a.deck.static_mesh and f"/ModularNuevas/{model}/" in a.deck.static_mesh.get_path_name():
                for c in (a.deck, a.rails, a.posts):
                    c.set_static_mesh(None)
    for model, (label, cls, turn, dims) in WALKS.items():
        info = build[model]
        dest = f"{ROOT}/{model}"
        if lib.does_directory_exist(dest):
            for old in lib.list_assets(dest, recursive=False, include_folder=False):
                lib.delete_asset(old.split(".")[0])
        names = list(info["pieces"])
        meshes = {}
        for i, name in enumerate(names):
            mesh = import_piece(dest, name, i == 0)
            b = mesh.get_bounding_box()
            size = [round(b.max.x - b.min.x, 1), round(b.max.y - b.min.y, 1), round(b.max.z - b.min.z, 1)]
            if abs(size[0] - info["pieces"][name]["size_cm"][0]) > 2:
                raise RuntimeError(f"{name} mide {size} cm (se esperaba {info['pieces'][name]['size_cm']})")
            meshes[name] = mesh
        material = meshes[names[0]].get_material(0)
        for name, mesh in meshes.items():
            if mesh.get_material(0) != material:
                mesh.set_material(0, material)
            body = mesh.get_editor_property("body_setup")
            # las patas chocan con su forma (se camina entre ellas); el resto, con su caja UCX
            body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
                                     if name.endswith("Patas") else unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
            mesh.set_editor_property("body_setup", body)
            lib.save_loaded_asset(mesh)
            geom = body.get_editor_property("agg_geom")
            b = mesh.get_bounding_box()
            report["piezas"][name] = {"tamano_cm": [round(b.max.x - b.min.x, 1), round(b.max.y - b.min.y, 1), round(b.max.z - b.min.z, 1)],
                                      "triangulos": mesh.get_num_triangles(0),
                                      "colision": "compleja" if name.endswith("Patas") else
                                      len(geom.get_editor_property("box_elems")) + len(geom.get_editor_property("convex_elems"))}
        lib.save_directory(dest, only_if_is_dirty=True, recursive=True)

        deck, rail, post, legs = (info["pieces"][n] for n in names)
        old = by.get(label)
        if old is None:
            raise RuntimeError(f"No esta {label} en el nivel")
        if isinstance(old, cls):
            walk = old
        else:
            t = old.get_actor_transform()
            rot = t.rotation.rotator()
            walk = actors.spawn_actor_from_class(cls, t.translation, unreal.Rotator(rot.roll, rot.pitch, rot.yaw + turn))
            folder = str(old.get_folder_path())
            actors.destroy_actor(old)
            walk.set_actor_label(label)
            walk.set_folder_path("Fabrica" if folder == "Despacho" else folder)
            for key, value in dims.items():
                walk.set_editor_property(key, value)
        walk.set_editor_property("deck_mesh", meshes[names[0]])
        walk.set_editor_property("rail_mesh", meshes[names[1]])
        walk.set_editor_property("post_mesh", meshes[names[2]])
        walk.set_editor_property("leg_mesh", meshes[names[3]])
        walk.set_editor_property("piece_deck_top", info["deck_top_cm"])
        walk.set_editor_property("piece_leg_top", info["leg_top_cm"])
        walk.set_editor_property("deck_piece_size", unreal.Vector2D(deck["cut_length_cm"], deck["size_cm"][1]))
        walk.set_editor_property("deck_past_rail", (deck["size_cm"][1] - info["rails_apart_cm"]) / 2)
        walk.set_editor_property("rail_piece_length", rail["cut_length_cm"])
        walk.set_editor_property("post_width", post["cut_length_cm"])
        walk.set_editor_property("post_spacing", info["post_spacing_cm"])
        walk.rebuild()
        loc = walk.get_actor_location()
        o, e = walk.get_actor_bounds(False)
        report["actores"].append({"nombre": label, "clase": walk.get_class().get_name(), "lugar": [round(loc.x), round(loc.y), round(loc.z)],
                                  "yaw": round(walk.get_actor_rotation().yaw, 1),
                                  "caja_cm": [round(o.x - e.x), round(o.y - e.y), round(o.x + e.x), round(o.y + e.y), round(o.z + e.z)],
                                  "altura_piso_cm": round(walk.get_editor_property("deck_height"), 1),
                                  "piso_cm": round(loc.z + walk.get_editor_property("deck_height"), 1),
                                  "piezas": [walk.deck.get_instance_count(), walk.rails.get_instance_count(), walk.posts.get_instance_count(),
                                             walk.legs.get_instance_count()]})
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = all(p["colision"] for p in report["piezas"].values()) and all(r["piezas"][0] > 0 for r in report["actores"])
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[PASARELAS_NUEVAS] " + report["error"])
finally:
    (project / "Docs/pasarelas_nuevas_modular.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
