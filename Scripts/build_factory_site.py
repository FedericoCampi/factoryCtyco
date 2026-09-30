"""Add a reversible progress annex to the original factory; preserve its machines.

Run through Unreal MCP after import_factory_site_assets.apply(). Calling apply()
keeps the editor open. Only actors with our Site_ prefix are replaced on rerun.
"""
from pathlib import Path
import json
import sys
import unreal

PROJECT = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(PROJECT / 'Scripts'))
from polish_factory_visuals import _backup

MAP = '/Game/FactoryCtyco/Maps/L_FactoryDemo'
ROOT = '/Game/FactoryCtyco/Factory'
MATERIALS = ROOT + '/Materials'
MODEL_ROOT = ROOT + '/Models/SiteProgress'
LIB = unreal.EditorAssetLibrary
ML = unreal.MaterialEditingLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def material(name, color, metal=.3, rough=.75, emission=(0, 0, 0)):
    path = MATERIALS + '/' + name
    result = unreal.load_asset(path)
    if not result:
        result = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, MATERIALS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    ML.set_material_instance_parent(result, unreal.load_asset(MATERIALS + '/M_FactoryDetail'))
    ML.set_material_instance_vector_parameter_value(result, 'BaseColor', unreal.LinearColor(*color, 1))
    ML.set_material_instance_vector_parameter_value(result, 'Emission', unreal.LinearColor(*emission, 1))
    ML.set_material_instance_scalar_parameter_value(result, 'Roughness', rough)
    ML.set_material_instance_scalar_parameter_value(result, 'Metallic', metal)
    assert LIB.save_loaded_asset(result, False)
    return result


def box(name, position, dimensions, mat, collision=False):
    actor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*position))
    actor.set_actor_label('Site_' + name)
    actor.set_folder_path('Factory / Site progress')
    mesh = actor.static_mesh_component
    mesh.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    mesh.set_material(0, mat)
    mesh.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    actor.set_actor_scale3d(unreal.Vector(*(v / 100 for v in dimensions)))
    return actor


def landmark(name, stage, pos, footprint, label, marker, mesh=None):
    # Service fronts face the annex; their backs sit against the old yard.
    actor = ACTORS.spawn_actor_from_class(unreal.FactorySiteLandmark, unreal.Vector(*pos),
                                         unreal.Rotator(pitch=0, yaw=180 if stage < 3 else 0, roll=0))
    actor.set_actor_label('Site_' + name)
    actor.set_folder_path('Factory / Site progress')
    actor.set_editor_property('required_stage', stage)
    actor.set_editor_property('footprint', unreal.Vector2D(*footprint))
    actor.set_editor_property('site_label', label)
    actor.set_editor_property('marker_material', marker)
    actor.set_editor_property('solid_when_built', stage == 1)
    if mesh:
        actor.visual.set_static_mesh(unreal.load_asset(MODEL_ROOT + '/' + mesh))
    return actor


