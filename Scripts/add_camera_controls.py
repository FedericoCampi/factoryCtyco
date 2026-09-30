"""Attach the compiled mouse-camera component to the existing robot Blueprint."""
import json
from pathlib import Path
import unreal

project=Path(unreal.Paths.project_dir()).resolve()
report={'passed':False}
try:
    bp=unreal.load_asset('/Game/FactoryCtyco/Blueprints/BP_Robot1')
    subsystem=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    funcs=unreal.SubobjectDataBlueprintFunctionLibrary
    handles=subsystem.k2_gather_subobject_data_for_blueprint(bp)
    camera=None
    for handle in handles:
        data=subsystem.k2_find_subobject_data_from_handle(handle)
        obj=funcs.get_object_for_blueprint(data,bp)
        if isinstance(obj,unreal.FactoryCameraComponent): camera=obj
    if camera is None:
        handle,failure=subsystem.add_new_subobject(unreal.AddNewSubobjectParams(
            parent_handle=handles[0],new_class=unreal.FactoryCameraComponent,blueprint_context=bp))
        if str(failure): raise RuntimeError(str(failure))
        subsystem.rename_subobject(handle,'FactoryCameraControls')
        camera=funcs.get_object_for_blueprint(subsystem.k2_find_subobject_data_from_handle(handle),bp)
    camera.set_editor_property('auto_activate',True)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
    report.update(passed=True,component=camera.get_name(),controls={
        'zoom':'Mouse wheel','pan':'Middle mouse drag','reset':'Home',
        'move':'WASD','jump':'Space'},zoom_cm=[1100,3800],maximum_pan_cm=1250)
finally:
    (project/'Docs/camera_build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('[CAMERA_BUILD] '+json.dumps(report))
