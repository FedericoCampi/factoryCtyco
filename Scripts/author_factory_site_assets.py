"""Author two decorative factory milestones through the real Blender MCP.

Create an isolated scene and keep the user's active scene/file. The meshes are
metre-authored, exported as FBX for Unreal centimetres, with floor-centred pivots.
Both face -Y, with their rear fittings toward +Y. No gameplay systems are changed.
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
DEST = PROJECT / "SourceAssets" / "Factory" / "SiteProgress"
LIBRARY = runpy.run_path(str(PROJECT / "Scripts" / "author_factory_detail_meshes.py"),
                          run_name="factory_site_bevel_helpers")
activate = LIBRARY["_activate"]
PALETTE = (
    ("Graphite", (.025, .038, .048, 1), .18, .62, (0, 0, 0, 1)),
    ("Steel", (.36, .44, .49, 1), .84, .28, (0, 0, 0, 1)),
    ("SafetyOrange", (.95, .245, .035, 1), .35, .34, (0, 0, 0, 1)),
    ("SiteCyan", (.015, .55, .66, 1), .15, .3, (.02, 1.1, 1.3, 1)),
)


def materials():
    result = []
    for name, color, metallic, roughness, emission in PALETTE:
        material = bpy.data.materials.new("M_Factory" + name)
        material.diffuse_color = color
        material.metallic, material.roughness = metallic, roughness
        material.use_nodes = True
        shader = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
        shader.inputs["Base Color"].default_value = color
        shader.inputs["Metallic"].default_value = metallic
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Emission Color"].default_value = emission
        shader.inputs["Emission Strength"].default_value = 1
        material["SiteEmission"] = list(emission)
        result.append(material)
    return result


def box(parts, mats, name, position, dimensions, slot=0, bevel=1, rotation=None):
    obj = LIBRARY["_box"](name, (0, 0, 0) if rotation else position, dimensions, bevel, mats, slot)
    if rotation:
        obj.location = tuple(value / 100 for value in position)
        obj.rotation_euler = tuple(math.radians(value) for value in rotation)
        activate(obj)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    parts.append(obj)
    return obj


def cylinder(parts, mats, name, position, radius, length, slot=1, bevel=.5, axis="Z", vertices=32):
    obj = LIBRARY["_cylinder"](name, position, radius, length, bevel, mats, slot, axis=axis, vertices=vertices)
    parts.append(obj)
    return obj


def brace(parts, mats, name, a, b, thickness=5, slot=1):
    start, end = Vector(a), Vector(b)
    vector = end - start
    obj = LIBRARY["_box"](name, (0, 0, 0), (thickness, thickness, vector.length), .7, mats, slot)
    obj.rotation_euler = vector.to_track_quat("Z", "Y").to_euler()
    obj.location = (start + end) / 200
    activate(obj)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    parts.append(obj)


def assign_slots(obj, mats, slot):
    for material in mats:
        obj.data.materials.append(material)
    for face in obj.data.polygons:
        face.material_index = slot
        face.use_smooth = True


def tube(parts, mats, name, points, radius=2.3, slot=0):
    data = bpy.data.curves.new(name + "_Curve", "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 12
    data.bevel_depth = radius / 100
    data.bevel_resolution = 3
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for knot, point in zip(spline.bezier_points, points):
        knot.co = tuple(value / 100 for value in point)
        knot.handle_left_type = knot.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    activate(obj)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    assign_slots(obj, mats, slot)
    parts.append(obj)


def torus(parts, mats, name, position, major_radius, minor_radius, slot=3):
    bpy.ops.mesh.primitive_torus_add(major_segments=64, minor_segments=8,
        location=tuple(value / 100 for value in position),
        major_radius=major_radius / 100, minor_radius=minor_radius / 100)
    obj = bpy.context.object
    obj.name = name
    activate(obj)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    assign_slots(obj, mats, slot)
    parts.append(obj)


def join(parts, name):
    activate(parts[0])
    for part in parts:
        part.select_set(True)
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name, obj.data.name = name, name + "_Geometry"
    return obj


def workshop(mats):
    parts = []
    box(parts, mats, "Workshop_Foundation", (0, 0, 5), (292, 172, 10), 0, 3)
    box(parts, mats, "Workshop_Deck", (0, 0, 11.5), (264, 144, 3), 1, .8)
    for x in (-126, 126):
        box(parts, mats, "Workshop_PillarFoot", (x, 65, 11), (25, 25, 22), 1, 2)
        box(parts, mats, "Workshop_RearPillar", (x, 65, 112), (12, 12, 204), 0, 1.2)
        box(parts, mats, "Workshop_PillarArmor", (x, 57.5, 121), (14, 3, 135), 2, .7)
        brace(parts, mats, "Workshop_CanopyBrace", (x, 65, 158), (x, -29, 209), 6, 1)
    # Cantilevered canopy leaves the whole front of the maintenance bench open.
    # Cover only the rear of the canopy: the open front lets the isometric
    # camera read the pegboard and tools instead of seeing a solid roof slab.
    box(parts, mats, "Workshop_Canopy", (0, 52, 214), (292, 68, 8), 0, 2)
    for y in (-87, 87):
        box(parts, mats, "Workshop_CanopyFascia", (0, y, 214), (300, 6, 12), 2, 1.2)
    for x in (-147, 147):
        box(parts, mats, "Workshop_CanopySide", (x, 0, 214), (6, 168, 12), 2, 1.2)
    for x in (-90, -30, 30, 90):
        box(parts, mats, "Workshop_RoofPanel", (x, 51, 218.5), (53, 76, 2), 1, .5)
    box(parts, mats, "Workshop_WorkLight", (0, -72, 209), (232, 4, 2), 3, .6)
    box(parts, mats, "Workshop_BackLight", (0, 51, 204), (220, 3, 2), 3, .5)
    for x in (-108, 108):
        for y in (-14, 45):
            box(parts, mats, "Workshop_BenchLeg", (x, y, 50), (10, 10, 74), 1, 1)
    box(parts, mats, "Workshop_LowerShelf", (0, 16, 31), (232, 68, 6), 0, 1.2)
    box(parts, mats, "Workshop_Table", (0, 16, 91), (244, 78, 8), 1, 1.7)
    box(parts, mats, "Workshop_FrontApron", (0, -26, 82), (244, 8, 12), 2, 1)
    box(parts, mats, "Workshop_DrawerCabinet", (-73, 13, 61), (56, 62, 45), 0, 2)
    for z in (49, 62, 75):
        box(parts, mats, "Workshop_Drawer", (-73, -19.5, z), (52, 4, 11), 2, .8)
        box(parts, mats, "Workshop_DrawerHandle", (-73, -23, z + 1), (25, 3, 2.5), 1, .6)
    box(parts, mats, "Workshop_PegboardFrame", (0, 65, 149), (230, 7, 78), 0, 1.5)
    box(parts, mats, "Workshop_Pegboard", (0, 60.5, 149), (214, 3, 69), 1, .8)
    for x in (-95, -47, 0, 47, 95):
        for z in (123, 148, 173):
            cylinder(parts, mats, "Workshop_PegHole", (x, 58.5, z), 1.3, .5, 0, .08, axis="Y", vertices=12)
    # Oversized silhouettes remain readable from the factory's isometric camera.
    for x, top in ((-66, 172), (31, 164)):
        box(parts, mats, "Workshop_WrenchShaft", (x, 56, top - 21), (4, 3, 39), 0, .7)
        box(parts, mats, "Workshop_WrenchHead", (x, 55.5, top), (15, 4, 7), 2, .6)
        for side in (-1, 1):
            box(parts, mats, "Workshop_WrenchJaw", (x + side * 5.5, 55.5, top + 5), (4, 4, 7), 2, .6)
    box(parts, mats, "Workshop_HammerHandle", (-17, 55.5, 150), (5, 4, 41), 2, .6)
    box(parts, mats, "Workshop_HammerHead", (-17, 54, 173), (26, 9, 12), 0, 1.5)
    box(parts, mats, "Workshop_DriverShaft", (75, 55.5, 143), (2, 3, 23), 1, .4)
    box(parts, mats, "Workshop_DriverGrip", (75, 55.5, 166), (7, 7, 19), 2, 1.2)
    # A vice and a small parts tray give the work surface a clear purpose.
    box(parts, mats, "Workshop_ViceBase", (61, -1, 99), (35, 31, 8), 0, 1.4)
    for x in (51, 72):
        box(parts, mats, "Workshop_ViceJaw", (x, -1, 110), (10, 29, 16), 2, 1)
        box(parts, mats, "Workshop_ViceFace", (x + (5.5 if x < 60 else -5.5), -1, 113), (2, 24, 8), 1, .5)
    box(parts, mats, "Workshop_PartsTray", (-36, 4, 99), (41, 30, 6), 0, 1.1)
    for x in (-47, -34, -21):
        cylinder(parts, mats, "Workshop_SpareBolt", (x, 3, 105), 3.4, 7, 1, .6, vertices=12)
    for x in (-103, -78, 78, 103):
        box(parts, mats, "Workshop_FloorMark", (x, -75, 12), (17, 7, 2), 2, .3)
    return join(parts, "SM_FactoryWorkshop")


def charge_station(mats):
    parts = []
    box(parts, mats, "Charge_Foundation", (0, 0, 6), (240, 240, 12), 0, 5)
    box(parts, mats, "Charge_Deck", (0, 0, 14), (216, 216, 4), 1, 2)
    cylinder(parts, mats, "Charge_CentrePad", (0, -6, 17.5), 77, 3, 0, 1.2, vertices=64)
    torus(parts, mats, "Charge_LocatorRing", (0, -6, 17), 83, 1.5)
    for x in (-96, 96):
        for y in (-99, 99):
            box(parts, mats, "Charge_CornerStripe", (x, y, 18), (24, 5, 2), 2, .5)
    for x in (-85, 85):
        box(parts, mats, "Charge_PostFoot", (x, 91, 22), (26, 28, 16), 2, 1.8)
        box(parts, mats, "Charge_Post", (x, 91, 78), (16, 20, 128), 0, 2)
        box(parts, mats, "Charge_PostCap", (x, 91, 142), (20, 24, 16), 2, 2)
        box(parts, mats, "Charge_PostStatus", (x, 79.8, 89), (5, 2, 74), 3, .7)
    box(parts, mats, "Charge_RearRail", (0, 95, 116), (152, 8, 10), 1, 1.5)
    box(parts, mats, "Charge_RearSocketBox", (0, 94, 79), (42, 18, 42), 0, 3)
    cylinder(parts, mats, "Charge_CouplerRim", (0, 82.5, 79), 13, 6, 2, .9, axis="Y")
    cylinder(parts, mats, "Charge_CouplerInset", (0, 78.9, 79), 8.5, 1.5, 1, .4, axis="Y")
    for x in (-3, 3):
        box(parts, mats, "Charge_ConnectorContact", (x, 77.8, 79), (2, 1, 7), 3, .3)
    tube(parts, mats, "Charge_StowedCable", [(-12, 81, 76), (-46, 77, 56), (-66, 80, 44), (-82, 83, 92)], 2.5)
    box(parts, mats, "Charge_CableClip", (-85, 79.5, 96), (12, 6, 14), 2, 1.1)
    box(parts, mats, "Charge_ConsolePedestal", (76, 40, 65), (12, 12, 96), 1, 1.4)
    box(parts, mats, "Charge_Console", (76, 40, 119), (30, 23, 43), 0, 3)
    box(parts, mats, "Charge_ConsoleScreen", (76, 27.7, 126), (22, 2, 18), 3, 1)
    for x in (69, 76, 83):
        cylinder(parts, mats, "Charge_ConsoleControl", (x, 26.4, 108), 1.8, 1.4, 2, .25, axis="Y", vertices=16)
    for y in (-50, -29):
        box(parts, mats, "Charge_CentreGuide", (0, y, 19.5), (24, 3, 1), 3, .4)
    return join(parts, "SM_FactoryChargeStation")


def export(obj, expected):
    activate(obj)
    obj.data.calc_loop_triangles()
    low = [min(vertex.co[i] for vertex in obj.data.vertices) * 100 for i in range(3)]
    high = [max(vertex.co[i] for vertex in obj.data.vertices) * 100 for i in range(3)]
    size = [high[i] - low[i] for i in range(3)]
    if any(abs(size[i] - expected[i]) > .03 for i in range(3)):
        raise RuntimeError(obj.name + " incorrect dimensions: " + str(size))
    if abs(low[2]) > .03 or any(abs(low[i] + high[i]) > .03 for i in (0, 1)):
        raise RuntimeError(obj.name + " needs a floor-centred pivot: " + str(low))
    if len(obj.data.materials) != 4:
        raise RuntimeError("Four consistent material slots are required")
    name = "SM_FactoryWorkshop" if "Workshop" in obj.name else "SM_FactoryChargeStation"
    destination = DEST / (name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=str(destination), use_selection=True, object_types={"MESH"},
        axis_forward="-Y", axis_up="Z", apply_unit_scale=True, global_scale=1,
        apply_scale_options="FBX_SCALE_NONE", bake_space_transform=False,
        mesh_smooth_type="FACE", use_mesh_modifiers=True, add_leaf_bones=False,
        bake_anim=False, path_mode="AUTO", use_custom_props=False)
    return {"id": name, "fbx": destination.name,
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "dimensions_cm": size, "min_cm": low, "max_cm": high,
        "triangles": len(obj.data.loop_triangles), "front": "-Y", "rear": "+Y",
        "material_slots": [{"slot": i, "key": PALETTE[i][0], "name": mat.name,
            "base_color": list(mat.diffuse_color), "metallic": mat.metallic,
            "roughness": mat.roughness, "emission": list(mat["SiteEmission"])}
            for i, mat in enumerate(obj.data.materials)]}


def render_preview(scene, objects):
    objects[0].location.x = -1.85
    objects[1].location.x = 1.8
    world = bpy.data.worlds.new("FactorySiteStudioWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.055, .075, .10, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .55
    scene.world = world
    floor_material = bpy.data.materials.new("FactorySitePreviewFloor")
    floor_material.diffuse_color = (.10, .125, .15, 1)
    floor_material.use_nodes = True
    shader = next(node for node in floor_material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = floor_material.diffuse_color
    shader.inputs["Roughness"].default_value = .8
    LIBRARY["_box"]("PreviewGround", (0, 0, -3), (2200, 2200, 6), 1, [floor_material])
    bpy.ops.object.camera_add(location=(6.4, -10, 7))
    camera = bpy.context.object
    camera.name = "FactorySitePreviewCamera"
    camera.rotation_euler = (Vector((0, 0, .8)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type, camera.data.ortho_scale = "ORTHO", 8.25
    scene.camera = camera
    for label, location, power, size in (
            ("Key", (-3, -5, 7), 1450, 6), ("Fill", (5, -3, 4), 1150, 5), ("Rim", (0, 5, 7), 1700, 5)):
        light = bpy.data.lights.new("FactorySite_" + label, "AREA")
        light.energy, light.shape, light.size = power, "DISK", size
        obj = bpy.data.objects.new("FactorySite_" + label, light)
        scene.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (Vector((0, 0, .7)) - obj.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1800, 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(DEST / "FactorySiteProgress.png")
    bpy.ops.render.render(write_still=True)


def author():
    if bpy.context.window is None or bpy.context.mode != "OBJECT":
        raise RuntimeError("Run through Blender MCP in Object Mode")
    destination = DEST / "FactorySiteProgress.blend"
    if bpy.data.filepath and Path(bpy.data.filepath).resolve() == destination.resolve():
        raise RuntimeError("Use a separate session to preserve the open source file")
    DEST.mkdir(parents=True, exist_ok=True)
    existing = [path for path in DEST.iterdir() if path.is_file()]
    backup = None
    if existing:
        folder = PROJECT / "Saved" / "VisualPolishWork" / ("FactorySiteSource-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ"))
        folder.mkdir(parents=True, exist_ok=False)
        for path in existing:
            shutil.copy2(path, folder / path.name)
        backup = str(folder)
    window = bpy.context.window
    previous_scene, previous_file = window.scene, bpy.data.filepath
    previous_scenes = set(bpy.data.scenes.keys())
    scene = bpy.data.scenes.new("FactorySiteProgress")
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    report = {"passed": False, "scene": scene.name, "blender_version": bpy.app.version_string,
              "backup": backup, "blend": str(destination), "assets": [],
              "preview": str(DEST / "FactorySiteProgress.png"),
              "contract": {"pivot": "floor and XY centre", "front": "-Y", "rear": "+Y",
                           "units_unreal": "cm", "scope": "decorative milestone assets; no battery simulation",
                           "charge_pad_top_cm": 20, "authoring": "metres, FBX scale converted to centimetres"}}
    try:
        window.scene = scene
        mats = materials()
        objects = [workshop(mats), charge_station(mats)]
        for obj, dimensions in zip(objects, ((300, 180, 220), (240, 240, 150))):
            report["assets"].append(export(obj, dimensions))
        render_preview(scene, objects)
        bpy.data.libraries.write(str(destination), {scene}, fake_user=True)
        if bpy.data.filepath != previous_file or not previous_scenes.issubset(set(bpy.data.scenes.keys())):
            raise RuntimeError("The user's original scene or working file changed")
        report["passed"] = True
        return report
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        window.scene = previous_scene
        (DEST / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("[FACTORY_SITE_AUTHORING] " + json.dumps(report), flush=True)


if __name__ == "__main__":
    author()
