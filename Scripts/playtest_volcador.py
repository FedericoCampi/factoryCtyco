"""Prueba (08/10), con L_FactoryDemo abierto en el editor: el camion volcador descarga cuarzo en la tolva.

En Play (el tiempo va 4 veces mas rapido):
- Camion_Volcador recorre la linea de los camiones, retrocede por la curva, sube la rampa y estaciona con el eje trasero
  en Cajon_Volcado, arriba de la plataforma;
- abre la persiana, levanta la caja hasta DumpAngle y la carga (48 trozos de cuarzo) cae dentro de la boca de la tolva;
- baja la caja, cierra y sale otra vez a la linea;
- la barrera de la garita se abre sola cuando un camion espera (en el juego la abre el jugador);
- los camiones de cajas siguen yendo a los cajones del muelle (nunca al de volcado);
- (08/10) cada camion lleva al camionero sentado (SK_TecJunior con A_TecJunior_Sit), con la cabeza en la cabina a la
  altura de las ventanillas;
- (08/10) la garita choca: el personaje caminando contra su pared del este no la atraviesa.
Corre en el tick del editor (Python del editor o el puente MCP). Informe: Docs/volcador_play.json.
"""
import json
import math
import time
import traceback
from pathlib import Path
import unreal

docs = Path(unreal.Paths.project_dir()).resolve() / "Docs"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}}
state = {"phase": "start", "t": time.monotonic(), "start": time.monotonic(), "max_tilt": 0.0, "max_door": 0.0,
         "max_pitch": 0.0, "in_hopper": set(), "outside": set(), "box_bays": set(), "samples": 0}


def phase(name):
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = dict(passed=bool(ok), **values)


def trace():
    """Donde esta cada camion (para entender un fallo)."""
    rows = []
    for t in [state.get("truck")] + state.get("box_trucks", []):
        if t:
            rows.append({"camion": t.get_actor_label(), "distancia": round(t.get_distance_along()), "estacionado": t.is_parked(),
                         "maniobra": t.is_maneuvering(), "cajon": t.get_bay().get_actor_label() if t.get_bay() else None,
                         "volcando": t.is_dumping(), "lugar": [round(v) for v in t.vehicle.get_world_location().to_tuple()],
                         "esperando_barrera": bool(t.get_waiting_gate())})
    return rows


