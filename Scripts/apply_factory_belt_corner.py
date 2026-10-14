"""Editor Python: esquina para las cintas de la fabrica (30/09). Requiere FactoryCtycoRuntime con TurnDegrees en las definiciones.

- Importa SourceAssets/CintaEsquinaFabrica/SM_CintaEsquinaFabrica.fbx (author_factory_belt_corner.py) en
  /Game/FactoryCtyco/Factory/Models/CintaEsquina (borra el asset antes: reimportar encima lo dejaba al 1 %).
- Crea o actualiza /Game/FactoryCtyco/Factory/Definitions/DB_BeltCorner: una cinta (Kind Belt) con esa malla y
  TurnDegrees -90, y la suma al catalogo de FactoryDemo_Simulation (tecla 5 en el modo construir; y el guardado F5/F9).
- Pone, si no existe, `Cinta_Fabrica_Esquina` en una celda libre del piso de la fabrica, para que el usuario la ubique.
- A todas las cintas de la fabrica les pone el acero de las cintas de carga en los postes (SupportMaterial).
Sin editor abre el mapa, guarda y cierra. Informe: Docs/factory_belt_corner.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SRC = project / "SourceAssets/CintaEsquinaFabrica"
DEST, NAME = "/Game/FactoryCtyco/Factory/Models/CintaEsquina", "SM_CintaEsquinaFabrica"
DEFS = "/Game/FactoryCtyco/Factory/Definitions"
LABEL = "Cinta_Fabrica_Esquina"
SPOTS = [(-600, 600), (-400, 600), (-200, 600), (0, 600), (200, 600), (-600, -600), (600, 600)]
STEEL = "/Game/FactoryCtyco/Environments/CintaCarga/M_CintaAcero"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
report = {"passed": False}


def import_mesh():
    path = f"{DEST}/{NAME}"
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {path}")
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
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    task = unreal.AssetImportTask()
    task.filename = str(SRC / f"{NAME}.fbx")
    task.destination_path, task.destination_name = DEST, NAME
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("No se importo la esquina")
    # la esquina choca con su propia malla (una caja llenaria tambien el hueco de adentro de la curva)
    body = mesh.get_editor_property("body_setup")
    body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    mesh.set_editor_property("body_setup", body)
    lib.save_loaded_asset(mesh, False)
    return mesh


try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir L_FactoryDemo")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level = actors.get_all_level_actors()
    corners = [a for a in level if isinstance(a, unreal.FactoryBuilding) and a.get_actor_label().startswith(LABEL)]
    mesh = import_mesh()

    straight = unreal.load_asset(f"{DEFS}/DB_Belt")
    path = f"{DEFS}/DB_BeltCorner"
    corner_def = unreal.load_asset(path) if lib.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "DB_BeltCorner", DEFS, unreal.FactoryBuildingDefinition, unreal.DataAssetFactory())
    for prop in ("kind", "presentation_material", "detail_box_mesh", "detail_cylinder_mesh", "scrap_cost", "capacity",
                 "input_item", "output_item", "input_quantity", "output_quantity", "cycle_seconds"):
        corner_def.set_editor_property(prop, straight.get_editor_property(prop))
    corner_def.set_editor_property("building_id", "BeltCorner")
    corner_def.set_editor_property("display_name", "Cinta esquina")
    corner_def.set_editor_property("mesh", mesh)
    corner_def.set_editor_property("mesh_scale", unreal.Vector(1, 1, 1))
    corner_def.set_editor_property("mesh_offset", unreal.Vector(0, 0, 0))
    corner_def.set_editor_property("mesh_yaw", 0.0)
    corner_def.set_editor_property("turn_degrees", -90.0)
    corner_def.set_editor_property("turn_radius", json.loads((SRC / "build.json").read_text(encoding="utf-8"))["turn_radius_cm"])
    lib.save_loaded_asset(corner_def, False)

    factory = next(a for a in level if isinstance(a, unreal.FactoryDemoWorld))
    catalog = list(factory.get_editor_property("catalog"))
    if corner_def not in catalog:
        catalog.append(corner_def)
        factory.set_editor_property("catalog", catalog)

    if not corners:
        spot = None
        for x, y in SPOTS:
            if not str(factory.placement_problem(unreal.Vector(x, y, 4), None)):
                spot = unreal.Vector(x, y, 4)
                break
        if spot is None:
            spot = unreal.Vector(*SPOTS[0], 4)
        corner = actors.spawn_actor_from_class(unreal.FactoryBuilding, spot, unreal.Rotator())
        corner.set_actor_label(LABEL)
        corner.set_editor_property("persistent_id", LABEL)
        corner.set_editor_property("paid_scrap", 0)
        corners = [corner]
    for c in corners:
        c.set_editor_property("definition", corner_def)
        c.refresh_visuals()

    steel = unreal.load_asset(STEEL)
    belts = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.FactoryBuilding) and a.get_actor_label().startswith("Cinta_Fabrica")]
    for b in belts:
        b.set_editor_property("support_material", steel)
        b.build_supports()
    loc = corners[0].get_actor_location()
    report.update(passed=True, mesh=mesh.get_path_name(), definition=path, catalog=[str(c.get_editor_property("building_id")) for c in catalog if c],
                  corner=LABEL, location=[round(loc.x), round(loc.y), round(loc.z)], belts_with_steel_posts=sorted(b.get_actor_label() for b in belts),
                  input_point=[round(v) for v in corners[0].input_point().to_tuple()], output_point=[round(v) for v in corners[0].output_point().to_tuple()])
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[FACTORY_CORNER] " + report["error"])
finally:
    (project / "Docs/factory_belt_corner.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
