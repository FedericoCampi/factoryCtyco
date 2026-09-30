"""Blender (background): el vagabundo del usuario, acostado con una botella al lado (29/09).

blender -b --factory-startup -P Scripts/author_vagabundo.py

Fuente: 3D assets/GLBs/vagabundo1.glb (malla de IA de ~700k triángulos, parado en pose A, 1 m, mira a -Y).
Se reduce a ~60k triángulos, se lleva a HEIGHT, se le arma un esqueleto simple (medidas tomadas de la malla) y los
pesos salen de un proxy macizo (como TecJunior). La textura de color se aclara (BRIGHTEN: se veía muy oscuro).
Pose: acostado boca arriba en el piso, la cabeza algo alta, la rodilla izquierda levantada y los brazos al costado.
Clips: Idle (8 s en bucle: respira, mueve apenas la cabeza y los dedos) y LevantaBrazo (3 s: sube el brazo derecho
hacia el cielo, lo sacude y lo baja; lo pasa AFactoryNpc cuando dice su frase). Botella de vidrio verde (SM_Botella),
parada junto a su mano izquierda (bottle_m en el informe, relativa al origen del personaje).
Salida en SourceAssets/Vagabundo: SK_Vagabundo.fbx (malla con esqueleto, en reposo parado), Vagabundo_Idle.fbx,
Vagabundo_LevantaBrazo.fbx, SM_Botella.fbx y vagabundo_build.json. El origen queda en el piso bajo la cadera; la
cabeza hacia +Y de Blender (-Y de Unreal). Vista previa en otra carpeta con PREVIEW=<carpeta>.
"""
import json, math, os
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Quaternion

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/vagabundo1.glb")
DEST = ROOT / "SourceAssets/Vagabundo"
NAME = "SK_Vagabundo"
HEIGHT = 1.72
TRIANGLES = 60000
BRIGHTEN = 1.55          # factor sobre la textura de color
FPS, SECONDS = 30, 8

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
body.name = NAME
body.data.name = NAME
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
body.data.transform(Matrix.Scale(HEIGHT, 4))
for poly in body.data.polygons:
    poly.use_smooth = True   # la reduccion deja caras planas: sombreado suave
body.data.update()

# --- textura mas clara ------------------------------------------------------------------------------------------
brightened = []
for mat in body.data.materials:
    if not mat or not mat.use_nodes:
        continue
    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    link = next((l for l in mat.node_tree.links if bsdf and l.to_socket == bsdf.inputs["Base Color"]), None)
    image = getattr(link.from_node, "image", None) if link else None
    if not image or image.name in brightened:
        continue
    px = np.empty(image.size[0] * image.size[1] * 4, dtype=np.float32)
    image.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    px[:, :3] = np.clip(px[:, :3] * BRIGHTEN + .02, 0.0, 1.0)
    image.pixels.foreach_set(px.ravel())
    image.update()
    image.pack()
    brightened.append(image.name)
print("BRIGHTENED", brightened)

# --- esqueleto (medidas en unidades de la fuente, 1 = altura; se escalan) -----------------------------------
rest = {}


def bone(name, head, tail, parent=None):
    rest[name] = (Vector(head) * HEIGHT, Vector(tail) * HEIGHT, parent)


bone("root", (0, 0, 0), (0, 0, .08))
bone("pelvis", (0, .01, .47), (0, .015, .55), "root")
bone("spine", (0, .015, .55), (0, .03, .66), "pelvis")
bone("chest", (0, .03, .66), (0, .03, .77), "spine")
bone("neck", (0, .03, .77), (0, .03, .82), "chest")
bone("head", (0, .03, .82), (0, .03, 1.0), "neck")
for side, s in (("l", 1), ("r", -1)):
    bone(f"clavicle_{side}", (s * .03, .03, .74), (s * .13, .03, .75), "chest")
    bone(f"upperarm_{side}", (s * .13, .03, .75), (s * .205, .02, .61), f"clavicle_{side}")
    bone(f"lowerarm_{side}", (s * .205, .02, .61), (s * .25, 0.0, .47), f"upperarm_{side}")
    bone(f"hand_{side}", (s * .25, 0.0, .47), (s * .265, -.01, .40), f"lowerarm_{side}")
    bone(f"thigh_{side}", (s * .09, .01, .47), (s * .09, 0.0, .27), "pelvis")
    bone(f"shin_{side}", (s * .09, 0.0, .27), (s * .10, .01, .07), f"thigh_{side}")
    bone(f"foot_{side}", (s * .10, .01, .07), (s * .10, -.10, .02), f"shin_{side}")

