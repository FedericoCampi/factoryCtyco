"""Editor Python (07/10): la fabrica quedaba muy iluminada. Baja sus lamparas de techo (Techo_Fabrica_Luz_* y
Techo_Fabrica_Relleno_*) al factor `light` de "Fabrica" en apply_techos.py, sin rehacer los techos. Se puede correr de
nuevo (pone el valor, no lo multiplica). Con el editor abierto. Guarda el nivel. Informe: Docs/luz_fabrica.json
(con las intensidades de antes, para volver atras).
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
LIGHT = 0.5               # el mismo factor que BUILDINGS["Fabrica"]["light"] en apply_techos.py
HEIGHT = 800.0            # techo de la fabrica sobre su piso
LAMP = 90.0 * (HEIGHT / 370.0) ** 2 * LIGHT     # LAMP_INTENSITY y FILL_INTENSITY de apply_techos.py
FILL = 12.0 * (HEIGHT / 370.0) ** 2 * LIGHT
report = {"passed": False}

try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    before, n = {}, {"focos": 0, "rellenos": 0}
    for a in actors.get_all_level_actors():
        label = a.get_actor_label()
        if label.startswith("Techo_Fabrica_Luz_"):
            comp, value, key = a.get_component_by_class(unreal.SpotLightComponent), LAMP, "focos"
        elif label.startswith("Techo_Fabrica_Relleno_"):
            comp, value, key = a.get_component_by_class(unreal.PointLightComponent), FILL, "rellenos"
        else:
            continue
        before.setdefault(key, round(comp.get_editor_property("intensity"), 1))
        a.modify()
        comp.set_editor_property("intensity", value)
        n[key] += 1
    if not n["focos"]:
        raise RuntimeError("No hay lamparas Techo_Fabrica_Luz_* (correr apply_techos.py)")
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report.update(passed=True, cantidad=n, antes=before, ahora={"focos": round(LAMP, 1), "rellenos": round(FILL, 1)})
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[LUZ_FABRICA] " + report["error"])
finally:
    (project / "Docs/luz_fabrica.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
