"""Editor Python (04/10): paredes del ascensor cerradas, horno de 5 s y liquido menos brillante.

1. Importa SM_Ascensor2Relleno (author_elevator_paneles.py: paneles que tapan los huecos de las paredes de la cabina
   arriba de sus paneles a media altura) en /Game/FactoryCtyco/Environments/Ascensor2 y se lo pone a cada
   AFactoryElevator (componente Panels, con colision).
2. Proceso_Fundicion: 5 s de fundido.
3. MI_LiquidoFundido: instancia de M_LiquidoFundido con Brillo BRIGHTNESS (con 6 el liquido gris se veia blanco).
Requiere FactoryCtycoRuntime con Panels (build_runtime_visuals.ps1 -Install). Guarda el nivel.
Informe: Docs/ascensor_paneles.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/Ascensor2"
NAME = "SM_Ascensor2Relleno"
MATS = "/Game/FactoryCtyco/Factory/Materials"
BRIGHTNESS = 1.2
MELT_SECONDS = 5.0
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
report = {"passed": False}

try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level = actors.get_all_level_actors()
    lifts = [a for a in level if isinstance(a, unreal.FactoryElevator)]
    for lift in lifts:
        lift.get_editor_property("panels").set_static_mesh(None)
    path = f"{DEST}/{NAME}"
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {path}")
    options = unreal.FbxImportUI()
    options.import_mesh, options.import_as_skeletal = True, False
    options.import_materials, options.import_textures = True, False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes, data.auto_generate_collision = True, False
    data.convert_scene = data.convert_scene_unit = True
    task = unreal.AssetImportTask()
    task.filename = str(project / f"SourceAssets/Ascensor2/{NAME}.fbx")
    task.destination_path, task.destination_name = DEST, NAME
    task.automated = task.save = task.replace_existing = True
    task.factory, task.options = unreal.FbxFactory(), options
    tools.import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {NAME}")
    body = mesh.get_editor_property("body_setup")
    body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    mesh.set_editor_property("body_setup", body)
    lib.save_loaded_asset(mesh, False)
    for lift in lifts:
        lift.modify()
        lift.get_editor_property("panels").set_static_mesh(mesh)

    # liquido: una instancia con menos brillo
    mi_path = f"{MATS}/MI_LiquidoFundido"
    mi = unreal.load_asset(mi_path) if lib.does_asset_exist(mi_path) else tools.create_asset(
        "MI_LiquidoFundido", MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    unreal.MaterialEditingLibrary.set_material_instance_parent(mi, unreal.load_asset(f"{MATS}/M_LiquidoFundido"))
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi, "Brillo", BRIGHTNESS)
    unreal.MaterialEditingLibrary.update_material_instance(mi)
    lib.save_loaded_asset(mi, False)
    melt = next(a for a in level if isinstance(a, unreal.FactoryMeltProcess))
    melt.modify()
    melt.set_editor_property("melt_seconds", MELT_SECONDS)
    melt.set_editor_property("molten_material", mi)

    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    b = mesh.get_bounding_box()
    report.update(passed=True, elevators=[l.get_actor_label() for l in lifts],
                  panels_size_cm=[round(b.max.x - b.min.x), round(b.max.y - b.min.y), round(b.max.z - b.min.z)],
                  melt_seconds=MELT_SECONDS, liquid=mi.get_path_name(), brightness=BRIGHTNESS)
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[ASCENSOR_PANELES] " + report["error"])
finally:
    (project / "Docs/ascensor_paneles.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
