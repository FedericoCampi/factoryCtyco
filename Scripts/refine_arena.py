"""Set explicit rotation axes and preserve source PBR material factors."""
import json
import re
import struct
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
library = unreal.EditorAssetLibrary
bp = unreal.load_asset("/Game/FactoryCtyco/Blueprints/BP_Robot1")
subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
    data = subsystem.k2_find_subobject_data_from_handle(handle)
    obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object_for_blueprint(data, bp)
    if isinstance(obj, unreal.StaticMeshComponent) and "RobotVisual" in obj.get_name():
        obj.modify()
        obj.set_editor_property("relative_rotation", unreal.Rotator(yaw=-90))
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
assert library.save_loaded_asset(bp, False)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert levels.load_level("/Game/FactoryCtyco/Maps/L_Recoleccion")
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if isinstance(actor, unreal.PlayerStart):
        actor.set_actor_rotation(unreal.Rotator(pitch=-10, yaw=-90), False)
    if isinstance(actor, unreal.DirectionalLight):
        actor.set_actor_rotation(unreal.Rotator(pitch=-50, yaw=-30), False)
assert levels.save_current_level()

source = (project / "SourceAssets/SceneRobot/scene.glb").read_bytes()
size = struct.unpack_from("<I", source, 12)[0]
document = json.loads(source[20:20 + size])
matlib = unreal.MaterialEditingLibrary
updated = []
for item in document.get("materials", []):
    name = re.sub(r"[^A-Za-z0-9_]", "_", item["name"])
    material = unreal.load_asset("/Game/FactoryCtyco/Environments/SceneRobot/" + name)
    if not isinstance(material, unreal.Material):
        raise RuntimeError(f"Missing source material: {name}")
    material.modify()
    pbr = item.get("pbrMetallicRoughness", {})
    for index, (key, prop, default) in enumerate([
        ("metallicFactor", unreal.MaterialProperty.MP_METALLIC, 1.0),
        ("roughnessFactor", unreal.MaterialProperty.MP_ROUGHNESS, 1.0),
    ]):
        node = matlib.create_material_expression(material, unreal.MaterialExpressionConstant, -200, 250 + index * 100)
        node.set_editor_property("r", pbr.get(key, default))
        assert matlib.connect_material_property(node, "", prop)
    material.set_editor_property("two_sided", item.get("doubleSided", False))
    matlib.recompile_material(material)
    assert library.save_loaded_asset(material, False)
    updated.append(name)
(project / "Docs/materials.json").write_text(json.dumps({"passed": True, "source_pbr_factors_preserved": updated}, indent=2), encoding="utf-8")
unreal.log("[ARENA_REFINED] Orientation corrected; source metallic and roughness restored")
