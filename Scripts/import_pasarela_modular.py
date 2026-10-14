"""Editor Python (con L_FactoryDemo abierto): las pasarelas armadas por piezas (03/10).

- Importa las piezas de author_pasarela_modular.py (SourceAssets/Pasarelas/Modular) con su caja de colision (UCX):
  las de la L (SM_PasarelaPiso/Baranda/Poste) en /Game/FactoryCtyco/Environments/Pasarelas/Modular y las de la recta
  (SM_PasarelaRectaPiso/Baranda/Poste) en .../Modular/Recta (cada modelo trae Image_0.. y Material_0: en la misma
  carpeta se pisarian). Las tres de un modelo comparten el material, que se importa con la primera.
- Cambia `Pasarela_L` (si todavia es la malla fija) por un AFactoryWalkwayL, y cada actor con la malla fija
  SM_PasarelaRecta (Pasarela_Recta, Pasarela_Recta2...) por un AFactoryWalkwayStraight: mismo lugar, giro, nombre y
  carpeta. Si la malla fija estaba estirada, el estiramiento pasa a las medidas (largo y ancho) y el actor queda a
  escala 1. Sus barandas y extremos se mueven con las manijas del viewport y el piso las sigue.
Informe: Docs/pasarela_modular.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
ROOT = "/Game/FactoryCtyco/Environments/Pasarelas/Modular"
SETS = {ROOT: ["SM_PasarelaPiso", "SM_PasarelaBaranda", "SM_PasarelaPoste"],
        f"{ROOT}/Recta": ["SM_PasarelaRectaPiso", "SM_PasarelaRectaBaranda", "SM_PasarelaRectaPoste"]}
STRAIGHT_MESH = "/Game/FactoryCtyco/Environments/Pasarelas/Recta/SM_PasarelaRecta"
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
    task.filename = str(project / f"SourceAssets/Pasarelas/Modular/{name}.fbx")
    task.destination_path, task.destination_name = dest, name
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(f"{dest}/{name}")
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    return mesh


def replace(old, cls):
    """A walkway actor in old's place (same transform without its scale, label and folder); old is destroyed."""
    t = old.get_actor_transform()
    new = actors.spawn_actor_from_class(cls, t.translation, t.rotation.rotator())
    label, folder = old.get_actor_label(), str(old.get_folder_path())
    actors.destroy_actor(old)
    new.set_actor_label(label)
    new.set_folder_path(folder)
    return new, t.scale3d


try:
    # piezas de nuevo desde cero (reimportar encima dejaba la malla al 1 %); los actores las sueltan antes
    for a in actors.get_all_level_actors():
        if isinstance(a, unreal.FactoryWalkway):
            for c in (a.deck, a.rails, a.posts):
                c.set_static_mesh(None)
    meshes = {}
    for dest, names in SETS.items():
        if lib.does_directory_exist(dest):
            for old in lib.list_assets(dest, recursive=False, include_folder=False):
                lib.delete_asset(old.split(".")[0])
        for i, name in enumerate(names):
            meshes[name] = import_piece(dest, name, i == 0)
        material = meshes[names[0]].get_material(0)
        for name in names:
            mesh = meshes[name]
            if mesh.get_material(0) != material:
                mesh.set_material(0, material)
            body = mesh.get_editor_property("body_setup")
            body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
            mesh.set_editor_property("body_setup", body)
            lib.save_loaded_asset(mesh)
            geom = body.get_editor_property("agg_geom")
            b = mesh.get_bounding_box()
            report["piezas"][name] = {"tamano_cm": [round(b.max.x - b.min.x, 1), round(b.max.y - b.min.y, 1), round(b.max.z - b.min.z, 1)],
                                      "triangulos": mesh.get_num_triangles(0),
                                      "colision": len(geom.get_editor_property("box_elems")) + len(geom.get_editor_property("convex_elems"))}
        lib.save_directory(dest, only_if_is_dirty=True, recursive=True)

    walks = []
    for a in actors.get_all_level_actors():
        mesh = a.static_mesh_component.static_mesh if isinstance(a, unreal.StaticMeshActor) else None
        path = mesh.get_path_name().split(".")[0] if mesh else ""
        if a.get_actor_label() == "Pasarela_L" and isinstance(a, unreal.StaticMeshActor):
            new, _ = replace(a, unreal.FactoryWalkwayL)
            walks.append(new)
        elif path == STRAIGHT_MESH:
            new, scale = replace(a, unreal.FactoryWalkwayStraight)
            # el estiramiento de la malla fija pasa a las medidas
            new.set_editor_property("start_x", -495.0 * scale.x)
            new.set_editor_property("end_x", 495.0 * scale.x)
            new.set_editor_property("left_rail_y", -110.0 * scale.y)
            new.set_editor_property("right_rail_y", 110.0 * scale.y)
            walks.append(new)
        elif isinstance(a, unreal.FactoryWalkway):
            walks.append(a)
    for w in walks:
        straight = isinstance(w, unreal.FactoryWalkwayStraight)
        prefix = "SM_PasarelaRecta" if straight else "SM_Pasarela"
        w.set_editor_property("deck_mesh", meshes[prefix + "Piso"])
        w.set_editor_property("rail_mesh", meshes[prefix + "Baranda"])
        w.set_editor_property("post_mesh", meshes[prefix + "Poste"])
        w.rebuild()
        loc = w.get_actor_location()
        report["actores"].append({"nombre": w.get_actor_label(), "clase": w.get_class().get_name(),
                                  "lugar": [round(loc.x), round(loc.y), round(loc.z)], "yaw": round(w.get_actor_rotation().yaw, 1),
                                  "piezas": [w.deck.get_instance_count(), w.rails.get_instance_count(), w.posts.get_instance_count()]})
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = all(p["colision"] > 0 for p in report["piezas"].values()) and all(r["piezas"][0] > 0 for r in report["actores"])
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[PASARELA_MODULAR] " + report["error"])
(project / "Docs/pasarela_modular.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
