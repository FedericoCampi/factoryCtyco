"""Editor Python: import TecJunior and make it the factory demo's playable character.

Inputs: SourceAssets/TecJunior/*.fbx and rig_report.json (author_tecjunior_rig.py).
Keeps Robot1's assets; BP_FactoryRobot is copied to BP_FactoryRobot_Robot1Backup first.
Writes Docs/tecjunior_import.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
SOURCE = project / "SourceAssets/TecJunior"
FOLDER = "/Game/FactoryCtyco/Characters/TecJunior"
PAWN = "/Game/FactoryCtyco/Factory/BP_FactoryRobot"
BACKUP = "BP_FactoryRobot_Robot1Backup"
rig = json.loads((SOURCE / "rig_report.json").read_text())
HALF_HEIGHT = round(rig["height_m"] * 100 / 2)   # capsule half height matches the character
WALK = float(rig["authored_walk_speed_cm_s"])
RUN = float(rig["authored_run_speed_cm_s"])   # Shift; clips play at rate 1 up to this speed
assets = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.EditorAssetLibrary
report = {"passed": False}

def save(asset):
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError("Could not save " + asset.get_path_name())

def import_fbx(filename, name, skeleton=None):
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = skeleton is None
    options.import_as_skeletal = True
    options.mesh_type_to_import = (unreal.FBXImportType.FBXIT_SKELETAL_MESH if skeleton is None
                                   else unreal.FBXImportType.FBXIT_ANIMATION)
    options.original_import_type = options.mesh_type_to_import
    options.import_animations = skeleton is not None
    options.import_materials = skeleton is None
    options.import_textures = skeleton is None
    options.create_physics_asset = False
    if skeleton:
        options.skeleton = skeleton
        data = options.anim_sequence_import_data
        data.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        data.set_editor_property("use_default_sample_rate", True)
        data.set_editor_property("preserve_local_transform", True)
        data.set_editor_property("remove_redundant_keys", False)
        data.set_editor_property("convert_scene", True)
        data.set_editor_property("convert_scene_unit", True)
    else:
        data = options.skeletal_mesh_import_data
        data.convert_scene = True
        data.convert_scene_unit = True
        data.import_uniform_scale = 1.0
        data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task = unreal.AssetImportTask()
    task.filename = str(SOURCE / filename)
    task.destination_path = FOLDER
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    task.options = options
    assets.import_asset_tasks([task])
    cls = unreal.AnimSequence if skeleton else unreal.SkeletalMesh
    result = next((a for a in map(unreal.load_asset, task.imported_object_paths) if isinstance(a, cls)), None)
    if result is None:
        raise RuntimeError("Import failed: " + filename)
    if isinstance(result, unreal.SkeletalMesh):
        if result.skeleton is None:
            raise RuntimeError("Imported mesh has no skeleton")
        save(result.skeleton)
    save(result)
    return result

try:
    mesh = import_fbx("TecJunior_Skeletal.fbx", "SK_TecJunior")
    height = mesh.get_bounds().box_extent.z * 2
    if abs(height - rig["height_m"] * 100) > 8:
        raise RuntimeError(f"Unexpected character height {height:.1f} cm")
    for slot in mesh.get_editor_property("materials"):
        material = slot.get_editor_property("material_interface")
        base = material.get_base_material() if material else None
        if isinstance(base, unreal.Material) and not base.get_editor_property("used_with_skeletal_mesh"):
            base.set_editor_property("used_with_skeletal_mesh", True)
            unreal.MaterialEditingLibrary.recompile_material(base)
            save(base)
    animations = {kind: import_fbx(f"TecJunior_{kind}.fbx", f"A_TecJunior_{kind}", mesh.skeleton)
                  for kind in ("Idle", "Walk", "Run", "Airborne")}

    blend_path = FOLDER + "/BS_TecJunior_Locomotion"
    if lib.does_asset_exist(blend_path):
        blend = unreal.load_asset(blend_path)
    else:
        factory = unreal.BlendSpaceFactory1D()
        factory.set_editor_property("target_skeleton", mesh.skeleton)
        blend = assets.create_asset("BS_TecJunior_Locomotion", FOLDER, unreal.BlendSpace1D, factory)
    parameters = list(blend.get_editor_property("blend_parameters"))
    axis = unreal.BlendParameter()
    axis.set_editor_property("display_name", "Speed")
    axis.set_editor_property("min", 0.0)
    axis.set_editor_property("max", RUN)
    axis.set_editor_property("grid_num", 4)
    parameters[0] = axis
    blend.set_editor_property("blend_parameters", parameters)
    samples = []
    for kind, speed in (("Idle", 0.0), ("Walk", WALK), ("Run", RUN)):
        sample = unreal.BlendSample()
        sample.set_editor_property("animation", animations[kind])
        sample.set_editor_property("sample_value", unreal.Vector(speed, 0, 0))
        sample.set_editor_property("rate_scale", 1.0)
        samples.append(sample)
    blend.set_editor_property("sample_data", samples)
    blend.set_editor_property("target_weight_interpolation_speed_per_sec", 7.0)
    blend.set_editor_property("interpolate_using_grid", False)
    unreal.RobotLocomotionComponent.rebuild_blend_space(blend)
    save(blend)

    backup_path = "/Game/FactoryCtyco/Factory/" + BACKUP
    if not lib.does_asset_exist(backup_path):
        if not lib.duplicate_asset(PAWN, backup_path):
            raise RuntimeError("Could not back up " + PAWN)
    bp = unreal.load_asset(PAWN)
    bp.modify()
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    funcs = unreal.SubobjectDataBlueprintFunctionLibrary
    locomotion = skeletal = None
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        obj = funcs.get_object_for_blueprint(subsystem.k2_find_subobject_data_from_handle(handle), bp)
        if isinstance(obj, unreal.SkeletalMeshComponent):
            skeletal = obj
        elif isinstance(obj, unreal.RobotLocomotionComponent):
            locomotion = obj
    if not skeletal or not locomotion:
        raise RuntimeError("BP_FactoryRobot is missing its mesh or locomotion component")
    skeletal.modify()
    skeletal.set_editor_property("skeletal_mesh_asset", mesh)
    skeletal.set_editor_property("override_materials", [])
    skeletal.set_editor_property("relative_location", unreal.Vector(0, 0, -HALF_HEIGHT))
    data = skeletal.get_editor_property("animation_data")
    data.set_editor_property("anim_to_play", blend)
    skeletal.set_editor_property("animation_data", data)
    locomotion.modify()
    locomotion.set_editor_property("locomotion", blend)
    locomotion.set_editor_property("airborne_pose", animations["Airborne"])
    # Movement speeds match the authored strides so feet do not slide.
    locomotion.set_editor_property("authored_walk_speed", RUN)
    locomotion.set_editor_property("walk_speed", WALK)
    locomotion.set_editor_property("fast_walk_speed", RUN)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.modify()
    radius = cdo.capsule_component.get_unscaled_capsule_radius()
    cdo.capsule_component.set_capsule_size(radius, HALF_HEIGHT)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)
    lib.save_directory(FOLDER, only_if_is_dirty=True, recursive=True)
    report.update(passed=True, mesh=mesh.get_path_name(), height_cm=round(height, 1),
                  animations={k: a.get_path_name() for k, a in animations.items()},
                  blendspace=blend.get_path_name(), pawn=PAWN, backup=backup_path,
                  capsule_cm={"radius": radius, "half_height": HALF_HEIGHT}, walk_speed_cm_s=WALK, run_speed_cm_s=RUN,
                  materials=[s.get_editor_property("material_interface").get_path_name()
                             for s in mesh.get_editor_property("materials") if s.get_editor_property("material_interface")])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[TECJUNIOR_IMPORT] {error}")
(project / "Docs/tecjunior_import.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
