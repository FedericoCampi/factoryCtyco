"""Blender: rampa con plataforma para que el camion volcador descargue en las tolvas (08/10).

Una plataforma de hormigon a la altura justa para que el borde de la caja del camion (0,80 m sobre las ruedas) quede
sobre la boca de la tolva, y una rampa que baja hasta el piso del patio. Muretes a los costados y un tope amarillo y
negro en el borde de la tolva (las ruedas traseras quedan contra el). Una sola malla; en Unreal choca con su propia malla
(se camina).
Origen: en el medio del borde de la plataforma que da a la tolva, al nivel del piso; la rampa baja hacia +X.
Salida: SourceAssets/RampaTolvas/SM_RampaTolvas.fbx y rampa_tolvas_build.json (las medidas: apply_rampa_tolvas.py).

blender -b --factory-startup -P Scripts/author_rampa_tolvas.py
"""
import json
from pathlib import Path
import bmesh
import bpy

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/RampaTolvas"
HEIGHT = 2.20        # plataforma sobre el piso del patio: boca de la tolva (2,90 sobre el piso) + 0,10 - 0,80 de la caja
PLATFORM = 4.6       # largo de la plataforma (el camion estacionado: eje trasero a 0,6 m del borde, delantero a 3,94)
RAMP = 10.5          # largo de la rampa (21 %)
INNER = 3.5          # ancho entre muretes (el camion mide 2,1)
WALL = 0.25          # espesor de los muretes
PARAPET = 0.8        # alto de los muretes sobre el piso de la plataforma y de la rampa
CURB = (0.0, 0.2, 0.15)   # tope en el borde: desde x, hasta x, alto
STRIPE = 0.35        # largo de cada franja amarilla o negra del tope

bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, color, rough=0.85, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


MATS = [material("M_RampaHormigon", (0.36, 0.35, 0.33)), material("M_RampaMuro", (0.55, 0.54, 0.5)),
        material("M_RampaAmarillo", (0.85, 0.62, 0.05), 0.6), material("M_RampaNegro", (0.03, 0.03, 0.03), 0.6)]
me = bpy.data.meshes.new("SM_RampaTolvas")
for m in MATS:
    me.materials.append(m)
bm = bmesh.new()


def prism(bottom, top, mat):
    """Solido de 8 vertices: bottom y top son 4 puntos (x, y, z) cada uno, en el mismo orden (antihorario visto de arriba)."""
    v = [bm.verts.new(p) for p in bottom + top]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    for f in faces:
        bm.faces.new([v[i] for i in f]).material_index = mat


def block(x0, x1, y0, y1, z0, z1, mat):
    prism([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
          [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], mat)


def slope(x0, x1, y0, y1, z0, top0, top1, mat):
    """Bloque de x0 a x1 con la cara de arriba en pendiente: alto top0 en x0 y top1 en x1 (abajo en z0)."""
    prism([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
          [(x0, y0, top0), (x1, y0, top1), (x1, y1, top1), (x0, y1, top0)], mat)


HALF = INNER / 2
END = PLATFORM + RAMP
# piso de la plataforma y de la rampa (hormigon), un poco bajo el piso del patio para que no quede una ranura
block(0, PLATFORM, -HALF, HALF, -0.05, HEIGHT, 0)
slope(PLATFORM, END, -HALF, HALF, -0.05, HEIGHT, 0.0, 0)
# muretes: hasta PARAPET sobre la superficie, a los dos lados, por toda la plataforma y la rampa
for y0, y1 in ((-HALF - WALL, -HALF), (HALF, HALF + WALL)):
    block(0, PLATFORM, y0, y1, -0.05, HEIGHT + PARAPET, 1)
    slope(PLATFORM, END, y0, y1, -0.05, HEIGHT + PARAPET, PARAPET, 1)
# tope del borde, en franjas amarillas y negras
x0, x1, h = CURB
count = max(1, round(INNER / STRIPE))
for i in range(count):
    a, b = -HALF + INNER * i / count, -HALF + INNER * (i + 1) / count
    block(x0, x1, a, b, HEIGHT, HEIGHT + h, 2 if i % 2 == 0 else 3)
bm.normal_update()
bm.to_mesh(me)
bm.free()
# UV simples (proyeccion de cubo) para que Unreal no se queje
obj = bpy.data.objects.new("SM_RampaTolvas", me)
bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.cube_project(cube_size=1.0)
bpy.ops.object.mode_set(mode="OBJECT")

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(OUT / "SM_RampaTolvas.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         axis_forward="-Y", axis_up="Z")
report = {"height_m": HEIGHT, "platform_m": PLATFORM, "ramp_m": RAMP, "grade": round(HEIGHT / RAMP, 3), "inner_m": INNER,
          "wall_m": WALL, "parapet_m": PARAPET, "curb_m": list(CURB), "size_m": [END, INNER + 2 * WALL, HEIGHT + PARAPET],
          "triangles": sum(len(p.vertices) - 2 for p in me.polygons)}
(OUT / "rampa_tolvas_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("RAMPA_TOLVAS_OK", json.dumps(report))
