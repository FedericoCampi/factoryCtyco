"""Blender: estacionamiento de empleados al aire libre, el piso 3 del ascensor (28/09).

Piezas (FBX en SourceAssets/Empleados, metros; +X de Blender = +X de Unreal, Unreal y = -Blender y; origen en el
centro de la playa, a nivel del pasto):
- SM_EmpleadosPiso: pasto grande alrededor (62 x 48 m), playa de asfalto (x -16..9,5, y -11..11) con dos filas de
  cajones pintados, flechas hacia el ascensor, senda peatonal, calle de entrada por el oeste, y la vereda del
  ascensor (x 9,5..16,5, y -6..6, 14 cm) con el agujero del pozo en (13, 0) (medio tubo del ascensor2). UCX: pasto y
  vereda partidos alrededor del agujero, y paredes invisibles en el perimetro (no se sale de la playa).
- SM_EmpleadosDecor: cerco de arbustos alrededor (con el hueco de la entrada), faroles, arboles y un banco.
- SM_AutoEmpleado_<Color>: auto estacionado simple (4,3 m, mira a +X), cuatro colores. UCX: la carroceria.
Informe: SourceAssets/Empleados/empleados_build.json (incluye los centros de los cajones).

blender -b --factory-startup -P Scripts/author_employee_parking.py
"""
import json
import math
import random
from pathlib import Path
import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "SourceAssets/Empleados"
random.seed(11)
build = json.loads((ROOT / "SourceAssets/Ascensor2/elevator2_build.json").read_text())
HX, HY = build["tube"]["hole_half_m"]
ELEVATOR = (13.0, 0.0)
PLAZA_TOP = 0.14
LOT = (-16.0, 9.5, -11.0, 11.0)
PLAZA = (9.5, 16.5, -6.0, 6.0)
STALL_W, STALL_D = 2.6, 5.0
STALL_X0 = -15.0
STALLS = 9
HOLE = (ELEVATOR[0] - HX, ELEVATOR[0] + HX, ELEVATOR[1] - HY, ELEVATOR[1] + HY)

bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, rough=0.8, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


M = {
    "pasto": mat("M_EmpPasto", (0.16, 0.34, 0.10), 0.95),
    "asfalto": mat("M_EmpAsfalto", (0.07, 0.075, 0.085), 0.9),
    "vereda": mat("M_EmpVereda", (0.55, 0.54, 0.50), 0.85),
    "cordon": mat("M_EmpCordon", (0.75, 0.74, 0.70), 0.8),
    "blanco": mat("M_EmpPintura", (0.88, 0.88, 0.85), 0.6),
    "amarillo": mat("M_EmpAmarillo", (0.95, 0.70, 0.08), 0.6),
    "arbusto": mat("M_EmpArbusto", (0.08, 0.24, 0.07), 0.9),
    "tronco": mat("M_EmpTronco", (0.26, 0.16, 0.09), 0.9),
    "copa": mat("M_EmpCopa", (0.12, 0.33, 0.10), 0.9),
    "metal": mat("M_EmpMetal", (0.18, 0.19, 0.21), 0.4, 0.8),
    "luz": mat("M_EmpLuz", (1.0, 0.95, 0.75), 0.3),
    "madera": mat("M_EmpMadera", (0.45, 0.28, 0.14), 0.8),
}


