"""Import the Blender-authored factory details without closing Unreal Editor.

Call apply() or run with the native Unreal MCP execute-python command. Only
generated detail meshes, their material instances and DB_* visual references
are saved. Existing level actors, source models and gameplay values remain.
"""
import hashlib
import json
import runpy
import traceback
from pathlib import Path

import unreal


PROJECT = Path(unreal.Paths.project_dir()).resolve()
SOURCE = PROJECT / "SourceAssets" / "Factory" / "VisualPolish"
ROOT = "/Game/FactoryCtyco/Factory"
DEST = ROOT + "/Models/VisualPolish"
MATERIAL_FOLDER = ROOT + "/Materials"
PARENT = MATERIAL_FOLDER + "/M_FactoryDetail"
DEFINITIONS = [ROOT + "/Definitions/DB_" + name
               for name in ("Crusher", "Smelter", "Storage", "Belt")]
MESHES = {
    "SM_FactoryBeveledBox": ((100, 100, 100), -50),
    "SM_FactoryMachinedCylinder": ((100, 100, 100), -50),
    "SM_FactoryBeltFrame": ((200, 140, 30), 0),
}
SURFACES = {
    "Graphite": ((.025, .038, .048, 1), .18, .62),
    "Steel": ((.36, .44, .49, 1), .84, .28),
    "SafetyOrange": ((.95, .245, .035, 1), .35, .34),
}
LIB = unreal.EditorAssetLibrary
ASSETS = unreal.AssetToolsHelpers.get_asset_tools()
ML = unreal.MaterialEditingLibrary


def _save(asset):
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError("Cannot save " + asset.get_path_name())


def _instance(name, color, metallic, roughness, parent):
    asset_name = "MI_Factory" + name
    path = MATERIAL_FOLDER + "/" + asset_name
    instance = unreal.load_asset(path) if LIB.does_asset_exist(path) else ASSETS.create_asset(
        asset_name, MATERIAL_FOLDER, unreal.MaterialInstanceConstant,
        unreal.MaterialInstanceConstantFactoryNew())
    if not isinstance(instance, unreal.MaterialInstanceConstant):
        raise RuntimeError("Expected MaterialInstanceConstant: " + path)
    instance.modify()
    ML.set_material_instance_parent(instance, parent)
    for parameter, value in (("BaseColor", color), ("Emission", (0, 0, 0, 1))):
        # UE 5.6's setter applies the value but always returns false. Read back.
        ML.set_material_instance_vector_parameter_value(instance, parameter, unreal.LinearColor(*value))
        actual = ML.get_material_instance_vector_parameter_value(instance, parameter)
        if any(abs(a - b) > .0001 for a, b in zip((actual.r, actual.g, actual.b, actual.a), value)):
            raise RuntimeError("Vector parameter did not persist: " + parameter)
    for parameter, value in (("Metallic", metallic), ("Roughness", roughness)):
        ML.set_material_instance_scalar_parameter_value(instance, parameter, value)
        if abs(ML.get_material_instance_scalar_parameter_value(instance, parameter) - value) > .0001:
            raise RuntimeError("Scalar parameter did not persist: " + parameter)
    ML.update_material_instance(instance)
    _save(instance)
    return instance


def _import(name, yaw=0):
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = False
    options.import_textures = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.convert_scene = True
    data.convert_scene_unit = True
    data.generate_lightmap_u_vs = False
    data.build_nanite = False
    data.import_uniform_scale = 1.0
    data.import_rotation = unreal.Rotator(pitch=0, yaw=yaw, roll=0)
    data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task = unreal.AssetImportTask()
    task.filename = str(SOURCE / (name + ".fbx"))
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.save = False
    task.replace_existing = True
    task.replace_existing_settings = True
    task.factory = unreal.FbxFactory()
    task.options = options
    ASSETS.import_asset_tasks([task])
    mesh = unreal.load_asset(DEST + "/" + name)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("Mesh import failed: " + name)
    return mesh


def _bounds(mesh):
    bounds = mesh.get_bounding_box()
    dimensions = bounds.max - bounds.min
    return {
        "dimensions_cm": [dimensions.x, dimensions.y, dimensions.z],
        "min_cm": [bounds.min.x, bounds.min.y, bounds.min.z],
        "max_cm": [bounds.max.x, bounds.max.y, bounds.max.z],
    }


def _near(actual, expected, tolerance=.05):
    return all(abs(a - b) <= tolerance for a, b in zip(actual, expected))


