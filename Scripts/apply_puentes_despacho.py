"""Editor Python (con L_FactoryDemo abierto): el circuito del despacho sin cortes (03/10).

Las cintas de cajas de las maquinas de despacho (Despacho_Cajas, Despacho_Cajas2) terminaban en su tope y las cintas
de carga al camion empezaban ~3 m mas alla, con la rejilla del piso en el medio: el circuito se veia cortado. Se unen
con tramos de cinta de carga (copias de las que ya estan, mismo aspecto y altura):
- Cinta_Puente2: de la punta de Despacho_Cajas2 a la entrada de Cinta_Carga2 (recta).
- Cinta_Puente1 (recta) + Cinta_Puente1_Curva (cuarto de vuelta): de la punta de Despacho_Cajas a la entrada de
  Cinta_Carga3, que va hacia +Y.
Una caja que se deje en un puente sigue sola a la cinta de carga (se enlazan solas por cercania). Las cajas de las
cintas de despacho todavia no pasan solas al puente: se agarran con E como siempre. Se rehacen cada vez.
Informe: Docs/puentes_despacho.json.
"""
import json
import math
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False}


def rnd(v):
    return [round(v.x), round(v.y), round(v.z)]


def end_of(dispatch):
    return dispatch.get_actor_transform().transform_location(dispatch.get_editor_property("end"))


def straight(template, label, a, b):
    belt = actors.duplicate_actor(template)
    belt.set_actor_label(label)
    belt.set_editor_property("turn_degrees", 0.0)
    belt.set_actor_scale3d(unreal.Vector(1, 1, 1))
    belt.set_actor_rotation(unreal.Rotator(0, 0, math.degrees(math.atan2(b.y - a.y, b.x - a.x))), False)
    belt.set_actor_location(unreal.Vector(a.x, a.y, template.get_actor_location().z), False, False)
    belt.set_editor_property("length", max(50.0, math.hypot(b.x - a.x, b.y - a.y)))
    belt.set_editor_property("next_belt", None)
    belt.rerun_construction_scripts() if hasattr(belt, "rerun_construction_scripts") else None
    belt.build_supports()
    return belt


try:
    by = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    for old in [a for a in by.values() if a.get_actor_label().startswith("Cinta_Puente")]:
        actors.destroy_actor(old)
    straight_t, corner_t = by["Cinta_Carga2"], by["Cinta_Esquina"]
    made = []
    # 2: recta de la punta de la cinta de cajas a Cinta_Carga2
    a2, b2 = end_of(by["Despacho_Cajas2"]), by["Cinta_Carga2"].world_at(0)
    made.append(straight(straight_t, "Cinta_Puente2", a2, b2))
    # 1: recta hacia +X y un cuarto de vuelta que termina en Cinta_Carga3 (que va hacia +Y)
    a1, b1 = end_of(by["Despacho_Cajas"]), by["Cinta_Carga3"].world_at(0)
    radius = abs(b1.y - a1.y)
    turn_at = unreal.Vector(b1.x - radius, a1.y, a1.z)
    made.append(straight(straight_t, "Cinta_Puente1", a1, turn_at))
    curve = actors.duplicate_actor(corner_t)
    curve.set_actor_label("Cinta_Puente1_Curva")
    # el modelo de la esquina gira para un solo lado (como Cinta_Esquina, -90): para el otro se espeja (escala Y -1), y se
    # agranda parejo en X e Y hasta el radio que hace falta (el largo de su linea central queda el de la plantilla)
    template_radius = corner_t.get_editor_property("length") / (math.radians(abs(corner_t.get_editor_property("turn_degrees"))))
    k = radius / template_radius
    turn_left = b1.y > a1.y        # va de +X hacia +Y: a la izquierda
    curve.set_editor_property("turn_degrees", corner_t.get_editor_property("turn_degrees"))
    curve.set_editor_property("length", corner_t.get_editor_property("length"))
    mirror = -1.0 if (corner_t.get_editor_property("turn_degrees") < 0) == turn_left else 1.0
    curve.set_actor_scale3d(unreal.Vector(k, k * mirror, 1))
    curve.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
    curve.set_actor_location(unreal.Vector(turn_at.x, turn_at.y, corner_t.get_actor_location().z), False, False)
    curve.set_editor_property("next_belt", None)
    curve.build_supports()
    made.append(curve)
    for belt in made:
        belt.set_folder_path(str(straight_t.get_folder_path()))
        belt.refresh_links() if hasattr(belt, "refresh_links") else None
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    targets = {"Cinta_Puente2": b2, "Cinta_Puente1": curve.world_at(0), "Cinta_Puente1_Curva": b1}
    rows = []
    for belt in made:
        end = belt.get_delivery_point()
        gap = math.hypot(end.x - targets[belt.get_actor_label()].x, end.y - targets[belt.get_actor_label()].y)
        rows.append({"cinta": belt.get_actor_label(), "desde": rnd(belt.world_at(0)), "hasta": rnd(end), "falta_cm": round(gap, 1)})
    report.update(puentes=rows, desde_despacho={"Despacho_Cajas": rnd(a1), "Despacho_Cajas2": rnd(a2)})
    report["passed"] = all(r["falta_cm"] < 20 for r in rows)
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[PUENTES_DESPACHO] " + report["error"])
(project / "Docs/puentes_despacho.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
