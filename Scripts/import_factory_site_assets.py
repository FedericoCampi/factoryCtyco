"""Import decorative workshop and charge-station milestones; keep Unreal open.

Only the two SiteProgress meshes and MI_FactorySiteCyan are saved. Existing
Graphite/Steel/SafetyOrange instances are reused without editing. No map, data
definition, HUD or gameplay state is changed. Workshop receives one simple box
collision; the walk-on charge station receives no collision.
"""
import hashlib
import json
import runpy
import traceback
from pathlib import Path

import unreal


PROJECT = Path(unreal.Paths.project_dir()).resolve()
SOURCE = PROJECT / "SourceAssets" / "Factory" / "SiteProgress"
DEST = "/Game/FactoryCtyco/Factory/Models/SiteProgress"
MATERIALS = "/Game/FactoryCtyco/Factory/Materials"
PARENT = MATERIALS + "/M_FactoryDetail"
CYAN = MATERIALS + "/MI_FactorySiteCyan"
EXPECTED = {"SM_FactoryWorkshop": (300, 180, 220), "SM_FactoryChargeStation": (240, 240, 150)}
SLOT_KEYS = ("Graphite", "Steel", "SafetyOrange", "SiteCyan")
LIB = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
ML = unreal.MaterialEditingLibrary


def save(asset):
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError("Cannot save " + asset.get_path_name())


def cyan_material(parent, values):
    material = unreal.load_asset(CYAN) if LIB.does_asset_exist(CYAN) else TOOLS.create_asset(
        "MI_FactorySiteCyan", MATERIALS, unreal.MaterialInstanceConstant,
        unreal.MaterialInstanceConstantFactoryNew())
    if not isinstance(material, unreal.MaterialInstanceConstant):
        raise RuntimeError("Expected material instance at " + CYAN)
    material.modify()
    ML.set_material_instance_parent(material, parent)
    for name, key in (("BaseColor", "base_color"), ("Emission", "emission")):
        value = values[key]
        # UE5.6 setters can return false after succeeding; verify the result.
        ML.set_material_instance_vector_parameter_value(material, name, unreal.LinearColor(*value))
        actual = ML.get_material_instance_vector_parameter_value(material, name)
        if any(abs(a - b) > .0001 for a, b in zip((actual.r, actual.g, actual.b, actual.a), value)):
            raise RuntimeError("Material vector did not persist: " + name)
    for name, key in (("Metallic", "metallic"), ("Roughness", "roughness")):
        ML.set_material_instance_scalar_parameter_value(material, name, values[key])
        if abs(ML.get_material_instance_scalar_parameter_value(material, name) - values[key]) > .0001:
            raise RuntimeError("Material scalar did not persist: " + name)
    ML.update_material_instance(material)
    save(material)
    return material


def import_mesh(name, yaw=0):
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
    data.import_uniform_scale = 1
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
    TOOLS.import_asset_tasks([task])
    mesh = unreal.load_asset(DEST + "/" + name)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("Mesh import failed: " + name)
    return mesh


def bounds(mesh):
    value = mesh.get_bounding_box()
    dimensions = value.max - value.min
    return {"dimensions_cm": [dimensions.x, dimensions.y, dimensions.z],
            "min_cm": [value.min.x, value.min.y, value.min.z],
            "max_cm": [value.max.x, value.max.y, value.max.z]}


def near(actual, expected):
    return len(actual) == len(expected) and all(abs(a - b) < .06 for a, b in zip(actual, expected))


