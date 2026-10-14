"""Prueba en Play (04/10), con L_FactoryDemo abierto en el editor: las puertas que se abren solas (la de recepcion y,
desde el 05/10, las dos de personal del muelle) abren hacia el otro lado del que viene el personaje.

Lleva al personaje a un lado de Puerta_Recepcion (AFactoryAutoDoor), espera que abra y anota hacia donde giro; lo aleja
para que cierre y lo lleva al otro lado: tiene que girar al reves, y en los dos casos la hoja se aleja del personaje.
No guarda nada. Corre en el tick del editor (puente MCP). Informe: Docs/puerta_recepcion_play.json.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

docs = Path(unreal.Paths.project_dir()).resolve() / "Docs"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}, "giros": {}}
DOORS = ["Puerta_Recepcion", "Puerta_Muelle_Personal_0", "Puerta_Muelle_Personal_1"]
state = {"phase": "start", "t": time.monotonic(), "start": time.monotonic(), "doors": list(DOORS), "sides": [1, -1]}


def finish():
    report["passed"] = bool(report["checks"]) and all(c["passed"] for c in report["checks"].values()) and "error" not in report
    (docs / "puerta_recepcion_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    unreal.unregister_slate_post_tick_callback(state["handle"])
    if unreal.EditorLevelLibrary.get_pie_worlds(False):
        levels.editor_request_end_play()


def tick(delta):
    try:
        age = time.monotonic() - state["t"]
        if time.monotonic() - state["start"] > 200:
            raise RuntimeError("La prueba tardo demasiado")
        name = state["phase"]
        if name == "start":
            levels.editor_request_begin_play()
            state.update(phase="spawn", t=time.monotonic())
        elif name == "spawn" and age > 4:
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            pawn = unreal.GameplayStatics.get_player_character(worlds[0], 0) if worlds else None
            if pawn is None:
                return
            state["world"] = worlds[0]
            state["pawn"] = pawn
            state.update(phase="pick", t=time.monotonic())
        elif name == "pick":
            label = state["doors"][0]
            pawn = state["pawn"]
            door = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(state["world"], unreal.FactoryAutoDoor)
                        if a.get_actor_label() == label)
            state["label"] = label
            state["sides"] = [1, -1]
            yaw = door.get_actor_rotation().yaw
            width = door.get_editor_property("width")
            fwd = unreal.MathLibrary.get_forward_vector(unreal.Rotator(0, 0, yaw))
            right = unreal.MathLibrary.get_right_vector(unreal.Rotator(0, 0, yaw))
            hinge = door.get_actor_location()
            middle = hinge - fwd * (width / 2)
            state.update(door=door, closed_yaw=yaw, right=right, middle=middle, phase="go", t=time.monotonic())
        elif name == "go":
            side = state["sides"][0]
            spot = state["middle"] + state["right"] * (side * 120.0)
            state["pawn"].set_actor_location(unreal.Vector(spot.x, spot.y, spot.z + 100), False, True)
            state.update(phase="open", t=time.monotonic())
        elif name == "open" and age > 1.5:
            side = state["sides"].pop(0)
            door = state["door"]
            turned = unreal.MathLibrary.normalize_axis(door.get_actor_rotation().yaw - state["closed_yaw"])
            report["giros"].setdefault(state["label"], {})[side] = round(turned, 1)
            # la punta libre de la hoja: del lado opuesto al personaje (positivo gira hacia -Y)
            check_ok = abs(turned) >= 45 and (turned > 0) == (side > 0)
            report["checks"][f"{state['label']}_lado_{'mas' if side > 0 else 'menos'}"] = dict(passed=check_ok, giro=round(turned, 1),
                                                                             apertura=round(door.get_openness(), 2))
            far = state["middle"] + state["right"] * 900.0 + unreal.Vector(0, 0, 100)
            state["pawn"].set_actor_location(far, False, True)
            state.update(phase="close", t=time.monotonic())
        elif name == "close" and age > 1.5:
            if state["sides"]:
                state.update(phase="go", t=time.monotonic())
            else:
                g = report["giros"][state["label"]]
                report["checks"][f"{state['label']}_gira_al_reves_segun_el_lado"] = dict(passed=(g.get(1, 0) > 0) != (g.get(-1, 0) > 0), giros=g)
                state["doors"].pop(0)
                if state["doors"]:
                    state.update(phase="pick", t=time.monotonic())
                else:
                    finish()
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error("[PUERTA_PLAY] " + report["error"])
        finish()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
