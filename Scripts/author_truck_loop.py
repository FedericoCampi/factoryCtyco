"""Blender: camion del usuario (3D assets/GLBs/truck.glb) que cruza el estacionamiento en loop.

Reemplaza al auto basico (author_vehicle_loop.py). Cruza derecho de oeste a este (28/09).
El GLB es una sola malla (1 m de largo, frente a +X). Las ruedas se recortan por geometria
(cilindro alrededor de cada eje, medido en el GLB) y van en huesos propios que giran segun la
distancia recorrida; las delanteras ademas doblan. Como la llanta del modelo es casi simetrica,
se agregan 6 tuercas por maza para que el giro se note.
El eje trasero sigue el recorrido y el delantero tambien (cuerda = distancia entre ejes), asi el
camion dobla como un vehiculo y no pivotea en el centro.

Salida: SourceAssets/Camion/camion_loop.fbx, Camion.blend y camion_build.json.
Huesos: Root > Camion (recorrido; origen en el eje trasero, a nivel del piso) > Rueda_DI, Rueda_DD,
Rueda_TI, Rueda_TD (D = delantera, T = trasera; I = izquierda (+Y), D = derecha (-Y)).

blender -b --factory-startup -P Scripts/author_truck_loop.py
"""
import json
import math
from pathlib import Path
import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

SRC = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/truck.glb")
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Camion"
LENGTH_M = 5.2                 # largo final del camion (el GLB mide 1); 6,5 quedaba grande
DECIMATE = 0.22                # ~700 000 caras -> ~150 000
FPS, SPEED = 30, 3.0           # m/s
MAX_STEER = math.radians(38)
# Ruedas medidas en el GLB normalizado (Scripts de revision del 28/09): centro x, z, radio y
# franja |y| que ocupa la goma (atras son duales, mas anchas).
WHEELS = {  # nombre: (x, z, radio, y_interior, y_exterior, lado)
    "Rueda_DI": (0.3358, 0.071, 0.072, 0.112, 0.176, 1),
    "Rueda_DD": (0.3358, 0.071, 0.072, 0.112, 0.176, -1),
    "Rueda_TI": (-0.3064, 0.071, 0.069, 0.085, 0.172, 1),
    "Rueda_TD": (-0.3064, 0.071, 0.069, 0.085, 0.172, -1),
}
CUT_MARGIN = 0.004             # el cilindro de corte excede un poco la goma
# Puerta de carga (28/09): la pared izquierda (+Y) de la caja, entre los esquineros y los rieles de
# arriba y abajo, en el GLB normalizado. Es la superficie del modelo (en y ~0.149), recortada y puesta
# en el hueso Puerta, con bisagra abajo: se rebate hacia afuera hasta quedar horizontal, como plataforma
# de carga (abriendo hacia arriba tapaba la carga a la camara de arriba). La caja del modelo
# es hueca y sin interior: se agrega un forro (piso, techo, paredes) que mira hacia adentro.
DOOR = (-0.395, 0.195, 0.195, 0.412)   # x0, x1, z0, z1
DOOR_Y = 0.12                          # caras de la pared: y mayor que esto
SKIN_Y = 0.149
CARGO = (-0.48, 0.21, -0.14, 0.14, 0.19, 0.435)   # interior: x0, x1, y0, y1, z0, z1
# Techo de la caja (hueso Techo): Unreal lo esconde con la puerta abierta, asi la camara de arriba ve la carga.
ROOF = (-0.47, 0.20, 0.14, 0.41)       # x0, x1, |y| maximo, z minimo (el techo tiene dos capas: 0,42 y 0,44)
# Recorrido en metros (coordenadas Blender del estacionamiento): derecho de oeste a este. Entra por
# el vano 0 del muro oeste (y -7.69..-4.31, abierto el 28/09 en author_parking_scene.py; la puerta
# sur se cerro) y sale por la puerta este (y -6.65..-3.35). En y -5.5 entra en las dos con ~20 cm
# por lado. Afuera al oeste hay piso desde el 28/09 (Piso_Exterior_Oeste).
LANE_Y = -5.5
PATH = [(-30.0, LANE_Y), (0.0, LANE_Y), (23.0, LANE_Y)]

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = FPS
bpy.ops.import_scene.gltf(filepath=str(SRC))
body = [o for o in scn.objects if o.type == "MESH"][0]
bpy.ops.object.select_all(action="DESELECT"); body.select_set(True)
bpy.context.view_layer.objects.active = body
body.parent = None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for extra in [x for x in scn.objects if x is not body]:
    bpy.data.objects.remove(extra)
