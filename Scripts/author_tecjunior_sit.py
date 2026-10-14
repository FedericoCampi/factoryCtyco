"""Blender: TecJunior sentado al volante (08/10), para el camionero de los camiones.

Parte de SourceAssets/TecJunior/TecJunior_Rig.blend (author_tecjunior_rig.py; pose T, mira a -Y). Cada hueso se apunta
en una direccion del mundo, de la cadera hacia afuera: muslos adelante, piernas abajo, la espalda apenas para atras y
los brazos hacia un volante delante del pecho. La cadera queda donde estaba (a 0,79 m del piso del personaje).
Dos cuadros iguales (una pose quieta) con un leve respiro en el pecho. Salida: SourceAssets/TecJunior/TecJunior_Sit.fbx
(solo el esqueleto, como las otras animaciones; en el editor: apply_camionero.py).

blender -b --factory-startup -P Scripts/author_tecjunior_sit.py
"""
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

DEST = Path(__file__).resolve().parent.parent / "SourceAssets/TecJunior"
FPS, SECONDS = 30, 4
# hueso: direccion en el mundo (x al costado izquierdo del personaje, -y adelante, z arriba); los _r van espejados en x
AIM = {
    "spine": (0, 0.12, 1),          # la espalda apoyada, un poco para atras
    "chest": (0, 0.05, 1),
    "neck": (0, -0.1, 1),
    "head": (0, -0.05, 1),
    "thigh_l": (0.05, -1, 0.05),    # muslos adelante, casi horizontales
    "shin_l": (0.02, -0.25, -1),    # piernas abajo, los pies un poco adelante
    "foot_l": (0, -1, -0.35),
    "clavicle_l": (1, -0.1, -0.15),
    "upperarm_l": (0.06, -0.5, -0.86),   # brazos al volante, los codos pegados al cuerpo (08/10: el codo
    "lowerarm_l": (-0.12, -0.97, 0.25),   # izquierdo salia por la puerta)
    "hand_l": (-0.2, -1, 0.15),
}
ORDER = ["spine", "chest", "neck", "head", "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l",
         "thigh_l", "shin_l", "foot_l"]

bpy.ops.wm.open_mainfile(filepath=str(DEST / "TecJunior_Rig.blend"))
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = next(o for o in bpy.data.objects if o.type == "MESH")
scene = bpy.context.scene
rig.animation_data_create()
rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
bpy.context.view_layer.update()


def aim(name, direction):
    pb = rig.pose.bones[name]
    head, tail = pb.head.copy(), pb.tail.copy()
    turn = (tail - head).normalized().rotation_difference(Vector(direction).normalized())
    pb.matrix = Matrix.Translation(head) @ turn.to_matrix().to_4x4() @ Matrix.Translation(-head) @ pb.matrix
    bpy.context.view_layer.update()


def pose(breath):
    for pb in rig.pose.bones:
        pb.location, pb.rotation_quaternion = (0, 0, 0), (1, 0, 0, 0)
    bpy.context.view_layer.update()
    for name in ORDER:
        x, y, z = AIM[name]
        if name == "chest":
            y += breath
        aim(name, (x, y, z))
        if name.endswith("_l"):
            aim(name[:-2] + "_r", (-x, y, z))


action = bpy.data.actions.new("TecJunior_Sit")
rig.animation_data.action = action
frames = FPS * SECONDS
for f in (0, frames // 2, frames):
    pose(0.0 if f != frames // 2 else 0.03)
    for pb in rig.pose.bones:
        for path in ("location", "rotation_quaternion", "scale"):
            pb.keyframe_insert(path, frame=f + 1, group=pb.name)
scene.frame_start, scene.frame_end = 1, frames + 1
scene.render.fps = FPS

bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(DEST / "TecJunior_Sit.fbx"), use_selection=True, object_types={"ARMATURE"},
                         axis_forward="-Y", axis_up="Z", add_leaf_bones=False, use_armature_deform_only=True,
                         bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                         bake_anim_simplify_factor=0)
scene.frame_set(1)
heads = {n: [round(v, 3) for v in rig.pose.bones[n].head] for n in ("pelvis", "head", "hand_l", "hand_r", "foot_l")}
heads["hand_l_tail"] = [round(v, 3) for v in rig.pose.bones["hand_l"].tail]
heads["hand_r_tail"] = [round(v, 3) for v in rig.pose.bones["hand_r"].tail]
# lo mas ancho del cuerpo deformado (para que no salga por la puerta de la cabina)
mesh = body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
heads["half_width"] = round(max(abs((body.matrix_world @ v.co).x) for v in mesh.vertices), 3)
heads["head_top"] = [round(v, 3) for v in rig.pose.bones["head"].tail]
print("TECJUNIOR_SIT_OK", heads)
