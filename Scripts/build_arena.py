"""Import the user's arena and static robot into this new Unreal project."""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
report = {"passed": False}
tools = unreal.AssetToolsHelpers.get_asset_tools()
library = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
gameplay = unreal.get_default_object(unreal.GameplayStatics)

def save(asset):
    if not library.save_loaded_asset(asset, False):
        raise RuntimeError(f"Could not save {asset.get_path_name()}")

def import_fbx(source, destination, name, custom_collision=False):
    path = f"{destination}/{name}"
    existing = unreal.load_asset(path) if library.does_asset_exist(path) else None
    if existing:
        return existing
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
    data.one_convex_hull_per_ucx = True
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    data.generate_lightmap_u_vs = False
    data.build_nanite = False
    data.vertex_color_import_option = unreal.VertexColorImportOption.REPLACE
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = destination
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = False
    task.factory = unreal.FbxFactory()
    task.options = options
    tools.import_asset_tasks([task])
    imported = [unreal.load_asset(p) for p in task.imported_object_paths]
    imported = [a for a in imported if isinstance(a, unreal.StaticMesh)]
    if len(imported) != 1:
        raise RuntimeError(f"Expected one static mesh: {source}, got {len(imported)}")
    return imported[0]

def spawn(cls, location, rotation=None):
    transform = unreal.Transform(location=location, rotation=rotation or unreal.Rotator())
    scale = unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT
    actor = gameplay.call_method("BeginDeferredActorSpawnFromClass", args=(
        world, cls, transform, unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN, None, scale))
    if actor is None:
        raise RuntimeError(f"Could not spawn {cls}")
    return gameplay.call_method("FinishSpawningActor", args=(actor, transform, scale))