faces_in = len(body.data.polygons)
# reducir primero: hecho despues de separar las piezas, mezclaba pesos en los bordes (la puerta se estiraba)
dec = body.modifiers.new("dec", "DECIMATE"); dec.ratio = DECIMATE
bpy.ops.object.modifier_apply(modifier=dec.name)
S = LENGTH_M
REAR_X = WHEELS["Rueda_TI"][0]
WHEELBASE = (WHEELS["Rueda_DI"][0] - REAR_X) * S


DOOR_PART = len(WHEELS)   # indice de la puerta en wheel_of
ROOF_PART = DOOR_PART + 1


def wheel_of(points):
    """Indice de rueda (0..3) o DOOR_PART (puerta) de cada punto, -1 si es carroceria."""
    idx = np.full(len(points), -1)
    for i, (x, z, r, yin, yout, side) in enumerate(WHEELS.values()):
        inside = ((np.hypot(points[:, 0] - x, points[:, 2] - z) < r + CUT_MARGIN)
                  & (points[:, 1] * side >= yin) & (points[:, 1] * side <= yout + 0.02))  # margen: tuercas
        idx[inside & (idx < 0)] = i
    x0, x1, z0, z1 = DOOR
    door = ((points[:, 0] > x0) & (points[:, 0] < x1) & (points[:, 2] > z0) & (points[:, 2] < z1)
            & (points[:, 1] > DOOR_Y - 0.03))   # el forro de la puerta va un poco adentro de la pared
    idx[door & (idx < 0)] = DOOR_PART
    rx0, rx1, ry, rz = ROOF
    roof = (points[:, 0] > rx0) & (points[:, 0] < rx1) & (np.abs(points[:, 1]) < ry) & (points[:, 2] > rz)
    idx[roof & (idx < 0)] = ROOF_PART
    return idx


# 1. separar las ruedas: split de sus caras (duplica los vertices del borde)
n = len(body.data.polygons)
centers = np.empty(n * 3); body.data.polygons.foreach_get("center", centers)
face_wheel = wheel_of(centers.reshape(-1, 3))
# en modo cara: cargada en modo vertice, la seleccion sumaba caras vecinas de la carroceria
bpy.context.tool_settings.mesh_select_mode = (False, False, True)
body.data.vertices.foreach_set("select", np.zeros(len(body.data.vertices), dtype=bool))
body.data.edges.foreach_set("select", np.zeros(len(body.data.edges), dtype=bool))
for part in range(ROOF_PART + 1):   # pieza por pieza: la puerta y el techo son vecinos
    # separar reordena las caras: clasificar de nuevo antes de cada pasada
    centers = np.empty(len(body.data.polygons) * 3); body.data.polygons.foreach_get("center", centers)
    body.data.polygons.foreach_set("select", wheel_of(centers.reshape(-1, 3)) == part)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.split()
    bpy.ops.object.mode_set(mode="OBJECT")
    body.data.vertices.foreach_set("select", np.zeros(len(body.data.vertices), dtype=bool))
    body.data.edges.foreach_set("select", np.zeros(len(body.data.edges), dtype=bool))
wheel_faces = [int((face_wheel == i).sum()) for i in range(len(WHEELS))]
door_faces = int((face_wheel == DOOR_PART).sum())
roof_faces = int((face_wheel == ROOF_PART).sum())

