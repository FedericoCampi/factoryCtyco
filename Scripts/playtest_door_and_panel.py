"""PIE: porton de la entrada de los camiones y los 3 estilos del panel de informacion (28/09).

Porton: arranca cerrado; el primer camion frena antes (sin tocarlo); E en la botonera lo abre; el camion pasa;
con un camion debajo no se cierra; E despues lo cierra. Captura Docs/roll_door_closed.png (camion esperando).
Panel (I): una captura por estilo al terminar su entrada (Docs/info_style_1.png, _2, _3) y una a mitad de la
entrada del 1 (Docs/info_style_1_entrada.png).
Informe: Docs/door_panel_play.json. Cierra el editor.
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
    unreal.log(f"[DOOR_PANEL] fase {name}")
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/door_panel_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def shot(name):
    print("[captura desactivada]", 1280, 720, str(project / "Docs" / name))


def door_gap():
    """Del paragolpes del camion 1 al plano del porton, a lo largo de su marcha (cm)."""
    mesh, door = state["mesh"], state["door"]
    front = mesh.get_world_location() + mesh.get_forward_vector() * state["t1"].get_editor_property("front_length")
    return (door.get_actor_location() - front).dot(mesh.get_forward_vector())


def stand_at_button():
    button = state["door"].get_editor_property("button").get_world_location()
    pawn = state["pawn"]
    pawn.set_actor_location(unreal.Vector(button.x + 90, button.y, pawn.get_actor_location().z), False, True)


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
    if time.monotonic() - state["start"] > 200 and state["phase"] != "quit":
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
        trucks = {t.get_actor_label(): t for t in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryVehiclePath)}
        doors = unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryRollDoor)
        check("hay_porton", len(doors) == 1)
        state.update(pawn=pawn, t1=trucks["Camion_Recorrido"], mesh=trucks["Camion_Recorrido"].get_editor_property("vehicle"),
                     door=doors[0], gathering=pawn.get_component_by_class(unreal.FactoryGatheringComponent),
                     hud=unreal.GameplayStatics.get_player_controller(worlds[0], 0).get_hud())
        check("porton_cerrado_al_empezar", not doors[0].get_editor_property("want_open") and doors[0].get_editor_property("openness") == 0)
        phase("wait_truck")
    elif name == "wait_truck":
        loc = state["mesh"].get_world_location()
        last = state.get("last")
        state["last"] = loc
        if last is not None and (loc - last).length() < 0.01 and age > 4:
            state.setdefault("still", time.monotonic())
            if time.monotonic() - state["still"] > 1.2:
                gap = door_gap()
                check("camion_frena_antes_del_porton", 0 < gap < 200, gap_cm=round(gap, 1))
                stand_at_button()
                phase("shot_closed")
        else:
            state.pop("still", None)
        if age > 40:
            check("camion_frena_antes_del_porton", False, gap_cm=round(door_gap(), 1))
    elif name == "shot_closed" and age > 1.0:
        shot("roll_door_closed.png")
        phase("open")
    elif name == "open" and age > 1.5:
        state["gathering"].interact()
        check("e_abre_el_porton", state["door"].get_editor_property("want_open"))
        state["before"] = state["mesh"].get_world_location()
        phase("pass")
    elif name == "pass":
        door = state["door"]
        if door.get_editor_property("vehicle_under") and "tried" not in state:
            state["tried"] = True
            state["gathering"].interact()   # cerrar con el camion debajo: no debe
            check("no_cierra_sobre_el_camion", door.get_editor_property("want_open"))
        if state.get("tried") and not door.get_editor_property("vehicle_under"):
            moved = (state["mesh"].get_world_location() - state["before"]).length()
            check("camion_pasa", moved > 400, moved_cm=round(moved))
            stand_at_button()
            state["gathering"].interact()
            check("e_cierra_el_porton", not door.get_editor_property("want_open"))
            phase("panel")
        elif age > 30:
            check("camion_pasa", False, under=door.get_editor_property("vehicle_under"))
    elif name == "panel" and age > 1.0:
        state["gathering"].toggle_inventory()   # tecla I (estilo 1)
        state["hud"].set_info_style(0)
        phase("style1_mid")
    elif name == "style1_mid" and age > 0.17:
        shot("info_style_1_entrada.png")
        phase("style1")
    elif name == "style1" and age > 1.6:
        check("estilo_1", state["hud"].get_info_style() == 0)
        shot("info_style_1.png")
        phase("to2")
    elif name == "to2" and age > 1.0:
        state["hud"].set_info_style(1)   # tecla 2 / pestana 2
        phase("style2")
    elif name == "style2" and age > 1.6:
        check("estilo_2", state["hud"].get_info_style() == 1)
        shot("info_style_2.png")
        phase("to3")
    elif name == "to3" and age > 1.0:
        state["hud"].set_info_style(2)   # tecla 3 / pestana 3
        phase("style3")
    elif name == "style3" and age > 1.6:
        check("estilo_3", state["hud"].get_info_style() == 2)
        shot("info_style_3.png")
        phase("done")
    elif name == "done" and age > 1.5:
        report["passed"] = True
        finish()
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal.log("[DOOR_PANEL] registrado")
