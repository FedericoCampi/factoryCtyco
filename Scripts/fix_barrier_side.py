"""Editor Python: pasa el poste de la barrera al lado del carril de la garita movida (28/09).

La garita (Cabina_Barrera) quedo al sur del carril (y 800 en cm del estacionamiento): el poste pasa a su lado
norte (relativo -40, -130) y el brazo apunta hacia el carril (-Y), asi lo cruza entero. Con -unattended abre
el mapa, guarda y cierra. Informe: Docs/barrier_side.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
report = {"passed": False}
try:
    if HEADLESS and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo"):
        raise RuntimeError("No se pudo abrir el mapa")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    gate = next(a for a in actors.get_all_level_actors() if isinstance(a, unreal.FactoryGateBarrier))
    gate.modify()
    post = gate.get_editor_property("post")
    post.modify()
    post.set_relative_location_and_rotation(unreal.Vector(-40, -130, 0), unreal.Rotator(0, 0, -90), False, False)
    park = next(a for a in actors.get_all_level_actors() if a.get_actor_label() == "Parking_Estacionamiento")
    arm = gate.get_editor_property("arm")
    tip = arm.get_world_transform().transform_location(unreal.Vector(gate.get_editor_property("arm_length"), 0, 0))
    local = lambda v: park.get_actor_transform().inverse_transform_location(v)
    p, t = local(post.get_world_location()), local(tip)
    if HEADLESS and not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, post=[round(p.x), round(p.y)], tip=[round(t.x), round(t.y)])
except Exception as error:
    report["error"] = str(error)
finally:
    (project / "Docs/barrier_side.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