arm_data = bpy.data.armatures.new("Vagabundo_Skeleton")
rig = bpy.data.objects.new("Vagabundo_Rig", arm_data)
bpy.context.collection.objects.link(rig)
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
for name, (h, t, parent) in rest.items():
    eb = arm_data.edit_bones.new(name)
    eb.head, eb.tail, eb.roll = h, t, 0
    if parent:
        eb.parent = arm_data.edit_bones[parent]
    eb.use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')

# --- pesos: calor sobre un proxy macizo, transferidos a la malla ----------------------------------------------
proxy = body.copy()
proxy.data = body.data.copy()
proxy.name = "WeightProxy"
bpy.context.collection.objects.link(proxy)
proxy.data.remesh_voxel_size = .007 * HEIGHT
bpy.ops.object.select_all(action='DESELECT')
proxy.select_set(True)
bpy.context.view_layer.objects.active = proxy
bpy.ops.object.voxel_remesh()
dec = proxy.modifiers.new("d", 'DECIMATE')
dec.ratio = min(1.0, 60000 / max(1, len(proxy.data.polygons)))
bpy.ops.object.modifier_apply(modifier=dec.name)
bpy.ops.object.select_all(action='DESELECT')
proxy.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
missing = [n for n in rest if n != "root" and n not in {g.name for g in proxy.vertex_groups}]
if missing:
    raise RuntimeError(f"El pesado por calor salteo huesos: {missing}")
for name in rest:
    body.vertex_groups.new(name=name)
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
bpy.context.view_layer.objects.active = body
dt = body.modifiers.new("WeightTransfer", 'DATA_TRANSFER')
dt.object = proxy
dt.use_vert_data = True
dt.data_types_verts = {'VGROUP_WEIGHTS'}
dt.vert_mapping = 'POLYINTERP_NEAREST'
dt.layers_vgroup_select_src = 'ALL'
dt.layers_vgroup_select_dst = 'NAME'
bpy.ops.object.modifier_apply(modifier=dt.name)
bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
bpy.data.objects.remove(proxy)
body.parent = rig
skin = body.modifiers.new("Skin", 'ARMATURE')
skin.object = rig
skin.use_deform_preserve_volume = True

# --- acostado y movimientos minimos; levanta el brazo cuando habla ----------------------------------------------
for pb in rig.pose.bones:
    pb.rotation_mode = 'QUATERNION'


def update():
    bpy.context.view_layer.update()


def rest_rot(name):
    return rig.data.bones[name].matrix_local.to_3x3()


def set_pose(name, head, rotation):
    """Hueso en el espacio del esqueleto: cabeza en head y rotacion extra respecto de su reposo."""
    rig.pose.bones[name].matrix = Matrix.Translation(head) @ (rotation.to_matrix() @ rest_rot(name)).to_4x4()
    update()


def aim(name, target):
    """Apunta el hueso (su cabeza queda donde la deja el padre) hacia target."""
    pb = rig.pose.bones[name]
    head = pb.head.copy()
    along = rest_rot(name) @ Vector((0, 1, 0))
    set_pose(name, head, along.rotation_difference((target - head).normalized()))


def turn(axis, degrees):
    return Quaternion(Vector(axis), math.radians(degrees))


def wave(t, period, phase=0.0):
    return math.sin(2 * math.pi * t / period + phase)


def smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


thigh = (rest["thigh_l"][1] - rest["thigh_l"][0]).length
shin = (rest["shin_l"][1] - rest["shin_l"][0]).length
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
LIE = turn(X, -90)          # boca arriba: la cabeza hacia +Y, la cara mirando arriba
HIP_Z = .12                 # altura de la cadera acostado


