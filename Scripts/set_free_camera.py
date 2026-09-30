"""Editor Python: camara libre por defecto para TecJunior (28/09).

BP_FactoryRobot, componente FactoryCamera: bStartFree = true (la camara no sigue al personaje hasta que se hace clic en
un personaje; Inicio vuelve a seguirlo). Con -unattended cierra al terminar. Informe: Docs/free_camera.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
PAWN = "/Game/FactoryCtyco/Factory/BP_FactoryRobot"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
report = {"passed": False}
try:
    bp = unreal.load_asset(PAWN)
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    funcs = unreal.SubobjectDataBlueprintFunctionLibrary
    camera = None
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        obj = funcs.get_object_for_blueprint(subsystem.k2_find_subobject_data_from_handle(handle), bp)
        if isinstance(obj, unreal.FactoryCameraComponent):
            camera = obj
    if not camera:
        raise RuntimeError("BP_FactoryRobot no tiene FactoryCamera")
    bp.modify()
    camera.modify()
    camera.set_editor_property("start_free", True)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    if not unreal.EditorAssetLibrary.save_loaded_asset(bp, False):
        raise RuntimeError("No se pudo guardar BP_FactoryRobot")
    report.update(passed=True, start_free=camera.get_editor_property("start_free"))
except Exception as error:
    report["error"] = str(error)
finally:
    (project / "Docs/free_camera.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
