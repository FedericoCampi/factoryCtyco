"""PIE (con el editor abierto): plataforma elevadora y primera persona (02/10).

1. Plataforma: Plataforma_Elevadora_1, en la linea (de Cinta_Cuarzo_Triturar a la tolva de la trituradora), sube
   con la carga hasta arriba, se la entrega a la trituradora y vuelve a bajar (tiempo x3).
2. Primera persona: V (set_first_person) pone la camara en los ojos del personaje, el cuerpo se oculta para el y el
   personaje camina hacia donde mira; el mouse mira sin apretar nada; con Inicio vuelve la camara isometrica.
Informe: Docs/plataforma_y_camara_play.json. Captura: Saved/Screenshots/primera_persona.png.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}}
state = {"started": time.monotonic(), "finishing": False, "busy": False}


def wait(seconds):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        yield


def wait_for(condition, seconds, what):
    until = time.monotonic() + seconds
    while not condition():
        if time.monotonic() > until:
            raise AssertionError(f"Se acabo el tiempo esperando: {what}")
        yield


def run():
    levels.editor_request_begin_play()
    yield from wait(4)
    world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
    pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
    buildings = {b.get_actor_label(): b for b in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryBuilding)}
    sim = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryDemoWorld)[0]
    lift, crusher = buildings["Plataforma_Elevadora_1"], buildings["Trituradora_Cuarzo"]
    unreal.GameplayStatics.set_global_time_dilation(world, 3.0)

    # 1. la plataforma de la linea: sube cada carga hasta la tolva, la entrega y vuelve a bajar
    # el deposito ya no esta en la linea (el usuario carga a mano): se pone cuarzo en la cinta, de a uno
    feeder = buildings["Cinta_Cuarzo_Triturar"]
    quartz = sim.resource("Quartz")
    highest, came_down, delivered = 0.0, False, 0
    before = crusher.input.get_total() + crusher.output.get_total()
    until = time.monotonic() + 60
    while not (came_down and delivered >= 2) and time.monotonic() < until:
        if feeder.input.get_total() == 0:
            feeder.input.add_item(quartz, 1)
        rise = lift.get_editor_property("platform_rise")
        highest = max(highest, rise)
        if highest > lift.get_editor_property("lift_height") - 10 and rise < 3:
            came_down = True
        delivered = max(delivered, crusher.input.get_total() + crusher.output.get_total() + int(crusher.progress_seconds > 0) - before)
        yield
    unreal.GameplayStatics.set_global_time_dilation(world, 1.0)
    report["checks"]["plataforma"] = {"sube_cm": round(lift.get_editor_property("lift_height")), "subio_cm": round(highest),
                                      "volvio_a_bajar": came_down, "trituradora_recibio": delivered,
                                      "segundos_por_viaje": round(lift.travel_seconds(), 2)}
    assert came_down and delivered >= 1, report["checks"]["plataforma"]

    # 2. primera persona
    camera = pawn.get_component_by_class(unreal.FactoryCameraComponent)
    view = unreal.GameplayStatics.get_player_camera_manager(world, 0)
    iso = view.get_camera_location()
    camera.send_editor_test_input("V", 1.0, True)
    camera.send_editor_test_input("V", 0.0, False)
    yield from wait(.6)
    eye = view.get_camera_location()
    body = pawn.get_actor_location()
    assert camera.is_first_person(), "V no paso a primera persona"
    assert abs(eye.x - body.x) < 30 and abs(eye.y - body.y) < 30 and 20 < eye.z - body.z < 120, f"camara {eye}, cuerpo {body}"
    # el mouse mira, sin apretar nada: se mueve en X y la vista gira
    yaw0 = view.get_camera_rotation().yaw
    for _ in range(10):
        camera.send_editor_test_input("MouseX", 2.0, True)
        yield
    yaw1 = view.get_camera_rotation().yaw
    turned = abs((yaw1 - yaw0 + 180) % 360 - 180)
    assert turned > 1, f"el mouse no giro la vista ({yaw0:.1f} -> {yaw1:.1f})"
    report["checks"]["mirar_con_mouse_grados"] = round(turned, 1)
    shot = project / "Saved/Screenshots/primera_persona.png"
    shot.unlink(missing_ok=True)
    unreal.AutomationLibrary.take_high_res_screenshot(1440, 900, str(shot))
    yield from wait(2.5)
    # en primera persona, cerca de un lingote y del horno: el aviso de E aparece bajo el punto de mira
    piles = {p.get_actor_label(): p for p in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryResourcePile)}
    for name, spot in (("lingote", piles["Lingote_Prueba_1"].get_actor_location() + unreal.Vector(-120, 0, 95)),):
        pawn.character_movement.stop_movement_immediately()
        pawn.set_actor_location(spot, False, True)
        yield from wait(.8)
        path = project / f"Saved/Screenshots/primera_persona_{name}.png"
        path.unlink(missing_ok=True)
        unreal.AutomationLibrary.take_high_res_screenshot(1440, 900, str(path))
        yield from wait(2.5)
        report["checks"].setdefault("capturas_cerca", []).append(path.name if path.exists() else f"(falto) {path.name}")
    camera.reset_camera()
    yield from wait(2.0)
    back = view.get_camera_location()
    assert not camera.is_first_person() and (back - body).length() > 500, f"no volvio a la isometrica: {back}"
    report["checks"]["primera_persona"] = {"isometrica": [round(iso.x), round(iso.y), round(iso.z)],
                                           "ojos": [round(eye.x), round(eye.y), round(eye.z)],
                                           "cuerpo": [round(body.x), round(body.y), round(body.z)],
                                           "captura": shot.name if shot.exists() else "falto"}
    report["passed"] = True


def finish():
    state["finishing"] = True
    (project / "Docs/plataforma_y_camara_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    levels.editor_request_end_play()
    yield from wait(2)
    unreal.unregister_slate_post_tick_callback(state["handle"])


state["steps"] = run()


def tick(delta):
    if state["busy"]:
        return
    state["busy"] = True
    try:
        if not state["finishing"] and time.monotonic() - state["started"] > 120:
            raise RuntimeError("Se acabo el tiempo")
        next(state["steps"])
    except StopIteration:
        if not state["finishing"]:
            state["steps"] = finish()
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error(report["error"])
        if not state["finishing"]:
            state["steps"] = finish()
    finally:
        state["busy"] = False


state["handle"] = unreal.register_slate_post_tick_callback(tick)
