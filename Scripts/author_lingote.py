"""Blender: lingote de silicio (02/10), lo que sale del contenedor del horno.

Una barra trapezoidal (mas angosta arriba, como un lingote colado) de 30 x 12 x 8 cm con los cantos de arriba
biselados. Sin texturas: el color lo pone M_LingoteSilicio en Unreal (apply_lingotes.py).
Salida: SourceAssets/Lingote/SM_LingoteSilicio.fbx.

blender -b --factory-startup -P Scripts/author_lingote.py
"""
from pathlib import Path
import bmesh
import bpy

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Lingote"
NAME = "SM_LingoteSilicio"
L, W, H, TOP = 0.30, 0.12, 0.08, 0.8   # largo, ancho, alto; la cara de arriba es TOP de la de abajo

bpy.ops.wm.read_factory_settings(use_empty=True)
b = bmesh.new()
verts = bmesh.ops.create_cube(b, size=1.0)["verts"]
for v in verts:
    k = TOP if v.co.z > 0 else 1.0
    v.co.x, v.co.y, v.co.z = v.co.x * L * k, v.co.y * W * k, (v.co.z + 0.5) * H
top = [e for e in b.edges if all(v.co.z > H * 0.9 for v in e.verts)]
bmesh.ops.bevel(b, geom=top, offset=0.008, segments=2, affect="EDGES")
me = bpy.data.meshes.new(NAME)
b.to_mesh(me)
b.free()
o = bpy.data.objects.new(NAME, me)
bpy.context.scene.collection.objects.link(o)
me.materials.append(bpy.data.materials.new("M_LingoteSilicio"))

OUT.mkdir(parents=True, exist_ok=True)
o.select_set(True)
bpy.context.view_layer.objects.active = o
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         axis_forward="-Y", axis_up="Z")
print("LINGOTE_OK", [round(d, 3) for d in o.dimensions], len(me.polygons))
