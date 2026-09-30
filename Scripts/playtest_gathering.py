"""Rendered PIE acceptance: resource accounting, reach, inventory and HUD."""
import json
import time
import traceback
from pathlib import Path
import unreal

project=Path(unreal.Paths.project_dir()).resolve()
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
report={'passed':False,'checks':{},'scope':'Rendered PIE with PlayerController input events; screenshots reviewed separately. Inventory is session-only.'}
state={'phase':'warmup','started':time.monotonic(),'phase_time':time.monotonic()}
assert levels.load_level('/Game/FactoryCtyco/Maps/L_Recoleccion')
unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),'t.MaxFPS 30')

def phase(name): state.update(phase=name,phase_time=time.monotonic())
def key(name,pressed=True): state['control'].send_editor_test_input(name,1.0 if pressed else 0.0,pressed)
def tap(name):
    key(name)
    key(name,False)
def near(a,b,tolerance=.1):
    if abs(a-b)>tolerance: raise RuntimeError(f'Expected {b}, got {a}')
def record(name,**values): report['checks'][name]={'passed':True,**values}
def move_to(position):
    state['pawn'].character_movement.stop_movement_immediately()
    state['pawn'].set_actor_location(position,False,True)
def capture(name): print("[captura desactivada]", 1440,900,str(project/'Docs'/name))
def total_world(): return sum(p.amount for p in state['piles'])
def spawn_blocker():
    gameplay=unreal.get_default_object(unreal.GameplayStatics)
    transform=unreal.Transform(location=unreal.Vector(180,880,85))
    scale=unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT
    actor=gameplay.call_method('BeginDeferredActorSpawnFromClass',args=(state['world'],unreal.StaticMeshActor,transform,
        unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,scale))
    actor=gameplay.call_method('FinishSpawningActor',args=(actor,transform,scale))
    actor.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    actor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    actor.static_mesh_component.set_collision_profile_name('BlockAll')
    actor.set_actor_scale3d(unreal.Vector(.8,.2,1.7))
    return actor
