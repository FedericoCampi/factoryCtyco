"""PIE: intro, briefing y pasos guiados de la misión 1, y remarcado de clickeables (29/09).

1. Al arrancar la intro tapa la pantalla: el personaje no se mueve y no hay paso activo todavía.
2. Tres tarjetas + briefing (Advance, como Espacio): arranca el paso 1 y el personaje se mueve.
3. Paso 1: la flecha grande está sobre la puerta del ascensor (Guia_PuertaAscensor); llegar al piso DESPACHO lo cumple.
4. Paso 2 portón abierto (flecha en su botonera), paso 3 cinta encendida, paso 4 caja en mano,
   paso 5 caja en la cinta del camión, paso 6 20 entregados.
5. El jugador tiene el componente de contorno y la cámara el post-proceso M_ContornoClic.
Sin capturas: informe Docs/mission_guide_play.json. Cierra el editor.
Lanzar con -ExecCmds="py <lanzador sin espacios en la ruta>" (en UE 5.6 -ExecutePythonScript cierra el editor).
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


def phase(name):
    unreal.log(f"[GUIDE_PLAY] fase {name}")
    state.update(phase=name, t=time.monotonic())


def check(name, ok, **values):
    report["checks"][name] = {"passed": bool(ok), **values}
    if not ok:
        raise RuntimeError(f"{name}: {values}")


def finish():
    (project / "Docs/mission_guide_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    levels.editor_request_end_play()
    phase("quit")


def by_label(cls):
    return {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(state["world"], cls)}


def rounded(v):
    return [round(v.x), round(v.y), round(v.z)]


def arrow_tip():
    guide = state["guide"]
    parts = [c for c in guide.get_components_by_class(unreal.StaticMeshComponent)]
    visible = [c for c in parts if c.is_visible()]
    head = next((c for c in parts if c.get_name() == "Head"), None)
    return bool(visible), head.get_world_location() if head else None


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
    if time.monotonic() - state["start"] > 240 and state["phase"] != "quit":
        raise RuntimeError("La prueba no termino a tiempo")
    name = state["phase"]
    if name == "warmup" and age > 8:
        levels.editor_request_begin_play()
        phase("spawn")
    elif name == "spawn":
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0) if worlds else None
        if pawn is None or age < 1.5:
            return
        state.update(world=worlds[0], pawn=pawn, player=unreal.GameplayStatics.get_player_controller(worlds[0], 0))
        guides = unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryGuide)
        check("hay_guia", len(guides) == 1, cantidad=len(guides))
        state["guide"] = guides[0]
        shown, _ = arrow_tip()
        check("intro_tapa_y_frena", state["player"].is_move_input_ignored() and not shown,
              quieto=state["player"].is_move_input_ignored(), flecha=shown)
        state["cards"] = 0
        phase("intro")
    elif name == "intro" and age > 0.6:
        # Three story cards and the briefing: four presses of Space.
        state["guide"].advance()
        state["cards"] += 1
        phase("intro" if state["cards"] < 4 else "started")
    elif name == "started" and age > 0.5:
        guide, player = state["guide"], state["player"]
        check("arranca_el_paso_1", guide.get_step_index() == 0 and not player.is_move_input_ignored(),
              paso=guide.get_step_index(), quieto=player.is_move_input_ignored())
        shown, tip = arrow_tip()
        at = by_label(unreal.TargetPoint)["Guia_PuertaAscensor"].get_actor_location()   # la puerta del ascensor
        check("flecha_sobre_la_puerta_del_ascensor", shown and tip is not None and abs(tip.x - at.x) < 150 and abs(tip.y - at.y) < 150 and tip.z > at.z,
              flecha=rounded(tip) if tip else None, puerta=rounded(at))
        stops = {e.get_actor_label(): e.get_editor_property("stop_name") for e in by_label(unreal.FactoryElevator).values()}
        check("piso_despacho", stops.get("Ascensor_Estacionamiento") == "DESPACHO", pisos=stops)
        hover = state["pawn"].get_component_by_class(unreal.FactoryHoverComponent)
        camera = state["pawn"].get_component_by_class(unreal.CameraComponent)
        blendables = camera.get_editor_property("post_process_settings").get_editor_property("weighted_blendables").get_editor_property("array")
        names = [b.get_editor_property("object").get_name() for b in blendables if b.get_editor_property("object")]
        check("contorno_listo", hover is not None and any("ContornoClic" in n or "MaterialInstanceDynamic" in n for n in names), blendables=names)
        # Arrive at the dispatch floor (as the elevator would leave the character).
        target = by_label(unreal.FactoryElevator)["Ascensor_Estacionamiento"].get_actor_location()
        state["pawn"].set_actor_location(target + unreal.Vector(0, 0, 110), False, True)
        phase("reach")
    elif name == "reach":
        if state["guide"].get_step_index() == 1:
            check("llegar_al_despacho_cumple_el_paso_1", True, segundos=round(age, 1))
            door = by_label(unreal.FactoryRollDoor)["Porton_Camiones"]
            shown, tip = arrow_tip()
            button = door.get_editor_property("button").get_world_location()
            check("flecha_sobre_la_botonera_del_porton", shown and tip is not None and abs(tip.x - button.x) < 60 and abs(tip.y - button.y) < 60,
                  flecha=rounded(tip) if tip else None, botonera=rounded(button))
            door.set_open(True)
            phase("door")
        elif age > 6:
            check("llegar_al_despacho_cumple_el_paso_1", False, paso=state["guide"].get_step_index())
    elif name == "door":
        if state["guide"].get_step_index() == 2:
            check("porton_abierto_cumple_el_paso_2", True, segundos=round(age, 1))
            by_label(unreal.FactoryDispatchBelt)["Despacho_Cajas"].set_belt_on(True)
            phase("belt")
        elif age > 8:
            check("porton_abierto_cumple_el_paso_2", False, paso=state["guide"].get_step_index())
    elif name == "belt":
        if state["guide"].get_step_index() == 3:
            check("cinta_encendida_cumple_el_paso_3", True)
            state["pawn"].get_component_by_class(unreal.FactoryCarryComponent).take(BOX)
            phase("carry")
        elif age > 6:
            check("cinta_encendida_cumple_el_paso_3", False, paso=state["guide"].get_step_index())
    elif name == "carry":
        if state["guide"].get_step_index() == 4:
            check("caja_en_mano_cumple_el_paso_4", True)
            shown, tip = arrow_tip()
            belt = by_label(unreal.FactoryLoadingBelt)["Cinta_Carga3"]
            check("flecha_sobre_la_cinta_del_camion", shown and tip is not None and ((tip.x - belt.get_actor_location().x) ** 2 + (tip.y - belt.get_actor_location().y) ** 2) ** 0.5 < 300,
                  flecha=rounded(tip) if tip else None, cinta=rounded(belt.get_actor_location()))
            length = belt.get_editor_property("length")
            side = belt.get_actor_transform().transform_location(unreal.Vector(length * 0.1, 90, 0))
            pawn = state["pawn"]
            pawn.set_actor_location(unreal.Vector(side.x, side.y, pawn.get_actor_location().z), False, True)
            phase("load")
        elif age > 6:
            check("caja_en_mano_cumple_el_paso_4", False, paso=state["guide"].get_step_index())
    elif name == "load" and age > 0.5:
        if not state.get("pressed"):
            state["pawn"].get_component_by_class(unreal.FactoryGatheringComponent).interact()
            state["pressed"] = True
        if state["guide"].get_step_index() == 5:
            check("caja_cargada_cumple_el_paso_5", True)
            economy = unreal.FactoryEconomySubsystem.get(state["pawn"])
            before = economy.get_money()
            unreal.FactoryMissionSubsystem.get(state["pawn"]).add_delivered(20)
            check("entregas_pagan_60_cada_una", economy.get_money() == before + 20 * 60, antes=before, despues=economy.get_money())
            phase("deliver")
        elif age > 8:
            check("caja_cargada_cumple_el_paso_5", False, paso=state["guide"].get_step_index(),
                  en_mano=state["pawn"].get_component_by_class(unreal.FactoryCarryComponent).is_carrying())
    elif name == "deliver":
        shown, _ = arrow_tip()
        if state["guide"].get_step_index() == 6:
            check("20_entregados_terminan_la_guia", not shown)
            report["passed"] = True
            finish()
        elif age > 6:
            check("20_entregados_terminan_la_guia", False, paso=state["guide"].get_step_index())
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal.log("[GUIDE_PLAY] registrado")
