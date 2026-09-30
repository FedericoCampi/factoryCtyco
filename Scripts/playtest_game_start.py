"""PIE: el nivel arranca como juego y se contrata al encargado de barrera (28/09).

1. Lo bloqueado (Despacho2: maquina, cajas y botonera de la cinta 2; Camion2: camion 2 y Cinta_Carga4) no se
   ve; el despacho 1 si. Cinta_Carga3 ya no reparte a Cinta_Carga4. El rincon de basura se ve.
   Captura Docs/rincon.png.
2. Panel I en la pestana CONTRATAR: Docs/contratar_panel.png.
3. Se contrata al encargado de barrera: llega en auto al piso 3, baja en el ascensor y camina a la cabina
   (Docs/encargado_cabina.png). Panel de la cabina (clic): Docs/cabina_panel.png.
4. Se abre el porton, el camion 1 carga 10 cajas y va a la barrera (Docs/ploteo_cerrado.png): el encargado
   la levanta solo y el camion entrega. Antes, con la puerta abierta: Docs/ploteo_abierto.png.
5. Desbloqueo de prueba: Unlock("Despacho2") -> la maquina aparece y el rincon se va.
   Captura Docs/desbloqueo_despacho2.png.
Informe: Docs/game_start_play.json. Cierra el editor.
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
LOCKED = ["Despacho_Machine2", "Despacho_Cajas2", "Botonera_Cinta2", "Camion_Recorrido2", "Cinta_Carga4"]
ACTIVE = ["Despacho_Machine", "Despacho_Cajas", "Botonera_Cinta1"]
JUNK = ["Rincon_Tablones", "Rincon_Volquete", "Rincon_Pallet", "Rincon_Bolsas"]


def phase(name):
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/game_start_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def hidden(actor):
    return bool(actor.get_editor_property("hidden"))


def shot(name):
    print("[captura desactivada]", 1280, 720, str(project / "Docs" / name))


def stand(x, y):
    pawn = state["pawn"]
    pawn.set_actor_location(unreal.Vector(x, y, pawn.get_actor_location().z), False, True)


def put_box(target, fraction):
    carry = state["pawn"].get_component_by_class(unreal.FactoryCarryComponent)
    if not carry.is_carrying():
        carry.take(BOX)
    length = target.get_editor_property("length")
    side = target.get_actor_transform().transform_location(unreal.Vector(length * fraction, 90, 0))
    stand(side.x, side.y)
    state["gathering"].interact()


def near_truck():
    spot = state["every"]["Camion_Recorrido"].vehicle.get_world_location()
    stand(spot.x + 150, spot.y + 350)


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
    if time.monotonic() - state["start"] > 330 and state["phase"] != "quit":
        raise RuntimeError("La prueba no termino a tiempo")
    name = state["phase"]
    every = state.get("every", {})
    if name == "warmup" and age > 8:
        levels.editor_request_begin_play()
        phase("spawn")
    elif name == "spawn":
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0) if worlds else None
        if pawn is None:
            return
        world = worlds[0]
        every = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)}
        controller = unreal.GameplayStatics.get_player_controller(world, 0)
        state.update(pawn=pawn, world=world, every=every, hud=controller.get_hud(),
                     door=unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryRollDoor)[0],
                     barrier=unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryGateBarrier)[0],
                     gathering=pawn.get_component_by_class(unreal.FactoryGatheringComponent))
        phase("locked")
    elif name == "locked" and age > 2:
        check("bloqueados_ocultos", all(hidden(every[l]) for l in LOCKED), estado={l: hidden(every[l]) for l in LOCKED})
        check("despacho1_activo", not any(hidden(every[l]) for l in ACTIVE))
        check("rincon_visible", all(l in every and not hidden(every[l]) for l in JUNK))
        outs = sorted(o.get_actor_label() for o in every["Cinta_Carga3"].get_outputs())
        check("cinta3_no_reparte_a_la_bloqueada", "Cinta_Carga4" not in outs, salidas=outs)
        spot = every["Rincon_Volquete"].get_actor_location()
        stand(spot.x + 380, spot.y + 120)
        phase("shot_junk")
    elif name == "shot_junk" and age > 1.5:
        shot("rincon.png")
        state["gathering"].toggle_inventory()
        state["hud"].set_info_tab(1)
        phase("shot_hire_panel")
    elif name == "shot_hire_panel" and age > 1.5:
        shot("contratar_panel.png")
        phase("close_hire_panel")
    elif name == "close_hire_panel" and age > 1.5:
        state["gathering"].toggle_inventory()
        staff = unreal.FactoryStaffSubsystem.get(state["world"])
        check("se_puede_contratar", staff.can_hire("Barrera"))
        worker = staff.hire("Barrera")
        check("contratado", worker is not None and staff.is_hired("Barrera"))
        state["worker"] = worker
        phase("walk")
    elif name == "walk":
        # llega en auto al piso 3, sube al ascensor y camina a la cabina (playtest_employee_floor.py lo sigue de cerca)
        worker = state["worker"]
        if worker.get_state() in (unreal.FactoryWorkerState.WORKING, unreal.FactoryWorkerState.ACTING):
            check("encargado_llega_a_la_cabina", state["barrier"].is_inside(worker), segundos=round(age, 1))
            spot = state["barrier"].get_actor_location()
            stand(spot.x - 250, spot.y - 280)
            phase("shot_booth")
        elif age > 90:
            loc = worker.get_actor_location()
            check("encargado_llega_a_la_cabina", False, estado=str(worker.get_state()), donde=[round(loc.x), round(loc.y), round(loc.z)])
    elif name == "shot_booth" and age > 1.5:
        shot("encargado_cabina.png")
        state["hud"].open_booth(state["barrier"])
        phase("shot_booth_panel")
    elif name == "shot_booth_panel" and age > 1.5:
        shot("cabina_panel.png")
        phase("close_booth_panel")
    elif name == "close_booth_panel" and age > 1.0:
        check("panel_cabina_abierto", state["hud"].get_open_booth() == state["barrier"])
        state["hud"].open_booth(None)
        state["door"].set_open(True)
        phase("arrive")
    elif name == "arrive":
        t1, t2 = every["Camion_Recorrido"], every["Camion_Recorrido2"]
        if t1.is_ready_to_load():
            check("camion2_no_sale", t2.get_distance_along() < 1.0, distancia=t2.get_distance_along())
            near_truck()
            phase("shot_open")
        elif age > 60:
            check("camion1_llega", False)
    elif name == "shot_open" and age > 2.0:
        shot("ploteo_abierto.png")
        phase("load_wait")
    elif name == "load_wait" and age > 2.0:
        phase("load")
    elif name == "load":
        t1 = every["Camion_Recorrido"]
        if t1.get_cargo_count() >= 10:
            state["delivered_before"] = unreal.FactoryMissionSubsystem.get(state["world"]).get_editor_property("delivered")
            phase("to_barrier")
        elif age > 1.0:
            put_box(every["Cinta_Carga"], 0.1)
            phase("load")
        if time.monotonic() - state["start"] > 250:
            check("camion_se_llena", False, carga=t1.get_cargo_count())
    elif name == "to_barrier":
        t1 = every["Camion_Recorrido"]
        if not t1.is_docked() and age > 4 and not state.get("closed_shot"):
            near_truck()
            state["closed_shot"] = time.monotonic()
        if state.get("closed_shot") and time.monotonic() - state["closed_shot"] > 1.0 and not state.get("closed_done"):
            shot("ploteo_cerrado.png")
            state["closed_done"] = True
        mission = unreal.FactoryMissionSubsystem.get(state["world"])
        if mission.get_editor_property("delivered") >= state["delivered_before"] + 10 and state.get("closed_done"):
            check("encargado_levanta_la_barrera", state["worker"].get_editor_property("handled") >= 1,
                  levantadas=state["worker"].get_editor_property("handled"))
            phase("unlock")
        elif age > 70:
            check("camion_entrega_con_el_encargado", False, handled=state["worker"].get_editor_property("handled"))
    elif name == "unlock" and age > 1.0:
        unlocks = unreal.FactoryUnlockSubsystem.get(state["world"])
        changed = unlocks.unlock("Despacho2")
        now = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(state["world"], unreal.Actor)}
        check("desbloqueo_despacho2", changed == 7 and not hidden(now["Despacho_Machine2"]) and "Rincon_Volquete" not in now,
              cambiados=changed)
        spot = now["Despacho_Machine2"].get_actor_location()
        stand(spot.x + 380, spot.y + 120)
        phase("shot_unlock")
    elif name == "shot_unlock" and age > 2.0:
        shot("desbloqueo_despacho2.png")
        report["passed"] = True
        finish()
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
