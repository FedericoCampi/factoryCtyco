"""Disable jumping and configure walk / held-Shift fast walking."""
import json
from pathlib import Path
import unreal

project=Path(unreal.Paths.project_dir()).resolve()
report={'passed':False}
try:
    bp=unreal.load_asset('/Game/FactoryCtyco/Blueprints/BP_Robot1')
    bp.modify()
    subsystem=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    funcs=unreal.SubobjectDataBlueprintFunctionLibrary
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        obj=funcs.get_object_for_blueprint(subsystem.k2_find_subobject_data_from_handle(handle),bp)
        if isinstance(obj,unreal.RobotLocomotionComponent):
            obj.modify()
            obj.set_editor_property('walk_speed',190.0)
            obj.set_editor_property('fast_walk_speed',300.0)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=unreal.get_default_object(bp.generated_class())
    cdo.modify()
    cdo.set_editor_property('jump_max_count',0)
    cdo.character_movement.set_editor_property('jump_z_velocity',0.0)
    cdo.character_movement.set_editor_property('max_walk_speed',190.0)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
    removed=[]
    for path in unreal.EditorAssetLibrary.list_assets('/Game/Input',True,False):
        context=unreal.load_asset(path)
        if not isinstance(context,unreal.InputMappingContext): continue
        for mapping in list(context.get_editor_property('mappings')):
            if mapping.action and 'Jump' in mapping.action.get_name():
                context.unmap_all_keys_from_action(mapping.action)
                removed.append(context.get_name())
        assert unreal.EditorAssetLibrary.save_loaded_asset(context,False)
    report.update(passed=True,jump_enabled=False,walk_speed_cm_s=190,
        fast_walk_speed_cm_s=300,fast_walk_keys=['LeftShift','RightShift'],
        jump_mappings_removed_from=sorted(set(removed)))
finally:
    (project/'Docs/factory_controls_build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('[FACTORY_CONTROLS_BUILD] '+json.dumps(report))
