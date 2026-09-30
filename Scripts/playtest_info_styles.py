"""PIE: capturas del panel de informacion (tecla I), estilo Pegatina Pop (28/09).

Docs/info_panel.png (entrada terminada) y Docs/info_panel_entrada.png (a mitad de la entrada). Cierra el editor.
"""
import time
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
state = {"phase": "warmup", "t": time.monotonic()}
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")


def tick(delta):
    age = time.monotonic() - state["t"]
    name = state["phase"]
    if name == "warmup" and age > 8:
        levels.editor_request_begin_play()
        state.update(phase="spawn", t=time.monotonic())
    elif name == "spawn":
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0) if worlds else None
        if pawn is None:
            return
        pawn.get_component_by_class(unreal.FactoryGatheringComponent).toggle_inventory()   # tecla I
        state.update(phase="mid", t=time.monotonic())
    elif name == "mid" and age > 0.2:
        print("[captura desactivada]", 1280, 720, str(project / "Docs/info_panel_entrada.png"))
        state.update(phase="full", t=time.monotonic())
    elif name == "full" and age > 2.0:
        print("[captura desactivada]", 1280, 720, str(project / "Docs/info_panel.png"))
        state.update(phase="end", t=time.monotonic())
    elif name == "end" and age > 1.5:
        levels.editor_request_end_play()
        state.update(phase="quit", t=time.monotonic())
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
