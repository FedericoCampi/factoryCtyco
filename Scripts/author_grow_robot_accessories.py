"""Author three profession backpacks through the real local Blender MCP.

Uses the verified bevel helpers without running their factory authoring pass.
All new meshes live in an isolated scene. Existing scenes and working file stay
unchanged. FBX local axes: +X robot front; the visible backpack face points -X.
"""
import hashlib
import json
import math
import runpy
import shutil
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


PROJECT = Path(__file__).resolve().parents[1]
DEST = PROJECT / "SourceAssets" / "GrowRobots"
HELPERS = runpy.run_path(str(PROJECT / "Scripts" / "author_factory_detail_meshes.py"),
                         run_name="grow_bevel_helpers")
box = HELPERS["_box"]
cylinder = HELPERS["_cylinder"]
activate = HELPERS["_activate"]
ROLES = {
    "Builder": {"color": (.95, .26, .045, 1), "decision": "recycling", "label": "CONSTRUCTOR"},
    "Caretaker": {"color": (.12, .62, .25, 1), "decision": "water", "label": "CUIDADOR"},
    "Courier": {"color": (.025, .30, .78, 1), "decision": "transport", "label": "TRANSPORTISTA"},
}


def make_material(name, color, metallic, roughness, emission=(0, 0, 0, 1)):
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.metallic = metallic
    material.roughness = roughness
    material.use_nodes = True
    shader = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Emission Color"].default_value = emission
    shader.inputs["Emission Strength"].default_value = 1.0
    material["GrowEmission"] = list(emission)
    return material


def join_parts(parts, name):
    activate(parts[0])
    for part in parts:
        part.select_set(True)
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name + "_Geometry"
    lo = Vector(tuple(min(vertex.co[i] for vertex in obj.data.vertices) for i in range(3)))
    hi = Vector(tuple(max(vertex.co[i] for vertex in obj.data.vertices) for i in range(3)))
    middle = (lo + hi) * .5
    for vertex in obj.data.vertices:
        vertex.co -= middle
    obj.data.update()
    return obj


def builder(materials):
    parts = [box("Builder_Harness", (11, 0, -3), (8, 43, 54), 2, materials, 0),
             box("Builder_Toolbox", (-2, 0, -7), (22, 42, 43), 3, materials, 1),
             box("Builder_DorsalPanel", (-14, 0, -7), (2, 32, 23), .6, materials, 0),
             box("Builder_Light", (-15.2, 0, 3), (1, 22, 2.5), .3, materials, 2)]
    for y in (-15, 15):
        parts.append(box("Builder_LowerGuard", (-1, y, -30.5), (25, 9, 4), 1, materials, 0))
    parts.append(cylinder("Builder_WrenchShaft", (-4, -22, 4), 2.5, 46, .55, materials, 0, vertices=20))
    parts.append(box("Builder_WrenchHead", (-4, -22, 25.5), (7, 11, 6), .7, materials, 1))
    for y in (-25.5, -18.5):
        parts.append(box("Builder_WrenchJaw", (-4, y, 30), (7, 4, 6), .65, materials, 1))
    parts.append(cylinder("Builder_HammerHandle", (-5, 18, 10), 2, 36, .45, materials, 0, vertices=20))
    parts.append(box("Builder_HammerHead", (-5, 18, 28), (10, 17, 9), 1.3, materials, 1))
    for z in (-17, -10, -3):
        parts.append(box("Builder_PanelGroove", (-15.25, 0, z), (.6, 22, 1), .2, materials, 1))
    return join_parts(parts, "SM_GrowBuilderPack")


def leaf(position, rotation, materials):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1,
                                       location=tuple(value / 100 for value in position))
    obj = bpy.context.object
    obj.name = "Caretaker_RobotLeaf"
    obj.scale = (.018, .095, .043)
    obj.rotation_euler.x = rotation
    activate(obj)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for material in materials:
        obj.data.materials.append(material)
    for face in obj.data.polygons:
        face.material_index = 1
        face.use_smooth = True
    return obj


