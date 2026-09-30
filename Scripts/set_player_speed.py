"""Editor Python: suma DELTA cm/s a la velocidad de caminar y a la de Shift de TecJunior (28/09).

BP_FactoryRobot, componente RobotLocomotion: WalkSpeed y FastWalkSpeed. Lee los valores actuales del
Blueprint (no los de un informe) y guarda. Con -unattended cierra al terminar. Informe: Docs/player_speed.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
PAWN = "/Game/FactoryCtyco/Factory/BP_FactoryRobot"
DELTA = 100.0
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
report = {"passed": False}
try:
    bp = unreal.load_asset(PAWN)
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    funcs = unreal.SubobjectDataBlueprintFunctionLibrary
    locomotion = None
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        obj = funcs.get_object_for_blueprint(subsystem.k2_find_subobject_data_from_handle(handle), bp)
        if isinstance(obj, unreal.RobotLocomotionComponent):
            locomotion = obj
    if not locomotion:
        raise RuntimeError("BP_FactoryRobot no tiene RobotLocomotion")
    before = {k: locomotion.get_editor_property(k) for k in ("walk_speed", "fast_walk_speed", "authored_walk_speed")}
    bp.modify()
    locomotion.modify()
    locomotion.set_editor_property("walk_speed", before["walk_speed"] + DELTA)
    locomotion.set_editor_property("fast_walk_speed", before["fast_walk_speed"] + DELTA)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    if not unreal.EditorAssetLibrary.save_loaded_asset(bp, False):
        raise RuntimeError("No se pudo guardar BP_FactoryRobot")
    after = {k: locomotion.get_editor_property(k) for k in ("walk_speed", "fast_walk_speed")}
    report.update(passed=True, before=before, after=after)
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[PLAYER_SPEED] {error}")
finally:
    (project / "Docs/player_speed.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
