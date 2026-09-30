"""Check horizontal orbit, input conflicts, pawn pivot and movement in FactoryDemo PIE."""
import json
import math
from pathlib import Path
import time
import traceback
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
report = {'passed': False, 'checks': {}, 'scope': 'Rendered L_FactoryDemo PIE, simulated PlayerController input. No physical mouse test.'}
state = {'started': time.monotonic(), 'finishing': False}


def wait(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        yield


def key(name, value=1.0, pressed=True):
    state['control'].send_editor_test_input(name, value, pressed)


def release(*names):
    for name in names:
        key(name, 0, False)


def tap(name):
    key(name)
    yield
    release(name)


def drag(x, y=0, count=12):
    for _ in range(count):
        key('MouseX', x)
        key('MouseY', y)
        yield


def angle_delta(start, end):
    return (end - start + 180) % 360 - 180


def near(actual, expected, tolerance=0.1):
    assert abs(actual - expected) <= tolerance, f'{actual} != {expected} +/- {tolerance}'


def record(name, **values):
    report['checks'][name] = {'passed': True, **values}


def yaw():
    return state['arm'].get_world_rotation().yaw


def run():
    yield from wait(5)
    world = editor.get_editor_world()
    assert 'L_FactoryDemo' in world.get_path_name(), 'Open L_FactoryDemo before running this test.'
    unreal.SystemLibrary.execute_console_command(world, 't.MaxFPS 30')
    levels.editor_request_begin_play()
    yield from wait(3)
    worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
    assert worlds, 'PIE did not start.'
    pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
    control = pawn.get_component_by_class(unreal.FactoryCameraComponent)
    arm = pawn.get_component_by_class(unreal.SpringArmComponent)
    camera = pawn.get_component_by_class(unreal.CameraComponent)
    demo = pawn.get_component_by_class(unreal.FactoryDemoComponent)
    assert control and arm and camera and demo
    state.update(control=control, arm=arm)
    initial_yaw = yaw()
    initial_pitch = arm.get_world_rotation().pitch
    initial_zoom = arm.target_arm_length
    initial_offset = arm.target_offset
    initial_position = pawn.get_actor_location()
    initial_pawn_yaw = pawn.get_actor_rotation().yaw

    yield from drag(10, 8)
    near(angle_delta(initial_yaw, control.desired_yaw), 0)
    key('RightMouseButton')
    yield from drag(10, 8)
    release('RightMouseButton')
    near(angle_delta(initial_yaw, control.desired_yaw), 0)
    record('no_orbit_without_ctrl_and_right_button')

    demo.toggle_build()
    assert demo.building
    key('LeftControl')
    yield
    key('RightMouseButton')
    yield from drag(10, 10)
    release('RightMouseButton', 'LeftControl')
    yield from wait(1.4)
    left_yaw = yaw()
    assert angle_delta(initial_yaw, left_yaw) > 5
    near(arm.get_world_rotation().pitch, initial_pitch)
    near((pawn.get_actor_location() - initial_position).length(), 0, 0.5)
    near(angle_delta(initial_pawn_yaw, pawn.get_actor_rotation().yaw), 0)
    assert demo.building, 'Ctrl + right click cancelled construction.'
    record('left_ctrl_horizontal_orbit_preserves_pitch_pawn_and_build_mode', yaw=left_yaw)

    yield from tap('RightMouseButton')
    yield from wait(0.2)
    assert not demo.building, 'Plain right click did not cancel construction.'
    record('plain_right_click_still_cancels_build_mode')

    key('RightControl')
    yield
    key('RightMouseButton')
    yield from drag(-10, -10)
    release('RightMouseButton', 'RightControl')
    yield from wait(1.4)
    assert angle_delta(left_yaw, yaw()) < -5
    near(arm.get_world_rotation().pitch, initial_pitch)
    record('right_ctrl_and_reverse_orbit', yaw=yaw())

    stopped_yaw = control.desired_yaw
    yield from drag(10, 10)
    near(angle_delta(stopped_yaw, control.desired_yaw), 0)
    record('release_stops_orbit')

    key('MiddleMouseButton')
    yield from drag(5, 3)
    release('MiddleMouseButton')
    yield from wait(1.4)
    assert control.desired_pan.length() > 20
    before_pan_length = control.desired_pan.length()
    before_yaw = yaw()
    before_camera = camera.get_world_location() - pawn.get_actor_location()
    record('middle_button_pan_preserved', distance=before_pan_length)

    key('LeftControl')
    yield
    key('RightMouseButton')
    # Check the camera's world-space orbit around the pawn after a manual pan.
    yield from drag(50, 0, 24)
    release('RightMouseButton', 'LeftControl')
    yield from wait(2)
    after_camera = camera.get_world_location() - pawn.get_actor_location()
    delta = math.radians(angle_delta(before_yaw, yaw()))
    expected_x = before_camera.x * math.cos(delta) - before_camera.y * math.sin(delta)
    expected_y = before_camera.x * math.sin(delta) + before_camera.y * math.cos(delta)
    near(after_camera.x, expected_x, 2)
    near(after_camera.y, expected_y, 2)
    near(after_camera.z, before_camera.z, 0.5)
    near(control.desired_pan.length(), before_pan_length, 0.5)
    near(angle_delta(control.desired_yaw, yaw()), 0, 0.2)
    assert -180 <= control.desired_yaw <= 180
    record('orbit_pivot_is_pawn_even_after_pan', yaw=yaw())

    origin = pawn.get_actor_location()
    heading = math.radians(yaw())
    key('W')
    yield from wait(0.35)
    release('W')
    displacement = pawn.get_actor_location() - origin
    distance = math.hypot(displacement.x, displacement.y)
    assert distance > 15, 'W did not move the pawn.'
    alignment = (displacement.x * math.cos(heading) + displacement.y * math.sin(heading)) / distance
    assert alignment > 0.9, f'WASD does not follow camera yaw: {alignment}'
    record('wasd_follows_orbit_heading', alignment=alignment)

    yield from tap('MouseScrollUp')
    yield from wait(1.4)
    near(arm.target_arm_length, initial_zoom * 0.9, 1)
    record('zoom_preserved')
    yield from tap('Home')
    yield from wait(2)
    near(angle_delta(initial_yaw, yaw()), 0, 0.2)
    near(arm.get_world_rotation().pitch, initial_pitch)
    near((arm.target_offset - initial_offset).length(), 0, 1)
    near(arm.target_arm_length, initial_zoom, 1)
    record('home_restores_heading_zoom_and_framing')
    report['passed'] = True


def finish():
    state['finishing'] = True
    if 'control' in state:
        release('LeftControl', 'RightControl', 'RightMouseButton', 'MiddleMouseButton', 'W')
    report['elapsed_seconds'] = round(time.monotonic() - state['started'], 1)
    (project / 'Docs/camera_orbit_playtest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.log('[CAMERA_ORBIT_PLAYTEST] ' + json.dumps(report))
    levels.editor_request_end_play()
    yield from wait(2)
    unreal.unregister_slate_post_tick_callback(state['handle'])
    unreal.SystemLibrary.quit_editor()


state['steps'] = run()


def tick(delta):
    try:
        if not state['finishing'] and time.monotonic() - state['started'] > 120:
            raise RuntimeError('Camera orbit playtest timed out.')
        next(state['steps'])
    except StopIteration:
        if not state['finishing']:
            state['steps'] = finish()
    except Exception:
        report['error'] = traceback.format_exc()
        report['passed'] = False
        state['steps'] = finish()


state['handle'] = unreal.register_slate_post_tick_callback(tick)
