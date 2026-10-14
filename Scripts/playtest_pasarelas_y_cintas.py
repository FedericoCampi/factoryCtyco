"""Prueba en Play (03/10), con L_FactoryDemo abierto en el editor: pasarelas, escalera, salto y cintas arregladas.

Despues de run_pasarelas_y_cintas.py (o de import_pasarelas.py y apply_fix_cintas_curva_y_puente.py). Juega en Play:
- escalera: el personaje camina desde el pie de Escalera_Plataforma hacia arriba y tiene que llegar al piso de arriba;
- pasarelas: parado sobre cada una, queda apoyado en su piso (no la atraviesa);
- salto: el personaje puede saltar (JumpMaxCount 1, sube y vuelve a apoyarse);
- despacho: Cinta_Puente1 y su curva (mejora del camion 2) siguen bloqueadas al empezar;
- cuarzo: una piedra puesta en Cinta_Cuarzo_Triturar3 pasa por Cinta_Fabrica_Esquina2 hasta Cinta_Cuarzo_Triturar.
Corre en el tick del editor (Python del editor o el puente MCP) y termina el Play al final; no guarda nada.
Informe: Docs/pasarelas_y_cintas_play.json.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

docs = Path(unreal.Paths.project_dir()).resolve() / "Docs"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}}
state = {"phase": "warmup", "t": time.monotonic(), "start": time.monotonic()}


def phase(name):
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = dict(passed=bool(ok), **values)


def finish():
    report["passed"] = bool(report["checks"]) and all(c["passed"] for c in report["checks"].values()) and "error" not in report
    (docs / "pasarelas_y_cintas_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    unreal.log("[PASARELAS_Y_CINTAS] " + json.dumps(report, default=str))
    unreal.unregister_slate_post_tick_callback(state["handle"])
    if unreal.EditorLevelLibrary.get_pie_worlds(False):
        levels.editor_request_end_play()


def label(world, cls, name):
    return next((a for a in unreal.GameplayStatics.get_all_actors_of_class(world, cls) if a.get_actor_label() == name), None)


def put(pawn, x, y, z):
    pawn.character_movement.set_editor_property("velocity", unreal.Vector(0, 0, 0))
    pawn.set_actor_location(unreal.Vector(x, y, z), False, True)


def tick(delta):
    try:
        age = time.monotonic() - state["t"]
        if time.monotonic() - state["start"] > 300:
            raise RuntimeError("La prueba tardo demasiado")
        name = state["phase"]
        # la piedra se sigue en cada cuadro: cruza las dos cintas en pocos segundos, mientras se prueba lo demas
        if "take" in state:
            take, item = state["take"], state["item"]
            if take.get_editor_property("input").get_quantity(item) + take.get_editor_property("output").get_quantity(item) > state["take_before"]:
                state.setdefault("arrived_at", time.monotonic() - state["injected_at"])
            if state["corner"].get_editor_property("input").get_total() > 0:
                state["seen_corner"] = True
        if name == "warmup" and age > 5:
            levels.editor_request_begin_play()
            phase("spawn")
        elif name == "spawn" and age > 4:
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            pawn = unreal.GameplayStatics.get_player_character(worlds[0], 0) if worlds else None
            if pawn is None:
                return
            world = worlds[0]
            state.update(world=world, pawn=pawn, half=pawn.capsule_component.get_scaled_capsule_half_height())
            # despacho: el puente del primer camion se ve desde el principio
            bridges = {n: label(world, unreal.Actor, n) for n in ("Cinta_Puente1", "Cinta_Puente1_Curva")}
            # lo bloqueado se oculta y pierde la colision (UFactoryUnlockSubsystem)
            alive = lambda a: a and "Bloqueado" not in [str(t) for t in a.tags] and a.get_actor_enable_collision()
            check("despacho_puente_bloqueado", all(a and not alive(a) for a in bridges.values()),
                  activas=[n for n, a in bridges.items() if a and alive(a)])
            # cuarzo: piedra en Triturar3
            feed = label(world, unreal.FactoryBuilding, "Cinta_Cuarzo_Triturar3")
            corner = label(world, unreal.FactoryBuilding, "Cinta_Fabrica_Esquina2")
            take = label(world, unreal.FactoryBuilding, "Cinta_Cuarzo_Triturar")
            deposit = label(world, unreal.FactoryBuilding, "Deposito_Cuarzo")
            factory = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryDemoWorld)[0]
            item = deposit.get_editor_property("storage_item")
            state.update(feed=feed, corner=corner, take=take, item=item,
                         take_before=take.get_editor_property("input").get_quantity(item))
            added = feed.get_editor_property("input").add_item(factory.resource(item), 1)
            state["injected_at"] = time.monotonic()
            check("cuarzo_piedra_puesta", added == 1, item=str(item))
            # escalera: al pie, del lado de los escalones (+X), mirando hacia la plataforma
            stairs = label(world, unreal.StaticMeshActor, "Escalera_Plataforma")
            s = stairs.get_actor_location()
            put(pawn, s.x + 430, s.y, s.z + state["half"] + 5)
            pawn.set_actor_rotation(unreal.Rotator(0, 0, 180), False)
            state.update(stairs=s, top=s.z)
            phase("stairs")
        elif name == "stairs":
            pawn = state["pawn"]
            pawn.add_movement_input(unreal.Vector(-1, 0, 0), 1.0, True)
            feet = pawn.get_actor_location().z - state["half"]
            state["top"] = max(state["top"], feet)
            if age > 7:
                loc = pawn.get_actor_location()
                arriba = feet - state["stairs"].z
                check("escalera_se_sube", arriba > 190 and pawn.character_movement.is_moving_on_ground(),
                      pies_sobre_piso_cm=round(arriba, 1), x=round(loc.x), y=round(loc.y))
                state["walk"] = [("Pasarela_Recta", None), ("Pasarela_L", None)]
                phase("walkway")
        elif name == "walkway":
            pawn, world = state["pawn"], state["world"]
            current = next((i for i, (n, v) in enumerate(state["walk"]) if v is None), None)
            if current is None:
                phase("jump_start")
                return
            n = state["walk"][current][0]
            if "placed" not in state:
                actor = label(world, unreal.StaticMeshActor, n)
                o, e = actor.get_actor_bounds(False)
                # el centro puede estar vacio (la L): se prueba sobre su piso donde el rayo pega
                spot = None
                for fx, fy in ((0, 0), (0.6, 0), (-0.6, 0), (0, 0.6), (0, -0.6), (0.6, 0.6), (-0.6, -0.6), (0.6, -0.6), (-0.6, 0.6)):
                    p = unreal.Vector(o.x + fx * e.x, o.y + fy * e.y, 0)
                    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(p.x, p.y, o.z + e.z + 50), unreal.Vector(p.x, p.y, o.z - e.z - 10),
                                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [pawn], unreal.DrawDebugTrace.NONE, True)
                    hit = hit.to_tuple() if hit else (False,)
                    if hit[0] and hit[9] == actor and hit[4].z < o.z - e.z + 80:
                        spot = hit[4]
                        break
                if spot is None:
                    state["walk"][current] = (n, {"passed": False, "motivo": "no se encontro su piso"})
                    return
                put(pawn, spot.x, spot.y, spot.z + state["half"] + 10)
                state.update(placed=spot, t=time.monotonic())
            elif age > 2:
                feet = pawn.get_actor_location().z - state["half"]
                ok = abs(feet - state["placed"].z) < 15 and pawn.character_movement.is_moving_on_ground()
                state["walk"][current] = (n, {"passed": ok, "pies_cm": round(feet, 1), "piso_cm": round(state["placed"].z, 1)})
                check(f"pasarela_{n}", ok, pies_cm=round(feet, 1), piso_cm=round(state["placed"].z, 1))
                state.pop("placed")
        elif name == "jump_start":
            pawn = state["pawn"]
            state["ground"] = pawn.get_actor_location().z
            state["peak"] = state["ground"]
            check("salto_habilitado", pawn.get_editor_property("jump_max_count") >= 1 and pawn.character_movement.get_editor_property("jump_z_velocity") > 0,
                  jump_max_count=pawn.get_editor_property("jump_max_count"), jump_z_velocity=pawn.character_movement.get_editor_property("jump_z_velocity"))
            pawn.jump()
            phase("jump")
        elif name == "jump":
            pawn = state["pawn"]
            state["peak"] = max(state["peak"], pawn.get_actor_location().z)
            if age > 0.3:
                pawn.stop_jumping()
            if age > 2.5:
                check("salto_sube_y_baja", state["peak"] - state["ground"] > 30 and pawn.character_movement.is_moving_on_ground(),
                      alto_cm=round(state["peak"] - state["ground"], 1))
                phase("belt")
        elif name == "belt":
            arrived = "arrived_at" in state
            if arrived or age > 25:
                check("cuarzo_pasa_la_curva", arrived and state.get("seen_corner", False), paso_por_curva=state.get("seen_corner", False),
                      llego_a_Triturar=arrived, segundos=round(state.get("arrived_at", -1), 1))
                finish()
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error("[PASARELAS_Y_CINTAS] " + report["error"])
        finish()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
