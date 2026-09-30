"""Blender: saca del GLB del estacionamiento una columna de la arcada con su viga, como malla aparte.

Las dos columnas libres (y = 0 y 4 en el GLB) son iguales: se usa la de y = 4 para un solo asset,
y apply_parking_columns.py pone dos actores que el usuario mueve a mano. author_parking_scene.py
las quita de SM_Parking.

Origen al centro del pie de la columna; la viga sale hacia -X (hacia el muro, 3,7 m). Colision UCX
solo en el fuste (la viga queda por encima del robot).
Salida: SourceAssets/Parking/SM_ParkingColumna.fbx y parking_columns.json.

blender -b --factory-startup -P Scripts/author_parking_columns.py
"""
import json
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

SOURCE = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/scenes/sceneStacionamiento.glb")
OUT = Path(__file__).resolve().parents[1] / "SourceAssets/Parking"
NAME = "SM_ParkingColumna"
PIER_Y = 4.0
BEAMS = ("Exposed transverse I beam", "Transverse beam flange", "Beam end connection plate", "Connection bolt")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))


def mid_y(o):
    ys = [(o.matrix_world @ Vector(c)).y for c in o.bound_box]
    return (min(ys) + max(ys)) / 2


parts = [o for o in bpy.context.scene.objects if o.type == 'MESH' and (
    o.name.startswith("Arcade free pier 4 ") or (o.name.startswith(BEAMS) and abs(mid_y(o) - PIER_Y) < 0.3))]
foot = next(o for o in parts if o.name.startswith("Arcade free pier 4 foot"))
pts = [foot.matrix_world @ Vector(c) for c in foot.bound_box]
centre = Vector(((min(p.x for p in pts) + max(p.x for p in pts)) / 2,
                 (min(p.y for p in pts) + max(p.y for p in pts)) / 2, min(p.z for p in pts)))
for o in [o for o in bpy.context.scene.objects if o not in parts]:
    bpy.data.objects.remove(o)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.join()
col = bpy.context.view_layer.objects.active
col.name = NAME; col.data.name = NAME
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
col.data.transform(Matrix.Translation(-centre))

# colision: el fuste con su pie (0,78 m) hasta debajo de la viga
me = bpy.data.meshes.new(f"UCX_{NAME}_00")
b = bmesh.new(); vs = bmesh.ops.create_cube(b, size=1.0)["verts"]
for v in vs:
    v.co = Vector((v.co.x * 0.78, v.co.y * 0.78, v.co.z * 2.9 + 1.45))
b.to_mesh(me); b.free()
bpy.context.scene.collection.objects.link(bpy.data.objects.new(me.name, me))

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={'MESH'},
                         apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
                         mesh_smooth_type='FACE', path_mode='COPY', embed_textures=True,
                         axis_forward='-Y', axis_up='Z')
report = {"pieces": len(parts), "faces": len(col.data.polygons), "size_m": [round(d, 3) for d in col.dimensions],
          "pier_centre_glb_m": [round(c, 3) for c in centre], "materials": [m.name for m in col.data.materials]}
(OUT / "parking_columns.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("COLUMNS_OK", report)
