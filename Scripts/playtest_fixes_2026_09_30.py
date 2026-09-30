"""PIE en el editor abierto (no carga el mapa ni cierra el editor): pedidos del 30/09.

1. La flecha del paso 1 esta sobre Ascensor_Empleados.
2. Puerta_Recepcion se abre hacia adentro de la sala (gira +OpenYaw) cuando el gerente se acerca.
3. Cinta_Carga3 sigue derecho a Cinta_Carga4 (el tramo en L esta bloqueado) y el camion estaciona en Cinta_Carga4.
4. Una caja apoyada en Cinta_Carga3 termina dentro del camion.
Informe: Docs/fixes_2026_09_30_play.json.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}}
state = {"phase": "start", "t": time.monotonic(), "start": time.monotonic()}
BOX = unreal.load_asset("/Game/FactoryCtyco/Environments/DispatchBox/SM_CajaDespacho")


def phase(name):
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/fixes_2026_09_30_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
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
    name = state["phase"]
    if time.monotonic() - state["start"] > 180 and name != "quit":
        raise RuntimeError("La prueba no termino a tiempo")
    if name == "start":
        levels.editor_request_begin_play()
        phase("spawn")
    elif name == "spawn":
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0) if worlds else None
        if pawn is None or age < 2:
            return
        world = worlds[0]
        by = lambda cls: {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(world, cls)}
        guide = list(by(unreal.FactoryGuide).values())[0]
        guide.call_method("SkipIntro")
        belts, trucks = by(unreal.FactoryLoadingBelt), by(unreal.FactoryVehiclePath)
        lift = by(unreal.FactoryElevator)["Ascensor_Empleados"]
        state.update(pawn=pawn, world=world, belts=belts, truck=trucks["Camion_Recorrido"], door=by(unreal.FactoryAutoDoor)["Puerta_Recepcion"],
                     gathering=pawn.get_component_by_class(unreal.FactoryGatheringComponent))
        step1 = guide.get_editor_property("steps")[0]
        origin, extent = lift.get_actor_bounds(True)
        check("flecha_sobre_el_ascensor", step1.get_editor_property("arrow_target") == lift and guide.get_step_index() == 0,
              arrow_target=step1.get_editor_property("arrow_target").get_actor_label(), step=guide.get_step_index(),
              arrow_at=[round(origin.x), round(origin.y), round(origin.z + extent.z + guide.get_editor_property("arrow_height"))])
        for door in by(unreal.FactoryRollDoor).values():
            door.set_open(True)   # el porton de camiones arranca cerrado: esta prueba no es sobre el
        outs = {k: sorted(o.get_actor_label() for o in v.get_outputs()) for k, v in belts.items() if not v.tags}
        check("cinta_derecho", outs.get("Cinta_Carga3") == ["Cinta_Carga4"] and outs.get("Cinta_Carga4") == [], outputs=outs)
        door = state["door"]
        state["closed_yaw"] = door.get_actor_rotation().yaw
        # delante de la puerta, del lado de la plataforma
        middle = door.get_actor_transform().transform_location(unreal.Vector(-door.get_editor_property("width") / 2, -120, 0))
        pawn.set_actor_location(unreal.Vector(middle.x, middle.y, middle.z + 100), False, True)
        phase("door")
    elif name == "door" and age > 1.6:
        door = state["door"]
        turned = door.get_actor_rotation().yaw - state["closed_yaw"]
        check("puerta_hacia_adentro", abs(turned - door.get_editor_property("open_yaw")) < 2 and door.get_editor_property("open_yaw") > 0,
              turned=round(turned, 1), open_yaw=door.get_editor_property("open_yaw"), openness=round(door.get_openness(), 2))
        phase("truck")
    elif name == "truck":
        truck = state["truck"]
        if truck.is_docked():
            check("camion_para_en_la_cinta_derecha", truck.get_dock_belt().get_actor_label() == "Cinta_Carga4",
                  belt=truck.get_dock_belt().get_actor_label(), along=round(truck.get_distance_along()))
            state["cargo"] = truck.get_cargo_count()
            belt = state["belts"]["Cinta_Carga3"]
            carry = state["pawn"].get_component_by_class(unreal.FactoryCarryComponent)
            if not carry.is_carrying():
                carry.take(BOX)
            side = belt.get_actor_transform().transform_location(unreal.Vector(belt.get_editor_property("length") * 0.3, 90, 0))
            state["pawn"].set_actor_location(unreal.Vector(side.x, side.y, side.z + 100), False, True)
            state["gathering"].interact()
            check("caja_en_la_cinta", belt.get_box_count() == 1, count=belt.get_box_count())
            phase("load")
        elif age > 90:
            check("camion_para_en_la_cinta_derecha", False, docked=False, along=round(truck.get_distance_along()),
                  gate=truck.get_waiting_gate().get_actor_label() if truck.get_waiting_gate() else None)
    elif name == "load":
        truck = state["truck"]
        if truck.get_cargo_count() > state["cargo"]:
            check("caja_llega_al_camion", True, cargo=truck.get_cargo_count(), seconds=round(age, 1))
            report["passed"] = True
            finish()
        elif age > 25:
            check("caja_llega_al_camion", False, cargo=truck.get_cargo_count(), counts={k: v.get_box_count() for k, v in state["belts"].items()})
    elif name == "quit" and age > 1:
        unreal.unregister_slate_post_tick_callback(state["handle"])


state["handle"] = unreal.register_slate_post_tick_callback(tick)
