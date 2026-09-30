"""PIE: cabina con barrera (Cabina_Barrera) y el camion (Camion_Recorrido).

1. Afuera de la cabina, E no hace nada con la barrera.
2. El camion frena y queda quieto antes de la barrera baja, sin tocarla.
3. El personaje entra a la cabina: el techo se oculta; E levanta la barrera (con UFactoryGatheringComponent.interact,
   el mismo camino que la tecla).
4. El camion arranca, pasa, y la barrera baja sola cuando termino de pasar.
Informe: Docs/gate_booth_play.json; captura Docs/gate_booth_play.png. Cierra el editor.
Lanzar con -ExecCmds="py <lanzador sin espacios en la ruta>".
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
    unreal.log(f"[GATE_PLAY] fase {name}")
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/gate_booth_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def front_gap():
    """Del paragolpes del camion al brazo de la barrera, a lo largo de su marcha (cm)."""
    mesh, gate = state["mesh"], state["gate"]
    front = mesh.get_world_location() + mesh.get_forward_vector() * state["truck"].get_editor_property("front_length")
    arm = gate.get_editor_property("arm").get_world_location()
    return (arm - front).dot(mesh.get_forward_vector())


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
    if time.monotonic() - state["start"] > 170 and state["phase"] != "quit":
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
        gates = unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryGateBarrier)
        trucks = unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryVehiclePath)
        check("hay_cabina_y_camion", len(gates) == 1 and len(trucks) == 1, gates=len(gates), trucks=len(trucks))
        state.update(pawn=pawn, gate=gates[0], truck=trucks[0], mesh=trucks[0].get_editor_property("vehicle"),
                     gathering=pawn.get_component_by_class(unreal.FactoryGatheringComponent))
        state["gathering"].interact()   # donde arranca el personaje, lejos de la cabina
        check("e_afuera_no_abre", not state["gate"].get_editor_property("want_open"))
        phase("approach")
    elif name == "approach":
        loc = state["mesh"].get_world_location()
        last = state.get("last")
        state["last"] = loc
        if last is not None and (loc - last).length() < 0.01 and age > 5:
            state.setdefault("still_since", time.monotonic())
            if time.monotonic() - state["still_since"] > 1.5:
                gap = front_gap()
                check("frena_antes_de_la_barrera", 0 < gap < 200, gap_cm=round(gap, 1))
                check("barrera_baja", state["gate"].get_editor_property("openness") < 0.01)
                phase("enter")
        else:
            state.pop("still_since", None)
        if age > 40:
            check("frena_antes_de_la_barrera", False, waited_s=round(age), gap_cm=round(front_gap(), 1))
    elif name == "enter" and age > 0.5:
        booth = state["gate"].get_editor_property("booth")
        inside = booth.get_world_location() + unreal.Vector(0, 0, 95)
        state["pawn"].set_actor_location(inside, False, True)
        phase("press")
    elif name == "press" and age > 1.0:
        gate = state["gate"]
        check("adentro_de_la_cabina", gate.is_inside(state["pawn"]))
        check("techo_oculto", gate.get_editor_property("roof").get_editor_property("hidden_in_game"))
        state["gathering"].interact()
        check("e_levanta", gate.get_editor_property("want_open"))
        phase("raise")
    elif name == "raise" and age > 2.5:
        gate = state["gate"]
        check("barrera_arriba", gate.is_open(), openness=round(gate.get_editor_property("openness"), 3))
        state["before"] = state["mesh"].get_world_location()
        print("[captura desactivada]", 1280, 720, str(project / "Docs/gate_booth_play.png"))
        phase("pass")
    elif name == "pass":
        gate = state["gate"]
        moved = (state["mesh"].get_world_location() - state["before"]).length()
        if gate.get_editor_property("vehicle_under"):
            state["was_under"] = True
        if state.get("was_under") and not gate.get_editor_property("want_open"):
            check("el_camion_pasa", moved > 500, moved_cm=round(moved))
            check("baja_sola_despues", front_gap() < -200, gap_cm=round(front_gap()))
            phase("lower")
        elif age > 25:
            check("baja_sola_despues", False, moved_cm=round(moved), under=state.get("was_under", False))
    elif name == "lower" and age > 2.5:
        check("barrera_abajo", state["gate"].get_editor_property("openness") < 0.01)
        report["passed"] = True
        finish()
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal.log("[GATE_PLAY] registrado")
