"""Exercise saved skeletal locomotion and fixed camera in a real PIE session."""
import json
import time
import traceback
from pathlib import Path
import unreal

project=Path(unreal.Paths.project_dir()).resolve()
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
report={'passed':False,'checks':{},'scope':'Automated PIE: skeletal pose changes, locomotion, camera, stop, jump and landing. Screenshots reviewed separately.'}
state={'phase':'warmup','started':time.monotonic(),'phase_time':time.monotonic(),'foot_samples':[]}
assert levels.load_level('/Game/FactoryCtyco/Maps/L_Recoleccion')
editor.set_level_viewport_camera_info(unreal.Vector(-1300,1750,1900),unreal.Rotator(pitch=-55,yaw=-45))
levels.editor_set_game_view(True)
unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),'t.MaxFPS 30')

def phase(name):
    state.update(phase=name,phase_time=time.monotonic())

def xyz(v):
    return [round(v.x,3),round(v.y,3),round(v.z,3)]

def capture(name):
    print("[captura desactivada]", 1440,900,str(project/'Docs'/name))

def write_report():
    (project/'Docs/isometric_playtest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('[ISOMETRIC_PLAYTEST] '+json.dumps(report))

def finish():
    write_report()
    levels.editor_request_end_play()
    phase('quit')

def tick(delta):
    try:
        now=time.monotonic()
        age=now-state['phase_time']
        if now-state['started']>210:
            raise RuntimeError('Playtest timed out')
        name=state['phase']
        if name=='warmup' and age>8:
            levels.editor_request_begin_play()
            phase('spawn')
        elif name=='spawn':
            worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
            if worlds and age>3:
                pawn=unreal.GameplayStatics.get_player_pawn(worlds[0],0)
                if pawn is None: return
                mesh=pawn.mesh
                skeletal=mesh.get_editor_property('skeletal_mesh_asset')
                runtime=pawn.get_component_by_class(unreal.RobotLocomotionComponent)
                camera=pawn.get_component_by_class(unreal.CameraComponent)
                if skeletal is None or skeletal.get_name()!='SK_Robot1' or runtime is None:
                    raise RuntimeError('Player has no authored skeletal robot or locomotion component')
                if not pawn.character_movement.is_moving_on_ground():
                    raise RuntimeError('Player did not land on the arena floor')
                if mesh.get_num_bones()<22:
                    raise RuntimeError('Incomplete imported skeleton')
                if abs(camera.get_world_rotation().pitch+55)>.5:
                    raise RuntimeError('Isometric pitch is incorrect')
                state.update(pawn=pawn,mesh=mesh,runtime=runtime,camera=camera,
                    origin=pawn.get_actor_location(),camera_rotation=camera.get_world_rotation())
                report['checks']['spawn']={'passed':True,'skeleton_bones':mesh.get_num_bones(),
                    'mesh':skeletal.get_path_name(),'animation_instance':mesh.get_anim_instance().get_class().get_name(),
                    'position_cm':xyz(state['origin'])}
                phase('settle')
        elif name=='settle' and age>2:
            capture('isometric_idle.png')
            phase('idle_capture')
        elif name=='idle_capture' and age>3:
            phase('walk')
        elif name=='walk':
            pawn=state['pawn']
            pawn.add_movement_input(unreal.Vector(0,-1,0),1,True)
            if age>.7:
                foot=state['mesh'].get_socket_location('foot_l')-pawn.get_actor_location()
                state['foot_samples'].append(xyz(foot))
            if age>1.5 and not state.get('walk_capture'):
                capture('isometric_walk.png')
                state['walk_capture']=True
            if age>3.0:
                distance=(pawn.get_actor_location()-state['origin']).length()
                samples=state['foot_samples']
                ranges=[max(v[i] for v in samples)-min(v[i] for v in samples) for i in range(3)]
                if distance<300 or max(ranges)<12:
                    raise RuntimeError(f'Walking did not animate correctly: distance={distance}, foot ranges={ranges}')
                if state['runtime'].get_editor_property('planar_speed')<100:
                    raise RuntimeError('Animation driver did not read character speed')
                report['checks']['walk']={'passed':True,'distance_cm':round(distance,2),
                    'foot_motion_ranges_cm':ranges,'sample_count':len(samples)}
                phase('turn')
        elif name=='turn':
            state['pawn'].add_movement_input(unreal.Vector(1,0,0),1,True)
            if age>.6:
                camera=state['camera'].get_world_rotation()
                before=state['camera_rotation']
                if abs(camera.pitch-before.pitch)>.1 or abs(camera.yaw-before.yaw)>.1:
                    raise RuntimeError('Camera rotated when the player changed direction')
                report['checks']['fixed_camera']={'passed':True,'pitch':camera.pitch,'yaw':camera.yaw}
                phase('stop')
        elif name=='stop' and age>1:
            speed=state['runtime'].get_editor_property('planar_speed')
            if speed>1:
                raise RuntimeError(f'Robot did not return to idle: speed={speed}')
            report['checks']['stop']={'passed':True,'speed_cm_s':speed}
            state['jump_z']=state['pawn'].get_actor_location().z
            state['max_z']=state['jump_z']
            state['pawn'].jump()
            phase('jump')
        elif name=='jump':
            pawn=state['pawn']
            state['max_z']=max(state['max_z'],pawn.get_actor_location().z)
            if state['runtime'].get_editor_property('airborne'):
                state['airborne_seen']=True
            if age>.25:
                pawn.stop_jumping()
            if age>2:
                rise=state['max_z']-state['jump_z']
                if rise>1 or state.get('airborne_seen') or not pawn.character_movement.is_moving_on_ground():
                    raise RuntimeError('Direct Jump unexpectedly left the ground')
                report['checks']['jump_disabled']={'passed':True,'rise_cm':round(rise,2)}
                capture('isometric_final.png')
                phase('final_capture')
        elif name=='final_capture' and age>3:
            report['passed']=True
            finish()
        elif name=='quit' and age>2:
            unreal.unregister_slate_post_tick_callback(state['handle'])
            unreal.SystemLibrary.quit_editor()
    except Exception:
        report['error']=traceback.format_exc()
        write_report()
        levels.editor_request_end_play()
        unreal.unregister_slate_post_tick_callback(state['handle'])
        unreal.SystemLibrary.quit_editor()

state['handle']=unreal.register_slate_post_tick_callback(tick)
