"""Rendered PIE acceptance: economy, construction, processing, belts and save/load."""
import json
import time
import traceback
from pathlib import Path
import unreal

PROJECT=Path(unreal.Paths.project_dir()).resolve()
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
assert levels.load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),"t.MaxFPS 30")
build=json.loads((PROJECT/"Docs/factory_demo_build.json").read_text())
report={"passed":False,"checks":{},"scope":"Rendered Unreal PIE; real input bindings plus public gameplay operations. No generated GPU jobs."}
state={"phase":"warmup","started":time.monotonic(),"at":time.monotonic()}


def phase(name): state.update(phase=name,at=time.monotonic())
def check(name,**values):
    report["checks"][name]={"passed":True,**values}
    unreal.log("[DEMO_CHECK] "+name)
def key(name,down=True): state["camera"].send_editor_test_input(name,1.0 if down else 0.0,down)
def tap(name): key(name);key(name,False)
def move(position):
    state["pawn"].character_movement.stop_movement_immediately()
    state["pawn"].set_actor_location(position,False,True)
def machine(item_id): return next(b for b in state["factory"].buildings() if str(b.persistent_id)==item_id)
def near(building):
    for x,y in [(0,145),(0,-145),(145,0),(-145,0),(145,145),(-145,-145)]:
        move(building.get_actor_location()+unreal.Vector(x,y,92))
        state["demo"].refresh_focus()
        if state["demo"].focused_building==building:return
    raise RuntimeError("No accessible interaction side for "+str(building.persistent_id))
def amounts(component): return {str(k):int(v) for k,v in component.items.items()}
def snapshot():
    factory=state["factory"]
    return {"inventory":amounts(state["inventory"]),"piles":{str(p.persistent_id):p.amount for p in state["piles"]},
        "machines":{str(b.persistent_id):{"input":amounts(b.input),"output":amounts(b.output),"progress":round(b.progress_seconds,4),"yaw":round(b.get_actor_rotation().yaw),"filter":str(b.storage_item),"paid":b.paid_scrap} for b in factory.buildings()},
        "produced":factory.plates_produced,"delivered":factory.plates_delivered}
def mass():
    def value(inv): return inv.get_quantity("Scrap")+inv.get_quantity("Fragments")+2*inv.get_quantity("Plate")
    return value(state["inventory"])+sum(p.amount for p in state["piles"])+sum(value(b.input)+value(b.output)+b.paid_scrap for b in state["factory"].buildings())
