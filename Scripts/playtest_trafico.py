"""Prueba (08/10), con L_FactoryDemo abierto en el editor: los camiones no se atraviesan, la barrera choca.

En el editor: la linea de Camion_Recorrido queda sobre el piso en todo su largo (se ve en el viewport).
En Play (4 veces mas rapido, con el camion 2 desbloqueado: tres camiones en la misma linea; la barrera de la garita se
levanta cuando un camion espera, como haria el jugador o el encargado):
- nunca hay dos camiones encimados (rectangulos reales: 1,05 m detras del eje trasero, 4,2 m delante, 2,1 m de ancho),
  salvo los que esperan juntos en el comienzo de la linea;
- el brazo de la barrera nunca esta bajo (ni bajando) con un camion debajo;
- las ruedas no se hunden en el piso (el eje trasero no queda mas de 5 cm debajo del piso que tiene debajo);
- el personaje no atraviesa el brazo bajo ni un camion estacionado;
- (08/10) movimiento suave: ni la linea ni los camiones tienen escalones (pendiente de mas de 30 % entre dos muestras),
  tampoco en las rampas de calle de las puertas del patio.
Informe: Docs/trafico_play.json.
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
state = {"phase": "line", "t": time.monotonic(), "start": time.monotonic(), "overlaps": [], "arm_hits": [], "ground": [],
         "blocked": {}, "backoffs": 0, "samples": 0, "dumped": False, "prev": {}, "jumps": []}
REAR, FRONT, HALF = 105.0, 420.0, 105.0


def phase(name):
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = dict(passed=bool(ok), **values)


def finish():
    report["passed"] = bool(report["checks"]) and all(c["passed"] for c in report["checks"].values()) and "error" not in report
    (docs / "trafico_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    unreal.log("[TRAFICO_PLAY] " + json.dumps(report, default=str))
    unreal.unregister_slate_post_tick_callback(state["handle"])
    if unreal.EditorLevelLibrary.get_pie_worlds(False):
        if "world" in state:
            unreal.SystemLibrary.execute_console_command(state["world"], "slomo 1")
        levels.editor_request_end_play()


def labelled(world, cls, name):
    return next((a for a in unreal.GameplayStatics.get_all_actors_of_class(world, cls) if a.get_actor_label() == name), None)


def floor_z(world, p, ignore):
    hit = unreal.SystemLibrary.line_trace_single_for_objects(world, unreal.Vector(p.x, p.y, p.z + 80), unreal.Vector(p.x, p.y, p.z - 150),
                                                             [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1], True, ignore,
                                                             unreal.DrawDebugTrace.NONE, True)
    return hit.to_tuple()[4].z if hit else None


def rect(truck):
    """Centro, eje y medidas del camion (en el plano)."""
    v = truck.vehicle
    p, yaw = v.get_world_location(), math.radians(v.get_world_rotation().yaw)
    x = (math.cos(yaw), math.sin(yaw))
    c = (p.x + x[0] * (FRONT - REAR) / 2, p.y + x[1] * (FRONT - REAR) / 2)
    return c, x, (FRONT + REAR) / 2, HALF


def overlap(a, b):
    (ca, xa, la, wa), (cb, xb, lb, wb) = a, b
    ya, yb = (-xa[1], xa[0]), (-xb[1], xb[0])
    d = (cb[0] - ca[0], cb[1] - ca[1])
    dot = lambda u, v: u[0] * v[0] + u[1] * v[1]
    for n in (xa, ya, xb, yb):
        ra = la * abs(dot(xa, n)) + wa * abs(dot(ya, n))
        rb = lb * abs(dot(xb, n)) + wb * abs(dot(yb, n))
        if abs(dot(d, n)) > ra + rb - 10:   # 10 cm de tolerancia (espejos, redondeo)
            return False
    return True


def segment_hits_rect(p, q, r):
    (c, x, l, w) = r
    y = (-x[1], x[0])
    for k in range(21):
        s = (p.x + (q.x - p.x) * k / 20 - c[0], p.y + (q.y - p.y) * k / 20 - c[1])
        if abs(s[0] * x[0] + s[1] * x[1]) < l and abs(s[0] * y[0] + s[1] * y[1]) < w:
            return True
    return False


def sample():
    world, trucks, gate = state["world"], state["trucks"], state["gate"]
    state["samples"] += 1
    live = [t for t in trucks if not (t.get_distance_along() < 700 and t.get_bay() is None)]
    rects = {t.get_actor_label(): rect(t) for t in live}
    names = list(rects)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if overlap(rects[names[i]], rects[names[j]]) and len(state["overlaps"]) < 10:
                state["overlaps"].append([names[i], names[j], round(time.monotonic() - state["start"], 1)])
    # brazo: bajo o bajando = no del todo arriba
    if gate.get_editor_property("openness") < 0.98:
        a = gate.get_editor_property("post").get_world_location()
        arm = gate.get_editor_property("arm")
        tip = arm.get_world_location() + arm.get_forward_vector() * gate.get_editor_property("arm_length")
        for t in trucks:
            if segment_hits_rect(a, tip, rect(t)) and len(state["arm_hits"]) < 10:
                state["arm_hits"].append([t.get_actor_label(), round(gate.get_editor_property("openness"), 2)])
    for t in trucks:
        b = t.get_blocked_by()
        if b:
            state["blocked"][t.get_actor_label()] = b.get_actor_label()
        if t.get_back_off() > 0:
            state["backoffs"] += 1
        # sin saltos: la altura no cambia de golpe entre dos muestras (fuera de los cajones)
        p = t.vehicle.get_world_location()
        last = state["prev"].get(t.get_actor_label())
        state["prev"][t.get_actor_label()] = p
        if last and t.get_bay() is None:
            ds = math.hypot(p.x - last.x, p.y - last.y)
            if 20 < ds < 2000 and abs(p.z - last.z) / ds > 0.3 and len(state["jumps"]) < 10:
                state["jumps"].append([t.get_actor_label(), round(p.x), round(p.y), round(p.z - last.z, 1), round(ds)])
        # ruedas en el piso (cada tanto)
        if state["samples"] % 5 == 0 and len(state["ground"]) < 400:
            p = t.vehicle.get_world_location()
            z = floor_z(world, p, trucks)
            if z is not None:
                state["ground"].append(round(p.z - z, 1))
    if state["volcador"].is_dumping():
        state["dumped"] = True


def tick(delta):
    try:
        age = time.monotonic() - state["t"]
        if time.monotonic() - state["start"] > 280:
            raise RuntimeError("La prueba tardo demasiado (fase %s)" % state["phase"])
        name = state["phase"]
        if name == "line":
            acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
            world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            line = next(a for a in acts if a.get_actor_label() == "Camion_Recorrido")
            sp = line.get_editor_property("path")
            under = []
            length = sp.get_spline_length()
            # sin los camiones ni la barrera (su brazo no es piso)
            trucks = [a for a in acts if isinstance(a, (unreal.FactoryVehiclePath, unreal.FactoryGateBarrier))]
            for k in range(int(length / 100)):
                p = sp.get_location_at_distance_along_spline(k * 100, unreal.SplineCoordinateSpace.WORLD)
                z = floor_z(world, unreal.Vector(p.x, p.y, p.z + 200), trucks)
                if z is not None and p.z < z - 1:
                    under.append([round(p.x), round(p.y), round(p.z - z, 1)])
            steps = []
            for k in range(int(length / 50) - 1):
                a = sp.get_location_at_distance_along_spline(k * 50, unreal.SplineCoordinateSpace.WORLD)
                b = sp.get_location_at_distance_along_spline(k * 50 + 50, unreal.SplineCoordinateSpace.WORLD)
                if abs(b.z - a.z) / 50 > 0.3:
                    steps.append([round(a.x), round(a.y), round(b.z - a.z, 1)])
            check("linea_sobre_el_piso", not under, puntos=sp.get_number_of_spline_points(), debajo_del_piso=under[:5],
                  se_dibuja=sp.get_editor_property("draw_debug"))
            check("linea_sin_escalones", not steps, escalones=steps[:5])
            levels.editor_request_begin_play()
            phase("spawn")
        elif name == "spawn" and age > 4:
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            pawn = unreal.GameplayStatics.get_player_character(worlds[0], 0) if worlds else None
            if pawn is None:
                return
            world = worlds[0]
            unreal.FactoryUnlockSubsystem.get(pawn).unlock("Camion2")
            trucks = [labelled(world, unreal.FactoryVehiclePath, n) for n in ("Camion_Recorrido", "Camion_Recorrido2", "Camion_Volcador")]
            gate = labelled(world, unreal.FactoryGateBarrier, "Cabina_Barrera")
            state.update(world=world, pawn=pawn, trucks=trucks, gate=gate, volcador=trucks[2],
                         half=pawn.capsule_component.get_scaled_capsule_half_height())
            # personaje contra el brazo bajo: parado a 1 m del brazo, camina hacia el
            post = gate.get_editor_property("post").get_world_location()
            arm = gate.get_editor_property("arm")
            mid = arm.get_world_location() + arm.get_forward_vector() * 150
            pawn.set_actor_location(unreal.Vector(mid.x + 100, mid.y, post.z + state["half"] + 5), False, True)
            state["arm_x"] = mid.x
            phase("arm")
        elif name == "arm":
            pawn = state["pawn"]
            pawn.add_movement_input(unreal.Vector(-1, 0, 0), 1.0, True)
            if age > 1.5:
                x = pawn.get_actor_location().x
                check("personaje_contra_el_brazo", x > state["arm_x"], personaje_x=round(x), brazo_x=round(state["arm_x"]))
                pawn.set_actor_location(unreal.Vector(-3000, 2000, 10 + state["half"] + 5), False, True)
                unreal.SystemLibrary.execute_console_command(state["world"], "slomo 4")
                phase("drive")
        elif name == "drive":
            sample()
            for t in state["trucks"]:
                g = t.get_waiting_gate()
                if g and isinstance(g, unreal.FactoryGateBarrier) and g.get_editor_property("openness") < 0.01:
                    g.set_open(True)
            parked = [t for t in state["trucks"][:2] if t.is_parked()]
            vol = state["volcador"]
            if (state["dumped"] and not vol.is_parked() and vol.get_bay() is None and len(parked) == 2) or age > 200:
                check("camiones_no_se_atraviesan", not state["overlaps"], encimados=state["overlaps"], muestras=state["samples"],
                      esperaron_a=state["blocked"], retrocesos=state["backoffs"])
                check("barrera_nunca_baja_sobre_un_camion", not state["arm_hits"], golpes=state["arm_hits"])
                g = state["ground"]
                off = [d for d in g if d < -5]   # hundido en el piso (sobre la calle de las rampas va mas alto)
                check("ruedas_en_el_piso", g and len(off) <= len(g) * 0.02, muestras=len(g), fuera=off[:10])
                check("movimiento_suave", not state["jumps"], saltos=state["jumps"])
                check("todos_terminan", state["dumped"] and len(parked) == 2,
                      volcado=state["dumped"], estacionados=[t.get_actor_label() for t in parked], segundos=round(age, 1))
                # personaje contra un camion estacionado: a 1,5 m de su costado, camina hacia el
                truck = parked[0] if parked else state["trucks"][0]
                v = truck.vehicle
                yaw = math.radians(v.get_world_rotation().yaw)
                c = v.get_world_location() + unreal.Vector(math.cos(yaw), math.sin(yaw), 0) * 150
                side = unreal.Vector(-math.sin(yaw), math.cos(yaw), 0)
                start = c + side * 260
                floor = floor_z(state["world"], c, state["trucks"]) or c.z
                state["pawn"].set_actor_location(unreal.Vector(start.x, start.y, floor + state["half"] + 5), False, True)
                state.update(side=side, truck_c=c, test_truck=truck.get_actor_label())
                unreal.SystemLibrary.execute_console_command(state["world"], "slomo 1")
                phase("truck_wall")
        elif name == "truck_wall":
            pawn = state["pawn"]
            pawn.add_movement_input(state["side"] * -1, 1.0, True)
            if age > 2.0:
                p, c, s = pawn.get_actor_location(), state["truck_c"], state["side"]
                dist = (p.x - c.x) * s.x + (p.y - c.y) * s.y
                check("personaje_contra_el_camion", dist > HALF - 20, camion=state["test_truck"], al_costado_cm=round(dist))
                finish()
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error("[TRAFICO_PLAY] " + report["error"])
        finish()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
