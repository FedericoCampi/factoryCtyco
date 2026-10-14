"""Blender: montoncito de arena de cuarzo, lo que sale de la trituradora de cuarzo (02/10).

Un monticulo irregular de ~30 cm de ancho con algunos granos sueltos encima. Sin texturas: el color lo pone
M_ArenaCuarzo en Unreal (apply_proceso_fundicion.py).
Salida: SourceAssets/Cuarzo/SM_ArenaCuarzo.fbx.

blender -b --factory-startup -P Scripts/author_arena_cuarzo.py
"""
import math
import random
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Cuarzo"
NAME = "SM_ArenaCuarzo"
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
b = bmesh.new()
mound = bmesh.ops.create_icosphere(b, subdivisions=3, radius=0.15)["verts"]
for v in mound:
    lump = 1.0 + 0.12 * math.sin(v.co.x * 40) * math.cos(v.co.y * 37) + random.uniform(-0.04, 0.04)
    v.co = Vector((v.co.x * lump, v.co.y * lump, max(v.co.z, 0.0) * 0.55 * lump))
for _ in range(9):   # granos sueltos
    grain = bmesh.ops.create_icosphere(b, subdivisions=0, radius=random.uniform(0.012, 0.022))["verts"]
    angle, dist = random.uniform(0, 2 * math.pi), random.uniform(0.0, 0.1)
    x, y = dist * math.cos(angle), dist * math.sin(angle)
    z = 0.08 * (1 - (dist / 0.15) ** 2) + 0.005
    bmesh.ops.transform(b, matrix=Matrix.Translation((x, y, z)), verts=grain)
bmesh.ops.remove_doubles(b, verts=b.verts[:], dist=0.0005)
me = bpy.data.meshes.new(NAME)
b.to_mesh(me)
b.free()
o = bpy.data.objects.new(NAME, me)
bpy.context.scene.collection.objects.link(o)
me.materials.append(bpy.data.materials.new("M_ArenaCuarzo"))
lo = min(v.co.z for v in me.vertices)
me.transform(Matrix.Translation((0, 0, -lo)))

OUT.mkdir(parents=True, exist_ok=True)
o.select_set(True)
bpy.context.view_layer.objects.active = o
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         axis_forward="-Y", axis_up="Z")
print("ARENA_OK", [round(d, 3) for d in o.dimensions], len(me.polygons))
