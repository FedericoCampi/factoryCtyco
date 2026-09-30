"""PIE input test: walk, both Shift keys, no jump, and camera compatibility."""
import json
import time
import traceback
from pathlib import Path
import unreal

project=Path(unreal.Paths.project_dir()).resolve()
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
report={'passed':False,'checks':{},'scope':'PIE with simulated input events through PlayerController; physical keyboard not manually tested.'}
state={'phase':'warmup','started':time.monotonic(),'phase_time':time.monotonic()}
assert levels.load_level('/Game/FactoryCtyco/Maps/L_Recoleccion')
unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),'t.MaxFPS 30')

def phase(name): state.update(phase=name,phase_time=time.monotonic())
def key(name,pressed=True): state['control'].send_editor_test_input(name,1.0 if pressed else 0.0,pressed)
def tap(name):
    key(name)
    key(name,False)
def near(a,b,tolerance=1):
    if abs(a-b)>tolerance: raise RuntimeError(f'Expected {b}, got {a}')
def record(name,**values): report['checks'][name]={'passed':True,**values}
def reset_path():
    state['pawn'].character_movement.stop_movement_immediately()
    state['pawn'].set_actor_location(state['origin'],False,True)
def finish():
    if 'control' in state:
        for name in ['LeftShift','RightShift','W','SpaceBar']: key(name,False)
    (project/'Docs/factory_controls_playtest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('[FACTORY_CONTROLS_PLAYTEST] '+json.dumps(report))
    levels.editor_request_end_play()
    phase('quit')
def speed_check(expected):
    pawn=state['pawn']
    runtime=state['runtime']
    near(pawn.character_movement.max_walk_speed,expected,.1)
    near(runtime.planar_speed,expected,2)
    return (pawn.get_actor_location()-state['origin']).length()

def tick(delta):
    try:
        age=time.monotonic()-state['phase_time']
        if time.monotonic()-state['started']>100: raise RuntimeError('Controls test timed out')
        name=state['phase']
        if name=='warmup' and age>6:
            levels.editor_request_begin_play()
            phase('spawn')
        elif name=='spawn' and age>3:
            worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
            if not worlds: return
            pawn=unreal.GameplayStatics.get_player_pawn(worlds[0],0)
            if pawn is None: return
            control=pawn.get_component_by_class(unreal.FactoryCameraComponent)
            runtime=pawn.get_component_by_class(unreal.RobotLocomotionComponent)
            arm=pawn.get_component_by_class(unreal.SpringArmComponent)
            if control is None or runtime is None: raise RuntimeError('Missing runtime controls')
            state.update(pawn=pawn,control=control,runtime=runtime,arm=arm,
                origin=pawn.get_actor_location(),rotation=arm.get_world_rotation(),initial_zoom=arm.target_arm_length)
            near(pawn.jump_max_count,0,0)
            if pawn.can_jump(): raise RuntimeError('Character still allows jumping')
            record('jump_disabled_in_character')
            key('W')
            phase('walk')
        elif name=='walk' and age>.75:
            distance=speed_check(190)
            if distance<75: raise RuntimeError('Robot did not walk')
            record('walk',speed_cm_s=state['runtime'].planar_speed,distance_cm=distance)
            reset_path()
            key('LeftShift')
            state['foot_samples']=[]
            phase('fast_left')
        elif name=='fast_left':
            foot=state['pawn'].mesh.get_socket_location('foot_l')-state['pawn'].get_actor_location()
            if age>.2: state['foot_samples'].append([foot.x,foot.y,foot.z])
            if age>.75:
                distance=speed_check(300)
                if not state['runtime'].fast_walking or distance<120: raise RuntimeError('Left Shift did not increase speed')
                samples=state['foot_samples']
                ranges=[max(v[i] for v in samples)-min(v[i] for v in samples) for i in range(3)]
                if max(ranges)<12: raise RuntimeError('Fast walking has a static pose')
                record('left_shift_fast_walk',speed_cm_s=state['runtime'].planar_speed,distance_cm=distance,foot_motion_cm=ranges)
                key('LeftShift',False)
                reset_path()
                phase('released')
        elif name=='released' and age>.65:
            speed_check(190)
            if state['runtime'].fast_walking: raise RuntimeError('Fast walk remained enabled after release')
            record('shift_release_restores_walk')
            reset_path()
            key('RightShift')
            phase('fast_right')
        elif name=='fast_right' and age>.65:
            speed_check(300)
            record('right_shift_fast_walk')
            key('LeftShift')
            key('RightShift',False)
            reset_path()
            phase('other_shift')
        elif name=='other_shift' and age>.65:
            speed_check(300)
            record('either_shift_keeps_fast_walk')
            key('LeftShift',False)
            key('W',False)
            phase('idle')
        elif name=='idle' and age>.6:
            near(state['runtime'].planar_speed,0,.1)
            near(state['pawn'].character_movement.max_walk_speed,190,.1)
            record('release_returns_to_idle')
            state['jump_z']=state['pawn'].get_actor_location().z
            state['maximum_z']=state['jump_z']
            key('SpaceBar')
            state['pawn'].jump()
            phase('no_jump')
        elif name=='no_jump':
            state['maximum_z']=max(state['maximum_z'],state['pawn'].get_actor_location().z)
            if age>.8:
                key('SpaceBar',False)
                state['pawn'].stop_jumping()
                near(state['maximum_z'],state['jump_z'],1)
                if not state['pawn'].character_movement.is_moving_on_ground(): raise RuntimeError('Character left the ground')
                record('space_and_direct_jump_do_not_jump',maximum_rise_cm=state['maximum_z']-state['jump_z'])
                tap('MouseScrollUp')
                phase('camera')
        elif name=='camera' and age>.8:
            near(state['arm'].target_arm_length,state['initial_zoom']*.9,1)
            rotation=state['arm'].get_world_rotation()
            near(rotation.pitch,state['rotation'].pitch,.01)
            near(rotation.yaw,state['rotation'].yaw,.01)
            record('camera_zoom_and_angle_preserved')
            tap('Home')
            phase('reset')
        elif name=='reset' and age>.8:
            near(state['arm'].target_arm_length,state['initial_zoom'],1)
            record('camera_reset')
            report['passed']=True
            finish()
        elif name=='quit' and age>2:
            unreal.unregister_slate_post_tick_callback(state['handle'])
            unreal.SystemLibrary.quit_editor()
    except Exception:
        report['error']=traceback.format_exc()
        finish()

state['handle']=unreal.register_slate_post_tick_callback(tick)
