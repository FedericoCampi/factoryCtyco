"""Blender: escalera industrial con plataforma elevada del usuario (3D assets/GLBs/Escalera industrial con plataforma
elevada-complete.glb) para Unreal (03/10).

El GLB viene normalizado (1 m en su lado mayor, ~700 000 triangulos, una sola malla con texturas de 2-4K). Se lleva a
LENGTH_M de largo (la plataforma queda a ~2 m y la baranda a ~0,8 m de alto, escala real), origen al centro del piso,
y se reduce a ~150 000 triangulos. La plataforma queda sin las barandas de los costados y con una baranda adelante
(el borde opuesto a la escalera). Sin caja de colision: en Unreal choca con su propia malla (complex as simple), asi
se puede subir por los escalones y caminar arriba.
Salida: SourceAssets/EscaleraPlataforma/SM_EscaleraPlataforma.fbx y escalera_build.json.

blender -b --factory-startup -P Scripts/author_escalera_plataforma.py
"""
import json
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

SRC = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/Escalera industrial con plataforma elevada-complete.glb")
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/EscaleraPlataforma"
NAME = "SM_EscaleraPlataforma"
SIZE_M = 7.0       # largo (lado mayor)
DECIMATE = 0.22    # ~700k -> ~150k triangulos

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


# Desde el 03/10: la plataforma sin las barandas de los costados (el usuario la va a alargar) y con una baranda en el
# borde de adelante (+Y, el lado opuesto a la escalera, que mira al horno), hecha con la baranda del costado girada y
# llevada al ancho, asi queda igual.
DECK_TOP = 2.08       # m: arriba de la chapa de la plataforma (2,05)
SIDE_X = 1.3          # m: mas afuera que esto estan las barandas de los costados
PLATFORM_FROM_Y = -0.05   # m: de aca en adelante es la plataforma (antes, la escalera y sus barandas)
b = bmesh.new()
b.from_mesh(o.data)
is_rail = lambda f, side: (f.calc_center_median().z > DECK_TOP and f.calc_center_median().x * side > SIDE_X
                           and f.calc_center_median().y > PLATFORM_FROM_Y)
right = [f for f in b.faces if is_rail(f, 1)]
left = [f for f in b.faces if is_rail(f, -1)]
ys = [v.co.y for f in right for v in f.verts]
y0, y1 = min(ys), max(ys)
xs = [v.co.x for f in right for v in f.verts]
x_mid = (min(xs) + max(xs)) / 2
front = bmesh.ops.duplicate(b, geom=right)["geom"]
front_verts = [g for g in front if isinstance(g, bmesh.types.BMVert)]
width = (hi.x - lo.x) * scale - 0.2
# a lo largo de X, centrada, del ancho de la plataforma, en el borde de adelante
place = (Matrix.Translation((0, (hi.y - lo.y) * scale / 2 - 0.08, 0)) @ Matrix.Diagonal((width / (y1 - y0), 1, 1, 1))
         @ Matrix.Rotation(math.radians(-90), 4, "Z") @ Matrix.Translation((-x_mid, -(y0 + y1) / 2, 0)))
bmesh.ops.transform(b, matrix=place, verts=front_verts)
bmesh.ops.delete(b, geom=right + left, context="FACES")
b.to_mesh(o.data)
b.free()


OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
o.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         path_mode="COPY", embed_textures=True, axis_forward="-Y", axis_up="Z")
tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
(OUT / "escalera_build.json").write_text(json.dumps({
    "source": str(SRC), "size_m": size, "scale": round(scale, 4),
    "triangles_in": tris_in, "triangles": tris, "materials": [m.name for m in o.data.materials if m],
    "collision": "complex"},
    indent=1, ensure_ascii=False), encoding="utf-8")
print("ESCALERA_OK", size, tris)