def author_pose(t, arm_up=0.0):
    """Acostado en el segundo t (los periodos dividen el largo del clip); arm_up 0..1 levanta el brazo derecho."""
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    update()
    breath = wave(t, 4.0)
    set_pose("pelvis", Vector((0, 0, HIP_Z)), LIE)
    set_pose("chest", rig.pose.bones["chest"].head.copy(), turn(X, 1.5 * breath) @ LIE)       # el pecho sube al inspirar
    set_pose("neck", rig.pose.bones["neck"].head.copy(), turn(X, 14) @ LIE)                   # la cabeza apoyada, algo alta
    look = 6 * wave(t, 8.0) + 18 * smooth(arm_up)                                              # cuando habla mira al jugador
    set_pose("head", rig.pose.bones["head"].head.copy(), turn(Y, -look) @ turn(X, 20) @ LIE)
    # piernas: la izquierda con la rodilla levantada, la derecha estirada
    hip = rig.pose.bones["thigh_l"].head.copy()
    aim("thigh_l", hip + Vector((.06, -thigh * math.cos(math.radians(50)), thigh * math.sin(math.radians(50)))))
    knee = rig.pose.bones["shin_l"].head.copy()
    drop = knee.z - .10
    aim("shin_l", knee + Vector((.02, -math.sqrt(max(shin ** 2 - drop ** 2, 0.0)), -drop)))
    hip = rig.pose.bones["thigh_r"].head.copy()
    aim("thigh_r", hip + Vector((-.05, -thigh, -.02)))
    knee = rig.pose.bones["shin_r"].head.copy()
    aim("shin_r", knee + Vector((-.03, -shin, -.02)))
    for side in ("l", "r"):
        ankle = rig.pose.bones[f"foot_{side}"].head.copy()
        aim(f"foot_{side}", ankle + Vector((0, -.06, .16)))      # la punta del pie hacia arriba
    # brazo izquierdo: al costado, con la mano junto a la botella; se mueven apenas los dedos
    shoulder = rig.pose.bones["upperarm_l"].head.copy()
    aim("upperarm_l", shoulder + Vector((.12, -.22, -.08)))
    elbow = rig.pose.bones["lowerarm_l"].head.copy()
    aim("lowerarm_l", Vector((elbow.x + .10, elbow.y - .20, .06)))
    wrist = rig.pose.bones["hand_l"].head.copy()
    aim("hand_l", wrist + Vector((.04, -.08, -.02 + .015 * wave(t, 2.0))))
    # brazo derecho: al costado en reposo; arriba, estirado hacia el cielo, cuando habla (con una sacudida)
    u = smooth(arm_up)
    shoulder = rig.pose.bones["upperarm_r"].head.copy()
    down_elbow = shoulder + Vector((-.12, -.22, -.08))
    up_elbow = shoulder + Vector((-.06, .02, .27))
    aim("upperarm_r", down_elbow.lerp(up_elbow, u))
    elbow = rig.pose.bones["lowerarm_r"].head.copy()
    down_hand = Vector((elbow.x - .10, elbow.y - .20, .06))
    shake = .05 * wave(t, .6) * u
    up_hand = elbow + Vector((-.03 + shake, .06, .24))
    aim("lowerarm_r", down_hand.lerp(up_hand, u))
    wrist = rig.pose.bones["hand_r"].head.copy()
    aim("hand_r", wrist + Vector((-.04, -.08, -.02)).lerp(Vector((-.01, .03, .1)), u))


def arm_curve(t, length):
    """Sube en 0,5 s, queda arriba y baja en los ultimos 0,7 s."""
    return smooth(t / .5) * (1 - smooth((t - (length - .7)) / .7))


scene = bpy.context.scene
scene.render.fps = FPS
rig.animation_data_create()
CLIPS = {"Idle": SECONDS, "LevantaBrazo": 3}
actions = {}
for clip, seconds in CLIPS.items():
    action = bpy.data.actions.new(f"Vagabundo_{clip}")
    action.use_fake_user = True
    rig.animation_data.action = action
    frames = FPS * seconds
    for f in range(frames + 1):
        scene.frame_set(f + 1)
        t = f / FPS
        author_pose(t, arm_curve(t, seconds) if clip == "LevantaBrazo" else 0.0)
        for pb in rig.pose.bones:
            for path in ("location", "rotation_quaternion", "scale"):
                pb.keyframe_insert(path, frame=f + 1, group=pb.name)
    actions[clip] = (action, frames + 1)

