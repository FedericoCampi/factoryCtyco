"""Read original GLBs and render identification previews without changing them.

Run with Blender --background --python Scripts/review_factory_assets.py.
Outputs are limited to Docs/factory_asset_review; this does not import into UE.
"""
import json
import math
import struct
from pathlib import Path

import bpy
from mathutils import Vector

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\Users\Usuario\Desktop\3D assets\GLBs\robotAutomation")
OUTPUT = PROJECT / "Docs" / "factory_asset_review"
OUTPUT.mkdir(parents=True, exist_ok=True)
FILES = [
    "trituradora-optimizada-complete.glb",
    "fundicion.glb",
    "deposito.glb",
    "cinta_recta.glb",
    "frag_metalicos.glb",
    "frag_triturado.glb",
    "frag_triturado_almacenamiento.glb",
    "deposito_triturado.glb",
]
ROLES = {
    "trituradora-optimizada-complete.glb": "Trituradora",
    "fundicion.glb": "Fundición",
    "deposito.glb": "Depósito general",
    "cinta_recta.glb": "Cinta transportadora recta",
    "frag_metalicos.glb": "Chatarra recogible sin procesar",
    "frag_triturado.glb": "Material triturado",
    "frag_triturado_almacenamiento.glb": "Material triturado almacenado temporalmente",
    "deposito_triturado.glb": "Depósito para guardar y almacenar material triturado",
}


def document(path):
    with path.open("rb") as stream:
        magic, version, length = struct.unpack("<III", stream.read(12))
        size, kind = struct.unpack("<II", stream.read(8))
        assert magic == 0x46546C67 and version == 2 and kind == 0x4E4F534A
        assert length == path.stat().st_size
        return json.loads(stream.read(size))


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_preview(filename):
    path = SOURCE / filename
    doc = document(path)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    assert objects, filename
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    dimensions = high - low
    assert min(dimensions) > 0
    centre = (low + high) / 2
    span = max(dimensions)
    # Use camera/light scale, leaving all imported geometry and transforms intact.
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 6
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("ReviewWorld")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.40, .43, .48, 1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = .65
    camera_data = bpy.data.cameras.new("ReviewCamera")
    camera = bpy.data.objects.new("ReviewCamera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = centre + Vector((1.8, -2.6, 1.7)) * span
    look_at(camera, centre)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = span * 1.65
    camera_data.clip_start = span * .001
    camera_data.clip_end = span * 30
    scene.camera = camera
    for name, offset, power, size in [
        ("Key", (-2, -3, 4), 650, 3),
        ("Fill", (3, -1, 2), 350, 2.5),
        ("Rim", (0, 3, 3), 450, 2),
    ]:
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = power * span * span
        light_data.shape = "DISK"
        light_data.size = span * size
        light = bpy.data.objects.new(name, light_data)
        scene.collection.objects.link(light)
        light.location = centre + Vector(offset) * span
        look_at(light, centre)
    scene.render.filepath = str(OUTPUT / (path.stem + ".png"))
    bpy.ops.render.render(write_still=True)
    triangles = 0
    for obj in objects:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
    return {
        "file": filename,
        "bytes": path.stat().st_size,
        "triangles": triangles,
        "mesh_objects": len(objects),
        "materials": len(doc.get("materials", [])),
        "images": [{"name": image.get("name"), "size": list(image.size)}
                   for image in bpy.data.images if image.type == "IMAGE"],
        "skins": len(doc.get("skins", [])),
        "animations": len(doc.get("animations", [])),
        "bounds_blender": {"min": list(low), "max": list(high)},
        "dimensions_blender": list(dimensions),
        "preview": Path(scene.render.filepath).name,
        "role": ROLES[filename],
    }


report = {"source": str(SOURCE), "originals_modified": False, "assets": []}
for filename in FILES:
    print("[FACTORY_REVIEW] " + filename, flush=True)
    report["assets"].append(render_preview(filename))
    (OUTPUT / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("[FACTORY_REVIEW_COMPLETE] " + str(OUTPUT), flush=True)
