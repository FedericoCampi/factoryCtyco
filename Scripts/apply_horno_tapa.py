"""Editor Python (04/10): horno con tapa que se abre y se cierra, liquido del color del material, triturado mas grande.

1. Importa SM_HornoFundicion_CuerpoSinTapa y SM_HornoFundicion_Tapa (author_horno_tapa.py) con los materiales del
   cuerpo; Horno_Fundicion (FactoryRaisedProp) usa el cuerpo sin tapa y `Horno_Tapa` (StaticMeshActor movible) cuelga de
   el, en la bisagra.
2. M_LiquidoFundido: material del liquido con Color (el del material que se funde) y Heat (brilla caliente, se apaga al
   enfriarse).
3. Proceso_Fundicion: LidActor = Horno_Tapa (LidSign medido aca: cerrar la baja), lote de 3, 5 s de fundido, cuela solo.
4. DA_CrushedStone (piedra triturada): 80 % del bloque en vez de 60 % (se ve mas grande).
Hay que correrlo con el editor abierto (crear actores sin ventana se cae). Guarda el nivel. Informe: Docs/horno_tapa.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SRC = project / "SourceAssets/HornoFundicion"
DEST = "/Game/FactoryCtyco/Environments/HornoFundicion"
MATS = "/Game/FactoryCtyco/Factory/Materials"
DEFS = "/Game/FactoryCtyco/Factory/Definitions"
LID_LABEL = "Horno_Tapa"
CRUSHED_PERCENT = 80.0
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
build = json.loads((SRC / "horno_tapa.json").read_text(encoding="utf-8"))
report = {"passed": False}


def import_mesh(name):
    path = f"{DEST}/{name}"
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
    task.filename = str(SRC / f"{name}.fbx")
    task.destination_path, task.destination_name = DEST, name
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    tools.import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    # los materiales del cuerpo entero, por nombre de ranura
    body = unreal.load_asset(f"{DEST}/SM_HornoFundicion_Cuerpo")
    by_slot = {str(m.material_slot_name): m.material_interface for m in body.static_materials}
    mesh.modify()
    for index, slot in enumerate(mesh.static_materials):
        if str(slot.material_slot_name) in by_slot:
            mesh.set_material(index, by_slot[str(slot.material_slot_name)])
    lib.save_loaded_asset(mesh, False)
    return mesh


def liquid_material():
    path = f"{MATS}/M_LiquidoFundido"
    if lib.does_asset_exist(path):
        return unreal.load_asset(path)
    mat = tools.create_asset("M_LiquidoFundido", MATS, unreal.Material, unreal.MaterialFactoryNew())
    color = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -700, -100)
    color.set_editor_property("parameter_name", "Color")
    color.set_editor_property("default_value", unreal.LinearColor(1.0, 0.42, 0.08, 1.0))
    heat = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -700, 150)
    heat.set_editor_property("parameter_name", "Heat")
    heat.set_editor_property("default_value", 1.0)
    glow = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -700, 300)
    glow.set_editor_property("parameter_name", "Brillo")
    glow.set_editor_property("default_value", 6.0)
    hot = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -400, 150)
    mel.connect_material_expressions(color, "", hot, "A")
    mel.connect_material_expressions(heat, "", hot, "B")
    bright = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -200, 200)
    mel.connect_material_expressions(hot, "", bright, "A")
    mel.connect_material_expressions(glow, "", bright, "B")
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 400)
    rough.set_editor_property("r", 0.3)
    mel.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(bright, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat)
    lib.save_loaded_asset(mat, False)
    return mat


try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    furnace, melt = by["Horno_Fundicion"], by["Proceso_Fundicion"]
    lid = by.get(LID_LABEL)
    if lid:
        lid.static_mesh_component.set_static_mesh(None)
    furnace.set_editor_property("body_mesh", None)
    body = import_mesh("SM_HornoFundicion_CuerpoSinTapa")
    tapa = import_mesh("SM_HornoFundicion_Tapa")
    furnace.modify()
    furnace.set_editor_property("body_mesh", body)

    if lid is None:
        lid = actors.spawn_actor_from_class(unreal.StaticMeshActor, furnace.get_actor_location(), furnace.get_actor_rotation())
        lid.set_actor_label(LID_LABEL)
    lid.modify()
    lid.set_folder_path(str(furnace.get_folder_path()) if str(furnace.get_folder_path()) != "None" else "Fabrica")
    comp = lid.static_mesh_component
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_static_mesh(tapa)
    comp.set_collision_profile_name("NoCollision")
    lid.attach_to_actor(furnace, "", unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE,
                        unreal.AttachmentRule.KEEP_RELATIVE, False)
    comp.set_editor_property("relative_location", unreal.Vector(*build["pivot_unreal_cm"]))
    comp.set_editor_property("relative_scale3d", unreal.Vector(1, 1, 1))

    # el sentido: cerrar (girar -angulo de la tapa) tiene que bajarla
    rest = build["lid_open_deg"]
    tops = {}
    for sign in (1.0, -1.0):
        comp.set_editor_property("relative_rotation", unreal.Rotator(roll=sign * (0.0 - rest), pitch=0.0, yaw=0.0))
        o, e = lid.get_actor_bounds(False)
        tops[sign] = round(o.z + e.z, 1)
    lid_sign = 1.0 if tops[1.0] < tops[-1.0] else -1.0
    comp.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))

    liquid = liquid_material()
    melt.modify()
    for prop, value in (("lid_actor", lid), ("lid_rest_angle", rest), ("lid_loading_angle", 75.0), ("lid_sign", lid_sign),
                        ("batch_size", 3), ("melt_seconds", 5.0), ("auto_pour", True), ("automatic", False),
                        ("molten_material", liquid)):
        melt.set_editor_property(prop, value)

    crushed = unreal.load_asset(f"{DEFS}/DA_CrushedStone")
    before = crushed.get_cargo_size()
    crushed.set_editor_property("size_percent", CRUSHED_PERCENT)
    lib.save_loaded_asset(crushed, False)

    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, pivot_cm=build["pivot_unreal_cm"], lid_rest_deg=rest, lid_sign=lid_sign, closed_top_cm=tops,
                  liquid=liquid.get_path_name(), crushed_size_cm=[round(before, 1), round(crushed.get_cargo_size(), 1)])
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[HORNO_TAPA] " + report["error"])
finally:
    (project / "Docs/horno_tapa.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
