"""Editor Python (con L_FactoryDemo abierto, sin Play): la primera curva del cuarzo, al derecho (03/10).

1. Cinta_Fabrica_Esquina2 (primera curva de la linea del cuarzo) quedo con el sentido al reves: su entrada estaba
   en la punta de Cinta_Cuarzo_Triturar (a donde tenia que entregar) y su salida en la de Cinta_Cuarzo_Triturar3 (de
   donde tenia que recibir), asi que la piedra se quedaba al final de Triturar3. Se recorre la misma curva al reves:
   girada 90 grados y espejada (escala Y negativa), con la entrada donde estaba la salida. Queda en el mismo lugar.
(Hasta el 03/10 tambien desbloqueaba Cinta_Puente1 y su curva: estaba mal, son la mejora del camion 2 y siguen
   bloqueadas.)
Informe: Docs/fix_cintas_curva_y_puente.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}


def rnd(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


try:
    by = {a.get_actor_label(): a for a in actors.get_all_level_actors()}

    # 1. la curva del cuarzo, al reves
    corner, feed, take = by["Cinta_Fabrica_Esquina2"], by["Cinta_Cuarzo_Triturar3"], by["Cinta_Cuarzo_Triturar"]
    before = {"entrada": rnd(corner.input_point()), "salida": rnd(corner.output_point())}
    if corner.input_point().distance(feed.output_point()) > 50:
        old_in, old_out = corner.input_point(), corner.output_point()
        rot = corner.get_actor_rotation()
        scale = corner.get_actor_scale3d()
        corner.modify()
        # mismo arco recorrido al reves: la entrada nueva es la salida vieja, mirando para el otro lado
        corner.set_actor_scale3d(unreal.Vector(scale.x, -scale.y, scale.z))
        corner.set_actor_rotation(unreal.Rotator(rot.roll, rot.pitch, rot.yaw + 90.0), False)
        shift = old_out - corner.input_point()
        corner.set_actor_location(corner.get_actor_location() + unreal.Vector(shift.x, shift.y, 0), False, False)
        report["curva_salida_vs_antes_cm"] = round(corner.output_point().distance(old_in), 1)
    report["curva"] = {"antes": before, "entrada": rnd(corner.input_point()), "salida": rnd(corner.output_point()),
                       "desde_Triturar3_cm": round(corner.input_point().distance(feed.output_point()), 1),
                       "hasta_Triturar_cm": round(corner.output_point().distance(take.input_point()), 1)}

    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    c = report["curva"]
    report["passed"] = c["desde_Triturar3_cm"] < 50 and c["hasta_Triturar_cm"] < 50
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[FIX_CINTAS] " + report["error"])
(project / "Docs/fix_cintas_curva_y_puente.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