def _import_and_finish(name, expected, bottom, instances):
    mesh = _import(name)
    bounds = _bounds(mesh)
    yaw = 0
    # Blender's existing -Y forward FBX convention can arrive with X/Y swapped.
    # Resolve it once through import settings, keeping runtime MeshYaw at zero.
    if name == "SM_FactoryBeltFrame" and _near(bounds["dimensions_cm"], (140, 200, 30)):
        yaw = 90
        mesh = _import(name, yaw=yaw)
        bounds = _bounds(mesh)
    if not _near(bounds["dimensions_cm"], expected):
        raise RuntimeError(name + " unexpected import dimensions: " + str(bounds))
    if abs(bounds["min_cm"][2] - bottom) > .05:
        raise RuntimeError(name + " unexpected vertical origin: " + str(bounds))
    if not _near([bounds["min_cm"][i] + bounds["max_cm"][i] for i in (0, 1)], (0, 0)):
        raise RuntimeError(name + " is not centred on X/Y")
    mesh.modify()
    slots = list(mesh.static_materials)
    expected_slots = 3 if name == "SM_FactoryBeltFrame" else 1
    if len(slots) != expected_slots:
        raise RuntimeError(name + " expected " + str(expected_slots) + " material slots, got " + str(len(slots)))
    material_report = []
    for index, slot in enumerate(slots):
        slot_name = str(slot.get_editor_property("material_slot_name"))
        matches = [key for key in SURFACES if key.lower() in slot_name.lower()]
        if len(matches) != 1:
            raise RuntimeError("Unrecognised material slot: " + slot_name)
        key = matches[0]
        mesh.set_material(index, instances[key])
        material_report.append({"slot": index, "name": slot_name, "material": instances[key].get_path_name()})
    # Decoration uses no collision; the existing building collision component
    # still handles placement and gameplay, including the new belt's footprint.
    unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).remove_collisions(mesh)
    _save(mesh)
    return mesh, {"path": mesh.get_path_name(), "import_yaw": yaw,
                  "triangles": mesh.get_num_triangles(0), "materials": material_report, **bounds}


def apply():
    report = {"passed": False, "assets": [], "definitions": []}
    try:
        if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError("Stop Play in Editor before importing the detail meshes")
        manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
        if not manifest.get("passed"):
            raise RuntimeError("Blender authoring did not finish successfully")
        entries = {entry["id"]: entry for entry in manifest["assets"]}
        for name in MESHES:
            source = SOURCE / (name + ".fbx")
            if name not in entries or not source.is_file():
                raise RuntimeError("Missing authored source: " + name)
            if hashlib.sha256(source.read_bytes()).hexdigest() != entries[name]["sha256"]:
                raise RuntimeError("Source differs from the validated Blender manifest: " + name)
        parent = unreal.load_asset(PARENT)
        if not isinstance(parent, unreal.Material):
            raise RuntimeError("Run polish_factory_visuals.py first to create " + PARENT)
        definitions = [unreal.load_asset(path) for path in DEFINITIONS]
        for definition in definitions:
            if definition is None:
                raise RuntimeError("Required building definition is missing")
            for field in ("detail_box_mesh", "detail_cylinder_mesh"):
                definition.get_editor_property(field)
        # Reuse the already verified package checkpoint helper without invoking
        # its material/lighting pass or its __main__ editor shutdown.
        helpers = runpy.run_path(str(PROJECT / "Scripts" / "polish_factory_visuals.py"),
                                 run_name="factory_visual_backup_helpers")
        touched = DEFINITIONS + [DEST + "/" + name for name in MESHES]
        touched += [MATERIAL_FOLDER + "/MI_Factory" + name for name in SURFACES]
        report["backup"] = str(helpers["_backup"](touched))
        LIB.make_directory(DEST)
        instances = {name: _instance(name, *values, parent) for name, values in SURFACES.items()}
        meshes = {}
        for name, (dimensions, bottom) in MESHES.items():
            meshes[name], result = _import_and_finish(name, dimensions, bottom, instances)
            report["assets"].append(result)
        for definition in definitions:
            definition.modify()
            definition.set_editor_property("detail_box_mesh", meshes["SM_FactoryBeveledBox"])
            definition.set_editor_property("detail_cylinder_mesh", meshes["SM_FactoryMachinedCylinder"])
            if str(definition.get_editor_property("building_id")) == "Belt":
                definition.set_editor_property("mesh", meshes["SM_FactoryBeltFrame"])
                definition.set_editor_property("mesh_scale", unreal.Vector(1, 1, 1))
                definition.set_editor_property("mesh_offset", unreal.Vector(0, 0, 0))
                definition.set_editor_property("mesh_yaw", 0.0)
            _save(definition)
            report["definitions"].append(definition.get_path_name())
        report["passed"] = True
        return report
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error(report["error"])
        raise
    finally:
        (PROJECT / "Docs" / "factory_detail_import.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8")
        unreal.log("[FACTORY_DETAIL_IMPORT] " + json.dumps(report))


if __name__ == "__main__":
    apply()
