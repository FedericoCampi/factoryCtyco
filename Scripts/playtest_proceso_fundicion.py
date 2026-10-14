"""PIE: proceso de fundicion (02/10). Sirve con el editor abierto (no lo cierra) o con -unattended (lo cierra al final).

0. La guia esta en pausa (sin intro ni mision) y el personaje empieza en la fabrica.
1. Se cargan piedras en la cinta corta (como a mano): pasan por adentro de la caja y salen cortadas en bloques
   (Sierra_Estacion), la plataforma los sube y los deja caer en la trituradora, que saca piedra triturada, y por Cinta_Fabrica_2, la esquina y
   Cinta_Fabrica_1 llegan al horno.
2. El horno junta la tanda (BatchSize) y queda listo; con el personaje en el punto de control, E (try_interact) lo
   enciende: se calienta y brilla hasta quedar el silicio fundido.
3. E abre la colada: el chorro corre por la canaleta, llena el contenedor, que se enfria hasta dejar el lingote.
4. E al lado del contenedor retira el lingote: queda en el inventario del personaje y el contenedor vuelve a vacio.
Corre con el tiempo acelerado (TIME_SCALE). Capturas: Saved/Screenshots/fundicion_*.png.
Informe: Docs/proceso_fundicion_play.json.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
shots = project / "Saved/Screenshots"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
TIME_SCALE = 4.0
report = {"passed": False, "checks": {}}
state = {"started": time.monotonic(), "finishing": False, "busy": False}
FS, MS = unreal.FactoryFurnaceStage, unreal.FactoryMoldStage


def wait(seconds):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        yield


def wait_for(condition, seconds, what):
    until = time.monotonic() + seconds
    while not condition():
        if time.monotonic() > until:
            raise AssertionError(f"Se acabo el tiempo esperando: {what}")
        yield


def capture(name):
    path = shots / f"fundicion_{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    unreal.AutomationLibrary.take_high_res_screenshot(1440, 900, str(path))
    yield from wait(2.5)
    report.setdefault("capturas", []).append(path.name if path.exists() else f"(falto) {path.name}")


def run():
    if HEADLESS:
        assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
        yield from wait(6)
    levels.editor_request_begin_play()
    yield from wait(4)
    worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
    assert worlds, "No arranco Play"
    world = worlds[0]
    pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
    guides = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryGuide)
    assert all(g.get_editor_property("paused") for g in guides), "La guia no esta en pausa"
    spawn = pawn.get_actor_location()
    start = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerStart)[0].get_actor_location()
    assert (spawn - start).length() < 300, f"El personaje no empezo en la fabrica: {spawn}"
    report["checks"]["inicio"] = {"guia_en_pausa": True, "personaje": [round(spawn.x), round(spawn.y), round(spawn.z)]}
    melt = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryMeltProcess)
    assert len(melt) == 1, f"Se esperaba un proceso de fundicion, hay {len(melt)}"
    melt = melt[0]
    buildings = {str(b.persistent_id) or b.get_actor_label(): b for b in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryBuilding)}
    labels = {b.get_actor_label(): b for b in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryBuilding)}
    short, main, riser, crusher = (labels[n] for n in ("Cinta_Cuarzo_Triturar3", "Cinta_Cuarzo_Triturar", "Cinta_Fabrica_2", "Trituradora_Cuarzo"))
    station = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryBeltStation)[0]
    sim = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryDemoWorld)[0]
    batch = melt.get_editor_property("batch_size")
    unreal.GameplayStatics.set_global_time_dilation(world, TIME_SCALE)
    loaded = {"n": 0}

    def wait_feeding(condition, seconds, what):
        """Como cargar piedras a mano: una en la cinta corta cada vez que esta vacia."""
        until = time.monotonic() + seconds
        while not condition():
            if short.input.get_total() == 0:
                short.input.add_item(sim.resource("Stone"), 1)
                loaded["n"] += 1
            if time.monotonic() > until:
                raise AssertionError(f"Se acabo el tiempo esperando: {what}")
            yield

    # 1. la piedra se lava en la caja, se tritura y llega al horno
    seen = {}
    def watch():
        if main.input.get_quantity("Stone") > 0:
            seen["en_bruto_en_la_cinta"] = True
        if main.input.get_quantity("StoneBlock") > 0:
            seen["bloque_en_la_cinta"] = True
        return station.get_editor_property("processed") > 0
    yield from wait_feeding(watch, 60, "el primer bloque cortado en la caja")
    yield from wait_feeding(lambda: crusher.progress_seconds > 0 or crusher.output.get_total() > 0, 40, "la trituradora trabajando")
    yield from wait_feeding(lambda: riser.cargo.is_visible(), 40, "piedra triturada sobre la cinta que sube")
    cargo = riser.cargo.static_mesh.get_name() if riser.cargo.static_mesh else None
    yield from wait_feeding(lambda: melt.get_editor_property("loaded") >= 1, 90, "la primera piedra triturada en el horno")
    report["checks"]["piedra_llega"] = {**seen, "cortadas": station.get_editor_property("processed"), "carga_que_sube": cargo}
    yield from wait_feeding(lambda: melt.get_editor_property("furnace") == FS.READY, 120, f"la tanda de {batch}")
    report["checks"]["tanda"] = {"cargado": melt.get_editor_property("loaded"), "estado": str(melt.get_editor_property("furnace")),
                                 "piedras_cargadas": loaded["n"]}

    # 2. E en el punto de control enciende el horno
    control = melt.get_actor_transform().transform_location(melt.get_editor_property("control_point"))
    pawn.character_movement.stop_movement_immediately()
    pawn.set_actor_location(unreal.Vector(control.x, control.y, control.z + 100), False, True)
    yield from wait(.3)
    prompt = melt.prompt_for(pawn)
    assert prompt == "[E] ENCENDER HORNO", prompt
    assert melt.try_interact(pawn), "E no encendio el horno"
    yield from wait_for(lambda: melt.get_editor_property("furnace_heat") > .5, 20, "que el horno se caliente")
    glow = melt.furnace_glow.intensity
    assert glow > 0, "El horno no brilla"
    yield from capture("fundiendo")
    yield from wait_for(lambda: melt.get_editor_property("furnace") == FS.MOLTEN, 20, "silicio fundido")
    report["checks"]["fundir"] = {"prompt": prompt, "brillo": round(glow)}

    # 3. E abre la colada
    assert melt.prompt_for(pawn) == "[E] ABRIR COLADA", melt.prompt_for(pawn)
    assert melt.try_interact(pawn), "E no abrio la colada"
    yield from wait_for(lambda: melt.stream.get_instance_count() >= 3, 10, "el chorro por la canaleta")
    yield from capture("colando")
    yield from wait_for(lambda: melt.get_editor_property("mold") == MS.FILLING and melt.get_editor_property("fill_level") > .5, 30, "que se llene el contenedor")
    pieces = melt.stream.get_instance_count()
    yield from capture("llenando")
    yield from wait_for(lambda: melt.get_editor_property("mold") == MS.COOLING, 30, "que termine de colar")
    assert melt.stream.get_instance_count() == 0, "Quedo liquido en la canaleta"
    # vacio, ya junta la tanda siguiente (la cinta puede haberle dejado algo)
    assert melt.get_editor_property("furnace") in (FS.LOADING, FS.READY), "El horno no volvio a cargar"
    heat = melt.get_editor_property("fill_heat")
    yield from wait_for(lambda: melt.get_editor_property("mold") == MS.INGOT_READY, 30, "el lingote frio")
    report["checks"]["colar"] = {"tramos_de_chorro": pieces, "llenado": round(melt.get_editor_property("fill_level"), 2),
                                 "calor_al_empezar_a_enfriar": round(heat, 2), "calor_final": round(melt.get_editor_property("fill_heat"), 2)}

    # 4. E al lado del contenedor retira el lingote
    box = melt.get_editor_property("container")
    origin, extent = box.get_actor_bounds(False)
    side = box.get_actor_right_vector() * (min(extent.x, extent.y) + 70)   # al costado largo, afuera
    pawn.set_actor_location(unreal.Vector(origin.x + side.x, origin.y + side.y, box.get_actor_location().z + 100), False, False)
    yield from wait(.3)
    assert melt.prompt_for(pawn) == "[E] RETIRAR LINGOTE", melt.prompt_for(pawn)
    yield from capture("lingote")
    inventory = pawn.get_component_by_class(unreal.FactoryInventoryComponent)
    before = inventory.get_quantity("SiliconIngot") if inventory else 0
    assert melt.try_interact(pawn), "E no retiro el lingote"
    assert melt.get_editor_property("ingots_made") == 1 and melt.get_editor_property("mold") == MS.EMPTY
    report["checks"]["lingote"] = {"hechos": melt.get_editor_property("ingots_made"),
                                   "en_inventario": (inventory.get_quantity("SiliconIngot") - before) if inventory else "sin inventario"}
    report["passed"] = True


def finish():
    state["finishing"] = True
    (project / "Docs/proceso_fundicion_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
    if worlds:
        unreal.GameplayStatics.set_global_time_dilation(worlds[0], 1.0)
    levels.editor_request_end_play()
    yield from wait(2)
    unreal.unregister_slate_post_tick_callback(state["handle"])
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()


state["steps"] = run()


def tick(delta):
    if state["busy"]:   # la captura re-entra el callback
        return
    state["busy"] = True
    try:
        if not state["finishing"] and time.monotonic() - state["started"] > 300:
            raise RuntimeError("Se acabo el tiempo")
        next(state["steps"])
    except StopIteration:
        if not state["finishing"]:
            state["steps"] = finish()
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error(report["error"])
        if not state["finishing"]:
            state["steps"] = finish()
    finally:
        state["busy"] = False


state["handle"] = unreal.register_slate_post_tick_callback(tick)
