"""Prueba en Play (04/10), con L_FactoryDemo abierto en el editor: el techo del ascensor.

Pone al personaje dentro de la cabina de Ascensor_Fabrica: con la camara isometrica el techo se esconde (se ve adentro
desde arriba); en primera persona (V) el techo queda puesto. Afuera, en cualquier vista, el techo esta.
Las paredes tienen el relleno (Panels) y, al viajar, el techo sube o baja junto con el piso.
No guarda nada. Corre en el tick del editor (puente MCP). Informe: Docs/ascensor_techo_play.json.
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


def finish():
    report["passed"] = bool(report["checks"]) and all(c["passed"] for c in report["checks"].values()) and "error" not in report
    (docs / "ascensor_techo_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    unreal.unregister_slate_post_tick_callback(state["handle"])
    if unreal.EditorLevelLibrary.get_pie_worlds(False):
        levels.editor_request_end_play()


def roof_visible():
    return state["lift"].get_editor_property("roof").is_visible()


def tick(delta):
    try:
        age = time.monotonic() - state["t"]
        if time.monotonic() - state["start"] > 90:
            raise RuntimeError("La prueba tardo demasiado")
        phase = state["phase"]
        if phase == "start":
            levels.editor_request_begin_play()
            state.update(phase="spawn", t=time.monotonic())
        elif phase == "spawn" and age > 4:
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            pawn = unreal.GameplayStatics.get_player_character(worlds[0], 0) if worlds else None
            if pawn is None:
                return
            lift = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryElevator)
                        if a.get_actor_label() == "Ascensor_Fabrica")
            cam = pawn.get_component_by_class(unreal.FactoryCameraComponent)
            state.update(pawn=pawn, lift=lift, cam=cam)
            loc = lift.get_actor_location()
            pawn.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + 100), False, True)
            state.update(phase="iso", t=time.monotonic())
        elif phase == "iso" and age > 0.5:
            report["checks"]["isometrica_adentro_sin_techo"] = dict(passed=state["lift"].in_cabin(state["pawn"]) and not roof_visible(),
                                                                    adentro=state["lift"].in_cabin(state["pawn"]), techo=roof_visible())
            state["cam"].set_first_person(True)
            state.update(phase="fp", t=time.monotonic())
        elif phase == "fp" and age > 0.5:
            report["checks"]["primera_persona_adentro_con_techo"] = dict(passed=roof_visible(), techo=roof_visible(),
                                                                          primera_persona=state["cam"].is_first_person())
            state["cam"].set_first_person(False)
            loc = state["lift"].get_actor_location()
            state["pawn"].set_actor_location(unreal.Vector(loc.x - 600, loc.y, loc.z + 100), False, True)
            state.update(phase="out", t=time.monotonic())
        elif phase == "out" and age > 0.5:
            report["checks"]["afuera_con_techo"] = dict(passed=roof_visible(), techo=roof_visible())
            # paredes cerradas y el techo baja con el piso en el viaje
            lift = state["lift"]
            report["checks"]["paredes_cerradas"] = dict(passed=lift.get_editor_property("panels").static_mesh is not None)
            loc = lift.get_actor_location()
            state["pawn"].set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + 100), False, True)
            state.update(phase="board", t=time.monotonic())
        elif phase == "board" and age > 0.6:
            lift = state["lift"]
            lift.try_interact(state["pawn"])   # E: el panel de pisos
            started = lift.select_floor(1 if lift.get_floor_number() != 1 else 2)
            report["checks"]["viaje_empieza"] = dict(passed=started)
            state.update(phase="ride", t=time.monotonic(), roof_z=[], floor_z=[])
        elif phase == "ride":
            lift = state["lift"]
            state["roof_z"].append(lift.get_editor_property("roof").get_editor_property("relative_location").z)
            state["floor_z"].append(lift.get_editor_property("platform").get_editor_property("relative_location").z)
            if age > 3.5:
                pairs = list(zip(state["roof_z"], state["floor_z"]))
                moved = max(abs(f) for _, f in pairs) > 50
                together = all(abs(r - f) < 0.5 for r, f in pairs)
                report["checks"]["techo_viaja_con_el_piso"] = dict(passed=moved and together,
                                                                   piso_max_cm=round(max(abs(f) for _, f in pairs), 1))
                finish()
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error("[ASCENSOR_TECHO] " + report["error"])
        finish()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
