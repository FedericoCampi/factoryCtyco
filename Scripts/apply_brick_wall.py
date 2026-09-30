"""Editor Python: pedazo de pared de ladrillos para colocar, girar y escalar a mano.

Importa SourceAssets/ParedLadrillo/SM_ParedLadrillo.fbx (author_sign_and_wall.py) con su UCX y le
pone M_LadrilloMundo: la textura del ladrillo del estacionamiento proyectada en coordenadas del
mundo (1 repeticion por metro, a lo largo de la pared y hacia arriba), asi al escalar o girar la
pared los ladrillos conservan su tamano. Si no existe, pone `Pared_Ladrillo` (carpeta Environment)
en el estacionamiento. Sin editor guarda el nivel y cierra; con editor abierto no guarda el nivel.
Informe: Docs/brick_wall.json.

UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/apply_brick_wall.py -unattended -nosound
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/ParedLadrillo"
NAME = "SM_ParedLadrillo"
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
TEXTURE = "/Game/FactoryCtyco/Environments/Parking/Weathered_burnt_orange_brick_packed_surface"
SPOT = unreal.Vector(-4000.0, -1300.0, 0.0)  # piso del estacionamiento; el usuario la mueve
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
report = {"passed": False}


def import_wall(users):
    path = f"{DEST}/{NAME}"
    for a in users:
        a.static_mesh_component.set_static_mesh(None)
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {NAME}")
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = False
    options.import_textures = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.one_convex_hull_per_ucx = True
    data.convert_scene = True
    data.convert_scene_unit = True
    task = unreal.AssetImportTask()
    task.filename = str(project / f"SourceAssets/ParedLadrillo/{NAME}.fbx")
    task.destination_path = DEST
    task.destination_name = NAME
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {NAME}")
    return mesh


def world_brick_material():
    """UV = (distancia a lo largo de la cara, altura) en metros, desde la posicion en el mundo.
    La direccion "a lo largo" es la horizontal perpendicular a la normal: sirve con cualquier giro."""
    path = f"{DEST}/M_LadrilloMundo"
    if lib.does_asset_exist(path):
        lib.delete_asset(path)
    texture = unreal.load_asset(TEXTURE)
    if texture is None:
        raise RuntimeError(f"Falta la textura {TEXTURE}")
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_LadrilloMundo", DEST, unreal.Material, unreal.MaterialFactoryNew())
    world = mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -900, 0)
    normal = mel.create_material_expression(mat, unreal.MaterialExpressionVertexNormalWS, -900, 150)
    # un nodo de codigo: la cadena de nodos sueltos terminaba en un vector de 4 y no compilaba
    uv = mel.create_material_expression(mat, unreal.MaterialExpressionCustom, -600, 50)
    uv.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    uv.set_editor_property("description", "UV de ladrillo en metros")
    uv.set_editor_property("code", (
        "float3 along = normalize(cross(N, float3(0, 0, 1)) + 0.0001);\n"
        "return float2(dot(W, along), -W.z) / 100.0;"))
    inputs = []
    for name in ("W", "N"):
        pin = unreal.CustomInput()
        pin.set_editor_property("input_name", name)
        inputs.append(pin)
    uv.set_editor_property("inputs", inputs)
    mel.connect_material_expressions(world, "", uv, "W")
    mel.connect_material_expressions(normal, "", uv, "N")
    meters = uv
    sample = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -350, 50)
    sample.set_editor_property("texture", texture)
    mel.connect_material_expressions(meters, "", sample, "UVs")
    mel.connect_material_property(sample, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -350, 300)
    rough.set_editor_property("r", 0.85)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat)
    lib.save_loaded_asset(mat, False)
    return mat


try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP):
        raise RuntimeError(f"No se pudo abrir {MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level_actors = actors.get_all_level_actors()
    users = [a for a in level_actors if isinstance(a, unreal.StaticMeshActor) and a.get_actor_label().startswith("Pared_Ladrillo")]
    mesh = import_wall(users)
    mat = world_brick_material()
    mesh.set_material(0, mat)
    if not lib.save_loaded_asset(mesh, False):
        raise RuntimeError(f"No se pudo guardar {NAME}")
    if not users:
        wall = actors.spawn_actor_from_class(unreal.StaticMeshActor, SPOT, unreal.Rotator())
        wall.set_actor_label("Pared_Ladrillo")
        wall.set_folder_path("Environment")
        users = [wall]
    for a in users:
        a.modify()
        a.static_mesh_component.set_static_mesh(mesh)
        a.static_mesh_component.set_collision_profile_name("BlockAll")
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(mesh)
    report.update(passed=True, mesh=mesh.get_path_name(), material=mat.get_path_name(), collisions=hulls,
                  actors=[a.get_actor_label() for a in users])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[BRICK_WALL] {error}")
finally:
    (project / "Docs/brick_wall.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
