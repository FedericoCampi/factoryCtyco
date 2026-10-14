"""Editor Python (con L_FactoryDemo abierto): baja el horno de fundicion y todo lo que va con el (02/10).

El horno (FactoryRaisedProp: su bloque de cemento se acorta solo), el tubo de descarga y el codo bajan DELTA cm; despues
apply_proceso_fundicion.py rehace lo que depende de esa altura: la pendiente de Cinta_Fabrica_1 (entrega en la boca),
los caños rectos hasta el contenedor y el camino del liquido. El contenedor no se mueve.
Con DELTA = -150 los caños terminan ~2 m arriba del piso, todavia arriba del borde del contenedor (1,68 m).
Informe: Docs/bajar_horno.json (y Docs/proceso_fundicion.json).
"""
import json
from pathlib import Path
import unreal

DELTA = -150.0
project = Path(unreal.Paths.project_dir()).resolve()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False, "delta_cm": DELTA}
try:
    by_label = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    horno = by_label["Horno_Fundicion"]
    elevation = horno.get_editor_property("elevation")
    if elevation + DELTA < 0:
        raise RuntimeError(f"El horno esta a {elevation:.0f} cm: no se puede bajar {-DELTA:.0f}")
    for label in ("Horno_Fundicion", "Tubo_Descarga", "Codo_Metalico"):
        a = by_label[label]
        a.modify()
        before = a.get_actor_location()
        a.set_actor_location(before + unreal.Vector(0, 0, DELTA), False, False)
        report[label] = [round(before.z, 1), round(a.get_actor_location().z, 1)]
    horno.refresh()
    report["elevacion_horno"] = [round(elevation, 1), round(horno.get_editor_property("elevation"), 1)]
    report["passed"] = True
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[BAJAR_HORNO] " + report["error"])
(project / "Docs/bajar_horno.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
if report["passed"]:
    exec(open(project / "Scripts/apply_proceso_fundicion.py", encoding="utf-8").read())
