"""Integrate Robot1's authored skeleton and locomotion, isometric camera and light."""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
report = {"passed":False}
assets = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
folder = '/Game/FactoryCtyco/Characters/Robot1/Rigged'

def save(asset):
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save '+asset.get_path_name())

def spawn(cls, location, rotation=None):
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    gameplay=unreal.get_default_object(unreal.GameplayStatics)
    transform=unreal.Transform(location=location,rotation=rotation or unreal.Rotator())
    scale=unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT
    actor=gameplay.call_method('BeginDeferredActorSpawnFromClass',args=(world,cls,transform,
        unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,scale))
    if actor is None: raise RuntimeError('Cannot spawn '+str(cls))
    return gameplay.call_method('FinishSpawningActor',args=(actor,transform,scale))

def import_fbx(filename, name, skeleton=None):
    path=folder+'/'+name
    if lib.does_asset_exist(path):
        existing=unreal.load_asset(path)
        if not isinstance(existing,unreal.SkeletalMesh) or existing.skeleton is not None:
            return existing
    options=unreal.FbxImportUI()
    options.automated_import_should_detect_type=False
    options.import_mesh=skeleton is None
    options.import_as_skeletal=True
    options.mesh_type_to_import=(unreal.FBXImportType.FBXIT_SKELETAL_MESH if skeleton is None
        else unreal.FBXImportType.FBXIT_ANIMATION)
    options.original_import_type=options.mesh_type_to_import
    options.import_animations=skeleton is not None
    options.import_materials=False
    options.import_textures=False
    options.create_physics_asset=False
    if skeleton:
        options.skeleton=skeleton
        options.anim_sequence_import_data.set_editor_property('animation_length',unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',True)
        options.anim_sequence_import_data.set_editor_property('preserve_local_transform',True)
        options.anim_sequence_import_data.set_editor_property('remove_redundant_keys',False)
        options.anim_sequence_import_data.set_editor_property('convert_scene',True)
        options.anim_sequence_import_data.set_editor_property('convert_scene_unit',True)
    else:
        options.skeletal_mesh_import_data.convert_scene=True
        options.skeletal_mesh_import_data.convert_scene_unit=True
        options.skeletal_mesh_import_data.import_uniform_scale=1.0
        options.skeletal_mesh_import_data.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=unreal.AssetImportTask()
    task.filename=str(project/'SourceAssets/Robot1/Rigged'/filename)
    task.destination_path=folder
    task.destination_name=name
    task.automated=True
    task.save=True
    task.replace_existing=lib.does_asset_exist(path)
    task.factory=unreal.FbxFactory()
    task.options=options
    assets.import_asset_tasks([task])
    imported=[unreal.load_asset(p) for p in task.imported_object_paths]
    cls=unreal.AnimSequence if skeleton else unreal.SkeletalMesh
    result=next((a for a in imported if isinstance(a,cls)),None)
    if result is None:
        raise RuntimeError('Import failed: '+filename)
    if isinstance(result,unreal.SkeletalMesh):
        if result.skeleton is None: raise RuntimeError('Imported mesh has no skeleton')
        save(result.skeleton)
    save(result)
    return result

try:
    mesh=import_fbx('Robot1_Skeletal.fbx','SK_Robot1')
    material=unreal.load_asset('/Game/FactoryCtyco/Characters/Robot1/Material_0')
    material.set_editor_property('used_with_skeletal_mesh',True)
    unreal.MaterialEditingLibrary.recompile_material(material)
    save(material)
    materials=list(mesh.get_editor_property('materials'))
    for slot in materials:
        slot.set_editor_property('material_interface',material)
    mesh.set_editor_property('materials',materials)
    save(mesh)
    animations={kind:import_fbx('Robot1_'+kind+'.fbx','A_Robot1_'+kind,mesh.skeleton)
        for kind in ['Idle','Walk','Airborne']}
    blendpath=folder+'/BS_Robot1_Locomotion'
    if lib.does_asset_exist(blendpath):
        blend=unreal.load_asset(blendpath)
    else:
        factory=unreal.BlendSpaceFactory1D()
        factory.set_editor_property('target_skeleton',mesh.skeleton)
        blend=assets.create_asset('BS_Robot1_Locomotion',folder,unreal.BlendSpace1D,factory)
    parameters=list(blend.get_editor_property('blend_parameters'))
    speed_axis=unreal.BlendParameter()
    speed_axis.set_editor_property('display_name','Speed')
    speed_axis.set_editor_property('min',0.0)
    speed_axis.set_editor_property('max',135.0)
    speed_axis.set_editor_property('grid_num',4)
    parameters[0]=speed_axis
    blend.set_editor_property('blend_parameters',parameters)
    assert blend.get_editor_property('blend_parameters')[0].get_editor_property('max')==135.0
    samples=[]
    for kind,speed in [('Idle',0.0),('Walk',135.0)]:
        sample=unreal.BlendSample()
        sample.set_editor_property('animation',animations[kind])
        sample.set_editor_property('sample_value',unreal.Vector(speed,0,0))
        sample.set_editor_property('rate_scale',1.0)
        samples.append(sample)
    blend.set_editor_property('sample_data',samples)
    blend.set_editor_property('target_weight_interpolation_speed_per_sec',7.0)
    blend.set_editor_property('interpolate_using_grid',False)
    unreal.RobotLocomotionComponent.rebuild_blend_space(blend)
    save(blend)
    report['animations']={kind:asset.get_path_name() for kind,asset in animations.items()}
    report['blendspace']=blend.get_path_name()
    unreal.log('[ARENA_UPGRADE] Skeleton, animations and locomotion blend space imported')

    bp=unreal.load_asset('/Game/FactoryCtyco/Blueprints/BP_Robot1')
    bp.modify()
    subsystem=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    funcs=unreal.SubobjectDataBlueprintFunctionLibrary
    handles=subsystem.k2_gather_subobject_data_for_blueprint(bp)
    runtime=None
    for handle in handles:
        data=subsystem.k2_find_subobject_data_from_handle(handle)
        obj=funcs.get_object_for_blueprint(data,bp)
        if isinstance(obj,unreal.StaticMeshComponent) and 'RobotVisual' in obj.get_name():
            obj.modify()
            obj.set_editor_property('static_mesh',None)
        elif isinstance(obj,unreal.SkeletalMeshComponent):
            obj.modify()
            obj.set_editor_property('skeletal_mesh_asset',mesh)
            obj.set_editor_property('anim_class',None)
            obj.set_editor_property('animation_mode',unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            obj.set_editor_property('relative_location',unreal.Vector(0,0,-90))
            obj.set_editor_property('relative_rotation',unreal.Rotator(yaw=-90))
            obj.set_editor_property('relative_scale3d',unreal.Vector(1,1,1))
            obj.set_editor_property('override_materials',[material])
            obj.set_editor_property('visibility_based_anim_tick_option',unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
            data=obj.get_editor_property('animation_data')
            data.set_editor_property('anim_to_play',blend)
            data.set_editor_property('saved_looping',True)
            data.set_editor_property('saved_playing',True)
            obj.set_editor_property('animation_data',data)
            obj.set_collision_profile_name('NoCollision')
        elif isinstance(obj,unreal.SpringArmComponent):
            obj.modify()
            obj.set_editor_property('use_pawn_control_rotation',False)
            obj.set_editor_property('absolute_rotation',True)
            obj.set_editor_property('inherit_pitch',False)
            obj.set_editor_property('inherit_yaw',False)
            obj.set_editor_property('inherit_roll',False)
            obj.set_editor_property('relative_rotation',unreal.Rotator(pitch=-55,yaw=-45))
            obj.set_editor_property('target_arm_length',2450.0)
            obj.set_editor_property('target_offset',unreal.Vector(0,0,35))
            obj.set_editor_property('do_collision_test',False)
        elif isinstance(obj,unreal.CameraComponent):
            obj.modify()
            obj.set_editor_property('use_pawn_control_rotation',False)
            obj.set_editor_property('field_of_view',35.0)
        elif isinstance(obj,unreal.RobotLocomotionComponent):
            runtime=obj
    if runtime is None:
        handle,failure=subsystem.add_new_subobject(unreal.AddNewSubobjectParams(
            parent_handle=handles[0],new_class=unreal.RobotLocomotionComponent,blueprint_context=bp))
        if str(failure): raise RuntimeError(str(failure))
        subsystem.rename_subobject(handle,'RobotLocomotion')
        runtime=funcs.get_object_for_blueprint(subsystem.k2_find_subobject_data_from_handle(handle),bp)
    runtime.set_editor_property('locomotion',blend)
    runtime.set_editor_property('airborne_pose',animations['Airborne'])
    runtime.set_editor_property('authored_walk_speed',135.0)
    runtime.set_editor_property('auto_activate',True)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=unreal.get_default_object(bp.generated_class())
    cdo.modify()
    cdo.set_editor_property('use_controller_rotation_yaw',False)
    cdo.character_movement.set_editor_property('max_walk_speed',190.0)
    cdo.character_movement.set_editor_property('orient_rotation_to_movement',True)
    cdo.character_movement.set_editor_property('rotation_rate',unreal.Rotator(yaw=540))
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)
    # Keep the existing WASD controls, while removing input that would rotate
    # the hidden controller direction behind a fixed isometric camera.
    for path in ['/Game/Input/IMC_Default','/Game/Input/IMC_MouseLook']:
        context=unreal.load_asset(path)
        for mapping in list(context.get_editor_property('mappings')):
            if 'Look' in mapping.action.get_name():
                context.unmap_all_keys_from_action(mapping.action)
        save(context)

    assert levels.load_level('/Game/FactoryCtyco/Maps/L_Recoleccion')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    all_actors=actors.get_all_level_actors()
    for actor in all_actors:
        if isinstance(actor,unreal.PlayerStart):
            actor.set_actor_rotation(unreal.Rotator(yaw=-45),False)
        elif isinstance(actor,unreal.DirectionalLight) and actor.get_actor_label()!='Luz_Relleno':
            light=actor.light_component
            light.set_editor_property('intensity',5.0)
            light.set_editor_property('light_source_angle',3.0)
            light.set_editor_property('light_color',unreal.Color(255,242,223,255))
            actor.set_actor_rotation(unreal.Rotator(pitch=-55,yaw=-35),False)
        elif isinstance(actor,unreal.SkyLight):
            light=actor.light_component
            light.set_editor_property('source_type',unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
            light.set_editor_property('cubemap',unreal.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))
            light.set_editor_property('intensity',0.6)
            light.set_editor_property('lower_hemisphere_is_black',False)
        elif isinstance(actor,unreal.PostProcessVolume):
            settings=actor.get_editor_property('settings')
            settings.set_editor_property('auto_exposure_bias',0.1)
            settings.set_editor_property('override_color_saturation',True)
            settings.set_editor_property('color_saturation',unreal.Vector4(1.08,1.08,1.08,1.0))
            actor.set_editor_property('settings',settings)
    fill=next((a for a in all_actors if a.get_actor_label()=='Luz_Relleno'),None)
    if fill is None:
        fill=spawn(unreal.DirectionalLight,unreal.Vector(0,0,600),unreal.Rotator(pitch=-40,yaw=140))
        fill.set_actor_label('Luz_Relleno')
    fill.set_actor_rotation(unreal.Rotator(pitch=-40,yaw=140),False)
    fill.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    fill.light_component.set_editor_property('intensity',1.15)
    fill.light_component.set_editor_property('cast_shadows',False)
    fill.light_component.set_editor_property('light_color',unreal.Color(217,235,255,255))
    # A neutral surround provides context at the arena edges in the high view.
    backdrop_material=unreal.load_asset('/Game/FactoryCtyco/Materials/M_Backdrop') if lib.does_asset_exist('/Game/FactoryCtyco/Materials/M_Backdrop') else assets.create_asset('M_Backdrop','/Game/FactoryCtyco/Materials',unreal.Material,unreal.MaterialFactoryNew())
    ml=unreal.MaterialEditingLibrary
    ml.delete_all_material_expressions(backdrop_material)
    color=ml.create_material_expression(backdrop_material,unreal.MaterialExpressionConstant3Vector,-300,0)
    color.set_editor_property('constant',unreal.LinearColor(.065,.085,.11,1))
    ml.connect_material_property(color,'',unreal.MaterialProperty.MP_BASE_COLOR)
    ml.recompile_material(backdrop_material)
    save(backdrop_material)
    if not any(a.get_actor_label()=='Piso_Exterior' for a in all_actors):
        backdrop=spawn(unreal.StaticMeshActor,unreal.Vector(0,0,-55))
        backdrop.set_actor_label('Piso_Exterior')
        backdrop.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
        backdrop.set_actor_scale3d(unreal.Vector(100,100,1))
        backdrop.static_mesh_component.set_material(0,backdrop_material)
        backdrop.static_mesh_component.set_collision_profile_name('NoCollision')
    assert levels.save_current_level()
    lib.save_directory('/Game/FactoryCtyco',False,True)
    report.update(passed=True,mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),
        camera={'pitch':-55,'yaw':-45,'arm_cm':2450,'fov':35,'fixed':True},walk_speed_cm_s=190)
except Exception as exc:
    report['error']=str(exc)
    raise
finally:
    (project/'Docs/isometric_build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('[ARENA_UPGRADE_RESULT] '+json.dumps(report))
