"""Prueba en Play (04/10), con L_FactoryDemo abierto en el editor: el horno con tapa.

- Apagado, la tapa esta en su reposo (38 grados) y el horno no toma nada de la cinta.
- Prendido (E), la tapa se abre mas (75) y toma piedra triturada de la cinta de la boca hasta juntar 3; entonces se
  cierra (0) y funde; lo que llega despues espera en la cinta.
- Fundido, cuela solo: el liquido es del color de la piedra triturada (su Color) y llena el contenedor; despues la tapa
  vuelve a abrirse para el lote siguiente.
El tiempo va 10 veces mas rapido. No guarda nada. Corre en el tick del editor (puente MCP). Informe: Docs/horno_play.json.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

docs = Path(unreal.Paths.project_dir()).resolve() / "Docs"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}, "timeline": []}
state = {"phase": "start", "t": time.monotonic(), "start": time.monotonic(), "fed": 0}
Stage = unreal.FactoryFurnaceStage


def phase(name):
    state.update(phase=name, t=time.monotonic())
    report["timeline"].append([name, round(time.monotonic() - state["start"], 1), round(state["melt"].get_lid_angle(), 1) if "melt" in state else None])


def check(name, ok, **values):
    report["checks"][name] = dict(passed=bool(ok), **values)


def finish():
    report["passed"] = bool(report["checks"]) and all(c["passed"] for c in report["checks"].values()) and "error" not in report
    (docs / "horno_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    unreal.unregister_slate_post_tick_callback(state["handle"])
    if unreal.EditorLevelLibrary.get_pie_worlds(False):
        if "world" in state:
            unreal.SystemLibrary.execute_console_command(state["world"], "slomo 1")
        levels.editor_request_end_play()


def feed():
    """Una piedra triturada en la cinta de la boca, si esta vacia (la cinta la lleva hasta la punta)."""
    belt = state["belt"]
    if belt.get_editor_property("input").get_quantity("CrushedStone") == 0:
        belt.get_editor_property("input").add_item(state["crushed"], 1)
        state["fed"] += 1


def tick(delta):
    try:
        age = time.monotonic() - state["t"]
        if time.monotonic() - state["start"] > 150:
            raise RuntimeError("La prueba tardo demasiado: " + state["phase"])
        name = state["phase"]
        if name == "start":
            levels.editor_request_begin_play()
            state.update(phase="spawn", t=time.monotonic())
        elif name == "spawn" and age > 4:
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            if not worlds or unreal.GameplayStatics.get_player_character(worlds[0], 0) is None:
                return
            world = worlds[0]
            melt = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.FactoryMeltProcess))
            state.update(world=world, melt=melt, belt=melt.get_editor_property("feed_belt"),
                         crushed=unreal.load_asset("/Game/FactoryCtyco/Factory/Definitions/DA_CrushedStone"))
            unreal.SystemLibrary.execute_console_command(world, "slomo 10")
            phase("apagado")
        elif name == "apagado" and age > 1.5:
            melt = state["melt"]
            feed()
            check("apagado_tapa_en_reposo", abs(melt.get_lid_angle() - melt.get_editor_property("lid_rest_angle")) < 1
                  and not melt.get_editor_property("on"), tapa=round(melt.get_lid_angle(), 1))
            state["off_loaded"] = melt.get_editor_property("loaded")
            melt.set_on(True)
            phase("prendido")
        elif name == "prendido":
            melt = state["melt"]
            feed()
            angle = melt.get_lid_angle()
            state["max_open"] = max(state.get("max_open", 0), angle)
            if melt.get_editor_property("furnace") == Stage.MELTING:
                check("apagado_no_toma", state["off_loaded"] == 0, cargadas_apagado=state["off_loaded"])
                check("prendido_abre_mas", state["max_open"] >= melt.get_editor_property("lid_loading_angle") - 1,
                      tapa_maxima=round(state["max_open"], 1))
                check("junta_3", melt.get_editor_property("loaded") == 3, cargadas=melt.get_editor_property("loaded"))
                phase("fundiendo")
        elif name == "fundiendo":
            melt = state["melt"]
            feed()   # lo que llega espera en la cinta
            state["min_lid"] = min(state.get("min_lid", 999), melt.get_lid_angle())
            state["waiting"] = state["belt"].get_editor_property("input").get_quantity("CrushedStone")
            if melt.get_editor_property("furnace") in (Stage.MOLTEN, Stage.POURING):
                check("cerrado_mientras_funde", state["min_lid"] < 1, tapa_minima=round(state["min_lid"], 1))
                check("material_espera_en_la_cinta", state["waiting"] >= 1 and melt.get_editor_property("loaded") == 3,
                      en_la_cinta=state["waiting"])
                phase("colando")
        elif name == "colando":
            melt = state["melt"]
            if melt.get_editor_property("furnace") == Stage.POURING:
                state["poured"] = True
            if melt.get_editor_property("fill_level") > 0.5:
                state["filled"] = True
            if melt.get_editor_property("furnace") == Stage.LOADING and state.get("poured"):
                color = melt.get_editor_property("molten_color")
                want = state["crushed"].get_editor_property("color")
                same = abs(color.r - want.r) + abs(color.g - want.g) + abs(color.b - want.b) < 0.02
                check("cuela_solo", bool(state.get("poured")) and bool(state.get("filled")))
                check("liquido_del_color_del_material", same, liquido=[round(color.r, 2), round(color.g, 2), round(color.b, 2)],
                      material=[round(want.r, 2), round(want.g, 2), round(want.b, 2)])
                phase("reabre")
        elif name == "reabre" and age > 0.6:
            melt = state["melt"]
            check("vuelve_a_abrir", melt.get_lid_angle() > melt.get_editor_property("lid_rest_angle"), tapa=round(melt.get_lid_angle(), 1))
            finish()
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error("[HORNO_PLAY] " + report["error"])
        finish()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
