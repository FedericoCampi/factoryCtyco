"""Import authored GROW profession backpacks; never close the editor.

Only /Game/FactoryCtyco/Grow packages are written. The existing Factory detail
material is a read-only parent. No map, robot blueprint or factory definition
is changed: the caller attaches returned meshes according to the manifest.
"""
import hashlib
import json
import runpy
import traceback
from pathlib import Path

import unreal


PROJECT = Path(unreal.Paths.project_dir()).resolve()
SOURCE = PROJECT / "SourceAssets" / "GrowRobots"
MODELS = "/Game/FactoryCtyco/Grow/Models"
MATERIALS = "/Game/FactoryCtyco/Grow/Materials"
PARENT = "/Game/FactoryCtyco/Factory/Materials/M_FactoryDetail"
ROLES = ("Builder", "Caretaker", "Courier")
LIB = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
ML = unreal.MaterialEditingLibrary


def save(asset):
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError("Cannot save " + asset.get_path_name())


def instance(name, values, parent):
    asset_name = "MI_Grow" + name
    path = MATERIALS + "/" + asset_name
    material = unreal.load_asset(path) if LIB.does_asset_exist(path) else TOOLS.create_asset(
        asset_name, MATERIALS, unreal.MaterialInstanceConstant,
        unreal.MaterialInstanceConstantFactoryNew())
    if not isinstance(material, unreal.MaterialInstanceConstant):
        raise RuntimeError("Expected material instance: " + path)
    material.modify()
    ML.set_material_instance_parent(material, parent)
    for parameter, key in (("BaseColor", "base_color"), ("Emission", "emission")):
        expected = values[key]
        # UE5.6 setter return values can be false despite success. Verify values.
        ML.set_material_instance_vector_parameter_value(material, parameter, unreal.LinearColor(*expected))
        actual = ML.get_material_instance_vector_parameter_value(material, parameter)
        if any(abs(a - b) > .0001 for a, b in zip((actual.r, actual.g, actual.b, actual.a), expected)):
            raise RuntimeError("Vector material parameter did not persist: " + parameter)
    for parameter, key in (("Metallic", "metallic"), ("Roughness", "roughness")):
        ML.set_material_instance_scalar_parameter_value(material, parameter, values[key])
        if abs(ML.get_material_instance_scalar_parameter_value(material, parameter) - values[key]) > .0001:
            raise RuntimeError("Scalar material parameter did not persist: " + parameter)
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
    data.import_uniform_scale = 1.0
    data.import_rotation = unreal.Rotator(pitch=0, yaw=yaw, roll=0)
    data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task = unreal.AssetImportTask()
    task.filename = str(SOURCE / (name + ".fbx"))
    task.destination_path = MODELS
    task.destination_name = name
    task.automated = True
    task.save = False
    task.replace_existing = True
    task.replace_existing_settings = True
    task.factory = unreal.FbxFactory()
    task.options = options
    TOOLS.import_asset_tasks([task])
    mesh = unreal.load_asset(MODELS + "/" + name)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("Failed to import " + name)
    return mesh


def near(actual, expected):
    return len(actual) == len(expected) and all(abs(a - b) < .06 for a, b in zip(actual, expected))


def bounds(mesh):
    value = mesh.get_bounding_box()
    size = value.max - value.min
    return {"dimensions_cm": [size.x, size.y, size.z],
            "min_cm": [value.min.x, value.min.y, value.min.z],
            "max_cm": [value.max.x, value.max.y, value.max.z]}


def apply():
    report = {"passed": False, "assets": [], "materials": []}
    try:
        if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError("Stop Play in Editor before importing robot accessories")
        manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
        if not manifest.get("passed"):
            raise RuntimeError("The Blender authoring manifest did not pass")
        entries = {entry["role"]: entry for entry in manifest["assets"]}
        configs = {}
        for role in ROLES:
            entry = entries[role]
            name = "SM_Grow" + role + "Pack"
            if entry["id"] != name:
                raise RuntimeError("Unexpected source mesh id")
            source = SOURCE / (name + ".fbx")
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != entry["sha256"]:
                raise RuntimeError("Source FBX is missing or has changed: " + name)
            if len(entry["material_slots"]) != 3:
                raise RuntimeError("The backpack must expose three material slots")
            for index, key in enumerate(("Graphite", role + "Role", role + "Emission")):
                values = entry["material_slots"][index]
                if not values["material"].startswith("M_Grow" + key):
                    raise RuntimeError("Unexpected source material order")
                configs.setdefault(key, values)
        parent = unreal.load_asset(PARENT)
        if not isinstance(parent, unreal.Material):
            raise RuntimeError("Required factory parent material is missing: " + PARENT)
        helpers = runpy.run_path(str(PROJECT / "Scripts" / "polish_factory_visuals.py"),
                                 run_name="grow_backup_helpers")
        touched = [MODELS + "/SM_Grow" + role + "Pack" for role in ROLES]
        touched += [MATERIALS + "/MI_Grow" + key for key in configs]
        report["backup"] = str(helpers["_backup"](touched))
        LIB.make_directory(MODELS)
        LIB.make_directory(MATERIALS)
        materials = {key: instance(key, values, parent) for key, values in configs.items()}
        report["materials"] = [material.get_path_name() for material in materials.values()]
        for role in ROLES:
            entry = entries[role]
            mesh = import_mesh(entry["id"])
            value = bounds(mesh)
            expected = entry["dimensions_cm"]
            yaw = 0
            if not near(value["dimensions_cm"], expected) and near(
                    value["dimensions_cm"], (expected[1], expected[0], expected[2])):
                yaw = 90
                mesh = import_mesh(entry["id"], yaw)
                value = bounds(mesh)
            if any(not near(value[key], entry[key]) for key in ("dimensions_cm", "min_cm", "max_cm")):
                raise RuntimeError("Unexpected imported axis, scale or pivot: " + str(value))
            slots = list(mesh.static_materials)
            if len(slots) != 3:
                raise RuntimeError("Imported backpack must have three material slots")
            mesh.modify()
            assigned = []
            for index, key in enumerate(("Graphite", role + "Role", role + "Emission")):
                slot_name = str(slots[index].get_editor_property("material_slot_name"))
                if not slot_name.startswith("M_Grow" + key):
                    raise RuntimeError("Imported material order differs: " + slot_name)
                mesh.set_material(index, materials[key])
                assigned.append({"slot": index, "material": materials[key].get_path_name()})
            unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).remove_collisions(mesh)
            save(mesh)
            report["assets"].append({"role": role, "mesh": mesh.get_path_name(),
                "decision": entry["decision"], "import_yaw": yaw,
                "triangles": mesh.get_num_triangles(0), "material_slots": assigned, **value})
        report["visual_contract"] = manifest["visual_contract"]
        report["passed"] = True
        return report
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error(report["error"])
        raise
    finally:
        (PROJECT / "Docs" / "grow_robot_accessory_import.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8")
        unreal.log("[GROW_ACCESSORY_IMPORT] " + json.dumps(report))


if __name__ == "__main__":
    apply()
