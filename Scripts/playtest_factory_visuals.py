"""Rendered visual smoke; isolated save slot and timestamped evidence.

Launch with -ExecutePythonScript=<this file>, a rendered Unreal Editor and
-NoLiveCoding. The script starts PIE and exits the editor when finished.
"""
import json
from pathlib import Path
import time
import traceback

import unreal


PROJECT = Path(unreal.Paths.project_dir()).resolve()
STAMP = time.strftime("%Y%m%d-%H%M%S")
OUTPUT = PROJECT / "Saved" / "VisualPolishWork" / ("Playtest-" + STAMP)
OUTPUT.mkdir(parents=True, exist_ok=True)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EDITOR = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
REPORT = {
    "passed": False,
    "checks": {},
    "screenshots": [],
    "save_slot": "FactoryCtycoDemo_VisualSmoke_" + STAMP,
    "scope": "Rendered PIE visual state, construction, production and save/load smoke. Test stock is injected through inventory APIs.",
}
STATE = {"started": time.monotonic(), "finishing": False}
unreal.EditorPythonScripting.set_keep_python_script_alive(True)


def wait(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        yield


def record(name, **values):
    REPORT["checks"][name] = {"passed": True, **values}
    unreal.log("[VISUAL_CHECK] " + name)


def machine(identity):
    return next(b for b in STATE["factory"].buildings() if str(b.persistent_id) == identity)


def presentation(building):
    result = building.get_component_by_class(unreal.FactoryPresentationComponent)
    assert result, "No presentation on " + str(building.persistent_id)
    assert 0 <= result.activity <= 1, "Activity outside 0..1"
    return result


def decorative_primitives(building):
    baseline = {building.visual.get_path_name(), building.cargo.get_path_name(), building.collision.get_path_name()}
    return [p for p in building.get_components_by_class(unreal.PrimitiveComponent) if p.get_path_name() not in baseline]


def inspect_buildings():
    result = {}
    for building in STATE["factory"].buildings():
        visual = presentation(building)
        pieces = decorative_primitives(building)
        assert pieces, "Presentation generated no decorative primitives: " + str(building.persistent_id)
        for piece in pieces:
            assert piece.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION, piece.get_path_name()
            assert not piece.is_simulating_physics(), piece.get_path_name()
        result[str(building.persistent_id)] = {
            "decorative_primitives": len(pieces),
            "activity": round(visual.activity, 3),
            "working": visual.working,
            "blocked": visual.blocked,
        }
    return result


def amounts(inventory):
    return {str(key): int(value) for key, value in inventory.items.items()}


def simulation_snapshot():
    factory = STATE["factory"]
    return {
        "inventory": amounts(STATE["inventory"]),
        "produced": factory.plates_produced,
        "delivered": factory.plates_delivered,
        "buildings": {
            str(b.persistent_id): {
                "input": amounts(b.input),
                "output": amounts(b.output),
                "progress": round(b.progress_seconds, 5),
                "yaw": round(b.get_actor_rotation().yaw, 2),
                "storage_item": str(b.storage_item),
                "paid_scrap": b.paid_scrap,
            }
            for b in factory.buildings()
        },
    }


def mass():
    def weight(inventory):
        return inventory.get_quantity("Scrap") + inventory.get_quantity("Fragments") + 2 * inventory.get_quantity("Plate")
    return weight(STATE["inventory"]) + sum(
        weight(b.input) + weight(b.output) + b.paid_scrap for b in STATE["factory"].buildings()
    )


def capture(name):
    path = OUTPUT / (name + ".png")
    print("[captura desactivada]", 1440, 900, str(path))
    REPORT["screenshots"].append(str(path))
    yield from wait(2)


def frame(close=False):
    # The authored framing is (0, -320, 0), so this pawn position centres the
    # production row. Real zoom input avoids reconstructing the pawn Blueprint
    # through set_editor_property on an owned component during PIE.
    pawn = STATE["pawn"]
    pawn.character_movement.stop_movement_immediately()
    pawn.set_actor_location(unreal.Vector(0, 320, 100), False, True)
    control = STATE["camera"]
    control.reset_camera()
    key_name = "MouseScrollUp" if close else "MouseScrollDown"
    for _ in range(5 if close else 1):
        # Legacy non-consuming bindings may return false while queuing the key.
        control.send_editor_test_input(key_name, 1.0, True)
        control.send_editor_test_input(key_name, 0.0, False)
        yield
    yield from wait(0.8)


def run():
    assert LEVELS.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
    unreal.SystemLibrary.execute_console_command(EDITOR.get_editor_world(), "t.MaxFPS 30")
    yield from wait(7)
    LEVELS.editor_request_begin_play()
    yield from wait(3)
    worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
    assert worlds, "PIE did not start"
    pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
    assert pawn
    demo = pawn.get_component_by_class(unreal.FactoryDemoComponent)
    assert demo and demo.factory
    inventory = pawn.get_component_by_class(unreal.FactoryInventoryComponent)
    STATE.update(world=worlds[0], pawn=pawn, demo=demo, factory=demo.factory, inventory=inventory,
                 camera=pawn.get_component_by_class(unreal.FactoryCameraComponent))
    factory = demo.factory
    factory.set_editor_property("save_slot", REPORT["save_slot"])
    yield from frame()
    initial = inspect_buildings()
    assert len(initial) == 4, initial
    for identity in ("Starter_2", "Starter_4"):
        visual = presentation(machine(identity))
        assert not visual.working and not visual.blocked and visual.activity < 0.05
    record("idle_starter_presentations_and_collision", buildings=initial)
    yield from capture("01_idle")

    crusher = machine("Starter_2")
    smelter = machine("Starter_4")
    assert crusher.input.add_item(factory.resource("Scrap"), 20) == 20
    assert smelter.input.add_item(factory.resource("Fragments"), 10) == 10
    yield from wait(1)
    for building in (crusher, smelter):
        visual = presentation(building)
        assert visual.working and not visual.blocked and visual.activity > 0.2, str(building.persistent_id)
    record("processors_animate_when_working", buildings=inspect_buildings())
    yield from frame(close=True)
    yield from capture("02_processing")

    # Hold the simulation for a short interval while decorative components tick.
    factory.set_actor_tick_enabled(False)
    expected = simulation_snapshot()
    initial_phase = presentation(crusher).motion_phase
    moving_pieces = decorative_primitives(crusher)
    initial_positions = [piece.get_world_location() for piece in moving_pieces]
    yield from wait(0.7)
    assert simulation_snapshot() == expected, "Presentation modified simulation state"
    assert presentation(crusher).motion_phase > initial_phase, "Animation phase did not advance"
    assert any(
        (piece.get_world_location() - position).length() > 0.1
        for piece, position in zip(moving_pieces, initial_positions)
    ), "Crusher decorative parts did not move"
    factory.set_actor_tick_enabled(True)
    record("decorative_animation_continues_without_mutating_paused_simulation")

    free = crusher.output.get_free_space()
    assert crusher.output.add_item(factory.resource("Fragments"), free) == free
    yield from wait(1)
    visual = presentation(crusher)
    assert visual.blocked and not visual.working, "Full output did not display blocked state"
    blocked_input = amounts(crusher.input)
    blocked_progress = crusher.progress_seconds
    yield from wait(0.8)
    assert amounts(crusher.input) == blocked_input
    assert abs(crusher.progress_seconds - blocked_progress) < 0.001
    record("blocked_output_stops_machine", activity=visual.activity)
    yield from capture("03_blocked")
    crusher.output.remove_item("Fragments", crusher.output.get_total())

    # Build real belt actors through the same public gameplay operation as clicks.
    build = json.loads((PROJECT / "Docs" / "factory_demo_build.json").read_text(encoding="utf-8"))
    assert inventory.add_item(factory.resource("Scrap"), 6) == 6
    belt_ids = []
    for position in build["belt_slots"]:
        belt = demo.build_at(3, unreal.Vector(*position), 0)
        assert belt, "Could not construct belt: " + demo.notification
        belt_ids.append(str(belt.persistent_id))
    assert machine("Starter_0").input.add_item(factory.resource("Scrap"), 40) == 40
    total_mass = mass()
    yield from wait(2)
    record("new_belts_get_presentations", buildings=inspect_buildings(), belt_ids=belt_ids)
    yield from wait(8)
    assert mass() == total_mass, "Production changed total material mass"
    assert factory.plates_produced > 0
    record("production_and_conservation", mass=total_mass, plates_produced=factory.plates_produced)
    yield from frame()
    yield from capture("04_active_line")

    expected = simulation_snapshot()
    assert factory.save_factory(pawn)
    yield from wait(1)
    assert factory.load_factory(pawn)
    assert simulation_snapshot() == expected, "Save/load changed gameplay state"
    yield from wait(1)
    loaded = inspect_buildings()
    assert set(loaded) == set(expected["buildings"])
    assert mass() == total_mass
    record("save_load_recreates_all_presentations", buildings=loaded)
    yield from capture("05_restored_line")
    for screenshot in REPORT["screenshots"]:
        assert Path(screenshot).exists(), "Screenshot was not written: " + screenshot
    record("screenshots_written", count=len(REPORT["screenshots"]))
    REPORT["passed"] = True


def finish():
    STATE["finishing"] = True
    if "factory" in STATE:
        STATE["factory"].set_actor_tick_enabled(True)
    REPORT["elapsed_seconds"] = round(time.monotonic() - STATE["started"], 1)
    path = OUTPUT / "report.json"
    path.write_text(json.dumps(REPORT, indent=2), encoding="utf-8")
    (OUTPUT.parent / "latest-playtest.txt").write_text(str(OUTPUT), encoding="utf-8")
    unreal.log("[FACTORY_VISUAL_PLAYTEST] " + json.dumps(REPORT))
    LEVELS.editor_request_end_play()
    yield from wait(2)
    unreal.unregister_slate_post_tick_callback(STATE["handle"])
    unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    unreal.SystemLibrary.quit_editor()


STATE["steps"] = run()


def tick(delta):
    # HighResShot can pump Slate recursively while the generator is executing.
    if STATE.get("in_tick"):
        return
    STATE["in_tick"] = True
    try:
        if not STATE["finishing"] and time.monotonic() - STATE["started"] > 150:
            raise RuntimeError("Visual smoke timed out")
        next(STATE["steps"])
    except StopIteration:
        if not STATE["finishing"]:
            STATE["steps"] = finish()
    except Exception:
        REPORT["error"] = traceback.format_exc()
        REPORT["passed"] = False
        unreal.log_error(REPORT["error"])
        STATE["steps"] = finish()
    finally:
        STATE["in_tick"] = False


STATE["handle"] = unreal.register_slate_post_tick_callback(tick)
