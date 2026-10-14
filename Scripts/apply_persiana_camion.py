"""Editor Python (04/10): reimporta el camion.

Reimporta SK_Camion (SourceAssets/Camion/camion_loop.fbx, de author_truck_loop.py: sin la pared de atras de la caja y
con el forro cerrado del costado) y se lo pone a cada AFactoryVehiclePath (Camion_Recorrido, Camion_Recorrido2), sin
tocar su linea. Borra antes solo lo que trae ese FBX (SK_Camion*, sus texturas y materiales): la persiana de tablillas
(SM_CamionPersiana*, M_Persiana*, de apply_persiana_tablillas.py) queda como esta.
Con -unattended abre el mapa, guarda y cierra; con el editor abierto no guarda el nivel.
Informe: Docs/persiana_camion.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SOURCE = project / "SourceAssets/Camion"
MAP = "/Game/FactoryCtyco/Maps/L_FactoryDemo"
DEST = "/Game/FactoryCtyco/Environments/Camion"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
build = json.loads((SOURCE / "camion_build.json").read_text(encoding="utf-8"))
report = {"passed": False}


def import_task(filename, name, skeletal):
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = True
    options.import_as_skeletal = skeletal
    options.import_materials = skeletal          # la persiana usa los materiales del camion
    options.import_textures = skeletal
    if skeletal:
        options.import_animations = True
        options.create_physics_asset = True
        options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
        data = options.skeletal_mesh_import_data
        anim = options.anim_sequence_import_data
        anim.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    else:
        options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
        data = options.static_mesh_import_data
        data.combine_meshes = True
        data.auto_generate_collision = False
    options.original_import_type = options.mesh_type_to_import
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    task = unreal.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)
    return unreal.load_asset(f"{DEST}/{name}")


try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP):
        raise RuntimeError(f"No se pudo abrir {MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    trucks = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.FactoryVehiclePath)]
    if not trucks:
        raise RuntimeError("No hay camiones (AFactoryVehiclePath) en el nivel")
    # Import limpio (reimportar encima puede cambiar la escala): primero se sueltan las referencias.
    for truck in trucks:
        truck.set_editor_property("vehicle_mesh", None)
        truck.get_editor_property("vehicle").set_skinned_asset_and_update(None)
    for path in lib.list_assets(DEST, recursive=True):
        name = path.split(".")[0].rsplit("/", 1)[-1]
        if name.startswith(("SK_Camion", "Image_", "Material_", "M_CamionInterior", "M_CamionTuerca")):
            lib.delete_asset(path.split(".")[0])
    mesh = import_task(SOURCE / "camion_loop.fbx", "SK_Camion", True)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError("No se importo SK_Camion")
    length = mesh.get_bounds().box_extent.x * 2
    if abs(length - build["size_m"][0] * 100) > 10:
        raise RuntimeError(f"SK_Camion mide {length:.0f} cm de largo")
    for truck in trucks:
        truck.modify()
        truck.set_editor_property("vehicle_mesh", mesh)
        truck.get_editor_property("vehicle").set_skinned_asset_and_update(mesh)
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, trucks=[t.get_actor_label() for t in trucks], length_cm=round(length, 1),
                  shutter_kept=lib.does_asset_exist(f"{DEST}/SM_CamionPersianaLama"))
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[PERSIANA_CAMION] {error}")
finally:
    (project / "Docs/persiana_camion.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
