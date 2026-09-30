"""PIE: dos camiones, cadena de 3 cintas y cinta suelta (28/09).

1. El primer camion va a la cinta final de la cadena (Cinta_Carga), no a la suelta (Cinta_Carga4).
2. El segundo, con esa ocupada, carga en la suelta. Nunca se chocan (distancia entre ellos).
3. Una caja apoyada en el medio de Cinta_Carga3 (el comienzo de la cadena) y otra en el medio de
   Cinta_Carga2 llegan al primer camion.
4. Se llena el primero: cierra y va a la barrera. El segundo sigue en la suelta mientras el primero
   ocupa la parada; se abre la barrera, el primero sale y el segundo cierra, pasa a Cinta_Carga y
   sigue cargando ahi con lo que ya tenia.
5. Lleno el segundo, va directo a la barrera.
Informe: Docs/two_trucks_play.json; captura Docs/two_trucks_play.png. Cierra el editor.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}, "min_gap_cm": None}
state = {"phase": "warmup", "t": time.monotonic(), "start": time.monotonic()}
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
BOX = unreal.load_asset("/Game/FactoryCtyco/Environments/DispatchBox/SM_CajaDespacho")


def phase(name):
    unreal.log(f"[TWO_PLAY] fase {name}")
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/two_trucks_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def belt(label):
    return state["belts"][label]


def put_box(target, along_fraction):
    """Caja en mano, parado al costado de la cinta a esa fraccion del largo, y E."""
    carry = state["pawn"].get_component_by_class(unreal.FactoryCarryComponent)
    if not carry.is_carrying():
        carry.take(BOX)
    length = target.get_editor_property("length")
    side = target.get_actor_transform().transform_location(unreal.Vector(length * along_fraction, 90, 0))
    pawn = state["pawn"]
    pawn.set_actor_location(unreal.Vector(side.x, side.y, pawn.get_actor_location().z), False, True)
    before = target.get_box_count()
    state["gathering"].interact()
    return target.get_box_count() > before


def gap_between_trucks():
    a, b = state["t1"], state["t2"]
    front, back = (a, b) if a.get_distance_along() > b.get_distance_along() else (b, a)
    return (front.get_distance_along() - front.get_editor_property("rear_length")) - (back.get_distance_along() + back.get_editor_property("front_length"))


def dock_label(truck):
    b = truck.get_dock_belt()
    return b.get_actor_label() if b else None


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
    if time.monotonic() - state["start"] > 300 and state["phase"] != "quit":
        raise RuntimeError("La prueba no termino a tiempo")
    name = state["phase"]
    if name not in ("warmup", "spawn", "quit") and "t1" in state:
        both_moving = state["t2"].get_distance_along() > 0 and state["t1"].get_distance_along() > 0
        if both_moving:
            gap = gap_between_trucks()
            report["min_gap_cm"] = round(gap) if report["min_gap_cm"] is None else min(report["min_gap_cm"], round(gap))
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
        check("dos_camiones_y_cuatro_cintas", len(trucks) == 2 and len(belts) == 4, trucks=sorted(trucks), belts=sorted(belts))
        chain = {k: (v.get_next().get_actor_label() if v.get_next() else None) for k, v in belts.items()}
        check("cadena_de_tres", chain == {"Cinta_Carga3": "Cinta_Carga2", "Cinta_Carga2": "Cinta_Carga",
                                          "Cinta_Carga": None, "Cinta_Carga4": None}, chain=chain)
        gate = unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryGateBarrier)[0]
        state.update(pawn=pawn, t1=trucks["Camion_Recorrido"], t2=trucks["Camion_Recorrido2"], belts=belts, gate=gate,
                     gathering=pawn.get_component_by_class(unreal.FactoryGatheringComponent))
        phase("docks")
    elif name == "docks":
        t1, t2 = state["t1"], state["t2"]
        if t1.is_ready_to_load():
            if t2.is_docked() and t2.get_door_openness() >= 1.0:
                check("primero_en_la_cadena", dock_label(t1) == "Cinta_Carga", dock=dock_label(t1))
                check("segundo_en_la_suelta", dock_label(t2) == "Cinta_Carga4", dock=dock_label(t2))
                phase("chain")
        if age > 60:
            check("estacionan", False, t1=dock_label(t1), t2=dock_label(t2), d1=t1.is_docked(), d2=t2.is_docked())
    elif name == "chain":
        if "c3" not in state:
            state["c3"] = put_box(belt("Cinta_Carga3"), 0.5)
            state["c2"] = False
        elif not state["c2"] and age > 1.0:
            state["c2"] = put_box(belt("Cinta_Carga2"), 0.5)
            check("apoya_en_el_medio_de_la_cadena", state["c3"] and state["c2"])
        elif state["c2"] and state["t1"].get_cargo_count() >= 2:
            check("llegan_por_la_cadena", True, seconds=round(age, 1))
            # dos cajas en la suelta para el segundo
            state["loose"] = 0
            phase("loose")
        elif age > 40:
            check("llegan_por_la_cadena", False, cargo=state["t1"].get_cargo_count(),
                  on=[belt(l).get_box_count() for l in ("Cinta_Carga3", "Cinta_Carga2", "Cinta_Carga")])
    elif name == "loose":
        if state["loose"] < 2 and age > 0.8 * (state["loose"] + 1):
            if put_box(belt("Cinta_Carga4"), 0.2):
                state["loose"] += 1
        elif state["loose"] >= 2 and state["t2"].get_cargo_count() >= 2:
            phase("fill1")
        elif age > 30:
            check("segundo_carga_en_la_suelta", False, cargo=state["t2"].get_cargo_count())
    elif name == "fill1":
        t1 = state["t1"]
        state.setdefault("fill1_start", time.monotonic())
        if not t1.is_docked() and t1.get_cargo_count() >= 10:
            check("primero_lleno_sale", True)
            phase("blocked")
        elif time.monotonic() - state["fill1_start"] > 60:
            check("primero_lleno_sale", False, cargo=t1.get_cargo_count())
        elif age > 0.7 and t1.get_cargo_count() + belt("Cinta_Carga").get_box_count() < 10:
            put_box(belt("Cinta_Carga"), 0.1)
            phase("fill1")
    elif name == "blocked" and age > 12:
        t2 = state["t2"]
        check("segundo_espera_en_la_suelta_con_la_parada_ocupada", t2.is_docked() and dock_label(t2) == "Cinta_Carga4",
              dock=dock_label(t2), docked=t2.is_docked())
        pawn = state["pawn"]
        pawn.set_actor_location(state["gate"].get_editor_property("booth").get_world_location() + unreal.Vector(0, 0, 95), False, True)
        phase("open")
    elif name == "open" and age > 1.0:
        state["gathering"].interact()
        check("barrera_levantada", state["gate"].get_editor_property("want_open"))
        phase("move_on")
    elif name == "move_on":
        t2 = state["t2"]
        if t2.is_docked() and dock_label(t2) == "Cinta_Carga" and t2.get_door_openness() >= 1.0:
            check("segundo_pasa_a_la_siguiente", t2.get_cargo_count() >= 2, cargo=t2.get_cargo_count())
            print("[captura desactivada]", 1280, 720, str(project / "Docs/two_trucks_play.png"))
            phase("fill2")
        elif age > 60:
            check("segundo_pasa_a_la_siguiente", False, dock=dock_label(t2), docked=t2.is_docked())
    elif name == "fill2":
        t2 = state["t2"]
        state.setdefault("fill2_start", time.monotonic())
        if age > 0.7 and t2.get_cargo_count() + belt("Cinta_Carga").get_box_count() < 10:
            put_box(belt("Cinta_Carga"), 0.1)
            state["t"] = time.monotonic()
        if not t2.is_docked() and t2.get_cargo_count() >= 10:
            check("segundo_lleno_va_a_la_barrera", True)
            check("nunca_se_chocan", report["min_gap_cm"] is None or report["min_gap_cm"] > 0, min_gap_cm=report["min_gap_cm"])
            report["passed"] = True
            finish()
        elif time.monotonic() - state["fill2_start"] > 60:
            check("segundo_lleno_va_a_la_barrera", False, cargo=t2.get_cargo_count(), docked=t2.is_docked())
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal.log("[TWO_PLAY] registrado")
