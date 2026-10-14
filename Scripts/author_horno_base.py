"""Blender: separa el horno de fundicion (SourceAssets/HornoFundicion/SM_HornoFundicion.fbx) en base y cuerpo (01/10).

La base es la placa de abajo (caras con todos sus vertices por debajo de CUT_M): en Unreal se estira en Z para elevar
el horno sin patas (AFactoryRaisedProp). El cuerpo es todo lo demas. Mismo origen (centro del piso) y materiales.
Salida: SourceAssets/HornoFundicion/SM_HornoFundicion_Base.fbx, SM_HornoFundicion_Cuerpo.fbx y horno_base.json.

blender -b --factory-startup -P Scripts/author_horno_base.py
"""
import json
from pathlib import Path
import bmesh
import bpy

DIR = Path(__file__).resolve().parent.parent / "SourceAssets/HornoFundicion"
SRC = DIR / "SM_HornoFundicion.fbx"
CUT_M = 0.10       # la placa de la base llega a ~10 cm; arriba de eso el contorno se angosta

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(SRC))
for o in [o for o in bpy.context.scene.objects if o.type != "MESH" or o.name.startswith("UCX")]:
    bpy.data.objects.remove(o)
src = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
src.parent = None
bpy.ops.object.select_all(action="DESELECT")
src.select_set(True)
bpy.context.view_layer.objects.active = src
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def part(name, keep_base):
    o = src.copy()
    o.data = src.data.copy()
    o.name = o.data.name = name
    bpy.context.scene.collection.objects.link(o)
    b = bmesh.new()
    b.from_mesh(o.data)
    drop = [f for f in b.faces if all(v.co.z < CUT_M for v in f.verts) != keep_base]
    bmesh.ops.delete(b, geom=drop, context="FACES")
    bmesh.ops.delete(b, geom=[v for v in b.verts if not v.link_faces], context="VERTS")   # sin vertices sueltos
    b.to_mesh(o.data)
    b.free()
    return o


report = {"source": str(SRC), "cut_m": CUT_M}
for name, keep_base in (("SM_HornoFundicion_Base", True), ("SM_HornoFundicion_Cuerpo", False)):
    o = part(name, keep_base)
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(DIR / f"{name}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                             path_mode="COPY", embed_textures=False, axis_forward="-Y", axis_up="Z")
    zs = [v.co.z for v in o.data.vertices]
    report[name] = {"triangles": sum(len(p.vertices) - 2 for p in o.data.polygons), "z_m": [round(min(zs), 3), round(max(zs), 3)]}
(DIR / "horno_base.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("HORNO_BASE_OK", report)
