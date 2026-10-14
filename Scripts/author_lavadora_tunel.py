"""Blender: la caja gris (SM_Deposito) con dos huecos enfrentados, para que la cinta pase por adentro (02/10).

Parte de la malla exportada de Unreal (SourceAssets/LavadoraTunel/SM_Deposito_export.fbx, apply_tunel_lavadora.py) y de
tunel_holes.json: un rectangulo por pared, en el espacio de la malla de Unreal (cm): centro en X, medio ancho, y Z de
abajo y de arriba (la cinta sube, asi que cada hueco tiene su altura). Las paredes son las de Y = +-HALF_Y.
Se corta el contorno de cada hueco (bisect) y se borran las caras de adentro; todo se duplica dado vuelta para que el
interior se vea por los huecos.
Salida: SourceAssets/LavadoraTunel/SM_LavadoraTunel.fbx (mismas coordenadas que SM_Deposito, un solo material).

blender -b --factory-startup -P Scripts/author_lavadora_tunel.py
"""
import json
from pathlib import Path
import bmesh
import bpy
from mathutils import Vector

DIR = Path(__file__).resolve().parent.parent / "SourceAssets/LavadoraTunel"
NAME = "SM_LavadoraTunel"
WALL_DEPTH = 8.0   # cm: caras a menos de esto de la pared son la pared

holes = json.loads((DIR / "tunel_holes.json").read_text(encoding="utf-8"))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(DIR / "SM_Deposito_export.fbx"))
o = [x for x in bpy.context.scene.objects if x.type == "MESH"][0]
bpy.context.view_layer.objects.active = o
o.select_set(True)
o.parent = None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for extra in [x for x in bpy.context.scene.objects if x is not o]:
    bpy.data.objects.remove(extra)

# de Unreal (cm) a esta malla: escala por el tamaño y Y dada vuelta si hace falta (lo dice el bounding box)
co = [v.co for v in o.data.vertices]
lo = Vector([min(c[i] for c in co) for i in range(3)])
hi = Vector([max(c[i] for c in co) for i in range(3)])
k = (hi.z - lo.z) / (holes["bounds_max"][2] - holes["bounds_min"][2])
flip = -1.0 if abs(lo.y / k - (-holes["bounds_max"][1])) < abs(lo.y / k - holes["bounds_min"][1]) else 1.0
to_mesh = lambda x, y, z: Vector((x * k, y * k * flip, z * k))
print("MAPA", k, flip, lo, hi)

b = bmesh.new()
b.from_mesh(o.data)
cut = 0
for hole in holes["holes"]:
    wall_y = to_mesh(0, hole["wall_y"], 0).y
    near = lambda f: abs(f.calc_center_median().y - wall_y) < WALL_DEPTH * k
    x0, x1 = (hole["x"] - hole["half_width"]) * k, (hole["x"] + hole["half_width"]) * k
    z0, z1 = hole["z0"] * k, hole["z1"] * k
    for co_, no in (((x0, 0, 0), (1, 0, 0)), ((x1, 0, 0), (1, 0, 0)), ((0, 0, z0), (0, 0, 1)), ((0, 0, z1), (0, 0, 1))):
        faces = [f for f in b.faces if near(f)]
        geom = list({v for f in faces for v in f.verts}) + list({e for f in faces for e in f.edges}) + faces
        bmesh.ops.bisect_plane(b, geom=geom, plane_co=co_, plane_no=no)
    inside = [f for f in b.faces if near(f) and x0 < f.calc_center_median().x < x1 and z0 < f.calc_center_median().z < z1]
    cut += len(inside)
    bmesh.ops.delete(b, geom=inside, context="FACES_ONLY")
back = bmesh.ops.duplicate(b, geom=b.faces[:])["geom"]
bmesh.ops.reverse_faces(b, faces=[g for g in back if isinstance(g, bmesh.types.BMFace)])
b.to_mesh(o.data)
b.free()
o.name = o.data.name = NAME
while len(o.data.materials) > 1:
    o.data.materials.pop()

bpy.ops.object.select_all(action="DESELECT")
o.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(DIR / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         axis_forward="-Y", axis_up="Z")
print("TUNEL_OK", cut, len(o.data.polygons))