class Mesh:
    """A bmesh collecting boxes and shapes with a material each."""

    def __init__(self, name):
        self.name, self.bm, self.mats = name, bmesh.new(), []

    def slot(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def box(self, lo, hi, m, rot_z=0.0, pivot=None):
        vs = bmesh.ops.create_cube(self.bm, size=1.0)["verts"]
        lo, hi = Vector(lo), Vector(hi)
        for v in vs:
            v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
        self._finish(vs, m, rot_z, pivot)

    def cyl(self, centre, radius, height, m, segments=12, axis="Z"):
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, segments=segments, radius1=radius, radius2=radius, depth=height)
        vs = res["verts"]
        for v in vs:
            if axis == "Y":
                v.co = Vector((v.co.x, v.co.z, v.co.y))
            v.co += Vector(centre)
        self._finish(vs, m)

    def ball(self, centre, radius, m, squash=1.0, subdiv=2):
        vs = bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=radius)["verts"]
        for v in vs:
            v.co = Vector((v.co.x * (1 + random.uniform(-.08, .08)), v.co.y * (1 + random.uniform(-.08, .08)), v.co.z * squash)) + Vector(centre)
        self._finish(vs, m)

    def poly(self, points, z0, z1, m):
        """A prism from a 2D outline (counter-clockwise), for arrows."""
        bottom = [self.bm.verts.new((x, y, z0)) for x, y in points]
        top = [self.bm.verts.new((x, y, z1)) for x, y in points]
        faces = [self.bm.faces.new(top), self.bm.faces.new(list(reversed(bottom)))]
        n = len(points)
        for i in range(n):
            faces.append(self.bm.faces.new((bottom[i], bottom[(i + 1) % n], top[(i + 1) % n], top[i])))
        for f in faces:
            f.material_index = self.slot(m)

    def _finish(self, vs, m, rot_z=0.0, pivot=None):
        if rot_z:
            c = Vector(pivot) if pivot else sum((v.co for v in vs), Vector()) / len(vs)
            cs, sn = math.cos(rot_z), math.sin(rot_z)
            for v in vs:
                d = v.co - c
                v.co = c + Vector((d.x * cs - d.y * sn, d.x * sn + d.y * cs, d.z))
        for f in {f for v in vs for f in v.link_faces}:
            f.material_index = self.slot(m)

    def build(self):
        me = bpy.data.meshes.new(self.name)
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        o = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(o)
        return o


