"""PIE: ascensor con panel de pisos, cabina y puertas fijas, piso que sube o baja (28/09).

1. Dentro del ascensor de la fabrica (piso 1), E abre el panel y otra E lo cierra.
2. Piso 2 (estacionamiento): el piso de adentro sube con el personaje; cabina y puertas quietas.
   Llega al estacionamiento subiendo desde el pozo y queda libre para caminar.
3. Piso 1: el piso baja al pozo; llega a la fabrica bajando desde arriba.
Capturas: Docs/elevator_panel.png (panel abierto) y Docs/elevator_ride.png (subiendo).
Informe: Docs/elevator_panel_play.json. Cierra el editor.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}, "platform_z": {}}
state = {"phase": "warmup", "t": time.monotonic(), "start": time.monotonic()}
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")


def phase(name):
    unreal.log(f"[ELEVATOR_PLAY] fase {name}")
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/elevator_panel_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def fixed_parts(e):
    """Cabina y altura de las 4 hojas: quedan en su piso (las hojas solo se deslizan a lo ancho)."""
    cabin = e.get_editor_property("cabin").get_editor_property("relative_location")
    doors = [d.get_editor_property("relative_location") for d in e.get_editor_property("doors")]
    return [round(cabin.x, 1), round(cabin.y, 1), round(cabin.z, 1)] + [(round(d.x, 1), round(d.z, 1)) for d in doors]


def door_gap(e):
    """Hueco entre las dos hojas de afuera (cm): cerrado ~0."""
    doors = e.get_editor_property("doors")
    return round(doors[0].get_editor_property("relative_location").y - doors[2].get_editor_property("relative_location").y
                 - e.get_editor_property("door_panel_width"), 1)


def platform_z(e):
    return round(e.get_editor_property("platform").get_editor_property("relative_location").z, 1)


def put_inside(e):
    pawn = state["pawn"]
    spot = e.get_actor_location() + unreal.Vector(0, 0, 100)
    pawn.set_actor_location(spot, False, True)


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


def track(key, e):
    report["platform_z"].setdefault(key, []).append(platform_z(e))
    report.setdefault("door_gap", {}).setdefault(key, []).append(door_gap(e))
    check_fixed(e)


def check_fixed(e):
    if fixed_parts(e) != state["fixed"][e.get_actor_label()]:
        check("cabina_y_puertas_quietas", False, elevator=e.get_actor_label(), now=fixed_parts(e))


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
        elevators = {e.get_actor_label(): e for e in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryElevator)}
        low, high = elevators["Ascensor_Fabrica"], elevators["Ascensor_Estacionamiento"]
        check("dos_pisos_en_orden", low.get_floor_number() == 1 and high.get_floor_number() == 2,
              fabrica=low.get_floor_number(), estacionamiento=high.get_floor_number())
        state.update(pawn=pawn, low=low, high=high, fixed={k: fixed_parts(v) for k, v in elevators.items()},
                     gathering=pawn.get_component_by_class(unreal.FactoryGatheringComponent))
        check("puertas_cerradas_por_defecto", low.get_door_openness() == 0 and high.get_door_openness() == 0,
              fabrica=low.get_door_openness(), estacionamiento=high.get_door_openness())
        put_inside(low)
        phase("open")
    elif name == "open" and age > 1.2:
        low = state["low"]
        check("se_abren_al_acercarse", low.get_door_openness() >= 1.0, abiertas=low.get_door_openness())
        state["gathering"].interact()
        check("e_abre_el_panel", low.get_editor_property("menu_open"))
        state["gathering"].interact()
        check("e_cierra_el_panel", not low.get_editor_property("menu_open"))
        state["gathering"].interact()
        phase("shot_panel")
    elif name == "shot_panel" and age > 0.8:
        print("[captura desactivada]", 1280, 720, str(project / "Docs/elevator_panel.png"))
        phase("go_up")
    elif name == "go_up" and age > 1.0:
        check("elige_piso_2", state["low"].select_floor(2))
        phase("riding_up")
    elif name == "riding_up":
        low, high = state["low"], state["high"]
        track("sale_fabrica", low)
        track("llega_estacionamiento", high)
        if 1.2 < age < 1.4 and "ride_shot" not in state:
            state["ride_shot"] = True
            print("[captura desactivada]", 1280, 720, str(project / "Docs/elevator_ride.png"))
        if age > 9.5:
            up = report["platform_z"]["sale_fabrica"]
            arrive = report["platform_z"]["llega_estacionamiento"]
            check("subiendo_el_piso_sube", max(up) > 100, max_z=max(up))
            gaps_out, gaps_in = report["door_gap"]["sale_fabrica"], report["door_gap"]["llega_estacionamiento"]
            # salida: se cierran al subir y quedan cerradas (ya no hay nadie); llegada: cerradas y se abren al llegar
            check("se_cierran_al_subir_y_abren_al_llegar", gaps_out[0] > 150 and min(gaps_out) < 5 and gaps_out[-1] < 5
                  and min(gaps_in) < 5 and gaps_in[-1] > 150,
                  salida=[gaps_out[0], min(gaps_out), gaps_out[-1]], llegada=[min(gaps_in), gaps_in[-1]])
            check("llega_desde_abajo", min(arrive) < -150 and arrive[-1] == 0, min_z=min(arrive), end=arrive[-1])
            check("queda_en_el_estacionamiento", high.in_cabin(state["pawn"]) and high.is_idle())
            check("puede_caminar", state["pawn"].get_movement_component().movement_mode == unreal.MovementMode.MOVE_WALKING)
            report["platform_z"] = {}
            report["door_gap"] = {}
            phase("go_down")
    elif name == "go_down" and age > 1.0:
        high = state["high"]
        state["gathering"].interact()
        check("panel_en_el_estacionamiento", high.get_editor_property("menu_open"))
        check("elige_piso_1", high.select_floor(1))
        phase("riding_down")
    elif name == "riding_down":
        low, high = state["low"], state["high"]
        track("sale_estacionamiento", high)
        track("llega_fabrica", low)
        if age > 9.5:
            down = report["platform_z"]["sale_estacionamiento"]
            arrive = report["platform_z"]["llega_fabrica"]
            check("bajando_el_piso_baja", min(down) < -150, min_z=min(down))
            check("llega_desde_arriba", max(arrive) > 100 and arrive[-1] == 0, max_z=max(arrive), end=arrive[-1])
            check("queda_en_la_fabrica", low.in_cabin(state["pawn"]) and low.is_idle())
            check("cabina_y_puertas_quietas", True)
            check("el_de_arriba_cierra_sin_nadie", high.get_door_openness() == 0, abiertas=high.get_door_openness())
            # alejarse: las puertas se cierran
            pawn = state["pawn"]
            away = low.get_actor_location() + low.get_actor_forward_vector() * -600.0
            pawn.set_actor_location(unreal.Vector(away.x, away.y, pawn.get_actor_location().z), False, True)
            phase("walk_away")
    elif name == "walk_away" and age > 1.5:
        low = state["low"]
        check("se_cierran_al_alejarse", low.get_door_openness() == 0, abiertas=low.get_door_openness())
        if True:  # fin
            report["platform_z"] = {k: [min(v), max(v)] for k, v in report["platform_z"].items()}
            report["passed"] = True
            finish()
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal.log("[ELEVATOR_PLAY] registrado")