def caretaker(materials):
    parts = [box("Caretaker_Harness", (11.5, 0, -4), (7, 45, 52), 2, materials, 0),
             box("Caretaker_LowerManifold", (0, 0, -29), (27, 51, 6), 1.5, materials, 0)]
    for y in (-13, 13):
        parts.append(cylinder("Caretaker_WaterTank", (-3, y, -4), 10.5, 44, 2.1, materials, 1, vertices=32))
        parts.append(cylinder("Caretaker_TankCap", (-3, y, 20), 8, 5, .9, materials, 0, vertices=32))
        parts.append(box("Caretaker_LevelGauge", (-13.75, y, -4), (1.5, 3, 23), .6, materials, 2))
        for z in (-18, 10):
            parts.append(box("Caretaker_TankBand", (-13.65, y, z), (1.3, 16, 3), .4, materials, 0))
    parts.append(cylinder("Caretaker_SproutStem", (-4, 0, 24), 1.5, 17, .3, materials, 0, vertices=16))
    parts.append(leaf((-4, -7, 27), -.55, materials))
    parts.append(leaf((-4, 7, 29), .5, materials))
    return join_parts(parts, "SM_GrowCaretakerPack")


def courier(materials):
    parts = [box("Courier_CargoBox", (0, 0, -4), (28, 53, 54), 3, materials, 1),
             box("Courier_Lid", (0, 0, 24), (29, 54, 5), 1.2, materials, 0),
             box("Courier_Base", (0, 0, -31), (29, 54, 4), 1, materials, 0)]
    for x in (-13, 13):
        for y in (-24.5, 24.5):
            parts.append(box("Courier_CornerGuard", (x, y, -3), (4, 6, 55), 1, materials, 0))
    for y in (-11, 11):
        parts.append(box("Courier_HandleUpright", (0, y, 29), (7, 5, 11), .9, materials, 0))
    parts.append(box("Courier_HandleTop", (0, 0, 33), (7, 27, 3), .9, materials, 0))
    parts.append(box("Courier_LabelPanel", (-14.7, 0, -2), (1.4, 33, 24), .6, materials, 0))
    for z, width in ((3, 22), (-3, 15), (-9, 22)):
        parts.append(box("Courier_RoutingMark", (-15.6, 0, z), (.6, width, 2.2), .35, materials, 2))
    return join_parts(parts, "SM_GrowCourierPack")


def export(obj, role):
    activate(obj)
    path = DEST / ("SM_Grow" + role + "Pack.fbx")
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"MESH"},
        axis_forward="-Y", axis_up="Z", apply_unit_scale=True, global_scale=1,
        apply_scale_options="FBX_SCALE_NONE", bake_space_transform=False,
        mesh_smooth_type="FACE", use_mesh_modifiers=True, add_leaf_bones=False,
        bake_anim=False, path_mode="AUTO", use_custom_props=False)
    obj.data.calc_loop_triangles()
    lo = [min(v.co[i] for v in obj.data.vertices) * 100 for i in range(3)]
    hi = [max(v.co[i] for v in obj.data.vertices) * 100 for i in range(3)]
    sizes = [hi[i] - lo[i] for i in range(3)]
    if len(obj.data.materials) != 3 or not all(abs(lo[i] + hi[i]) < .02 for i in range(3)):
        raise RuntimeError("Backpack material/pivot validation failed")
    if not (25 <= sizes[0] <= 35 and 45 <= sizes[1] <= 60 and 58 <= sizes[2] <= 75):
        raise RuntimeError("Backpack exceeds visual bounds: " + str(sizes))
    return {"id": "SM_Grow" + role + "Pack", "role": role, "decision": ROLES[role]["decision"],
            "fbx": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "triangles": len(obj.data.loop_triangles), "dimensions_cm": sizes,
            "min_cm": lo, "max_cm": hi, "material_slots": [
                {"slot": i, "material": mat.name, "base_color": list(mat.diffuse_color),
                 "metallic": mat.metallic, "roughness": mat.roughness,
                 "emission": list(mat["GrowEmission"])} for i, mat in enumerate(obj.data.materials)]}


