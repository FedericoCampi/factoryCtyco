"""PIE: cintas de la fabrica estiradas, inclinadas, en altura y en esquina (30/09). No guarda nada y cierra el editor.

Arma (solo para la prueba, en el piso del laboratorio, lejos de la linea de la fabrica) una cadena:
deposito de chatarra -> cinta recta estirada x1,5 que sube 10 grados -> esquina (DB_BeltCorner) -> cinta recta en
altura -> deposito. Cada pieza se pone con su entrada justo en la salida de la anterior.
1. Cada pieza encuentra a la siguiente (entrada en la salida).
2. Hay postes bajo lo que quedo en el aire (esquina y cinta alta); la cinta que sube tiene poste en su punta alta.
3. La chatarra del primer deposito llega al ultimo, pasando por la esquina (la carga gira con la curva).
4. La cinta estirada tarda mas que una normal (0,8 s por cada 2 m).
Lanzar con -ExecCmds="py <lanzador sin espacios>". Informe: Docs/factory_belts_play.json.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"passed": False, "checks": {}, "cargo_yaw_on_corner": []}
state = {"phase": "warmup", "t": time.monotonic(), "start": time.monotonic()}
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
DEFS = "/Game/FactoryCtyco/Factory/Definitions"
d = {n: unreal.load_asset(f"{DEFS}/DB_{n}") for n in ("Storage", "Belt", "BeltCorner")}
START = unreal.Vector(3300, -300, 4)   # piso del laboratorio
TEST = []


def put(label, definition, rotation, scale, after):
    """Pone una pieza con su entrada en la salida de `after` (o en START)."""
    a = actors.spawn_actor_from_class(unreal.FactoryBuilding, unreal.Vector(0, 0, 0), rotation)
    a.set_actor_label(label)
    a.set_editor_property("persistent_id", "Prueba_" + label)
    a.set_editor_property("definition", definition)
    a.set_editor_property("storage_item", "Scrap")
    a.set_actor_scale3d(scale)
    a.refresh_visuals()
    target = after.output_point() if after else START + unreal.Vector(0, 0, 33)
    a.set_actor_location(a.get_actor_location() + (target - a.input_point()), False, False)
    a.refresh_visuals()
    TEST.append(a)
    return a


s1 = put("S1", d["Storage"], unreal.Rotator(0, 0, 0), unreal.Vector(1, 1, 1), None)
b1 = put("B1", d["Belt"], unreal.Rotator(roll=0, pitch=10, yaw=0), unreal.Vector(1.5, 1, 1), s1)
c1 = put("C1", d["BeltCorner"], unreal.Rotator(0, 0, 0), unreal.Vector(1, 1, 1), b1)
b2 = put("B2", d["Belt"], unreal.Rotator(0, 0, -90), unreal.Vector(1, 1, 1), c1)
s2 = put("S2", d["Storage"], unreal.Rotator(0, 0, -90), unreal.Vector(1, 1, 1), b2)
report["layout"] = {a.get_actor_label(): {"in": [round(v) for v in a.input_point().to_tuple()], "out": [round(v) for v in a.output_point().to_tuple()]}
                    for a in TEST}


def phase(name):
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/factory_belts_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
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
    if time.monotonic() - state["start"] > 200 and name != "quit":
        raise RuntimeError("La prueba no termino a tiempo")
    if name == "warmup" and age > 8:
        levels.editor_request_begin_play()
        phase("spawn")
    elif name == "spawn":
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds or age < 2:
            return
        w = worlds[0]
        pie = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.FactoryBuilding)}
        factory = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.FactoryDemoWorld)[0]
        state.update(p=pie, factory=factory)
        # 1. cada pieza tiene a la siguiente pegada (el mundo lo marca en bConnected en su primer paso)
        chain = ["S1", "B1", "C1", "B2"]
        check("enganches", all(pie[n].get_editor_property("connected") for n in chain),
              connected={n: pie[n].get_editor_property("connected") for n in chain + ["S2"]})
        # 2. postes
        posts = {n: pie[n].get_component_by_class(unreal.InstancedStaticMeshComponent).get_instance_count() for n in ("B1", "C1", "B2")}
        check("postes", posts["C1"] >= 1 and posts["B2"] >= 1 and posts["B1"] >= 1, postes=posts,
              alto_cm={n: round(pie[n].get_actor_location().z) for n in ("B1", "C1", "B2")})
        # 4. tiempos
        times = {n: round(pie[n].travel_seconds(), 2) for n in ("B1", "C1", "B2")}
        check("tiempos", abs(times["B2"] - 0.8) < 0.05 and times["B1"] > 1.1, segundos=times)
        pie["S1"].input.add_item(factory.resource("Scrap"), 6)
        phase("flow")
    elif name == "flow":
        p = state["p"]
        corner = p["C1"]
        if corner.cargo.is_visible():
            report["cargo_yaw_on_corner"].append(round(corner.cargo.get_editor_property("relative_rotation").yaw))
        got = p["S2"].input.get_quantity("Scrap")
        if got >= 3:
            yaws = report["cargo_yaw_on_corner"]
            check("llega_al_final", True, en_el_deposito=got, segundos=round(age, 1))
            check("gira_en_la_esquina", yaws and min(yaws) < -45, giros=sorted(set(yaws))[:12])
            report["passed"] = True
            finish()
        elif age > 40:
            check("llega_al_final", False, en_el_deposito=got,
                  cargas={n: p[n].input.get_total() for n in ("S1", "B1", "C1", "B2", "S2")},
                  estados={n: p[n].get_editor_property("state_text") for n in ("B1", "C1", "B2")})
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        for a in TEST:
            actors.destroy_actor(a)
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