# la mano izquierda (donde va la botella), en el cuadro 1 del reposo
rig.animation_data.action = actions["Idle"][0]
scene.frame_set(1)
hand = rig.matrix_world @ rig.pose.bones["hand_l"].tail
head_top = (rig.matrix_world @ rig.pose.bones["head"].tail).z

# --- botella de vidrio verde, parada junto a la mano ----------------------------------------------------------------
PROFILE = [(0.0, 0.0), (.036, 0.0), (.038, .01), (.038, .17), (.03, .2), (.014, .235), (.013, .28), (.015, .285), (.015, .29), (0.0, .29)]
bm = bmesh.new()
rings = []
SEG = 20
for r, z in PROFILE:
    rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / SEG), r * math.sin(2 * math.pi * k / SEG), z)) for k in range(SEG)])
for a, b in zip(rings, rings[1:]):
    for k in range(SEG):
        bm.faces.new((a[k], a[(k + 1) % SEG], b[(k + 1) % SEG], b[k]))
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bottle_me = bpy.data.meshes.new("SM_Botella")
bm.to_mesh(bottle_me)
bm.free()
for poly in bottle_me.polygons:
    poly.use_smooth = True
glass = bpy.data.materials.new("M_BotellaVidrio")
glass.use_nodes = True
bsdf = glass.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (.05, .22, .08, 1)
bsdf.inputs["Roughness"].default_value = .12
bsdf.inputs["Metallic"].default_value = .0
bottle_me.materials.append(glass)
bottle = bpy.data.objects.new("SM_Botella", bottle_me)
bpy.context.collection.objects.link(bottle)
BOTTLE_AT = (hand.x + .12, hand.y + .02, 0.0)

preview = os.environ.get("PREVIEW")
if preview:
    bottle.location = BOTTLE_AT
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.color_type = 'TEXTURE'
    scene.render.resolution_x, scene.render.resolution_y = 800, 600
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 2.6
    for clip, frame in (("Idle", 1), ("LevantaBrazo", 45)):
        rig.animation_data.action = actions[clip][0]
        scene.frame_set(frame)
        cam.location = (2.6, -2.2, 2.4)
        cam.rotation_euler = (Vector((0, 0, .15)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(Path(preview) / f"vagabundo_{clip}.png")
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    bottle.location = (0, 0, 0)

# --- exportar: malla con esqueleto (en reposo), las animaciones y la botella ---------------------------------------
DEST.mkdir(parents=True, exist_ok=True)
common = dict(use_selection=True, axis_forward='-Y', axis_up='Z', add_leaf_bones=False, use_armature_deform_only=True,
              apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS')
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = rig
rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
update()
bpy.ops.export_scene.fbx(filepath=str(DEST / f"{NAME}.fbx"), object_types={'MESH', 'ARMATURE'}, path_mode='COPY',
    embed_textures=True, bake_anim=False, mesh_smooth_type='FACE', **common)
body.select_set(False)
for clip, (action, end) in actions.items():
    rig.animation_data.action = action
    scene.frame_start, scene.frame_end = 1, end
    bpy.ops.export_scene.fbx(filepath=str(DEST / f"Vagabundo_{clip}.fbx"), object_types={'ARMATURE'}, bake_anim=True,
        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0, **common)
bpy.ops.object.select_all(action='DESELECT')
bottle.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(DEST / "SM_Botella.fbx"), use_selection=True, object_types={'MESH'},
    apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE', axis_forward='-Y', axis_up='Z')
rig.animation_data.action = actions["Idle"][0]
bpy.ops.wm.save_as_mainfile(filepath=str(DEST / "Vagabundo.blend"))
report = {"source": str(SOURCE), "source_triangles": source_tris, "triangles": sum(len(p.vertices) - 2 for p in body.data.polygons),
          "bones": len(rest), "height_standing_m": HEIGHT, "brightened": brightened, "brighten": BRIGHTEN,
          "clips": {c: {"frames": e, "seconds": CLIPS[c]} for c, (_, e) in actions.items()},
          "lying_head_top_z_m": round(head_top, 2), "bottle_m": [round(v, 3) for v in BOTTLE_AT],
          "materials": [m.name for m in body.data.materials if m]}
(DEST / "vagabundo_build.json").write_text(json.dumps(report, indent=1))
print("### VAGABUNDO", json.dumps(report))
