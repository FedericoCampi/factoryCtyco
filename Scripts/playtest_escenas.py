"""Prueba en Play (04/10), con L_FactoryDemo abierto en el editor: solo se ve la escena donde esta el personaje.

Lleva al personaje al medio de cada escena (Fabrica, Despacho, Laboratorio, Empleados) y comprueba que solo esa se dibuja
(UFactorySceneSubsystem), que una pieza de cada otra escena queda oculta para la camara del jugador y que lo compartido
(pisos de afuera, horizonte) se sigue viendo. Despues, en la Fabrica: el techo se ve en isometrica y en primera
persona (desde el 07/10 el de la fabrica va siempre en Play; antes, con la etiqueta Techo, no se veia en isometrica). No guarda nada. Corre en el tick del editor (puente MCP).
Informe: Docs/escenas_play.json.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

docs = Path(unreal.Paths.project_dir()).resolve() / "Docs"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}}
# escena -> pieza que la representa (se lleva al personaje a su centro)
SCENES = {"Fabrica": "SceneRobot_Fabrica", "Despacho": "Parking_Estacionamiento", "Laboratorio": "Lab1_Escena",
          "Empleados": "Recepcion_Sala"}
SHARED = ["Piso_Exterior", "Cielo_Horizonte"]
ROOF = "Techo_Fabrica_Losa"
state = {"phase": "start", "t": time.monotonic(), "start": time.monotonic(), "todo": list(SCENES)}


def finish():
    report["passed"] = bool(report["checks"]) and all(c["passed"] for c in report["checks"].values()) and "error" not in report
    (docs / "escenas_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    unreal.unregister_slate_post_tick_callback(state["handle"])
    if unreal.EditorLevelLibrary.get_pie_worlds(False):
        levels.editor_request_end_play()


def tick(delta):
    try:
        age = time.monotonic() - state["t"]
        if time.monotonic() - state["start"] > 120:
            raise RuntimeError("La prueba tardo demasiado")
        if state["phase"] == "start":
            levels.editor_request_begin_play()
            state.update(phase="spawn", t=time.monotonic())
        elif state["phase"] == "spawn" and age > 4:
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            pawn = unreal.GameplayStatics.get_player_character(worlds[0], 0) if worlds else None
            if pawn is None:
                return
            world = worlds[0]
            by = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)}
            sub = unreal.FactorySceneZone.get_scene_subsystem(pawn)
            state.update(world=world, pawn=pawn, by=by, sub=sub, phase="move", t=time.monotonic())
        elif state["phase"] == "move":
            scene = state["todo"][0]
            o, e = state["by"][SCENES[scene]].get_actor_bounds(False)
            state["pawn"].set_actor_location(unreal.Vector(o.x, o.y, o.z + 50), False, True)
            state.update(phase="look", t=time.monotonic())
        elif state["phase"] == "look" and age > 0.6:
            scene = state["todo"].pop(0)
            sub, by = state["sub"], state["by"]
            visible = sorted(str(s) for s in sub.get_visible_scenes())
            others = {s: sub.is_hidden(by[a]) for s, a in SCENES.items() if s != scene}
            mine = sub.is_hidden(by[SCENES[scene]])
            shared = {a: sub.is_hidden(by[a]) for a in SHARED}
            report["checks"][f"en_{scene}"] = dict(
                passed=visible == [scene] and all(others.values()) and not mine and not any(shared.values()),
                visibles=visible, otras_ocultas=others, la_propia_oculta=mine, compartidas_ocultas=shared,
                ocultos=sub.get_hidden_count())
            if state["todo"]:
                state.update(phase="move", t=time.monotonic())
            else:
                o, e = state["by"][SCENES["Fabrica"]].get_actor_bounds(False)
                state["pawn"].set_actor_location(unreal.Vector(o.x, o.y, o.z + 50), False, True)
                state["view"] = state["pawn"].get_component_by_class(unreal.FactoryCameraComponent)
                state["view"].set_first_person(False)
                state.update(phase="roof_iso", t=time.monotonic())
        elif state["phase"] == "roof_iso" and age > 0.6:
            roof = state["by"][ROOF]
            report["checks"]["techo_isometrica"] = dict(passed=not state["sub"].is_hidden(roof), oculto=state["sub"].is_hidden(roof))
            state["view"].set_first_person(True)
            state.update(phase="roof_fp", t=time.monotonic())
        elif state["phase"] == "roof_fp" and age > 0.6:
            roof = state["by"][ROOF]
            hidden = state["sub"].is_hidden(roof)
            report["checks"]["techo_primera_persona"] = dict(passed=not hidden, oculto=hidden)
            state["view"].set_first_person(False)
            finish()
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error("[ESCENAS_PLAY] " + report["error"])
        finish()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
