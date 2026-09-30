"""Load the project's real assets and defaults inside Unreal Editor."""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
report = {"engine": unreal.SystemLibrary.get_engine_version(), "checks": [], "passed": False}
try:
    paths = [
        "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter",
        "/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode",
        "/Game/ThirdPerson/Blueprints/BP_ThirdPersonPlayerController",
        "/Game/Input/IMC_Default",
        "/Game/Input/IMC_MouseLook",
        "/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple",
        "/Game/ThirdPerson/Lvl_ThirdPerson",
    ]
    for path in paths:
        asset = unreal.load_asset(path)
        if asset is None:
            raise RuntimeError(f"Asset could not be loaded: {path}")
        report["checks"].append({"asset": path, "loaded": True})
    character = unreal.EditorAssetLibrary.load_blueprint_class(paths[0])
    mode = unreal.EditorAssetLibrary.load_blueprint_class(paths[1])
    controller = unreal.EditorAssetLibrary.load_blueprint_class(paths[2])
    if not all((character, mode, controller)):
        raise RuntimeError("A gameplay Blueprint has no generated class")
    pawn = unreal.get_default_object(character)
    game_mode = unreal.get_default_object(mode)
    mesh = pawn.get_component_by_class(unreal.SkeletalMeshComponent)
    camera = pawn.get_component_by_class(unreal.CameraComponent)
    capsule = pawn.get_component_by_class(unreal.CapsuleComponent)
    if not all((mesh, camera, capsule)):
        raise RuntimeError("Character mesh, camera or collision capsule is missing")
    if mesh.get_editor_property("skeletal_mesh_asset") is None:
        raise RuntimeError("The playable character has no skeletal mesh")
    if mesh.get_editor_property("anim_class") is None:
        raise RuntimeError("The playable character has no animation Blueprint")
    if game_mode.get_editor_property("default_pawn_class") != character:
        raise RuntimeError("GameMode is not configured to spawn the Third Person character")
    report["gameplay"] = {
        "character": character.get_path_name(),
        "game_mode": mode.get_path_name(),
        "mesh": mesh.get_editor_property("skeletal_mesh_asset").get_path_name(),
        "animation": mesh.get_editor_property("anim_class").get_path_name(),
        "camera": True, "collision_capsule": True,
    }
    report["passed"] = True
    report["scope"] = "Unreal asset loading and gameplay defaults; interactive Play has not been tested."
except Exception as exc:
    report["error"] = str(exc)
    raise
finally:
    destination = project / "Docs/validation.json"
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    unreal.log("[ARENA_VALIDATION] " + json.dumps(report))
