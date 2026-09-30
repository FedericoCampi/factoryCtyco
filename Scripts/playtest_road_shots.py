"""PIE: capturas de la calle del recorrido de los camiones (28/09): Docs/road_1.png (entrada oeste),
road_2.png (carril adentro) y road_3.png (salida). Cierra el editor."""
import time
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
state = {"phase": "warmup", "t": time.monotonic(), "i": 0}
SPOTS = [(-1000, 150), (250, 250), (1000, 150)]   # cm en el espacio del estacionamiento
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")


def tick(delta):
    # la captura procesa Slate y vuelve a llamar este callback desde adentro: sin reentrar
    if state.get("busy"):
        return
    state["busy"] = True
    try:
        step()
    finally:
        state["busy"] = False


def step():
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
        park = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.StaticMeshActor)
                    if a.get_actor_label() == "Parking_Estacionamiento")
        state.update(pawn=pawn, park=park, phase="move", t=time.monotonic())
    elif name == "move":
        x, y = SPOTS[state["i"]]
        spot = state["park"].get_actor_transform().transform_location(unreal.Vector(x, y, 100))
        state["pawn"].set_actor_location(spot, False, True)
        state.update(phase="shot", t=time.monotonic())
    elif name == "shot" and age > 1.5:
        print("[captura desactivada]", 1280, 720, str(project / f"Docs/road_{state['i'] + 1}.png"))
        state["i"] += 1
        state.update(phase="move" if state["i"] < len(SPOTS) else "end", t=time.monotonic())
    elif name == "end" and age > 1.5:
        levels.editor_request_end_play()
        state.update(phase="quit", t=time.monotonic())
    elif name == "quit" and age > 2:
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.SystemLibrary.quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
