"""Editor Python: porton enrollable en la entrada de los camiones (muro oeste del estacionamiento), 28/09.

Importa SM_Porton, SM_PortonCaja y SM_PortonBoton (SourceAssets/Porton, author_roll_door.py) en
/Game/FactoryCtyco/Environments/Porton y, si no existe, pone `Porton_Camiones` (AFactoryRollDoor, carpeta
Environment, enganchado a Parking_Estacionamiento): cortina en la abertura (dentro del espesor del muro), caja
del rollo sobre la abertura del lado de adentro y botonera en la cara de adentro de la columna de su derecha
(vista desde el estacionamiento). La luz de la botonera usa M_Boton (rojo cerrado, verde abierto).
Si ya existe solo cambia las mallas y conserva su lugar. Con -unattended abre el mapa, guarda y cierra.
Informe: Docs/roll_door.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SOURCE = project / "SourceAssets/Porton"
DEST = "/Game/FactoryCtyco/Environments/Porton"
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
LABEL = "Porton_Camiones"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
# cm en el espacio del estacionamiento (Blender x, y, z -> Unreal 100x, -100y, 100z): borde de arriba de la
# cortina al centro de la abertura (x -10.95, y -6.0, z 2.44 m); columna -4 (cara de adentro x -10.69, y -4.0).
DOOR_AT = unreal.Vector(-1095, 600, 244)
BUTTON_REL, HOUSING_REL = unreal.Vector(26, -200, -119), unreal.Vector(43, 0, 24)
PIECES = ("SM_Porton", "SM_PortonCaja", "SM_PortonBoton")
lib = unreal.EditorAssetLibrary
report = {"passed": False}


def import_mesh(name):
    path = f"{DEST}/{name}"
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {name}")
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = True
    options.import_textures = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = name == "SM_PortonBoton"
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    task = unreal.AssetImportTask()
    task.filename = str(SOURCE / f"{name}.fbx")
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"No se importo {name}")
    return mesh


try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP):
        raise RuntimeError(f"No se pudo abrir {MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level = actors.get_all_level_actors()
    door = next((a for a in level if a.get_actor_label() == LABEL), None)
    if door:
        for comp in ("door", "housing", "button"):
            door.get_editor_property(comp).set_static_mesh(None)
    meshes = {n: import_mesh(n) for n in PIECES}
    light = unreal.load_asset("/Game/FactoryCtyco/Environments/DispatchBox/M_Boton")
    button_mesh = meshes["SM_PortonBoton"]
    materials = button_mesh.static_materials
    for m in materials:
        if "PortonLuz" in str(m.material_slot_name) and light:
            m.set_editor_property("material_interface", light)
    button_mesh.set_editor_property("static_materials", materials)
    lib.save_directory(DEST, only_if_is_dirty=False, recursive=True)
    created = door is None
    if created:
        park = next(a for a in level if a.get_actor_label() == "Parking_Estacionamiento")
        door = actors.spawn_actor_from_class(unreal.FactoryRollDoor, park.get_actor_transform().transform_location(DOOR_AT),
                                             park.get_actor_rotation())
        door.set_actor_label(LABEL)
        door.set_folder_path("Environment")
        door.attach_to_actor(park, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                             unreal.AttachmentRule.KEEP_WORLD, False)
        door.get_editor_property("button").set_relative_location(BUTTON_REL, False, False)
        door.get_editor_property("housing").set_relative_location(HOUSING_REL, False, False)
    door.modify()
    door.get_editor_property("door").set_static_mesh(meshes["SM_Porton"])
    door.get_editor_property("housing").set_static_mesh(meshes["SM_PortonCaja"])
    door.get_editor_property("button").set_static_mesh(button_mesh)
    sound = unreal.load_asset("/Game/FactoryCtyco/Environments/DispatchBox/S_CintaEncender")
    if sound:
        door.set_editor_property("move_sound", sound)
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    loc = door.get_actor_location()
    report.update(passed=True, created=created, location=[round(loc.x), round(loc.y), round(loc.z)], light=bool(light),
                  sound=bool(sound))
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[ROLL_DOOR] {error}")
finally:
    (project / "Docs/roll_door.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
