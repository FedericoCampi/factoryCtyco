"""Editor Python: el vagabundo acostado, con su botella, en una esquina del estacionamiento de empleados (29/09).

Importa de SourceAssets/Vagabundo (author_vagabundo.py y make_vagabundo_voice.py) en /Game/FactoryCtyco/Characters/Vagabundo
(borra los assets antes): SK_Vagabundo (malla con esqueleto), A_Vagabundo_Idle (acostado, respira y mueve apenas la
cabeza), A_Vagabundo_LevantaBrazo (levanta el brazo cuando habla), SM_Botella y S_Vagabundo_YElla (su voz). Coloca el
actor `Vagabundo` (AFactoryNpc, carpeta Empleados) acostado a lo largo del cerco, en la esquina del fondo a la izquierda
del patio, con la cabeza hacia la nave, y `Vagabundo_Botella` junto a su mano. Al acercarse el jugador dice "¿Y ella?"
con su voz y levanta un brazo.
Idempotente. Con -unattended abre el mapa, guarda y cierra. Informe: Docs/vagabundo.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SRC = project / "SourceAssets/Vagabundo"
DEST = "/Game/FactoryCtyco/Characters/Vagabundo"
ORIGIN = unreal.Vector(-3800, 9000, 400)     # Empleados_Escena
SPOT = (-10.55, 6.3)                          # m de Blender de la escena: esquina del fondo a la izquierda
YAW = 0.0                                     # acostado a lo largo del cerco, la cabeza hacia la nave
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
report = {"passed": False}


def fresh(name):
    path = f"{DEST}/{name}"
    if lib.does_asset_exist(path) and not lib.delete_asset(path):
        raise RuntimeError(f"No se pudo borrar {path}")


def run(task_file, name, options=None, factory=None):
    task = unreal.AssetImportTask()
    task.filename = str(SRC / task_file)
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    if factory:
        task.factory = factory
    if options:
        task.options = options
    tools.import_asset_tasks([task])
    return [unreal.load_asset(p) for p in task.imported_object_paths]


try:
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if HEADLESS and not levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir el mapa")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by_label = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    old = by_label.pop("Vagabundo", None)
    if old:
        actors.destroy_actor(old)
    # la version anterior era una malla fija
    old_bottle = by_label.pop("Vagabundo_Botella", None)
    if old_bottle:
        actors.destroy_actor(old_bottle)
    for name in ("SM_Vagabundo", "A_Vagabundo_Idle", "A_Vagabundo_LevantaBrazo", "SM_Botella", "SK_Vagabundo",
                 "SK_Vagabundo_Skeleton", "SK_Vagabundo_PhysicsAsset", "S_Vagabundo_YElla"):
        fresh(name)

    # malla con esqueleto
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = True
    options.import_as_skeletal = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    options.original_import_type = options.mesh_type_to_import
    options.import_animations = False
    options.import_materials = True
    options.import_textures = True
    options.create_physics_asset = False
    data = options.skeletal_mesh_import_data
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh = next((a for a in run("SK_Vagabundo.fbx", "SK_Vagabundo", options, unreal.FbxFactory()) if isinstance(a, unreal.SkeletalMesh)), None)
    if mesh is None or mesh.skeleton is None:
        raise RuntimeError("No se importo el vagabundo con su esqueleto")
    lib.save_loaded_asset(mesh.skeleton)
    height = mesh.get_bounds().box_extent.z * 2
    report["height_cm"] = round(height)
    if abs(height - 172) > 12:
        raise RuntimeError(f"Altura inesperada: {height:.0f} cm")

    # animaciones: reposo y levantar el brazo
    def import_anim(filename, name):
        options = unreal.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.import_mesh = False
        options.import_as_skeletal = True
        options.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
        options.original_import_type = options.mesh_type_to_import
        options.import_animations = True
        options.import_materials = False
        options.import_textures = False
        options.skeleton = mesh.skeleton
        anim_data = options.anim_sequence_import_data
        anim_data.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        anim_data.set_editor_property("use_default_sample_rate", True)
        anim_data.set_editor_property("preserve_local_transform", True)
        anim_data.set_editor_property("remove_redundant_keys", False)
        anim_data.set_editor_property("convert_scene", True)
        anim_data.set_editor_property("convert_scene_unit", True)
        anim = next((a for a in run(filename, name, options, unreal.FbxFactory()) if isinstance(a, unreal.AnimSequence)), None)
        if anim is None:
            raise RuntimeError(f"No se importo {name}")
        return anim

    talk = import_anim("Vagabundo_LevantaBrazo.fbx", "A_Vagabundo_LevantaBrazo")
    report["talk_seconds"] = round(talk.get_play_length(), 2)
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = False
    options.import_as_skeletal = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
    options.original_import_type = options.mesh_type_to_import
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = mesh.skeleton
    anim_data = options.anim_sequence_import_data
    anim_data.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    anim_data.set_editor_property("use_default_sample_rate", True)
    anim_data.set_editor_property("preserve_local_transform", True)
    anim_data.set_editor_property("remove_redundant_keys", False)
    anim_data.set_editor_property("convert_scene", True)
    anim_data.set_editor_property("convert_scene_unit", True)
    idle = next((a for a in run("Vagabundo_Idle.fbx", "A_Vagabundo_Idle", options, unreal.FbxFactory()) if isinstance(a, unreal.AnimSequence)), None)
    if idle is None:
        raise RuntimeError("No se importo la animacion")
    report["idle_seconds"] = round(idle.get_play_length(), 2)

    # voz
    voice = next((a for a in run("vagabundo_y_ella.wav", "S_Vagabundo_YElla") if isinstance(a, unreal.SoundWave)), None)
    if voice is None:
        raise RuntimeError("No se importo la voz")
    report["voice_seconds"] = round(voice.get_editor_property("duration"), 2)

    where = ORIGIN + unreal.Vector(SPOT[0] * 100, -SPOT[1] * 100, 0)
    npc = actors.spawn_actor_from_class(unreal.FactoryNpc, where, unreal.Rotator(0, 0, YAW))
    npc.set_actor_label("Vagabundo")
    npc.set_folder_path("Empleados")
    npc.get_editor_property("skeletal").set_skinned_asset_and_update(mesh)
    npc.set_editor_property("idle_animation", idle)
    npc.set_editor_property("talk_animation", talk)
    npc.set_editor_property("speech_height", 85.0)
    blocker = npc.get_editor_property("blocker")   # acostado: largo a lo largo de Y
    blocker.set_box_extent(unreal.Vector(38, 98, 20))
    blocker.set_relative_location(unreal.Vector(0, 0, 20), False, False)
    # la botella, junto a su mano
    bottle_options = unreal.FbxImportUI()
    bottle_options.import_mesh = True
    bottle_options.import_as_skeletal = False
    bottle_options.import_materials = True
    bottle_options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    bottle_options.automated_import_should_detect_type = False
    bottle_options.static_mesh_import_data.combine_meshes = True
    bottle_options.static_mesh_import_data.auto_generate_collision = False
    bottle_options.static_mesh_import_data.convert_scene_unit = True
    bottle_mesh = next((a for a in run("SM_Botella.fbx", "SM_Botella", bottle_options, unreal.FbxFactory()) if isinstance(a, unreal.StaticMesh)), None)
    if bottle_mesh is None:
        raise RuntimeError("No se importo la botella")
    build = json.loads((SRC / "vagabundo_build.json").read_text(encoding="utf-8"))
    bx, by, bz = build["bottle_m"]
    bottle_at = npc.get_actor_transform().transform_location(unreal.Vector(bx * 100, -by * 100, bz * 100))
    bottle = actors.spawn_actor_from_class(unreal.StaticMeshActor, bottle_at, unreal.Rotator(0, 0, 0))
    bottle.set_actor_label("Vagabundo_Botella")
    bottle.set_folder_path("Empleados")
    bottle.static_mesh_component.set_static_mesh(bottle_mesh)
    bottle.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    bottle.attach_to_actor(npc, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    report["bottle"] = [round(bottle_at.x), round(bottle_at.y), round(bottle_at.z)]
    npc.set_editor_property("display_name", "Vagabundo")
    npc.set_editor_property("lines", ["¿Y ella?"])
    npc.set_editor_property("line_sounds", [voice])
    report["actor"] = {"world": [round(where.x), round(where.y), round(where.z)], "yaw": YAW}

    lib.save_directory(DEST, only_if_is_dirty=False, recursive=True)
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = True
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
finally:
    (project / "Docs/vagabundo.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
