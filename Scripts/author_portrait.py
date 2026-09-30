"""Blender: retrato de TecJunior para el panel del personaje (tecla I), 28/09.

Renderiza la cabeza del modelo del usuario (SourceAssets/TecJunior/tecJunior.glb) de frente, un poco
girada, con fondo transparente: SourceAssets/UI/T_RetratoTecJunior.png (512 x 512).

blender -b --factory-startup -P Scripts/author_portrait.py
"""
import math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "SourceAssets/TecJunior/tecJunior.glb"
OUT = ROOT / "SourceAssets/UI/T_RetratoTecJunior.png"
HEIGHT = 1.70

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
scale = HEIGHT / (hi.z - lo.z)
for o in [o for o in bpy.context.scene.objects if o.parent is None]:
    o.scale = o.scale * scale
    o.location = (o.location - Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))) * scale
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
top = max(p.z for p in pts)
# El frente del personaje: el lado con mas volumen de la cabeza (la cara). En el glb mira a -Y.
head = Vector((0, 0, top - 0.2))

scn = bpy.context.scene
scn.render.engine = "BLENDER_EEVEE"
scn.render.film_transparent = True
scn.render.resolution_x = scn.render.resolution_y = 512
scn.render.image_settings.file_format = "PNG"
scn.render.image_settings.color_mode = "RGBA"
world = bpy.data.worlds.new("w"); scn.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
for name, energy, rot in (("key", 3.5, (0.9, 0.1, -0.5)), ("fill", 1.2, (1.1, 0.0, 0.9)), ("rim", 2.0, (2.3, 0.0, 3.1))):
    light = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN")); light.data.energy = energy
    light.rotation_euler = rot; scn.collection.objects.link(light)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scn.collection.objects.link(cam); scn.camera = cam
cam.data.lens = 85
yaw = math.radians(18)
cam.location = head + Vector((math.sin(yaw) * 1.55, -math.cos(yaw) * 1.55, 0.04))
direction = head - cam.location
cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
OUT.parent.mkdir(parents=True, exist_ok=True)
scn.render.filepath = str(OUT)
bpy.ops.render.render(write_still=True)
print("RETRATO_OK", OUT)
