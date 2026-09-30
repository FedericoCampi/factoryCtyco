"""Editor Python (con L_FactoryDemo abierto): reemplaza el auto basico por el camion del usuario.

Importa SK_Camion (SourceAssets/Camion/camion_loop.fbx, de author_truck_loop.py) en
/Game/FactoryCtyco/Environments/Camion, borra `Auto_Loop` y pone `Camion_Loop` (SkeletalMeshActor, carpeta
Environment, enganchado a Parking_Estacionamiento en su mismo origen) con la animacion en loop.
Los assets del auto basico quedan en /Game/FactoryCtyco/Environments/AutoBasico, sin uso.
No guarda el nivel (guardarlo a mano). Informe: Docs/truck_loop.json.
Con el editor abierto: correrlo por MCP (execute_python con runpy.run_path).
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SOURCE = project / "SourceAssets/Camion"
DEST = "/Game/FactoryCtyco/Environments/Camion"
NAME, LABEL, OLD = "SK_Camion", "Camion_Loop", "Auto_Loop"
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
build = json.loads((SOURCE / "camion_build.json").read_text(encoding="utf-8"))
report = {"passed": False}


def import_truck():
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
    task.filename = str(SOURCE / "camion_loop.fbx")
    task.destination_path = DEST
    task.destination_name = NAME
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    lib.save_directory(DEST, only_if_is_dirty=True, recursive=True)
    mesh = unreal.load_asset(f"{DEST}/{NAME}")
    anims = [a for a in map(unreal.load_asset, lib.list_assets(DEST, recursive=False)) if isinstance(a, unreal.AnimSequence)]
    if not isinstance(mesh, unreal.SkeletalMesh) or len(anims) != 1:
        raise RuntimeError("No se importo el camion con su animacion")
    return mesh, anims[0]


try:
    level = actors.get_all_level_actors()
    park = next((a for a in level if a.get_actor_label() == "Parking_Estacionamiento"), None)
    if park is None:
        raise RuntimeError("Abrir L_FactoryDemo (no esta Parking_Estacionamiento)")
    removed = []
    for old in level:
        if old.get_actor_label() in (OLD, LABEL):
            removed.append(old.get_actor_label())
            actors.destroy_actor(old)
    # Import limpio: reimportar encima de un asset existente puede cambiarle la escala.
    if lib.does_directory_exist(DEST):
        for path in lib.list_assets(DEST, recursive=True):
            lib.delete_asset(path.split(".")[0])
    mesh, anim = import_truck()
    box = mesh.get_bounds().box_extent
    length = box.x * 2
    if abs(length - build["size_m"][0] * 100) > 10:
        raise RuntimeError(f"Largo inesperado {length:.0f} cm")
    truck = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, park.get_actor_location(), park.get_actor_rotation())
    truck.set_actor_label(LABEL)
    truck.set_folder_path("Environment")
    truck.attach_to_actor(park, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                          unreal.AttachmentRule.KEEP_WORLD, False)  # se mueve con el estacionamiento
    comp = truck.skeletal_mesh_component
    comp.set_skinned_asset_and_update(mesh)
    comp.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    data = comp.get_editor_property("animation_data")
    data.set_editor_property("anim_to_play", anim)
    data.set_editor_property("saved_looping", True)
    data.set_editor_property("saved_playing", True)
    comp.set_editor_property("animation_data", data)
    comp.set_editor_property("visibility_based_anim_tick_option",
                             unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    # La malla en reposo esta en el origen; el recorrido llega a ~23 m: agrandar los limites.
    comp.set_editor_property("bounds_scale", 10.0)
    comp.set_collision_profile_name("BlockAllDynamic")
    report.update(passed=True, removed=removed, mesh=mesh.get_path_name(), animation=anim.get_path_name(),
                  anim_seconds=round(anim.get_play_length(), 2), length_cm=round(length, 1),
                  bones=build["bones"],
                  materials=[str(m.material_slot_name) for m in mesh.materials])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[TRUCK_LOOP] {error}")
(project / "Docs/truck_loop.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
