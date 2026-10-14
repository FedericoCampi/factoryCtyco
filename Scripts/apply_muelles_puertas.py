"""Editor Python (05/10): las puertas de personal del muelle, que se abren solas.

author_muelles.py saca del edificio las dos hojas (con su manija) y exporta una, SM_MuellePuertaPersonal, con el origen
en la bisagra; detras de cada puerta hay un pasaje en L hasta adentro del edificio. Importa esa hoja (con los materiales
de SM_Muelles) y pone `Puerta_Muelle_Personal_0` y `_1` (AFactoryAutoDoor, carpeta Muelles), enganchadas a
Muelles_Carga en la bisagra de cada una (muelles_build.json, "man_doors"): se abren hacia el lado contrario del que
llega el personaje. Ademas, Bloqueo_PuertaEstacionamiento (la caja que tapaba la puerta vieja del estacionamiento, ya
cerrada con pared en author_parking_scene.py) deja de verse en el editor y conserva su colision.
Con el editor abierto (crear actores sin ventana se cae). Guarda el nivel. Informe: Docs/muelles_puertas.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/Muelles"
NAME = "SM_MuellePuertaPersonal"
lib = unreal.EditorAssetLibrary
report = {"passed": False}

try:
    build = json.loads((project / "SourceAssets/Muelles/muelles_build.json").read_text(encoding="utf-8"))
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level = actors.get_all_level_actors()
    by = {a.get_actor_label(): a for a in level}
    for a in level:
        if isinstance(a, unreal.FactoryAutoDoor) and a.get_actor_label().startswith("Puerta_Muelle_Personal_"):
            a.get_editor_property("leaf").set_static_mesh(None)
    path = f"{DEST}/{NAME}"
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {path}")
    options = unreal.FbxImportUI()
    options.import_mesh, options.import_as_skeletal = True, False
    options.import_materials = options.import_textures = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes, data.auto_generate_collision = True, False
    data.convert_scene = data.convert_scene_unit = True
    task = unreal.AssetImportTask()
    task.filename = str(project / f"SourceAssets/Muelles/{NAME}.fbx")
    task.destination_path, task.destination_name = DEST, NAME
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    leaf = unreal.load_asset(path)
    if not isinstance(leaf, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {NAME}")
    # los materiales por nombre de ranura: la hoja es "Sectional door" (hoy solo en los portones) y la manija
    # "Leveler plate" (en el edificio)
    by_slot = {}
    for source in (f"{DEST}/SM_Muelles", f"{DEST}/SM_PortonMuelle"):
        for m in unreal.load_asset(source).static_materials:
            if m.material_interface:
                by_slot[str(m.material_slot_name).lower().replace("_", " ")] = m.material_interface
    leaf.modify()
    for index, slot in enumerate(leaf.static_materials):
        material = by_slot.get(str(slot.material_slot_name).lower().replace("_", " "))
        if material:
            leaf.set_material(index, material)
    lib.save_loaded_asset(leaf, False)
    b = leaf.get_bounding_box()
    size = [round(b.max.x - b.min.x), round(b.max.y - b.min.y), round(b.max.z - b.min.z)]
    if abs(size[0] - 96) > 4:
        raise RuntimeError(f"La hoja mide {size} cm")
    # origen en la bisagra: la hoja va de x -96 a 0, pegada al piso
    if abs(b.max.x) > 3 or abs(b.min.z) > 3:
        raise RuntimeError(f"La hoja no tiene el origen en la bisagra: {b.min} .. {b.max}")
    missing = [str(sl.material_slot_name) for sl in leaf.static_materials if sl.material_interface is None
               or "WorldGrid" in sl.material_interface.get_name()]
    if missing:
        raise RuntimeError(f"Ranuras sin material: {missing}")

    building = by["Muelles_Carga"]
    scale_xy = building.get_actor_scale3d().x
    doors = {}
    for index, info in build["man_doors"].items():
        label = f"Puerta_Muelle_Personal_{index}"
        door = by.get(label)
        if door is None:
            door = actors.spawn_actor_from_class(unreal.FactoryAutoDoor, building.get_actor_location(), building.get_actor_rotation())
            door.set_actor_label(label)
            door.set_folder_path("Muelles")
        door.modify()
        comp = door.get_editor_property("leaf")
        comp.set_static_mesh(leaf)
        door.attach_to_actor(building, "", unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE,
                             unreal.AttachmentRule.KEEP_RELATIVE, False)
        x, y, z = info["hinge_m"]   # Blender (x, y, z) m -> Unreal (100x, -100y, 100z) cm, en el espacio del edificio
        # (07/10) la hoja original (0,96 x 2,10 m) quedaba chica en el vano del marco (1,60 x 2,30 m): se estira para
        # llenarlo, con 1 cm de luz a cada lado, y la bisagra va al borde del vano
        x0, x1, sill, top = info.get("opening_m", (x, x + info["width_m"], z, z + size[2] / 100))
        width_m = x1 - x0 - 0.02
        comp.set_editor_property("relative_location", unreal.Vector((x0 + 0.01) * 100, -y * 100, (sill + 0.005) * 100))
        comp.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 180))   # la hoja corre hacia -X desde la bisagra
        comp.set_editor_property("relative_scale3d", unreal.Vector(width_m * 100 / size[0], 1, (top - sill - 0.015) * 100 / size[2]))
        door.set_editor_property("width", width_m * 100 * scale_xy)
        door.set_editor_property("open_radius", 200.0)
        door.set_editor_property("open_away_from_pawn", True)
        loc = door.get_actor_location()
        doors[label] = [round(loc.x), round(loc.y), round(loc.z), round(door.get_actor_rotation().yaw)]
        sc = comp.get_world_scale()
        doors[label + "_hoja_cm"] = [round(size[0] * sc.x), round(size[1] * sc.y), round(size[2] * sc.z)]

    blocker = by.get("Bloqueo_PuertaEstacionamiento")
    if blocker:
        blocker.modify()
        blocker.static_mesh_component.set_visibility(False)   # no se dibuja (tampoco en el editor); sigue chocando
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, leaf_size_cm=size, doors=doors, blocker_hidden=bool(blocker))
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[MUELLES_PUERTAS] " + report["error"])
finally:
    (project / "Docs/muelles_puertas.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
