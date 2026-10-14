"""Editor Python (con L_FactoryDemo abierto): la cinta donde se cargan los lingotes a mano va hacia la linea (03/10).

El usuario armo Cinta_Cuarzo_Triturar3 (junto a la pared este, a lo largo de Y) y Cinta_Fabrica_Esquina2 (que la une con
Cinta_Cuarzo_Triturar), pero las dos quedaron al reves: lo que se cargaba se iba hacia el sur, lejos de la esquina.
- Cinta_Cuarzo_Triturar3 se da vuelta en su lugar (entra por donde salia).
- La esquina va de la salida de esa cinta a la entrada de Cinta_Cuarzo_Triturar (de las 4 orientaciones y las 2 manos,
  la que une los dos puntos), a la altura de las cintas.
- Cinta_Cuarzo_Triturar2 estaba duplicada exactamente encima de Cinta_Cuarzo_Triturar: se borra.
- Cinta_Fabrica_Esquina (la que va al horno) se volvio a unir de Cinta_Fabrica_2 a Cinta_Fabrica_1, y cada pieza tiene su
  propio PersistentId (las duplicadas con Ctrl+D lo repetian; F5 no guarda con ids repetidos).
Informe: Docs/cinta_lingotes.json.
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


def fit_straight(belt, a, b):
    d = b - a
    flat = math.hypot(d.x, d.y)
    slope = math.degrees(math.atan2(d.z, flat))
    belt.modify()
    belt.set_editor_property("slope", slope)
    s = belt.get_actor_scale3d()
    belt.set_actor_scale3d(unreal.Vector(math.hypot(flat, d.z) / 200.0, s.y, 1.0))
    belt.set_actor_rotation(unreal.Rotator(0, slope, math.degrees(math.atan2(d.y, d.x))), False)
    belt.set_actor_location(belt.get_actor_location() + a - belt.input_point(), False, False)
    belt.refresh_visuals()
    belt.build_supports()


def fit_corner(belt, a, b):
    s = belt.get_actor_scale3d()
    belt.modify()
    best = None
    for yaw in (0, 90, 180, -90):
        for hand in (1, -1):
            belt.set_actor_scale3d(unreal.Vector(s.x, abs(s.y) * hand, s.z))
            belt.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
            belt.set_actor_location(belt.get_actor_location() + a - belt.input_point(), False, False)
            gap = (belt.output_point() - b).length()
            if best is None or gap < best[0]:
                best = (gap, yaw, hand)
    gap, yaw, hand = best
    belt.set_actor_scale3d(unreal.Vector(s.x, abs(s.y) * hand, s.z))
    belt.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
    belt.set_actor_location(belt.get_actor_location() + a - belt.input_point(), False, False)
    belt.refresh_visuals()
    belt.build_supports()
    return gap


def receiver_of(belt, others):
    out = belt.output_point()
    for o in others:
        i = o.input_point()
        if o != belt and math.hypot(out.x - i.x, out.y - i.y) <= 50 and abs(out.z - i.z) <= 60:
            return o.get_actor_label()
    return None


try:
    by = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    short, corner, main = by["Cinta_Cuarzo_Triturar3"], by["Cinta_Fabrica_Esquina2"], by["Cinta_Cuarzo_Triturar"]
    dup = by.get("Cinta_Cuarzo_Triturar2")
    if dup and (dup.input_point() - main.input_point()).length() < 5 and (dup.output_point() - main.output_point()).length() < 5:
        actors.destroy_actor(dup)
        report["borrada"] = "Cinta_Cuarzo_Triturar2 (duplicada encima de Cinta_Cuarzo_Triturar)"
    # la esquina que va al horno: de la salida de Cinta_Fabrica_2 a la entrada de Cinta_Fabrica_1 (el usuario la dio vuelta)
    c2, c1, corner1 = by["Cinta_Fabrica_2"], by["Cinta_Fabrica_1"], by["Cinta_Fabrica_Esquina"]
    report["esquina_horno_gap_cm"] = round(fit_corner(corner1, c2.output_point(), c1.input_point()), 1)
    # identificadores repetidos (cintas duplicadas con Ctrl+D): cada una el suyo, su nombre
    seen = set()
    for b in [a for a in actors.get_all_level_actors() if isinstance(a, unreal.FactoryBuilding)]:
        pid = str(b.get_editor_property("persistent_id"))
        if not pid or pid == "None" or pid in seen:
            b.set_editor_property("persistent_id", b.get_actor_label())
            report.setdefault("ids_corregidos", []).append(b.get_actor_label())
        seen.add(str(b.get_editor_property("persistent_id")))
    target = main.input_point()
    # la corta: entra por donde salia; queda apuntando a la esquina (la punta mas cerca de la cinta larga es la salida)
    a, b = short.input_point(), short.output_point()
    if (a - target).length() < (b - target).length():
        a, b = b, a
    fit_straight(short, unreal.Vector(a.x, a.y, target.z), unreal.Vector(b.x, b.y, target.z))
    gap = fit_corner(corner, short.output_point(), target)
    chain = [short, corner, main] + [by[n] for n in ("Plataforma_Elevadora_1", "Trituradora_Cuarzo", "Cinta_Fabrica_2",
                                                       "Cinta_Fabrica_Esquina", "Cinta_Fabrica_1") if n in by]
    report.update(corta={"in": rnd(short.input_point()), "out": rnd(short.output_point())},
                  esquina={"in": rnd(corner.input_point()), "out": rnd(corner.output_point()), "gap_cm": round(gap, 1)},
                  chain=[{"from": c.get_actor_label(), "to": receiver_of(c, chain)} for c in chain])
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = all(c["to"] for c in report["chain"][:-1])
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[CINTA_LINGOTES] " + report["error"])
(project / "Docs/cinta_lingotes.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
