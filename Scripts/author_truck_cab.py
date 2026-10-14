"""Blender: cabina del camion con vidrios, volante, asiento y tablero (08/10), para que se vea al camionero.

El vidrio del modelo esta pintado en la textura (opaco). Las ventanillas y el parabrisas se cortan con planos (bordes
rectos, no el serrucho de quitar caras enteras): la capa de afuera del vidrio pasa al material M_CamionVidrio (en Unreal,
translucido: apply_camionero.py) y la de adentro se quita. La cabina recibe un forro hacia adentro (sus caras dadas vuelta,
con M_CamionInterior; sin el se veia a traves de ella), un asiento, un tablero y el volante, en el hueso Camion.
Las medidas son en m desde el eje trasero (x adelante, y a la izquierda, z arriba), tomadas el 08/10 en vistas
ortograficas. El camionero (AFactoryVehiclePath::DriverTransform) va sentado en DRIVER, con las manos en el volante.
Parte siempre de Camion_antes_cabina.blend (la cabina original) y guarda Camion.blend; exporta otra vez camion_loop.fbx
como author_truck_loop.py (con su animacion). Despues: author_truck_dump.py y, en el editor, apply_camionero.py.

blender -b --factory-startup -P Scripts/author_truck_cab.py
"""
import json
import math
import shutil
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Camion"
CAB_X = 2.95                     # la cabina: adelante de la caja
CAB_FLOOR = 0.9                  # el forro empieza aca (abajo quedan el chasis y las ruedas)
# ventanilla de cada lado: poligono en (x, z); cuenta para las caras que miran de costado con |y| > SIDE_Y (el vidrio
# esta hundido, |y| ~0,73)
SIDE = [(3.19, 1.53), (3.68, 1.38), (3.635, 1.775), (3.19, 1.775)]
SIDE_Y = 0.6
# parabrisas: caras que miran adelante o atras, x > FRONT_X, |y| < FRONT_HALF, z entre FRONT_Z
FRONT_X, FRONT_HALF, FRONT_Z = 3.70, 0.68, (1.40, 1.81)
DRIVER = (3.35, 0.38, 0.16)      # donde va el origen del camionero (Unreal: 335, -38, 16)
WHEEL = (3.75, 0.38, 1.24)       # centro del volante (entre las manos), radio y cuanto se inclina hacia atras
WHEEL_R, WHEEL_TILT = 0.19, 30.0

backup = OUT / "Camion_antes_cabina.blend"
blend = OUT / "Camion.blend"
if not backup.exists():
    shutil.copy2(blend, backup)
bpy.ops.wm.open_mainfile(filepath=str(backup))
body = bpy.data.objects["SK_Camion_Mesh"]
arm = bpy.data.objects["Camion"]


def material(name, color, rough=0.6, metal=0.0, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Alpha"].default_value = alpha
    if m.name not in body.data.materials:
        body.data.materials.append(m)
    return list(body.data.materials).index(m)


GLASS = material("M_CamionVidrio", (0.08, 0.11, 0.13), 0.05, 0.0, 0.3)
INTERIOR = next(i for i, m in enumerate(body.data.materials) if m.name == "M_CamionInterior")
DARK = next(i for i, m in enumerate(body.data.materials) if m.name == "M_CamionTuerca")


def inside(poly, x, z):
    hit = False
    for i in range(len(poly)):
        (x1, z1), (x2, z2) = poly[i], poly[(i + 1) % len(poly)]
        if (z1 > z) != (z2 > z) and x < x1 + (z - z1) * (x2 - x1) / (z2 - z1):
            hit = not hit
    return hit


bm = bmesh.new()
bm.from_mesh(body.data)
deform = bm.verts.layers.deform.verify()
truck_group = body.vertex_groups["Camion"].index


def cab_faces():
    return [f for f in bm.faces if f.calc_center_median().x >= CAB_X and f.calc_center_median().z >= CAB_FLOOR
            and all(truck_group in v[deform] for v in f.verts) and f.material_index == 0]


def cut(faces, co, no):
    """Corta las caras con el plano (co, no): sus bordes quedan rectos ahi."""
    geom = list({e for f in faces for e in f.edges}) + faces + list({v for f in faces for v in f.verts})
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_inner=False, clear_outer=False)


# 1. cortes rectos: los lados del poligono de cada ventanilla y los del parabrisas
for i in range(len(SIDE)):
    (x1, z1), (x2, z2) = SIDE[i], SIDE[(i + 1) % len(SIDE)]
    no = Vector((z2 - z1, 0, -(x2 - x1))).normalized()
    side = [f for f in cab_faces() if abs(f.normal.y) > 0.3 and 3.0 < f.calc_center_median().x < 3.9]
    cut(side, Vector((x1, 0, z1)), no)


def front():
    return [f for f in cab_faces() if abs(f.normal.x) > 0.3 and f.calc_center_median().x > FRONT_X - 0.05]


