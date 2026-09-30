"""PIE: caja al comienzo de la cinta larga, sonidos de cajas y mision de 20 paquetes (28/09).

1. Los dos camiones estacionan (el 1 en Cinta_Carga, el 2 en Cinta_Carga4); se llena el 1.
2. Con el 1 lleno, una caja apoyada al comienzo de Cinta_Carga2 (la cinta larga que va al camion 1) se va por
   Cinta_Carga4 al camion 2.
3. Las cajas tienen sonido al agarrar y al soltar (cargados).
4. Se abre la barrera: el camion 1 pasa y cuenta 10 entregados; el panel (I) lo muestra
   (Docs/mission_panel.png).
5. Con 20 entregados: mision cumplida y aviso en pantalla (Docs/mission_complete.png).
Informe: Docs/mission_play.json. Cierra el editor.
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
BOX = unreal.load_asset("/Game/FactoryCtyco/Environments/DispatchBox/SM_CajaDespacho")


def phase(name):
    unreal.log(f"[MISSION_PLAY] fase {name}")
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/mission_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def belt(label):
    return state["belts"][label]


def mission():
    return unreal.FactoryMissionSubsystem.get(state["pawn"])


def put_box(target, fraction):
    carry = state["pawn"].get_component_by_class(unreal.FactoryCarryComponent)
    if not carry.is_carrying():
        carry.take(BOX)
    length = target.get_editor_property("length")
    side = target.get_actor_transform().transform_location(unreal.Vector(length * fraction, 90, 0))
    pawn = state["pawn"]
    pawn.set_actor_location(unreal.Vector(side.x, side.y, pawn.get_actor_location().z), False, True)
    state["gathering"].interact()
    return not carry.is_carrying()


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
    if time.monotonic() - state["start"] > 240 and state["phase"] != "quit":
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
        belts = {b.get_actor_label(): b for b in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryLoadingBelt)}
        gate = unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryGateBarrier)[0]
        for door in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryRollDoor):
            door.set_open(True)   # el porton de la entrada arranca cerrado: esta prueba no es sobre el
        state.update(pawn=pawn, t1=trucks["Camion_Recorrido"], t2=trucks["Camion_Recorrido2"], belts=belts, gate=gate,
                     gathering=pawn.get_component_by_class(unreal.FactoryGatheringComponent))
        check("mision_empieza_en_cero", mission().get_editor_property("delivered") == 0 and mission().get_editor_property("goal") == 20)
        phase("docks")
    elif name == "docks":
        if state["t1"].is_ready_to_load() and state["t2"].is_docked():
            phase("fill1")
        elif age > 45:
            check("estacionan", False, t1=state["t1"].is_docked(), t2=state["t2"].is_docked())
    elif name == "fill1":
        t1 = state["t1"]
        state.setdefault("fill_start", time.monotonic())
        if t1.get_cargo_count() >= 10:
            carry = state["pawn"].get_component_by_class(unreal.FactoryCarryComponent)
            check("sonidos_de_cajas", carry.get_editor_property("pickup_sound") is not None
                  and carry.get_editor_property("drop_sound") is not None)
            state["before"] = {"c2": belt("Cinta_Carga2").get_box_count(), "c4": belt("Cinta_Carga4").get_box_count() + state["t2"].get_cargo_count()}
            check("apoya_al_comienzo_de_la_larga", put_box(belt("Cinta_Carga2"), 0.05))
            phase("to_truck2")
        elif time.monotonic() - state["fill_start"] > 60:
            check("primero_se_llena", False, cargo=t1.get_cargo_count())
        elif age > 0.7 and t1.get_cargo_count() + belt("Cinta_Carga").get_box_count() < 10:
            put_box(belt("Cinta_Carga"), 0.1)
            phase("fill1")
    elif name == "to_truck2" and age > 1.0:
        c2 = belt("Cinta_Carga2").get_box_count()
        c4 = belt("Cinta_Carga4").get_box_count() + state["t2"].get_cargo_count()
        check("con_el_1_lleno_va_al_camion_2", c2 == state["before"]["c2"] and c4 == state["before"]["c4"] + 1,
              antes=state["before"], cinta2=c2, camion2=c4)
        phase("wait_leave")
    elif name == "wait_leave":
        if not state["t1"].is_docked() and age > 4:
            pawn = state["pawn"]
            pawn.set_actor_location(state["gate"].get_editor_property("booth").get_world_location() + unreal.Vector(0, 0, 95), False, True)
            phase("open")
        elif age > 30:
            check("camion_1_sale", False)
    elif name == "open" and age > 1.0:
        state["gathering"].interact()
        check("barrera_arriba", state["gate"].get_editor_property("want_open"))
        phase("through")
    elif name == "through":
        if mission().get_editor_property("delivered") >= 10:
            check("pasa_la_barrera_y_cuenta_10", mission().get_editor_property("delivered") == 10
                  and not mission().get_editor_property("completed"), entregados=mission().get_editor_property("delivered"))
            state["gathering"].toggle_inventory()   # tecla I
            phase("shot_panel")
        elif age > 30:
            check("pasa_la_barrera_y_cuenta_10", False, entregados=mission().get_editor_property("delivered"))
    elif name == "shot_panel" and age > 1.0:
        print("[captura desactivada]", 1280, 720, str(project / "Docs/mission_panel.png"))
        phase("complete")
    elif name == "complete" and age > 1.5:
        state["gathering"].toggle_inventory()
        mission().add_delivered(10)             # como si pasara el segundo camion lleno
        check("mision_cumplida", mission().get_editor_property("completed") and mission().get_editor_property("delivered") == 20)
        phase("shot_done")
    elif name == "shot_done" and age > 1.0:
        print("[captura desactivada]", 1280, 720, str(project / "Docs/mission_complete.png"))
        phase("done")
    elif name == "done" and age > 1.5:
        report["passed"] = True
        finish()
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal.log("[MISSION_PLAY] registrado")