def apply():
    report = {"passed": False, "assets": [], "materials": {}}
    try:
        if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError("Stop Play in Editor before importing milestone assets")
        manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
        if not manifest.get("passed"):
            raise RuntimeError("Blender authoring did not finish successfully")
        entries = {entry["id"]: entry for entry in manifest["assets"]}
        for name, dimensions in EXPECTED.items():
            entry = entries[name]
            path = SOURCE / (name + ".fbx")
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                raise RuntimeError("FBX source is missing or differs from the Blender manifest: " + name)
            if not near(entry["dimensions_cm"], dimensions):
                raise RuntimeError("Source dimensions differ from the milestone contract")
            if tuple(slot["key"] for slot in entry["material_slots"]) != SLOT_KEYS:
                raise RuntimeError("Source requires four consistent material slots")
        parent = unreal.load_asset(PARENT)
        if not isinstance(parent, unreal.Material):
            raise RuntimeError("Required factory parent material is missing")
        materials = {key: unreal.load_asset(MATERIALS + "/MI_Factory" + key) for key in SLOT_KEYS[:3]}
        for key, material in materials.items():
            if not isinstance(material, unreal.MaterialInstanceConstant):
                raise RuntimeError("Required existing factory surface is missing: " + key)
        # Backup only packages this importer may write. Shared original materials
        # are deliberately excluded because they are never modified or saved.
        helpers = runpy.run_path(str(PROJECT / "Scripts" / "polish_factory_visuals.py"),
                                 run_name="factory_site_backup_helpers")
        report["backup"] = str(helpers["_backup"]([DEST + "/" + name for name in EXPECTED] + [CYAN]))
        LIB.make_directory(DEST)
        cyan_values = entries["SM_FactoryWorkshop"]["material_slots"][3]
        materials["SiteCyan"] = cyan_material(parent, cyan_values)
        report["materials"] = {key: material.get_path_name() for key, material in materials.items()}
        collision = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        shared_yaw = None
        for name, dimensions in EXPECTED.items():
            # Import the asymmetric workshop first to establish the shared FBX
            # axis convention. The square pad cannot reveal an X/Y swap through
            # bounds, so it must inherit the workshop correction to face -Y too.
            yaw = 0 if shared_yaw is None else shared_yaw
            mesh = import_mesh(name, yaw)
            value = bounds(mesh)
            if shared_yaw is None and not near(value["dimensions_cm"], dimensions) and near(
                    value["dimensions_cm"], (dimensions[1], dimensions[0], dimensions[2])):
                yaw = 90
                mesh = import_mesh(name, yaw)
                value = bounds(mesh)
            if any(not near(value[key], entries[name][key]) for key in ("dimensions_cm", "min_cm", "max_cm")):
                raise RuntimeError("Imported axis, dimensions or floor pivot differ: " + str(value))
            shared_yaw = yaw
            slots = list(mesh.static_materials)
            if len(slots) != 4:
                raise RuntimeError("Milestone mesh must retain four material slots")
            mesh.modify()
            for index, key in enumerate(SLOT_KEYS):
                slot_name = str(slots[index].get_editor_property("material_slot_name"))
                if not slot_name.startswith("M_Factory" + key):
                    raise RuntimeError("Unexpected imported material order: " + slot_name)
                mesh.set_material(index, materials[key])
            collision.remove_collisions(mesh)
            expected_collision = 1 if name == "SM_FactoryWorkshop" else 0
            if expected_collision:
                collision.add_simple_collisions(mesh, unreal.ScriptingCollisionShapeType.BOX)
            count = collision.get_simple_collision_count(mesh)
            if count != expected_collision:
                raise RuntimeError("Unexpected collision count: " + str(count))
            save(mesh)
            report["assets"].append({"path": mesh.get_path_name(), "import_yaw": yaw,
                "triangles": mesh.get_num_triangles(0), "simple_collision_count": count,
                "collision": "BOX" if expected_collision else "none", "front": "-Y", "rear": "+Y",
                "material_slots": [{"slot": i, "key": key, "material": materials[key].get_path_name()}
                                   for i, key in enumerate(SLOT_KEYS)], **value})
        report["contract"] = manifest["contract"]
        report["shared_import_yaw"] = shared_yaw
        report["passed"] = True
        return report
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error(report["error"])
        raise
    finally:
        (PROJECT / "Docs" / "factory_site_asset_import.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8")
        unreal.log("[FACTORY_SITE_ASSET_IMPORT] " + json.dumps(report))


if __name__ == "__main__":
    apply()
