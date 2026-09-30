"""Editor Python: importa la maquina de despacho y la coloca en L_FactoryDemo para que el usuario la ubique.

Fuente: SourceAssets/DespachoMachine/SM_DespachoMachine.fbx (author_despacho_machine.py).
Crea /Game/FactoryCtyco/Environments/DespachoMachine/SM_DespachoMachine (con UCX) y, si no existe,
el actor `Despacho_Machine` (StaticMeshActor, carpeta Environment) 4 m al este de
PlayerStart_Robot1, apoyado en el piso. Si el actor ya existe solo se le cambia la malla,
asi se conserva la posicion ajustada a mano. Informe: Docs/despacho_import.json.

Sin editor (abre el mapa, guarda el nivel y cierra):
UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/import_despacho_machine.py
    -unattended -nosound
Con el editor abierto (MCP execute_python o consola Python) usa el nivel abierto, guarda solo
los assets y deja el nivel sin guardar para que el usuario lo guarde con sus cambios.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SOURCE = project / "SourceAssets/DespachoMachine"
DEST = "/Game/FactoryCtyco/Environments/DespachoMachine"
NAME = "SM_DespachoMachine"
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
LABEL = "Despacho_Machine"
OFFSET = unreal.Vector(400.0, 0.0, 0.0)  # desde PlayerStart_Robot1; el usuario lo reubica
build = json.loads((SOURCE / "despacho_build.json").read_text())
lib = unreal.EditorAssetLibrary
report = {"passed": False}
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()


def import_fbx(users):
    # reimportar encima deja la colision vieja: soltar las referencias y borrar antes
    path = f"{DEST}/{NAME}"
    for a in users:
        a.static_mesh_component.set_static_mesh(None)
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {NAME}")
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = True
    options.import_textures = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.one_convex_hull_per_ucx = True
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    task = unreal.AssetImportTask()
    task.filename = str(SOURCE / f"{NAME}.fbx")
    task.destination_path = DEST
    task.destination_name = NAME
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)  # materiales y texturas
    mesh = unreal.load_asset(f"{DEST}/{NAME}")
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("No se importo la malla")
    if not lib.save_loaded_asset(mesh, False):  # falla si otro editor tiene el archivo abierto
        raise RuntimeError(f"No se pudo guardar {NAME}")
    return mesh


def roller_material(mesh):
    """Rodillos que giran: franjas claras y oscuras alrededor del tubo (U) que se desplazan con el tiempo.
    Parametro Velocidad = vueltas aparentes por segundo (negativo invierte el giro)."""
    mel = unreal.MaterialEditingLibrary
    path = f"{DEST}/M_DespachoRodillo"
    if lib.does_asset_exist(path):
        lib.delete_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_DespachoRodillo", DEST, unreal.Material, unreal.MaterialFactoryNew())
    uv = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1400, 0)
    u = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -1200, 0)
    u.set_editor_property("r", True)
    mel.connect_material_expressions(uv, "", u, "")
    bands = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -1000, 0)
    bands.set_editor_property("const_b", 3.0)
    mel.connect_material_expressions(u, "", bands, "A")
    time = mel.create_material_expression(mat, unreal.MaterialExpressionTime, -1400, 250)
    speed = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -1400, 350)
    speed.set_editor_property("parameter_name", "Velocidad")
    speed.set_editor_property("default_value", 1.5)
    turns = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -1200, 250)
    mel.connect_material_expressions(time, "", turns, "A")
    mel.connect_material_expressions(speed, "", turns, "B")
    # U - t*v: el lado de arriba avanza hacia el final de la cinta, como las cajas
    phase = mel.create_material_expression(mat, unreal.MaterialExpressionSubtract, -800, 100)
    mel.connect_material_expressions(bands, "", phase, "A")
    mel.connect_material_expressions(turns, "", phase, "B")
    wave = mel.create_material_expression(mat, unreal.MaterialExpressionSine, -600, 100)
    wave.set_editor_property("period", 1.0)
    mel.connect_material_expressions(phase, "", wave, "")
    alpha = mel.create_material_expression(mat, unreal.MaterialExpressionConstantBiasScale, -400, 100)
    alpha.set_editor_property("bias", 1.0)
    alpha.set_editor_property("scale", 0.5)
    mel.connect_material_expressions(wave, "", alpha, "")
    dark = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -400, -150)
    dark.set_editor_property("constant", unreal.LinearColor(0.09, 0.09, 0.1, 1))
    light = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -400, -50)
    light.set_editor_property("constant", unreal.LinearColor(0.55, 0.56, 0.58, 1))
    color = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -200, 0)
    mel.connect_material_expressions(dark, "", color, "A")
    mel.connect_material_expressions(light, "", color, "B")
    mel.connect_material_expressions(alpha, "", color, "Alpha")
    mel.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    metal = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -200, 200)
    metal.set_editor_property("r", 0.85)
    mel.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -200, 300)
    rough.set_editor_property("r", 0.35)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat)
    lib.save_loaded_asset(mat, False)
    materials = mesh.static_materials
    found = False
    for m in materials:
        if "Rodillo" in str(m.material_slot_name):
            m.set_editor_property("material_interface", mat)
            found = True
    if not found:
        raise RuntimeError("La malla no tiene la ranura M_Rodillo")
    mesh.set_editor_property("static_materials", materials)
    if not lib.save_loaded_asset(mesh, False):
        raise RuntimeError(f"No se pudo guardar {NAME}")
    return mat


def floor_z(world, x, y):
    hit = unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(x, y, 1000.0), unreal.Vector(x, y, -500.0),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
    if isinstance(hit, tuple):
        hit = next((h for h in hit if isinstance(h, unreal.HitResult)), None)
    if hit is None or not hit.to_tuple()[0]:
        return 0.0
    return float(hit.to_tuple()[4].z)


try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if HEADLESS:
        if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP):
            raise RuntimeError(f"No se pudo abrir {MAP}")
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    elif world.get_path_name().split(".")[0] != MAP:
        raise RuntimeError(f"Abrir {MAP} en el editor antes de correr el script")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level_actors = actors.get_all_level_actors()
    actor = next((a for a in level_actors if a.get_actor_label() == LABEL), None)
    # todas las copias que puso el usuario (Despacho_Machine2, ...) usan la misma malla
    users = [a for a in level_actors if isinstance(a, unreal.StaticMeshActor)
             and a.get_actor_label().startswith(LABEL)]
    mesh = import_fbx(users)
    box = mesh.get_bounding_box()
    height = box.max.z - box.min.z
    if abs(height - build["size_m"][2] * 100) > 5:
        raise RuntimeError(f"Altura inesperada {height:.1f} cm")
    roller = roller_material(mesh)
    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(mesh)
    if hulls != 2:
        raise RuntimeError(f"Se esperaban 2 colisiones; hay {hulls}")

    if actor is None:
        start = next(a for a in level_actors if a.get_actor_label() == "PlayerStart_Robot1")
        spot = start.get_actor_location() + OFFSET
        spot.z = floor_z(world, spot.x, spot.y)
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, spot, unreal.Rotator())
        actor.set_actor_label(LABEL)
        actor.set_folder_path("Environment")
    for a in users + ([] if actor in users else [actor]):
        a.modify()  # sin esto la copia del usuario se guardo sin malla
        a.static_mesh_component.set_static_mesh(mesh)
        a.static_mesh_component.set_collision_profile_name("BlockAll")
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    loc = actor.get_actor_location()
    report.update(passed=True, mesh=mesh.get_path_name(), height_cm=round(height, 1), collisions=hulls,
                  actor=LABEL, copies=sorted(a.get_actor_label() for a in users),
                  roller_material=roller.get_path_name(), location=[round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)],
                  materials=[str(m.material_slot_name) for m in mesh.static_materials])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[DESPACHO_IMPORT] {error}")
finally:
    (project / "Docs/despacho_import.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
