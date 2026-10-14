"""Blender: separa la tapa del horno de fundicion (04/10), para que en Unreal se abra y se cierre.

Toma SourceAssets/HornoFundicion/SM_HornoFundicion_Cuerpo.fbx (author_horno_base.py). La tapa (con su aro y el brazo de
la bisagra) son los trozos sueltos que estan arriba del borde de la olla, en el plano de la tapa: en el modelo esta
abierta unos 38 grados, con la bisagra atras (+Y en Blender, -Y en Unreal) a ~1,3 m, y gira alrededor de X.
Salida (mismos materiales y escala que el cuerpo):
- SM_HornoFundicion_CuerpoSinTapa.fbx: el cuerpo sin la tapa.
- SM_HornoFundicion_Tapa.fbx: la tapa, con el origen en el eje de la bisagra (tal como esta en el modelo).
- horno_tapa.json: el punto de la bisagra en cm de Unreal (desde el origen del horno) y el angulo de la tapa.

blender -b --factory-startup -P Scripts/author_horno_tapa.py
"""
import json
import math
from pathlib import Path
import bmesh
import bpy
import numpy as np
from mathutils import Matrix

DIR = Path(__file__).resolve().parent.parent / "SourceAssets/HornoFundicion"
SRC = DIR / "SM_HornoFundicion_Cuerpo.fbx"
RIM_Z = 1.11          # m: el borde de la olla llega a ~1,08; la tapa empieza arriba
LID_X = (-0.82, 0.45)  # m: a lo ancho de la tapa (mas alla estan los postes y la caja de control)

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

# trozos sueltos (el modelo viene en miles de islas)
b = bmesh.new()
b.from_mesh(src.data)
b.verts.ensure_lookup_table()
island_of = {}
islands = []
for v in b.verts:
    if v.index in island_of:
        continue
    stack, members = [v], []
    island_of[v.index] = len(islands)
    while stack:
        a = stack.pop()
        members.append(a.index)
        for e in a.link_edges:
            o = e.other_vert(a)
            if o.index not in island_of:
                island_of[o.index] = len(islands)
                stack.append(o)
    islands.append(members)
co = np.array([v.co[:] for v in b.verts])

# 1) lo seguro: trozos enteros por encima del borde y a lo ancho de la tapa; 2) el plano de la tapa (el de esos
# trozos) y todo trozo pegado a ese plano, dentro de su disco (el aro y las piezas de los costados)
lid = np.zeros(len(islands), bool)
for i, members in enumerate(islands):
    c = co[members]
    lid[i] = c[:, 2].min() > RIM_Z and LID_X[0] < c[:, 0].min() and c[:, 0].max() < LID_X[1]
in_lid = np.array([lid[island_of[i]] for i in range(len(co))])
center = co[in_lid].mean(0)
normal = np.linalg.svd(co[in_lid] - center, full_matrices=False)[2][2]
if normal[2] < 0:
    normal = -normal
for i, members in enumerate(islands):
    c = co[members]
    m = c.mean(0)
    radial = np.linalg.norm((m - center) - ((m - center) @ normal) * normal)
    if np.abs((c - center) @ normal).max() < 0.2 and radial < 0.78 and c[:, 2].min() > 1.08 and c[:, 0].max() < 0.5:
        lid[i] = True
in_lid = np.array([lid[island_of[i]] for i in range(len(co))])
pts = co[in_lid]
# bisagra: el borde de la tapa del lado +Y (donde estan los nudillos), a lo largo de X
knuckles = pts[pts[:, 1] > pts[:, 1].max() - 0.08]
pivot = np.array([pts[:, 0].mean(), knuckles[:, 1].mean(), knuckles[:, 2].mean()])
angle = math.degrees(math.acos(min(1.0, abs(normal[2]))))
b.free()


def keep(name, want_lid):
    o = src.copy()
    o.data = src.data.copy()
    o.name = o.data.name = name
    bpy.context.scene.collection.objects.link(o)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    drop = [f for f in bm.faces if bool(in_lid[f.verts[0].index]) != want_lid]
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(o.data)
    bm.free()
    return o


body = keep("SM_HornoFundicion_CuerpoSinTapa", False)
tapa = keep("SM_HornoFundicion_Tapa", True)
tapa.data.transform(Matrix.Translation((-pivot[0], -pivot[1], -pivot[2])))
report = {"source": str(SRC), "islands": len(islands), "lid_islands": int(lid.sum()),
          "pivot_unreal_cm": [round(pivot[0] * 100, 1), round(-pivot[1] * 100, 1), round(pivot[2] * 100, 1)],
          "lid_open_deg": round(angle, 1), "lid_normal": [round(float(x), 3) for x in normal]}
for obj in (body, tapa):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(DIR / f"{obj.name}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                             path_mode="COPY", embed_textures=False, axis_forward="-Y", axis_up="Z")
    report[obj.name] = {"triangles": sum(len(p.vertices) - 2 for p in obj.data.polygons)}
(DIR / "horno_tapa.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("HORNO_TAPA_OK", json.dumps(report))
