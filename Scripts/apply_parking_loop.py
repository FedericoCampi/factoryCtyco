"""Editor Python (con L_FactoryDemo abierto): estacionamiento abierto + auto en loop.

1. SM_Parking (sin el primer pilar de la arcada) en Parking_Estacionamiento (reimport_parking_mesh.py).
2. Quita las maquinas y guias de cinta de la demo que estaban dentro del estacionamiento.
3. Importa SK_AutoBasico (SourceAssets/AutoBasico/auto_loop.fbx) y lo coloca como Auto_Loop en
   el mismo origen que el estacionamiento (enganchado a el), con su animacion en loop.
No guarda el nivel. Informe: Docs/parking_loop.json.
"""
import json
import runpy
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/AutoBasico"
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}


def import_car():
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = True
    options.import_as_skeletal = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    options.original_import_type = options.mesh_type_to_import
    options.import_animations = True
    options.import_materials = True
    options.import_textures = True
    options.create_physics_asset = True
    data = options.skeletal_mesh_import_data
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    anim = options.anim_sequence_import_data
    anim.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    anim.set_editor_property("remove_redundant_keys", False)
    task = unreal.AssetImportTask()
    task.filename = str(project / "SourceAssets/AutoBasico/auto_loop.fbx")
    task.destination_path = DEST
    task.destination_name = "SK_AutoBasico"
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)
    mesh = unreal.load_asset(f"{DEST}/SK_AutoBasico")
    anims = [a for a in map(unreal.load_asset, lib.list_assets(DEST, recursive=False)) if isinstance(a, unreal.AnimSequence)]
    if not isinstance(mesh, unreal.SkeletalMesh) or len(anims) != 1:
        raise RuntimeError("No se importo el auto con su animacion")
    return mesh, anims[0]


try:
    runpy.run_path(str(project / "Scripts/reimport_parking_mesh.py"), run_name="__main__")
    parking = json.loads((project / "Docs/parking_reimport.json").read_text(encoding="utf-8"))
    if not parking.get("passed"):
        raise RuntimeError("Estacionamiento: " + parking.get("error", "?"))

    removed = []
    park_at = next(a for a in actors.get_all_level_actors() if a.get_actor_label() == "Parking_Estacionamiento").get_actor_location()
    for a in actors.get_all_level_actors():
        l = a.get_actor_location() - park_at  # medidas de SM_Parking (x -1143..1190, y -1243..1043)
        inside = -1150 < l.x < 1150 and -1250 < l.y < 1250
        if inside and (isinstance(a, unreal.FactoryBuilding) or a.get_actor_label().startswith("FactoryGuide_")):
            removed.append(a.get_actor_label())
            actors.destroy_actor(a)

    for old in actors.get_all_level_actors():
        if old.get_actor_label() == "Auto_Loop":
            actors.destroy_actor(old)
    # Import limpio: reimportar encima de un asset existente puede cambiarle la escala.
    if lib.does_directory_exist(DEST):
        for path in lib.list_assets(DEST, recursive=True):
            lib.delete_asset(path.split(".")[0])
    mesh, anim = import_car()
    park = next(a for a in actors.get_all_level_actors() if a.get_actor_label() == "Parking_Estacionamiento")
    car = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, park.get_actor_location(), park.get_actor_rotation())
    car.set_actor_label("Auto_Loop")
    car.set_folder_path("Environment")
    car.attach_to_actor(park, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                        unreal.AttachmentRule.KEEP_WORLD, False)  # se mueve con el estacionamiento
    comp = car.skeletal_mesh_component
    comp.set_skinned_asset_and_update(mesh)
    comp.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    data = comp.get_editor_property("animation_data")
    data.set_editor_property("anim_to_play", anim)
    data.set_editor_property("saved_looping", True)
    data.set_editor_property("saved_playing", True)
    comp.set_editor_property("animation_data", data)
    comp.set_editor_property("visibility_based_anim_tick_option",
                             unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    # La malla en reposo esta en el origen; el recorrido llega a 9 m: agrandar los limites.
    comp.set_editor_property("bounds_scale", 12.0)
    comp.set_collision_profile_name("BlockAllDynamic")
    report.update(passed=True, parking=parking, removed=removed, car=mesh.get_path_name(),
                  animation=anim.get_path_name(), anim_seconds=round(anim.get_play_length(), 2))
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[PARKING_LOOP] {error}")
(project / "Docs/parking_loop.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
