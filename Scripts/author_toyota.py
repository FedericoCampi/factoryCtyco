"""Blender (background): la Toyota del usuario para el estacionamiento (03/10).

blender -b --factory-startup -P Scripts/author_toyota.py

Fuente: 3D assets/GLBs/toyota.glb (camioneta de IA, ~700k triangulos, 1 m de largo a lo largo de Y, una malla con 4
texturas de 4K). Como el auto de los empleados (author_employee_cars.py): se reduce a TRIANGLES, se lleva a LENGTH de
largo, se gira para que la trompa (-Y en el GLB) mire a +X, origen en el piso al centro, colision UCX de la
carroceria (sin espejos). Las texturas bajan a TEXTURE.
Salida: SourceAssets/Toyota/SM_Toyota.fbx y toyota_build.json.
"""
import json
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/toyota.glb")
OUT = ROOT / "SourceAssets/Toyota"
NAME = "SM_Toyota"
LENGTH = 4.9      # m: camioneta mediana (alto ~0,4 del largo)
TRIANGLES = 80000
TEXTURE = 2048

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
body = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
bpy.context.view_layer.objects.active = body
body.select_set(True)
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(bpy.context.scene.objects):
    if o is not body:
        bpy.data.objects.remove(o)
bm = bmesh.new()
bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
bm.to_mesh(body.data)
bm.free()
source_tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
mod = body.modifiers.new("Gameplay", 'DECIMATE')
mod.ratio = min(1.0, TRIANGLES / max(1, source_tris))
mod.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier=mod.name)
co = [v.co.copy() for v in body.data.vertices]
lo = Vector([min(c[i] for c in co) for i in range(3)])
hi = Vector([max(c[i] for c in co) for i in range(3)])
scale = LENGTH / (hi.y - lo.y)
centre = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
body.data.transform(Matrix.Rotation(math.pi / 2, 4, 'Z') @ Matrix.Scale(scale, 4) @ Matrix.Translation(-centre))
for poly in body.data.polygons:
    poly.use_smooth = True
body.data.update()
body.name = body.data.name = NAME
co = [v.co.copy() for v in body.data.vertices]
lo = Vector([min(c[i] for c in co) for i in range(3)])
hi = Vector([max(c[i] for c in co) for i in range(3)])

# colision: la carroceria (sin espejos), un poco adentro
me = bpy.data.meshes.new(f"UCX_{NAME}_00")
b = bmesh.new()
vs = bmesh.ops.create_cube(b, size=1.0)["verts"]
clo, chi = Vector((lo.x + .05, lo.y + .15, .15)), Vector((hi.x - .05, hi.y - .15, hi.z - .05))
for v in vs:
    v.co = Vector((v.co.x * (chi.x - clo.x), v.co.y * (chi.y - clo.y), v.co.z * (chi.z - clo.z))) + (clo + chi) / 2
b.to_mesh(me)
b.free()
ucx = bpy.data.objects.new(me.name, me)
bpy.context.scene.collection.objects.link(ucx)

for image in bpy.data.images:
    if image.size[0] > TEXTURE:
        image.scale(TEXTURE, TEXTURE)
        image.pack()

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
ucx.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={'MESH'},
                         apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE',
                         path_mode='COPY', embed_textures=True, axis_forward='-Y', axis_up='Z')
report = {"source": str(SOURCE), "triangles_in": source_tris, "triangles": sum(len(p.vertices) - 2 for p in body.data.polygons),
          "size_m": [round(hi[i] - lo[i], 2) for i in range(3)], "textures": TEXTURE}
(OUT / "toyota_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("TOYOTA_OK", json.dumps(report))