# 2. tuercas en cada maza (en el GLB normalizado), del lado de afuera
co = np.empty(len(body.data.vertices) * 3); body.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
nut_mat = bpy.data.materials.new("M_CamionTuerca")
nut_mat.use_nodes = True
bsdf = nut_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.08, 0.08, 0.09, 1)
bsdf.inputs["Metallic"].default_value = 0.9
bsdf.inputs["Roughness"].default_value = 0.35
body.data.materials.append(nut_mat)
nut_slot = len(body.data.materials) - 1
bm = bmesh.new(); bm.from_mesh(body.data)
nut_faces = []
hub_faces = {}
for name, (x, z, r, yin, yout, side) in WHEELS.items():
    near = co[np.hypot(co[:, 0] - x, co[:, 2] - z) < r * 0.45]
    face_y = float((near[:, 1] * side).max()) if len(near) else yout  # cara exterior de la maza
    hub_faces[name] = round(face_y, 4)
    size = r * 0.09
    for k in range(6):
        a = k * math.pi / 3
        c = Vector((x + math.cos(a) * r * 0.36, (face_y - size * 0.3) * side, z + math.sin(a) * r * 0.36))
        made = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=size, radius2=size * 0.8,
                                     depth=size * 1.6, matrix=Matrix.Translation(c) @ Matrix.Rotation(-side * math.pi / 2, 4, "X"))
        for f in {f for v in made["verts"] for f in v.link_faces}:
            f.material_index = nut_slot
            nut_faces.append(f)
bm.to_mesh(body.data); bm.free()

# 3. grupos de vertices por cara (despues del split cada vertice es de una sola pieza)
n = len(body.data.polygons)
centers = np.empty(n * 3); body.data.polygons.foreach_get("center", centers)
face_wheel = wheel_of(centers.reshape(-1, 3))
groups = ([body.vertex_groups.new(name="Camion")] + [body.vertex_groups.new(name=w) for w in WHEELS]
          + [body.vertex_groups.new(name="Puerta"), body.vertex_groups.new(name="Techo")])
members = [set() for _ in groups]
for p in body.data.polygons:
    members[int(face_wheel[p.index]) + 1].update(p.vertices)
for g, verts in zip(groups, members):
    g.add(list(verts), 1.0, "REPLACE")
loose = set(range(len(body.data.vertices))) - set().union(*members)   # sin cara: a la carroceria
groups[0].add(list(loose), 1.0, "REPLACE")

# 4. forro del interior y escala con origen en el eje trasero, al piso

# forro del interior (hacia adentro, sin la pared de la puerta) y dorso de la puerta, despues de reducir
inner_mat = bpy.data.materials.new("M_CamionInterior")
inner_mat.use_nodes = True
inner_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.32, 0.26, 0.19, 1)
inner_mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
body.data.materials.append(inner_mat)
inner_slot = len(body.data.materials) - 1
bm = bmesh.new(); bm.from_mesh(body.data)
deform = bm.verts.layers.deform.verify()


def slab(lo, hi, group, inward=False, drop_side=None):
    made = bmesh.ops.create_cube(bm, size=1.0)
    lo, hi = Vector(lo), Vector(hi)
    for v in made["verts"]:
        v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
        v[deform][body.vertex_groups[group].index] = 1.0   # por nombre: tras reducir, las referencias vencen
    faces = list({f for v in made["verts"] for f in v.link_faces})
    for f in faces:
        f.material_index = inner_slot
    if inward:
        bmesh.ops.reverse_faces(bm, faces=faces)
    if drop_side is not None:  # la pared que da a la puerta queda abierta
        bmesh.ops.delete(bm, geom=[f for f in faces if f.calc_center_median().y > hi.y - 1e-4], context="FACES_ONLY")


cx0, cx1, cy0, cy1, cz0, cz1 = CARGO
slab((cx0, cy0, cz0), (cx1, cy1, cz1), "Camion", inward=True, drop_side="+y")
slab((DOOR[0], DOOR_Y - 0.012, DOOR[2]), (DOOR[1], DOOR_Y - 0.004, DOOR[3]), "Puerta")
bm.to_mesh(body.data); bm.free()
zmin = min(v.co.z for v in body.data.vertices)
to_final = Matrix.Scale(S, 4) @ Matrix.Translation((-REAR_X, 0, -zmin))
body.data.transform(to_final)
body.name = "SK_Camion_Mesh"
co = [v.co for v in body.data.vertices]
size = [round(max(c[i] for c in co) - min(c[i] for c in co), 3) for i in range(3)]


def wheel_center(name):
    x, z, *_, side = WHEELS[name]
    return to_final @ Vector((x, side * 0.14, z))


