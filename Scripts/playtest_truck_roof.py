"""PIE: capturas del techo del camion con la tapa cerrada (andando: con techo) y abierta (en la cinta: sin techo).

Docs/truck_roof_closed.png y Docs/truck_roof_open.png; informe Docs/truck_roof_play.json. Cierra el editor.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "samples": []}
state = {"phase": "warmup", "t": time.monotonic(), "start": time.monotonic()}
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")


def phase(name):
    state.update(phase=name, t=time.monotonic())


def finish():
    (project / "Docs/truck_roof_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def sample(tag):
    t, mesh = state["truck"], state["truck"].get_editor_property("vehicle")
    report["samples"].append({"tag": tag, "door": round(t.get_door_openness(), 2),
                              "roof_hidden": mesh.is_bone_hidden_by_name("Techo"),
                              "roof_loc": str(mesh.get_bone_location_by_name("Techo", unreal.BoneSpaces.COMPONENT_SPACE)),
                              "roof_cs": str(mesh.get_bone_transform_by_name("Techo", unreal.BoneSpaces.COMPONENT_SPACE)),
                              })


def near_truck(side=350.0):
    mesh = state["truck"].get_editor_property("vehicle")
    spot = mesh.get_world_location() + mesh.get_forward_vector() * 150 - mesh.get_right_vector() * side
    pawn = state["pawn"]
    pawn.set_actor_location(unreal.Vector(spot.x, spot.y, pawn.get_actor_location().z), False, True)


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
        state.update(pawn=pawn, truck=trucks["Camion_Recorrido"])
        phase("drive")
    elif name == "drive" and age > 6.0:
        near_truck()
        phase("shot_closed")
    elif name == "shot_closed" and age > 0.3:
        sample("cerrada")
        print("[captura desactivada]", 1280, 720, str(project / "Docs/truck_roof_closed.png"))
        phase("wait_dock")
    elif name == "wait_dock":
        if state["truck"].get_door_openness() >= 1.0:
            near_truck()
            phase("shot_open")
        elif age > 30:
            report["error"] = "no abrio"
            finish()
    elif name == "shot_open" and age > 0.8:
        sample("abierta")
        print("[captura desactivada]", 1280, 720, str(project / "Docs/truck_roof_open.png"))
        phase("done")
    elif name == "done" and age > 1.5:
        report["passed"] = True
        finish()
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
