"""Blender: prepara el tubo de descarga con tolva del usuario (3D assets/GLBs/Tubo de descarga...glb) para Unreal (01/10).

El GLB viene normalizado (1 m de largo, ~700 000 triangulos, una sola malla con 4 texturas de 2-4K). Se lleva a
LENGTH_M de largo, origen al centro del piso, se reduce a ~150 000 triangulos y se le agrega una colision UCX de caja
(un poco adentro del contorno). Mismo camino que author_horno_fundicion.py.
Desde el 02/10 el caño va abierto: se le saca la mitad de arriba (corte por el eje del caño, que baja unos 6 grados
hacia la boca) desde CUT_FROM_X hasta la boca, para que se vea bajar el liquido; la tolva queda entera. Las caras que quedan
se duplican dadas vuelta para que el interior se vea. La boca de salida (centro y radio) va a tubo_build.json: con eso
apply_linea_descarga.py le alinea el codo.
Salida: SourceAssets/TuboDescarga/SM_TuboDescarga.fbx y tubo_build.json.

blender -b --factory-startup -P Scripts/author_tubo_descarga.py
"""
import json
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

SRC = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/Tubo de descarga con tolva industrial-complete.glb")
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/TuboDescarga"
NAME = "SM_TuboDescarga"
LENGTH_M = 2.0     # lo mas largo (X); queda ~0,9 m de alto y ~0,6 m de ancho
DECIMATE = 0.22    # ~700k -> ~150k triangulos
INSET = 0.02       # la caja de colision queda 2 cm adentro del contorno
CUT_FROM_X = -0.28 # m: el caño abierto empieza despues de la tolva (la tolva termina en ~-0,3)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
o = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
bpy.ops.object.select_all(action="DESELECT")
o.select_set(True)
bpy.context.view_layer.objects.active = o
o.parent = None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for extra in [x for x in bpy.context.scene.objects if x is not o]:
    bpy.data.objects.remove(extra)
tris_in = sum(len(p.vertices) - 2 for p in o.data.polygons)

co = [v.co for v in o.data.vertices]
lo = Vector([min(c[i] for c in co) for i in range(3)])
hi = Vector([max(c[i] for c in co) for i in range(3)])
scale = LENGTH_M / max(hi[i] - lo[i] for i in range(3))
o.data.transform(Matrix.Scale(scale, 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
dec = o.modifiers.new("Decimate", "DECIMATE")
dec.ratio = DECIMATE
bpy.ops.object.modifier_apply(modifier=dec.name)
o.name = o.data.name = NAME
size = [round((hi[i] - lo[i]) * scale, 3) for i in range(3)]


def end_port(mesh, depth=0.02):
    """Boca de salida (+X): centro y radio del anillo de vertices de la punta."""
    pts = [v.co for v in mesh.vertices]
    end = max(c.x for c in pts)
    ring = [c for c in pts if c.x > end - depth]
    y0, y1 = min(c.y for c in ring), max(c.y for c in ring)
    z0, z1 = min(c.z for c in ring), max(c.z for c in ring)
    return Vector((end, (y0 + y1) / 2, (z0 + z1) / 2)), max(y1 - y0, z1 - z0) / 2


def pipe_axis(mesh, x0, x1, n=8, depth=0.01):
    """Recta z = a + m x del eje del caño: centro en z de cortes finos entre x0 y x1 (sin el pie ni la tolva)."""
    pts = [v.co for v in mesh.vertices]
    samples = []
    for i in range(n):
        x = x0 + (x1 - x0) * i / (n - 1)
        zs = [c.z for c in pts if abs(c.x - x) < depth]
        samples.append((x, (min(zs) + max(zs)) / 2))
    mx, mz = sum(x for x, _ in samples) / n, sum(z for _, z in samples) / n
    m = sum((x - mx) * (z - mz) for x, z in samples) / sum((x - mx) ** 2 for x, _ in samples)
    return mz - m * mx, m


def open_top(mesh, a, m, x_from):
    """Saca la mitad de arriba (sobre el plano del eje z = a + m x) del tramo x > x_from y duplica dado vuelta lo que
    queda de ese tramo."""
    b = bmesh.new()
    b.from_mesh(mesh)
    bmesh.ops.bisect_plane(b, geom=b.verts[:] + b.edges[:] + b.faces[:], plane_co=(x_from, 0, 0), plane_no=(1, 0, 0))
    region = lambda: [f for f in b.faces if f.calc_center_median().x > x_from]
    part = region()
    co, no = Vector((0, 0, a)), Vector((-m, 0, 1)).normalized()
    bmesh.ops.bisect_plane(b, geom=list({v for f in part for v in f.verts}) + list({e for f in part for e in f.edges}) + part,
                           plane_co=co, plane_no=no)
    bmesh.ops.delete(b, geom=[f for f in region() if (f.calc_center_median() - co).dot(no) > 0], context="FACES_ONLY")
    inside = bmesh.ops.duplicate(b, geom=region())["geom"]
    bmesh.ops.reverse_faces(b, faces=[g for g in inside if isinstance(g, bmesh.types.BMFace)])
    b.to_mesh(mesh)
    b.free()


port, port_r = end_port(o.data)
axis_a, axis_m = pipe_axis(o.data, 0.3, 0.9)   # el pie esta entre -0,2 y 0,2
port.z = axis_a + axis_m * port.x               # centro de la boca sobre el eje
open_top(o.data, axis_a, axis_m, CUT_FROM_X)

me = bpy.data.meshes.new(f"UCX_{NAME}_00")
b = bmesh.new()
for v in bmesh.ops.create_cube(b, size=1.0)["verts"]:
    v.co = Vector((v.co.x * (size[0] - 2 * INSET), v.co.y * (size[1] - 2 * INSET), (v.co.z + 0.5) * (size[2] - INSET)))
b.to_mesh(me)
b.free()
ucx = bpy.data.objects.new(me.name, me)
bpy.context.scene.collection.objects.link(ucx)

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
o.select_set(True)
ucx.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         path_mode="COPY", embed_textures=True, axis_forward="-Y", axis_up="Z")
tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
(OUT / "tubo_build.json").write_text(json.dumps({
    "source": str(SRC), "length_m": LENGTH_M, "size_m": size, "scale": round(scale, 4),
    "triangles_in": tris_in, "triangles": tris, "materials": [m.name for m in o.data.materials if m],
    "ucx": 1, "cut_from_x_m": CUT_FROM_X,
    # en Unreal (cm, Y invertida): centro de la boca de salida, que mira a +X
    "outlet_cm": [round(port.x * 100, 1), round(-port.y * 100, 1), round(port.z * 100, 1)], "outlet_radius_cm": round(port_r * 100, 1),
    "outlet_slope_deg": round(math.degrees(math.atan(axis_m)), 2)},
    indent=1), encoding="utf-8")
print("TUBO_OK", size, tris, port, port_r)
