"""Blender: prepara el horno de fundicion del usuario (3D assets/GLBs/hornoFundicion.glb) para Unreal (30/09).

El GLB viene normalizado (1 m de alto, ~690 000 triangulos, una sola malla con 4 texturas de 2-4K). Se lleva a
HEIGHT_M de alto (entra en una celda de 2 x 2 m), origen al centro del piso, se reduce a ~150 000 triangulos y se le
agrega una colision UCX de caja (un poco adentro del contorno).
Salida: SourceAssets/HornoFundicion/SM_HornoFundicion.fbx y horno_build.json.

blender -b --factory-startup -P Scripts/author_horno_fundicion.py
"""
import json
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

SRC = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/hornoFundicion.glb")
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/HornoFundicion"
NAME = "SM_HornoFundicion"
HEIGHT_M = 2.0     # TecJunior mide 1,70 m
DECIMATE = 0.22    # ~690k -> ~150k triangulos
INSET = 0.03       # la caja de colision queda 3 cm adentro del contorno

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
o = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
bpy.ops.object.select_all(action="DESELECT")
o.select_set(True)
bpy.context.view_layer.objects.active = o
o.parent = None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for extra in [x for x in bpy.context.scene.objects if x is not o]:
    bpy.data.objects.remove(extra)
tris_in = sum(len(p.vertices) - 2 for p in o.data.polygons)

co = [v.co for v in o.data.vertices]
lo = Vector([min(c[i] for c in co) for i in range(3)])
hi = Vector([max(c[i] for c in co) for i in range(3)])
scale = HEIGHT_M / (hi.z - lo.z)
o.data.transform(Matrix.Scale(scale, 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
dec = o.modifiers.new("Decimate", "DECIMATE")
dec.ratio = DECIMATE
bpy.ops.object.modifier_apply(modifier=dec.name)
o.name = o.data.name = NAME
size = [round((hi[i] - lo[i]) * scale, 3) for i in range(3)]

me = bpy.data.meshes.new(f"UCX_{NAME}_00")
b = bmesh.new()
for v in bmesh.ops.create_cube(b, size=1.0)["verts"]:
    v.co = Vector((v.co.x * (size[0] - 2 * INSET), v.co.y * (size[1] - 2 * INSET), (v.co.z + 0.5) * (size[2] - INSET)))
b.to_mesh(me)
b.free()
ucx = bpy.data.objects.new(me.name, me)
bpy.context.scene.collection.objects.link(ucx)

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
o.select_set(True)
ucx.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         path_mode="COPY", embed_textures=True, axis_forward="-Y", axis_up="Z")
tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
(OUT / "horno_build.json").write_text(json.dumps({
    "source": str(SRC), "height_m": HEIGHT_M, "size_m": size, "scale": round(scale, 4),
    "triangles_in": tris_in, "triangles": tris, "materials": [m.name for m in o.data.materials if m],
    "ucx": 1}, indent=1), encoding="utf-8")
print("HORNO_OK", size, tris)
