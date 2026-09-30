"""Blender: cinta de carga del camion (28/09).

SM_CintaCarga: cinta de rodillos de 3 m (+X, desde la punta de carga en x 0 hasta la del camion),
0,8 m de ancho, rodillos arriba a 0,88 m (el piso de la caja del camion esta a 0,99 m). Barandas
naranjas a los costados, patas y una bandeja amarilla en la punta de carga. Los rodillos usan la
ranura M_Rodillo (en Unreal, M_DespachoRodillo: giran con su parametro Velocidad). UCX: la cinta entera.
Origen: centro de la punta de carga, al piso. Salida: SourceAssets/CintaCarga/SM_CintaCarga.fbx.

blender -b --factory-startup -P Scripts/author_loading_belt.py
"""
import json
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/CintaCarga"
NAME = "SM_CintaCarga"
LENGTH, WIDTH, DECK = 3.0, 0.8, 0.88
ROLLER_R, ROLLER_STEP = 0.035, 0.11

bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, rough=0.5, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


steel = mat("M_CintaAcero", (0.07, 0.08, 0.1), 0.45, 0.8)
orange = mat("M_CintaNaranja", (0.85, 0.32, 0.04))
yellow = mat("M_CintaAmarillo", (0.85, 0.62, 0.04))
roller = mat("M_Rodillo", (0.5, 0.5, 0.52), 0.35, 0.85)
mats = [steel, orange, yellow, roller]

me = bpy.data.meshes.new(NAME)
bm = bmesh.new()
uv = bm.loops.layers.uv.new("UVMap")


def box(lo, hi, material):
    lo, hi = Vector(lo), Vector(hi)
    vs = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)["verts"]
    for v in vs:
        v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = mats.index(material)


w = WIDTH / 2
top = DECK - ROLLER_R
# largueros y barandas
for side in (-1, 1):
    y0, y1 = sorted((side * (w - 0.05), side * w))
    box((0, y0, top - 0.14), (LENGTH, y1, top + 0.02), steel)
    box((0, y0, DECK + 0.03), (LENGTH, y1, DECK + 0.07), orange)
    for x in (0.05, LENGTH / 2, LENGTH - 0.08):                 # postes de la baranda
        box((x, y0, top), (x + 0.03, y1, DECK + 0.03), steel)
# patas y travesanos
for x in (0.1, LENGTH / 2 - 0.03, LENGTH - 0.16):
    for side in (-1, 1):
        box((x, side * (w - 0.1) - 0.03, 0), (x + 0.06, side * (w - 0.1) + 0.03, top - 0.14), steel)
    box((x, -w + 0.1, 0.12), (x + 0.06, w - 0.1, 0.17), steel)
    box((x - 0.04, -w + 0.05, 0), (x + 0.1, w - 0.05, 0.02), steel)       # pie
# bandeja de carga amarilla (punta de carga)
box((-0.18, -w, top - 0.02), (0.0, w, DECK - 0.005), yellow)
# rodillos: cilindros a lo ancho con UV alrededor del tubo (el material franjea U)
n = int((LENGTH - 0.06) / ROLLER_STEP)
for i in range(n + 1):
    x = 0.04 + i * ROLLER_STEP
    made = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=ROLLER_R, radius2=ROLLER_R,
                                 depth=WIDTH - 0.1, calc_uvs=True,
                                 matrix=Matrix.Translation((x, 0, top)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    for f in {f for v in made["verts"] for f in v.link_faces}:
        f.material_index = mats.index(roller)
bm.to_mesh(me); bm.free()
for m in mats:
    me.materials.append(m)
obj = bpy.data.objects.new(NAME, me)
bpy.context.scene.collection.objects.link(obj)
# colision
cm = bpy.data.meshes.new(f"UCX_{NAME}_00")
b = bmesh.new(); vs = bmesh.ops.create_cube(b, size=1.0)["verts"]
lo, hi = Vector((-0.18, -w, 0)), Vector((LENGTH, w, DECK + 0.07))
for v in vs:
    v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
b.to_mesh(cm); b.free()
bpy.context.scene.collection.objects.link(bpy.data.objects.new(cm.name, cm))

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         axis_forward="-Y", axis_up="Z")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "CintaCarga.blend"))
report = {"length_m": LENGTH, "width_m": WIDTH, "deck_m": DECK, "rollers": n + 1, "faces": len(me.polygons)}
(OUT / "cinta_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("CINTA_OK", json.dumps(report))
