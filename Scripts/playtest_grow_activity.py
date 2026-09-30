"""Short, independent PIE smoke for GROW deliveries and visible reaction pulses."""
from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import time
import traceback

import unreal


PROJECT = Path(unreal.Paths.project_dir()).resolve()
OUTPUT = PROJECT / "Saved" / "GrowEvolutionWork" / (
    "Activity-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ"))
OUTPUT.mkdir(parents=True, exist_ok=False)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EDITOR = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
REPORT = {"passed": False, "checks": {}, "screenshots": [],
          "scope": "PIE delivery work and actual moving reaction meshes."}
STATE = {"started": time.monotonic(), "finishing": False, "in_tick": False}
unreal.EditorPythonScripting.set_keep_python_script_alive(True)


def wait(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        yield


def record(name, **data):
    REPORT["checks"][name] = {"passed": True, **data}
    unreal.log("[GROW_ACTIVITY_CHECK] " + name)


def settled():
    evolution = STATE["world"]
    deadline = time.monotonic() + 10
    while evolution.resolving or evolution.transition_remaining > 0:
        assert time.monotonic() < deadline, "Reaction did not settle"
        yield
    yield


def choose(decision):
    yield from settled()
    assert STATE["world"].choose_decision(decision)
    yield from settled()


def run():
    assert not LEVELS.is_in_play_in_editor(), "Stop the other PIE acceptance before running this smoke"
    assert LEVELS.load_level("/Game/FactoryCtyco/Maps/L_GrowRobots")
    unreal.SystemLibrary.execute_console_command(EDITOR.get_editor_world(), "t.MaxFPS 30")
    yield from wait(2)
    LEVELS.editor_request_begin_play()
    deadline = time.monotonic() + 15
    while True:
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        matches = unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.GrowEvolutionWorld) if worlds else []
        if matches and unreal.GameplayStatics.get_player_pawn(worlds[0], 0):
            break
        assert time.monotonic() < deadline, "PIE did not start"
        yield
    assert len(matches) == 1
    evolution = matches[0]
    STATE["world"] = evolution
    D = unreal.GrowDecision
    evolution.reset_evolution()
    yield from settled()

    # Observe the mesh throughout the first half of a production-length event.
    # No screenshot work occurs here, so renderer stalls cannot mimic movement.
    evolution.upgrade_delay_seconds = 2.0
    yield from choose(D.ENERGY)
    yield from choose(D.RECYCLING)
    assert evolution.choose_decision(D.WATER)
    assert evolution.resolving
    pulses = [component for component in evolution.get_components_by_class(unreal.StaticMeshComponent)
              if component.get_name().startswith("GrowLink_") and "_Pulse" in component.get_name()]
    assert pulses, "No connection pulse meshes were created"
    pulse_positions = {}
    countdowns = []
    serial = evolution.upgrade_serial
    deadline = time.monotonic() + 0.55
    while time.monotonic() < deadline:
        yield
        assert evolution.resolving and evolution.upgrade_serial == serial
        countdowns.append(evolution.evolution_countdown)
        visible = [component for component in pulses if component.is_visible()
                   and not component.get_editor_property("hidden_in_game")]
        assert len(visible) == 1, "Expected exactly the active reaction's visible pulse"
        for component in visible:
            assert component.get_editor_property("static_mesh"), "Pulse is a counter without a rendered mesh"
            pulse_positions.setdefault(component.get_name(), []).append(component.get_world_location())
    distances = {name: max((position - positions[0]).length() for position in positions)
                 for name, positions in pulse_positions.items()}
    assert countdowns[-1] < countdowns[0]
    assert max(distances.values()) > 10, "Visible pulse did not travel along its connection"
    record("visible_pulse_moves_during_two_second_delay", travel_cm=distances,
           countdown_from=countdowns[0], countdown_to=countdowns[-1], source=str(evolution.pending_source),
           target=str(evolution.pending_decision), samples=len(countdowns))

    # Capture after the station reveal has finished, with roughly 1.4 seconds
    # left on the first reaction. This follows the movement measurement.
    screenshot = OUTPUT / "reaction_pulse_formed_station.png"
    REPORT["screenshot_countdown_at_request"] = evolution.evolution_countdown
    print("[captura desactivada]", 1440, 900, str(screenshot))
    deadline = time.monotonic() + 8
    while not screenshot.is_file():
        assert time.monotonic() < deadline, "Activity screenshot was not written"
        yield
    # High-resolution capture writes again after its initial file appears.
    # Preserve the current world through that second render/write pass.
    yield from wait(2.0)
    with screenshot.open("rb") as stream:
        header = stream.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", header[16:24]) == (1440, 900)
    REPORT["screenshots"].append(str(screenshot))

    # Reach a completed courier colony quickly, then observe normal production
    # jobs. Delay tuning is confined to this transient PIE world.
    evolution.reset_evolution()
    yield from settled()
    evolution.upgrade_delay_seconds = 0.15
    for decision in [D.ENERGY, D.LOGISTICS, D.AWAKEN, D.RECYCLING, D.WATER, D.HABITAT]:
        yield from choose(decision)
    assert evolution.is_complete() and evolution.is_successful()
    assert evolution.profession == unreal.GrowProfession.COURIER and evolution.creature_level == 3
    creatures = list(evolution.creatures)
    assert creatures
    for creature in creatures:
        assert creature.species and creature.species.walk_animation and creature.species.idle_animation
        assert creature.body.get_anim_instance(), "Courier has no skeletal animation instance"
    starts = [creature.completed_trips for creature in creatures]
    initial_positions = [creature.get_actor_location() for creature in creatures]
    max_travel = [0.0] * len(creatures)
    delivery_samples = [0] * len(creatures)
    activities = [set() for _ in creatures]
    pairs = [set() for _ in creatures]
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        for index, creature in enumerate(creatures):
            assert creature.work_source != creature.work_target, "Courier has no distinct work destination"
            assert evolution.has_decision(creature.work_source) and evolution.has_decision(creature.work_target)
            assert creature.activity
            activities[index].add(creature.activity)
            pairs[index].add((str(creature.work_source), str(creature.work_target)))
            max_travel[index] = max(max_travel[index], (creature.get_actor_location() - initial_positions[index]).length())
            cargo_visible = creature.cargo.is_visible() and not creature.cargo.get_editor_property("hidden_in_game")
            assert cargo_visible == creature.delivering, "Cargo visibility differs from the delivery leg"
            if creature.delivering:
                delivery_samples[index] += 1
        if all(creature.completed_trips > start for creature, start in zip(creatures, starts)) and all(delivery_samples):
            break
        yield
    increases = [creature.completed_trips - start for creature, start in zip(creatures, starts)]
    assert all(increase > 0 for increase in increases), ("Courier failed to finish a trip within ten seconds", increases)
    assert all(samples > 0 for samples in delivery_samples), "A completed delivery had no visible cargo leg"
    assert all(distance > 10 for distance in max_travel), "Trip counter changed without actual actor movement"
    record("couriers_collect_carry_and_complete_station_trips", completed_trip_increases=increases,
           delivery_samples=delivery_samples, actor_motion_cm=max_travel,
           station_pairs=[sorted(values) for values in pairs], activities=[sorted(values) for values in activities])
    record("idle_and_walk_animations_are_available", creatures=len(creatures))
    evolution.upgrade_delay_seconds = 2.0
    REPORT["passed"] = True


def finish():
    STATE["finishing"] = True
    REPORT["elapsed_seconds"] = round(time.monotonic() - STATE["started"], 1)
    (OUTPUT / "report.json").write_text(json.dumps(REPORT, indent=2), encoding="utf-8")
    (OUTPUT.parent / "latest-activity-playtest.txt").write_text(str(OUTPUT), encoding="utf-8")
    unreal.log("[GROW_ACTIVITY_PLAYTEST] " + json.dumps(REPORT))
    if LEVELS.is_in_play_in_editor():
        LEVELS.editor_request_end_play()
        yield from wait(1)
    unreal.unregister_slate_post_tick_callback(STATE["handle"])
    unreal.EditorPythonScripting.set_keep_python_script_alive(False)


def tick(delta):
    if STATE["in_tick"]:
        return
    STATE["in_tick"] = True
    try:
        if not STATE["finishing"] and time.monotonic() - STATE["started"] > 45:
            raise TimeoutError("GROW activity smoke timed out")
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


STATE["steps"] = run()
STATE["handle"] = unreal.register_slate_post_tick_callback(tick)
