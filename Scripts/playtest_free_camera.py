"""PIE: camara libre por defecto y seguir al personaje con clic (29/09).

1. Al empezar la camara esta libre: el personaje camina 6 m y la camara no se mueve (Docs/camara_libre.png).
2. "Clic" sobre el personaje (su posicion en pantalla): la camara lo sigue y lo acompana (Docs/camara_sigue.png).
3. StopFollowing: queda libre otra vez. Un salto grande del personaje (como el ascensor) la lleva con el.
4. La flecha arriba mueve la camara libre.
5. Se contrata al encargado y se lo sigue: mientras maneja, la camara va con el auto (Docs/camara_sigue_auto.png).
Informe: Docs/free_camera_play.json. Cierra el editor.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}}
state = {"phase": "warmup", "t": time.monotonic(), "start": time.monotonic()}
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")


def phase(name):
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/free_camera_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def shot(name):
    print("[captura desactivada]", 1280, 720, str(project / "Docs" / name))


def dist2d(a, b):
    return round(((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5)


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
    if time.monotonic() - state["start"] > 150 and state["phase"] != "quit":
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
        camera = pawn.get_component_by_class(unreal.FactoryCameraComponent)
        state.update(pawn=pawn, world=worlds[0], camera=camera, controller=unreal.GameplayStatics.get_player_controller(worlds[0], 0))
        phase("free")
    elif name == "free" and age > 2:
        camera, pawn = state["camera"], state["pawn"]
        check("empieza_libre", camera.is_free() and camera.get_follow_target() is None)
        state["focus0"] = camera.get_focus()
        loc = pawn.get_actor_location()
        pawn.set_actor_location(unreal.Vector(loc.x + 600, loc.y, loc.z), True, True)
        phase("free_check")
    elif name == "free_check" and age > 1.5:
        camera = state["camera"]
        moved = dist2d(camera.get_focus(), state["focus0"])
        check("libre_no_sigue", moved < 5, foco_se_movio_cm=moved, personaje_al_foco_cm=dist2d(state["pawn"].get_actor_location(), camera.get_focus()))
        shot("camara_libre.png")
        phase("pick")
    elif name == "pick" and age > 1.5:
        screen = state["controller"].project_world_location_to_screen(state["pawn"].get_actor_location(), False)
        if isinstance(screen, tuple):
            screen = screen[-1]
        picked = screen is not None and state["camera"].follow_at_screen(screen)
        check("clic_en_el_personaje_lo_sigue", picked and state["camera"].get_follow_target() == state["pawn"], pantalla=[round(screen.x), round(screen.y)])
        phase("follow_check")
    elif name == "follow_check" and age > 2.0:
        gap = dist2d(state["pawn"].get_actor_location(), state["camera"].get_focus())
        check("foco_en_el_personaje", gap < 40, distancia_cm=gap)
        shot("camara_sigue.png")
        loc = state["pawn"].get_actor_location()
        state["pawn"].set_actor_location(unreal.Vector(loc.x, loc.y + 400, loc.z), True, True)
        phase("follow_move")
    elif name == "follow_move" and age > 1.5:
        gap = dist2d(state["pawn"].get_actor_location(), state["camera"].get_focus())
        check("lo_acompana_al_moverse", gap < 40, distancia_cm=gap)
        state["camera"].stop_following()
        state["focus1"] = state["camera"].get_focus()
        loc = state["pawn"].get_actor_location()
        state["pawn"].set_actor_location(unreal.Vector(loc.x - 400, loc.y, loc.z), True, True)
        phase("free_again")
    elif name == "free_again" and age > 1.0:
        moved = dist2d(state["camera"].get_focus(), state["focus1"])
        check("libre_otra_vez", state["camera"].get_follow_target() is None and moved < 5, foco_se_movio_cm=moved)
        # salto grande (como un viaje en ascensor): la camara libre va con el
        pawn = state["pawn"]
        state["before_jump"] = pawn.get_actor_location() - state["camera"].get_focus()
        loc = pawn.get_actor_location()
        pawn.set_actor_location(unreal.Vector(loc.x, loc.y + 3000, loc.z), False, True)
        phase("jump_check")
    elif name == "jump_check" and age > 1.0:
        now = state["pawn"].get_actor_location() - state["camera"].get_focus()
        diff = round(((now.x - state["before_jump"].x) ** 2 + (now.y - state["before_jump"].y) ** 2) ** 0.5)
        check("ascensor_la_lleva", diff < 30, cambio_de_encuadre_cm=diff)
        state["focus_keys"] = state["camera"].get_focus()
        state["pawn_keys"] = state["pawn"].get_actor_location()
        state["camera"].send_editor_test_input("Up", 1.0, True)
        phase("keys")
    elif name == "keys" and age > 1.0:
        state["camera"].send_editor_test_input("Up", 1.0, False)
        moved = dist2d(state["camera"].get_focus(), state["focus_keys"])
        pawn_moved = dist2d(state["pawn"].get_actor_location(), state["pawn_keys"])
        check("flechas_mueven_la_camara", moved > 500, foco_se_movio_cm=moved)
        check("flechas_no_mueven_al_personaje", pawn_moved < 5, personaje_se_movio_cm=pawn_moved)
        phase("hire_worker")
    elif name == "hire_worker" and age > 0.5:
        worker = unreal.FactoryStaffSubsystem.get(state["world"]).hire("Barrera")
        check("contratado", worker is not None)
        state["worker"] = worker
        state["camera"].follow(worker)
        phase("car_check")
    elif name == "car_check" and age > 3.0:
        car = state["worker"].get_editor_property("car")
        gap = dist2d(car.get_actor_location(), state["camera"].get_focus()) if car else 99999
        check("sigue_al_auto", state["worker"].get_state() == unreal.FactoryWorkerState.DRIVING and gap < 150, distancia_cm=gap)
        shot("camara_sigue_auto.png")
        phase("done")
    elif name == "done" and age > 1.5:
        report["passed"] = True
        finish()
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
