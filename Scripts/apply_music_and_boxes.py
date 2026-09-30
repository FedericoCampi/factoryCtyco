"""Sin editor abierto: musica de fondo, sonidos de las cintas y animaciones para cargar cajas.

UnrealEditor.exe FactoryCtyco.uproject -ExecutePythonScript=Scripts/apply_music_and_boxes.py -unattended -nosound

Antes: python Scripts/make_music.py, python Scripts/make_belt_sounds.py,
blender -b --factory-startup -P Scripts/author_tecjunior_rig.py (genera TecJunior_Carry*.fbx) y
FactoryCtycoRuntime instalado (UFactoryCarryComponent, CarryLocomotion).
1. A_TecJunior_CarryIdle/Walk/Run y BS_TecJunior_Carry (mismas velocidades que la locomocion),
   asignado como CarryLocomotion en BP_FactoryRobot. No toca las animaciones existentes.
2. S_MusicaFabrica (loop) en el actor Musica_Fondo del nivel, sin espacializar.
3. S_CintaEncender / S_CintaApagar en cada AFactoryDispatchBelt.
Guarda el nivel. Informe: Docs/music_and_boxes.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
TEC = project / "SourceAssets/TecJunior"
FOLDER = "/Game/FactoryCtyco/Characters/TecJunior"
PAWN = "/Game/FactoryCtyco/Factory/BP_FactoryRobot"
AUDIO = "/Game/FactoryCtyco/Audio"
BELT_AUDIO = "/Game/FactoryCtyco/Environments/DispatchBox"
MUSIC_VOLUME = 0.35
assets = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.EditorAssetLibrary
report = {"passed": False}


def save(asset):
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError("No se pudo guardar " + asset.get_path_name())


def import_animation(kind, skeleton):
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = False
    options.import_as_skeletal = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
    options.original_import_type = options.mesh_type_to_import
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    options.skeleton = skeleton
    data = options.anim_sequence_import_data
    data.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property("use_default_sample_rate", True)
    data.set_editor_property("preserve_local_transform", True)
    data.set_editor_property("remove_redundant_keys", False)
    data.set_editor_property("convert_scene", True)
    data.set_editor_property("convert_scene_unit", True)
    task = unreal.AssetImportTask()
    task.filename = str(TEC / f"TecJunior_{kind}.fbx")
    task.destination_path = FOLDER
    task.destination_name = f"A_TecJunior_{kind}"
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    assets.import_asset_tasks([task])
    anim = next((a for a in map(unreal.load_asset, task.imported_object_paths) if isinstance(a, unreal.AnimSequence)), None)
    if anim is None:
        raise RuntimeError(f"No se importo TecJunior_{kind}.fbx")
    save(anim)
    return anim


def import_sound(filename, folder, name, looping=False):
    task = unreal.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    assets.import_asset_tasks([task])
    sound = unreal.load_asset(f"{folder}/{name}")
    if not isinstance(sound, unreal.SoundWave):
        raise RuntimeError(f"No se importo {filename}")
    sound.set_editor_property("looping", looping)
    save(sound)
    return sound


try:
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir L_FactoryDemo")
    rig = json.loads((TEC / "rig_report.json").read_text())
    walk, run = float(rig["authored_walk_speed_cm_s"]), float(rig["authored_run_speed_cm_s"])

    # 1. Animaciones de carga y su blend space (copia los parametros de la locomocion normal)
    base = unreal.load_asset(FOLDER + "/BS_TecJunior_Locomotion")
    skeleton = base.get_editor_property("skeleton")
    anims = {k: import_animation(k, skeleton) for k in ("CarryIdle", "CarryWalk", "CarryRun")}
    path = FOLDER + "/BS_TecJunior_Carry"
    if lib.does_asset_exist(path):
        blend = unreal.load_asset(path)
    else:
        factory = unreal.BlendSpaceFactory1D()
        factory.set_editor_property("target_skeleton", skeleton)
        blend = assets.create_asset("BS_TecJunior_Carry", FOLDER, unreal.BlendSpace1D, factory)
    blend.set_editor_property("blend_parameters", base.get_editor_property("blend_parameters"))
    samples = []
    for kind, speed in (("CarryIdle", 0.0), ("CarryWalk", walk), ("CarryRun", run)):
        sample = unreal.BlendSample()
        sample.set_editor_property("animation", anims[kind])
        sample.set_editor_property("sample_value", unreal.Vector(speed, 0, 0))
        sample.set_editor_property("rate_scale", 1.0)
        samples.append(sample)
    blend.set_editor_property("sample_data", samples)
    blend.set_editor_property("target_weight_interpolation_speed_per_sec", 7.0)
    blend.set_editor_property("interpolate_using_grid", False)
    unreal.RobotLocomotionComponent.rebuild_blend_space(blend)
    save(blend)

    bp = unreal.load_asset(PAWN)
    bp.modify()
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    funcs = unreal.SubobjectDataBlueprintFunctionLibrary
    locomotion = next((o for o in (funcs.get_object_for_blueprint(subsystem.k2_find_subobject_data_from_handle(h), bp)
                                   for h in subsystem.k2_gather_subobject_data_for_blueprint(bp))
                       if isinstance(o, unreal.RobotLocomotionComponent)), None)
    if not locomotion:
        raise RuntimeError("BP_FactoryRobot no tiene RobotLocomotionComponent")
    locomotion.modify()
    locomotion.set_editor_property("carry_locomotion", blend)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)

    # 2. Musica de fondo
    music = import_sound(project / "SourceAssets/Audio/musica_fabrica.wav", AUDIO, "S_MusicaFabrica", looping=True)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    player = next((a for a in actors.get_all_level_actors() if a.get_actor_label() == "Musica_Fondo"), None)
    if not player:
        player = actors.spawn_actor_from_class(unreal.AmbientSound, unreal.Vector(0, 0, 400))
        player.set_actor_label("Musica_Fondo")
        player.set_folder_path("Audio")
    audio = player.get_component_by_class(unreal.AudioComponent)
    audio.set_editor_property("sound", music)
    audio.set_editor_property("allow_spatialization", False)
    audio.set_editor_property("volume_multiplier", MUSIC_VOLUME)
    audio.set_editor_property("auto_activate", True)

    # 3. Sonidos de encender / apagar las cintas
    on = import_sound(project / "SourceAssets/DispatchBox/cinta_encender.wav", BELT_AUDIO, "S_CintaEncender")
    off = import_sound(project / "SourceAssets/DispatchBox/cinta_apagar.wav", BELT_AUDIO, "S_CintaApagar")
    belts = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.FactoryDispatchBelt)]
    for belt in belts:
        belt.set_editor_property("on_sound", on)
        belt.set_editor_property("off_sound", off)

    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, carry_blendspace=blend.get_path_name(),
                  carry_animations={k: a.get_path_name() for k, a in anims.items()},
                  music=music.get_path_name(), music_volume=MUSIC_VOLUME, music_seconds=round(music.get_editor_property("duration"), 1),
                  belts=[b.get_actor_label() for b in belts], belt_capacity={b.get_actor_label(): b.get_capacity() for b in belts})
except Exception as error:
    report["error"] = repr(error)
    unreal.log_error(f"[MUSIC_AND_BOXES] {error}")
finally:
    (project / "Docs/music_and_boxes.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    unreal.SystemLibrary.quit_editor()
