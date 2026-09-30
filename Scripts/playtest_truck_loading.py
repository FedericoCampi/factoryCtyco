"""PIE: carga de 10 cajas en el camion por la cinta (Cinta_Carga + Camion_Recorrido).

1. El camion para en la cinta (antes de la barrera) y abre la puerta hacia afuera y arriba.
2. Con una caja en mano junto a la punta de carga, E (UFactoryGatheringComponent.interact) la pone en la
   cinta; la cinta la lleva y la caja entra al camion. Despues de la primera: "1/10".
3. Diez cajas: "10/10 LLENO"; una mas no entra (queda en las manos).
4. La puerta se cierra y el camion sigue hasta la barrera.
Informe: Docs/truck_loading_play.json; capturas Docs/truck_loading_play.png (con cajas) y
Docs/truck_loading_full.png. Cierra el editor. Lanzar con -ExecCmds="py <lanzador sin espacios>".
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}, "loads": []}
state = {"phase": "warmup", "t": time.monotonic(), "start": time.monotonic(), "given": 0}
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
BOX = unreal.load_asset("/Game/FactoryCtyco/Environments/DispatchBox/SM_CajaDespacho")


def phase(name):
    unreal.log(f"[LOADING_PLAY] fase {name}")
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/truck_loading_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def door_edge():
    """Borde de abajo de la puerta, respecto del camion: (hacia la derecha, altura)."""
    mesh = state["mesh"]
    edge = mesh.get_socket_location("Puerta_Borde")
    rel = edge - mesh.get_world_location()
    return round(rel.dot(mesh.get_right_vector()), 1), round(rel.z, 1)


def roof_scale():
    return round(state["mesh"].get_bone_scale_by_name("Techo", unreal.BoneSpaces.COMPONENT_SPACE).x, 3)


def look_at_cargo():
    """Pone al personaje al costado de la puerta, para que la camara mire la carga."""
    mesh, pawn = state["mesh"], state["pawn"]
    spot = mesh.get_world_location() + mesh.get_forward_vector() * 60.0 - mesh.get_right_vector() * 330.0
    pawn.set_actor_location(unreal.Vector(spot.x, spot.y, pawn.get_actor_location().z), False, True)


def stand_at_belt():
    belt = state["belt"]
    load = belt.get_actor_location() - belt.get_actor_forward_vector() * 60.0
    pawn = state["pawn"]
    pawn.set_actor_location(unreal.Vector(load.x, load.y, pawn.get_actor_location().z), False, True)


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
    if time.monotonic() - state["start"] > 200 and state["phase"] != "quit":
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
        belts = unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryLoadingBelt)
        trucks = unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryVehiclePath)
        check("hay_cinta_y_camion", len(belts) == 1 and len(trucks) == 1, belts=len(belts), trucks=len(trucks))
        state.update(pawn=pawn, belt=belts[0], truck=trucks[0], mesh=trucks[0].get_editor_property("vehicle"),
                     gathering=pawn.get_component_by_class(unreal.FactoryGatheringComponent))
        state["closed_edge"] = door_edge()
        check("techo_con_la_puerta_cerrada", roof_scale() > 0.99, scale=roof_scale())
        phase("dock")
    elif name == "dock":
        truck = state["truck"]
        if truck.is_docked() and truck.get_door_openness() >= 1.0:
            belt = state["belt"]
            end = belt.get_actor_transform().transform_location(unreal.Vector(belt.get_editor_property("length"), 0, belt.get_editor_property("deck_height")))
            mesh = state["mesh"]
            door_centre = mesh.get_world_location() + mesh.get_forward_vector() * truck.get_editor_property("cargo_door_offset")
            along = (end - door_centre).dot(mesh.get_forward_vector())
            check("para_con_la_puerta_en_la_cinta", abs(along) < 15, off_cm=round(along, 1))
            gate = unreal.GameplayStatics.get_all_actors_of_class(state["truck"].get_world(), unreal.FactoryGateBarrier)
            if gate:
                arm = gate[0].get_editor_property("arm").get_world_location()
                front = mesh.get_world_location() + mesh.get_forward_vector() * truck.get_editor_property("front_length")
                check("para_antes_de_la_barrera", (arm - front).dot(mesh.get_forward_vector()) > 150,
                      gap_cm=round((arm - front).dot(mesh.get_forward_vector())))
            check("sin_techo_con_la_puerta_abierta", roof_scale() < 0.01, scale=roof_scale())
            open_edge = door_edge()
            closed = state["closed_edge"]
            # la puerta esta a la izquierda (-derecha): abierta, su borde sale hacia afuera y sube
            # bisagra abajo: el borde de arriba baja a la altura de la bisagra y sale ~113 cm hacia afuera
            check("puerta_se_rebate_hacia_afuera", open_edge[0] < closed[0] - 90 and open_edge[1] < closed[1] - 90,
                  closed=closed, open=open_edge)
            phase("load")
        elif age > 40:
            check("para_en_la_cinta", False, docked=truck.is_docked(), door=truck.get_door_openness())
    elif name == "load":
        truck, belt = state["truck"], state["belt"]
        carry = state["pawn"].get_component_by_class(unreal.FactoryCarryComponent)
        if truck.get_cargo_count() >= 5 and "shot5" not in state:
            state["shot5"] = True
            look_at_cargo()
            phase("shotaim")
            return
        if state["given"] < 10:
            if not carry.is_carrying():
                carry.take(BOX)
            stand_at_belt()
            before = belt.get_box_count()
            state["gathering"].interact()
            if belt.get_box_count() > before:
                state["given"] += 1
                report["loads"].append(round(time.monotonic() - state["t"], 1))
            if state["given"] == 1 and "primera" not in state:
                state["primera"] = True
                phase("first")
        elif truck.get_cargo_count() >= 10:
            counter = truck.get_editor_property("counter")
            check("diez_de_diez", str(counter.get_editor_property("text")) == "10/10 LLENO",
                  text=str(counter.get_editor_property("text")))
            if not carry.is_carrying():
                carry.take(BOX)
            stand_at_belt()
            state["gathering"].interact()
            check("una_mas_no_entra", carry.is_carrying() and belt.get_box_count() == 0 and truck.get_cargo_count() == 10)
            state["docked_at"] = state["mesh"].get_world_location()
            look_at_cargo()
            phase("fullaim")
        elif age > 60:
            check("diez_de_diez", False, cargo=truck.get_cargo_count(), given=state["given"])
    elif name == "shotaim" and age > 1.0:
        print("[captura desactivada]", 1280, 720, str(project / "Docs/truck_loading_play.png"))
        phase("shotwait")
    elif name == "shotwait" and age > 1.5:
        phase("load")
    elif name == "first":
        truck = state["truck"]
        if truck.get_cargo_count() >= 1:
            counter = truck.get_editor_property("counter")
            check("primera_caja_1_de_10", str(counter.get_editor_property("text")) == "1/10"
                  and not counter.get_editor_property("hidden_in_game"), text=str(counter.get_editor_property("text")))
            phase("load")
        elif age > 10:
            check("primera_caja_1_de_10", False, cargo=truck.get_cargo_count())
    elif name == "fullaim" and age > 0.8:
        print("[captura desactivada]", 1280, 720, str(project / "Docs/truck_loading_full.png"))
        phase("leave")
    elif name == "leave":
        truck = state["truck"]
        moved = (state["mesh"].get_world_location() - state["docked_at"]).length()
        if not truck.is_docked() and truck.get_door_openness() <= 0.0 and moved > 100:
            check("cierra_y_sigue", True, moved_cm=round(moved))
            check("techo_vuelve_al_cerrar", roof_scale() > 0.99, scale=roof_scale())
            report["passed"] = True
            finish()
        elif age > 20:
            check("cierra_y_sigue", False, docked=truck.is_docked(), door=truck.get_door_openness(), moved_cm=round(moved))
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal.log("[LOADING_PLAY] registrado")
