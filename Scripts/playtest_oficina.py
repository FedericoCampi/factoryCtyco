"""Prueba en Play (07/10), con L_FactoryDemo abierto en el editor: al piso de ADMINISTRACION por ascensor.

Pone al personaje adentro de Ascensor_Fabrica, abre su panel (TryInteract), elige el piso de Ascensor_Oficina
(SelectFloor) y espera: tiene que llegar parado en la oficina (dentro de Escena_Oficina, a la altura de su piso), con
la escena Oficina visible y la Fabrica oculta, y poder caminar hacia adentro (sale de la cabina sin chocar). No guarda
nada. Corre en el tick del editor (puente MCP). Informe: Docs/oficina_play.json.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

docs = Path(unreal.Paths.project_dir()).resolve() / "Docs"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}}
state = {"phase": "start", "t": time.monotonic(), "start": time.monotonic()}


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}


def finish():
    report["passed"] = bool(report["checks"]) and all(c["passed"] for c in report["checks"].values()) and "error" not in report
    (docs / "oficina_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    unreal.unregister_slate_post_tick_callback(state["handle"])
    if unreal.EditorLevelLibrary.get_pie_worlds(False):
        levels.editor_request_end_play()


def tick(delta):
    try:
        age = time.monotonic() - state["t"]
        if time.monotonic() - state["start"] > 90:
            raise RuntimeError(f"La prueba tardo demasiado (fase {state['phase']})")
        if state["phase"] == "start":
            levels.editor_request_begin_play()
            state.update(phase="spawn", t=time.monotonic())
        elif state["phase"] == "spawn" and age > 4:
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            pawn = unreal.GameplayStatics.get_player_character(worlds[0], 0) if worlds else None
            if pawn is None:
                return
            by = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.Actor)}
            lift, office = by["Ascensor_Fabrica"], by["Ascensor_Oficina"]
            loc = lift.get_actor_location()
            pawn.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + 100), False, True)
            state.update(pawn=pawn, by=by, lift=lift, office=office, phase="panel", t=time.monotonic())
        elif state["phase"] == "panel" and age > 1.0:
            lift, office, pawn = state["lift"], state["office"], state["pawn"]
            floors = [f.get_editor_property("stop_name") for f in lift.get_floors()]
            check("administracion_en_el_panel", "ADMINISTRACIÓN" in floors, pisos=floors)
            check("en_la_cabina", lift.in_cabin(pawn))
            lift.try_interact(pawn)
            started = lift.select_floor(office.get_floor_number())
            check("arranca_el_viaje", started, piso=office.get_floor_number())
            state.update(phase="ride", t=time.monotonic())
        elif state["phase"] == "ride" and age > 8 and state["office"].is_idle() and state["lift"].is_idle():
            pawn, by = state["pawn"], state["by"]
            p = pawn.get_actor_location()
            o, e = by["Escena_Oficina"].get_actor_bounds(False)
            floor_z = by["Oficina_Administracion"].get_actor_location().z
            check("llega_a_la_oficina", abs(p.x - o.x) < e.x and abs(p.y - o.y) < e.y and abs(p.z - floor_z - 90) < 60,
                  personaje=[round(v) for v in p.to_tuple()], piso=floor_z)
            sub = unreal.FactorySceneZone.get_scene_subsystem(pawn)
            visible = sorted(str(s) for s in sub.get_visible_scenes())
            check("se_ve_la_oficina", "Oficina" in visible and "Fabrica" not in visible, visibles=visible)
            # sale caminando hacia adentro de la oficina (-Y)
            state["before"] = p
            pawn.add_movement_input(unreal.Vector(0, -1, 0), 1.0, False)
            state.update(phase="walk", t=time.monotonic(), walk_until=time.monotonic() + 2.5)
        elif state["phase"] == "walk":
            state["pawn"].add_movement_input(unreal.Vector(0, -1, 0), 1.0, False)
            if time.monotonic() > state["walk_until"]:
                p, b = state["pawn"].get_actor_location(), state["before"]
                check("camina_adentro", b.y - p.y > 150 and abs(p.z - b.z) < 40, avanzo_cm=round(b.y - p.y), z=round(p.z))
                finish()
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error("[OFICINA_PLAY] " + report["error"])
        finish()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
