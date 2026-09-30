"""Blender: tramo de calle para el recorrido de los camiones (28/09).

SM_CalleTramo: 2 m de largo a lo largo de +X (de x 0 a x 2), 3,8 m de ancho, 3 cm de alto (asfalto), con
banquina oscura a los costados, lineas blancas de borde y una linea central amarilla punteada (un trazo de
0,9 m por tramo). Subdividido a lo largo para que se curve bien: AFactoryVehiclePath lo repite con
SplineMeshComponents a lo largo de su linea (se reacomoda solo al mover los puntos). Sin colision.
Salida: SourceAssets/Calle/SM_CalleTramo.fbx.

blender -b --factory-startup -P Scripts/author_road.py
"""
import json
from pathlib import Path
import bmesh
import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Calle"
LENGTH, WIDTH, HEIGHT = 2.0, 3.8, 0.03
SLICES = 10

bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, rough=0.8):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    return m


asphalt = mat("M_CalleAsfalto", (0.055, 0.058, 0.066), 0.9)
gutter = mat("M_CalleBanquina", (0.03, 0.031, 0.035), 0.95)
white = mat("M_CalleLineaBlanca", (0.85, 0.85, 0.82), 0.6)
yellow = mat("M_CalleLineaAmarilla", (0.95, 0.68, 0.06), 0.6)
mats = [asphalt, gutter, white, yellow]
bm = bmesh.new()
bm.loops.layers.uv.new("UVMap")


def strip(y0, y1, z0, z1, x0, x1, material, slices):
    """A box from x0 to x1, cut into slices along X so the spline mesh can bend it."""
    for i in range(slices):
        a, b = x0 + (x1 - x0) * i / slices, x0 + (x1 - x0) * (i + 1) / slices
        vs = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)["verts"]
        lo, hi = Vector((a, y0, z0)), Vector((b, y1, z1))
        for v in vs:
            v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
        for f in {f for v in vs for f in v.link_faces}:
            f.material_index = mats.index(material)


w = WIDTH / 2
strip(-w + 0.12, w - 0.12, 0.0, HEIGHT, 0.0, LENGTH, asphalt, SLICES)
strip(-w, -w + 0.12, 0.0, HEIGHT - 0.005, 0.0, LENGTH, gutter, SLICES)
strip(w - 0.12, w, 0.0, HEIGHT - 0.005, 0.0, LENGTH, gutter, SLICES)
for side in (-1, 1):   # lineas de borde
    y = side * (w - 0.25)
    strip(y - 0.06, y + 0.06, HEIGHT, HEIGHT + 0.002, 0.0, LENGTH, white, SLICES)
strip(-0.06, 0.06, HEIGHT, HEIGHT + 0.002, 0.55, 1.45, yellow, 5)   # trazo central
me = bpy.data.meshes.new("SM_CalleTramo")
bm.to_mesh(me); bm.free()
for m in mats:
    me.materials.append(m)
obj = bpy.data.objects.new("SM_CalleTramo", me)
bpy.context.scene.collection.objects.link(obj)
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.fbx(filepath=str(OUT / "SM_CalleTramo.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         axis_forward="-Y", axis_up="Z")
report = {"length_m": LENGTH, "width_m": WIDTH, "faces": len(me.polygons)}
(OUT / "calle_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("CALLE_OK", json.dumps(report))