# 5. esqueleto
arm = bpy.data.objects.new("Camion", bpy.data.armatures.new("SK_Camion"))
scn.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones


def bone(name, head, parent=None):
    b = eb.new(name); b.head = head; b.tail = Vector(head) + Vector((0, 0.3, 0)); b.roll = 0
    if parent: b.parent = eb[parent]
    return b


bone("Root", (0, 0, 0)); bone("Camion", (0, 0, 0), "Root")
for w in WHEELS:
    bone(w, wheel_center(w), "Camion")
door_mid = (DOOR[0] + DOOR[1]) / 2
bone("Puerta", to_final @ Vector((door_mid, SKIN_Y, DOOR[2])), "Camion")                  # bisagra (abajo)
bone("Puerta_Borde", to_final @ Vector((door_mid, SKIN_Y, DOOR[3])), "Puerta")           # borde de arriba
bone("Techo", to_final @ Vector(((ROOF[0] + ROOF[1]) / 2, 0, 0.443)), "Camion")          # se achica hacia el centro
bpy.ops.object.mode_set(mode="OBJECT")
body.parent = arm
body.modifiers.new("Armature", "ARMATURE").object = arm


# 6. recorrido
def catmull(points, per_seg=40):
    """Curva Catmull-Rom (centripeta) densa a traves de los puntos, extremos en linea recta."""
    P = [Vector((x, y, 0)) for x, y in points]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t0 = 0; t1 = t0 + (p1 - p0).length ** 0.5; t2 = t1 + (p2 - p1).length ** 0.5; t3 = t2 + (p3 - p2).length ** 0.5
        for k in range(per_seg):
            t = t1 + (t2 - t1) * k / per_seg
            a1 = p0 * ((t1 - t) / (t1 - t0)) + p1 * ((t - t0) / (t1 - t0))
            a2 = p1 * ((t2 - t) / (t2 - t1)) + p2 * ((t - t1) / (t2 - t1))
            a3 = p2 * ((t3 - t) / (t3 - t2)) + p3 * ((t - t2) / (t3 - t2))
            b1 = a1 * ((t2 - t) / (t2 - t0)) + a2 * ((t - t0) / (t2 - t0))
            b2 = a2 * ((t3 - t) / (t3 - t1)) + a3 * ((t - t1) / (t3 - t1))
            out.append(b1 * ((t2 - t) / (t2 - t1)) + b2 * ((t - t1) / (t2 - t1)))
    out.append(P[-2])
    return out


dense = catmull(PATH)
cum = [0.0]
for i in range(1, len(dense)):
    cum.append(cum[-1] + (dense[i] - dense[i - 1]).length)
TOTAL = cum[-1]