def capture(name): print("[captura desactivada]", 1440,900,str(PROJECT/"Docs"/name))
def finish():
    phase("quit")
    report["elapsed_seconds"]=round(time.monotonic()-state["started"],1)
    (PROJECT/"Docs/factory_demo_playtest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    unreal.log("[FACTORY_DEMO_PLAYTEST] "+json.dumps(report))
    levels.editor_request_end_play()


def tick(delta):
    try:
        age=time.monotonic()-state["at"]
        name=state["phase"]
        if name!="quit" and time.monotonic()-state["started"]>240: raise RuntimeError("Demo acceptance timed out in "+name)
        if name=="warmup" and age>9:
            levels.editor_request_begin_play()
            phase("spawn")
        elif name=="spawn" and age>3:
            worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
            if not worlds:return
            world=worlds[0]
            pawn=unreal.GameplayStatics.get_player_pawn(world,0)
            if not pawn:return
            demo=pawn.get_component_by_class(unreal.FactoryDemoComponent)
            assert demo and demo.factory,"Missing demo component/manager"
            state.update(world=world,pawn=pawn,demo=demo,factory=demo.factory,inventory=demo.inventory() if hasattr(demo,"inventory") else pawn.get_component_by_class(unreal.FactoryInventoryComponent),
                camera=pawn.get_component_by_class(unreal.FactoryCameraComponent),gathering=pawn.get_component_by_class(unreal.FactoryGatheringComponent))
            state["piles"]=sorted(unreal.GameplayStatics.get_all_actors_of_class(world,unreal.FactoryResourcePile),key=lambda p:str(p.persistent_id))
            demo.factory.set_editor_property("save_slot","FactoryCtycoDemo_AcceptanceOnly")
            assert len(demo.factory.buildings())==4
            assert isinstance(unreal.GameplayStatics.get_player_controller(world,0).get_hud(),unreal.FactoryDemoHUD)
            assert state["inventory"].get_total()==0 and mass()==210
            check("spawn_and_starting_resources",mass=mass(),machines=4)
            move(state["piles"][0].get_actor_location()+unreal.Vector(0,125,92))
            tap("I");tap("E")
            phase("gather")
        elif name=="gather" and age>.5:
            assert state["inventory"].get_quantity("Scrap")==30 and state["piles"][0].amount==0
            assert state["gathering"].inventory_open
            check("gather_and_inventory_controls")
            tap("I")
            tap("B");tap("R")
            phase("build_menu")
        elif name=="build_menu" and age>.5:
            assert state["demo"].building and state["demo"].quarter_turns==1
            tap("RightMouseButton")
            phase("cancel")
        elif name=="cancel" and age>.4:
            demo=state["demo"]
            assert not demo.building and state["inventory"].get_quantity("Scrap")==30
            assert demo.build_at(3,unreal.Vector(20000,0,4),0) is None
            assert demo.build_at(3,machine("Starter_0").get_actor_location(),0) is None
            free=next(unreal.Vector(x,y,4) for x in range(-600,601,200) for y in [400,-400,600,-600] if not state["factory"].placement_problem(unreal.Vector(x,y,4)))
            move(free+unreal.Vector(0,0,92))
            assert demo.build_at(3,free,0) is None,"Built on robot"
            move(free+unreal.Vector(0,180,92))
            extra=demo.build_at(3,free,0)
            assert extra and state["inventory"].get_quantity("Scrap")==28
            assert demo.build_at(3,free,0) is None
            near(extra)
            # Add temporary test stock through the runtime API. Editing component
            # properties in PIE can rerun the pawn's Blueprint construction script.
            assert state["inventory"].add_item(state["factory"].resource("Scrap"),172)==172
            assert not demo.dismantle(),"Dismantle lost content at full capacity"
            assert state["inventory"].remove_item("Scrap",172)==172
            removed=demo.dismantle()
            assert removed and state["inventory"].get_quantity("Scrap")==30,(removed,amounts(state["inventory"]),demo.notification)
            assert mass()==210
            check("construction_validation_cancel_cost_and_refund")
            near(machine("Starter_2"));tap("E")
            phase("crusher_loaded")
        elif name=="crusher_loaded" and age>.4:
            assert machine("Starter_2").input.get_quantity("Scrap")==20,amounts(machine("Starter_2").input)
            assert state["inventory"].get_quantity("Scrap")==10
            assert machine("Starter_2").output.get_total()==0
            phase("crusher_cycle")
        elif name=="crusher_cycle" and age>3.2:
            crusher=machine("Starter_2")
            assert crusher.output.get_quantity("Fragments")==2
            assert crusher.output.add_item(state["factory"].resource("Fragments"),18)==18
            state["blocked_input"]=crusher.input.get_quantity("Scrap")
            state["blocked_progress"]=crusher.progress_seconds
            phase("blocked_output")
        elif name=="blocked_output" and age>4:
            crusher=machine("Starter_2")
            assert crusher.input.get_quantity("Scrap")==state["blocked_input"]
            assert abs(crusher.progress_seconds-state["blocked_progress"])<.01
            assert crusher.output.remove_item("Fragments",18)==18
            tap("F")
            phase("withdraw_fragments")
        elif name=="withdraw_fragments" and age>.4:
            assert state["inventory"].get_quantity("Fragments")==2
            near(machine("Starter_4"));tap("E")
            phase("smelt")
        elif name=="smelt" and age>4.5:
            assert machine("Starter_4").output.get_quantity("Plate")==1
            tap("F")
            phase("manual_plate")
        elif name=="manual_plate" and age>.4:
            assert state["inventory"].get_quantity("Plate")==1
            assert mass()==210
            check("manual_recipes_timing_output_pause_and_resource_conservation")
            move(state["piles"][1].get_actor_location()+unreal.Vector(0,120,92))
            tap("E")
            phase("more_scrap")
        elif name=="more_scrap" and age>.4:
            assert state["inventory"].get_quantity("Scrap")==40
            move(unreal.Vector(0,800,100))
            # Place the first segment backwards to test directional connections.
            state["belts"]=[]
            for index,p in enumerate(build["belt_slots"]):
                belt=state["demo"].build_at(3,unreal.Vector(*p),2 if index==0 else 0)
                assert belt,"Belt slot not buildable: "+str(p)+" "+state["demo"].notification
                state["belts"].append(str(belt.persistent_id))
            assert state["inventory"].get_quantity("Scrap")==34
            near(machine("Starter_0"));tap("E")
            phase("reverse_belt")
        elif name=="reverse_belt" and age>1.2:
            source=machine("Starter_0")
            assert source.input.get_quantity("Scrap")==34
            assert state["inventory"].get_quantity("Plate")==1,"Storage accepted the wrong resource"
            assert not source.connected
            wrong=machine(state["belts"][0]);near(wrong)
            assert state["demo"].dismantle()
            fixed=state["demo"].build_at(3,unreal.Vector(*build["belt_slots"][0]),0)
            assert fixed
            state["belts"][0]=str(fixed.persistent_id)
            move(unreal.Vector(0,600,100))
            check("straight_belt_direction_and_storage_filter")
            phase("flow")
        elif name=="flow" and age>6:
            assert machine("Starter_0").input.get_quantity("Scrap")<34
            assert mass()==210
            factory=state["factory"]
            expected=snapshot()
            assert factory.save_factory(state["pawn"])
            state["saved"]=expected
            phase("save_in_flight")
        elif name=="save_in_flight" and age>2:
            assert state["factory"].load_factory(state["pawn"])
            assert snapshot()==state["saved"],"Save/load changed amounts, progress, filters or orientation"
            assert mass()==210
            check("save_load_preserves_in_flight_material_and_progress")
            move(state["piles"][2].get_actor_location()+unreal.Vector(0,120,92))
            tap("E")
            phase("spare_stock")
        elif name=="spare_stock" and age>.5:
            assert state["inventory"].get_quantity("Scrap")==30
            move(unreal.Vector(0,600,100))
            state["preview_target"]=next(unreal.Vector(x,y,4) for y in [400,-400,600] for x in [0,-400,400,-600,600] if not state["factory"].placement_problem(unreal.Vector(x,y,4)))
            tap("B");tap("Four")
            phase("preview_capture")
        elif name=="preview_capture" and age>.6:
            assert state["demo"].building and state["demo"].selected_index==3
            assert state["demo"].set_editor_test_cursor(state["preview_target"])
            phase("preview_settle")
        elif name=="preview_settle" and age>1:
            assert (state["demo"].preview_position-state["preview_target"]).length()<1,(state["demo"].preview_position,state["preview_target"])
            assert state["demo"].preview_valid,state["demo"].placement_message
            phase("preview_done")
            capture("factory_demo_build_mode.png")
        elif name=="preview_done" and age>3:
            tap("LeftMouseButton")
            phase("click_placed")
        elif name=="click_placed" and age>.5:
            assert state["inventory"].get_quantity("Scrap")==28
            assert len(state["factory"].buildings())==8
            check("mouse_preview_and_click_construction")
            tap("RightMouseButton")
            phase("close_build")
        elif name=="close_build" and age>.4:
            assert not state["demo"].building
            near(machine("Starter_6"))
            phase("goal")
        elif name=="goal":
            assert mass()==210,"Transport duplicated or lost resources"
            if state["factory"].goal_complete():
                check("automatic_line_produces_twenty_plates",stored=state["factory"].stored_plates(),delivered=state["factory"].plates_delivered,mass=mass())
                tap("I")
                phase("final_capture")
                capture("factory_demo_completed.png")
        elif name=="final_capture" and age>3:
            tap("F5")
            phase("save_key")
        elif name=="save_key" and age>.5:
            assert "guardada" in state["demo"].notification
            tap("F9")
            phase("load_key")
        elif name=="load_key" and age>.6:
            assert "cargada" in state["demo"].notification
            assert state["factory"].goal_complete() and mass()==210
            check("save_and_load_keyboard_controls")
            report["passed"]=True
            finish()
        elif name=="quit" and age>2:
            unreal.unregister_slate_post_tick_callback(state["handle"])
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            unreal.SystemLibrary.quit_editor()
        elif name=="failure_capture" and age>3:
            finish()
    except Exception:
        report["error"]=traceback.format_exc()
        unreal.log_error(report["error"])
        phase("failure_capture")
        capture("factory_demo_failure.png")


state["handle"]=unreal.register_slate_post_tick_callback(tick)
