"""Add reusable inventory, scrap definition, pickups and the first gameplay HUD."""
import json
from pathlib import Path
import unreal

project=Path(unreal.Paths.project_dir()).resolve()
lib=unreal.EditorAssetLibrary
assets=unreal.AssetToolsHelpers.get_asset_tools()
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report={'passed':False}

def save(asset):
    assert lib.save_loaded_asset(asset,False), asset.get_path_name()

def spawn(cls,location):
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    gameplay=unreal.get_default_object(unreal.GameplayStatics)
    transform=unreal.Transform(location=location)
    scale=unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT
    actor=gameplay.call_method('BeginDeferredActorSpawnFromClass',args=(world,cls,transform,
        unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,scale))
    if actor is None: raise RuntimeError('Cannot spawn '+str(cls))
    return gameplay.call_method('FinishSpawningActor',args=(actor,transform,scale))

try:
    folder='/Game/FactoryCtyco/Resources'
    lib.make_directory(folder)
    resource=unreal.load_asset(folder+'/DA_Scrap') if lib.does_asset_exist(folder+'/DA_Scrap') else None
    if resource is None:
        factory=unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class',unreal.FactoryResourceDefinition)
        resource=assets.create_asset('DA_Scrap',folder,unreal.FactoryResourceDefinition,factory)
    assert resource is not None
    resource.set_editor_property('item_id','Scrap')
    resource.set_editor_property('display_name',unreal.Text('Chatarra'))
    resource.set_editor_property('description',unreal.Text('Metal recuperado para construir y procesar.'))
    resource.set_editor_property('color',unreal.LinearColor(1,.52,.16,1))
    save(resource)

    markerpath=folder+'/M_ScrapFocus'
    marker=unreal.load_asset(markerpath) if lib.does_asset_exist(markerpath) else assets.create_asset('M_ScrapFocus',folder,unreal.Material,unreal.MaterialFactoryNew())
    ml=unreal.MaterialEditingLibrary
    ml.delete_all_material_expressions(marker)
    color=ml.create_material_expression(marker,unreal.MaterialExpressionConstant3Vector,-240,0)
    color.set_editor_property('constant',unreal.LinearColor(.025,.5,.4,1))
    ml.connect_material_property(color,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    marker.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    ml.recompile_material(marker)
    save(marker)

    bp=unreal.load_asset('/Game/FactoryCtyco/Blueprints/BP_Robot1')
    subsystem=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    funcs=unreal.SubobjectDataBlueprintFunctionLibrary
    handles=subsystem.k2_gather_subobject_data_for_blueprint(bp)
    for cls,name in [(unreal.FactoryInventoryComponent,'FactoryInventory'),(unreal.FactoryGatheringComponent,'FactoryGathering')]:
        component=None
        for handle in handles:
            obj=funcs.get_object_for_blueprint(subsystem.k2_find_subobject_data_from_handle(handle),bp)
            if isinstance(obj,cls): component=obj
        if component is None:
            handle,failure=subsystem.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=handles[0],new_class=cls,blueprint_context=bp))
            if str(failure): raise RuntimeError(str(failure))
            subsystem.rename_subobject(handle,name)
            component=funcs.get_object_for_blueprint(subsystem.k2_find_subobject_data_from_handle(handle),bp)
        if isinstance(component,unreal.FactoryInventoryComponent): component.set_editor_property('capacity',200)
        else: component.set_editor_property('interaction_distance',200.0)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)
    mode=unreal.load_asset('/Game/FactoryCtyco/Blueprints/BP_FactoryGameMode')
    mode.modify()
    cdo=unreal.get_default_object(mode.generated_class())
    cdo.modify()
    cdo.set_editor_property('hud_class',unreal.FactoryGatheringHUD)
    unreal.BlueprintEditorLibrary.compile_blueprint(mode)
    save(mode)

    assert levels.load_level('/Game/FactoryCtyco/Maps/L_Recoleccion')
    existing={a.get_actor_label():a for a in actors.get_all_level_actors() if isinstance(a,unreal.FactoryResourcePile)}
    metal=unreal.load_asset('/Game/FactoryCtyco/Environments/SceneRobot/Gunmetal___abraded_rolled_steel')
    accent=unreal.load_asset('/Game/FactoryCtyco/Environments/SceneRobot/Safety_orange___chipped_enamel')
    assert metal and accent
    for material in [metal,accent]:
        material.set_editor_property('used_with_instanced_static_meshes',True)
        ml.recompile_material(material)
        save(material)
    locations=[(-140,830,4),(180,800,4),(-780,650,4),(780,650,4),(-750,-680,4),(750,-650,4),(0,-730,4)]
    placed=[]
    for index,position in enumerate(locations,1):
        name=f'Scrap_{index:02d}'
        pile=existing.get(name) or spawn(unreal.FactoryResourcePile,unreal.Vector(*position))
        pile.set_actor_label(name)
        pile.set_actor_location(unreal.Vector(*position),False,True)
        pile.set_editor_property('persistent_id',name)
        pile.set_editor_property('resource',resource)
        pile.set_editor_property('amount',30)
        pile.set_editor_property('metal_material',metal)
        pile.set_editor_property('accent_material',accent)
        pile.set_editor_property('focus_material',marker)
        pile.refresh_visuals()
        placed.append(name)
    assert levels.save_current_level()
    report.update(passed=True,resource=resource.get_path_name(),piles=placed,world_quantity=210,
        inventory_capacity=200,interaction_distance_cm=200,controls={'gather':'E','inventory':'I'},persistence='Session only')
finally:
    (project/'Docs/gathering_build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('[GATHERING_BUILD] '+json.dumps(report))
