"""Blender: trozo de cuarzo para las cintas y el deposito (02/10).

Un racimo de cinco cristales hexagonales con punta sobre una piedrita, ~30 cm de alto (el tamaño con el que las cintas
muestran la carga). Sin texturas: el color lo pone M_Cuarzo en Unreal (apply_proceso_fundicion.py).
Salida: SourceAssets/Cuarzo/SM_Cuarzo.fbx.

blender -b --factory-startup -P Scripts/author_cuarzo.py
"""
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Cuarzo"
NAME = "SM_Cuarzo"
# (x, y, alto, radio, inclinacion en grados, hacia donde se inclina)
CRYSTALS = [(0.0, 0.0, 0.26, 0.045, 0, 0), (0.05, 0.02, 0.19, 0.035, 22, 20), (-0.045, 0.03, 0.17, 0.032, 25, 150),
            (0.01, -0.05, 0.15, 0.03, 28, 265), (-0.03, -0.03, 0.12, 0.026, 32, 215)]

bpy.ops.wm.read_factory_settings(use_empty=True)
b = bmesh.new()
rock = bmesh.ops.create_icosphere(b, subdivisions=1, radius=0.08)["verts"]
for v in rock:
    v.co = Vector((v.co.x * 1.3, v.co.y * 1.1, v.co.z * 0.45 + 0.025))
for x, y, height, radius, tilt, toward in CRYSTALS:
    prism = bmesh.ops.create_cone(b, cap_ends=True, segments=6, radius1=radius, radius2=radius, depth=height * 0.8)["verts"]
    tip = max(prism, key=lambda v: v.co.z)
    top = [v for v in prism if v.co.z > 0]
    # punta: los seis vertices de arriba se juntan en un pico
    peak = bmesh.ops.poke(b, faces=[f for f in b.faces if all(v in top for v in f.verts) and len(f.verts) == 6])["verts"]
    for v in peak:
        v.co.z += height * 0.25
    place = Matrix.Translation((x, y, 0.02)) @ Matrix.Rotation(math.radians(toward), 4, "Z") @ Matrix.Rotation(math.radians(tilt), 4, "Y") \
        @ Matrix.Translation((0, 0, height * 0.4))
    bmesh.ops.transform(b, matrix=place, verts=prism + peak)
me = bpy.data.meshes.new(NAME)
b.to_mesh(me)
b.free()
o = bpy.data.objects.new(NAME, me)
bpy.context.scene.collection.objects.link(o)
for p in me.polygons:
    p.use_smooth = False
mat = bpy.data.materials.new("M_Cuarzo")
me.materials.append(mat)
lo = min(v.co.z for v in me.vertices)
me.transform(Matrix.Translation((0, 0, -lo)))

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
o.select_set(True)
bpy.context.view_layer.objects.active = o
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         axis_forward="-Y", axis_up="Z")
size = [round(d, 3) for d in o.dimensions]
print("CUARZO_OK", size, len(me.polygons))
