"""Blender: caño recto para la linea de descarga (02/10), hecho del tubo de descarga del usuario sin el pie ni la tolva.

Del GLB del tubo (mismo camino que author_tubo_descarga.py: 2 m de largo, ~150 000 triangulos) se queda solo el caño
desde la brida que lo une a la tolva hasta la boca. El caño del modelo baja ~5,4 grados: se endereza (eje horizontal),
se le saca el pie (lo que queda por debajo del caño) y la mitad de arriba (abierto, como el tubo y el codo), y lo que
queda se duplica dado vuelta para que el interior se vea.
Origen en el centro de la entrada (la brida), el caño hacia +X y su eje en z = 0: se estira en X para cada tramo.
Salida: SourceAssets/CanoRecto/SM_CanoRecto.fbx y cano_build.json (largo y radio de la boca).

blender -b --factory-startup -P Scripts/author_cano_recto.py
"""
import json
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

SRC = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/Tubo de descarga con tolva industrial-complete.glb")
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/CanoRecto"
NAME = "SM_CanoRecto"
LENGTH_M = 2.0     # el tubo entero, como Tubo_Descarga: el caño sale del mismo tamaño
DECIMATE = 0.22
START_X = -0.27    # m: empieza en la brida de la tolva (la tolva termina en ~-0,3)
BELOW = 0.2        # m: lo que esta mas de esto por debajo del eje es el pie

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
co = [v.co for v in o.data.vertices]
lo = Vector([min(c[i] for c in co) for i in range(3)])
hi = Vector([max(c[i] for c in co) for i in range(3)])
scale = LENGTH_M / max(hi[i] - lo[i] for i in range(3))
o.data.transform(Matrix.Scale(scale, 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
dec = o.modifiers.new("Decimate", "DECIMATE")
dec.ratio = DECIMATE
bpy.ops.object.modifier_apply(modifier=dec.name)
o.name = o.data.name = NAME


def pipe_axis(mesh, x0, x1, n=8, depth=0.01):
    """Recta z = a + m x del eje del caño (como en author_tubo_descarga.py)."""
    pts = [v.co for v in mesh.vertices]
    samples = []
    for i in range(n):
        x = x0 + (x1 - x0) * i / (n - 1)
        zs = [c.z for c in pts if abs(c.x - x) < depth]
        samples.append((x, (min(zs) + max(zs)) / 2))
    mx, mz = sum(x for x, _ in samples) / n, sum(z for _, z in samples) / n
    m = sum((x - mx) * (z - mz) for x, z in samples) / sum((x - mx) ** 2 for x, _ in samples)
    return mz - m * mx, m


a, m = pipe_axis(o.data, 0.3, 0.9)
b = bmesh.new()
b.from_mesh(o.data)
# solo el caño: afuera la tolva (antes de START_X) y el pie (muy por debajo del eje)
bmesh.ops.bisect_plane(b, geom=b.verts[:] + b.edges[:] + b.faces[:], plane_co=(START_X, 0, 0), plane_no=(1, 0, 0))
drop = [f for f in b.faces if f.calc_center_median().x < START_X
        or f.calc_center_median().z < a + m * f.calc_center_median().x - BELOW]
bmesh.ops.delete(b, geom=drop, context="FACES")
# enderezar: el eje queda horizontal, en z = 0, y la entrada en x = 0
bmesh.ops.transform(b, matrix=Matrix.Rotation(math.atan(m), 4, "Y") @ Matrix.Translation((-START_X, 0, -(a + m * START_X))),
                    verts=b.verts[:])
# fuera las piezas sueltas que queden lejos del caño (restos del pie)
bmesh.ops.delete(b, geom=[v for v in b.verts if math.hypot(v.co.y, v.co.z) > 0.3], context="VERTS")
# abierto arriba y con el interior visible
bmesh.ops.bisect_plane(b, geom=b.verts[:] + b.edges[:] + b.faces[:], plane_co=(0, 0, 0), plane_no=(0, 0, 1))
bmesh.ops.delete(b, geom=[f for f in b.faces if f.calc_center_median().z > 0], context="FACES_ONLY")
inside = bmesh.ops.duplicate(b, geom=b.faces[:])["geom"]
bmesh.ops.reverse_faces(b, faces=[g for g in inside if isinstance(g, bmesh.types.BMFace)])
b.to_mesh(o.data)
b.free()
xs = [v.co.x for v in o.data.vertices]
length = max(xs)
ring = [v.co for v in o.data.vertices if v.co.x > length - 0.02]
radius = max(abs(c.y) for c in ring)

# colision: media caja bajo el eje, a lo largo del caño
me = bpy.data.meshes.new(f"UCX_{NAME}_00")
bb = bmesh.new()
for v in bmesh.ops.create_cube(bb, size=1.0)["verts"]:
    v.co = Vector(((v.co.x + 0.5) * length, v.co.y * 2 * radius, (v.co.z - 0.5) * radius))
bb.to_mesh(me)
bb.free()
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
(OUT / "cano_build.json").write_text(json.dumps({
    "source": str(SRC), "length_cm": round(length * 100, 1), "radius_cm": round(radius * 100, 1),
    "straightened_deg": round(math.degrees(math.atan(m)), 2), "triangles": tris,
    "materials": [mt.name for mt in o.data.materials if mt], "ucx": 1}, indent=1, ensure_ascii=False), encoding="utf-8")
print("CANO_OK", round(length, 3), round(radius, 3), tris)
