"""Editor Python (con L_FactoryDemo abierto): piedras -> sierra -> trituradora -> horno (03/10).

El usuario carga piedras a mano en la cinta corta (Cinta_Cuarzo_Triturar3). Al pasar por adentro de la caja
(Lavadora_Cuarzo) la sierra la corta en un bloque prolijo (AFactoryBeltStation Sierra_Estacion, con su caja del tamaño
del interior, y chispas naranjas en cada corte); la plataforma lo sube y lo deja caer en la tolva de la trituradora, que
de cada bloque saca 2 piedras trituradas; esas van al horno, que funde la piedra triturada.
- Mallas (author_piedras.py): SM_Piedra (M_Piedra), SM_BloquePiedra (M_BloquePiedra) y SM_PiedraTriturada.
  Recursos: DA_Stone (Piedra), DA_StoneBlock (Bloque de piedra), DA_CrushedStone (Piedra triturada), sumados a
  FactoryDemo_Simulation.
- Tamaños en porcentaje (SizeFrom / SizePercent): el bloque mide BLOCK_PERCENT de la piedra y lo triturado
  CRUSHED_PERCENT del bloque; si cambia el tamaño de la piedra (CargoSize de DA_Stone) se acomodan solos.
- La sierra tambien corta lingotes (Sierra_Estacion_Lingotes): sale un lingote cortado (DA_SiliconIngotCut) de
  INGOT_CUT_PERCENT del tamaño del lingote. La trituradora no los acepta (solo bloques de piedra).
- DB_QuartzCrusher: StoneBlock -> 2 CrushedStone. Proceso_Fundicion: funde CrushedStone («PIEDRA TRITURADA»).
- En lugar de los lingotes de prueba deja COUNT piedras (Piedra_Prueba_N, 1 cada una) en el mismo lugar.
Informe: Docs/piedras.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
MODELS = "/Game/FactoryCtyco/Factory/Models/Piedras"
MATS = "/Game/FactoryCtyco/Factory/Materials"
DEFS = "/Game/FactoryCtyco/Factory/Definitions"
START = (1860.0, -380.0)
COUNT, PER_ROW, STEP_X, STEP_Y = 10, 5, 70.0, 60.0
STONE_SIZE = 32.0         # cm, lado mayor de la piedra en bruto
BLOCK_PERCENT = 75.0      # el bloque, de la piedra
CRUSHED_PERCENT = 80.0    # lo triturado, del bloque (04/10: 60 se veia chico)
INGOT_CUT_PERCENT = 50.0  # el lingote cortado por la sierra, del lingote
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}


def color_material(name, color, metallic, roughness, specular=0.5):
    path = f"{MATS}/{name}"
    if lib.does_asset_exist(path):
        m = unreal.load_asset(path)
        mel.delete_all_material_expressions(m)
    else:
        m = tools.create_asset(name, MATS, unreal.Material, unreal.MaterialFactoryNew())
    for value, prop, y in ((color, unreal.MaterialProperty.MP_BASE_COLOR, 0), (metallic, unreal.MaterialProperty.MP_METALLIC, 120),
                           (roughness, unreal.MaterialProperty.MP_ROUGHNESS, 240), (specular, unreal.MaterialProperty.MP_SPECULAR, 360)):
        if isinstance(value, unreal.LinearColor):
            e = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -400, y)
            e.set_editor_property("constant", value)
        else:
            e = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -400, y)
            e.set_editor_property("r", value)
        mel.connect_material_property(e, "", prop)
    mel.recompile_material(m)
    lib.save_loaded_asset(m)
    return m


def import_mesh(name, mat):
    path = f"{MODELS}/{name}"
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {name}")
    options = unreal.FbxImportUI()
    options.import_mesh, options.import_as_skeletal = True, False
    options.import_materials = options.import_textures = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes, data.auto_generate_collision = True, True
    data.convert_scene = data.convert_scene_unit = True
    task = unreal.AssetImportTask()
    task.filename = str(project / f"SourceAssets/Piedras/{name}.fbx")
    task.destination_path, task.destination_name = MODELS, name
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    tools.import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    mesh.set_material(0, mat)
    lib.save_loaded_asset(mesh)
    return mesh


def resource(name, item_id, display, color, mesh, size=30.0, size_from=None, percent=100.0):
    path = f"{DEFS}/{name}"
    res = unreal.load_asset(path) if lib.does_asset_exist(path) else None
    if res is None:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property("data_asset_class", unreal.FactoryResourceDefinition)
        res = tools.create_asset(name, DEFS, unreal.FactoryResourceDefinition, factory)
    for prop, value in (("item_id", item_id), ("display_name", display), ("color", color), ("pickup_mesh", mesh),
                        ("pickup_scale", unreal.Vector(1, 1, 1)), ("cargo_size", size), ("size_from", size_from),
                        ("size_percent", percent)):
        res.set_editor_property(prop, value)
    lib.save_loaded_asset(res)
    return res


try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    level = actors.get_all_level_actors()
    by = {a.get_actor_label(): a for a in level}
    # las piedras de prueba de antes y los lingotes salen antes de reimportar las mallas
    for old in [a for a in level if a.get_actor_label().startswith(("Lingote_Prueba_", "Piedra_Prueba_"))]:
        actors.destroy_actor(old)
    for name in ("DA_Stone", "DA_StoneBlock", "DA_CrushedStone"):
        if lib.does_asset_exist(f"{DEFS}/{name}"):
            unreal.load_asset(f"{DEFS}/{name}").set_editor_property("pickup_mesh", None)

    raw = import_mesh("SM_Piedra", color_material("M_Piedra", unreal.LinearColor(0.32, 0.27, 0.22), 0.0, 0.92, 0.3))
    block_mesh = import_mesh("SM_BloquePiedra", color_material("M_BloquePiedra", unreal.LinearColor(0.6, 0.57, 0.53), 0.0, 0.55, 0.45))
    crushed_mesh = import_mesh("SM_PiedraTriturada", color_material("M_PiedraTriturada", unreal.LinearColor(0.55, 0.52, 0.49), 0.0, 0.8, 0.4))

    stone = resource("DA_Stone", "Stone", "Piedra", unreal.LinearColor(0.32, 0.27, 0.22), raw, STONE_SIZE)
    block = resource("DA_StoneBlock", "StoneBlock", "Bloque de piedra", unreal.LinearColor(0.6, 0.57, 0.53), block_mesh, 30.0, stone, BLOCK_PERCENT)
    crushed = resource("DA_CrushedStone", "CrushedStone", "Piedra triturada", unreal.LinearColor(0.55, 0.52, 0.49), crushed_mesh, 30.0, block, CRUSHED_PERCENT)
    sim = [a for a in level if isinstance(a, unreal.FactoryDemoWorld)][0]
    resources = list(sim.get_editor_property("resources"))
    for r in (stone, block, crushed):
        if r not in resources:
            resources.append(r)
    sim.modify()
    sim.set_editor_property("resources", resources)

    # trituradora y horno
    crusher_def = unreal.load_asset(f"{DEFS}/DB_QuartzCrusher")
    for prop, value in (("display_name", "Trituradora"), ("input_item", "StoneBlock"), ("output_item", "CrushedStone"),
                        ("input_quantity", 1), ("output_quantity", 2)):
        crusher_def.set_editor_property(prop, value)
    lib.save_loaded_asset(crusher_def)
    melt = by["Proceso_Fundicion"]
    melt.modify()
    melt.set_editor_property("input_item", "CrushedStone")
    melt.set_editor_property("input_label", "PIEDRA TRITURADA")

    # la sierra: la caja del interior de Lavadora_Cuarzo, sobre la cinta que la atraviesa (antes Lavadora_Estacion)
    box = by["Lavadora_Cuarzo"]
    bb = box.static_mesh_component.static_mesh.get_bounding_box()
    bt = box.get_actor_transform()
    centre = bt.transform_location(unreal.Vector((bb.min.x + bb.max.x) / 2, (bb.min.y + bb.max.y) / 2, (bb.min.z + bb.max.z) / 2))
    scale = box.get_actor_scale3d()
    extent = unreal.Vector((bb.max.x - bb.min.x) / 2 * scale.x * 0.9, (bb.max.y - bb.min.y) / 2 * scale.y * 0.9, (bb.max.z - bb.min.z) / 2 * scale.z)
    station = by.get("Sierra_Estacion") or by.get("Lavadora_Estacion")
    if station is None:
        station = actors.spawn_actor_from_class(unreal.FactoryBeltStation, centre, box.get_actor_rotation())
    station.set_actor_label("Sierra_Estacion")
    station.set_folder_path(str(box.get_folder_path()))
    station.modify()
    station.set_actor_location_and_rotation(centre, box.get_actor_rotation(), False, False)
    station.zone.set_box_extent(extent)
    passing = [a for a in level if isinstance(a, unreal.FactoryBuilding) and a.get_editor_property("definition")
               and str(a.get_editor_property("definition").get_editor_property("kind")).endswith("BELT: 2>")]
    zt = station.zone.get_world_transform()
    def crosses(belt):
        for f in (0.1, 0.3, 0.5, 0.7, 0.9):
            a, b = belt.input_point(), belt.output_point()
            p = zt.inverse_transform_location(a + (b - a) * f)
            if abs(p.x) <= extent.x and abs(p.y) <= extent.y and abs(p.z) <= extent.z:
                return True
        return False
    belts = [b for b in passing if crosses(b)]
    station.set_editor_property("belts", belts)
    station.set_editor_property("input_item", "Stone")
    station.set_editor_property("output_resource", block)
    station.set_editor_property("flash_color", unreal.LinearColor(1.0, 0.55, 0.15))

    # la sierra tambien corta los lingotes que se cargan a mano: sale la mitad (el tamaño va en porcentaje del lingote)
    ingot = unreal.load_asset(f"{DEFS}/DA_SiliconIngot")
    cut = resource("DA_SiliconIngotCut", "SiliconIngotCut", "Lingote cortado", unreal.LinearColor(0.52, 0.55, 0.6),
                   ingot.get_editor_property("pickup_mesh"), 30.0, ingot, INGOT_CUT_PERCENT)
    resources = list(sim.get_editor_property("resources"))
    if cut not in resources:
        resources.append(cut)
        sim.set_editor_property("resources", resources)
    saw2 = [a for a in actors.get_all_level_actors() if a.get_actor_label() == "Sierra_Estacion_Lingotes"]
    saw2 = saw2[0] if saw2 else actors.spawn_actor_from_class(unreal.FactoryBeltStation, centre, box.get_actor_rotation())
    saw2.modify()
    saw2.set_actor_label("Sierra_Estacion_Lingotes")
    saw2.set_folder_path(str(box.get_folder_path()))
    saw2.set_actor_location_and_rotation(centre, box.get_actor_rotation(), False, False)
    saw2.zone.set_box_extent(extent)
    saw2.set_editor_property("belts", belts)
    saw2.set_editor_property("input_item", "SiliconIngot")
    saw2.set_editor_property("output_resource", cut)
    saw2.set_editor_property("flash_color", unreal.LinearColor(1.0, 0.55, 0.15))

    # las piedras para cargar a mano
    placed = []
    for i in range(COUNT):
        x, y = START[0] + (i % PER_ROW) * STEP_X, START[1] + (i // PER_ROW) * STEP_Y
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 300), unreal.Vector(x, y, -100),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
        z = hit.to_tuple()[4].z if hit else 4.0
        pile = actors.spawn_actor_from_class(unreal.FactoryResourcePile, unreal.Vector(x, y, z), unreal.Rotator(0, 0, i * 37))
        pile.set_actor_label(f"Piedra_Prueba_{i + 1}")
        pile.set_folder_path("Fabrica")
        pile.set_editor_property("resource", stone)
        pile.set_editor_property("amount", 1)
        pile.set_editor_property("persistent_id", f"Piedra_Prueba_{i + 1}")
        pile.refresh_visuals()
        placed.append([round(x), round(y), round(z)])
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=bool(belts) and all(p[2] < 20 for p in placed), estacion_cintas=[b.get_actor_label() for b in belts],
                  zona={"centro": [round(centre.x), round(centre.y), round(centre.z)], "medio": [round(extent.x), round(extent.y), round(extent.z)]},
                  piedras=placed, tamaños_cm={"piedra": round(stone.get_cargo_size(), 1), "bloque": round(block.get_cargo_size(), 1),
                                               "triturada": round(crushed.get_cargo_size(), 1)})
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[PIEDRAS] " + report["error"])
(project / "Docs/piedras.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
