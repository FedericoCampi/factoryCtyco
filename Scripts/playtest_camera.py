"""Verify camera controls via PlayerController input events in a rendered PIE game."""
import json
import time
import traceback
from pathlib import Path
import unreal

project=Path(unreal.Paths.project_dir()).resolve()
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
report={'passed':False,'checks':{},'scope':'Rendered PIE; simulated mouse and keyboard events through the real PlayerController input stack. Physical mouse interaction not manually tested.'}
state={'phase':'warmup','started':time.monotonic(),'phase_time':time.monotonic()}
assert levels.load_level('/Game/FactoryCtyco/Maps/L_Recoleccion')
unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),'t.MaxFPS 30')

def phase(name): state.update(phase=name,phase_time=time.monotonic(),count=0)
def key(name,value=1.0,pressed=True): state['control'].send_editor_test_input(name,value,pressed)
def tap(name):
    key(name)
    key(name,0.0,False)
def capture(name): print("[captura desactivada]", 1440,900,str(project/'Docs'/name))
def near(a,b,tolerance=1):
    if abs(a-b)>tolerance: raise RuntimeError(f'Expected {b}, got {a}')
def record(name,**values): report['checks'][name]={'passed':True,**values}
def write_report():
    (project/'Docs/camera_playtest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('[CAMERA_PLAYTEST] '+json.dumps(report))
def finish():
    if 'control' in state:
        for name in ['MiddleMouseButton','W','SpaceBar']: key(name,0,False)
    write_report()
    levels.editor_request_end_play()
    phase('quit')

def tick(delta):
    try:
        now=time.monotonic()
        age=now-state['phase_time']
        if now-state['started']>150: raise RuntimeError('Camera playtest timed out')
        name=state['phase']
        if name=='warmup' and age>8:
            levels.editor_request_begin_play()
            phase('spawn')
        elif name=='spawn' and age>3:
            worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
            if not worlds: return
            pawn=unreal.GameplayStatics.get_player_pawn(worlds[0],0)
            if pawn is None: return
            control=pawn.get_component_by_class(unreal.FactoryCameraComponent)
            if control is None: raise RuntimeError('Missing camera component')
            arm=pawn.get_component_by_class(unreal.SpringArmComponent)
            state.update(pawn=pawn,control=control,arm=arm,
                rotation=arm.get_world_rotation(),initial_distance=arm.target_arm_length,
                initial_offset=arm.target_offset)
            near(arm.target_arm_length,2450)
            tap('MouseScrollUp')
            phase('zoom_in')
        elif name=='zoom_in' and age>.9:
            near(state['arm'].target_arm_length,2205)
            record('wheel_zoom_in',distance_cm=state['arm'].target_arm_length)
            tap('MouseScrollDown')
            phase('zoom_out')
        elif name=='zoom_out' and age>1:
            near(state['arm'].target_arm_length,2450)
            record('wheel_zoom_out',distance_cm=state['arm'].target_arm_length)
            phase('minimum')
        elif name in ('minimum','maximum'):
            count=state['count']
            limit=20 if name=='minimum' else 35
            if count<limit:
                tap('MouseScrollUp' if name=='minimum' else 'MouseScrollDown')
                state['count']+=1
                state['last_scroll']=now
            elif now-state['last_scroll']>1:
                expected=1100 if name=='minimum' else 3800
                near(state['arm'].target_arm_length,expected)
                record('zoom_'+name,distance_cm=state['arm'].target_arm_length)
                if name=='minimum': phase('maximum')
                else:
                    tap('Home')
                    phase('before_pan')
        elif name=='before_pan' and age>1:
            near(state['arm'].target_arm_length,2450)
            key('MiddleMouseButton')
            phase('pan')
        elif name=='pan':
            if age<.5:
                key('MouseX',10.0)
                key('MouseY',6.0)
            elif age>1:
                key('MiddleMouseButton',0,False)
                offset=state['control'].desired_pan
                if offset.length()<50 or offset.length()>1251: raise RuntimeError('Drag did not pan or exceeded its limit')
                state['pan']=offset
                record('middle_mouse_drag',offset_cm=[offset.x,offset.y,offset.z])
                phase('released')
        elif name=='released':
            key('MouseX',12.0)
            key('MouseY',8.0)
            if age>.6:
                near((state['control'].desired_pan-state['pan']).length(),0,.01)
                record('mouse_release_stops_pan')
                key('MiddleMouseButton')
                phase('pan_limit')
        elif name=='pan_limit':
            if age<.5: key('MouseX',1000.0)
            elif age>1:
                near(state['control'].desired_pan.length(),1250,.1)
                key('MiddleMouseButton',0,False)
                record('pan_limit',distance_cm=state['control'].desired_pan.length())
                tap('Home')
                phase('reset')
        elif name=='reset' and age>1.2:
            near(state['arm'].target_arm_length,2450)
            near((state['arm'].target_offset-state['initial_offset']).length(),0,1)
            record('home_recenters_and_resets_zoom')
            state['origin']=state['pawn'].get_actor_location()
            key('W')
            phase('move')
        elif name=='move' and age>1.2:
            distance=(state['pawn'].get_actor_location()-state['origin']).length()
            runtime=state['pawn'].get_component_by_class(unreal.RobotLocomotionComponent)
            if distance<120 or runtime.planar_speed<100: raise RuntimeError('WASD or locomotion was blocked')
            key('W',0,False)
            record('keyboard_movement',distance_cm=distance,animation_speed=runtime.planar_speed)
            state['jump_z']=state['pawn'].get_actor_location().z
            state['max_z']=state['jump_z']
            key('SpaceBar')
            phase('jump')
        elif name=='jump':
            state['max_z']=max(state['max_z'],state['pawn'].get_actor_location().z)
            if age>.25: key('SpaceBar',0,False)
            if age>2:
                rise=state['max_z']-state['jump_z']
                if rise>1 or not state['pawn'].character_movement.is_moving_on_ground(): raise RuntimeError('Space unexpectedly triggered a jump')
                record('keyboard_jump_disabled',rise_cm=rise)
                rotation=state['arm'].get_world_rotation()
                near(rotation.pitch,state['rotation'].pitch,.01)
                near(rotation.yaw,state['rotation'].yaw,.01)
                record('isometric_angle_preserved',pitch=rotation.pitch,yaw=rotation.yaw)
                phase('capture')
                capture('camera_final.png')
        elif name=='capture' and age>3:
            report['passed']=True
            finish()
        elif name=='quit' and age>2:
            unreal.unregister_slate_post_tick_callback(state['handle'])
            unreal.SystemLibrary.quit_editor()
    except Exception:
        report['error']=traceback.format_exc()
        finish()

state['handle']=unreal.register_slate_post_tick_callback(tick)
