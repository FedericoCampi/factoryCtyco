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
def floor_spot(*offsets):
    """El primer lugar (START + offset) con piso a la altura de START debajo de toda la cinta."""
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for off in offsets:
        if any(abs(off.x - u.x) < 300 and abs(off.y - u.y) < 300 for u in USED):
            continue
        ok = True
        for dx in (-120, 0, 120):
            for dy in (-80, 80):
                top = START + off + unreal.Vector(dx, dy, 400)
                hit = unreal.SystemLibrary.line_trace_single(w, top, top - unreal.Vector(0, 0, 800), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
                ok = ok and bool(hit) and abs(hit.to_tuple()[4].z - START.z) < 20
        if ok:
            USED.append(off)
            return START + off
    raise RuntimeError("No hay piso libre para las cintas sueltas de la prueba")


USED = []
SPOTS = [unreal.Vector(x, y, 0) for y in (600, 900, -900, 1200) for x in (300, 0, 600, -300)]
# una cinta suelta estirada en Z (como en el editor): tiene que quedar arriba sobre patas, sin estirarse
tall = actors.spawn_actor_from_class(unreal.FactoryBuilding, floor_spot(*SPOTS), unreal.Rotator(0, 0, 0))   # dentro del piso del laboratorio
tall.set_actor_label("Alta")
tall.set_editor_property("persistent_id", "Prueba_Alta")
tall.set_editor_property("definition", d["Belt"])
tall.set_actor_scale3d(unreal.Vector(1, 1, 4))
TEST.append(tall)
# una cinta elevada e inclinada 15 grados con la propiedad Slope (01/10): sube alrededor de su centro
TILT_SPOT = floor_spot(*SPOTS)
tilted = actors.spawn_actor_from_class(unreal.FactoryBuilding, TILT_SPOT, unreal.Rotator(0, 0, 0))
tilted.set_actor_label("Inclinada")
tilted.set_editor_property("persistent_id", "Prueba_Inclinada")
tilted.set_editor_property("definition", d["Belt"])
tilted.set_editor_property("elevation", 100.0)
tilted.set_editor_property("slope", 15.0)
TEST.append(tilted)
# otra igual, inclinada arrastrando la manija de su salida 36,4 cm hacia arriba (tan 20 grados x 100 cm)
HANDLE_SPOT = floor_spot(*SPOTS)
handled = actors.spawn_actor_from_class(unreal.FactoryBuilding, HANDLE_SPOT, unreal.Rotator(0, 0, 0))
handled.set_actor_label("Manija")
handled.set_editor_property("persistent_id", "Prueba_Manija")
handled.set_editor_property("definition", d["Belt"])
handled.set_editor_property("elevation", 100.0)
handled.set_editor_property("output_end_handle", unreal.Vector(100, 0, 133 + 36.4))
TEST.append(handled)
# un horno (FactoryRaisedProp) a escala 2,25 estirado en Z a 2,25 x 1,25: sube y la base de abajo se estira (01/10)
OVEN_SPOT = floor_spot(*SPOTS)
oven = actors.spawn_actor_from_class(unreal.FactoryRaisedProp, OVEN_SPOT, unreal.Rotator(0, 0, 0))
oven.set_actor_label("HornoPrueba")
oven.set_editor_property("body_mesh", unreal.load_asset("/Game/FactoryCtyco/Environments/HornoFundicion/SM_HornoFundicion_Cuerpo"))
oven.set_editor_property("base_mesh", unreal.load_asset("/Game/FactoryCtyco/Environments/HornoFundicion/SM_HornoFundicion_Base"))
oven.set_actor_scale3d(unreal.Vector(2.25, 2.25, 2.25 * 1.25))
oven.refresh()
TEST.append(oven)
report["layout"] = {a.get_actor_label(): {"in": [round(v) for v in a.input_point().to_tuple()], "out": [round(v) for v in a.output_point().to_tuple()]}
                    for a in TEST if isinstance(a, unreal.FactoryBuilding)}


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
        check("postes", posts["C1"] >= 2 and posts["B2"] >= 2 and posts["B1"] >= 2, postes=posts,
              alto_cm={n: round(pie[n].get_actor_location().z) for n in ("B1", "C1", "B2")})
        # 4. tiempos
        tall = pie["Alta"]
        legs = tall.get_component_by_class(unreal.InstancedStaticMeshComponent).get_instance_count()
        check("estirar_en_z_sube_sobre_patas", abs(tall.get_actor_scale3d().z - 1) < 0.01 and abs(tall.get_editor_property("elevation") - 102) < 1
              and legs == 4 and tall.get_component_by_class(unreal.BoxComponent).get_editor_property("relative_location").z > 100,
              escala_z=tall.get_actor_scale3d().z, elevacion=tall.get_editor_property("elevation"), patas=legs)
        # sin plataforma: en altura va sobre patas (01/10); la cinta del nivel (x5) lleva 8 patas, la esquina 4
        level_legs = {n: pie[n].get_component_by_class(unreal.InstancedStaticMeshComponent).get_instance_count()
                      for n in ("Cinta_Fabrica_1", "Cinta_Fabrica_Esquina")}
        bases = {n: str(pie[n].get_editor_property("base").static_mesh) for n in ("Alta", "Cinta_Fabrica_1")}
        check("sin_plataforma_y_menos_patas", all(v == "None" for v in bases.values()) and level_legs["Cinta_Fabrica_1"] == 8
              and level_legs["Cinta_Fabrica_Esquina"] == 4, plataformas=bases, patas_nivel=level_legs)
        tl = pie["Inclinada"]
        rise = tl.output_point().z - tl.input_point().z
        mid = (tl.output_point() + tl.input_point()) / 2 - TILT_SPOT
        pitch = tl.get_actor_rotation().pitch
        check("inclinacion_slope", abs(rise - 200 * 0.2588) < 3 and abs(mid.z - 133) < 3 and abs(mid.x) < 3 and abs(pitch - 15) < 0.5,
              sube_cm=round(rise, 1), centro_cm=[round(v, 1) for v in mid.to_tuple()], pitch_actor=round(pitch, 1),
              patas=tl.get_component_by_class(unreal.InstancedStaticMeshComponent).get_instance_count())
        hd = pie["Manija"]
        hmid = (hd.output_point() + hd.input_point()) / 2 - HANDLE_SPOT
        back = hd.get_editor_property("output_end_handle")
        check("inclinacion_con_manija", abs(hd.get_editor_property("slope") - 20) < 0.5 and abs(hd.get_actor_rotation().pitch - 20) < 0.5
              and abs(hmid.z - 133) < 3 and abs(back.z - 133) < 1 and abs(back.x - 100) < 1,
              slope=round(hd.get_editor_property("slope"), 1), centro_cm=[round(v, 1) for v in hmid.to_tuple()], manija_vuelve_a=back.to_tuple())
        ov = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.FactoryRaisedProp) if a.get_actor_label() == "HornoPrueba")
        base_top = ov.base.get_world_transform().transform_location(unreal.Vector(0, 0, 10)).z - OVEN_SPOT.z
        base_bottom = ov.base.get_world_transform().transform_location(unreal.Vector(0, 0, 0)).z - OVEN_SPOT.z
        body_z = ov.body.get_world_location().z - OVEN_SPOT.z
        # 0,25 de escala de mas x 10 cm de base = 2,5 cm... en el mundo: (2,8125 - 2,25) x 10 = 5,6 cm de elevacion
        check("horno_elevable", abs(ov.get_actor_scale3d().z - 2.25) < 0.01 and abs(ov.get_editor_property("elevation") - 5.625) < 0.1
              and abs(body_z - 5.625) < 0.5 and abs(base_top - (22.5 + 5.625)) < 0.5 and abs(base_bottom) < 0.5,
              escala_z=ov.get_actor_scale3d().z, elevacion=ov.get_editor_property("elevation"), cuerpo_cm=round(body_z, 2),
              base_cm=[round(base_bottom, 2), round(base_top, 2)])
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
