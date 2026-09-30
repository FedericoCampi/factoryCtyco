"""PIE: el camion (Camion_Recorrido, AFactoryVehiclePath) recorre su linea y las ruedas ruedan hacia adelante.

Comprueba: arranca en el primer punto; avanza a su velocidad; el eje trasero queda sobre la linea;
el frente apunta al sentido de marcha; un punto de arriba de cada rueda se mueve hacia adelante (giro
en el sentido correcto) y al final vuelve a empezar. Informe: Docs/vehicle_path_play.json. Cierra el editor.
Lanzar con -ExecCmds="py <lanzador sin espacios en la ruta>" (ver Docs/ESTACIONAMIENTO.md).
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}}
state = {"phase": "warmup", "t": time.monotonic(), "start": time.monotonic(), "spins": []}
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
WHEELS = ("Rueda_DI", "Rueda_DD", "Rueda_TI", "Rueda_TD")


def phase(name):
    unreal.log(f"[VEHICLE_PLAY] fase {name}")
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def v(x):
    return [round(x.x, 1), round(x.y, 1), round(x.z, 1)]


def finish():
    (project / "Docs/vehicle_path_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
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
        found = unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryVehiclePath) if worlds else []
        if not found:
            return
        truck = found[0]
        state.update(truck=truck, mesh=truck.get_editor_property("vehicle"), path=truck.get_editor_property("path"),
                     play=time.monotonic())
        first = state["path"].get_location_at_spline_point(0, unreal.SplineCoordinateSpace.WORLD)
        start = state["mesh"].get_world_location()
        check("arranca_en_el_primer_punto", (start - first).length() < 60, start=v(start), first=v(first))
        phase("drive")
    elif name == "drive":
        truck, mesh, path = state["truck"], state["mesh"], state["path"]
        now = {w: mesh.get_socket_transform(w, unreal.RelativeTransformSpace.RTS_WORLD) for w in WHEELS}
        prev = state.get("prev")
        if prev:
            forward = mesh.get_forward_vector()
            for w in WHEELS:
                # punto de la rueda que en el cuadro anterior estaba arriba de su centro
                up_local = prev[w].rotation.unrotate_vector(unreal.Vector(0, 0, 1))
                moved = now[w].rotation.rotate_vector(up_local)
                state["spins"].append(moved.dot(forward))
        state["prev"] = now
        if age > 4 and "on_line" not in report["checks"]:
            loc = mesh.get_world_location()
            closest = path.find_location_closest_to_world_location(loc, unreal.SplineCoordinateSpace.WORLD)
            speed = truck.get_editor_property("speed")
            travelled = path.get_distance_along_spline_at_location(loc, unreal.SplineCoordinateSpace.WORLD) \
                if hasattr(path, "get_distance_along_spline_at_location") else None
            check("sobre_la_linea", (loc - closest).length() < 5, loc=v(loc), closest=v(closest))
            report["checks"]["on_line"] = {"passed": True}
            tangent = path.find_direction_closest_to_world_location(loc, unreal.SplineCoordinateSpace.WORLD)
            check("mira_hacia_adelante", mesh.get_forward_vector().dot(tangent) > 0.95,
                  forward=v(mesh.get_forward_vector()), tangent=v(tangent))
            check("avanza", travelled is None or abs(travelled - speed * age) < speed * 1.0,
                  travelled=travelled, expected=round(speed * age))
            spins = state["spins"]
            check("ruedas_giran_hacia_adelante", len(spins) > 20 and sum(1 for s in spins if s > 0.01) > 0.9 * len(spins),
                  samples=len(spins), forward=sum(1 for s in spins if s > 0.01), backward=sum(1 for s in spins if s < -0.01))
            report["length_cm"] = round(path.get_spline_length())
            state["last"] = path.get_spline_length()
            phase("loop")
    elif name == "loop":
        mesh, path = state["mesh"], state["path"]
        first = path.get_location_at_spline_point(0, unreal.SplineCoordinateSpace.WORLD)
        seconds = state["last"] / state["truck"].get_editor_property("speed")
        if (mesh.get_world_location() - first).length() < 300 and age > 2:
            check("vuelve_a_empezar", True, after_s=round(time.monotonic() - state["play"], 1), trip_s=round(seconds, 1))
            report["passed"] = True
            finish()
        elif age > seconds + 10:
            check("vuelve_a_empezar", False, waited_s=round(age, 1))
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal.log("[VEHICLE_PLAY] registrado")
