"""Blender: tapa los huecos de las paredes de la cabina del ascensor (04/10).

La cabina del usuario (SM_Ascensor2Cabina, author_elevator2.py) tiene las paredes a media altura: los costados (+-Y)
llegan a ~1 m y el fondo (-X) a ~1,55 m, y arriba quedaba abierto hasta el techo. Mide, en cada pared, que celdas de
GRID metros tienen geometria (caras que miran hacia esa pared, proyectadas sobre su plano) y llena las vacias entre los
postes, del piso al techo (CLEAR), con paneles en el plano de la pared, del color de sus paneles (medido en su
textura). El frente (+X) es la entrada: lo cierran las puertas corredizas, no se toca.
Salida: SourceAssets/Ascensor2/SM_Ascensor2Relleno.fbx (mismo origen que la cabina) y elevator_paneles.json.

blender -b --factory-startup -P Scripts/author_elevator_paneles.py
"""
import json
from pathlib import Path
import bmesh
import bpy
import numpy as np
from mathutils import Vector

DIR = Path(__file__).resolve().parent.parent / "SourceAssets/Ascensor2"
GRID = 0.05
CLEAR = 2.255          # m: del piso al techo por dentro (elevator2_build.json)
THICK = 0.02
WALLS = (("-X", 0, -1), ("+Y", 1, 1), ("-Y", 1, -1))   # el frente (+X) es la entrada

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(DIR / "SM_Ascensor2Cabina.fbx"))
for o in list(bpy.context.scene.objects):
    if o.type != "MESH" or o.name.startswith("UCX"):
        bpy.data.objects.remove(o)
cab = list(bpy.context.scene.objects)[0]
bpy.context.view_layer.objects.active = cab
cab.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me = cab.data
me.calc_loop_triangles()
co = np.array([v.co[:] for v in me.vertices])
lo, hi = co.min(0), co.max(0)

# color de los paneles: mediana de la textura en las caras de las paredes, abajo
image = next((n.image for m in me.materials if m and m.use_nodes for n in m.node_tree.nodes if n.type == "TEX_IMAGE"), None)
uv = me.uv_layers.active.data if me.uv_layers.active else None
samples = []


def inside(points, a, b, c):
    def side(p, q, r):
        return (p[..., 0] - r[0]) * (q[1] - r[1]) - (q[0] - r[0]) * (p[..., 1] - r[1])
    d1, d2, d3 = side(points, a, b), side(points, b, c), side(points, c, a)
    return ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))


bm = bmesh.new()
filled = {}
for name, axis, sign in WALLS:
    across = 1 if axis == 0 else 0
    U = np.arange(lo[across], hi[across], GRID) + GRID / 2
    Z = np.arange(0.0, CLEAR, GRID) + GRID / 2
    grid = np.zeros((len(Z), len(U)), bool)
    depths = []
    for t in me.loop_triangles:
        p = co[list(t.vertices)]
        n = np.array(t.normal[:])
        if abs(n[axis]) < 0.7 or np.sign(p[:, axis].mean()) != sign or abs(p[:, axis].mean()) < 0.4:
            continue
        depths.append(p[:, axis].mean())
        if image and uv is not None and p[:, 2].max() < 0.9 and len(samples) < 3000:
            for li in t.loops:
                u, v = uv[li].uv
                samples.append((u % 1, v % 1))
        a, b, c = p[:, [across, 2]]
        iu = np.where((U >= min(a[0], b[0], c[0])) & (U <= max(a[0], b[0], c[0])))[0]
        iz = np.where((Z >= min(a[1], b[1], c[1])) & (Z <= max(a[1], b[1], c[1])))[0]
        if len(iu) and len(iz):
            uu, zz = np.meshgrid(U[iu], Z[iz])
            grid[np.ix_(iz, iu)] |= inside(np.stack([uu, zz], -1), a, b, c)
    plane = float(np.median(depths))
    # entre los postes: de la primera a la ultima columna con algo
    cols = np.where(grid.any(0))[0]
    first, last = cols.min(), cols.max()
    boxes = 0
    for row in range(len(Z)):
        col = first
        while col <= last:
            if grid[row, col]:
                col += 1
                continue
            start = col
            while col <= last and not grid[row, col]:
                col += 1
            u0, u1 = U[start] - GRID / 2, U[col - 1] + GRID / 2
            z0, z1 = Z[row] - GRID / 2, Z[row] + GRID / 2
            lo3 = [0.0, 0.0, z0]
            hi3 = [0.0, 0.0, z1]
            lo3[axis], hi3[axis] = plane - THICK / 2, plane + THICK / 2
            lo3[across], hi3[across] = u0, u1
            made = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)["verts"]
            l3, h3 = Vector(lo3), Vector(hi3)
            for v in made:
                v.co = Vector((v.co.x * (h3.x - l3.x), v.co.y * (h3.y - l3.y), v.co.z * (h3.z - l3.z))) + (l3 + h3) / 2
            boxes += 1
    filled[name] = {"plane_m": round(plane, 3), "boxes": boxes, "open_cells": int((~grid[:, first:last + 1]).sum()),
                    "between_m": [round(float(U[first]), 2), round(float(U[last]), 2)]}

# un solo color de pared (srgb de la textura, a lineal)
color = (0.35, 0.36, 0.37)
if image and samples:
    W, H = image.size
    px = np.array(image.pixels[:]).reshape(H, W, 4)
    picks = np.array([px[int(v * (H - 1)), int(u * (W - 1)), :3] for u, v in samples])
    srgb = np.median(picks, axis=0)
    color = tuple(float(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) for c in srgb)
mat = bpy.data.materials.new("M_Ascensor2Relleno")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (*color, 1)
bsdf.inputs["Roughness"].default_value = 0.6
bsdf.inputs["Metallic"].default_value = 0.3
mesh = bpy.data.meshes.new("SM_Ascensor2Relleno")
bm.to_mesh(mesh)
bm.free()
mesh.materials.append(mat)
obj = bpy.data.objects.new("SM_Ascensor2Relleno", mesh)
bpy.context.scene.collection.objects.link(obj)
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.remove_doubles(threshold=0.001)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.export_scene.fbx(filepath=str(DIR / "SM_Ascensor2Relleno.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         axis_forward="-Y", axis_up="Z")
report = {"walls": filled, "color_linear": [round(c, 3) for c in color], "faces": len(mesh.polygons)}
(DIR / "elevator_paneles.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("PANELES_OK", json.dumps(report))
