"""Editor Python: carga de cajas en el camion (28/09).

1. Reimporta SK_Camion (SourceAssets/Camion/camion_loop.fbx, de author_truck_loop.py: puerta de carga con
   hueso Puerta e interior) y se la vuelve a poner a Camion_Recorrido, sin tocar su linea.
2. Importa SM_CintaCarga (author_loading_belt.py) con los rodillos de M_DespachoRodillo y, si no existe,
   pone `Cinta_Carga` (AFactoryLoadingBelt, carpeta Environment, enganchada al estacionamiento) al norte
   del carril: su punta de entrega queda junto a la puerta del camion cuando este para, 2,5 m antes de
   la barrera. Si ya existe conserva su lugar.
Con -unattended abre el mapa, guarda y cierra; con el editor abierto no guarda el nivel.
Informe: Docs/truck_loading.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
TRUCK_DEST, BELT_DEST = "/Game/FactoryCtyco/Environments/Camion", "/Game/FactoryCtyco/Environments/CintaCarga"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
# cm en el espacio del estacionamiento: punta de carga en (252, 45), entrega en (252, 345) (+Y de Unreal,
# hacia el carril en y 550). El camion para con el centro de la puerta en x 252; su puerta rebatida
# (113 cm) cubre el espacio entre la cinta y el camion.
BELT_AT, BELT_YAW = unreal.Vector(252, 45, 0), 90.0
OLD_BELT_AT = unreal.Vector(252, 155, 0)   # lugar de la primera version (puerta hacia arriba)
lib = unreal.EditorAssetLibrary
report = {"passed": False}


def import_task(filename, dest, name, skeletal):
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = True
    options.import_materials = True
    options.import_as_skeletal = skeletal
    if skeletal:
        options.import_textures = True
        options.import_animations = True
        options.create_physics_asset = True
        options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
        data = options.skeletal_mesh_import_data
        anim = options.anim_sequence_import_data
        anim.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    else:
        options.import_textures = False
        options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
        data = options.static_mesh_import_data
        data.combine_meshes = True
        data.auto_generate_collision = False
        data.one_convex_hull_per_ucx = True
    options.original_import_type = options.mesh_type_to_import
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    task = unreal.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = dest
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(dest, only_if_is_dirty=True, recursive=True)
    return unreal.load_asset(f"{dest}/{name}")


try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP):
        raise RuntimeError(f"No se pudo abrir {MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level = actors.get_all_level_actors()
    park = next(a for a in level if a.get_actor_label() == "Parking_Estacionamiento")
    truck = next((a for a in level if isinstance(a, unreal.FactoryVehiclePath)), None)
    if truck is None:
        raise RuntimeError("No hay Camion_Recorrido (correr apply_vehicle_path.py)")

    # 1. camion: import limpio (reimportar encima puede cambiar la escala) y de nuevo en su actor
    truck.set_editor_property("vehicle_mesh", None)
    truck.get_editor_property("vehicle").set_skinned_asset_and_update(None)
    for path in lib.list_assets(TRUCK_DEST, recursive=True):
        lib.delete_asset(path.split(".")[0])
    mesh = import_task(project / "SourceAssets/Camion/camion_loop.fbx", TRUCK_DEST, "SK_Camion", True)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError("No se importo SK_Camion")
    truck.modify()
    truck.set_editor_property("vehicle_mesh", mesh)
    truck.get_editor_property("vehicle").set_skinned_asset_and_update(mesh)

    # 2. cinta de carga
    belt_actor = next((a for a in level if isinstance(a, unreal.FactoryLoadingBelt)), None)
    if belt_actor:
        belt_actor.get_editor_property("belt").set_static_mesh(None)
    if lib.does_asset_exist(f"{BELT_DEST}/SM_CintaCarga"):
        lib.delete_asset(f"{BELT_DEST}/SM_CintaCarga")
    belt_mesh = import_task(project / "SourceAssets/CintaCarga/SM_CintaCarga.fbx", BELT_DEST, "SM_CintaCarga", False)
    if not isinstance(belt_mesh, unreal.StaticMesh):
        raise RuntimeError("No se importo SM_CintaCarga")
    roller = unreal.load_asset("/Game/FactoryCtyco/Environments/DespachoMachine/M_DespachoRodillo")
    materials = belt_mesh.static_materials
    for m in materials:
        if "Rodillo" in str(m.material_slot_name) and roller:
            m.set_editor_property("material_interface", roller)
    belt_mesh.set_editor_property("static_materials", materials)
    lib.save_loaded_asset(belt_mesh, False)
    created = belt_actor is None
    if created:
        spot = park.get_actor_transform().transform_location(BELT_AT)
        belt_actor = actors.spawn_actor_from_class(unreal.FactoryLoadingBelt, spot,
                                                   park.get_actor_rotation().combine(unreal.Rotator(0, 0, BELT_YAW)))
        belt_actor.set_actor_label("Cinta_Carga")
        belt_actor.set_folder_path("Environment")
        belt_actor.attach_to_actor(park, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                                   unreal.AttachmentRule.KEEP_WORLD, False)
    elif (belt_actor.get_actor_location() - park.get_actor_transform().transform_location(OLD_BELT_AT)).length() < 5:
        belt_actor.set_actor_location(park.get_actor_transform().transform_location(BELT_AT), False, False)
    belt_actor.modify()
    belt_actor.get_editor_property("belt").set_static_mesh(belt_mesh)
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    loc = belt_actor.get_actor_location()
    report.update(passed=True, truck_mesh=mesh.get_path_name(), belt_created=created,
                  belt_location=[round(loc.x), round(loc.y), round(loc.z)], roller=bool(roller),
                  belt_materials=[str(m.material_slot_name) for m in belt_mesh.static_materials])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[TRUCK_LOADING] {error}")
finally:
    (project / "Docs/truck_loading.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
