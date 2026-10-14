"""Prueba en Play (03/10), con L_FactoryDemo abierto en el editor: el camion carga en el muelle.

- La garita (`Cabina_Barrera`) esta en el patio de los muelles y la calle se dibuja a lo largo de la linea.
- Las cintas del cajon 1 van encadenadas: Cinta_Carga3 -> Cinta_Muelle_5 (la ultima termina en el anden); las del
  despacho (Cinta_Carga2, Cinta_Carga) acumulan y el jugador lleva las cajas a mano.
- El camion entra (la prueba levanta la barrera cuando espera en ella), entra marcha atras a `Cajon_Muelle_1`, abre y
  carga las cajas que el personaje deja en la primera cinta (la prueba se las da), sale lleno, y al llegar al final de su
  linea la mision cuenta los paquetes.
- (04/10) Estacionado abre la persiana de atras (las tablillas suben tras el dintel); el costado y el techo no se abren.
- (04/10) El porton del cajon (`Porton_Muelle_N`, DockDoor del cajon) sigue cerrado mientras el camion espera en la
  garita, sube cuando la pasa (ya esta arriba al estacionar) y baja cuando el camion sale.
- (04/10) Las cajas esperan antes del porton mientras no esta arriba: la cinta que lo cruza (Cinta_Muelle_5) lo
  encuentra sola y ninguna caja pasa su plano con el porton bajo.
El tiempo va 4 veces mas rapido. No guarda nada. Corre en el tick del editor (Python del editor o el puente MCP).
Informe: Docs/muelles_carga_play.json.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

docs = Path(unreal.Paths.project_dir()).resolve() / "Docs"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}, "timeline": []}
state = {"phase": "start", "t": time.monotonic(), "start": time.monotonic(), "handed": 0, "max_cargo": 0}
# recorrido armado por el usuario el 04/10 (antes: Cinta_Carga3 -> Cinta_Carga4 -> Cinta_Muelle_1 .. 5)
# desde el 05/10 las cintas del despacho acumulan y el jugador lleva las cajas a mano: la cadena del cajon 1 empieza adentro
CHAIN = ["Cinta_Carga3", "Cinta_Muelle_5"]


def phase(name):
    state.update(phase=name, t=time.monotonic())
    report["timeline"].append([name, round(time.monotonic() - state["start"], 1)])


def check(name, ok, **values):
    report["checks"][name] = dict(passed=bool(ok), **values)


def finish():
    report["passed"] = bool(report["checks"]) and all(c["passed"] for c in report["checks"].values()) and "error" not in report
    (docs / "muelles_carga_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    unreal.log("[MUELLES_CARGA_PLAY] " + json.dumps(report, default=str))
    unreal.unregister_slate_post_tick_callback(state["handle"])
    if unreal.EditorLevelLibrary.get_pie_worlds(False):
        if "world" in state:
            unreal.SystemLibrary.execute_console_command(state["world"], "slomo 1")
        levels.editor_request_end_play()


def labelled(world, cls, name):
    return next((a for a in unreal.GameplayStatics.get_all_actors_of_class(world, cls) if a.get_actor_label() == name), None)


def tick(delta):
    try:
        age = time.monotonic() - state["t"]
        if time.monotonic() - state["start"] > 280:
            raise RuntimeError("La prueba tardo demasiado")
        name = state["phase"]
        if name == "start":
            levels.editor_request_begin_play()
            phase("spawn")
        elif name == "spawn" and age > 4:
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            pawn = unreal.GameplayStatics.get_player_character(worlds[0], 0) if worlds else None
            if pawn is None:
                return
            world = worlds[0]
            gate = labelled(world, unreal.FactoryGateBarrier, "Cabina_Barrera")
            docks = labelled(world, unreal.StaticMeshActor, "Muelles_Carga")
            o, e = docks.get_actor_bounds(False)
            inside = gate and o.x - e.x < gate.get_actor_location().x < o.x + e.x and o.y - e.y < gate.get_actor_location().y < o.y + e.y
            check("garita_en_los_muelles", bool(inside))
            truck = labelled(world, unreal.FactoryVehiclePath, "Camion_Recorrido")
            check("calle", truck.get_editor_property("road_mesh") is not None)
            belts = [labelled(world, unreal.FactoryLoadingBelt, n) for n in CHAIN]
            links = []
            for a, b in zip(belts, belts[1:]):
                nxt = a.get_next() if a else None
                links.append([a.get_actor_label() if a else None, nxt.get_actor_label() if nxt else None])
            check("cintas_encadenadas", all(l[1] == n for l, n in zip(links, CHAIN[1:])) and belts[-1].get_next() is None, enlaces=links)
            dispatch = labelled(world, unreal.FactoryDispatchBelt, "Despacho_Cajas")
            mission = unreal.FactoryMissionSubsystem.get(pawn)
            state.update(world=world, pawn=pawn, gate=gate, truck=truck, feed=belts[0], box=dispatch.get_editor_property("box_mesh"),
                         carry=pawn.get_component_by_class(unreal.FactoryCarryComponent), mission=mission,
                         delivered0=mission.get_editor_property("delivered"),
                         bay=labelled(world, unreal.FactoryTruckBay, "Cajon_Muelle_1"))
            last = belts[-1]
            hold_bay = last.get_hold_bay()
            check("cinta_espera_en_el_porton", hold_bay is not None and hold_bay.get_actor_label() == "Cajon_Muelle_1"
                  and last.get_hold_at() > 0, cajon=hold_bay.get_actor_label() if hold_bay else None,
                  espera_en_cm=round(last.get_hold_at(), 1))
            door = state["bay"].get_editor_property("dock_door")
            state.update(last=last, door=door, crossed_shut=0, held_seen=0)
            state["slats_shut"] = truck.get_editor_property("rear_slats").get_instance_count()
            # el personaje junto al comienzo de la primera cinta, para dejar cajas
            p = belts[0].world_at(30)
            pawn.set_actor_location(unreal.Vector(p.x + 120, p.y, p.z + 20), False, True)
            unreal.SystemLibrary.execute_console_command(world, "slomo 4")
            phase("run")
        elif name == "run":
            truck, gate = state["truck"], state["gate"]
            if gate and truck.get_waiting_gate() == gate:
                state.setdefault("door_at_gate", round(state["bay"].get_door_openness(), 3))
                # la barrera se abre recien con cajas esperando ante el porton (asi se prueba que esperan)
                if state["last"].get_box_count() >= 2 or time.monotonic() - state["start"] > 120:
                    state.setdefault("waiting_at_door", state["last"].get_box_count())
                    gate.set_open(True)
            # diez cajas a la cinta, de a una cuando hay lugar
            capacity = truck.get_editor_property("cargo_capacity")
            if state["handed"] < capacity:
                if not state["carry"].is_carrying():
                    state["carry"].take(state["box"])
                # TryLoad tambien devuelve true sin lugar (la caja queda en las manos): cuenta solo si la solto
                if state["feed"].try_load(state["pawn"]) and not state["carry"].is_carrying():
                    state["handed"] += 1
            state["max_cargo"] = max(state["max_cargo"], truck.get_cargo_count())
            # seguimiento: cajas en cada cinta + en el camion + en la mano, cuando cambia
            counts = {b.get_actor_label(): b.get_box_count() for b in unreal.GameplayStatics.get_all_actors_of_class(state["world"], unreal.FactoryLoadingBelt) if b.get_box_count()}
            snap = (tuple(sorted(counts.items())), truck.get_cargo_count(), state["carry"].is_carrying())
            if snap != state.get("snap"):
                state["snap"] = snap
                report.setdefault("cajas", []).append([round(time.monotonic() - state["start"], 2), round(delta, 3), state["handed"], counts, truck.get_cargo_count()])
            # con la puerta abierta en el cajon: la persiana arriba (escala Z minima) y la de atras en uso
            if truck.is_parked() and truck.get_door_openness() >= 0.99:
                rise = truck.get_rear_door_rise()
                state["open_rear"] = (truck.uses_rear_door(), round(rise, 1), truck.get_editor_property("rear_slat_mesh") is not None,
                                      truck.get_editor_property("rear_slats").get_instance_count())
            # con el porton sin subir del todo, ninguna caja de la ultima cinta del otro lado de su plano
            if state["door"] and state["bay"].get_door_openness() < 0.99:
                across = state["door"].get_actor_right_vector()
                origin = state["door"].get_actor_location()
                side0 = (state["last"].world_at(0) - origin).dot(across)
                belt_mesh = state["last"].get_editor_property("belt")
                for comp in state["last"].get_components_by_class(unreal.StaticMeshComponent):
                    if comp == belt_mesh or not comp.get_name().startswith("StaticMeshComponent"):
                        continue
                    state["held_seen"] += 1
                    if (comp.get_world_location() - origin).dot(across) * side0 < 0:
                        state["crossed_shut"] += 1
            # cada caja mira hacia donde va su cinta (salvo en los primeros cm, donde se acomoda tras pasar de cinta)
            for belt in [b for b in unreal.GameplayStatics.get_all_actors_of_class(state["world"], unreal.FactoryLoadingBelt) if b.get_box_count()]:
                span = belt.get_editor_property("length") * belt.get_actor_scale3d().x
                pts = [belt.world_at(span * k / 60) for k in range(61)]
                mesh_comp = belt.get_editor_property("belt")
                for comp in belt.get_components_by_class(unreal.StaticMeshComponent):
                    if comp == mesh_comp or not comp.get_name().startswith("StaticMeshComponent"):
                        continue
                    p = comp.get_world_location()
                    k = min(range(60), key=lambda i: (pts[i] - p).length())
                    if span * k / 60 < belt.get_editor_property("handoff_blend") + 5:
                        continue
                    d = pts[k + 1] - pts[k]
                    import math
                    off = (comp.get_world_rotation().yaw - math.degrees(math.atan2(d.y, d.x)) + 180) % 360 - 180
                    worst = state.setdefault("worst_yaw", [0, None])
                    if abs(off) > abs(worst[0]):
                        state["worst_yaw"] = [round(off, 1), belt.get_actor_label()]
            dock = state["bay"]
            if truck.is_parked() and dock.get_door_openness() >= 0.99:
                door = dock.get_editor_property("dock_door")
                state["dock_open"] = (door.get_actor_label() if door else None,
                                      round(door.root_component.get_editor_property("relative_scale3d").z, 3) if door else None)
            bay = truck.get_bay()
            if truck.is_parked() and "parked" not in state:
                state["door_on_arrival"] = round(state["bay"].get_door_openness(), 3)
                last = labelled(state["world"], unreal.FactoryLoadingBelt, CHAIN[-1])
                rear = truck.get_editor_property("vehicle").get_world_location()
                tip = last.get_delivery_point()
                docked = last.get_editor_property("docked")
                report["al_estacionar"] = dict(eje_trasero=[round(rear.x), round(rear.y)], punta=[round(tip.x), round(tip.y)],
                                               distancia=round(unreal.Vector(rear.x - tip.x, rear.y - tip.y, 0).length()),
                                               cinta_amarrada_a=docked.get_actor_label() if docked else None,
                                               siguiente=(last.get_next().get_actor_label() if last.get_next() else None),
                                               tags=[str(t) for t in last.tags], amarrado=truck.is_docked(),
                                               carga=truck.get_cargo_count(), capacidad=truck.get_editor_property("cargo_capacity"),
                                               usa_atras=truck.uses_rear_door(),
                                               cajon=[round(state["bay"].get_actor_location().x), round(state["bay"].get_actor_location().y)])
                state["parked"] = bay.get_actor_label() if bay else None
                state["parked_docked"] = truck.is_docked()
                phase("parked")
                state["phase"] = "run"
            if state.get("parked") and not truck.is_parked() and not truck.is_maneuvering() and "left" not in state:
                state["left"] = True
                phase("left")
                state["phase"] = "run"
            delivered = state["mission"].get_editor_property("delivered") - state["delivered0"]
            if state.get("parked") and "cargo_track" in state and truck.get_cargo_count() != state["cargo_track"][-1][1]:
                state["cargo_track"].append([round(time.monotonic() - state["start"], 1), truck.get_cargo_count()])
            state.setdefault("cargo_track", [[0, 0]])
            if delivered > 0 or time.monotonic() - state["start"] > 200:
                report["cajas_en_cintas"] = {b.get_actor_label(): b.get_box_count() for b in unreal.GameplayStatics.get_all_actors_of_class(state["world"], unreal.FactoryLoadingBelt) if b.get_box_count()}
                report["salidas_carga3"] = [o.get_actor_label() for o in state["feed"].get_outputs()]
                report["carga"] = state["cargo_track"]
                check("estaciona_en_cajon_1", state.get("parked") == "Cajon_Muelle_1", cajon=state.get("parked"))
                check("carga_desde_la_cinta", state["max_cargo"] >= capacity and state.get("parked_docked"),
                      cajas_dadas=state["handed"], carga_maxima=state["max_cargo"], amarrado_al_estacionar=state.get("parked_docked"))
                rear = state.get("open_rear")
                # arriba: el zocalo sube hasta el dintel y no queda ninguna tablilla a la vista
                full = truck.get_editor_property("rear_door_height") - truck.get_editor_property("rear_header") - 6.0
                check("abre_la_persiana", bool(rear) and rear[0] and rear[2] and rear[1] >= full - 0.5 and rear[3] == 0,
                      atras_subida_tablillas=rear)
                check("persiana_cerrada_al_salir", truck.get_rear_door_rise() < 0.5
                      and truck.get_editor_property("rear_slats").get_instance_count() == state["slats_shut"] > 0,
                      tablillas=[state["slats_shut"], truck.get_editor_property("rear_slats").get_instance_count()])
                dock_open = state.get("dock_open")
                check("cajas_no_pasan_el_porton_cerrado", state["crossed_shut"] == 0 and state["held_seen"] > 0,
                      cajas_vistas=state["held_seen"], pasaron=state["crossed_shut"],
                      esperando_al_abrir_la_barrera=state.get("waiting_at_door"))
                worst = state.get("worst_yaw", [0, None])
                check("cajas_miran_hacia_la_cinta", abs(worst[0]) <= 8.0, peor_giro=worst)
                check("porton_cerrado_en_la_garita", state.get("door_at_gate") == 0.0, apertura=state.get("door_at_gate"))
                check("porton_abierto_al_estacionar", (state.get("door_on_arrival") or 0) >= 0.99,
                      apertura=state.get("door_on_arrival"))
                check("porton_sube_estacionado", bool(dock_open and dock_open[0]
                      and dock_open[1] <= state["bay"].get_editor_property("door_rolled") + 0.01), porton_escala=dock_open)
                check("porton_baja_al_irse", state["bay"].get_door_openness() <= 0.01)
                check("sale_lleno", bool(state.get("left")))
                check("cuenta_la_entrega", delivered >= capacity, paquetes=delivered)
                finish()
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error("[MUELLES_CARGA_PLAY] " + report["error"])
        finish()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