def finish():
    if "error" in report:
        report["camiones"] = trace()
    report["passed"] = bool(report["checks"]) and all(c["passed"] for c in report["checks"].values()) and "error" not in report
    (docs / "volcador_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    unreal.log("[VOLCADOR_PLAY] " + json.dumps(report, default=str))
    unreal.unregister_slate_post_tick_callback(state["handle"])
    if unreal.EditorLevelLibrary.get_pie_worlds(False):
        if "world" in state:
            unreal.SystemLibrary.execute_console_command(state["world"], "slomo 1")
        levels.editor_request_end_play()


def labelled(world, cls, name):
    return next((a for a in unreal.GameplayStatics.get_all_actors_of_class(world, cls) if a.get_actor_label() == name), None)


def sample():
    """Mira la caja, la persiana y donde estan los trozos que caen."""
    truck = state["truck"]
    state["max_tilt"] = max(state["max_tilt"], truck.get_dump_tilt())
    state["max_door"] = max(state["max_door"], truck.get_door_openness())
    state["max_pitch"] = max(state["max_pitch"], abs(truck.vehicle.get_world_rotation().pitch))
    if truck.is_dumping() or truck.is_parked():
        landed = truck.get_load_landings()
        if len(landed) >= len(state.get("landings") or []):
            state["landings"] = list(landed)
    if not truck.is_dumping():
        return
    load = truck.get_editor_property("load")
    lo, hi, rim = state["mouth"]
    for i in range(load.get_instance_count()):
        t = load.get_instance_transform(i, True)
        p, s = t.translation, t.scale3d.x
        if s <= 0.01:
            continue
        # cayendo: por debajo del borde de la caja
        if p.z < rim - 5:
            inside = lo.x < p.x < hi.x and lo.y < p.y < hi.y
            (state["in_hopper"] if inside else state["outside"]).add(i)
    state["samples"] += 1


def tick(delta):
    try:
        age = time.monotonic() - state["t"]
        if time.monotonic() - state["start"] > 150:
            raise RuntimeError("La prueba tardo demasiado (fase %s)" % state["phase"])
        name = state["phase"]
        if name == "start":
            levels.editor_request_begin_play()
            phase("spawn")
        elif name == "spawn" and age > 4:
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            if not worlds:
                return
            world = worlds[0]
            truck = labelled(world, unreal.FactoryVehiclePath, "Camion_Volcador")
            bay = labelled(world, unreal.FactoryTruckBay, "Cajon_Volcado")
            hoppers = labelled(world, unreal.StaticMeshActor, "Tolvas_Gemelas")
            xf = hoppers.get_actor_transform()
            # boca de la tolva del este: x 0..300 y +-136 del actor, a 360 de su base
            a, b = xf.transform_location(unreal.Vector(0, -136, 360)), xf.transform_location(unreal.Vector(300, 136, 360))
            state["mouth"] = (unreal.Vector(min(a.x, b.x), min(a.y, b.y), 0), unreal.Vector(max(a.x, b.x), max(a.y, b.y), 0), a.z)
            state.update(world=world, truck=truck, bay=bay,
                         box_trucks=[labelled(world, unreal.FactoryVehiclePath, n) for n in ("Camion_Recorrido",)])
            check("cargado", truck.get_load_in_cargo() == truck.get_editor_property("load_pieces") > 0,
                  trozos=truck.get_load_in_cargo())
            rows = []
            for t in [truck] + state["box_trucks"]:
                d = t.get_editor_property("driver")
                head = t.vehicle.get_world_transform().inverse_transform_location(d.get_socket_location("head"))
                rows.append({"camion": t.get_actor_label(), "malla": d.get_skeletal_mesh_asset().get_name() if d.get_skeletal_mesh_asset() else None,
                             "animando": d.is_playing(), "cabeza_cm": [round(v) for v in head.to_tuple()]})
            # cabeza: detras del parabrisas (x 300..370), del lado izquierdo, entre el borde de la ventanilla y el techo
            check("camionero_sentado", all(r["malla"] == "SK_TecJunior" and r["animando"] and 300 < r["cabeza_cm"][0] < 370
                                           and -70 < r["cabeza_cm"][1] < -20 and 140 < r["cabeza_cm"][2] < 175 for r in rows),
                  camiones=rows)
            # garita: el personaje parado al este de la cabina camina hacia el oeste, contra la pared
            gate = labelled(world, unreal.FactoryGateBarrier, "Cabina_Barrera")
            o, e, _ = unreal.SystemLibrary.get_component_bounds(gate.get_editor_property("booth"))
            pawn = unreal.GameplayStatics.get_player_character(world, 0)
            half = pawn.capsule_component.get_scaled_capsule_half_height()
            pawn.set_actor_location(unreal.Vector(o.x + e.x + 80, o.y, gate.get_actor_location().z + half + 5), False, True)
            state.update(pawn=pawn, booth=(o, e))
            unreal.SystemLibrary.execute_console_command(world, "slomo 4")
            phase("drive")
        elif name == "drive":
            truck = state["truck"]
            sample()
            if "garita" not in report["checks"]:
                pawn, (o, e) = state["pawn"], state["booth"]
                pawn.add_movement_input(unreal.Vector(-1, 0, 0), 1.0, True)
                if age > 2.0:   # ~8 s de juego caminando contra la pared
                    x = pawn.get_actor_location().x
                    check("garita", x > o.x + e.x - 5, personaje_x=round(x), pared_este_x=round(o.x + e.x))
            # la barrera de la garita la abre el jugador: aca, cuando un camion espera en ella
            for t in [truck] + state["box_trucks"]:
                gate = t.get_waiting_gate() if t else None
                if gate and isinstance(gate, unreal.FactoryGateBarrier):
                    gate.set_open(True)
            for t in state["box_trucks"]:
                if t and t.get_bay():
                    state["box_bays"].add(t.get_bay().get_actor_label())
            if truck.is_parked() and truck.is_dumping():
                a, b = truck.vehicle.get_world_location(), state["bay"].get_actor_location()
                check("estaciona_en_la_plataforma", truck.get_bay() == state["bay"]
                      and math.hypot(a.x - b.x, a.y - b.y) < 30 and abs(a.z - b.z) < 10,
                      eje_trasero=[round(v) for v in a.to_tuple()], cajon=[round(v) for v in b.to_tuple()],
                      inclinacion_max_en_rampa=round(state["max_pitch"], 1), segundos_reales=round(age, 1))
                phase("dump")
        elif name == "dump":
            truck = state["truck"]
            sample()
            if not truck.is_parked() and truck.get_bay() is None or age > 60:
                total = truck.get_editor_property("load_pieces")
                check("levanta_la_caja", state["max_tilt"] >= 0.999 and state["max_door"] >= 0.999,
                      caja_max=round(state["max_tilt"], 3), persiana_max=round(state["max_door"], 3),
                      angulo=truck.get_editor_property("dump_angle"))
                # donde termino cada trozo (LoadFall bajo el borde de la caja): adentro de la boca, mas abajo que ella
                lo, hi, rim = state["mouth"]
                ends = state.get("landings") or []
                inside = [p for p in ends if lo.x < p.x < hi.x and lo.y < p.y < hi.y and p.z < rim]
                check("cuarzo_en_la_tolva", len(ends) == total and len(inside) == total,
                      trozos=total, cayeron=len(ends), dentro_de_la_boca=len(inside),
                      afuera=[[round(v) for v in p.to_tuple()] for p in ends if p not in inside][:5],
                      boca=[round(lo.x), round(hi.x), round(lo.y), round(hi.y), round(rim)], muestras=state["samples"])
                phase("leave")
        elif name == "leave":
            truck = state["truck"]
            if age > 3:
                check("sale_a_la_linea", not truck.is_parked() and truck.get_dump_tilt() == 0 and truck.get_door_openness() == 0,
                      distancia_en_linea=round(truck.get_distance_along()))
                check("camiones_de_cajas_no_usan_el_volcado", "Cajon_Volcado" not in state["box_bays"],
                      cajones=sorted(state["box_bays"]))
                finish()
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error("[VOLCADOR_PLAY] " + report["error"])
        finish()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