try:
    arena = import_fbx(project / "SourceAssets/SceneRobot/scene_unreal.fbx",
        "/Game/FactoryCtyco/Environments/SceneRobot", "SM_SceneRobot", True)
    build = json.loads((project / "SourceAssets/SceneRobot/build.json").read_text())
    count = meshes.get_convex_collision_count(arena)
    if count != build["convex_collision_pieces"]:
        raise RuntimeError(f"Expected {build['convex_collision_pieces']} collision hulls; got {count}")
    report["arena"] = {"asset": arena.get_path_name(), "convex_collisions": count,
        "materials": len(arena.static_materials), "triangles": arena.get_num_triangles(0)}
    unreal.log("[ARENA_BUILD] Arena and collisions imported")
    robot = import_fbx(project / "SourceAssets/Robot1/robot1_unreal.fbx",
        "/Game/FactoryCtyco/Characters/Robot1", "SM_Robot1")
    bounds = robot.get_bounding_box()
    height = bounds.max.z - bounds.min.z
    if height < 1:
        raise RuntimeError(f"Robot import has unexpected height: {height}")
    scale = 180.0 / height
    report["robot"] = {"asset": robot.get_path_name(), "source_height_cm": height,
        "display_height_cm": 180, "triangles": robot.get_num_triangles(0),
        "rigged": False, "animations": 0}
    bp_path = "/Game/FactoryCtyco/Blueprints/BP_Robot1"
    if library.does_asset_exist(bp_path):
        bp = unreal.load_asset(bp_path)
    else:
        bp = tools.duplicate_asset("BP_Robot1", "/Game/FactoryCtyco/Blueprints",
            unreal.load_asset("/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"))
    bp.modify()
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    funcs = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
    parent = handles[0]
    robot_component = None
    for handle in handles:
        data = subsystem.k2_find_subobject_data_from_handle(handle)
        obj = funcs.get_object_for_blueprint(data, bp)
        if isinstance(obj, unreal.CapsuleComponent):
            parent = handle
        if isinstance(obj, unreal.StaticMeshComponent) and "RobotVisual" in obj.get_name():
            robot_component = obj
        if isinstance(obj, unreal.SkeletalMeshComponent):
            obj.modify()
            obj.set_editor_property("skeletal_mesh_asset", None)
            obj.set_editor_property("anim_class", None)
    if robot_component is None:
        handle, failure = subsystem.add_new_subobject(unreal.AddNewSubobjectParams(
            parent_handle=parent, new_class=unreal.StaticMeshComponent, blueprint_context=bp))
        if str(failure):
            raise RuntimeError(f"Cannot add robot visual: {failure}")
        subsystem.rename_subobject(handle, "RobotVisual")
        data = subsystem.k2_find_subobject_data_from_handle(handle)
        robot_component = funcs.get_object_for_blueprint(data, bp)
    robot_component.modify()
    robot_component.set_editor_property("static_mesh", robot)
    robot_component.set_editor_property("relative_scale3d", unreal.Vector(scale, scale, scale))
    robot_component.set_editor_property("relative_location", unreal.Vector(0, 0, -90 - bounds.min.z * scale))
    robot_component.set_editor_property("relative_rotation", unreal.Rotator(yaw=-90))
    robot_component.set_collision_profile_name("NoCollision")
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.modify()
    capsule = cdo.get_component_by_class(unreal.CapsuleComponent)
    capsule.set_editor_property("capsule_half_height", 90.0)
    capsule.set_editor_property("capsule_radius", 35.0)
    cdo.character_movement.set_editor_property("max_walk_speed", 450.0)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)
    mode_path = "/Game/FactoryCtyco/Blueprints/BP_FactoryGameMode"
    mode = unreal.load_asset(mode_path) if library.does_asset_exist(mode_path) else tools.duplicate_asset(
        "BP_FactoryGameMode", "/Game/FactoryCtyco/Blueprints",
        unreal.load_asset("/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode"))
    mode.modify()
    unreal.get_default_object(mode.generated_class()).set_editor_property("default_pawn_class", bp.generated_class())
    unreal.BlueprintEditorLibrary.compile_blueprint(mode)
    save(mode)
    unreal.log("[ARENA_BUILD] Robot character Blueprint created")

    if not levels.new_level("/Game/FactoryCtyco/Maps/L_Recoleccion"):
        raise RuntimeError("Could not create the arena level")
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property("default_game_mode", mode.generated_class())
    actor = spawn(unreal.StaticMeshActor, unreal.Vector())
    actor.set_actor_label("SceneRobot_Fabrica")
    actor.static_mesh_component.set_static_mesh(arena)
    actor.static_mesh_component.set_collision_profile_name("BlockAll")
    origin = arena.find_socket("LevelGeometry_Origin").relative_location
    axes = [arena.find_socket("LevelGeometry_Axis" + axis).relative_location - origin for axis in "XYZ"]
    if any(abs(axis.length() - 100) > .1 for axis in axes) or axes[2].z < 99.9:
        raise RuntimeError("Incorrect arena scale or up axis")
    def position(point):
        return origin + axes[0] * point[0] + axes[1] * point[1] + axes[2] * point[2]
    spawn_point = position(build["spawn_blender_metres"])
    start = spawn(unreal.PlayerStart, spawn_point, unreal.Rotator(pitch=-10, yaw=-90))
    start.set_actor_label("PlayerStart_Robot1")

    sunlight = spawn(unreal.DirectionalLight, unreal.Vector(0, 0, 700), unreal.Rotator(pitch=-50, yaw=-30))
    sunlight.set_actor_label("Sun")
    sunlight.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sunlight.light_component.set_editor_property("intensity", 3.0)
    sky = spawn(unreal.SkyLight, unreal.Vector(0, 0, 500))
    sky.set_actor_label("SkyFill")
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property("intensity", 1.0)
    sky.light_component.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    cubemap = unreal.load_asset("/Engine/EngineResources/DefaultTextureCube")
    if cubemap:
        sky.light_component.set_editor_property("cubemap", cubemap)
    post = spawn(unreal.PostProcessVolume, unreal.Vector())
    post.set_editor_property("unbound", True)
    settings = post.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", 0.0)
    settings.set_editor_property("override_auto_exposure_apply_physical_camera_exposure", True)
    settings.set_editor_property("auto_exposure_apply_physical_camera_exposure", False)
    post.set_editor_property("settings", settings)
    trace = unreal.TraceTypeQuery.TRACE_TYPE_QUERY1
    hit = unreal.SystemLibrary.line_trace_single(world, spawn_point + unreal.Vector(0, 0, 100),
        spawn_point - unreal.Vector(0, 0, 250), trace, False, [], unreal.DrawDebugTrace.NONE)
    fields = gameplay.call_method("BreakHitResult", args=(hit,)) if hit else None
    if not fields or not fields[0]:
        raise RuntimeError("PlayerStart has no collision floor")
    report["level"] = world.get_path_name()
    report["player_start_cm"] = [spawn_point.x, spawn_point.y, spawn_point.z]
    report["player_start_floor_z"] = fields[5].z
    if not levels.save_current_level():
        raise RuntimeError("Could not save arena level")
    library.save_directory("/Game/FactoryCtyco", False, True)
    report["passed"] = True
    report["scope"] = "Import, saved level, character configuration and collision floor. Gameplay verification is separate."
except Exception as exc:
    report["error"] = str(exc)
    raise
finally:
    (project / "Docs/arena_build.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    unreal.log("[ARENA_BUILD_RESULT] " + json.dumps(report))
