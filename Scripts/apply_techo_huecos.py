"""Editor Python (07/10): cierra las ranuras que dejaban los dinteles de la pared alta de la fabrica.

apply_techos.py deja libres hasta DOOR_CLEAR (2,60 m) los lugares sin pared (pasos) y arriba del ascensor desde lo que
mide (4,14 m): ahi se veia afuera. Desde el 07/10 el vano norte esta cerrado (author_arena_edit.py, muro de ~2,3 m) y
arriba del ascensor de la fabrica no debe haber hueco. Cada dintel Techo_Fabrica_*_hueco_* baja hasta BOTTOM (el muro de
la arena), y los que estan sobre el ascensor hasta su techo (LIFT_TOP). Correr despues de apply_techos.py (que los
rehace). Guarda el nivel. Informe: Docs/techo_huecos.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
BOTTOM = 215.0        # cm: un poco abajo del borde de arriba del muro de la arena (2,21-2,33 m)
LIFT_TOP = 222.0      # cm: techo de la estructura de la cabina de Ascensor_Fabrica (medido con rayos)
report = {"passed": False, "dinteles": {}}

try:
    acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    lift = next(a for a in acts if a.get_actor_label() == "Ascensor_Fabrica")
    lo_o, lo_e = lift.get_actor_bounds(False)
    for a in acts:
        label = a.get_actor_label()
        if not (label.startswith("Techo_Fabrica_") and "_hueco_" in label):
            continue
        o, e = a.get_actor_bounds(False)
        over_lift = (abs(o.x - lo_o.x) < e.x + lo_e.x and abs(o.y - lo_o.y) < e.y + lo_e.y)
        bottom, top = (LIFT_TOP if over_lift else BOTTOM), o.z + e.z
        old = o.z - e.z
        if abs(old - bottom) < 1:
            report["dinteles"][label] = [round(old), round(top)]
            continue
        scale = a.get_actor_scale3d()
        a.modify()
        a.set_actor_scale3d(unreal.Vector(scale.x, scale.y, scale.z * (top - bottom) / (top - old)))
        loc = a.get_actor_location()
        a.set_actor_location(unreal.Vector(loc.x, loc.y, (top + bottom) / 2), False, False)
        o, e = a.get_actor_bounds(False)
        report["dinteles"][label] = [round(o.z - e.z), round(o.z + e.z), "sobre el ascensor" if over_lift else "muro"]
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = all(abs(v[0] - (LIFT_TOP if len(v) > 2 and v[2] == "sobre el ascensor" else BOTTOM)) < 2 or len(v) == 2
                           for v in report["dinteles"].values())
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[TECHO_HUECOS] " + report["error"])
finally:
    (project / "Docs/techo_huecos.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
