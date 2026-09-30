"""Blender (background): el auto del usuario para el estacionamiento de empleados, en varios colores (29/09).

blender -b --factory-startup -P Scripts/author_employee_cars.py

Fuente: 3D assets/GLBs/autoAzul1.glb (hatchback azul de IA, ~700k triángulos, 1 m, trompa hacia -Y).
Se reduce a ~50k triángulos, se lleva a LENGTH de largo, se gira para que la trompa mire a +X (como los autos
anteriores: apply_employee_scene.py los gira según el cajón) con el origen en el piso, al centro, y lleva una colisión
UCX (la carrocería). Colores: la textura de color se reduce a 2048 y se recolorea solo la chapa azul (tono 190-255°,
saturada); vidrios, gomas y plásticos quedan igual.
Salida: SourceAssets/AutoEmpleado/SM_Auto_<Color>.fbx (uno por color) y autos_build.json.
"""
import colorsys, json
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/autoAzul1.glb")
OUT = ROOT / "SourceAssets/AutoEmpleado"
LENGTH = 3.9
TRIANGLES = 50000
TEXTURE = 2048
# color: (tono 0-1 o None para gris, saturacion x, brillo x, brillo +)
COLORS = {"Azul": None, "Rojo": (0.0, 1.05, 1.05, 0.0), "Verde": (0.36, 0.85, 0.95, 0.0),
          "Blanco": (None, 0.08, 1.9, 0.30), "Gris": (None, 0.08, 1.25, 0.05)}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
body = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
bpy.context.view_layer.objects.active = body
body.select_set(True)
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(bpy.context.scene.objects):
    if o is not body:
        bpy.data.objects.remove(o)
bm = bmesh.new()
bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
bm.to_mesh(body.data)
bm.free()
source_tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
mod = body.modifiers.new("Gameplay", 'DECIMATE')
mod.ratio = min(1.0, TRIANGLES / max(1, source_tris))
mod.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier=mod.name)
# largo en Y -> LENGTH; trompa de -Y a +X; origen en el piso al centro
co = [v.co.copy() for v in body.data.vertices]
lo = Vector([min(c[i] for c in co) for i in range(3)])
hi = Vector([max(c[i] for c in co) for i in range(3)])
scale = LENGTH / (hi.y - lo.y)
centre = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
body.data.transform(Matrix.Rotation(np.pi / 2, 4, 'Z') @ Matrix.Scale(scale, 4) @ Matrix.Translation(-centre))
for poly in body.data.polygons:
    poly.use_smooth = True
body.data.update()
co = [v.co.copy() for v in body.data.vertices]
lo = Vector([min(c[i] for c in co) for i in range(3)])
hi = Vector([max(c[i] for c in co) for i in range(3)])

# colision: la carroceria (sin espejos), un poco adentro
me = bpy.data.meshes.new("UCX_car")
b = bmesh.new()
vs = bmesh.ops.create_cube(b, size=1.0)["verts"]
clo, chi = Vector((lo.x + .05, lo.y + .12, .12)), Vector((hi.x - .05, hi.y - .12, hi.z - .05))
for v in vs:
    v.co = Vector((v.co.x * (chi.x - clo.x), v.co.y * (chi.y - clo.y), v.co.z * (chi.z - clo.z))) + (clo + chi) / 2
b.to_mesh(me)
b.free()
ucx = bpy.data.objects.new("UCX_car", me)
bpy.context.scene.collection.objects.link(ucx)

# textura de color: la que entra al Base Color
mat = body.data.materials[0]
bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
tex_node = next(l.from_node for l in mat.node_tree.links if l.to_socket == bsdf.inputs["Base Color"])
base = tex_node.image
base.scale(TEXTURE, TEXTURE)
px = np.empty(TEXTURE * TEXTURE * 4, dtype=np.float32)
base.pixels.foreach_get(px)
px = px.reshape(-1, 4)
rgb = px[:, :3].astype(np.float64)
# HSV vectorizado
mx, mn = rgb.max(axis=1), rgb.min(axis=1)
delta = mx - mn
sat = np.where(mx > 1e-6, delta / np.maximum(mx, 1e-6), 0.0)
r, g, bl = rgb[:, 0], rgb[:, 1], rgb[:, 2]
hue = np.zeros_like(mx)
safe = np.maximum(delta, 1e-6)
hue = np.where(mx == r, ((g - bl) / safe) % 6, hue)
hue = np.where(mx == g, (bl - r) / safe + 2, hue)
hue = np.where(mx == bl, (r - g) / safe + 4, hue)
hue = (hue / 6.0) % 1.0
paint = (hue > 190 / 360) & (hue < 255 / 360) & (sat > 0.25) & (delta > 0.03)
print("PAINT_FRACTION", round(float(paint.mean()), 3))


def hsv_to_rgb(h, s, v):
    i = np.floor(h * 6).astype(int) % 6
    f = h * 6 - np.floor(h * 6)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    out = np.zeros((len(h), 3))
    for k, (a, b_, c) in enumerate(((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))):
        m = i == k
        out[m] = np.stack([a[m], b_[m], c[m]], axis=1)
    return out


OUT.mkdir(parents=True, exist_ok=True)
made = {}
for name, recipe in COLORS.items():
    image = base.copy()
    image.name = f"T_Auto_{name}"
    image.scale(TEXTURE, TEXTURE)   # la copia vuelve al tamano original
    image.pixels.foreach_set(px.ravel())
    if recipe:
        new_hue, s_mul, v_mul, v_add = recipe
        h = np.full(paint.sum(), new_hue if new_hue is not None else 0.0)
        s = np.clip(sat[paint] * s_mul, 0, 1)
        v = np.clip(mx[paint] * v_mul + v_add, 0, 1)
        out = px.copy()
        out[paint, :3] = hsv_to_rgb(h, s, v)
        image.pixels.foreach_set(out.ravel())
        image.update()
    image.pack()
    tex_node.image = image
    body.name = body.data.name = f"SM_Auto_{name}"
    ucx.name = ucx.data.name = f"UCX_SM_Auto_{name}_00"
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    ucx.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / f"SM_Auto_{name}.fbx"), use_selection=True, object_types={'MESH'},
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE', path_mode='COPY',
        embed_textures=True, axis_forward='-Y', axis_up='Z')
    made[name] = f"SM_Auto_{name}.fbx"
tex_node.image = base
report = {"source": str(SOURCE), "source_triangles": source_tris, "triangles": sum(len(p.vertices) - 2 for p in body.data.polygons),
          "size_m": [round(hi.x - lo.x, 2), round(hi.y - lo.y, 2), round(hi.z - lo.z, 2)], "paint_fraction": round(float(paint.mean()), 3),
          "colors": made}
(OUT / "autos_build.json").write_text(json.dumps(report, indent=1))
print("### AUTOS", json.dumps(report))
