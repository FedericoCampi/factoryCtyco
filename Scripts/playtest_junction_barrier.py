"""PIE: cajas en la union de cintas sin encimarse, y la barrera del otro lado del carril (28/09).

1. Con el porton cerrado (ningun camion carga) se llena Cinta_Carga y se ponen cajas en Cinta_Carga2: la caja que
   espera al final de Cinta_Carga2 queda a una caja de distancia de la primera de Cinta_Carga (no se enciman).
   Captura Docs/junction_boxes.png.
2. Se abre el porton; el camion 1 carga esas cajas (y las que faltan), sale y frena antes de la barrera,
   que ahora esta del lado norte del carril.
Informe: Docs/junction_barrier_play.json. Cierra el editor.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}}
state = {"phase": "warmup", "t": time.monotonic(), "start": time.monotonic(), "put": 0}
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
BOX = unreal.load_asset("/Game/FactoryCtyco/Environments/DispatchBox/SM_CajaDespacho")


def phase(name):
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/junction_barrier_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def belt(label):
    return state["belts"][label]


def box_positions(target):
    return [c.get_world_location() for c in target.get_components_by_class(unreal.StaticMeshComponent)
            if c.static_mesh and c.static_mesh.get_name() == "SM_CajaDespacho"]


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
        trucks = {t.get_actor_label(): t for t in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryVehiclePath)}
        belts = {b.get_actor_label(): b for b in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryLoadingBelt)}
        state.update(pawn=pawn, t1=trucks["Camion_Recorrido"], belts=belts,
                     door=unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryRollDoor)[0],
                     gathering=pawn.get_component_by_class(unreal.FactoryGatheringComponent))
        phase("fill_last")
    elif name == "fill_last":
        # Cinta_Carga llena (sin camion), despues 3 cajas en Cinta_Carga2 que se acumulan contra ella
        if state["put"] < 7 and age > 1.0:
            put_box(belt("Cinta_Carga"), 0.08)
            state["put"] += 1
            phase("fill_last")
        elif state["put"] >= 7 and age > 1.0:
            state["put"] = 0
            phase("feed")
    elif name == "feed":
        if state["put"] < 3 and age > 1.2:
            put_box(belt("Cinta_Carga2"), 0.3)
            state["put"] += 1
            phase("feed")
        elif state["put"] >= 3 and age > 9:
            a, b = box_positions(belt("Cinta_Carga2")), box_positions(belt("Cinta_Carga"))
            gaps = [(p - q).length() for p in a for q in b]
            check("no_se_enciman_en_la_union", gaps and min(gaps) >= 55, min_gap_cm=round(min(gaps), 1) if gaps else None,
                  en_cinta2=len(a), en_cinta=len(b))
            spot = belt("Cinta_Carga").get_actor_location()
            pawn = state["pawn"]
            pawn.set_actor_location(unreal.Vector(spot.x - 250, spot.y - 150, pawn.get_actor_location().z), False, True)
            phase("shot")
    elif name == "shot" and age > 1.0:
        print("[captura desactivada]", 1280, 720, str(project / "Docs/junction_boxes.png"))
        state["door"].set_open(True)
        phase("load")
    elif name == "load":
        t1 = state["t1"]
        state.setdefault("load_start", time.monotonic())
        if t1.get_cargo_count() >= 10 and not t1.is_docked():
            phase("barrier")
        elif time.monotonic() - state["load_start"] > 80:
            check("camion_se_llena", False, cargo=t1.get_cargo_count())
        elif t1.is_ready_to_load() and age > 1.0 and t1.get_cargo_count() + sum(len(box_positions(belt(l))) for l in ("Cinta_Carga", "Cinta_Carga2")) < 10:
            put_box(belt("Cinta_Carga"), 0.1)
            phase("load")
    elif name == "barrier":
        gate = state["t1"].get_waiting_gate()
        if gate is not None:
            check("frena_en_la_barrera_nueva", gate.get_class().get_name() == "FactoryGateBarrier")
            report["passed"] = True
            finish()
        elif age > 25:
            check("frena_en_la_barrera_nueva", False)
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
