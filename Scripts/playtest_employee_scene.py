"""PIE: la escena nueva del estacionamiento de empleados (piso 3, 29/09).

1. El gerente aparece parado en el patio (no cae) y el ascensor sigue teniendo 3 pisos, el 3 es EMPLEADOS.
2. El vagabundo de la esquina está acostado y animado; al acercarse dice "¿Y ella?" con su voz y levanta un brazo;
   se calla al alejarse.
3. La sala de recepción está contra la fachada: su puerta está cerrada, se abre sola hacia afuera al acercarse,
   y adentro se está parado en su piso.
4. Desde Ascensor_Empleados (en la recepción) baja al DESPACHO: la guía cumple el paso 1.
5. Dinero: se empieza con $0; sin plata suficiente no se puede contratar; contratar al de barrera cuesta $800.
3. Se contrata al encargado de barrera: entra en auto por la calle y la barrera, estaciona en el cajón F4, camina al
   ascensor (sin saltos por trabarse), baja y llega a la cabina.
Sin capturas. Informe: Docs/employee_scene_play.json. Cierra el editor.
Lanzar con -ExecCmds="py <lanzador sin espacios en la ruta>".
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}, "trip": []}
state = {"phase": "warmup", "t": time.monotonic(), "start": time.monotonic()}
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
S = unreal.FactoryWorkerState
ARRIVAL = unreal.Vector(-3270, 9780, 400)   # cajon F4 (Docs/employee_scene.json)
ORIGIN = unreal.Vector(-3800, 9000, 400)    # Empleados_Escena


def local(x, y, z):
    return ORIGIN + unreal.Vector(x * 100, -y * 100, z * 100)


def phase(name):
    unreal.log(f"[EMPLOYEE_SCENE_PLAY] fase {name}")
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/employee_scene_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def v(p):
    return [round(p.x), round(p.y), round(p.z)]


def put(p):
    state["pawn"].set_actor_location(p, False, True)


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
        state.update(pawn=pawn, world=world, every=every,
                     barrier=unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryGateBarrier)[0],
                     gathering=pawn.get_component_by_class(unreal.FactoryGatheringComponent),
                     guide=every["Guia_Mision"], z0=pawn.get_actor_location().z)
        state["guide"].call_method("SkipIntro")   # skip_intro es la propiedad bSkipIntro
        phase("standing")
    elif name == "standing" and age > 3:
        here = state["pawn"].get_actor_location()
        check("aparece_parado_en_el_patio", 400 < here.z < 560 and abs(here.z - state["z0"]) < 60, donde=v(here), z_inicial=round(state["z0"]))
        every = state["every"]
        floors = [f.get_actor_label() for f in every["Ascensor_Empleados"].get_floors()]
        check("tres_pisos", floors == ["Ascensor_Fabrica", "Ascensor_Estacionamiento", "Ascensor_Empleados"], pisos=floors)
        npc = every["Vagabundo"]
        state["npc"] = npc
        put(npc.get_actor_location() + unreal.Vector(220, 0, 100))
        phase("near_npc")
    elif name == "near_npc" and age > 1.5:
        npc = state["npc"]
        check("vagabundo_habla_al_acercarse", npc.is_talking() and npc.get_line() == "¿Y ella?" and npc.get_lines_voiced() == 1,
              linea=npc.get_line(), voces=npc.get_lines_voiced())
        check("vagabundo_levanta_el_brazo", npc.is_gesturing())
        skeletal = npc.get_editor_property("skeletal")
        check("vagabundo_animado", skeletal.get_skeletal_mesh_asset() is not None and skeletal.is_playing(),
              malla=str(skeletal.get_skeletal_mesh_asset().get_name() if skeletal.get_skeletal_mesh_asset() else None))
        put(npc.get_actor_location() + unreal.Vector(800, 0, 100))
        phase("far_npc")
    elif name == "far_npc" and age > 1.5:
        check("vagabundo_se_calla_al_alejarse", not state["npc"].is_talking())
        door = state["every"]["Puerta_Recepcion"]
        check("puerta_cerrada_de_lejos", door.get_openness() < 0.05, abierta=round(door.get_openness(), 2))
        put(local(7.55, 7.4, 3.5))            # en la plataforma, frente a la puerta de la sala
        phase("inside")
    elif name == "inside" and age > 1.5:
        door = state["every"]["Puerta_Recepcion"]
        # la hoja (hacia -X desde la bisagra) tiene que abrirse hacia afuera, sobre la plataforma: Unreal +Y
        tip = door.get_actor_transform().transform_location(unreal.Vector(-100, 0, 0))
        hinge = door.get_actor_location()
        check("puerta_se_abre_hacia_afuera", door.get_openness() > 0.95 and tip.y > hinge.y + 70,
              abierta=round(door.get_openness(), 2), punta=v(tip), bisagra=v(hinge))
        put(local(5.68, 9.6, 3.5))            # adentro de la sala, entre la entrada y el mostrador
        phase("in_room")
    elif name == "in_room" and age > 1.0:
        here = state["pawn"].get_actor_location()
        check("se_para_en_la_recepcion", 620 < here.z < 760, donde=v(here))
        put(state["every"]["Ascensor_Empleados"].get_actor_location() + unreal.Vector(0, 0, 110))
        phase("open_panel")
    elif name == "open_panel" and age > 1.5:
        state["gathering"].interact()
        phase("select")
    elif name == "select" and age > 0.8:
        check("elige_despacho", state["every"]["Ascensor_Empleados"].select_floor(2))
        phase("ride_down")
    elif name == "ride_down":
        z = state["pawn"].get_actor_location().z
        if z < 350 and age > 4 and state["guide"].get_step_index() == 1:
            check("baja_al_despacho_y_cumple_el_paso_1", True, z=round(z), segundos=round(age, 1))
            phase("hire")
        elif age > 25:
            check("baja_al_despacho_y_cumple_el_paso_1", False, z=round(z), paso=state["guide"].get_step_index())
    elif name == "hire" and age > 1.0:
        economy = unreal.FactoryEconomySubsystem.get(state["world"])
        staff = unreal.FactoryStaffSubsystem.get(state["world"])
        check("dinero_inicial", economy.get_money() == 0 and economy.get_hire_cost("Barrera") == 800,
              dinero=economy.get_money(), costo=economy.get_hire_cost("Barrera"))
        economy.earn(500, "prueba")
        check("sin_plata_no_contrata", staff.hire("Barrera") is None and economy.get_money() == 500, dinero=economy.get_money())
        economy.earn(500, "prueba")
        worker = staff.hire("Barrera")
        check("contratar_cuesta_800", worker is not None and economy.get_money() == 200, dinero=economy.get_money())
        check("contratado_llega_en_auto", worker is not None and worker.get_state() == S.DRIVING)
        state.update(worker=worker, last_state=None, state_at=time.monotonic())
        phase("follow")
    elif name == "follow":
        worker = state["worker"]
        now = worker.get_state()
        if now != state["last_state"]:
            report["trip"].append({"estado": str(now).split(".")[-1].split(":")[0], "a_los_s": round(time.monotonic() - state["state_at"], 1),
                                   "donde": v(worker.get_actor_location())})
            if now == S.WALKING and state["last_state"] == S.DRIVING:
                car = worker.get_editor_property("car").get_actor_location()
                gap = ((car.x - ARRIVAL.x) ** 2 + (car.y - ARRIVAL.y) ** 2) ** 0.5
                check("estaciona_en_el_cajon_F4", gap < 150, auto=v(car), cajon=v(ARRIVAL))
                elevator = state["every"]["Ascensor_Empleados"]
                front = elevator.get_actor_location() + elevator.get_actor_forward_vector() * 230
                found = unreal.NavigationSystemV1.find_path_to_location_synchronously(state["world"], worker.get_actor_location(), front)
                report["camino_al_ascensor"] = {"valido": bool(found and found.is_valid()), "parcial": bool(found and found.is_partial()),
                                                "puntos": [v(q) for q in found.get_editor_property("path_points")] if found else []}
            state["last_state"] = now
        if now in (S.WORKING, S.ACTING):
            check("encargado_en_la_cabina", state["barrier"].is_inside(worker), donde=v(worker.get_actor_location()),
                  segundos=round(time.monotonic() - state["state_at"], 1), saltos=worker.get_editor_property("skips"))
            check("camina_sin_trabarse", worker.get_editor_property("skips") == 0, saltos=worker.get_editor_property("skips"),
                  trabado_en=v(worker.get_editor_property("last_held_at")))
            report["passed"] = True
            finish()
        elif time.monotonic() - state["state_at"] > 150:
            check("encargado_llega", False, estado=str(now), donde=v(worker.get_actor_location()))
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal.log("[EMPLOYEE_SCENE_PLAY] registrado")
