"""Capture the completed annex using the isolated acceptance save, not player data."""
from pathlib import Path
import json
import time
import traceback
import unreal

PROJECT = Path(unreal.Paths.project_dir()).resolve()
REPORT = json.loads((PROJECT/'Docs/factory_site_playtest.json').read_text(encoding='utf-8'))
assert REPORT['checks'].get('earned_expansion', {}).get('passed'), 'Expansion must be earned first'
SLOT = next(s for s in REPORT['save_slots'] if s.endswith('_final_v2'))
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
STATE = {'busy':False, 'started':time.monotonic()}
unreal.EditorPythonScripting.set_keep_python_script_alive(True)


def wait(seconds):
    until = time.monotonic()+seconds
    while time.monotonic()<until:
        yield


def run():
    assert not LEVELS.is_in_play_in_editor()
    LEVELS.load_level('/Game/FactoryCtyco/Maps/L_FactoryDemo')
    LEVELS.editor_request_begin_play()
    deadline = time.monotonic()+15
    while True:
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0],0) if worlds else None
        if pawn: break
        assert time.monotonic()<deadline
        yield
    world = worlds[0]
    pc = unreal.GameplayStatics.get_player_controller(world,0)
    factory = unreal.GameplayStatics.get_actor_of_class(world,unreal.FactoryDemoWorld)
    factory.set_editor_property('save_slot',SLOT)
    assert factory.load_factory(pawn)
    demo = pawn.get_component_by_class(unreal.FactoryDemoComponent)
    store = next(b for b in factory.buildings() if str(b.persistent_id)=='Starter_6')
    pawn.set_actor_location(store.get_actor_location()+unreal.Vector(0,150,96),False,True)
    demo.refresh_focus()
    assert demo.focused_building == store
    assert demo.interact_machine()
    assert factory.goal_complete()
    pawn.set_actor_location(unreal.Vector(-130,1780,96),False,True)
    pawn.character_movement.stop_movement_immediately()
    gameplay = unreal.get_default_object(unreal.GameplayStatics)
    transform = unreal.Transform(location=unreal.Vector(0,3900,3400))
    scale = unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT
    camera = gameplay.call_method('BeginDeferredActorSpawnFromClass',args=(world,unreal.CameraActor,transform,
                                  unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,scale))
    camera = gameplay.call_method('FinishSpawningActor',args=(camera,transform,scale))
    camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(camera.get_actor_location(),unreal.Vector(0,1550,0)),False)
    camera.camera_component.set_editor_property('projection_mode',unreal.CameraProjectionMode.ORTHOGRAPHIC)
    camera.camera_component.set_editor_property('ortho_width',3000)
    camera.camera_component.set_editor_property('constrain_aspect_ratio',False)
    pc.set_view_target_with_blend(camera,0)
    yield from wait(5)
    target=PROJECT/'Docs/factory_site_completed.png'
    print("[captura desactivada]", 1440,900,str(target))
    yield from wait(3)
    assert target.is_file()
    STATE['passed']=True


def cleanup():
    LEVELS.editor_request_end_play()
    yield from wait(1)
    unreal.unregister_slate_post_tick_callback(STATE['handle'])
    unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    (PROJECT/'Saved/SiteProgressWork/capture.json').write_text(json.dumps({k:v for k,v in STATE.items() if k in ('passed','error')},indent=2),encoding='utf-8')


def tick(delta):
    if STATE['busy']: return
    STATE['busy']=True
    try:
        next(STATE['steps'])
    except StopIteration:
        STATE['steps']=cleanup()
    except Exception:
        STATE['error']=traceback.format_exc()
        unreal.log_error(STATE['error'])
        STATE['steps']=cleanup()
    finally:
        STATE['busy']=False


STATE['steps']=run()
STATE['handle']=unreal.register_slate_post_tick_callback(tick)