def apply():
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert not levels.is_in_play_in_editor(), 'Stop PIE before editing the factory'
    required = [MODEL_ROOT + '/' + n for n in ('SM_FactoryWorkshop', 'SM_FactoryChargeStation')]
    assert all(LIB.does_asset_exist(p) for p in required), 'Import the Blender site assets first'
    names = ['MI_SiteDeckA', 'MI_SiteDeckB', 'MI_SiteDeckC', 'MI_SiteEdge', 'MI_SiteMarking', 'MI_SiteLight']
    backup = _backup([MAP] + [MATERIALS + '/' + n for n in names])
    assert levels.load_level(MAP)
    factories = [a for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.FactoryDemoWorld)]
    assert len(factories) == 1
    factory = factories[0]
    original_buildings = sorted(a.get_path_name() for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.FactoryBuilding))
    original_piles = sorted(a.get_path_name() for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.FactoryResourcePile))
    for actor in ACTORS.get_all_level_actors():
        if actor.get_actor_label().startswith('Site_'):
            ACTORS.destroy_actor(actor)
    decks = [material(names[i], c, .45, .79) for i, c in enumerate(((.17,.215,.235), (.19,.23,.25), (.155,.20,.225)))]
    edge = material('MI_SiteEdge', (.032,.051,.065), .6, .55)
    marking = material('MI_SiteMarking', (.79,.40,.065), .15, .69)
    light = material('MI_SiteLight', (.04,.45,.34), .2, .4, (.025,.4,.3))
    # One continuous collider; thin separate tiles give seams without gameplay gaps.
    box('Deck', (0,1800,-24), (2000,1200,48), edge, True)
    box('Bridge', (0,1175,-12), (400,150,24), edge, True)
    for ix, x in enumerate(range(-900, 1000, 200)):
        for iy, y in enumerate(range(1300, 2400, 200)):
            box('Tile_%d_%d' % (ix,iy), (x,y,.25), (197.5,197.5,.5), decks[(ix+iy)%3])
    # Rails stay outside all 36 build cells, with a central entrance to the old yard.
    for x in (-989,989):
        box('SideCurb_' + str(x), (x,1800,9), (18,1200,18), edge, True)
        box('SideRail_' + str(x), (x,1800,76), (10,1200,10), edge, True)
        for y in (1220,1600,2000,2380):
            box('Post_%d_%d' % (x,y), (x,y,40), (18,18,80), edge, True)
            box('PostLight_%d_%d' % (x,y), (x,y,84), (20,20,6), light)
    box('EndCurb', (0,2389,9), (1960,18,18), edge, True)
    box('EndRail', (0,2389,76), (1960,10,10), edge, True)
    for x in (-600,-200,200,600):
        box('EndPost_' + str(x), (x,2389,40), (18,18,80), edge, True)
    for x in (-610,610):
        box('FrontCurb_' + str(x), (x,1210,9), (750,18,18), edge, True)
        box('FrontRail_' + str(x), (x,1210,76), (750,10,10), edge, True)
        for dx in (-350,350):
            box('FrontPost_%d_%d' % (x,dx), (x+dx,1210,40), (18,18,80), edge, True)
    for y in (1120,1160,1200,1240):
        for x in (-177,177):
            box('EntranceStripe_%d_%d' % (x,y), (x,y,.7), (20,23,1), marking)
    # Guides are flush and non-colliding. Expansion lighting belongs to saved stage3.
    for x in range(-800, 801, 200):
        for y in range(1600, 2201, 200):
            for sign in (-1,1):
                box('Cell_%d_%d_%d' % (x,y,sign), (x+sign*85,y-85,.7), (12,2,1), marking)
    marker = unreal.load_asset(MATERIALS + '/M_FactoryDetail')
    landmark('Taller', 1, (-650,1350,0), (330,230), '01 / TALLER', marker, 'SM_FactoryWorkshop')
    landmark('Carga', 2, (650,1350,0), (260,260), '02 / CARGA', marker, 'SM_FactoryChargeStation')
    landmark('Expansion', 3, (0,1925,0), (1900,850), '03 / AMPLIACION', marker)
    factory.set_editor_property('enable_site_progress', True)
    factory.set_editor_property('expansion_min', unreal.Vector2D(-950,1500))
    factory.set_editor_property('expansion_max', unreal.Vector2D(950,2350))
    factory.set_editor_property('connector_min', unreal.Vector2D(-100,850))
    factory.set_editor_property('connector_max', unreal.Vector2D(100,1500))
    assert original_buildings == sorted(a.get_path_name() for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.FactoryBuilding))
    assert original_piles == sorted(a.get_path_name() for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.FactoryResourcePile))
    assert levels.save_current_level()
    report = {'passed': True, 'map': MAP, 'backup': str(backup), 'initial_buildings_preserved':len(original_buildings),
              'piles_preserved':len(original_piles), 'expansion_min':[-950,1500], 'expansion_max':[950,2350],
              'build_cells':36, 'connector_cells':[[0,1000],[0,1200],[0,1400]], 'thresholds':[5,10,20], 'reveal_seconds':2,
              'decorative_landmarks':['Taller','Carga'], 'functional_unlock':'36 construction cells'}
    (PROJECT / 'Docs' / 'factory_site_build.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.log('[SITE_BUILD] ' + json.dumps(report))
    return report


if __name__ == '__main__':
    apply()
