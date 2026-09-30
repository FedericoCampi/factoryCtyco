"""PIE: senal de eventos (arriba a la izquierda) y aviso de mision cumplida al estilo del panel (28/09).

1. Sin nada pendiente la senal esta en calma (0 eventos).
2. El camion 1 llega al porton cerrado: 1 evento (camion esperando en el porton).
3. Una cinta de despacho se llena: 2 eventos. Se abre el detalle (clic en la senal): Docs/events_panel.png.
4. Mision cumplida: aviso nuevo con confeti: Docs/mission_notice.png.
Informe: Docs/events_play.json. Cierra el editor.
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
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/events_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


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
    if time.monotonic() - state["start"] > 150 and state["phase"] != "quit":
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
        hud = unreal.GameplayStatics.get_player_controller(worlds[0], 0).get_hud()
        trucks = {t.get_actor_label(): t for t in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryVehiclePath)}
        belts = sorted(unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryDispatchBelt), key=lambda b: b.get_actor_label())
        state.update(pawn=pawn, hud=hud, t1=trucks["Camion_Recorrido"], belt=belts[0])
        phase("calm")
    elif name == "calm" and age > 1.0:
        check("sin_eventos_al_empezar", state["hud"].get_event_count() == 0, eventos=state["hud"].get_event_count())
        phase("door")
    elif name == "door":
        if state["t1"].get_waiting_gate() is not None and state["hud"].get_event_count() >= 1:
            check("camion_en_el_porton_es_evento", state["t1"].get_waiting_gate().get_class().get_name() == "FactoryRollDoor",
                  eventos=state["hud"].get_event_count())
            belt = state["belt"]
            belt.set_editor_property("seconds_between_boxes", 0.1)
            belt.set_belt_on(True)
            phase("belt")
        elif age > 30:
            check("camion_en_el_porton_es_evento", False, eventos=state["hud"].get_event_count())
    elif name == "belt":
        if state["belt"].get_editor_property("full") and state["hud"].get_event_count() >= 2:
            check("cinta_llena_es_evento", True, eventos=state["hud"].get_event_count())
            state["hud"].toggle_events()   # clic en la senal
            phase("shot_events")
        elif age > 60:
            check("cinta_llena_es_evento", False, eventos=state["hud"].get_event_count())
    elif name == "shot_events" and age > 1.0:
        print("[captura desactivada]", 1280, 720, str(project / "Docs/events_panel.png"))
        phase("mission")
    elif name == "mission" and age > 1.0:
        state["hud"].toggle_events()
        unreal.FactoryMissionSubsystem.get(state["pawn"]).add_delivered(20)
        phase("shot_mission")
    elif name == "shot_mission" and age > 1.3:
        print("[captura desactivada]", 1280, 720, str(project / "Docs/mission_notice.png"))
        phase("done")
    elif name == "done" and age > 1.5:
        report["passed"] = True
        finish()
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
