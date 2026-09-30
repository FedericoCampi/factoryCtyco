"""Blender: auto basico que cruza el estacionamiento en loop (puerta sur -> puerta este).

Salida: SourceAssets/AutoBasico/auto_loop.fbx, AutoBasico.blend y auto_build.json.
La animacion esta en las coordenadas del estacionamiento (mismo origen que SM_Parking), asi
que el actor va en la misma posicion que Parking_Estacionamiento.
Huesos: Root > Auto (recorrido) > 4 ruedas (giran segun la distancia).
Para cambiar el vehiculo mas adelante: reemplazar build_car() por la malla del camion
(rueda = objeto cuyo nombre empieza con "Rueda_") y volver a correr.

blender -b --factory-startup -P Scripts/author_vehicle_loop.py
"""
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/AutoBasico"
FPS, SPEED = 30, 3.5          # m/s
WHEEL_R = 0.33
# Recorrido en metros (coordenadas Blender del estacionamiento): entra desde afuera por la
# puerta sur (lineas amarillas, x -10.9..-7.1, y -7.9..-6.9), dobla donde estaba el primer pilar
# de la arcada (quitado) y cruza hasta la puerta este (lineas amarillas, x 9.9..10.9,
# y -7..-3.1, la vieja union con la fabrica), por donde sale. Al terminar (afuera) vuelve a empezar.
PATH = [(-9.0, -14.0), (-9.0, -9.0), (-8.9, -7.2), (-7.9, -5.8), (-6.3, -5.2), (0.0, -5.0),
        (8.0, -5.0), (10.4, -5.0), (12.5, -5.0), (18.0, -5.0)]
CLOSED = False

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = FPS


def mat(name, color, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = 0.35
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


def box(name, size, loc, material, bevel=0.06):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        m = o.modifiers.new("b", "BEVEL"); m.width = bevel; m.segments = 3
        bpy.ops.object.modifier_apply(modifier=m.name)
    o.data.materials.append(material)
    return o


def build_car():
    body, glass = mat("M_AutoCarroceria", (0.75, 0.08, 0.05)), mat("M_AutoVidrio", (0.05, 0.08, 0.12))
    tire, rim = mat("M_AutoRueda", (0.02, 0.02, 0.02)), mat("M_AutoLlanta", (0.6, 0.6, 0.62))
    front, back = mat("M_AutoFaro", (1.0, 0.9, 0.6), 4.0), mat("M_AutoStop", (1.0, 0.05, 0.02), 3.0)
    parts = [box("Carroceria", (3.6, 1.62, 0.55), (0, 0, 0.62), body, 0.12),
             box("Cabina", (1.9, 1.42, 0.5), (-0.25, 0, 1.12), glass, 0.15),
             box("Techo", (1.7, 1.36, 0.06), (-0.25, 0, 1.4), body, 0.02)]
    for side in (-1, 1):
        parts.append(box(f"Faro{side}", (0.05, 0.3, 0.12), (1.8, side * 0.55, 0.7), front, 0.01))
        parts.append(box(f"Stop{side}", (0.05, 0.3, 0.1), (-1.8, side * 0.55, 0.72), back, 0.01))
    wheels = []
    for i, (x, y) in enumerate(((1.15, 0.72), (1.15, -0.72), (-1.15, 0.72), (-1.15, -0.72))):
        bpy.ops.mesh.primitive_cylinder_add(radius=WHEEL_R, depth=0.24, vertices=24,
                                            location=(x, y, WHEEL_R), rotation=(math.pi / 2, 0, 0))
        w = bpy.context.object; w.name = f"Rueda_{i}"; w.data.materials.append(tire)
        bpy.ops.object.transform_apply(rotation=True)
        bpy.ops.mesh.primitive_cylinder_add(radius=WHEEL_R * 0.55, depth=0.26, vertices=6,
                                            location=(x, y, WHEEL_R), rotation=(math.pi / 2, 0, 0))
        h = bpy.context.object; h.data.materials.append(rim)
        bpy.ops.object.transform_apply(rotation=True)
        bpy.ops.object.select_all(action="DESELECT"); h.select_set(True); w.select_set(True)
        bpy.context.view_layer.objects.active = w; bpy.ops.object.join()
        wheels.append(w)
    return parts, wheels


def catmull(points, closed, per_seg=40):
    """Curva Catmull-Rom (centripeta) densa a traves de los puntos."""
    P = [Vector((x, y, 0)) for x, y in points]
    if not closed:  # extremos prolongados en linea recta
        P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out, n = [], len(P)
    for i in (range(n) if closed else range(1, n - 2)):
        p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % n], P[(i + 2) % n]
        t0 = 0; t1 = t0 + (p1 - p0).length ** 0.5; t2 = t1 + (p2 - p1).length ** 0.5; t3 = t2 + (p3 - p2).length ** 0.5
        for k in range(per_seg):
            t = t1 + (t2 - t1) * k / per_seg
            a1 = p0 * ((t1 - t) / (t1 - t0)) + p1 * ((t - t0) / (t1 - t0))
            a2 = p1 * ((t2 - t) / (t2 - t1)) + p2 * ((t - t1) / (t2 - t1))
            a3 = p2 * ((t3 - t) / (t3 - t2)) + p3 * ((t - t2) / (t3 - t2))
            b1 = a1 * ((t2 - t) / (t2 - t0)) + a2 * ((t - t0) / (t2 - t0))
            b2 = a2 * ((t3 - t) / (t3 - t1)) + a3 * ((t - t1) / (t3 - t1))
            out.append(b1 * ((t2 - t) / (t2 - t1)) + b2 * ((t - t1) / (t2 - t1)))
    if not closed:
        out.append(P[-2])
    return out