for co, no in (((0, FRONT_HALF, 0), (0, 1, 0)), ((0, -FRONT_HALF, 0), (0, 1, 0)), ((0, 0, FRONT_Z[0]), (0, 0, 1)),
               ((0, 0, FRONT_Z[1]), (0, 0, 1))):
    cut(front(), Vector(co), Vector(no))

# 2. vidrios: la capa de afuera al material de vidrio, la de adentro se quita; el resto de la cabina se forra
glass, inner, shell = [], [], []
for f in cab_faces():
    c, n = f.calc_center_median(), f.normal
    if abs(n.y) > 0.5 and abs(c.y) > SIDE_Y and inside(SIDE, c.x, c.z):
        (glass if n.y * c.y > 0 else inner).append(f)
    elif abs(n.x) > 0.5 and c.x > FRONT_X and abs(c.y) < FRONT_HALF and FRONT_Z[0] < c.z < FRONT_Z[1]:
        (glass if n.x > 0 else inner).append(f)
    else:
        shell.append(f)
for f in glass:
    f.material_index = GLASS
glass_area = sum(f.calc_area() for f in glass)
inner_count = len(inner)
bmesh.ops.delete(bm, geom=inner, context="FACES")
copy = bmesh.ops.duplicate(bm, geom=shell)
lining = [g for g in copy["geom"] if isinstance(g, bmesh.types.BMFace)]
for v in [g for g in copy["geom"] if isinstance(g, bmesh.types.BMVert)]:
    v.co -= v.normal * 0.01
for f in lining:
    f.material_index = INTERIOR
bmesh.ops.reverse_faces(bm, faces=lining)


# 3. asiento, tablero y volante (en el hueso Camion)
def weight(verts):
    for v in verts:
        v[deform].clear()
        v[deform][truck_group] = 1.0


def box(lo, hi, mat):
    made = bmesh.ops.create_cube(bm, size=1.0)
    lo, hi = Vector(lo), Vector(hi)
    for v in made["verts"]:
        v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
    for f in {f for v in made["verts"] for f in v.link_faces}:
        f.material_index = mat
    weight(made["verts"])


dx, dy, _ = DRIVER
box((dx - 0.25, dy - 0.27, 0.80), (dx + 0.2, dy + 0.27, 0.93), INTERIOR)        # asiento
box((dx - 0.36, dy - 0.27, 0.80), (dx - 0.24, dy + 0.27, 1.62), INTERIOR)       # respaldo
box((3.60, -0.74, 1.02), (3.80, 0.74, 1.30), DARK)                              # tablero (detras del frente, x ~3,9)
# volante: aro (tubo de 2,5 cm), maza, un rayo y la columna; armado acostado y despues girado hacia el camionero
SEG, SIDES = 24, 6
tube = []
for i in range(SEG):
    a = 2 * math.pi * i / SEG
    for k in range(SIDES):
        b = 2 * math.pi * k / SIDES
        r = WHEEL_R + 0.025 * math.cos(b)
        tube.append(bm.verts.new((r * math.cos(a), r * math.sin(a), 0.025 * math.sin(b))))
for i in range(SEG):
    for k in range(SIDES):
        q = [tube[i * SIDES + k], tube[i * SIDES + (k + 1) % SIDES], tube[((i + 1) % SEG) * SIDES + (k + 1) % SIDES],
             tube[((i + 1) % SEG) * SIDES + k]]
        bm.faces.new(q).material_index = DARK
hub = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.05, radius2=0.05, depth=0.05)["verts"]
spoke = bmesh.ops.create_cube(bm, size=1.0)["verts"]
for v in spoke:
    v.co = Vector((v.co.x * WHEEL_R * 2, v.co.y * 0.03, v.co.z * 0.015))
column = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.035, radius2=0.035, depth=0.35)["verts"]
for v in column:
    v.co.z -= 0.2
for f in {f for v in hub + spoke + column for f in v.link_faces}:
    f.material_index = DARK
parts = tube + hub + spoke + column
place = Matrix.Translation(WHEEL) @ Matrix.Rotation(math.radians(-90 + WHEEL_TILT), 4, "Y")
for v in parts:
    v.co = place @ v.co
weight(parts)
bm.normal_update()
bm.to_mesh(body.data)
bm.free()

# exportar como author_truck_loop.py (con la animacion del recorrido)
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True); body.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(filepath=str(OUT / "camion_loop.fbx"), use_selection=True,
                         object_types={"ARMATURE", "MESH"}, add_leaf_bones=False, bake_anim=True,
                         bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                         bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
                         mesh_smooth_type="FACE", primary_bone_axis="Y", secondary_bone_axis="X",
                         path_mode="COPY", embed_textures=True)
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
report = {"glass_faces": len(glass), "glass_area_m2": round(glass_area, 3), "inner_glass_removed": inner_count,
          "lining_faces": len(lining), "faces": len(body.data.polygons), "driver_m": DRIVER, "wheel_m": WHEEL,
          "materials": [m.name for m in body.data.materials]}
(OUT / "camion_cabina_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("CAMION_CABINA_OK", json.dumps(report))
