"""Blender: prepara el codo metalico del usuario (3D assets/GLBs/Codo metálico reforzado con pernos-complete.glb) para
Unreal (02/10).

El GLB viene normalizado (1 m en su lado mayor, ~700 000 triangulos, una sola malla con 4 texturas de 2-4K). Se deja
con SIZE_M en su lado mayor, origen al centro del piso, se reduce a ~150 000 triangulos y se le agrega una colision
UCX de caja (un poco adentro del contorno). Va abierto: se le saca la mitad de arriba (corte horizontal a la altura del
centro de sus bocas, el codo esta acostado) y lo que queda se duplica dado vuelta para que el interior se vea.
Las dos bocas (centro, radio y hacia donde miran) van a codo_build.json para apply_linea_descarga.py.
Salida: SourceAssets/CodoMetalico/SM_CodoMetalico.fbx y codo_build.json.

blender -b --factory-startup -P Scripts/author_codo_metalico.py
"""
import json
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

SRC = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/Codo metálico reforzado con pernos-complete.glb")
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/CodoMetalico"
NAME = "SM_CodoMetalico"
SIZE_M = 1.0       # lado mayor; el usuario lo escala en el editor si hace falta
DECIMATE = 0.22    # ~700k -> ~150k triangulos
INSET = 0.02       # la caja de colision queda 2 cm adentro del contorno

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
scale = SIZE_M / max(hi - lo)
o.data.transform(Matrix.Scale(scale, 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
dec = o.modifiers.new("Decimate", "DECIMATE")
dec.ratio = DECIMATE
bpy.ops.object.modifier_apply(modifier=dec.name)
o.name = o.data.name = NAME
size = [round((hi[i] - lo[i]) * scale, 3) for i in range(3)]


def end_port(mesh, axis, depth=0.02):
    """Boca en la punta -axis del codo: centro y radio del anillo de vertices de la punta."""
    pts = [v.co for v in mesh.vertices]
    end = min(c[axis] for c in pts)
    ring = [c for c in pts if c[axis] < end + depth]
    other = [i for i in range(3) if i != axis]
    lo_, hi_ = [min(c[i] for c in ring) for i in other], [max(c[i] for c in ring) for i in other]
    center = Vector((0, 0, 0))
    center[axis] = end
    for i, a, b_ in zip(other, lo_, hi_):
        center[i] = (a + b_) / 2
    return center, max(b_ - a for a, b_ in zip(lo_, hi_)) / 2


def open_top(mesh, z):
    """Saca la mitad de arriba (z > z) y duplica dado vuelta lo que queda."""
    b = bmesh.new()
    b.from_mesh(mesh)
    bmesh.ops.bisect_plane(b, geom=b.verts[:] + b.edges[:] + b.faces[:], plane_co=(0, 0, z), plane_no=(0, 0, 1))
    bmesh.ops.delete(b, geom=[f for f in b.faces if f.calc_center_median().z > z], context="FACES_ONLY")
    inside = bmesh.ops.duplicate(b, geom=b.faces[:])["geom"]
    bmesh.ops.reverse_faces(b, faces=[g for g in inside if isinstance(g, bmesh.types.BMFace)])
    b.to_mesh(mesh)
    b.free()


# las bocas miran a -X y a -Y en Blender (-X y +Y en Unreal)
ports = {"x": end_port(o.data, 0), "y": end_port(o.data, 1)}
open_top(o.data, sum(c.z for c, _ in ports.values()) / 2)

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
(OUT / "codo_build.json").write_text(json.dumps({
    "source": str(SRC), "size_m": size, "scale": round(scale, 4),
    "triangles_in": tris_in, "triangles": tris, "materials": [m.name for m in o.data.materials if m],
    "ucx": 1,
    # en Unreal (cm, Y invertida): centro, radio y hacia donde mira cada boca
    "ports": [{"center_cm": [round(c.x * 100, 1), round(-c.y * 100, 1), round(c.z * 100, 1)], "radius_cm": round(r * 100, 1),
               "facing": facing} for (c, r), facing in ((ports["x"], [-1, 0, 0]), (ports["y"], [0, 1, 0]))]},
    indent=1, ensure_ascii=False), encoding="utf-8")
print("CODO_OK", size, tris, ports)
