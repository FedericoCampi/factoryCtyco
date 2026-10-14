"""Prueba en Play (04/10), con L_FactoryDemo abierto en el editor: el pasillo en L de la puerta del muelle.

El personaje arranca en el anden, delante de la puerta de personal del bloque este (Man door 1), entra, baja la rampa
del tramo 1, dobla al oeste por el tramo 2 y tiene que terminar adentro del edificio del muelle, sobre su piso (o
sobre la losa del estacionamiento que entra en el edificio, 20 cm mas alta: los muelles estan a z -10).
Medidas en metros del GLB (author_muelles.py), pasadas al mundo con la transformacion de `Muelles_Carga`.
Corre en el tick del editor (Python del editor o el puente MCP). Informe: Docs/pasillo_muelle_play.json.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

docs = Path(unreal.Paths.project_dir()).resolve() / "Docs"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}, "path": []}
state = {"phase": "start", "t": time.monotonic(), "start": time.monotonic()}
# (direccion en el GLB, segundos): adentro por el tramo 1 (+y del GLB) y al oeste por el tramo 2 (-x)
LEGS = [((0, 1), 3.2), ((-1, 0), 2.5)]


def phase(name):
    state.update(phase=name, t=time.monotonic())


def finish():
    report["passed"] = bool(report["checks"]) and all(c["passed"] for c in report["checks"].values()) and "error" not in report
    (docs / "pasillo_muelle_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    unreal.unregister_slate_post_tick_callback(state["handle"])
    if unreal.EditorLevelLibrary.get_pie_worlds(False):
        levels.editor_request_end_play()


def tick(delta):
    try:
        age = time.monotonic() - state["t"]
        if time.monotonic() - state["start"] > 90:
            raise RuntimeError("La prueba tardo demasiado")
        if state["phase"] == "start":
            levels.editor_request_begin_play()
            phase("spawn")
        elif state["phase"] == "spawn" and age > 4:
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            pawn = unreal.GameplayStatics.get_player_character(worlds[0], 0) if worlds else None
            if pawn is None:
                return
            docks = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.StaticMeshActor)
                         if a.get_actor_label() == "Muelles_Carga")
            xf = docks.get_actor_transform()
            half = pawn.capsule_component.get_scaled_capsule_half_height()
            to_world = lambda x, y, z: xf.transform_location(unreal.Vector(x * 100, -y * 100, z * 100))
            to_glb = lambda w: (lambda l: (l.x / 100, -l.y / 100, l.z / 100))(xf.inverse_transform_location(w))
            start = to_world(12.2, 13.0, 1.2)
            pawn.set_actor_location(unreal.Vector(start.x, start.y, start.z + half + 5), False, True)
            state.update(pawn=pawn, xf=xf, half=half, to_glb=to_glb, to_world=to_world, leg=0)
            phase("walk")
        elif state["phase"] == "walk":
            pawn = state["pawn"]
            (gx, gy), seconds = LEGS[state["leg"]]
            d = state["xf"].transform_direction(unreal.Vector(gx * 100, -gy * 100, 0))
            pawn.add_movement_input(d, 1.0, True)
            g = state["to_glb"](pawn.get_actor_location() - unreal.Vector(0, 0, state["half"]))
            report["path"].append([round(c, 2) for c in g]) if len(report["path"]) < 400 and int(age * 10) % 3 == 0 else None
            if age > seconds:
                state["leg"] += 1
                state["t"] = time.monotonic()
                if state["leg"] == len(LEGS):
                    g = state["to_glb"](pawn.get_actor_location() - unreal.Vector(0, 0, state["half"]))
                    inside = -17.6 < g[0] < 9.9 and 14.0 < g[1] < 22.0
                    report["checks"]["sale_adentro_del_edificio"] = {
                        "passed": inside and abs(g[2]) < 0.3 and pawn.character_movement.is_moving_on_ground(),
                        "pies_glb_m": [round(c, 2) for c in g]}
                    finish()
    except Exception:
        report["error"] = traceback.format_exc()
        finish()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
