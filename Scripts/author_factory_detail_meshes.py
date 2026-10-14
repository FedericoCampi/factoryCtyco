"""Author bevelled factory meshes in an isolated Blender scene.

Execute via Blender MCP with __file__ set to this script's absolute path, or:
    runpy.run_path(path, run_name="__main__")

Existing scenes, objects, materials and the active working file are preserved.
Only this script's new objects are joined. FBXs use the same metre-to-centimetre
pipeline as prepare_factory_models.py; verify the reported bounds after import.
"""
import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

import bpy


PROJECT = Path(__file__).resolve().parents[1]
DEST = PROJECT / "SourceAssets" / "Factory" / "VisualPolish"
ASSET_NAMES = (
    "SM_FactoryBeveledBox", "SM_FactoryMachinedCylinder", "SM_FactoryBeltFrame")
PALETTE = (
    ("M_FactoryGraphite", (.025, .038, .048, 1), .18, .62),
    ("M_FactorySteel", (.36, .44, .49, 1), .84, .28),
    ("M_FactorySafetyOrange", (.95, .245, .035, 1), .35, .34),
)


def _metres(values):
    return tuple(value / 100.0 for value in values)


def _activate(obj):
    # The active scene is newly created and contains no user objects.
    for selected in list(bpy.context.selected_objects):
        selected.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _materials():
    materials = []
    for name, color, metallic, roughness in PALETTE:
        material = bpy.data.materials.new(name)
        material.diffuse_color = color
        material.use_nodes = True
        shader = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
        shader.inputs["Base Color"].default_value = color
        shader.inputs["Metallic"].default_value = metallic
        shader.inputs["Roughness"].default_value = roughness
        material.metallic = metallic
        material.roughness = roughness
        materials.append(material)
    return materials


def _finish(obj, name, bevel_cm, materials, material_index=0, smooth=False):
    obj.name = name
    obj.data.name = name + "_Geometry"
    _activate(obj)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for material in materials:
        obj.data.materials.append(material)
    for face in obj.data.polygons:
        face.material_index = material_index
        if smooth is not None:
            face.use_smooth = smooth
    bevel = obj.modifiers.new("MachinedEdge_3Segments", "BEVEL")
    bevel.width = bevel_cm / 100.0
    bevel.segments = 3
    bevel.limit_method = "ANGLE"
    bevel.angle_limit = math.radians(30)
    bevel.harden_normals = True
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    # Blender 4.1+ no longer exposes use_auto_smooth; custom normals work without it.
    if hasattr(obj.data, "use_auto_smooth"):
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = math.pi
    weighted = obj.modifiers.new("WeightedMachinedNormals", "WEIGHTED_NORMAL")
    weighted.mode = "FACE_AREA"
    weighted.weight = 50
    weighted.keep_sharp = True
    bpy.ops.object.modifier_apply(modifier=weighted.name)
    obj.data.update()
    return obj


def _box(name, position_cm, dimensions_cm, bevel_cm, materials, material_index=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=_metres(position_cm))
    obj = bpy.context.object
    obj.dimensions = _metres(dimensions_cm)
    return _finish(obj, name, bevel_cm, materials, material_index, smooth=True)


def _cylinder(name, position_cm, radius_cm, length_cm, bevel_cm, materials,
              material_index=0, axis="Z", vertices=48):
    rotation = (math.pi / 2, 0, 0) if axis == "Y" else (0, 0, 0)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius_cm / 100, depth=length_cm / 100,
        end_fill_type="NGON", location=_metres(position_cm), rotation=rotation)
    obj = bpy.context.object
    # Large end caps stay flat, while the barrel and its bevels shade smoothly.
    for face in obj.data.polygons:
        face.use_smooth = abs(face.normal.z) < .5
    result = _finish(obj, name, bevel_cm, materials, material_index, smooth=None)
    return result


def _belt(materials):
    parts = []
    parts.append(_box("Belt_LowerChassis", (0, 0, 4), (192, 120, 8), 1.5, materials, 0))
    # The clear working surface ends at Z28, below the runtime slats at Z30.5.
    # The deck reaches the cell edge (X +-100), flush with the orange end fittings, and covers the end rollers:
    # no grey strip between the belt and its end, which a belt stretched in X made wide (01/10).
    parts.append(_box("Belt_RubberDeck", (0, 0, 23), (200, 116, 10), 1.2, materials, 0))
    for y in (-65, 65):
        parts.append(_box("Belt_SteelRail", (0, y, 21), (148, 10, 18), 1.4, materials, 1))
        for x in (-87, 87):
            # These meet the centre rail; no coplanar decorative overlay faces.
            parts.append(_box("Belt_OrangeEndFitting", (x, y, 21), (26, 10, 18), 1.5, materials, 2))
            parts.append(_box("Belt_OrangeFoot", (x, y, 6), (26, 10, 12), 1.4, materials, 2))
    for x in (-86, 86):
        parts.append(_cylinder("Belt_EndRoller", (x, 0, 17), 11, 116, .8,
                               materials, 1, axis="Y"))
    for x in (-74, 74):
        for y in (-53, 53):
            parts.append(_cylinder("Belt_DeckFastener", (x, y, 28.5), 2.1, 1, .18,
                                   materials, 1, vertices=12))
    _activate(parts[0])
    for part in parts:
        part.select_set(True)
    # Joining consumes exclusively the new parts created above.
    bpy.ops.object.join()
    result = bpy.context.object
    result.name = "SM_FactoryBeltFrame"
    result.data.name = "SM_FactoryBeltFrame_Geometry"
    return result


