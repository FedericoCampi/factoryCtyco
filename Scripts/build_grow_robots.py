"""Build the first decision-driven creature diorama without modifying the factory map."""
import json
import runpy
import shutil
import time
import traceback
from pathlib import Path
import unreal

PROJECT = Path(unreal.Paths.project_dir()).resolve()
MAP = "/Game/FactoryCtyco/Maps/L_GrowRobots"
ROOT = "/Game/FactoryCtyco/Grow"
LIB = unreal.EditorAssetLibrary
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def spawn(cls, location=unreal.Vector(), rotation=unreal.Rotator()):
    actor = ACTORS.spawn_actor_from_class(cls, location, rotation)
    assert actor, str(cls)
    return actor


def apply():
    report = {"passed": False, "map": MAP}
    try:
        assert not LEVELS.is_in_play_in_editor(), "Stop PIE before building the map"
        # Keep authored previous iterations recoverable when rerunning this builder.
        backup = PROJECT / "Saved/GrowEvolutionWork" / ("BeforeMap-" + time.strftime("%Y%m%d-%H%M%S"))
        for relative in ("Content/FactoryCtyco/Maps/L_GrowRobots.umap", "Content/FactoryCtyco/Grow/DA_RobotSpecies.uasset"):
            source = PROJECT / relative
            if source.exists():
                destination = backup / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
        imported = runpy.run_path(str(PROJECT / "Scripts/import_grow_robot_accessories.py"))["apply"]()
        assert imported["passed"]
        LIB.make_directory(ROOT)
        path = ROOT + "/DA_RobotSpecies"
        if LIB.does_asset_exist(path):
            species = unreal.load_asset(path)
        else:
            factory = unreal.DataAssetFactory()
            factory.set_editor_property("data_asset_class", unreal.GrowSpeciesDefinition)
            species = TOOLS.create_asset("DA_RobotSpecies", ROOT, unreal.GrowSpeciesDefinition, factory)
        species.set_editor_property("species_id", "Robot")
        species.set_editor_property("display_name", "Robots")
        rig = "/Game/FactoryCtyco/Characters/Robot1/Rigged/"
        species.set_editor_property("body_mesh", unreal.load_asset(rig + "SK_Robot1"))
        species.set_editor_property("idle_animation", unreal.load_asset(rig + "A_Robot1_Idle"))
        species.set_editor_property("walk_animation", unreal.load_asset(rig + "A_Robot1_Walk"))
        species.set_editor_property("body_scale", unreal.Vector(.70, .70, .70))
        species.set_editor_property("body_rotation", unreal.Rotator(yaw=-90))
        species.set_editor_property("accessory_offset", unreal.Vector(-22, 0, 82))
        species.set_editor_property("profession_meshes", {
            unreal.GrowProfession.BUILDER: unreal.load_asset(ROOT + "/Models/SM_GrowBuilderPack"),
            unreal.GrowProfession.CARETAKER: unreal.load_asset(ROOT + "/Models/SM_GrowCaretakerPack"),
            unreal.GrowProfession.COURIER: unreal.load_asset(ROOT + "/Models/SM_GrowCourierPack"),
        })
        assert LIB.save_loaded_asset(species, False)

        if LIB.does_asset_exist(MAP):
            assert LEVELS.load_level(MAP)
        else:
            assert LEVELS.new_level_from_template(MAP, "/Game/FactoryCtyco/Maps/L_FactoryDemo")
        # This is a distinct copied map. Keep its lighting, sky and backdrop only.
        for actor in list(ACTORS.get_all_level_actors()):
            if isinstance(actor, (unreal.FactoryDemoWorld, unreal.FactoryBuilding, unreal.FactoryResourcePile,
                                  unreal.GrowEvolutionWorld, unreal.PlayerStart)):
                ACTORS.destroy_actor(actor)
            elif isinstance(actor, unreal.StaticMeshActor) and actor.get_actor_label() != "Piso_Exterior":
                ACTORS.destroy_actor(actor)
            elif actor.get_actor_label().startswith(("FactoryGuide_", "GrowPreview_")):
                ACTORS.destroy_actor(actor)
        editor_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        editor_world.get_world_settings().set_editor_property("default_game_mode", unreal.GrowEvolutionGameMode)
        director = spawn(unreal.GrowEvolutionWorld)
        director.set_actor_label("Grow_Evolution")
        director.set_editor_property("species", species)
        models = "/Game/FactoryCtyco/Factory/Models/VisualPolish/"
        director.set_editor_property("box_mesh", unreal.load_asset(models + "SM_FactoryBeveledBox"))
        director.set_editor_property("cylinder_mesh", unreal.load_asset(models + "SM_FactoryMachinedCylinder"))
        director.set_editor_property("belt_mesh", unreal.load_asset(models + "SM_FactoryBeltFrame"))
        director.set_editor_property("detail_material", unreal.load_asset("/Game/FactoryCtyco/Factory/Materials/M_FactoryDetail"))
        start = spawn(unreal.PlayerStart, unreal.Vector(0, 0, 40))
        start.set_actor_label("Grow_ViewStart")
        for actor in ACTORS.get_all_level_actors():
            if actor.get_actor_label() == "Piso_Exterior":
                actor.set_actor_location(unreal.Vector(0, 0, -162), False, True)
            elif isinstance(actor, unreal.DirectionalLight):
                actor.light_component.set_editor_property("intensity", 3.6 if actor.get_actor_label() != "Luz_Relleno" else .8)
            elif isinstance(actor, unreal.PostProcessVolume):
                settings = actor.get_editor_property("settings")
                settings.set_editor_property("override_vignette_intensity", True)
                settings.set_editor_property("vignette_intensity", .25)
                actor.set_editor_property("settings", settings)
        # Editor preview of the play-space; runtime geometry is animated by the director.
        preview = spawn(unreal.StaticMeshActor, unreal.Vector(0, 0, -60))
        preview.set_actor_label("GrowPreview_PlaySpace")
        preview.static_mesh_component.set_static_mesh(director.cylinder_mesh)
        preview.static_mesh_component.set_material(0, unreal.load_asset("/Game/FactoryCtyco/Factory/Materials/MI_FactoryGraphite"))
        preview.set_actor_scale3d(unreal.Vector(15.8, 15.8, 1))
        preview.set_actor_hidden_in_game(True)
        preview.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(-1500,1500,2400),unreal.Rotator(pitch=-49,yaw=-45))
        assert LEVELS.save_current_level()
        report.update(passed=True, species=species.get_path_name(), accessories=imported["assets"],
                      mode="/Script/FactoryCtycoRuntime.GrowEvolutionGameMode", decisions=6, professions=3,
                      scope="First playable: three robot professions, order-sensitive evolution, undo and reset.")
        return report
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error(report["error"])
        raise
    finally:
        (PROJECT / "Docs/grow_evolution_build.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    apply()
