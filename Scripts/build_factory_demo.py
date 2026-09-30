"""Create an isolated playable factory map and its editable data definitions."""
import json
import traceback
from pathlib import Path
import unreal

PROJECT=Path(unreal.Paths.project_dir()).resolve()
ROOT="/Game/FactoryCtyco/Factory"
MAP="/Game/FactoryCtyco/Maps/L_FactoryDemo"
assets=unreal.AssetToolsHelpers.get_asset_tools()
lib=unreal.EditorAssetLibrary
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report={"passed":False}
bindings=json.loads((PROJECT/"Docs/factory_demo_bindings.json").read_text())


def save(asset):
    assert lib.save_loaded_asset(asset,False),asset.get_path_name()


def data_asset(name,cls):
    folder=ROOT+"/Definitions"
    lib.make_directory(folder)
    if lib.does_asset_exist(folder+"/"+name): return unreal.load_asset(folder+"/"+name)
    factory=unreal.DataAssetFactory()
    factory.set_editor_property("data_asset_class",cls)
    return assets.create_asset(name,folder,cls,factory)


def model(role):
    source=bindings[role]
    mesh=unreal.load_asset(ROOT+"/Models/"+source+"/SM_"+source)
    assert isinstance(mesh,unreal.StaticMesh),source
    return mesh


def spawn(cls,position,rotation=None):
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    gameplay=unreal.get_default_object(unreal.GameplayStatics)
    transform=unreal.Transform(location=position,rotation=rotation or unreal.Rotator())
    scale=unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT
    obj=gameplay.call_method("BeginDeferredActorSpawnFromClass",args=(world,cls,transform,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,scale))
    assert obj is not None
    return gameplay.call_method("FinishSpawningActor",args=(obj,transform,scale))