def _bounds_and_export(obj, asset_name, expected_dimensions, expected_min_z):
    obj.data.calc_loop_triangles()
    low = [min(vertex.co[axis] for vertex in obj.data.vertices) * 100 for axis in range(3)]
    high = [max(vertex.co[axis] for vertex in obj.data.vertices) * 100 for axis in range(3)]
    dimensions = [high[axis] - low[axis] for axis in range(3)]
    if any(abs(value - expected) > .02 for value, expected in zip(dimensions, expected_dimensions)):
        raise RuntimeError(asset_name + " dimensions do not match: " + str(dimensions))
    if abs(low[2] - expected_min_z) > .02:
        raise RuntimeError(asset_name + " has the wrong vertical origin: " + str(low))
    if abs(low[0] + high[0]) > .02 or abs(low[1] + high[1]) > .02:
        raise RuntimeError(asset_name + " must be centred on X/Y")
    _activate(obj)
    destination = DEST / (asset_name + ".fbx")
    bpy.ops.export_scene.fbx(
        filepath=str(destination), use_selection=True, object_types={"MESH"},
        axis_forward="-Y", axis_up="Z", apply_unit_scale=True,
        global_scale=1.0, apply_scale_options="FBX_SCALE_NONE",
        bake_space_transform=False, mesh_smooth_type="FACE",
        use_mesh_modifiers=True, add_leaf_bones=False, bake_anim=False,
        path_mode="AUTO", use_custom_props=False)
    if not destination.is_file() or destination.stat().st_size < 1024:
        raise RuntimeError("FBX export was not written: " + str(destination))
    return {
        "id": asset_name, "object": obj.name, "fbx": destination.name,
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "dimensions_cm": dimensions, "min_cm": low, "max_cm": high,
        "triangles": len(obj.data.loop_triangles),
        "materials": [material.name for material in obj.data.materials],
        "material_slots": [
            {"slot": index, "material": material.name,
             "base_color": list(material.diffuse_color),
             "metallic": material.metallic, "roughness": material.roughness}
            for index, material in enumerate(obj.data.materials)],
    }


def _backup_generated_files():
    names = [name + ".fbx" for name in ASSET_NAMES] + ["FactoryDetails.blend", "manifest.json"]
    existing = [DEST / name for name in names if (DEST / name).is_file()]
    if not existing:
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ")
    folder = PROJECT / "Saved" / "VisualPolishWork" / ("BlenderSource-" + stamp)
    folder.mkdir(parents=True, exist_ok=False)
    for path in existing:
        shutil.copy2(path, folder / path.name)
    return str(folder)


def author():
    destination = DEST / "FactoryDetails.blend"
    if bpy.data.filepath and Path(bpy.data.filepath).resolve() == destination.resolve():
        raise RuntimeError("FactoryDetails.blend is the active working file; use a separate Blender session")
    if bpy.context.window is None:
        raise RuntimeError("Run in the Blender MCP editor window so its original scene can be restored")
    if bpy.context.mode != "OBJECT":
        raise RuntimeError("Leave Edit/Sculpt mode before authoring; the script preserves the user's mode")
    DEST.mkdir(parents=True, exist_ok=True)
    backup = _backup_generated_files()
    window = bpy.context.window
    previous_scene = window.scene
    previous_filepath = bpy.data.filepath
    existing_scene_names = set(bpy.data.scenes.keys())
    scene = bpy.data.scenes.new("FactoryVisualPolish")
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "CENTIMETERS"
    report = {"passed": False, "blender_version": bpy.app.version_string,
              "scene": scene.name, "backup": backup, "assets": [],
              "fbx_axis_forward": "-Y", "fbx_axis_up": "Z",
              "authoring_units": "metres; Unreal FBX import converts to centimetres",
              "blend": str(destination), "source_assets_preserved": True}
    try:
        window.scene = scene
        materials = _materials()
        box = _box(ASSET_NAMES[0], (0, 0, 0), (100, 100, 100), 2.5, [materials[1]])
        cylinder = _cylinder(ASSET_NAMES[1], (0, 0, 0), 50, 100, 2, [materials[1]])
        belt = _belt(materials)
        for obj, name, dimensions, bottom in (
                (box, ASSET_NAMES[0], (100, 100, 100), -50),
                (cylinder, ASSET_NAMES[1], (100, 100, 100), -50),
                (belt, ASSET_NAMES[2], (200, 140, 30), 0)):
            report["assets"].append(_bounds_and_export(obj, name, dimensions, bottom))
        # The .blend opens with the belt ready to inspect; primitive library
        # meshes retain centred local coordinates and can be unhidden separately.
        box.hide_set(True)
        cylinder.hide_set(True)
        box.hide_render = True
        cylinder.hide_render = True
        _activate(belt)
        scene["FactoryVisualPolish_Source"] = "Scripts/author_factory_detail_meshes.py"
        scene["FactoryVisualPolish_Units"] = "Metres; FBX imported into Unreal as centimetres"
        # Write only this scene and dependencies; do not save/rename the user's
        # active working file or include any preexisting scenes in the artifact.
        bpy.data.libraries.write(str(destination), {scene}, fake_user=True)
        if bpy.data.filepath != previous_filepath:
            raise RuntimeError("The original Blender working filename changed")
        if not existing_scene_names.issubset(set(bpy.data.scenes.keys())):
            raise RuntimeError("A preexisting Blender scene was removed")
        report["passed"] = True
        return report
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        window.scene = previous_scene
        (DEST / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("[FACTORY_DETAIL_AUTHORING] " + json.dumps(report), flush=True)


if __name__ == "__main__":
    author()
