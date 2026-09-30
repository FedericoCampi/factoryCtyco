"""Rendered PIE acceptance for GROW robot evolution, using public gameplay APIs.

Evidence is isolated in Saved/GrowEvolutionWork/Playtest-<UTC timestamp>.
Run through Unreal MCP execute_python or -ExecutePythonScript. The editor stays
open after the test; set GROW_TEST_QUIT_EDITOR=1 for a standalone worker run.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import struct
import time
import traceback

import unreal


PROJECT = Path(unreal.Paths.project_dir()).resolve()
OUTPUT = PROJECT / "Saved" / "GrowEvolutionWork" / ("Playtest-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ"))
OUTPUT.mkdir(parents=True, exist_ok=False)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EDITOR = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
QUIT_EDITOR = os.environ.get("GROW_TEST_QUIT_EDITOR", "0") == "1"
REPORT = {
    "passed": False,
    "checks": {},
    "routes": {},
    "screenshots": [],
    "scope": "Rendered L_GrowRobots PIE; authored outcome examples, public decision/undo/reset APIs, actual keyboard input, live creature animation and screenshots.",
}
STATE = {"started": time.monotonic(), "finishing": False, "in_tick": False}
unreal.EditorPythonScripting.set_keep_python_script_alive(True)


def wait(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        yield


def record(name, **values):
    REPORT["checks"][name] = {"passed": True, **values}
    unreal.log("[GROW_CHECK] " + name)


def world():
    return STATE["evolution"]


def snapshot():
    evolution = world()
    return {
        "history": [str(value) for value in evolution.history],
        "system_levels": list(evolution.system_levels),
        "profession": str(evolution.profession),
        "creature_level": evolution.creature_level,
        "complete": evolution.is_complete(),
        "successful": evolution.is_successful(),
        "creatures": [{"profession": str(creature.profession), "level": creature.level,
                       "species": str(creature.species.species_id) if creature.species else None}
                      for creature in evolution.creatures],
    }


def creature_visible(creature):
    return (not creature.get_editor_property("hidden") and creature.body.is_visible()
            and not creature.body.get_editor_property("hidden_in_game"))


def settled():
    deadline = time.monotonic() + max(8, world().transition_remaining + 5)
    while world().transition_remaining > 0:
        assert time.monotonic() < deadline, "Evolution transition did not finish"
        yield
    # Allow the render presentation to apply the final state for this frame.
    yield


def choose(decision):
    yield from settled()
    before = list(world().history)
    assert decision not in before
    assert world().choose_decision(decision), "Decision rejected: " + str(decision)
    assert list(world().history) == before + [decision]
    assert world().has_decision(decision)
    assert world().transition_remaining > 0, "Decision did not start its reveal transition"
    yield from settled()


def reset():
    world().reset_evolution()
    yield from settled()
    assert not list(world().history)
    assert len(world().system_levels) == 6
    assert list(world().system_levels) == [0] * 6
    assert world().creature_level == 0
    assert world().profession == unreal.GrowProfession.APPRENTICE
    assert not world().is_complete() and not world().is_successful()
    assert not any(creature_visible(creature) for creature in world().creatures)


def capture(name, width=1440, height=900):
    path = OUTPUT / (name + ".png")
    print("[captura desactivada]", width, height, str(path))
    REPORT["screenshots"].append(str(path))
    yield from wait(1.5)
    deadline = time.monotonic() + 6
    while not path.is_file():
        assert time.monotonic() < deadline, "Screenshot was not written: " + str(path)
        yield
    with path.open("rb") as stream:
        header = stream.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n", "Expected a PNG screenshot"
    actual_size = struct.unpack(">II", header[16:24])
    assert actual_size == (width, height), (name, actual_size, (width, height))
    REPORT.setdefault("screenshot_resolutions", {})[name] = list(actual_size)


def tap(key):
    # A non-consuming binding can return false even when the key is queued.
    STATE["pawn"].camera_controls.send_editor_test_input(key, 1.0, True)
    yield
    STATE["pawn"].camera_controls.send_editor_test_input(key, 0.0, False)
    yield


def click_card(index, decision):
    """Click the production Canvas HUD through the local PlayerController."""
    yield from settled()
    controller = STATE["controller"]
    pixel_width, pixel_height = controller.get_viewport_size()
    assert pixel_width > 0 and pixel_height > 0, "HUD viewport has no dimensions"
    scale = min(1.8, max(0.5, min(pixel_width / 1440.0, pixel_height / 900.0)))
    width, height = pixel_width / scale, pixel_height / scale
    card_width = (width - 48 - 5 * 10) / 6
    x = round((24 + (card_width + 10) * index + card_width / 2) * scale)
    y = round((height - 194 + 70) * scale)
    before = list(world().history)
    controller.set_mouse_location(x, y)
    yield
    yield from tap("LeftMouseButton")
    assert list(world().history) == before + [decision], {
        "error": "HUD mouse click did not choose expected card",
        "card": index, "position": [x, y], "viewport": [pixel_width, pixel_height],
        "history": [str(value) for value in world().history],
    }
    yield from settled()
    REPORT.setdefault("mouse_clicks", []).append({"card": index, "viewport": [pixel_width, pixel_height],
                                                   "position": [x, y], "decision": str(decision)})


def route(name, decisions, profession, creature_level, successful):
    yield from reset()
    prefixes = [snapshot()]
    for decision in decisions:
        yield from choose(decision)
        prefixes.append(snapshot())
    evolution = world()
    assert len(evolution.history) == 6 and len(set(str(value) for value in evolution.history)) == 6
    assert evolution.is_complete()
    assert evolution.is_successful() == successful
    assert evolution.profession == profession, (name, snapshot())
    assert evolution.creature_level == creature_level, (name, snapshot())
    assert evolution.creatures, "Awakening did not create any creatures"
    for creature in evolution.creatures:
        assert creature.profession == profession and creature.level == creature_level
        assert creature_visible(creature), "Completed route has a hidden robot"
        assert creature.species and creature.body.get_editor_property("skeletal_mesh_asset")
        if profession != unreal.GrowProfession.APPRENTICE:
            assert creature.accessory.get_editor_property("static_mesh"), "Profession has no authored accessory"
    assert evolution.visible_piece_count > 0
    stable = snapshot()
    for decision in decisions:
        assert not evolution.choose_decision(decision), "A seventh or repeated decision was accepted"
        assert snapshot() == stable, "Rejected decision modified state"
    REPORT["routes"][name] = stable
    record("route_" + name, profession=str(profession), creature_level=creature_level,
           system_levels=list(evolution.system_levels), visible_pieces=evolution.visible_piece_count)
    return prefixes


def verify_animation():
    creatures = list(world().creatures)
    starts = [creature.get_actor_location() for creature in creatures]
    phases = [creature.motion_phase for creature in creatures]
    world_phase = world().motion_phase
    bone_samples = [[] for _ in creatures]
    positions = [[] for _ in creatures]
    deadline = time.monotonic() + 2.1
    while time.monotonic() < deadline:
        for index, creature in enumerate(creatures):
            assert creature.body.get_anim_instance(), "Robot has no active skeletal animation instance"
            positions[index].append(creature.get_actor_location())
            # Component-space bone samples distinguish authored skeletal motion
            # from merely moving the whole actor around its station.
            if creature.body.does_socket_exist("foot_l"):
                pose = creature.body.get_socket_transform("foot_l", unreal.RelativeTransformSpace.RTS_COMPONENT)
                bone_samples[index].append([pose.translation.x, pose.translation.y, pose.translation.z])
        yield
    assert world().motion_phase != world_phase, "World animation phase is frozen"
    assert all(creature.motion_phase != phase for creature, phase in zip(creatures, phases))
    travel = [max((position - start).length() for position in samples)
              for start, samples in zip(starts, positions)]
    pose_ranges = []
    for samples in bone_samples:
        pose_ranges.append(max(max(values) - min(values) for values in zip(*samples)) if samples else 0)
    assert max(travel + pose_ranges) > 0.1, "Robots only changed counters; no rendered motion was observed"
    record("live_creatures_animate", actor_motion_cm=travel, skeletal_pose_range_cm=pose_ranges,
           activities=[creature.activity for creature in creatures])


def run():
    assert not LEVELS.is_in_play_in_editor(), "Stop the current PIE session before running acceptance"
    assert LEVELS.load_level("/Game/FactoryCtyco/Maps/L_GrowRobots")
    unreal.SystemLibrary.execute_console_command(EDITOR.get_editor_world(), "t.MaxFPS 30")
    yield from wait(5)
    LEVELS.editor_request_begin_play()
    deadline = time.monotonic() + 15
    while True:
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0) if worlds else None
        if pawn:
            break
        assert time.monotonic() < deadline, "PIE did not start"
        yield
    matches = unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.GrowEvolutionWorld)
    assert len(matches) == 1, "Expected one GROW world controller"
    controller = unreal.GameplayStatics.get_player_controller(worlds[0], 0)
    assert isinstance(pawn, unreal.GrowViewPawn)
    assert isinstance(controller, unreal.GrowPlayerController)
    assert isinstance(controller.get_hud(), unreal.GrowEvolutionHUD)
    STATE.update(evolution=matches[0], pawn=pawn, controller=controller, pie_world=worlds[0])
    D = unreal.GrowDecision
    P = unreal.GrowProfession
    yield from reset()
    initial = snapshot()
    assert not world().undo_decision()
    record("empty_world_camera_and_hud", state=initial)
    yield from capture("01_initial")

    # Exercise the same hit regions and input handlers used by the player.
    yield from click_card(1, D.WATER)
    yield from tap("BackSpace")
    yield from settled()
    assert snapshot() == initial, "Backspace did not undo the mouse selection"
    yield from click_card(0, D.RECYCLING)
    yield from click_card(3, D.ENERGY)
    yield from tap("R")
    yield from settled()
    assert snapshot() == initial, "R did not restart the mouse-built sequence"
    record("hud_mouse_selection_and_keyboard_undo_restart", mouse_choices=3)

    # Numeric input is the production binding, not a test-only selector.
    yield from tap("Four")
    assert list(world().history) == [D.ENERGY], "Key 4 did not choose Energy"
    yield from settled()
    stable = snapshot()
    assert not world().choose_decision(D.ENERGY)
    assert snapshot() == stable
    # Check the lock in the same callback as the accepted API call. A long
    # rendered frame after keyboard input can legitimately finish its reveal.
    assert world().choose_decision(D.RECYCLING)
    assert world().transition_remaining > 0
    assert not world().choose_decision(D.WATER), "Accepted a choice during reveal"
    assert list(world().history) == [D.ENERGY, D.RECYCLING]
    yield from settled()
    record("keyboard_choice_transition_lock_and_duplicate_rejection")

    # Rewind across awakening must remove the role and the visible robots.
    before_awaken = snapshot()
    yield from choose(D.AWAKEN)
    assert world().profession == P.BUILDER and world().creature_level >= 1
    assert any(creature_visible(creature) for creature in world().creatures)
    assert world().undo_decision()
    yield from settled()
    assert snapshot() == before_awaken
    assert not any(creature_visible(creature) for creature in world().creatures)
    record("undo_awakening_removes_role_and_hides_robots")

    builder = [D.ENERGY, D.RECYCLING, D.AWAKEN, D.WATER, D.LOGISTICS, D.HABITAT]
    prefixes = yield from route("builder", builder, P.BUILDER, 3, True)
    builder_result = snapshot()
    yield from verify_animation()
    yield from capture("02_builder_level3")
    yield from capture("02_builder_level3_1280x720", 1280, 720)
    assert world().undo_decision()
    yield from settled()
    assert snapshot() == prefixes[-2], "Undo failed to restore the exact preceding outcome"
    yield from choose(builder[-1])
    assert snapshot() == builder_result, "Replaying the same prefix changed the result"
    record("undo_and_replay_are_deterministic")

    caretaker = [D.ENERGY, D.WATER, D.AWAKEN, D.RECYCLING, D.HABITAT, D.LOGISTICS]
    yield from route("caretaker", caretaker, P.CARETAKER, 3, True)
    yield from capture("03_caretaker_level3")
    courier = [D.ENERGY, D.LOGISTICS, D.AWAKEN, D.RECYCLING, D.WATER, D.HABITAT]
    yield from route("courier", courier, P.COURIER, 3, True)
    yield from capture("04_courier_level3")
    early = [D.AWAKEN, D.ENERGY, D.RECYCLING, D.WATER, D.LOGISTICS, D.HABITAT]
    yield from route("early_awakening", early, P.APPRENTICE, 1, False)
    yield from capture("05_early_awakening_level1")
    results = REPORT["routes"]
    assert len({tuple(result["system_levels"]) for result in results.values()}) > 1
    assert len({result["profession"] for result in results.values()}) == 4
    assert {result["creature_level"] for result in results.values()} == {1, 3}
    record("same_six_choices_different_order_changes_profession_and_levels")

    yield from reset()
    assert snapshot() == initial, "Reset did not restore the original simulation state"
    yield from reset()
    assert snapshot() == initial, "Reset is not idempotent"
    record("reset_restores_empty_world")
    yield from capture("06_reset")
    record("screenshots_written", count=len(REPORT["screenshots"]))
    REPORT["passed"] = True


def finish():
    STATE["finishing"] = True
    REPORT["elapsed_seconds"] = round(time.monotonic() - STATE["started"], 1)
    (OUTPUT / "report.json").write_text(json.dumps(REPORT, indent=2), encoding="utf-8")
    (OUTPUT.parent / "latest-playtest.txt").write_text(str(OUTPUT), encoding="utf-8")
    unreal.log("[GROW_EVOLUTION_PLAYTEST] " + json.dumps(REPORT))
    if LEVELS.is_in_play_in_editor():
        LEVELS.editor_request_end_play()
        yield from wait(1)
    unreal.unregister_slate_post_tick_callback(STATE["handle"])
    unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    if QUIT_EDITOR:
        unreal.SystemLibrary.quit_editor()


STATE["steps"] = run()


def tick(delta):
    if STATE["in_tick"]:
        return
    STATE["in_tick"] = True
    try:
        if not STATE["finishing"] and time.monotonic() - STATE["started"] > 160:
            raise TimeoutError("GROW acceptance timed out")
        next(STATE["steps"])
    except StopIteration:
        if not STATE["finishing"]:
            STATE["steps"] = finish()
    except Exception:
        REPORT["passed"] = False
        REPORT["error"] = traceback.format_exc()
        unreal.log_error(REPORT["error"])
        STATE["steps"] = finish()
    finally:
        STATE["in_tick"] = False


STATE["handle"] = unreal.register_slate_post_tick_callback(tick)
