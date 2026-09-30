"""PIE: reparto de cajas entre cintas y panel del personaje (28/09).

Cintas: Cinta_Carga3 termina donde empiezan Cinta_Carga2 (-> Cinta_Carga, camion de adelante) y Cinta_Carga4
(otro camion).
1. Sin camiones las cintas aceptan cajas y en el cruce van por la rama del camion de adelante (izquierda).
2. Con el primer camion esperando en Cinta_Carga (y el segundo todavia no), las cajas van hacia el.
3. Primer camion lleno: una caja mas en Cinta_Carga igual se acepta (espera al proximo) y las del cruce siguen
   derecho hacia el segundo camion.
4. Tecla I: panel de informacion (bienvenida y opcion de silenciar); M silencia y devuelve el sonido.
   Captura Docs/character_panel.png.
Informe: Docs/belt_routing_play.json. Cierra el editor.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}, "log": []}
state = {"phase": "warmup", "t": time.monotonic(), "start": time.monotonic()}
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
BOX = unreal.load_asset("/Game/FactoryCtyco/Environments/DispatchBox/SM_CajaDespacho")


def phase(name):
    unreal.log(f"[ROUTING_PLAY] fase {name}")
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/belt_routing_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def belt(label):
    return state["belts"][label]


def put_box(target, fraction):
    carry = state["pawn"].get_component_by_class(unreal.FactoryCarryComponent)
    if not carry.is_carrying():
        carry.take(BOX)
    length = target.get_editor_property("length")
    side = target.get_actor_transform().transform_location(unreal.Vector(length * fraction, 90, 0))
    pawn = state["pawn"]
    pawn.set_actor_location(unreal.Vector(side.x, side.y, pawn.get_actor_location().z), False, True)
    before = target.get_box_count()
    state["gathering"].interact()
    return target.get_box_count() > before


def counts():
    return {k: v.get_box_count() for k, v in state["belts"].items()}


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
        for door in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryRollDoor):
            door.set_open(True)   # el porton de la entrada arranca cerrado: esta prueba no es sobre el
        state.update(pawn=pawn, t1=trucks["Camion_Recorrido"], t2=trucks["Camion_Recorrido2"], belts=belts,
                     gathering=pawn.get_component_by_class(unreal.FactoryGatheringComponent))
        outs = {k: sorted(o.get_actor_label() for o in v.get_outputs()) for k, v in belts.items()}
        check("cruce_con_dos_salidas", outs["Cinta_Carga3"] == ["Cinta_Carga2", "Cinta_Carga4"]
              and outs["Cinta_Carga2"] == ["Cinta_Carga"] and outs["Cinta_Carga"] == [] and outs["Cinta_Carga4"] == [], outputs=outs)
        state["put"] = 0
        phase("no_trucks")
    elif name == "no_trucks":
        # 1. dos cajas sin ningun camion estacionado
        if state["put"] < 2 and age > 1.2 * (state["put"] + 1):
            check("acepta_sin_camion", put_box(belt("Cinta_Carga3"), 0.3), camiones=[state["t1"].is_docked(), state["t2"].is_docked()])
            state["put"] += 1
        elif state["put"] >= 2 and belt("Cinta_Carga3").get_box_count() == 0:
            c = counts()
            # sin camiones esperan en la rama de adelante (la del camion mas cerca de la barrera)
            check("sin_camion_van_por_la_de_adelante", c["Cinta_Carga2"] + c["Cinta_Carga"] == 2 and c["Cinta_Carga4"] == 0, counts=c)
            phase("wait_first")
        elif age > 20:
            check("sin_camion_van_por_la_de_adelante", False, counts=counts())
    elif name == "wait_first":
        t1, t2 = state["t1"], state["t2"]
        if t1.is_docked() and not t2.is_docked():
            state["main_before"] = belt("Cinta_Carga2").get_box_count() + belt("Cinta_Carga").get_box_count() + t1.get_cargo_count()
            state["put"] = 0
            phase("prefer_waiting")
        elif age > 30:
            info = lambda t: {"dist": round(t.get_distance_along()), "belt": t.get_dock_belt().get_actor_label() if t.get_dock_belt() else None,
                              "docked": t.is_docked(), "cargo": t.get_cargo_count(), "loc": str(t.get_editor_property("vehicle").get_world_location())}
            check("primer_camion_solo", False, t1=info(t1), t2=info(t2))
    elif name == "prefer_waiting":
        # 2. con el primer camion esperando, 2 cajas mas al cruce
        if state["put"] < 2 and age > 1.2 * (state["put"] + 1):
            put_box(belt("Cinta_Carga3"), 0.3)
            state["put"] += 1
        elif state["put"] >= 2 and belt("Cinta_Carga3").get_box_count() == 0:
            report["log"].append({"despues_del_cruce": counts(), "t2_docked": state["t2"].is_docked()})
            main = belt("Cinta_Carga2").get_box_count() + belt("Cinta_Carga").get_box_count() + state["t1"].get_cargo_count()
            check("van_al_camion_que_espera", main == state["main_before"] + 2, before=state["main_before"], after=main, counts=counts())
            phase("fill1")
        elif age > 20:
            check("van_al_camion_que_espera", False, counts=counts())
    elif name == "leftover":
        # 3. el segundo camion llega y carga la sobrante de Cinta_Carga4
        if state["t2"].get_cargo_count() >= 1:
            check("segundo_carga_la_sobrante", True, cargo=state["t2"].get_cargo_count())
            phase("fill1")
        elif age > 40:
            check("segundo_carga_la_sobrante", False, cargo=state["t2"].get_cargo_count(), docked=state["t2"].is_docked(), counts=counts())
    elif name == "fill1":
        t1 = state["t1"]
        state.setdefault("fill_start", time.monotonic())
        if t1.get_cargo_count() >= 10:
            # 4. lleno: la cinta igual acepta una caja mas (queda esperando); donde haya lugar
            state.setdefault("full_at", time.monotonic())
            if put_box(belt("Cinta_Carga"), 0.5):
                check("acepta_con_camion_lleno", True, cargo=t1.get_cargo_count(), en_cinta=belt("Cinta_Carga").get_box_count())
                state["c4_before"] = belt("Cinta_Carga4").get_box_count() + state["t2"].get_cargo_count()
                phase("to_other")
            elif time.monotonic() - state["full_at"] > 4:
                check("acepta_con_camion_lleno", False, cargo=t1.get_cargo_count(), counts=counts())
        elif time.monotonic() - state["fill_start"] > 60:
            check("primero_se_llena", False, cargo=t1.get_cargo_count())
        elif age > 1.0 and t1.get_cargo_count() + belt("Cinta_Carga").get_box_count() + belt("Cinta_Carga2").get_box_count() < 10:
            put_box(belt("Cinta_Carga"), 0.1)
            phase("fill1")
    elif name == "to_other":
        if age > 3.5 and "sent" not in state:
            state["sent"] = put_box(belt("Cinta_Carga3"), 0.3)
        if state.get("sent") and belt("Cinta_Carga3").get_box_count() == 0 and age > 7:
            after = belt("Cinta_Carga4").get_box_count() + state["t2"].get_cargo_count()
            check("lleno_sigue_derecho_al_otro", after == state["c4_before"] + 1, before=state["c4_before"], after=after, counts=counts())
            state["gathering"].toggle_inventory()   # tecla I
            state["gathering"].toggle_mute()        # tecla M
            hud = unreal.GameplayStatics.get_player_controller(state["pawn"].get_world(), 0).get_hud()
            check("m_silencia", hud.is_muted())
            phase("panel")
        elif age > 25:
            check("lleno_sigue_derecho_al_otro", False, counts=counts())
    elif name == "panel" and age > 1.0:
        print("[captura desactivada]", 1280, 720, str(project / "Docs/character_panel.png"))
        phase("done")
    elif name == "done" and age > 1.5:
        state["gathering"].toggle_mute()
        hud = unreal.GameplayStatics.get_player_controller(state["pawn"].get_world(), 0).get_hud()
        check("m_devuelve_el_sonido", not hud.is_muted())
        report["passed"] = True
        finish()
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal.log("[ROUTING_PLAY] registrado")