def at(d):
    d = min(max(d, 0.0), TOTAL - 1e-6)
    i = max(k for k in range(len(cum) - 1) if cum[k] <= d)
    f = (d - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
    a, b = dense[i], dense[i + 1]
    return a.lerp(b, f), (b - a).normalized()


def front_d(d):
    """Distancia del eje delantero sobre el recorrido: a una cuerda WHEELBASE del trasero."""
    lo, hi = d + WHEELBASE * 0.8, d + WHEELBASE * 1.2
    rear = at(d)[0]
    for _ in range(40):
        mid = (lo + hi) / 2
        if (at(mid)[0] - rear).length < WHEELBASE: lo = mid
        else: hi = mid
    return (lo + hi) / 2


def ground_z(pos, slab=(11.3, 8.3), drop=0.65, ramp=1.5):
    """Afuera el piso (Piso_Exterior, z -55) esta 65 cm mas abajo que el estacionamiento (z 10):
    bajar en 1,5 m desde el borde. Al oeste, la calzada de la entrada (author_parking_scene.py,
    DRIVEWAY) sigue a nivel 6 m afuera del muro y baja en 4 m."""
    if pos.x < -slab[0]:
        return -drop * min(max(-slab[0] - 6.0 - pos.x, 0.0) / 4.0, 1.0)
    out = max(abs(pos.x) - slab[0], abs(pos.y) - slab[1], 0.0)
    return -drop * min(out / ramp, 1.0)


RUN = front_d(0.0)
while front_d(RUN) < TOTAL - 0.01:  # el eje trasero avanza hasta que el delantero llega al final
    RUN += 0.05
RUN -= 0.05
FRAMES = round(RUN / SPEED * FPS)

arm.animation_data_create()
arm.animation_data.action = bpy.data.actions.new("Camion_Loop")
truck = arm.pose.bones["Camion"]; truck.rotation_mode = "XYZ"
spins = {w: arm.pose.bones[w] for w in WHEELS}
for s in spins.values():
    s.rotation_mode = "XYZ"
yaw_prev, max_steer = None, 0.0
for f in range(FRAMES + 1):
    d = RUN * f / FRAMES
    df = front_d(d)
    rear, _ = at(d)
    front, front_tan = at(df)
    heading = front - rear
    yaw = math.atan2(heading.y, heading.x)
    if yaw_prev is not None:  # desenrollar para que no salte de +180 a -180
        while yaw - yaw_prev > math.pi: yaw -= 2 * math.pi
        while yaw - yaw_prev < -math.pi: yaw += 2 * math.pi
    yaw_prev = yaw
    zr, zf = ground_z(rear), ground_z(front)
    pitch = -math.atan2(zf - zr, WHEELBASE)
    steer = math.atan2(front_tan.y, front_tan.x) - math.atan2(heading.y, heading.x)
    steer = (steer + math.pi) % (2 * math.pi) - math.pi
    steer = max(-MAX_STEER, min(MAX_STEER, steer))
    max_steer = max(max_steer, abs(steer))
    truck.location = (rear.x, rear.y, zr); truck.rotation_euler = (0, pitch, yaw)
    truck.keyframe_insert("location", frame=f); truck.keyframe_insert("rotation_euler", frame=f)
    for name, pb in spins.items():
        front_wheel = name.startswith("Rueda_D")
        radius = WHEELS[name][2] * S
        # Euler XYZ = Rz(giro de direccion) * Ry(rodado): la rueda rueda en su plano y despues dobla
        pb.rotation_euler = (0, (df if front_wheel else d) / radius, steer if front_wheel else 0.0)
        pb.keyframe_insert("rotation_euler", frame=f)
scn.frame_start, scn.frame_end = 0, FRAMES

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True); body.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT / "camion_loop.fbx"), use_selection=True,
                         object_types={"ARMATURE", "MESH"}, add_leaf_bones=False, bake_anim=True,
                         bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                         bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
                         mesh_smooth_type="FACE", primary_bone_axis="Y", secondary_bone_axis="X",
                         path_mode="COPY", embed_textures=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Camion.blend"))
report = {
    "source": str(SRC), "faces_in": faces_in, "faces": len(body.data.polygons), "size_m": size,
    "wheelbase_m": round(WHEELBASE, 3), "wheel_faces": dict(zip(WHEELS, wheel_faces)),
    "wheel_radius_m": {w: round(v[2] * S, 3) for w, v in WHEELS.items()}, "hub_face_y": hub_faces,
    "lug_nuts": len(WHEELS) * 6, "path_m": PATH, "path_length_m": round(TOTAL, 2),
    "seconds": round(FRAMES / FPS, 2), "frames": FRAMES, "fps": FPS, "speed_mps": SPEED,
    "max_steer_deg": round(math.degrees(max_steer), 1),
    "bones": ["Root", "Camion"] + list(WHEELS) + ["Puerta", "Puerta_Borde", "Techo"], "door_faces": door_faces,
    "roof_faces": roof_faces,
    # en cm de Unreal (x adelante, y a la derecha: la puerta esta del lado -y), desde el eje trasero al piso
    "cargo_cm": {k: round(v * 100, 1) for k, v in zip(("x0", "x1", "y_door", "y_far", "z0", "z1"),
                 ((to_final @ Vector((cx0, 0, 0))).x, (to_final @ Vector((cx1, 0, 0))).x, -cy1 * S, -cy0 * S,
                  (to_final @ Vector((0, 0, cz0))).z, (to_final @ Vector((0, 0, cz1))).z))},
    "materials": [m.name for m in body.data.materials],
}
(OUT / "camion_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("CAMION_OK", json.dumps(report))
