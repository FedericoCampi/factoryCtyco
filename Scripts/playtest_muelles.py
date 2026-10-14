"""Prueba (03/10), con L_FactoryDemo abierto en el editor: muelles, cajones, paso al muelle y pasarelas rectas.

En el editor (sin guardar; lo deja como estaba):
- la manija de la baranda derecha de una pasarela recta la corre 40 cm y la del extremo la alarga 2 m.
En Play (el tiempo va 4 veces mas rapido; el camion 2 se desbloquea solo en esta prueba):
- la garita ya no esta y la calle no se dibuja;
- los dos camiones entran marcha atras a dos cajones distintos y quedan estacionados con el eje trasero en el cajon;
- el personaje camina del estacionamiento al interior del edificio del muelle (sin muros en el medio, sin caer);
- parado sobre una pasarela recta, queda apoyado en su piso.
Corre en el tick del editor (Python del editor o el puente MCP). Informe: Docs/muelles_play.json.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

docs = Path(unreal.Paths.project_dir()).resolve() / "Docs"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False, "checks": {}}
state = {"phase": "handles", "t": time.monotonic(), "start": time.monotonic()}


def phase(name):
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = dict(passed=bool(ok), **values)


def finish():
    report["passed"] = bool(report["checks"]) and all(c["passed"] for c in report["checks"].values()) and "error" not in report
    (docs / "muelles_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    unreal.log("[MUELLES_PLAY] " + json.dumps(report, default=str))
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
        if time.monotonic() - state["start"] > 300:
            raise RuntimeError("La prueba tardo demasiado")
        name = state["phase"]
        if name == "handles":
            walk = next(a for a in actors.get_all_level_actors() if isinstance(a, unreal.FactoryWalkwayStraight))
            keep = {p: walk.get_editor_property(p) for p in ("left_rail_y", "right_rail_y", "start_x", "end_x")}
            h = walk.get_editor_property("right_rail_handle")
            walk.set_editor_property("right_rail_handle", unreal.Vector(h.x, h.y + 40, h.z))
            e = walk.get_editor_property("end_handle")
            walk.set_editor_property("end_handle", unreal.Vector(e.x + 200, e.y, e.z))
            check("recta_manijas", abs(walk.get_editor_property("right_rail_y") - keep["right_rail_y"] - 40) < 1
                  and abs(walk.get_editor_property("end_x") - keep["end_x"] - 200) < 1,
                  baranda_cm=round(walk.get_editor_property("right_rail_y") - keep["right_rail_y"], 1),
                  largo_cm=round(walk.get_editor_property("end_x") - keep["end_x"], 1))
            for p, v in keep.items():
                walk.set_editor_property(p, v)
            walk.rebuild()
            state["walk_label"] = walk.get_actor_label()
            levels.editor_request_begin_play()
            phase("spawn")
        elif name == "spawn" and age > 4:
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            pawn = unreal.GameplayStatics.get_player_character(worlds[0], 0) if worlds else None
            if pawn is None:
                return
            world = worlds[0]
            state.update(world=world, pawn=pawn, half=pawn.capsule_component.get_scaled_capsule_half_height())
            check("sin_garita", labelled(world, unreal.FactoryGateBarrier, "Cabina_Barrera") is None)
            truck = labelled(world, unreal.FactoryVehiclePath, "Camion_Recorrido")
            check("sin_calle", truck.get_editor_property("road_mesh") is None)
            unreal.FactoryUnlockSubsystem.get(pawn).unlock("Camion2")
            unreal.SystemLibrary.execute_console_command(world, "slomo 4")
            state["trucks"] = [truck, labelled(world, unreal.FactoryVehiclePath, "Camion_Recorrido2")]
            state["bays"] = {b.get_actor_label(): b for b in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryTruckBay)}
            # paso al muelle: dentro del estacionamiento, cerca de su borde norte, caminando hacia el muelle (+Y)
            docks = labelled(world, unreal.StaticMeshActor, "Muelles_Carga")
            o, e = docks.get_actor_bounds(False)
            state["docks_back_y"] = o.y - e.y
            start = unreal.Vector(-4300, state["docks_back_y"] - 450, 10 + state["half"] + 5)
            pawn.set_actor_location(start, False, True)
            state["floor_z"] = 10.0
            phase("walk")
        elif name == "walk":
            pawn = state["pawn"]
            pawn.add_movement_input(unreal.Vector(0, 1, 0), 1.0, True)
            if age > 1.6:   # 6 s de juego
                loc = pawn.get_actor_location()
                feet = loc.z - state["half"]
                check("paso_al_muelle", loc.y > state["docks_back_y"] + 300 and abs(feet - state["floor_z"]) < 20 and pawn.character_movement.is_moving_on_ground(),
                      y=round(loc.y), borde_muelle_y=round(state["docks_back_y"]), pies_cm=round(feet, 1))
                walk = labelled(state["world"], unreal.FactoryWalkwayStraight, state["walk_label"])
                xf = walk.get_actor_transform()
                mid = unreal.Vector((walk.get_editor_property("start_x") + walk.get_editor_property("end_x")) / 2,
                                    (walk.get_editor_property("left_rail_y") + walk.get_editor_property("right_rail_y")) / 2, 60)
                p = xf.transform_location(mid)
                pawn.set_actor_location(unreal.Vector(p.x, p.y, p.z + state["half"] + 5), False, True)
                state.update(xf=xf)
                phase("stand")
        elif name == "stand" and age > 0.6:
            pawn = state["pawn"]
            feet = state["xf"].inverse_transform_location(pawn.get_actor_location()).z - state["half"]
            check("recta_apoyado", abs(feet - 37.0) < 8 and pawn.character_movement.is_moving_on_ground(), pies_sobre_actor_cm=round(feet, 1))
            phase("trucks")
        elif name == "trucks":
            trucks = state["trucks"]
            parked = [t for t in trucks if t and t.is_parked()]
            if len(parked) == len(trucks) or age > 60:
                rows, bays_used = [], set()
                for t in trucks:
                    bay = t.get_bay()
                    gap = None
                    if bay:
                        a, b = t.vehicle.get_world_location(), bay.get_actor_location()
                        gap = round(((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5, 1)
                        bays_used.add(bay.get_actor_label())
                    rows.append({"camion": t.get_actor_label(), "estacionado": t.is_parked(),
                                 "cajon": bay.get_actor_label() if bay else None, "eje_trasero_a_cm": gap})
                check("camiones_estacionados", len(parked) == len(trucks) and len(bays_used) == len(trucks)
                      and all(r["eje_trasero_a_cm"] is not None and r["eje_trasero_a_cm"] < 30 for r in rows),
                      camiones=rows, segundos_reales=round(age, 1))
                finish()
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error("[MUELLES_PLAY] " + report["error"])
        finish()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
