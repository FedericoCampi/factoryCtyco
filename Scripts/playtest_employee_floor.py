"""PIE: piso 3 (estacionamiento de empleados) y el contratado que llega en auto (28/09).

1. El panel del ascensor tiene 3 pisos, el 3 es EMPLEADOS. El personaje sube desde el estacionamiento
   (panel, piso 3) y llega arriba: Docs/piso3_llegada.png y Docs/piso3_playa.png.
2. Se contrata al encargado de barrera: llega en auto por la calle y estaciona (Docs/piso3_auto.png), se baja y
   camina al ascensor (Docs/piso3_caminando.png), viaja, sale en el estacionamiento y camina a la cabina
   (Docs/piso3_encargado_cabina.png, con el personaje de vuelta abajo).
Informe: Docs/employee_floor_play.json (con los segundos de cada tramo). Cierra el editor.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}, "trip": []}
state = {"phase": "warmup", "t": time.monotonic(), "start": time.monotonic()}
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
S = unreal.FactoryWorkerState


def phase(name):
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/employee_floor_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def shot(name):
    print("[captura desactivada]", 1280, 720, str(project / "Docs" / name))


def put(x, y, z=None):
    pawn = state["pawn"]
    pawn.set_actor_location(unreal.Vector(x, y, pawn.get_actor_location().z if z is None else z), False, True)


def v(p):
    return [round(p.x), round(p.y), round(p.z)]


def tick(delta):
    if state.get("busy"):
        return
    state["busy"] = True
    try:
        step()
    except Exception:
        report["error"] = traceback.format_exc()
        finish()
    finally:
        state["busy"] = False


def step():
    age = time.monotonic() - state["t"]
    if time.monotonic() - state["start"] > 300 and state["phase"] != "quit":
        raise RuntimeError("La prueba no termino a tiempo")
    name = state["phase"]
    if name == "warmup" and age > 8:
        levels.editor_request_begin_play()
        phase("spawn")
    elif name == "spawn":
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0) if worlds else None
        if pawn is None:
            return
        world = worlds[0]
        every = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)}
        state.update(pawn=pawn, world=world, every=every,
                     barrier=unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryGateBarrier)[0],
                     gathering=pawn.get_component_by_class(unreal.FactoryGatheringComponent))
        phase("to_elevator")
    elif name == "to_elevator" and age > 3:   # la malla de navegacion se arma al empezar
        every = state["every"]
        low = every["Ascensor_Estacionamiento"]
        floors = [f.get_actor_label() for f in low.get_floors()]
        check("tres_pisos", floors == ["Ascensor_Fabrica", "Ascensor_Estacionamiento", "Ascensor_Empleados"], pisos=floors)
        check("piso3_empleados", every["Ascensor_Empleados"].get_editor_property("stop_name") == "EMPLEADOS")
        spot = low.get_actor_location()
        put(spot.x, spot.y, spot.z + 110)
        phase("open_panel")
    elif name == "open_panel" and age > 1.5:
        state["gathering"].interact()
        phase("select")
    elif name == "select" and age > 0.8:
        ok = state["every"]["Ascensor_Estacionamiento"].select_floor(3)
        check("elige_piso_3", ok)
        phase("ride_up")
    elif name == "ride_up":
        z = state["pawn"].get_actor_location().z
        if z > 380 and age > 4:
            check("llega_al_piso_3", True, z=round(z), segundos=round(age, 1))
            phase("shot_arrival")
        elif age > 25:
            check("llega_al_piso_3", False, z=round(z))
    elif name == "shot_arrival" and age > 3.0:
        shot("piso3_llegada.png")
        floor = state["every"]["Empleados_Piso"].get_actor_location()
        put(floor.x + 200, floor.y + 300)
        phase("shot_lot")
    elif name == "shot_lot" and age > 1.5:
        shot("piso3_playa.png")
        phase("hire")
    elif name == "hire" and age > 1.0:
        staff = unreal.FactoryStaffSubsystem.get(state["world"])
        worker = staff.hire("Barrera")
        check("contratado", worker is not None)
        check("llega_en_auto", worker.get_state() == S.DRIVING and worker.get_editor_property("car") is not None)
        state["worker"] = worker
        state["last_state"] = None
        state["state_at"] = time.monotonic()
        phase("follow")
    elif name == "follow":
        worker = state["worker"]
        now = worker.get_state()
        if now != state["last_state"]:
            loc = worker.get_actor_location()
            report["trip"].append({"estado": str(now).split(".")[-1].split(":")[0], "a_los_s": round(time.monotonic() - state["state_at"], 1), "donde": v(loc)})
            state["last_state"] = now
            if now == S.WALKING and not state.get("parked_shot"):
                car = worker.get_editor_property("car").get_actor_location()
                put(car.x + 300, car.y + 350)
                state["parked_shot"] = time.monotonic()
            if now == S.RIDING and not state.get("down"):
                # el personaje baja por su lado, para ver al encargado salir y caminar a la cabina
                booth = state["barrier"].get_actor_location()
                put(booth.x - 250, booth.y - 300, booth.z + 110)
                state["down"] = True
        if state.get("parked_shot") and not state.get("parked_done") and time.monotonic() - state["parked_shot"] > 1.2:
            shot("piso3_caminando.png")
            state["parked_done"] = True
        if now == S.DRIVING and not state.get("car_shot") and time.monotonic() - state["state_at"] > 3.0:
            car = worker.get_editor_property("car").get_actor_location()
            put(car.x + 250, car.y + 450)
            state["car_shot"] = time.monotonic()
        if state.get("car_shot") and not state.get("car_done") and time.monotonic() - state["car_shot"] > 1.0:
            shot("piso3_auto.png")
            state["car_done"] = True
        if now in (S.WORKING, S.ACTING):
            check("encargado_en_la_cabina", state["barrier"].is_inside(worker), donde=v(worker.get_actor_location()),
                  segundos=round(time.monotonic() - state["state_at"], 1), saltos=worker.get_editor_property("skips"),
                  trabado_en=v(worker.get_editor_property("last_held_at")))
            phase("shot_booth")
        elif time.monotonic() - state["state_at"] > 150:
            check("encargado_llega", False, estado=str(now), donde=v(worker.get_actor_location()))
    elif name == "shot_booth" and age > 1.5:
        shot("piso3_encargado_cabina.png")
        report["passed"] = True
        finish()
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