dense = catmull(PATH, CLOSED)
cum = [0.0]
for i in range(1, len(dense) + (1 if CLOSED else 0)):
    cum.append(cum[-1] + (dense[i % len(dense)] - dense[i - 1]).length)
LENGTH = cum[-1]
FRAMES = round(LENGTH / SPEED * FPS)


def at(d):
    d = d % LENGTH if CLOSED else min(d, LENGTH - 1e-6)
    i = max(k for k in range(len(cum) - 1) if cum[k] <= d)
    f = (d - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
    a, b = dense[i], dense[(i + 1) % len(dense)]
    return a.lerp(b, f), (b - a).normalized()


def ground_z(pos, slab=(11.3, 8.3), drop=0.55, ramp=1.5):
    """Afuera el piso (Piso_Exterior) esta 55 cm mas abajo: bajar en 1,5 m desde el borde."""
    out = max(abs(pos.x) - slab[0], abs(pos.y) - slab[1], 0.0)
    return -drop * min(out / ramp, 1.0)


parts, wheels = build_car()
arm = bpy.data.objects.new("AutoBasico", bpy.data.armatures.new("SK_AutoBasico"))
scn.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones


def bone(name, head, parent=None):
    b = eb.new(name); b.head = head; b.tail = Vector(head) + Vector((0, 0.3, 0)); b.roll = 0
    if parent: b.parent = eb[parent]
    return b


bone("Root", (0, 0, 0)); bone("Auto", (0, 0, 0), "Root")
for w in wheels:
    c = sum((w.matrix_world @ v.co for v in w.data.vertices), Vector()) / len(w.data.vertices)
    bone(w.name, (c.x, c.y, WHEEL_R), "Auto")
bpy.ops.object.mode_set(mode="OBJECT")

for o in parts + wheels:
    vg = o.vertex_groups.new(name=o.name if o in wheels else "Auto")
    vg.add(range(len(o.data.vertices)), 1.0, "REPLACE")
wheel_names = [w.name for w in wheels]
bpy.ops.object.select_all(action="DESELECT")
for o in parts + wheels:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
mesh = parts[0]; mesh.name = "SK_AutoBasico_Mesh"
mesh.parent = arm
mesh.modifiers.new("Armature", "ARMATURE").object = arm

arm.animation_data_create()
arm.animation_data.action = bpy.data.actions.new("Auto_Loop")
car = arm.pose.bones["Auto"]; car.rotation_mode = "XYZ"
spins = [arm.pose.bones[n] for n in wheel_names]
yaw_prev = None
for f in range(FRAMES + 1):
    d = LENGTH * f / FRAMES
    pos, tan = at(d)
    yaw = math.atan2(tan.y, tan.x)
    if yaw_prev is not None:  # desenrollar para que no salte de +180 a -180
        while yaw - yaw_prev > math.pi: yaw -= 2 * math.pi
        while yaw - yaw_prev < -math.pi: yaw += 2 * math.pi
    yaw_prev = yaw
    car.location = (pos.x, pos.y, ground_z(pos)); car.rotation_euler = (0, 0, yaw)
    car.keyframe_insert("location", frame=f); car.keyframe_insert("rotation_euler", frame=f)
    for s in spins:
        s.rotation_mode = "XYZ"; s.rotation_euler = (0, d / WHEEL_R, 0)
        s.keyframe_insert("rotation_euler", frame=f)
scn.frame_start, scn.frame_end = 0, FRAMES

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True); mesh.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT / "auto_loop.fbx"), use_selection=True,
                         object_types={"ARMATURE", "MESH"}, add_leaf_bones=False, bake_anim=True,
                         bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                         bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
                         mesh_smooth_type="FACE", primary_bone_axis="Y", secondary_bone_axis="X")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "AutoBasico.blend"))
(OUT / "auto_build.json").write_text(json.dumps({
    "length_m": round(LENGTH, 2), "seconds": round(FRAMES / FPS, 2), "frames": FRAMES, "fps": FPS,
    "speed_mps": SPEED, "path_m": PATH, "closed": CLOSED, "bones": ["Root", "Auto"] + wheel_names,
}, indent=1), encoding="utf-8")
print("AUTO_OK", round(LENGTH, 2), FRAMES)
