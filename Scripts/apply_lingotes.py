"""Editor Python (con L_FactoryDemo abierto): lingotes de silicio sueltos para probar (02/10).

- Importa SM_LingoteSilicio (author_lingote.py) con M_LingoteSilicio (gris metalico) y se lo pone a DA_SiliconIngot
  (antes era el cubo del motor, de 1 m): es como se ve el lingote en el inventario, en las cintas y en el piso.
- Deja COUNT lingotes en el piso (Lingote_Prueba_N, AFactoryResourcePile de 1 lingote cada uno, carpeta Fabrica) en dos
  filas, entre el ascensor de la fabrica y la caja tunel, junto a la pared este. Con E se juntan (van al inventario) y
  con E al lado de una cinta se carga uno en la cinta. Se rehacen cada vez que se corre.
Informe: Docs/lingotes.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
MESH = "/Game/FactoryCtyco/Factory/Models/Lingote/SM_LingoteSilicio"
MATS = "/Game/FactoryCtyco/Factory/Materials"
START = (1860.0, -380.0)   # primer lingote (cm); las filas van hacia +Y
COUNT, PER_ROW, STEP_X, STEP_Y = 10, 5, 70.0, 55.0
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}

try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    # material
    path = f"{MATS}/M_LingoteSilicio"
    if lib.does_asset_exist(path):
        mat = unreal.load_asset(path)
        mel.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset("M_LingoteSilicio", MATS, unreal.Material, unreal.MaterialFactoryNew())
    for value, prop, y in ((unreal.LinearColor(0.52, 0.55, 0.6), unreal.MaterialProperty.MP_BASE_COLOR, 0),
                           (0.9, unreal.MaterialProperty.MP_METALLIC, 120), (0.28, unreal.MaterialProperty.MP_ROUGHNESS, 240)):
        if isinstance(value, unreal.LinearColor):
            e = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -400, y)
            e.set_editor_property("constant", value)
        else:
            e = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, y)
            e.set_editor_property("r", value)
        mel.connect_material_property(e, "", prop)
    mel.recompile_material(mat)
    lib.save_loaded_asset(mat)

    # malla (borrar los lingotes de antes y la malla vieja antes de importar)
    for old in [a for a in actors.get_all_level_actors() if a.get_actor_label().startswith("Lingote_Prueba_")]:
        actors.destroy_actor(old)
    ingot = unreal.load_asset("/Game/FactoryCtyco/Factory/Definitions/DA_SiliconIngot")
    ingot.set_editor_property("pickup_mesh", None)
    if lib.does_asset_exist(MESH) and not lib.delete_asset(MESH):
        raise RuntimeError("No se pudo borrar SM_LingoteSilicio")
    options = unreal.FbxImportUI()
    options.import_mesh, options.import_as_skeletal = True, False
    options.import_materials = options.import_textures = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes, data.auto_generate_collision = True, True
    data.convert_scene = data.convert_scene_unit = True
    task = unreal.AssetImportTask()
    task.filename = str(project / "SourceAssets/Lingote/SM_LingoteSilicio.fbx")
    task.destination_path, task.destination_name = MESH.rsplit("/", 1)
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    tools.import_asset_tasks([task])
    mesh = unreal.load_asset(MESH)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("No se importo SM_LingoteSilicio")
    mesh.set_material(0, mat)
    lib.save_loaded_asset(mesh)
    ingot.set_editor_property("pickup_mesh", mesh)
    ingot.set_editor_property("pickup_scale", unreal.Vector(1, 1, 1))
    lib.save_loaded_asset(ingot)

    # los lingotes en el piso
    placed = []
    for i in range(COUNT):
        x, y = START[0] + (i % PER_ROW) * STEP_X, START[1] + (i // PER_ROW) * STEP_Y
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 300), unreal.Vector(x, y, -100),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
        z = hit.to_tuple()[4].z if hit else 4.0
        floor_actor = hit.to_tuple()[9].get_actor_label() if hit else None
        pile = actors.spawn_actor_from_class(unreal.FactoryResourcePile, unreal.Vector(x, y, z), unreal.Rotator(0, 0, 90))
        pile.set_actor_label(f"Lingote_Prueba_{i + 1}")
        pile.set_folder_path("Fabrica")
        pile.set_editor_property("resource", ingot)
        pile.set_editor_property("amount", 1)
        pile.set_editor_property("persistent_id", f"Lingote_Prueba_{i + 1}")
        pile.refresh_visuals()
        placed.append({"lingote": pile.get_actor_label(), "en": [round(x), round(y), round(z)], "piso": floor_actor})
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=all(p["piso"] and p["piso"].startswith("SceneRobot") for p in placed), lingotes=placed,
                  tamaño_cm=[round(v) for v in (mesh.get_bounding_box().max - mesh.get_bounding_box().min).to_tuple()])
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[LINGOTES] " + report["error"])
(project / "Docs/lingotes.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
