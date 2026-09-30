"""Editor Python (con L_FactoryDemo abierto): hunde la jaula de los ascensores y ajusta el viaje.

El travesano inferior de SM_AscensorEstructura va de 17 a 57 cm y el personaje lo atravesaba al
entrar. Se baja la estructura (Crown) 57 cm para que quede al ras del piso y se entre por cualquier
lado. Toda la cabina (piso y jaula) sube 2 m con el personaje. Idempotente; guarda el nivel.
Informe: Docs/elevator_sink.json.
"""
import json
from pathlib import Path
import unreal

SINK_CM, TRAVEL_DEPTH, TRAVEL_SECONDS = 57.0, -200.0, 2.2
project = Path(unreal.Paths.project_dir()).resolve()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}
try:
    done = []
    for e in [a for a in actors.get_all_level_actors() if a.get_class().get_name() == "FactoryElevator"]:
        crown = next(c for c in e.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == "Crown")
        crown.set_relative_location(unreal.Vector(0, 0, -SINK_CM), False, False)
        e.set_editor_property("travel_depth", TRAVEL_DEPTH)
        e.set_editor_property("travel_seconds", TRAVEL_SECONDS)
        done.append([e.get_actor_label(), crown.get_editor_property("relative_location").z,
                     e.get_editor_property("travel_depth")])
    if len(done) != 2:
        raise RuntimeError(f"Se esperaban 2 ascensores: {done}")
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, elevators=done)
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[ELEVATOR_SINK] {error}")
(project / "Docs/elevator_sink.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
