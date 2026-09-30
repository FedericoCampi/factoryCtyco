"""Editor Python (con L_FactoryDemo abierto): columnas de la arcada del estacionamiento como actores sueltos.

Importa SourceAssets/Parking/SM_ParkingColumna.fbx (author_parking_columns.py) en
/Game/FactoryCtyco/Environments/Parking, con los materiales de SM_Parking, y pone `Columna_Arcada_1` y
`Columna_Arcada_2` (carpeta Environment, enganchadas a Parking_Estacionamiento) donde estaban,
corridas 1 m hacia el carril del auto. Si los actores ya existen solo cambia la malla y conserva la
posicion ajustada a mano. No guarda el nivel. Informe: Docs/parking_columns.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/Parking"
NAME = "SM_ParkingColumna"
# centro del pie en coordenadas locales del estacionamiento (cm): GLB (x, y) -> (100x, -100y)
SPOTS = {"Columna_Arcada_1": (-730.0, -300.0), "Columna_Arcada_2": (-730.0, 100.0)}
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}

try:
    level_actors = actors.get_all_level_actors()
    parking = next(a for a in level_actors if a.get_actor_label() == "Parking_Estacionamiento")
    existing = {a.get_actor_label(): a for a in level_actors if a.get_actor_label() in SPOTS}
    path = f"{DEST}/{NAME}"
    for a in existing.values():  # soltar referencias antes de borrar
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
    data.import_uniform_scale = 1.0
    task = unreal.AssetImportTask()
    task.filename = str(project / f"SourceAssets/Parking/{NAME}.fbx")
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

    # mismos materiales que el estacionamiento, por nombre de ranura
    by_name = {str(m.material_slot_name): m.material_interface for m in parking.static_mesh_component.static_mesh.static_materials}
    materials = mesh.static_materials
    missing = []
    for m in materials:
        if str(m.material_slot_name) in by_name:
            m.set_editor_property("material_interface", by_name[str(m.material_slot_name)])
        else:
            missing.append(str(m.material_slot_name))
    if missing:
        raise RuntimeError(f"Materiales sin par en SM_Parking: {missing}")
    mesh.set_editor_property("static_materials", materials)
    if not lib.save_loaded_asset(mesh, False):
        raise RuntimeError(f"No se pudo guardar {NAME}")
    hulls = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(mesh)

    base = parking.get_actor_transform()
    placed = {}
    for label, (x, y) in SPOTS.items():
        actor = existing.get(label)
        if actor is None:
            world = base.transform_location(unreal.Vector(x, y, 0.0))
            actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, world, parking.get_actor_rotation())
            actor.set_actor_label(label)
            actor.set_folder_path("Environment")
            actor.attach_to_actor(parking, "", unreal.AttachmentRule.KEEP_WORLD,
                                  unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
        comp = actor.static_mesh_component
        comp.set_static_mesh(mesh)
        comp.set_collision_profile_name("BlockAll")
        loc = actor.get_actor_location()
        placed[label] = [round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)]
    report.update(passed=True, mesh=mesh.get_path_name(), collisions=hulls, actors=placed,
                  materials=[str(m.material_slot_name) for m in materials])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[PARKING_COLUMNS] {error}")
(project / "Docs/parking_columns.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
