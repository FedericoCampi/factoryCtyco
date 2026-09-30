"""PIE acceptance for earned factory milestones, persistence and the annex.

Stock enters through inventory APIs. Recipes, processing cycles, conveyors,
production/delivery counters and site delays all run at their native speed.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import time
import traceback

import unreal

PROJECT = Path(unreal.Paths.project_dir()).resolve()
STAMP = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ")
OUTPUT = PROJECT / "Saved" / "SiteProgressWork" / ("Playtest-" + STAMP)
OUTPUT.mkdir(parents=True, exist_ok=False)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EDITOR = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
REPORT = {"passed": False, "checks": {}, "reveals": [], "screenshots": [], "save_slots": [],
          "scope": "Original L_FactoryDemo; real production and conveyor milestones, timed scenery, persistence and annex access.",
          "acceleration": "None. Native processor cycles, belt travel and site timers."}
STATE = {"started": time.monotonic(), "finishing": False, "in_tick": False}
RESUME_FROM = globals().get("FACTORY_SITE_RESUME_FROM")
if RESUME_FROM:
    resume_path = Path(RESUME_FROM).resolve()
    assert resume_path.is_relative_to((PROJECT / "Saved" / "SiteProgressWork").resolve())
    prior = json.loads((resume_path / "report.json").read_text(encoding="utf-8"))
    assert prior["checks"]["connector_circuit_dismantles_without_material_loss"]["passed"]
    for key in ("checks", "reveals", "screenshots", "save_slots"):
        REPORT[key] = prior[key]
    REPORT["prior_runs"] = [{"report": str(resume_path / "report.json"), "passed": prior["passed"],
                            "elapsed_seconds": prior["elapsed_seconds"], "error": prior.get("error")}]
    REPORT["scope"] += " Persistence and occupied-workshop continuation from the recorded native-production run."
unreal.EditorPythonScripting.set_keep_python_script_alive(True)


def wait(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        yield


def record(name, **values):
    REPORT["checks"][name] = {"passed": True, **values}
    unreal.log("[FACTORY_SITE_CHECK] " + name)


def factory():
    return STATE["factory"]


def machine(identity):
    return next(building for building in factory().buildings() if str(building.persistent_id) == identity)


def amounts(inventory):
    return {str(key): int(value) for key, value in inventory.items.items()}


def snapshot():
    return {"inventory": amounts(STATE["inventory"]),
            "piles": {str(pile.persistent_id): pile.amount for pile in STATE["piles"]},
            "produced": factory().plates_produced, "delivered": factory().plates_delivered,
            "site_stage": factory().site_stage,
            "site_remaining": round(factory().site_transition_remaining, 6),
            "buildings": {str(building.persistent_id): {
                "input": amounts(building.input), "output": amounts(building.output),
                "progress": round(building.progress_seconds, 6), "paid": building.paid_scrap,
                "filter": str(building.storage_item), "yaw": round(building.get_actor_rotation().yaw, 3),
                "position": [round(value, 3) for value in (building.get_actor_location().x,
                             building.get_actor_location().y, building.get_actor_location().z)]}
                for building in factory().buildings()}}


def mass():
    def weight(inventory):
        return inventory.get_quantity("Scrap") + inventory.get_quantity("Fragments") + 2 * inventory.get_quantity("Plate")
    return weight(STATE["inventory"]) + sum(pile.amount for pile in STATE["piles"]) + sum(
        weight(building.input) + weight(building.output) + building.paid_scrap for building in factory().buildings())


def save_slot(suffix):
    slot = "FactoryCtycoSite_" + STAMP + "_" + suffix
    if slot not in REPORT["save_slots"]:
        REPORT["save_slots"].append(slot)
    return slot


def save_bytes(slot):
    assert slot.startswith("FactoryCtycoSite_") and Path(slot).name == slot
    data = (PROJECT / "Saved" / "SaveGames" / (slot + ".sav")).read_bytes()
    assert data[:4] == b"GVAS" and b"/Script/FactoryCtycoRuntime.FactoryDemoSave\x00" in data
    assert data.endswith(b"\x05\x00\x00\x00None\x00\x00\x00\x00\x00")
    return data


def scalar_tag(name, kind):
    """UE 5.6 scalar tag: name, FPropertyTypeName (no parameters), size, flags.

    Protected SaveGame fields cannot be edited through Python reflection.
    Verify the exact scalar layout against native saves before copying fixtures.
    """
    assert kind in ("IntProperty", "FloatProperty")
    def fstring(value):
        encoded = value.encode("ascii") + b"\x00"
        return struct.pack("<i", len(encoded)) + encoded
    return fstring(name) + fstring(kind) + struct.pack("<iiB", 0, 4, 0)


def scalar_value(data, name, kind, default=None):
    tag = scalar_tag(name, kind)
    count = data.count(tag)
    assert count <= 1, ("Ambiguous SaveGame scalar", name, count)
    if not count:
        assert (name.encode("ascii") + b"\x00") not in data, ("Unexpected scalar layout", name)
        return default
    offset = data.index(tag) + len(tag)
    assert offset + 4 <= len(data) - 13
    return struct.unpack_from("<i" if kind == "IntProperty" else "<f", data, offset)[0]


def fixture_save(source_slot, suffix, overrides, remove=()):
    """Write only a new test-owned slot; preserve every untouched serialized byte."""
    data = save_bytes(source_slot)
    kinds = {"Version": "IntProperty", "SiteStage": "IntProperty",
             "SiteTransitionRemaining": "FloatProperty", "PlatesProduced": "IntProperty"}
    for name in remove:
        tag = scalar_tag(name, kinds[name])
        scalar_value(data, name, kinds[name])
        if tag in data:
            start = data.index(tag)
            data = data[:start] + data[start + len(tag) + 4:]
    for name, value in overrides.items():
        kind = kinds[name]
        tag = scalar_tag(name, kind)
        scalar_value(data, name, kind)
        encoded = struct.pack("<i" if kind == "IntProperty" else "<f", value)
        if tag in data:
            start = data.index(tag) + len(tag)
            data = data[:start] + encoded + data[start + 4:]
        else:
            data = data[:-13] + tag + encoded + data[-13:]
        assert scalar_value(data, name, kind) == value
    slot = save_slot(suffix)
    path = PROJECT / "Saved" / "SaveGames" / (slot + ".sav")
    with path.open("xb") as stream:
        stream.write(data)
    assert save_bytes(slot) == data
    return slot


def move(position):
    pawn = STATE["pawn"]
    pawn.character_movement.stop_movement_immediately()
    pawn.set_actor_location(position, False, True)


def near(building):
    for x, y in [(0, 145), (0, -145), (145, 0), (-145, 0), (145, 145)]:
        move(building.get_actor_location() + unreal.Vector(x, y, 92))
        STATE["demo"].refresh_focus()
        if STATE["demo"].focused_building == building:
            return
    raise AssertionError("No interaction side for " + str(building.persistent_id))


def frame_annex():
    move(unreal.Vector(0, 1550, 100))
    camera = STATE["camera"]
    camera.reset_camera()
    for _ in range(5):
        camera.send_editor_test_input("MouseScrollDown", 1.0, True)
        yield
        camera.send_editor_test_input("MouseScrollDown", 0.0, False)
        yield
    yield from wait(0.6)


def capture(name):
    path = OUTPUT / (name + ".png")
    print("[captura desactivada]", 1440, 900, str(path))
    deadline = time.monotonic() + 8
    while not path.is_file():
        assert time.monotonic() < deadline, "Screenshot did not appear"
        yield
    # Unreal can write twice: preserve the scene through its final render pass.
    yield from wait(2.0)
    with path.open("rb") as stream:
        header = stream.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", header[16:24]) == (1440, 900)
    REPORT["screenshots"].append(str(path))


def inspect_landmarks():
    result = {}
    for stage, landmark in STATE["landmarks"].items():
        assert 0 <= landmark.reveal_alpha <= 1
        assert landmark.marker_pieces
        for piece in list(landmark.marker_pieces) + [landmark.scan_beam]:
            assert piece.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION
        complete = factory().site_stage >= stage
        if complete:
            assert abs(landmark.reveal_alpha - 1) < 0.001
            assert landmark.visual.is_visible()
        elif factory().site_stage + 1 != stage or factory().site_transition_remaining <= 0:
            assert landmark.reveal_alpha < 0.001
            assert not landmark.visual.is_visible()
        expected_collision = (unreal.CollisionEnabled.QUERY_AND_PHYSICS
                              if landmark.solid_when_built and complete else unreal.CollisionEnabled.NO_COLLISION)
        assert landmark.visual.get_collision_enabled() == expected_collision
        result[str(stage)] = {"name": landmark.get_actor_label(), "alpha": landmark.reveal_alpha,
                              "visible": landmark.visual.is_visible(), "solid": landmark.solid_when_built}
    return result


def floor_trace(x, y):
    hit = unreal.SystemLibrary.line_trace_single(STATE["world"], unreal.Vector(x, y, 10),
            unreal.Vector(x, y, -30), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False,
            [STATE["pawn"]], unreal.DrawDebugTrace.NONE)
    fields = unreal.get_default_object(unreal.GameplayStatics).call_method("BreakHitResult", args=(hit,)) if hit else None
    assert fields and fields[0], ("No continuous floor", x, y)
    assert abs(fields[5].z) <= 8 and fields[7].z >= 0.9, ("Uneven annex floor", x, y, fields[5], fields[7])
    return round(fields[5].z, 3)


def physical_annex_access():
    heights = [floor_trace(x, y) for x in (-165, 0, 165) for y in (1000, 1100, 1150, 1200, 1250, 1400)]
    for x in range(-800, 801, 200):
        for y in range(1600, 2201, 200):
            for dx, dy in [(-95, -95), (-95, 95), (95, -95), (95, 95), (0, 0)]:
                heights.append(floor_trace(x + dx, y + dy))
    move(unreal.Vector(0, 800, 100))
    yield from wait(0.4)
    pawn = STATE["pawn"]
    origin = pawn.get_actor_location()
    deadline = time.monotonic() + 12
    minimum_z, maximum_z = origin.z, origin.z
    while pawn.get_actor_location().y < 2190:
        assert time.monotonic() < deadline, "Character could not walk through the original gate to the annex"
        pawn.add_movement_input(unreal.Vector(0, 1, 0), 1.0)
        yield
        position = pawn.get_actor_location()
        minimum_z, maximum_z = min(minimum_z, position.z), max(maximum_z, position.z)
        assert abs(position.x) < 10, "A collision diverted the central access route"
        assert pawn.character_movement.is_moving_on_ground(), "Character left the floor at the annex seam"
    pawn.character_movement.stop_movement_immediately()
    record("annex_floor_and_character_access", floor_samples=len(heights), floor_z_range=[min(heights), max(heights)],
           walked_cm=(pawn.get_actor_location() - origin).length(), character_z_range=[minimum_z, maximum_z])


def wait_for_reveal(stage, label, checkpoint=False):
    deadline = time.monotonic() + 150
    while factory().site_stage == stage and factory().site_transition_remaining <= 0:
        assert time.monotonic() < deadline, "Milestone was not earned: " + label
        assert mass() == STATE["expected_mass"]
        yield
    assert factory().site_stage == stage, "Milestone advanced without a visible pending phase"
    remaining = factory().site_transition_remaining
    assert 1.8 <= remaining <= 2.001, ("Reveal did not begin with a two-second delay", stage, remaining)
    assert factory().site_current_progress() >= factory().site_next_target()
    if checkpoint:
        yield from wait(0.4)
        remaining = factory().site_transition_remaining
        assert 0.5 < remaining < 1.9
        factory().set_editor_property("save_slot", save_slot("pending"))
        expected = snapshot()
        assert factory().save_factory(STATE["pawn"])
        yield from wait(0.3)
        assert factory().load_factory(STATE["pawn"])
        assert snapshot() == expected, "Pending save/load changed site time or production state"
        remaining = factory().site_transition_remaining
        record("save_load_preserves_pending_reveal_and_factory", state=expected)
    started, game_started = time.monotonic(), unreal.GameplayStatics.get_time_seconds(STATE["world"])
    alphas, scan_positions = [], []
    landmark = STATE["landmarks"][stage + 1]
    while factory().site_stage == stage:
        assert time.monotonic() - started < remaining + 4, "Reveal failed to finish"
        assert factory().site_transition_remaining > 0
        assert mass() == STATE["expected_mass"], "A site reveal consumed or granted resources"
        if 0.05 < landmark.reveal_alpha < 0.95:
            assert landmark.visual.is_visible() and landmark.scan_beam.is_visible()
            alphas.append(landmark.reveal_alpha)
            scan_positions.append(landmark.scan_beam.get_world_location())
        yield
    elapsed = time.monotonic() - started
    game_elapsed = unreal.GameplayStatics.get_time_seconds(STATE["world"]) - game_started
    assert factory().site_stage == stage + 1
    assert elapsed >= remaining - 0.18 and game_elapsed >= remaining - 0.12, ("Reveal completed too early", remaining, elapsed, game_elapsed)
    assert alphas and max(alphas) - min(alphas) > 0.15, "Landmark appeared without progressive assembly"
    assert max((position - scan_positions[0]).length() for position in scan_positions) > 10, "Assembly scan did not move"
    yield
    REPORT["reveals"].append({"label": label, "stage": stage + 1, "remaining_at_observation": remaining,
                              "wall_seconds": round(elapsed, 4), "game_seconds": round(game_elapsed, 4),
                              "alpha_range": [min(alphas), max(alphas)], "checkpoint": checkpoint})
    record("earned_" + label, produced=factory().plates_produced, delivered=factory().plates_delivered,
           landmarks=inspect_landmarks())


def verify_connector_delivery():
    """Transport an already earned plate from the old yard into the annex."""
    inventory = STATE["inventory"]
    count_before = len(factory().buildings())
    assert inventory.add_item(factory().resource("Scrap"), 26) == 26
    STATE["expected_mass"] += 26
    scrap_before = inventory.get_quantity("Scrap")
    plate_before = inventory.get_quantity("Plate")
    move(unreal.Vector(600, 800, 100))
    created = []
    for index, y in [(2, 800), (3, 1000), (3, 1200), (3, 1400), (2, 1600)]:
        point = unreal.Vector(0, y, 4)
        assert not factory().placement_problem(point), (point, factory().placement_problem(point))
        building = STATE["demo"].build_at(index, point, 1)
        assert building, STATE["demo"].notification
        if index == 2:
            building.set_editor_property("storage_item", "Plate")
            building.refresh_visuals()
        created.append(building)
    source, destination = created[0], created[-1]
    assert inventory.remove_item("Plate", 1) == 1
    assert source.input.add_item(factory().resource("Plate"), 1) == 1
    delivered_before = factory().plates_delivered
    started = time.monotonic()
    seen_on_belts = set()
    deadline = started + 8
    while destination.input.get_quantity("Plate") != 1:
        assert time.monotonic() < deadline, "The corridor did not deliver the plate to the annex"
        assert mass() == STATE["expected_mass"]
        for building in created[1:-1]:
            if building.input.get_quantity("Plate"):
                seen_on_belts.add(round(building.get_actor_location().y))
        yield
    assert seen_on_belts == {1000, 1200, 1400}, seen_on_belts
    assert factory().plates_delivered == delivered_before + 1
    assert all(building.connected for building in created[:-1])
    assert mass() == STATE["expected_mass"]
    record("old_yard_to_annex_conveyor_delivery", connector_y=sorted(seen_on_belts),
           elapsed_seconds=round(time.monotonic() - started, 3), source_y=800, destination_y=1600,
           orientation_degrees=90, additional_deliveries=1)
    yield from frame_annex()
    yield from capture("06_connected_yard_and_annex")
    near(destination)
    STATE["demo"].withdraw()
    assert inventory.get_quantity("Plate") == plate_before
    for building in reversed(created):
        near(building)
        assert STATE["demo"].dismantle()
    assert len(factory().buildings()) == count_before
    assert inventory.get_quantity("Scrap") == scrap_before
    assert mass() == STATE["expected_mass"]
    record("connector_circuit_dismantles_without_material_loss")


def verify_occupied_workshop(final_slot, final_state, pending_slot):
    """Reload inside an assembling workshop and walk out before collision turns on."""
    workshop = STATE["landmarks"][1]
    assert workshop.solid_when_built
    factory().set_editor_property("save_slot", pending_slot)
    assert factory().load_factory(STATE["pawn"])
    yield
    assert workshop.visual.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION
    centre = workshop.get_actor_location()
    move(unreal.Vector(centre.x, centre.y, 100))
    slot = save_slot("pending_occupied_workshop")
    factory().set_editor_property("save_slot", slot)
    assert factory().save_factory(STATE["pawn"])
    remaining = factory().site_transition_remaining
    assert 0 < remaining < 2
    assert factory().load_factory(STATE["pawn"])
    assert abs(factory().site_transition_remaining - remaining) < 0.00001
    deadline = time.monotonic() + 5
    while factory().site_stage == 0:
        assert time.monotonic() < deadline
        assert workshop.visual.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION
        yield
    yield from wait(0.2)
    pawn = STATE["pawn"]
    position = pawn.get_actor_location()
    assert abs(position.x - centre.x) < 5 and abs(position.y - centre.y) < 5, "Workshop reveal ejected the occupying robot"
    assert workshop.visual.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION, "Workshop became solid around its occupant"
    started = pawn.get_actor_location()
    deadline = time.monotonic() + 4
    while pawn.get_actor_location().y < centre.y + 250:
        assert time.monotonic() < deadline, "Robot could not leave the completed workshop"
        pawn.add_movement_input(unreal.Vector(0, 1, 0), 1.0)
        yield
        assert pawn.character_movement.is_moving_on_ground()
    pawn.character_movement.stop_movement_immediately()
    yield from wait(0.2)
    assert workshop.visual.get_collision_enabled() == unreal.CollisionEnabled.QUERY_AND_PHYSICS
    record("pending_reload_keeps_occupied_workshop_nonblocking_until_exit",
           restored_remaining=remaining, exit_distance_cm=(pawn.get_actor_location() - started).length())
    factory().set_editor_property("save_slot", final_slot)
    assert factory().load_factory(pawn)
    assert snapshot() == final_state
    yield
    inspect_landmarks()


def verify_persistence(final_slot, final_state, pending_slot):
    pawn = STATE["pawn"]
    final_data, pending_data = save_bytes(final_slot), save_bytes(pending_slot)
    assert scalar_value(final_data, "Version", "IntProperty", 2) == 2
    assert scalar_value(final_data, "SiteStage", "IntProperty") == 3
    assert scalar_value(final_data, "PlatesProduced", "IntProperty") == final_state["produced"]
    assert scalar_value(final_data, "PlatesDelivered", "IntProperty") == final_state["delivered"]
    assert 0 < scalar_value(pending_data, "SiteTransitionRemaining", "FloatProperty") < 2
    # The original v1 schema has no site fields. Keep native economy bytes.
    legacy_slot = fixture_save(final_slot, "legacy_v1", {"Version": 1},
                               remove=("SiteStage", "SiteTransitionRemaining"))
    factory().set_editor_property("save_slot", legacy_slot)
    assert factory().load_factory(pawn)
    assert snapshot() == dict(final_state, site_stage=0, site_remaining=0.0)
    for stage, label in enumerate(("legacy_workshop", "legacy_charging", "legacy_expansion")):
        yield from wait_for_reveal(stage, label)
    assert snapshot() == final_state
    record("version_one_save_replays_earned_reveals_without_economic_changes", fixture=legacy_slot)

    invalid_cases = [
        ("stage_out_of_range", {"SiteStage": 4}),
        ("completed_with_pending_timer", {"SiteStage": 3, "SiteTransitionRemaining": 0.5}),
        ("unearned_pending_reveal", {"SiteStage": 0, "SiteTransitionRemaining": 1.0, "PlatesProduced": 4}),
    ]
    for label, overrides in invalid_cases:
        slot = fixture_save(final_slot, "invalid_" + label, overrides)
        factory().set_editor_property("save_slot", slot)
        identities = [building.get_path_name() for building in factory().buildings()]
        expected = snapshot()
        assert not factory().load_factory(pawn), "Malformed save was accepted: " + label
        assert snapshot() == expected
        assert [building.get_path_name() for building in factory().buildings()] == identities
    factory().set_editor_property("save_slot", final_slot)
    record("malformed_version_two_saves_rejected_before_world_mutation", cases=[label for label, _ in invalid_cases])
    yield from verify_occupied_workshop(final_slot, final_state, pending_slot)


def run():
    assert not LEVELS.is_in_play_in_editor(), "Stop the current PIE session first"
    assert LEVELS.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
    unreal.SystemLibrary.execute_console_command(EDITOR.get_editor_world(), "t.MaxFPS 30")
    yield from wait(5)
    LEVELS.editor_request_begin_play()
    deadline = time.monotonic() + 15
    while True:
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0) if worlds else None
        if pawn:
            break
        assert time.monotonic() < deadline
        yield
    demo = pawn.get_component_by_class(unreal.FactoryDemoComponent)
    assert demo and demo.factory
    STATE.update(world=worlds[0], pawn=pawn, demo=demo, factory=demo.factory,
                 inventory=pawn.get_component_by_class(unreal.FactoryInventoryComponent),
                 camera=pawn.get_component_by_class(unreal.FactoryCameraComponent),
                 piles=unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactoryResourcePile))
    landmarks = unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.FactorySiteLandmark)
    assert len(landmarks) == 3 and {landmark.required_stage for landmark in landmarks} == {1, 2, 3}
    STATE["landmarks"] = {landmark.required_stage: landmark for landmark in landmarks}
    assert factory().enable_site_progress and factory().site_stage == 0
    assert factory().site_transition_remaining == 0 and len(factory().buildings()) == 4
    assert (factory().expansion_min.x, factory().expansion_min.y) == (-950, 1500)
    assert (factory().expansion_max.x, factory().expansion_max.y) == (950, 2350)
    yield
    if RESUME_FROM:
        final_slots = [slot for slot in REPORT["save_slots"] if slot.endswith("_final_v2")]
        pending_slots = [slot for slot in REPORT["save_slots"] if slot.endswith("_pending")]
        assert len(final_slots) == len(pending_slots) == 1
        final_slot, pending_slot = final_slots[0], pending_slots[0]
        factory().set_editor_property("save_slot", final_slot)
        assert factory().load_factory(pawn)
        assert factory().site_stage == 3 and factory().site_transition_remaining == 0
        assert factory().plates_produced == 20 and factory().plates_delivered == 21
        assert STATE["inventory"].get_quantity("Plate") == 20
        STATE["expected_mass"] = mass()
        assert STATE["expected_mass"] == 286
        final_state = snapshot()
        yield
        inspect_landmarks()
        record("continuation_restores_earned_native_final_save", source_slot=final_slot, total_mass=mass())
        yield from verify_persistence(final_slot, final_state, pending_slot)
        REPORT["passed"] = True
        return
    record("initial_original_factory_and_locked_landmarks", landmarks=inspect_landmarks())
    assert factory().placement_problem(unreal.Vector(0, 2000, 4)), "Annex was buildable before earning expansion"
    for y in (1000, 1200, 1400):
        assert factory().placement_problem(unreal.Vector(0, y, 4)), "Corridor construction unlocked too early"
    yield from physical_annex_access()
    yield from frame_annex()
    yield from capture("01_initial_reserved_annex")

    initial_mass = mass()
    assert STATE["inventory"].add_item(factory().resource("Scrap"), 10) == 10
    before = snapshot()
    assert STATE["demo"].build_at(3, unreal.Vector(0, 2000, 4), 0) is None
    assert snapshot() == before, "Locked construction changed economy"
    for x in (-400, 0, 400):
        assert STATE["demo"].build_at(3, unreal.Vector(x, 0, 4), 0), STATE["demo"].notification
    assert machine("Starter_0").input.add_item(factory().resource("Scrap"), 40) == 40
    STATE["expected_mass"] = initial_mass + 50
    assert mass() == STATE["expected_mass"]
    record("real_conveyor_circuit_ready", machines=len(factory().buildings()), injected_scrap=50, total_mass=mass())
    yield from wait_for_reveal(0, "workshop", checkpoint=True)
    yield from capture("02_workshop_earned")
    yield from wait_for_reveal(1, "charging_station")
    yield from capture("03_charging_station_earned")
    yield from wait_for_reveal(2, "expansion")
    assert factory().plates_produced == 20 and factory().plates_delivered == 20
    assert factory().stored_plates() == 20 and factory().goal_complete()
    assert mass() == STATE["expected_mass"]
    yield from capture("04_expansion_earned")

    move(unreal.Vector(600, 800, 100))
    cells = [unreal.Vector(x, y, 4) for x in range(-800, 801, 200) for y in range(1600, 2201, 200)]
    problems = [(str(position), factory().placement_problem(position)) for position in cells]
    assert not any(problem for _, problem in problems), problems
    assert factory().placement_problem(unreal.Vector(1000, 2000, 4))
    assert factory().placement_problem(unreal.Vector(0, 2400, 4))
    for y in (1000, 1200, 1400):
        assert not factory().placement_problem(unreal.Vector(0, y, 4)), ("Corridor did not unlock", y)
        assert factory().placement_problem(unreal.Vector(200, y, 4)), ("Unlocked beyond the narrow corridor", y)
    record("thirty_six_annex_cells_unlock_with_existing_floor_and_overlap_checks", cells=len(cells))
    record("three_central_corridor_cells_unlock_at_stage_three", cells=[[0, y, 4] for y in (1000, 1200, 1400)])
    before = snapshot()
    before_mass = mass()
    extra = STATE["demo"].build_at(3, unreal.Vector(0, 2000, 4), 0)
    assert extra and mass() == before_mass
    assert STATE["demo"].build_at(3, unreal.Vector(0, 2000, 4), 0) is None
    yield from frame_annex()
    yield from capture("05_building_in_new_sector")
    near(extra)
    assert STATE["demo"].dismantle()
    assert snapshot() == before and mass() == before_mass, "Annex build/dismantle did not refund exactly"
    record("annex_construction_occupancy_and_refund")

    near(machine("Starter_6"))
    STATE["demo"].withdraw()
    assert factory().stored_plates() == 0 and STATE["inventory"].get_quantity("Plate") == 20
    yield from wait(2.25)
    assert factory().site_stage == 3 and factory().site_transition_remaining == 0
    assert mass() == STATE["expected_mass"]
    record("withdrawing_earned_plates_does_not_regress_site")
    yield from verify_connector_delivery()

    final_slot = save_slot("final_v2")
    factory().set_editor_property("save_slot", final_slot)
    assert factory().save_factory(pawn)
    final_state = snapshot()
    yield from verify_persistence(final_slot, final_state, save_slot("pending"))
    REPORT["passed"] = True


def finish():
    STATE["finishing"] = True
    REPORT["elapsed_seconds"] = round(time.monotonic() - STATE["started"], 1)
    if RESUME_FROM:
        REPORT["combined_elapsed_seconds"] = round(
            REPORT["elapsed_seconds"] + sum(run["elapsed_seconds"] for run in REPORT["prior_runs"]), 1)
    text = json.dumps(REPORT, indent=2)
    (OUTPUT / "report.json").write_text(text, encoding="utf-8")
    (PROJECT / "Docs" / "factory_site_playtest.json").write_text(text, encoding="utf-8")
    (OUTPUT.parent / "latest-playtest.txt").write_text(str(OUTPUT), encoding="utf-8")
    unreal.log("[FACTORY_SITE_PLAYTEST] " + text)
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
        if not STATE["finishing"] and time.monotonic() - STATE["started"] > 300:
            raise TimeoutError("Factory site acceptance timed out")
        next(STATE["steps"])
    except StopIteration:
        if not STATE["finishing"]:
            STATE["finishing"] = True
            STATE["steps"] = finish()
    except Exception:
        REPORT["passed"] = False
        REPORT["error"] = traceback.format_exc()
        unreal.log_error(REPORT["error"])
        # Mark cleanup immediately so a failing cleanup cannot restart itself.
        if STATE["finishing"]:
            unreal.unregister_slate_post_tick_callback(STATE["handle"])
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        else:
            STATE["finishing"] = True
            STATE["steps"] = finish()
    finally:
        STATE["in_tick"] = False


STATE["steps"] = run()
STATE["handle"] = unreal.register_slate_post_tick_callback(tick)