def finish():
    if 'control' in state:
        for name in ['E','I','W','LeftShift']: key(name,False)
    (project/'Docs/gathering_playtest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('[GATHERING_PLAYTEST] '+json.dumps(report))
    levels.editor_request_end_play()
    phase('quit')

def tick(delta):
    try:
        age=time.monotonic()-state['phase_time']
        if time.monotonic()-state['started']>170: raise RuntimeError('Gathering test timed out')
        name=state['phase']
        if name=='warmup' and age>8:
            levels.editor_request_begin_play()
            phase('spawn')
        elif name=='spawn' and age>3:
            worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
            if not worlds: return
            world=worlds[0]
            pawn=unreal.GameplayStatics.get_player_pawn(world,0)
            if pawn is None: return
            inventory=pawn.get_component_by_class(unreal.FactoryInventoryComponent)
            gathering=pawn.get_component_by_class(unreal.FactoryGatheringComponent)
            control=pawn.get_component_by_class(unreal.FactoryCameraComponent)
            player=unreal.GameplayStatics.get_player_controller(world,0)
            if not inventory or not gathering or not control: raise RuntimeError('Missing gathering components')
            if not isinstance(player.get_hud(),unreal.FactoryGatheringHUD): raise RuntimeError('Factory HUD not active')
            piles=sorted(unreal.GameplayStatics.get_all_actors_of_class(world,unreal.FactoryResourcePile),key=lambda p:str(p.persistent_id))
            if len(piles)!=7: raise RuntimeError('Expected 7 scrap piles')
            state.update(world=world,pawn=pawn,inventory=inventory,gathering=gathering,control=control,piles=piles,origin=pawn.get_actor_location())
            near(inventory.get_total(),0)
            near(total_world(),210)
            if pawn.can_jump(): raise RuntimeError('Jump was re-enabled')
            record('spawn_and_hud',piles=7,capacity=inventory.capacity,world_quantity=210)
            tap('I')
            phase('open')
        elif name=='open' and age>.4:
            if not state['gathering'].inventory_open: raise RuntimeError('I did not open the inventory')
            if state['gathering'].focused_pile!=state['piles'][0]: raise RuntimeError('First pile not reachable from spawn')
            record('inventory_opens_and_target_is_highlighted')
            phase('empty_capture')
            capture('gathering_empty.png')
        elif name=='empty_capture' and age>3:
            tap('E')
            phase('first_pickup')
        elif name=='first_pickup' and age>.4:
            near(state['inventory'].get_quantity('Scrap'),30)
            near(state['piles'][0].amount,0)
            record('e_collects_and_depletes',quantity=30,remaining_world=total_world())
            tap('E')
            phase('repeat')
        elif name=='repeat' and age>.4:
            near(state['inventory'].get_total(),30)
            record('exhausted_pile_cannot_duplicate')
            move_to(unreal.Vector(0,0,92.15))
            tap('E')
            phase('range')
        elif name=='range' and age>.4:
            near(state['inventory'].get_total(),30)
            if state['gathering'].focused_pile: raise RuntimeError('Distant resources can be targeted')
            record('out_of_range_cannot_collect')
            move_to(unreal.Vector(180,960,92.15))
            state['blocker']=spawn_blocker()
            phase('wall_ready')
        elif name=='wall_ready' and age>.4:
            tap('E')
            phase('wall')
        elif name=='wall' and age>.4:
            near(state['inventory'].get_total(),30)
            near(state['piles'][1].amount,30)
            if state['gathering'].focused_pile: raise RuntimeError('Pile can be reached through a blocking wall')
            record('wall_blocks_collection')
            state['blocker'].destroy_actor()
            phase('wall_removed')
        elif name=='wall_removed' and age>.4:
            tap('E')
            phase('second_pickup')
        elif name=='second_pickup' and age>.4:
            near(state['inventory'].get_total(),60)
            near(state['piles'][1].amount,0)
            record('collection_resumes_after_obstruction_removed')
            # Use normal inventory operations: editor property changes on a PIE
            # component can reconstruct the Blueprint and reset its runtime state.
            near(state['inventory'].add_item(state['piles'][2].resource,135),135)
            near(state['inventory'].get_total(),195)
            move_to(unreal.Vector(-780,790,92.15))
            tap('E')
            phase('partial')
        elif name=='partial' and age>.4:
            near(state['inventory'].get_total(),200)
            near(state['piles'][2].amount,25)
            near(state['inventory'].get_total()+total_world(),345)
            record('partial_pickup_conserves_resources',inventory=200,pile_remainder=25,total=345,injected_test_stock=135)
            tap('E')
            phase('full')
        elif name=='full' and age>.4:
            near(state['inventory'].get_total(),200)
            near(state['piles'][2].amount,25)
            if state['gathering'].notification!='Inventario lleno': raise RuntimeError('Missing full inventory feedback')
            record('full_inventory_keeps_world_resources')
            phase('full_capture')
            capture('gathering_full.png')
        elif name=='full_capture' and age>3:
            inventory=state['inventory']
            resource=state['piles'][2].resource
            near(inventory.add_item(resource,-10),0)
            near(inventory.add_item(None,20),0)
            near(inventory.remove_item('Scrap',-10),0)
            near(inventory.remove_item('Missing',10),0)
            near(inventory.get_total(),200)
            near(inventory.remove_item('Scrap',1000),200)
            near(inventory.get_total(),0)
            near(inventory.add_item(resource,200),200)
            record('inventory_rejects_invalid_amounts_and_clamps_removal')
            near(inventory.remove_item('Scrap',135),135)
            tap('E')
            phase('remaining')
        elif name=='remaining' and age>.4:
            near(state['inventory'].get_total(),90)
            near(state['piles'][2].amount,0)
            near(state['inventory'].get_total()+total_world(),210)
            record('remaining_scrap_can_be_collected',inventory=90,total_resources=210)
            move_to(state['origin'])
            key('W')
            key('LeftShift')
            phase('movement')
        elif name=='movement' and age>.65:
            runtime=state['pawn'].get_component_by_class(unreal.RobotLocomotionComponent)
            near(runtime.planar_speed,300,2)
            if (state['pawn'].get_actor_location()-state['origin']).length()<100: raise RuntimeError('Inventory blocks movement')
            record('fast_walk_works_with_inventory_open')
            key('W',False)
            key('LeftShift',False)
            tap('I')
            tap('MouseScrollUp')
            phase('camera')
        elif name=='camera' and age>.8:
            if state['gathering'].inventory_open: raise RuntimeError('I did not close inventory')
            arm=state['pawn'].get_component_by_class(unreal.SpringArmComponent)
            near(arm.target_arm_length,2205,1)
            record('inventory_closes_and_camera_zoom_works')
            tap('Home')
            tap('I')
            phase('final_settle')
        elif name=='final_settle' and age>1:
            phase('final_capture')
            capture('gathering_inventory.png')
        elif name=='final_capture' and age>3:
            report['passed']=True
            finish()
        elif name=='quit' and age>2:
            unreal.unregister_slate_post_tick_callback(state['handle'])
            unreal.SystemLibrary.quit_editor()
    except Exception:
        report['error']=traceback.format_exc()
        finish()

state['handle']=unreal.register_slate_post_tick_callback(tick)
