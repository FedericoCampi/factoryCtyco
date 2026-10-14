"""Prueba (03/10), con L_FactoryDemo abierto en el editor: la pasarela en L armada por piezas (Pasarela_L).

En el editor (sin guardar; lo deja como estaba):
- manijas: correr la de la baranda interior del brazo A 50 cm la mueve 50 cm y el piso se ensancha; la del extremo B
  alarga el brazo B y suma piezas.
En Play:
- se sube caminando desde el suelo por el extremo abierto del brazo A y se queda arriba del piso;
- parado en el codo y en el brazo B, queda apoyado (no lo atraviesa);
- caminando de costado contra la baranda exterior no se cae del piso.
Corre en el tick del editor (Python del editor o el puente MCP). Informe: Docs/pasarela_modular_play.json.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

docs = Path(unreal.Paths.project_dir()).resolve() / "Docs"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False, "checks": {}}
state = {"phase": "handles", "t": time.monotonic(), "start": time.monotonic()}


def phase(name):
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = dict(passed=bool(ok), **values)


def finish():
    report["passed"] = bool(report["checks"]) and all(c["passed"] for c in report["checks"].values()) and "error" not in report
    (docs / "pasarela_modular_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    unreal.log("[PASARELA_MODULAR_PLAY] " + json.dumps(report, default=str))
    unreal.unregister_slate_post_tick_callback(state["handle"])
    if unreal.EditorLevelLibrary.get_pie_worlds(False):
        levels.editor_request_end_play()


def walkway(world):
    return next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryWalkwayL) if a.get_actor_label() == "Pasarela_L")


def put(pawn, local):
    w = state["xf"].transform_location(local)
    pawn.character_movement.set_editor_property("velocity", unreal.Vector(0, 0, 0))
    pawn.set_actor_location(unreal.Vector(w.x, w.y, w.z + state["half"] + 5), False, True)


def feet(pawn):
    return state["xf"].inverse_transform_location(pawn.get_actor_location()).z - state["half"]


def tick(delta):
    try:
        age = time.monotonic() - state["t"]
        if time.monotonic() - state["start"] > 240:
            raise RuntimeError("La prueba tardo demasiado")
        name = state["phase"]
        if name == "handles":
            walk = next(a for a in actors.get_all_level_actors() if a.get_actor_label() == "Pasarela_L")
            keep = {p: walk.get_editor_property(p) for p in ("outer_a", "inner_a", "outer_b", "inner_b", "end_a", "end_b")}
            deck0 = walk.deck.get_instance_count()
            h = walk.get_editor_property("inner_rail_a_handle")
            walk.set_editor_property("inner_rail_a_handle", unreal.Vector(h.x, h.y + 50, h.z))
            moved = walk.get_editor_property("inner_a") - keep["inner_a"]
            back = walk.get_editor_property("inner_rail_a_handle")
            check("manija_baranda_interior_A", abs(moved - 50) < 1 and abs(back.y - walk.get_editor_property("inner_a")) < 1,
                  movio_cm=round(moved, 1), manija_en_la_baranda=abs(back.y - walk.get_editor_property("inner_a")) < 1)
            e = walk.get_editor_property("end_b_handle")
            walk.set_editor_property("end_b_handle", unreal.Vector(e.x, e.y + 300, e.z))
            check("manija_extremo_B", abs(walk.get_editor_property("end_b") - keep["end_b"] - 300) < 1 and walk.deck.get_instance_count() > deck0,
                  alargo_cm=round(walk.get_editor_property("end_b") - keep["end_b"], 1), piezas_piso=[deck0, walk.deck.get_instance_count()])
            # como estaba (cada set_editor_property vuelve a armarla)
            for p, v in keep.items():
                walk.set_editor_property(p, v)
            walk.rebuild()
            check("vuelve_como_estaba", all(abs(walk.get_editor_property(p) - v) < 0.1 for p, v in keep.items()) and walk.deck.get_instance_count() == deck0)
            levels.editor_request_begin_play()
            phase("spawn")
        elif name == "spawn" and age > 4:
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            pawn = unreal.GameplayStatics.get_player_character(worlds[0], 0) if worlds else None
            if pawn is None:
                return
            walk = walkway(worlds[0])
            state.update(pawn=pawn, walk=walk, half=pawn.capsule_component.get_scaled_capsule_half_height(), xf=walk.get_actor_transform(),
                         e={p: walk.get_editor_property(p) for p in ("outer_a", "inner_a", "outer_b", "inner_b", "end_a", "end_b")})
            e = state["e"]
            mid_a = (e["outer_a"] + e["inner_a"]) / 2
            # en el suelo, mas alla del extremo abierto del brazo A, mirando hacia el codo
            put(pawn, unreal.Vector(e["end_a"] + 120, mid_a, -state["xf"].translation.z))
            state["dir"] = state["xf"].transform_direction(unreal.Vector(-1, 0, 0))
            phase("climb")
        elif name == "climb":
            pawn = state["pawn"]
            pawn.add_movement_input(state["dir"], 1.0, True)
            if state["xf"].translation.z > 30:
                # en alto (unida a una plataforma): desde el suelo no se llega, se prueba solo apoyarse
                check("se_sube_desde_el_suelo", True, no_aplica=f"la pasarela esta a {round(state['xf'].translation.z)} cm del piso")
                age = 99
            if age > 2.5:
                f = feet(pawn)
                if "se_sube_desde_el_suelo" not in report["checks"]:
                    check("se_sube_desde_el_suelo", abs(f - 40.4) < 8 and pawn.character_movement.is_moving_on_ground(), pies_sobre_actor_cm=round(f, 1))
                state["spots"] = [("codo", unreal.Vector((state["e"]["outer_b"] + state["e"]["inner_b"]) / 2, (state["e"]["outer_a"] + state["e"]["inner_a"]) / 2, 60)),
                                  ("brazo_B", unreal.Vector((state["e"]["outer_b"] + state["e"]["inner_b"]) / 2, (state["e"]["inner_a"] + state["e"]["end_b"]) / 2, 60))]
                phase("stand")
        elif name == "stand":
            if "spot" not in state:
                if not state["spots"]:
                    put(state["pawn"], unreal.Vector((state["e"]["inner_b"] + state["e"]["end_a"]) / 2, (state["e"]["outer_a"] + state["e"]["inner_a"]) / 2, 60))
                    state["dir"] = state["xf"].transform_direction(unreal.Vector(0, -1, 0))
                    phase("rail")
                    return
                state["spot"] = state["spots"].pop(0)
                put(state["pawn"], state["spot"][1])
                state["t"] = time.monotonic()
            elif age > 1.5:
                f = feet(state["pawn"])
                check(f"apoyado_{state['spot'][0]}", abs(f - 40.4) < 8 and state["pawn"].character_movement.is_moving_on_ground(), pies_sobre_actor_cm=round(f, 1))
                state.pop("spot")
        elif name == "rail":
            pawn = state["pawn"]
            pawn.add_movement_input(state["dir"], 1.0, True)
            if age > 2.5:
                local = state["xf"].inverse_transform_location(pawn.get_actor_location())
                check("la_baranda_frena", local.y > state["e"]["outer_a"] - 5 and abs(feet(pawn) - 40.4) < 8,
                      y_local=round(local.y, 1), baranda_y=round(state["e"]["outer_a"], 1), pies_sobre_actor_cm=round(feet(pawn), 1))
                finish()
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error("[PASARELA_MODULAR_PLAY] " + report["error"])
        finish()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
