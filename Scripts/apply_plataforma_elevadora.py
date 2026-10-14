"""Editor Python (con L_FactoryDemo abierto): plataforma elevadora para las cintas (02/10).

- Importa SM_PlataformaElevadora (author_plataforma_elevadora.py) con M_PlataformaChapa (gris oscuro) y
  M_PlataformaBorde (naranja), y crea DB_Lift: una cinta (copia de DB_Belt) que se ve como la plataforma.
- Pone Plataforma_Elevadora_1 suelta en el piso (EXAMPLE_AT), con LiftHeight = 200 cm, para que el usuario la ubique:
  su borde de atras recibe de una cinta a la altura de las cintas del piso (33 cm, o Elevation mas arriba) y entrega
  arriba por el de adelante, a 33 + Elevation + LiftHeight. La altura se cambia con LiftHeight o arrastrando el rombo
  de adelante; mas copias: duplicar el actor.
Informe: Docs/plataforma_elevadora.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEFS = "/Game/FactoryCtyco/Factory/Definitions"
MESH = "/Game/FactoryCtyco/Factory/Models/PlataformaElevadora/SM_PlataformaElevadora"
MATS = "/Game/FactoryCtyco/Factory/Materials"
EXAMPLE_AT = (1700.0, 250.0, 4.0)
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}


def color_material(name, color, metallic, roughness):
    path = f"{MATS}/{name}"
    if lib.does_asset_exist(path):
        m = unreal.load_asset(path)
        mel.delete_all_material_expressions(m)
    else:
        m = tools.create_asset(name, MATS, unreal.Material, unreal.MaterialFactoryNew())
    for value, prop, y in ((color, unreal.MaterialProperty.MP_BASE_COLOR, 0), (metallic, unreal.MaterialProperty.MP_METALLIC, 120),
                           (roughness, unreal.MaterialProperty.MP_ROUGHNESS, 240)):
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


try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    level = actors.get_all_level_actors()
    users = [a for a in level if isinstance(a, unreal.FactoryBuilding) and a.get_editor_property("definition")
             and a.get_editor_property("definition").get_name() == "DB_Lift"]
    plate = color_material("M_PlataformaChapa", unreal.LinearColor(0.12, 0.13, 0.14), 0.8, 0.5)
    edge = color_material("M_PlataformaBorde", unreal.LinearColor(1.0, 0.36, 0.04), 0.1, 0.45)
    lift_def = unreal.load_asset(f"{DEFS}/DB_Lift") if lib.does_asset_exist(f"{DEFS}/DB_Lift") else lib.duplicate_asset(f"{DEFS}/DB_Belt", f"{DEFS}/DB_Lift")
    lift_def.set_editor_property("mesh", None)
    for u in users:
        u.refresh_visuals()
    if lib.does_asset_exist(MESH) and not lib.delete_asset(MESH):
        raise RuntimeError("No se pudo borrar SM_PlataformaElevadora")
    options = unreal.FbxImportUI()
    options.import_mesh, options.import_as_skeletal = True, False
    options.import_materials = options.import_textures = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes, data.auto_generate_collision = True, True
    data.convert_scene = data.convert_scene_unit = True
    task = unreal.AssetImportTask()
    task.filename = str(project / "SourceAssets/PlataformaElevadora/SM_PlataformaElevadora.fbx")
    task.destination_path, task.destination_name = MESH.rsplit("/", 1)
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    tools.import_asset_tasks([task])
    mesh = unreal.load_asset(MESH)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("No se importo SM_PlataformaElevadora")
    slots = [str(m.material_slot_name) for m in mesh.static_materials]
    for i, slot in enumerate(slots):
        mesh.set_material(i, edge if "Borde" in slot else plate)
    lib.save_loaded_asset(mesh)
    for prop, value in (("building_id", "Lift"), ("display_name", "Plataforma elevadora"), ("mesh", mesh),
                        ("mesh_scale", unreal.Vector(1, 1, 1)), ("mesh_offset", unreal.Vector(0, 0, 0)), ("mesh_yaw", 0.0),
                        ("turn_degrees", 0.0)):
        lift_def.set_editor_property(prop, value)
    lib.save_loaded_asset(lift_def)

    example = [a for a in level if a.get_actor_label() == "Plataforma_Elevadora_1"]
    if example:
        lift = example[0]
    else:
        lift = actors.spawn_actor_from_class(unreal.FactoryBuilding, unreal.Vector(*EXAMPLE_AT), unreal.Rotator())
        lift.set_actor_label("Plataforma_Elevadora_1")
        belt = [a for a in level if a.get_actor_label() == "Cinta_Fabrica_2"]
        if belt:
            lift.set_folder_path(str(belt[0].get_folder_path()))
        lift.set_editor_property("definition", lift_def)
        lift.set_editor_property("persistent_id", "Plataforma_Elevadora_1")
        lift.set_editor_property("lift_height", 200.0)
    for u in users + [lift]:
        u.refresh_visuals()
        u.build_supports()
    hits = unreal.SystemLibrary.box_overlap_actors(world, lift.get_actor_location() + unreal.Vector(0, 0, 150), unreal.Vector(95, 75, 140),
                                                   [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2], None,
                                                   [lift] + [a for a in level if a.get_actor_label().startswith("SceneRobot")])
    if isinstance(hits, tuple):
        hits = hits[-1]
    i, o = lift.input_point(), lift.output_point()
    report.update(material_slots=slots, ejemplo=lift.get_actor_label(), recibe=[round(i.x), round(i.y), round(i.z)],
                  entrega=[round(o.x), round(o.y), round(o.z)], es_elevador=lift.is_lift(), segundos=round(lift.travel_seconds(), 2),
                  choca_con=sorted({h.get_actor_label() for h in hits or []}))
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = lift.is_lift() and not report["choca_con"]
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[PLATAFORMA_ELEVADORA] " + report["error"])
(project / "Docs/plataforma_elevadora.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
