"""Rendered PIE acceptance for delayed GROW interactions.

Run through Unreal MCP execute_python. Evidence is isolated from the original
evolution acceptance; all temporary tuning applies only to the PIE actor.
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
OUTPUT = PROJECT / "Saved" / "GrowEvolutionWork" / (
    "Interactions-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ"))
OUTPUT.mkdir(parents=True, exist_ok=False)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EDITOR = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
QUIT_EDITOR = os.environ.get("GROW_TEST_QUIT_EDITOR", "0") == "1"
REPORT = {
    "passed": False,
    "checks": {},
    "routes": {},
    "events": [],
    "screenshots": [],
    "scope": "Rendered PIE; delayed upgrades, observed dependencies, cancellation, final result timing and production input.",
}
STATE = {"started": time.monotonic(), "finishing": False, "in_tick": False}
unreal.EditorPythonScripting.set_keep_python_script_alive(True)


def wait(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        yield


def record(name, **values):
    REPORT["checks"][name] = {"passed": True, **values}
    unreal.log("[GROW_INTERACTION_CHECK] " + name)


def world():
    return STATE["evolution"]


def game_time():
    return unreal.GameplayStatics.get_time_seconds(STATE["pie_world"])


def snapshot():
    evolution = world()
    return {
        "history": [str(value) for value in evolution.history],
        "system_levels": list(evolution.system_levels),
        "profession": str(evolution.profession),
        "creature_level": evolution.creature_level,
        "complete": evolution.is_complete(),
        "successful": evolution.is_successful(),
    }


def busy():
    return world().resolving or world().transition_remaining > 0


def queue_empty():
    assert not world().resolving
    assert world().pending_upgrade_count == 0
    assert world().evolution_countdown == 0


def network_snapshot():
    return [{"source": str(link.source), "target": str(link.target),
             "required_level": link.required_level, "active": link.active}
            for link in world().interactions]


def verify_network():
    links = network_snapshot()
    nodes = {str(value) for value in STATE["decisions"]}
    assert links, "The six systems have no interaction graph"
    assert {link["source"] for link in links} == nodes, "A system cannot help any other system"
    assert {link["target"] for link in links} == nodes, "A system cannot receive help"
    assert all(link["source"] != link["target"] for link in links), "Self-links do not connect systems"
    assert all(1 <= link["required_level"] <= 3 for link in links)
    assert world().active_links == sum(link["active"] for link in links)
    REPORT["interaction_graph"] = links
    record("all_six_systems_have_incoming_and_outgoing_links", nodes=6, links=len(links))


def choose_now(decision):
    """Only the newly placed node may become level one synchronously."""
    evolution = world()
    assert not busy()
    before = list(evolution.system_levels)
    history = list(evolution.history)
    serial = evolution.upgrade_serial
    index = STATE["decisions"].index(decision)
    assert decision not in history
    started = {"wall": time.monotonic(), "game": game_time()}
    assert evolution.choose_decision(decision), "Decision rejected: " + str(decision)
    expected = before[:]
    expected[index] = 1
    assert list(evolution.system_levels) == expected, {
        "error": "An existing system upgraded synchronously", "decision": str(decision),
        "before": before, "after": list(evolution.system_levels)}
    assert evolution.upgrade_serial == serial, "Placement applied a queued upgrade immediately"
    assert list(evolution.history) == history + [decision]
    assert evolution.has_decision(decision)
    assert evolution.creature_level == evolution.decision_level(unreal.GrowDecision.AWAKEN)
    assert not evolution.is_complete(), "Completion appeared before the placement/reactions finished"
    assert not evolution.is_successful()
    assert not evolution.outcome_text()
    if evolution.resolving:
        assert evolution.pending_upgrade_count > 0
        assert evolution.evolution_countdown > 0
        assert evolution.pending_reason
        assert abs(evolution.evolution_countdown - evolution.upgrade_delay_seconds) < 0.01
    stable = snapshot()
    assert not evolution.choose_decision(decision), "A repeated choice was accepted"
    assert snapshot() == stable
    return started


def drain(label, timing=False, started=None):
    """Observe actual level changes, without screenshots or blocking work."""
    evolution = world()
    delay = evolution.upgrade_delay_seconds
    pending = evolution.pending_upgrade_count
    deadline = time.monotonic() + max(15, pending * (delay + 2) + 8)
    previous_levels = list(evolution.system_levels)
    previous_serial = evolution.upgrade_serial
    last_wall = started["wall"] if started else time.monotonic()
    last_game = started["game"] if started else game_time()
    events = []
    upgraded = set()
    while busy():
        assert time.monotonic() < deadline, "Reaction chain failed to terminate: " + label
        assert not evolution.is_complete(), "Final result appeared with pending reactions"
        assert not evolution.is_successful()
        assert not evolution.outcome_text()
        if evolution.resolving:
            assert evolution.pending_upgrade_count > 0
            assert evolution.evolution_countdown > 0
        yield
        levels = list(evolution.system_levels)
        serial = evolution.upgrade_serial
        if serial != previous_serial:
            assert serial == previous_serial + 1, "Several delayed upgrades collapsed into one observed frame"
            upgrade = evolution.last_upgrade
            index = STATE["decisions"].index(upgrade.target)
            expected = previous_levels[:]
            expected[index] += 1
            assert levels == expected, {"error": "Upgrade changed an unrelated node", "label": label,
                                        "before": previous_levels, "after": levels}
            assert levels[index] == upgrade.level and 2 <= upgrade.level <= 3
            assert str(upgrade.target) not in upgraded, "A node upgraded twice in one decision"
            upgraded.add(str(upgrade.target))
            assert upgrade.reason
            source_index = STATE["decisions"].index(upgrade.source)
            matching_links = [link for link in evolution.interactions
                              if link.source == upgrade.source and link.target == upgrade.target]
            assert matching_links, "Upgrade has no corresponding interaction edge"
            assert any(previous_levels[source_index] >= link.required_level for link in matching_links), (
                "Upgrade ran before its source reached the required level", str(upgrade.source), str(upgrade.target))
            now_wall, now_game = time.monotonic(), game_time()
            event = {"route": label, "serial": serial, "source": str(upgrade.source),
                     "target": str(upgrade.target), "level": upgrade.level,
                     "reason": upgrade.reason, "levels_before": previous_levels,
                     "levels_after": levels,
                     "wall_interval_seconds": round(now_wall - last_wall, 4),
                     "game_interval_seconds": round(now_game - last_game, 4),
                     "delay_seconds": delay, "timed": timing}
            REPORT["events"].append(event)
            events.append(event)
            if timing:
                # Sampling starts after the preceding rendered frame. One frame
                # of tolerance avoids false failures due to tick boundaries.
                assert now_wall - last_wall >= delay - 0.15, ("Upgrade happened before its real-time delay", event)
                assert now_game - last_game >= delay - 0.12, ("Upgrade happened before its game-time delay", event)
            last_wall, last_game = now_wall, now_game
            previous_levels, previous_serial = levels, serial
        else:
            assert levels == previous_levels, "Levels changed without an upgrade event"
        assert evolution.creature_level == evolution.decision_level(unreal.GrowDecision.AWAKEN)
    queue_empty()
    assert len(events) == pending, {"error": "Pending upgrades were lost or added unexpectedly", "label": label,
                                    "scheduled": pending, "observed": len(events)}
    if len(evolution.history) == 6:
        assert evolution.is_complete(), "Finished six decisions never produced a final result"
        assert evolution.outcome_text()
    else:
        assert not evolution.is_complete()
    yield
    return events


def reset():
    world().reset_evolution()
    yield from drain("reset")
    assert not list(world().history)
    assert list(world().system_levels) == [0] * 6
    assert world().creature_level == 0
    assert world().profession == unreal.GrowProfession.APPRENTICE
    assert world().upgrade_serial == 0
    assert not any(creature_visible(creature) for creature in world().creatures)
    assert world().active_links == 0


def choose(decision, label, timing=False):
    started = choose_now(decision)
    return (yield from drain(label, timing=timing, started=started))


def assert_stable(seconds, expected):
    serial = world().upgrade_serial
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        assert snapshot() == expected, "Cancelled/finished work later changed gameplay state"
        assert world().upgrade_serial == serial, "A cancelled or finished upgrade executed later"
        queue_empty()
        yield


def creature_visible(creature):
    return (not creature.get_editor_property("hidden") and creature.body.is_visible()
            and not creature.body.get_editor_property("hidden_in_game"))


def tap(key):
    # A non-consuming production binding can return false while queuing input.
    STATE["pawn"].camera_controls.send_editor_test_input(key, 1.0, True)
    yield
    STATE["pawn"].camera_controls.send_editor_test_input(key, 0.0, False)
    yield


def click_card(index):
    controller = STATE["controller"]
    pixel_width, pixel_height = controller.get_viewport_size()
    assert pixel_width > 0 and pixel_height > 0
    scale = min(1.8, max(0.5, min(pixel_width / 1440.0, pixel_height / 900.0)))
    width, height = pixel_width / scale, pixel_height / scale
    card_width = (width - 48 - 5 * 10) / 6
    x = round((24 + (card_width + 10) * index + card_width / 2) * scale)
    y = round((height - 194 + 70) * scale)
    controller.set_mouse_location(x, y)
    yield
    yield from tap("LeftMouseButton")
    REPORT.setdefault("mouse_clicks", []).append({
        "card": index, "viewport": [pixel_width, pixel_height], "position": [x, y]})


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
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    actual_size = struct.unpack(">II", header[16:24])
    assert actual_size == (width, height), (name, actual_size)
    REPORT.setdefault("screenshot_resolutions", {})[name] = list(actual_size)


def start_pie():
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
    assert len(matches) == 1
    controller = unreal.GameplayStatics.get_player_controller(worlds[0], 0)
    assert isinstance(pawn, unreal.GrowViewPawn)
    assert isinstance(controller, unreal.GrowPlayerController)
    assert isinstance(controller.get_hud(), unreal.GrowEvolutionHUD)
    STATE.update(evolution=matches[0], pawn=pawn, controller=controller, pie_world=worlds[0])


def run():
    yield from start_pie()
    D, P = unreal.GrowDecision, unreal.GrowProfession
    STATE["decisions"] = [D.RECYCLING, D.WATER, D.LOGISTICS, D.ENERGY, D.HABITAT, D.AWAKEN]
    assert abs(world().upgrade_delay_seconds - 2.0) < 0.001, "Player-facing delay must default to two seconds"
    REPORT["production_delay_seconds"] = world().upgrade_delay_seconds
    yield from reset()
    verify_network()
    initial = snapshot()

    # Authored dependency example: neither Energy nor Recycling can advance
    # without Water. Water first raises Energy, whose new level enables Recycling.
    yield from choose(D.ENERGY, "timed_energy", timing=True)
    yield from choose(D.RECYCLING, "timed_recycling", timing=True)
    assert world().decision_level(D.ENERGY) == 1
    assert world().decision_level(D.RECYCLING) == 1
    assert world().upgrade_serial == 0, "Systems advanced without their dependency"
    recycling_power = [link for link in world().interactions
                       if link.source == D.ENERGY and link.target == D.RECYCLING]
    assert len(recycling_power) == 1 and recycling_power[0].required_level == 2, (
        "Recycling must depend on upgraded Energy, not merely on queue ordering")
    before_water = snapshot()
    started = choose_now(D.WATER)
    assert world().resolving and world().pending_upgrade_count == 2
    stable = snapshot()
    assert not world().choose_decision(D.AWAKEN), "A new decision interrupted a running reaction chain"
    assert snapshot() == stable
    events = yield from drain("timed_water_chain", timing=True, started=started)
    assert [(event["source"], event["target"], event["level"]) for event in events] == [
        (str(D.WATER), str(D.ENERGY), 2), (str(D.ENERGY), str(D.RECYCLING), 2)]
    assert events[0]["levels_after"][3] == 2 and events[0]["levels_after"][0] == 1
    assert time.monotonic() - started["wall"] >= 3.8
    record("two_second_upgrades_are_sequential_and_dependency_driven", events=events)
    for decision in [D.AWAKEN, D.LOGISTICS, D.HABITAT]:
        yield from choose(decision, "timed_full_route", timing=True)
    REPORT["routes"]["timed"] = snapshot()
    assert world().is_complete()
    record("final_result_waits_for_last_upgrade", final_state=snapshot())
    yield from capture("01_timed_chain_complete")

    # Rebuild the known two-event prefix quickly; retain production timing while
    # cancelling so a stale event has enough time to reveal itself afterward.
    world().upgrade_delay_seconds = 0.15
    yield from reset()
    yield from choose(D.ENERGY, "cancel_prefix_energy")
    yield from choose(D.RECYCLING, "cancel_prefix_recycling")
    assert snapshot() == before_water
    world().upgrade_delay_seconds = 2.0
    choose_now(D.WATER)
    deadline = time.monotonic() + 8
    while world().upgrade_serial == 0:
        assert time.monotonic() < deadline
        yield
    assert world().upgrade_serial == 1 and world().resolving
    assert world().pending_upgrade_count == 1
    yield from tap("BackSpace")
    assert list(world().history) == [D.ENERGY, D.RECYCLING], "Backspace did not cancel the active decision"
    yield from drain("undo_mid_chain")
    assert snapshot() == before_water, "Undo retained part of a partially applied reaction chain"
    yield from assert_stable(2.25, before_water)
    record("undo_mid_chain_restores_prefix_and_cancels_pending_upgrade")

    choose_now(D.WATER)
    locked_history = list(world().history)
    yield from tap("Six")
    assert list(world().history) == locked_history, "Numeric input bypassed the active chain lock"
    yield from click_card(2)
    assert list(world().history) == locked_history, "HUD mouse input bypassed the active chain lock"
    assert world().resolving, "Input test outlasted both production-timed upgrades"
    yield from tap("R")
    assert not list(world().history), "R did not cancel the active chain and restart"
    yield from drain("reset_mid_chain")
    assert snapshot() == initial
    yield from assert_stable(2.25, initial)
    record("keyboard_and_mouse_respect_lock_reset_cancels_old_events")

    yield from tap("Four")
    assert list(world().history) == [D.ENERGY], "Numeric input did not choose an available decision"
    yield from drain("numeric_available_choice")
    yield from click_card(0)
    assert list(world().history) == [D.ENERGY, D.RECYCLING], "HUD click did not choose an available decision"
    yield from drain("mouse_available_choice")
    yield from tap("R")
    yield from drain("input_reset")
    assert snapshot() == initial
    record("numeric_and_mouse_input_choose_available_systems")

    # These authored outcomes exercise all professions at a shorter PIE-only
    # delay; the real two-second behavior was measured above without screenshots.
    world().upgrade_delay_seconds = 0.15
    routes = [
        ("builder", [D.ENERGY, D.RECYCLING, D.AWAKEN, D.WATER, D.LOGISTICS, D.HABITAT], P.BUILDER),
        ("caretaker", [D.ENERGY, D.WATER, D.AWAKEN, D.RECYCLING, D.HABITAT, D.LOGISTICS], P.CARETAKER),
        ("courier", [D.ENERGY, D.LOGISTICS, D.AWAKEN, D.RECYCLING, D.WATER, D.HABITAT], P.COURIER),
    ]
    for name, decisions, profession in routes:
        yield from reset()
        prefixes = [snapshot()]
        for decision in decisions:
            yield from choose(decision, name)
            prefixes.append(snapshot())
        assert world().profession == profession, (name, snapshot())
        assert world().creature_level == 3, (name, snapshot())
        assert world().is_complete() and world().is_successful()
        assert world().creatures and all(creature_visible(creature) for creature in world().creatures)
        assert all(creature.level == 3 and creature.profession == profession for creature in world().creatures)
        stable = snapshot()
        for decision in decisions:
            assert not world().choose_decision(decision), "A seventh/repeated decision was accepted"
            assert snapshot() == stable
        yield from assert_stable(0.3, stable)
        REPORT["routes"][name] = stable
        record("delayed_route_" + name, state=stable, upgrades=world().upgrade_serial)
        if name == "builder":
            assert world().undo_decision()
            yield from drain("undo_finished_route")
            assert snapshot() == prefixes[-2]
            yield from choose(decisions[-1], "builder_replay")
            assert snapshot() == stable, "Undo and replay produced a different outcome"
            record("settled_undo_and_replay_are_deterministic")
        yield from capture("02_" + name + "_connected", 1280, 720)
    assert len({tuple(REPORT["routes"][name]["system_levels"]) for name, _, _ in routes}) > 1
    record("order_still_changes_system_levels_and_profession")
    verify_network()
    assert world().active_links > 0
    record("active_links_match_current_dependencies", active_links=world().active_links)

    # Dedicated visual evidence avoids perturbing the timing measurements above.
    yield from reset()
    yield from choose(D.ENERGY, "visual_prefix_energy")
    yield from choose(D.RECYCLING, "visual_prefix_recycling")
    world().upgrade_delay_seconds = 2.0
    choose_now(D.WATER)
    REPORT["captured_reaction"] = {"source": str(world().pending_source),
                                   "target": str(world().pending_decision),
                                   "reason": world().pending_reason,
                                   "countdown": world().evolution_countdown}
    yield from capture("03_reaction_in_progress")
    # A screenshot can advance several rendered frames, so do not reuse the
    # event-count observer across it. Reset deliberately discards that chain.
    yield from reset()
    assert snapshot() == initial
    record("reset_restores_empty_world_and_production_delay", delay_seconds=world().upgrade_delay_seconds)
    record("screenshots_written", count=len(REPORT["screenshots"]))
    REPORT["passed"] = True


def finish():
    STATE["finishing"] = True
    REPORT["elapsed_seconds"] = round(time.monotonic() - STATE["started"], 1)
    (OUTPUT / "report.json").write_text(json.dumps(REPORT, indent=2), encoding="utf-8")
    (OUTPUT.parent / "latest-interactions-playtest.txt").write_text(str(OUTPUT), encoding="utf-8")
    unreal.log("[GROW_INTERACTIONS_PLAYTEST] " + json.dumps(REPORT))
    if LEVELS.is_in_play_in_editor():
        LEVELS.editor_request_end_play()
        yield from wait(1)
    unreal.unregister_slate_post_tick_callback(STATE["handle"])
    unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    if QUIT_EDITOR:
        unreal.SystemLibrary.quit_editor()


def tick(delta):
    # Screenshot work can pump Slate again inside this callback.
    if STATE["in_tick"]:
        return
    STATE["in_tick"] = True
    try:
        if not STATE["finishing"] and time.monotonic() - STATE["started"] > 240:
            raise TimeoutError("GROW interaction acceptance timed out")
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
