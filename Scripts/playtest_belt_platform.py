"""PIE: las cintas de la fabrica sobre su plataforma (30/09).

1. Las tres cintas tienen la plataforma y el marco 50 cm arriba; las maquinas siguen en el piso.
2. Se carga chatarra en el deposito de entrada: la carga viaja por arriba de la cinta levantada (no adentro de
   la plataforma) y llega a la trituradora, o sea que levantarlas no corto el paso de material.
3. Una captura de la linea: Saved/Screenshots/belt_platform.png.
Informe: Docs/belt_platform_play.json. Cierra el editor.
Lanzar con -ExecCmds="py <lanzador sin espacios en la ruta>".
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
shot = project / "Saved/Screenshots/belt_platform.png"
report = {"passed": False, "checks": {}}
state = {"started": time.monotonic(), "finishing": False, "busy": False}


def wait(seconds):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        yield


def run():
    assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
    yield from wait(6)
    levels.editor_request_begin_play()
    yield from wait(4)
    worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
    assert worlds, "No arranco Play"
    pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
    # La intro tapa la pantalla, y la captura: tres tarjetas y el briefing, cuatro avances.
    for _ in range(4):
        for guide in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryGuide):
            guide.advance()
        yield from wait(.7)
    factory = pawn.get_component_by_class(unreal.FactoryDemoComponent).factory
    by_id = {str(b.persistent_id): b for b in factory.buildings()}
    floor = factory.floor_z
    belts = [by_id[f"Cinta_Fabrica_{n}"] for n in (1, 2, 3)]
    lift = belts[0].lift()
    assert lift > 0, "Las cintas no tienen plataforma"
    rows = []
    for belt in belts:
        rows.append([str(belt.persistent_id), round(belt.get_actor_location().z, 1), round(belt.visual.get_world_location().z, 1),
                     belt.base.static_mesh.get_name() if belt.base.static_mesh else None,
                     round(belt.base.get_world_scale().z, 2)])
        assert abs(belt.get_actor_location().z - floor) < .1, "La cinta tiene que seguir en el piso"
        assert abs(belt.visual.get_world_location().z - (floor + lift)) < .1, rows[-1]
        assert belt.base.static_mesh is not None, rows[-1]
    machines = {round(b.get_actor_location().x): b for b in factory.buildings() if b not in belts}
    assert sorted(machines) == [-600, -200, 200, 600], sorted(machines)
    for x, machine in machines.items():
        assert machine.lift() == 0 and machine.base.static_mesh is None, x
    report["checks"]["plataforma"] = {"lift_cm": lift, "cintas": rows}

    storage, crusher = machines[-600], machines[-200]
    assert storage.input.add_item(factory.resource("Scrap"), 10) == 10
    cargo_z, arrived = None, False
    limit = time.monotonic() + 25
    while time.monotonic() < limit and not (cargo_z is not None and arrived):
        if cargo_z is None and belts[0].cargo.is_visible():
            cargo_z = belts[0].cargo.get_world_location().z
        arrived = arrived or crusher.input.get_total() + crusher.output.get_total() > 0 or crusher.progress_seconds > 0
        yield
    assert cargo_z is not None, "La carga nunca aparecio sobre la cinta"
    assert abs(cargo_z - (floor + lift + 33)) < .5, f"La carga viaja a z={cargo_z}, no sobre la cinta"
    assert arrived, "El material no llego a la trituradora"
    report["checks"]["material"] = {"carga_z": round(cargo_z, 1), "llego_a_trituradora": True}

    pawn.character_movement.stop_movement_immediately()
    pawn.set_actor_location(unreal.Vector(-200, 320, 100), False, True)
    camera = pawn.get_component_by_class(unreal.FactoryCameraComponent)
    camera.reset_camera()
    for _ in range(3):
        camera.send_editor_test_input("MouseScrollUp", 1.0, True)
        camera.send_editor_test_input("MouseScrollUp", 0.0, False)
        yield
    yield from wait(2.5)
    shot.parent.mkdir(parents=True, exist_ok=True)
    shot.unlink(missing_ok=True)
    unreal.AutomationLibrary.take_high_res_screenshot(1440, 900, str(shot))
    yield from wait(4)
    assert shot.exists(), "No se escribio la captura"
    report["checks"]["captura"] = str(shot)
    report["passed"] = True


def finish():
    state["finishing"] = True
    (project / "Docs/belt_platform_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    yield from wait(2)
    unreal.unregister_slate_post_tick_callback(state["handle"])
    unreal.SystemLibrary.quit_editor()


state["steps"] = run()


def tick(delta):
    if state["busy"]:   # la captura re-entra el callback
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