def preview(scene, objects):
    for index, obj in enumerate(objects):
        obj.location.y = (index - 1) * .9
    world = bpy.data.worlds.new("GrowAccessoryStudio")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.065, .085, .11, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .5
    scene.world = world
    bpy.ops.object.camera_add(location=(-3.8, -2.7, 2.1))
    camera = bpy.context.object
    camera.name = "Grow_AccessoryPreviewCamera"
    camera.rotation_euler = (Vector((0, 0, -.02)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 3.25
    scene.camera = camera
    for name, position, power, size in (
            ("Key", (-3, -2, 4), 650, 4), ("Fill", (-2, 3, 2), 450, 3), ("Rim", (3, 1, 3), 600, 3)):
        data = bpy.data.lights.new("Grow_" + name, "AREA")
        data.energy, data.shape, data.size = power, "DISK", size
        obj = bpy.data.objects.new("Grow_" + name, data)
        scene.collection.objects.link(obj)
        obj.location = position
        obj.rotation_euler = (-obj.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1500
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(DEST / "GrowRobotAccessories.png")
    bpy.ops.render.render(write_still=True)


def author():
    if bpy.context.window is None or bpy.context.mode != "OBJECT":
        raise RuntimeError("Run through Blender MCP in Object Mode")
    blend = DEST / "GrowRobotAccessories.blend"
    if bpy.data.filepath and Path(bpy.data.filepath).resolve() == blend.resolve():
        raise RuntimeError("Use a separate session to preserve the open Grow working file")
    DEST.mkdir(parents=True, exist_ok=True)
    old = [path for path in DEST.iterdir() if path.is_file()]
    if old:
        backup = PROJECT / "Saved" / "GrowRobotsWork" / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ")
        backup.mkdir(parents=True, exist_ok=False)
        for path in old:
            shutil.copy2(path, backup / path.name)
    window = bpy.context.window
    previous_scene, previous_file = window.scene, bpy.data.filepath
    old_scenes = set(bpy.data.scenes.keys())
    scene = bpy.data.scenes.new("GrowRobotAccessories")
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    report = {"passed": False, "scene": scene.name, "blender_version": bpy.app.version_string,
              "assets": [], "blend": str(blend), "preview": str(DEST / "GrowRobotAccessories.png"),
              "visual_contract": {"units": "cm in Unreal; metres in Blender", "robot_height_cm": 180,
                "pivot": "centred local bounding box", "robot_forward": "+X", "dorsal_face": "-X",
                "suggested_attach_offset_cm": [-29, 0, 35], "attachment_space": "robot actor origin at capsule centre",
                "material_slots": {"0": "graphite", "1": "profession color", "2": "status emission"},
                "levels": "same role mesh; runtime may vary emission and attachment scale for levels 1-3"}}
    try:
        window.scene = scene
        graphite = make_material("M_GrowGraphite", (.032, .045, .058, 1), .62, .42)
        objects = []
        for role, build in (("Builder", builder), ("Caretaker", caretaker), ("Courier", courier)):
            color = ROLES[role]["color"]
            emission = tuple(value * 1.6 for value in color[:3]) + (1,)
            materials = [graphite, make_material("M_Grow" + role + "Role", color, .42, .34),
                         make_material("M_Grow" + role + "Emission", color, .15, .3, emission)]
            obj = build(materials)
            report["assets"].append(export(obj, role))
            objects.append(obj)
        preview(scene, objects)
        bpy.data.libraries.write(str(blend), {scene}, fake_user=True)
        if bpy.data.filepath != previous_file or not old_scenes.issubset(set(bpy.data.scenes.keys())):
            raise RuntimeError("The previous Blender scene or file changed")
        report["passed"] = True
        return report
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        window.scene = previous_scene
        (DEST / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("[GROW_ACCESSORY_AUTHORING] " + json.dumps(report), flush=True)


if __name__ == "__main__":
    author()