def flat_material(name,color,preview=False):
    folder=ROOT+"/Materials"
    lib.make_directory(folder)
    path=folder+"/"+name
    mat=unreal.load_asset(path) if lib.does_asset_exist(path) else assets.create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
    ml=unreal.MaterialEditingLibrary
    ml.delete_all_material_expressions(mat)
    mat.set_editor_property("shading_model",unreal.MaterialShadingModel.MSM_UNLIT)
    rgb=ml.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector,-200,0)
    rgb.set_editor_property("constant",unreal.LinearColor(*color))
    ml.connect_material_property(rgb,"",unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if preview:
        mat.set_editor_property("blend_mode",unreal.BlendMode.BLEND_TRANSLUCENT)
        alpha=ml.create_material_expression(mat,unreal.MaterialExpressionConstant,-200,120)
        alpha.set_editor_property("r",.48)
        ml.connect_material_property(alpha,"",unreal.MaterialProperty.MP_OPACITY)
    ml.recompile_material(mat)
    save(mat)
    return mat


try:
    resources=[]
    for item_id,label,color in [("Scrap","Chatarra",(1,.48,.13,1)),("Fragments","Triturado",(.47,.66,.76,1)),("Plate","Placas",(.12,.80,.66,1))]:
        resource=data_asset("DA_"+item_id,unreal.FactoryResourceDefinition)
        resource.set_editor_property("item_id",item_id)
        resource.set_editor_property("display_name",unreal.Text(label))
        resource.set_editor_property("description",unreal.Text(label+" para la fábrica de reciclaje."))
        resource.set_editor_property("color",unreal.LinearColor(*color))
        mesh=model(item_id)
        resource.set_editor_property("pickup_mesh",mesh)
        resource.set_editor_property("pickup_scale",unreal.Vector(.80,.80,.80) if item_id=="Scrap" else unreal.Vector(.30,.30,.30))
        save(resource)
        resources.append(resource)
    catalog=[]
    for building_id,label,kind,cost in [
        ("Crusher","Trituradora",unreal.FactoryBuildingKind.PROCESSOR,20),
        ("Smelter","Fundición",unreal.FactoryBuildingKind.PROCESSOR,25),
        ("Storage","Depósito",unreal.FactoryBuildingKind.STORAGE,10),
        ("Belt","Cinta recta",unreal.FactoryBuildingKind.BELT,2),
    ]:
        definition=data_asset("DB_"+building_id,unreal.FactoryBuildingDefinition)
        definition.set_editor_property("building_id",building_id)
        definition.set_editor_property("display_name",unreal.Text(label))
        definition.set_editor_property("kind",kind)
        definition.set_editor_property("scrap_cost",cost)
        definition.set_editor_property("capacity",20 if kind==unreal.FactoryBuildingKind.PROCESSOR else 100)
        mesh=model(building_id)
        definition.set_editor_property("mesh",mesh)
        bounds=mesh.get_bounding_box()
        size=bounds.max-bounds.min
        scale=180/max(size.x,size.y)
        meshscale=unreal.Vector(scale,scale,scale)
        if building_id=="Belt": meshscale=unreal.Vector(200/size.x,140/size.y,30/size.z)
        definition.set_editor_property("mesh_scale",meshscale)
        definition.set_editor_property("mesh_offset",unreal.Vector(0,0,-bounds.min.z*meshscale.z))
        definition.set_editor_property("mesh_yaw",0.0)
        definition.set_editor_property("input_item","Scrap" if building_id=="Crusher" else "Fragments" if building_id=="Smelter" else "None")
        definition.set_editor_property("output_item","Fragments" if building_id=="Crusher" else "Plate" if building_id=="Smelter" else "None")
        definition.set_editor_property("input_quantity",2)
        definition.set_editor_property("output_quantity",2 if building_id=="Crusher" else 1)
        definition.set_editor_property("cycle_seconds",3.0 if building_id=="Crusher" else 4.0)
        save(definition)
        catalog.append(definition)

    pawnpath=ROOT+"/BP_FactoryRobot"
    pawn=unreal.load_asset(pawnpath) if lib.does_asset_exist(pawnpath) else assets.duplicate_asset("BP_FactoryRobot",ROOT,unreal.load_asset("/Game/FactoryCtyco/Blueprints/BP_Robot1"))
    subsystem=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    funcs=unreal.SubobjectDataBlueprintFunctionLibrary
    handles=subsystem.k2_gather_subobject_data_for_blueprint(pawn)
    has_demo=False
    for handle in handles:
        obj=funcs.get_object_for_blueprint(subsystem.k2_find_subobject_data_from_handle(handle),pawn)
        if isinstance(obj,unreal.FactoryDemoComponent): has_demo=True
        elif isinstance(obj,unreal.SpringArmComponent):
            obj.set_editor_property("target_arm_length",3000.0)
            obj.set_editor_property("target_offset",unreal.Vector(0,-320,0))
    if not has_demo:
        handle,failure=subsystem.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=handles[0],new_class=unreal.FactoryDemoComponent,blueprint_context=pawn))
        if str(failure): raise RuntimeError(str(failure))
        subsystem.rename_subobject(handle,"FactoryDemo")
    unreal.BlueprintEditorLibrary.compile_blueprint(pawn)
    save(pawn)
    modepath=ROOT+"/BP_FactoryDemoMode"
    mode=unreal.load_asset(modepath) if lib.does_asset_exist(modepath) else assets.duplicate_asset("BP_FactoryDemoMode",ROOT,unreal.load_asset("/Game/FactoryCtyco/Blueprints/BP_FactoryGameMode"))
    defaults=unreal.get_default_object(mode.generated_class())
    defaults.set_editor_property("default_pawn_class",pawn.generated_class())
    defaults.set_editor_property("hud_class",unreal.FactoryDemoHUD)
    unreal.BlueprintEditorLibrary.compile_blueprint(mode)
    save(mode)

    if lib.does_asset_exist(MAP): assert levels.load_level(MAP)
    else: assert levels.new_level_from_template(MAP,"/Game/FactoryCtyco/Maps/L_Recoleccion")
    for actor in actors.get_all_level_actors():
        if isinstance(actor,(unreal.FactoryBuilding,unreal.FactoryDemoWorld)) or actor.get_actor_label().startswith("FactoryGuide_"):
            actors.destroy_actor(actor)
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property("default_game_mode",mode.generated_class())
    factory=spawn(unreal.FactoryDemoWorld,unreal.Vector())
    factory.set_actor_label("FactoryDemo_Simulation")
    factory.set_editor_property("resources",resources)
    factory.set_editor_property("catalog",catalog)
    factory.set_editor_property("area_min",unreal.Vector2D(-950,-950))
    factory.set_editor_property("area_max",unreal.Vector2D(950,950))
    factory.set_editor_property("valid_material",flat_material("M_BuildValid",(.03,.6,.35,1),True))
    factory.set_editor_property("invalid_material",flat_material("M_BuildInvalid",(.8,.03,.02,1),True))
    for actor in actors.get_all_level_actors():
        if isinstance(actor,unreal.FactoryResourcePile):
            actor.set_editor_property("resource",resources[0])
            actor.set_editor_property("amount",30)
            actor.refresh_visuals()
        elif isinstance(actor,unreal.PlayerStart):
            actor.set_actor_location(unreal.Vector(0,800,100),False,True)
    candidates=[]
    for y in [0,200,-200,400,-400]:
        positions=[unreal.Vector(x,y,4) for x in range(-600,601,200)]
        problems=[factory.placement_problem(p) for p in positions]
        candidates.append({"y":y,"problems":problems})
        if not any(problems): break
    else: raise RuntimeError("No clear starter row: "+json.dumps(candidates))
    report["placement_scan"]=candidates
    placed=[]
    for index,definition_index,storage_item in [(0,2,"Scrap"),(2,0,"Scrap"),(4,1,"Scrap"),(6,2,"Plate")]:
        obj=spawn(unreal.FactoryBuilding,positions[index])
        obj.set_actor_label("Factory_"+str(index)+"_"+str(catalog[definition_index].building_id))
        obj.set_editor_property("persistent_id","Starter_"+str(index))
        obj.set_editor_property("definition",catalog[definition_index])
        obj.set_editor_property("storage_item",storage_item)
        obj.set_editor_property("paid_scrap",0)
        obj.refresh_visuals()
        placed.append({"id":str(obj.persistent_id),"definition":str(obj.definition.building_id),"position":[positions[index].x,positions[index].y,positions[index].z],"storage_item":storage_item})
    guide=flat_material("M_BeltSlot",(.014,.13,.11,1))
    cube=unreal.load_asset("/Engine/BasicShapes/Cube")
    for index in [1,3,5]:
        obj=spawn(unreal.StaticMeshActor,positions[index]-unreal.Vector(0,0,2))
        obj.set_actor_label("FactoryGuide_Belt_"+str(index))
        obj.static_mesh_component.set_static_mesh(cube)
        obj.static_mesh_component.set_material(0,guide)
        obj.static_mesh_component.set_collision_profile_name("NoCollision")
        obj.static_mesh_component.set_cast_shadow(False)
        obj.set_actor_scale3d(unreal.Vector(1.8,1.8,.01))
    assert levels.save_current_level()
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(-1700,2000,2200),unreal.Rotator(pitch=-55,yaw=-45))
    report.update(passed=True,map=MAP,starter_buildings=placed,belt_slots=[[positions[i].x,positions[i].y,4] for i in [1,3,5]],
        bindings=bindings,grid_cm=200,goal="20 plates stored with conveyor delivery",save_slot="FactoryCtycoDemo_v1")
except Exception:
    report["error"]=traceback.format_exc()
    unreal.log_error(report["error"])
finally:
    (PROJECT/"Docs/factory_demo_build.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    unreal.log("[FACTORY_DEMO_BUILD] "+json.dumps(report))
    unreal.SystemLibrary.quit_editor()