def ucx(owner, index, lo, hi):
    b = bmesh.new()
    vs = bmesh.ops.create_cube(b, size=1.0)["verts"]
    lo, hi = Vector(lo), Vector(hi)
    for v in vs:
        v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
    me = bpy.data.meshes.new(f"UCX_{owner}_{index:02d}")
    b.to_mesh(me)
    b.free()
    o = bpy.data.objects.new(me.name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def around_hole(x0, x1, y0, y1):
    """The rectangle minus the elevator hole, as up to four rectangles."""
    hx0, hx1, hy0, hy1 = HOLE
    if x1 <= hx0 or x0 >= hx1 or y1 <= hy0 or y0 >= hy1:
        return [(x0, x1, y0, y1)]
    parts = [(x0, hx0, y0, y1), (hx1, x1, y0, y1), (hx0, hx1, y0, hy0), (hx0, hx1, hy1, y1)]
    return [p for p in parts if p[1] - p[0] > 1e-3 and p[3] - p[2] > 1e-3]


def export(objects, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / f"{name}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                             axis_forward="-Y", axis_up="Z")


OUT.mkdir(parents=True, exist_ok=True)
report = {}

# ------------------------------------------------------------------ piso
floor = Mesh("SM_EmpleadosPiso")
floor_ucx = []
GRASS = (-31.0, 31.0, -24.0, 24.0)
for x0, x1, y0, y1 in around_hole(*GRASS):
    floor.box((x0, y0, -0.3), (x1, y1, 0.0), M["pasto"])
    floor_ucx.append(((x0, y0, -0.3), (x1, y1, 0.0)))
lx0, lx1, ly0, ly1 = LOT
floor.box((lx0, ly0, 0.0), (lx1, ly1, 0.02), M["asfalto"])
floor.box((-31.0, -3.2, 0.0), (lx0, 3.2, 0.02), M["asfalto"])                  # calle de entrada (oeste)
for y in (-3.2, 3.2):                                                             # bordes de la calle
    floor.box((-31.0, y - 0.08, 0.02), (lx0, y + 0.08, 0.026), M["blanco"])
px0, px1, py0, py1 = PLAZA
for x0, x1, y0, y1 in around_hole(*PLAZA):
    floor.box((x0, y0, 0.0), (x1, y1, PLAZA_TOP), M["vereda"])
    floor_ucx.append(((x0, y0, 0.0), (x1, y1, PLAZA_TOP)))
floor.box((px0 - 0.15, py0, 0.0), (px0, py1, PLAZA_TOP + 0.01), M["cordon"])       # cordon del lado de la playa
for gx in range(int(px0) + 1, int(px1)):                                          # juntas de la vereda
    for x0, x1, y0, y1 in around_hole(gx - 0.01, gx + 0.01, py0, py1):
        floor.box((x0, y0, PLAZA_TOP), (x1, y1, PLAZA_TOP + 0.002), M["cordon"])
# cajones: dos filas contra los bordes norte y sur
stalls = []
for side in (1, -1):
    y_in, y_out = side * (ly1 - STALL_D), side * ly1
    for i in range(STALLS + 1):
        x = STALL_X0 + STALL_W * i
        floor.box((x - 0.06, min(y_in, y_out), 0.02), (x + 0.06, max(y_in, y_out), 0.026), M["blanco"])
    for i in range(STALLS):
        stalls.append({"x": STALL_X0 + STALL_W * (i + 0.5), "y": side * (ly1 - STALL_D / 2), "side": side})
    floor.box((STALL_X0, y_in - side * 0.06 - 0.06, 0.02), (STALL_X0 + STALL_W * STALLS, y_in - side * 0.06 + 0.06, 0.026), M["blanco"])
# flechas hacia el ascensor y senda peatonal hasta la vereda
for ax in (-11.0, -3.0):
    arrow = [(ax - 1.4, -0.18), (ax + 0.5, -0.18), (ax + 0.5, -0.55), (ax + 1.4, 0.0), (ax + 0.5, 0.55), (ax + 0.5, 0.18), (ax - 1.4, 0.18)]
    floor.poly(arrow, 0.02, 0.026, M["blanco"])
for i in range(7):
    y = -2.1 + i * 0.7
    floor.box((6.6, y, 0.02), (9.3, y + 0.38, 0.026), M["blanco"])
# cartel pintado en el piso delante del ascensor: una franja amarilla (el texto lo pone Unreal)
floor.box((4.0, -1.6, 0.02), (6.2, 1.6, 0.024), M["amarillo"])
floor.box((4.1, -1.5, 0.024), (6.1, 1.5, 0.026), M["asfalto"])
# paredes invisibles: no se sale de la playa (la calle de entrada es solo para autos)
for lo, hi in (((-17.6, -13.2, 0), (-17.2, 13.2, 1.6)), ((17.2, -13.2, 0), (17.6, 13.2, 1.6)),
               ((-17.6, -13.2, 0), (17.6, -12.8, 1.6)), ((-17.6, 12.8, 0), (17.6, 13.2, 1.6))):
    floor_ucx.append((lo, hi))
floor_obj = floor.build()
floor_parts = [floor_obj] + [ucx("SM_EmpleadosPiso", i, lo, hi) for i, (lo, hi) in enumerate(floor_ucx)]
export(floor_parts, "SM_EmpleadosPiso")
report["SM_EmpleadosPiso"] = {"faces": len(floor_obj.data.polygons), "ucx": len(floor_ucx)}

# ------------------------------------------------------------------ decoracion
decor = Mesh("SM_EmpleadosDecor")
decor_ucx = []


def hedge(x0, x1, y0, y1):
    """A row of hedge: a box with some lumps on top."""
    decor.box((x0, y0, 0.0), (x1, y1, 0.8), M["arbusto"])
    length = max(x1 - x0, y1 - y0)
    for k in range(int(length / 1.2)):
        t = (k + 0.5) / int(length / 1.2)
        c = (x0 + (x1 - x0) * t if x1 - x0 > y1 - y0 else (x0 + x1) / 2,
             y0 + (y1 - y0) * t if y1 - y0 >= x1 - x0 else (y0 + y1) / 2, 0.78)
        decor.ball(c, 0.55, M["arbusto"], squash=0.55, subdiv=1)


hedge(-17.8, 17.8, 12.9, 13.7)
hedge(-17.8, 17.8, -13.7, -12.9)
hedge(17.0, 17.8, -12.9, 12.9)
hedge(-17.8, -17.0, 3.4, 12.9)       # oeste, con el hueco de la entrada (y -3,2..3,2)
hedge(-17.8, -17.0, -12.9, -3.4)
for x, y in ((px0 + 0.4, py0 + 0.4), (px0 + 0.4, py1 - 0.4), (px1 - 0.4, py0 + 0.4), (px1 - 0.4, py1 - 0.4),
             (-15.6, 0.0), (-4.0, 0.0)):
    z0 = PLAZA_TOP if x > px0 else 0.02
    decor.cyl((x, y, z0 + 2.5), 0.08, 5.0, M["metal"])
    decor.box((x - 0.5, y - 0.12, z0 + 4.9), (x + 0.1, y + 0.12, z0 + 5.05), M["metal"])
    decor.box((x - 0.45, y - 0.1, z0 + 4.85), (x + 0.05, y + 0.1, z0 + 4.9), M["luz"])
    decor_ucx.append(((x - 0.1, y - 0.1, z0), (x + 0.1, y + 0.1, z0 + 3.0)))
for x, y in ((-22, -16), (-12, -17), (-3, -18.5), (8, -16.5), (21, -15), (23, 2), (21, 16), (9, 17.5), (-4, 16.8),
             (-14, 18), (-24, 15), (-25, -8), (26, -6), (-21, 8)):
    h = random.uniform(2.2, 3.2)
    decor.cyl((x, y, h / 2), 0.18, h, M["tronco"], segments=8)
    decor.ball((x, y, h + 0.6), random.uniform(1.3, 1.8), M["copa"], squash=0.85)
    decor.ball((x + 0.6, y + 0.4, h + 1.2), random.uniform(0.9, 1.2), M["copa"], squash=0.85)
# banco en la vereda, mirando a la playa
bx, by = 15.4, 4.2
decor.box((bx - 0.25, by - 0.9, PLAZA_TOP + 0.42), (bx + 0.25, by + 0.9, PLAZA_TOP + 0.48), M["madera"])
decor.box((bx + 0.2, by - 0.9, PLAZA_TOP + 0.5), (bx + 0.26, by + 0.9, PLAZA_TOP + 0.9), M["madera"])
for y in (by - 0.75, by + 0.75):
    decor.box((bx - 0.22, y - 0.04, PLAZA_TOP), (bx + 0.22, y + 0.04, PLAZA_TOP + 0.42), M["metal"])
decor_ucx.append(((bx - 0.3, by - 0.95, PLAZA_TOP), (bx + 0.3, by + 0.95, PLAZA_TOP + 0.9)))
decor_obj = decor.build()
decor_parts = [decor_obj] + [ucx("SM_EmpleadosDecor", i, lo, hi) for i, (lo, hi) in enumerate(decor_ucx)]
export(decor_parts, "SM_EmpleadosDecor")
report["SM_EmpleadosDecor"] = {"faces": len(decor_obj.data.polygons), "ucx": len(decor_ucx)}

# ------------------------------------------------------------------ autos
COLORS = {"Rojo": (0.55, 0.05, 0.05), "Azul": (0.05, 0.16, 0.45), "Blanco": (0.82, 0.82, 0.80), "Gris": (0.25, 0.26, 0.28)}
glass = mat("M_AutoEmpVidrio", (0.05, 0.08, 0.12), 0.1, 0.3)
tyre = mat("M_AutoEmpGoma", (0.02, 0.02, 0.02), 0.9)
rim = mat("M_AutoEmpLlanta", (0.6, 0.6, 0.62), 0.3, 0.9)
head = mat("M_AutoEmpFaro", (1.0, 0.97, 0.85), 0.2)
tail = mat("M_AutoEmpStop", (0.7, 0.03, 0.03), 0.3)
for color, rgb in COLORS.items():
    name = f"SM_AutoEmpleado_{color}"
    car = Mesh(name)
    paint = mat(f"M_AutoEmp{color}", rgb, 0.35, 0.4)
    car.box((-2.15, -0.88, 0.32), (2.15, 0.88, 0.82), paint)                     # carroceria
    car.box((-2.05, -0.84, 0.26), (2.05, 0.84, 0.34), M["metal"])                # zocalo
    car.box((-1.05, -0.8, 0.82), (1.0, 0.8, 1.32), glass)                         # habitaculo (vidrios)
    car.box((-0.95, -0.72, 1.32), (0.85, 0.72, 1.38), paint)                      # techo
    for x in (1.0, -1.05):                                                         # parantes
        for y in (-0.8, 0.74):
            car.box((x - 0.05, y, 0.82), (x + 0.05, y + 0.06, 1.34), paint)
    for x in (1.35, -1.35):
        for y in (-0.82, 0.82):
            car.cyl((x, y, 0.33), 0.33, 0.24, tyre, segments=14, axis="Y")
            car.cyl((x, y * 1.02, 0.33), 0.19, 0.24, rim, segments=10, axis="Y")
    for y in (-0.6, 0.6):
        car.box((2.13, y - 0.2, 0.62), (2.17, y + 0.2, 0.74), head)
        car.box((-2.17, y - 0.22, 0.62), (-2.13, y + 0.22, 0.72), tail)
    obj = car.build()
    export([obj, ucx(name, 0, (-2.2, -0.9, 0.1), (2.2, 0.9, 1.35))], name)
    report[name] = {"faces": len(obj.data.polygons)}
report["stalls"] = stalls
report["elevator_m"] = [ELEVATOR[0], ELEVATOR[1], PLAZA_TOP]
report["hole_half_m"] = [HX, HY]
(OUT / "empleados_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("EMPLEADOS_OK", json.dumps({k: v for k, v in report.items() if k != "stalls"}))
