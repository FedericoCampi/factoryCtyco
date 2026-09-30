"""Blender (background): rig tecJunior.glb (T-pose) and author idle, walk and airborne.

blender -b --factory-startup -P Scripts/author_tecjunior_rig.py

The source is an AI-generated mesh of ~700k triangles in 3861 loose pieces,
normalised to 1 m. It is decimated for gameplay and scaled to HEIGHT. Joint
positions are measured from the mesh itself. Because heat weighting fails on
loose pieces, weights are solved on a watertight voxel proxy and transferred
to the real mesh. Outputs go to SourceAssets/TecJunior (FBX per clip, .blend,
report and preview renders).
"""
import json, math
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "SourceAssets/TecJunior/tecJunior.glb"
DEST = ROOT / "SourceAssets/TecJunior"
HEIGHT = 1.70           # metres
DECIMATE = 0.12         # ~84k triangles
FPS = 30
PREFIX = "TecJunior"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
body = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
bpy.context.view_layer.objects.active = body; body.select_set(True)
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(bpy.context.scene.objects):
    if o is not body: bpy.data.objects.remove(o)
body.name = f"{PREFIX}_Skinned"
bm = bmesh.new(); bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
bm.to_mesh(body.data); bm.free()
mod = body.modifiers.new("GameplayTopology", 'DECIMATE'); mod.ratio = DECIMATE; mod.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier=mod.name)
body.data.transform(Matrix.Scale(HEIGHT, 4)); body.data.update()

co = np.empty(len(body.data.vertices) * 3, dtype=np.float64)
body.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3) / HEIGHT   # measure in normalised units

# ---------------------------------------------------------------- landmarks --
def centroid(mask):
    pts = co[mask]
    return pts.mean(axis=0) if len(pts) else None

x_max = co[:, 0].max()
def arm_centre(x):          # centre of the left arm's cross-section at x
    c = centroid((co[:, 0] > x - .008) & (co[:, 0] < x + .008) & (co[:, 2] > .55))
    return c
shoulder_x, wrist_x = .135, x_max - .125
elbow_x = shoulder_x + .52 * (wrist_x - shoulder_x)
sh, el, wr = arm_centre(.20), arm_centre(elbow_x), arm_centre(wrist_x)
hand_end = arm_centre(x_max - .03)

def leg_centre(z):          # centre of the left leg's cross-section at height z
    return centroid((co[:, 0] > .01) & (co[:, 2] > z - .01) & (co[:, 2] < z + .01))
hip_z, knee_z, ankle_z = .465, .275, .085
hip, knee, ankle = leg_centre(.40), leg_centre(knee_z), leg_centre(ankle_z)
sole = co[(co[:, 0] > .01) & (co[:, 2] < .03)]
toe_tip_y = sole[:, 1].min()
heel_y = sole[:, 1].max()

def torso(z):
    return centroid((np.abs(co[:, 0]) < .09) & (co[:, 2] > z - .01) & (co[:, 2] < z + .01))
pelvis_y, chest_y, neck_y = torso(.50)[1], torso(.62)[1], torso(.74)[1]
head_c = centroid(co[:, 2] > .80)
landmarks = {"shoulder": sh, "elbow": el, "wrist": wr, "hand_end": hand_end, "hip": hip,
             "knee": knee, "ankle": ankle, "toe_tip_y": toe_tip_y, "heel_y": heel_y, "x_max": x_max}

rest = {}
def bone(name, head, tail, parent=None):
    rest[name] = (Vector(head) * HEIGHT, Vector(tail) * HEIGHT, parent)
bone("root", (0, 0, 0), (0, 0, .08))
bone("pelvis", (0, pelvis_y, .48), (0, pelvis_y, .54), "root")
bone("spine", (0, pelvis_y, .54), (0, chest_y, .62), "pelvis")
bone("chest", (0, chest_y, .62), (0, neck_y, .735), "spine")
bone("neck", (0, neck_y, .735), (0, head_c[1], .775), "chest")
bone("head", (0, head_c[1], .775), (0, head_c[1], .99), "neck")
for side, s in (("l", 1), ("r", -1)):
    bone(f"clavicle_{side}", (s * .03, chest_y, sh[2]), (s * shoulder_x, sh[1], sh[2]), "chest")
    bone(f"upperarm_{side}", (s * shoulder_x, sh[1], sh[2]), (s * elbow_x, el[1], el[2]), f"clavicle_{side}")
    bone(f"lowerarm_{side}", (s * elbow_x, el[1], el[2]), (s * wrist_x, wr[1], wr[2]), f"upperarm_{side}")
    bone(f"hand_{side}", (s * wrist_x, wr[1], wr[2]), (s * (x_max - .01), hand_end[1], hand_end[2]), f"lowerarm_{side}")
    bone(f"thigh_{side}", (s * hip[0], hip[1], hip_z), (s * knee[0], knee[1], knee_z), "pelvis")
    bone(f"shin_{side}", (s * knee[0], knee[1], knee_z), (s * ankle[0], ankle[1], ankle_z), f"thigh_{side}")
    ball_y = toe_tip_y + .045
    bone(f"foot_{side}", (s * ankle[0], ankle[1], ankle_z), (s * ankle[0], ball_y, .025), f"shin_{side}")
    bone(f"toe_{side}", (s * ankle[0], ball_y, .025), (s * ankle[0], toe_tip_y, .02), f"foot_{side}")

arm_data = bpy.data.armatures.new(f"{PREFIX}_Skeleton")
rig = bpy.data.objects.new(f"{PREFIX}_Rig", arm_data)
bpy.context.collection.objects.link(rig)
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
for name, (h, t, parent) in rest.items():
    eb = arm_data.edit_bones.new(name); eb.head, eb.tail = h, t; eb.roll = 0
    if parent: eb.parent = arm_data.edit_bones[parent]
    eb.use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')

# ------------------------------------------------------ weights via proxy ----
proxy = body.copy(); proxy.data = body.data.copy(); proxy.name = "WeightProxy"
bpy.context.collection.objects.link(proxy)
proxy.data.remesh_voxel_size = .007 * HEIGHT
bpy.ops.object.select_all(action='DESELECT'); proxy.select_set(True); bpy.context.view_layer.objects.active = proxy
bpy.ops.object.voxel_remesh()
dec = proxy.modifiers.new("d", 'DECIMATE'); dec.ratio = min(1.0, 60000 / max(1, len(proxy.data.polygons)))
bpy.ops.object.modifier_apply(modifier=dec.name)
bpy.ops.object.select_all(action='DESELECT'); proxy.select_set(True); rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
proxy_groups = {g.name for g in proxy.vertex_groups}
missing = [n for n in rest if n != "root" and n not in proxy_groups]
if missing: raise RuntimeError(f"Heat weighting skipped bones: {missing}")

for name in rest:
    body.vertex_groups.new(name=name)
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); bpy.context.view_layer.objects.active = body
dt = body.modifiers.new("WeightTransfer", 'DATA_TRANSFER')
dt.object = proxy; dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}
dt.vert_mapping = 'POLYINTERP_NEAREST'; dt.layers_vgroup_select_src = 'ALL'; dt.layers_vgroup_select_dst = 'NAME'
bpy.ops.object.modifier_apply(modifier=dt.name)
bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
bpy.data.objects.remove(proxy)
unweighted = sum(1 for v in body.data.vertices if not any(g.weight > 1e-4 for g in v.groups))
body.parent = rig
arm = body.modifiers.new(f"{PREFIX}_Skin", 'ARMATURE'); arm.object = rig; arm.use_deform_preserve_volume = True

# ------------------------------------------------------------- animation ------
# Human gait, authored procedurally: heel strike -> flat foot -> heel rise and
# toe-off with the toe staying on the ground; pelvis bob, weight shift, yaw and
# hip drop; chest counter-rotation; stable head; arms that lag the legs and
# bend more at the elbow when swinging forward. Poses are set in armature
# space, parent first: each child's posed head follows its parent.
for pb in rig.pose.bones: pb.rotation_mode = 'QUATERNION'
scene = bpy.context.scene; scene.render.fps = FPS
H = HEIGHT
FORWARD = Vector((0, -1, 0))

def update(): bpy.context.view_layer.update()
def reset_pose():
    for pb in rig.pose.bones: pb.matrix_basis.identity()
def rot(pitch=0.0, roll=0.0, yaw=0.0):
    """World-space delta. +pitch leans forward (top toward -Y), +roll raises the +X side, +yaw turns +X toward +Y."""
    return Euler((math.radians(pitch), math.radians(-roll), math.radians(yaw)), 'XYZ').to_quaternion()
def place(name, head, rotation):
    rest_q = arm_data.bones[name].matrix_local.to_quaternion()
    rig.pose.bones[name].matrix = Matrix.Translation(head) @ (rotation @ rest_q).to_matrix().to_4x4()
    update()
def aim(name, head, tail):
    h0, t0, _ = rest[name]
    place(name, head, (t0 - h0).rotation_difference(tail - head))
def posed_head(name): return rig.pose.bones[name].head.copy()
def length(name): return (rest[name][1] - rest[name][0]).length
def smooth(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)

def solve_knee(hip_p, ankle_p, la, lb):
    delta = ankle_p - hip_p
    dist = min(delta.length, la + lb - 1e-4)
    axis = delta.normalized()
    bend = (FORWARD - axis * FORWARD.dot(axis)).normalized()     # knees point forward
    along = (la * la - lb * lb + dist * dist) / (2 * dist)
    return hip_p + axis * along + bend * math.sqrt(max(0, la * la - along * along))

def foot_pose(side, dy, pitch, lift, pivot):
    """Foot rotated by pitch (+ = toes up) about the heel or the ball, shifted dy along Y and lifted."""
    a0, b0 = rest[f"foot_{side}"][0], rest[f"toe_{side}"][0]
    heel = Vector((a0.x, heel_y * H, 0))
    q = Quaternion((1, 0, 0), -math.radians(pitch))
    shift = Vector((0, dy, lift))
    around = heel if pivot == "heel" else b0
    return around + shift + q @ (a0 - around), q, around + shift + q @ (b0 - around)

def foot_blend(side, dy, pitch, lift, u):
    """Swing: the pivot moves from the ball (toe-off) to the heel (strike) so both ends stay continuous."""
    a1, q, b1 = foot_pose(side, dy, pitch, 0, "ball")
    a2, _, b2 = foot_pose(side, dy, pitch, 0, "heel")
    up = Vector((0, 0, lift))
    return a1.lerp(a2, u) + up, q, b1.lerp(b2, u) + up

def gait_foot(side, c, g):
    """Foot target for gait g at leg phase c (0 = heel strike with the foot forward)."""
    if c < g["stance"]:
        k = c / g["stance"]
        dy = -g["S"] + 2 * g["S"] * k
        if k < .12:
            pitch, pivot = g["strike"] * (1 - smooth(k / .12)), "heel"
        elif k < g["rise"]:
            pitch, pivot = 0.0, "heel"
        else:
            pitch, pivot = -g["toe_off"] * ((k - g["rise"]) / (1 - g["rise"])) ** 1.6, "ball"
        ankle, q, ball = foot_pose(side, dy, pitch, 0, pivot)
        return ankle, q, ball, (Quaternion() if pitch < 0 else q)   # the toe stays flat during heel rise
    u = (c - g["stance"]) / (1 - g["stance"])
    dy = g["S"] - 2 * g["S"] * smooth(u) + g.get("kick", 0) * math.sin(math.pi * u) * (1 - u)
    pitch = -g["toe_off"] * (1 - u) ** 2 + g["strike"] * u ** 1.5
    lift = g["lift"] * math.sin(math.pi * u ** .75)
    ankle, q, ball = foot_blend(side, dy, pitch, lift, smooth(u))
    return ankle, q, ball, Quaternion().slerp(q, smooth(u * 3))

def pose_leg(side, ankle_p, foot_q, ball_p, toe_q):
    hip_p = posed_head(f"thigh_{side}")
    knee_p = solve_knee(hip_p, ankle_p, length(f"thigh_{side}"), length(f"shin_{side}"))
    aim(f"thigh_{side}", hip_p, knee_p)
    aim(f"shin_{side}", knee_p, ankle_p)
    place(f"foot_{side}", ankle_p, foot_q)
    place(f"toe_{side}", ball_p, toe_q)

def pose_torso(offset, pelvis, spine, chest, neck, head):
    place("pelvis", rest["pelvis"][0] + offset, pelvis)
    for name, q in (("spine", spine), ("chest", chest), ("neck", neck), ("head", head)):
        place(name, posed_head(name), q)

def pose_arm(side, s, chest_q, swing, spread, elbow, wrist=6.0, inward=0.0):
    """swing: + forward (deg); elbow: flexion (deg); inward: forearm yaw toward the body's midline."""
    shoulder = posed_head(f"upperarm_{side}")
    down = Vector((s * math.sin(math.radians(spread)), 0, -math.cos(math.radians(spread))))
    def bent(deg, turn=0.0):
        d = Quaternion((1, 0, 0), -math.radians(deg)) @ down
        return chest_q @ (Quaternion((0, 0, 1), -s * math.radians(turn)) @ d)
    upper, fore, hand = bent(swing), bent(swing + elbow, inward), bent(swing + elbow + wrist, inward)
    elbow_p = shoulder + upper * length(f"upperarm_{side}")
    wrist_p = elbow_p + fore * length(f"lowerarm_{side}")
    aim(f"upperarm_{side}", shoulder, elbow_p)
    aim(f"lowerarm_{side}", elbow_p, wrist_p)
    aim(f"hand_{side}", wrist_p, wrist_p + hand * length(f"hand_{side}"))

# Carrying (27/09/2026): both hands hold a dispatch box (0.40 x 0.40 x 0.32 m) in front of the body.
# The box centre is fixed to the chest; the wrists sit on its sides and the elbows point down and out.
# In Unreal the box is placed from the two hand bones (UFactoryGatheringComponent), so it follows this pose.
BOX_HALF_W = 0.20
CARRY_CENTRE = Vector((0, -0.31, 1.02))     # box centre in the rest pose (m, forward is -Y)
CARRY = False

def pose_arm_ik(side, s, chest_q, wrist_target, hand_dir):
    shoulder = posed_head(f"upperarm_{side}")
    la, lb = length(f"upperarm_{side}"), length(f"lowerarm_{side}")
    delta = wrist_target - shoulder
    dist = min(delta.length, la + lb - 1e-4)
    axis = delta.normalized()
    pole = chest_q @ Vector((s * .55, .45, -1)).normalized()      # elbows out, back and down
    bend = (pole - axis * pole.dot(axis)).normalized()
    along = (la * la - lb * lb + dist * dist) / (2 * dist)
    elbow_p = shoulder + axis * along + bend * math.sqrt(max(0, la * la - along * along))
    wrist_p = elbow_p + (wrist_target - elbow_p).normalized() * lb
    aim(f"upperarm_{side}", shoulder, elbow_p)
    aim(f"lowerarm_{side}", elbow_p, wrist_p)
    h0, t0, _ = rest[f"hand_{side}"]
    # palms turned toward the box sides (the rest palms face down)
    place(f"hand_{side}", wrist_p, Quaternion(hand_dir, s * math.radians(PALM_ROLL)) @ (t0 - h0).rotation_difference(hand_dir))

PALM_ROLL = 80.0

def pose_carry_arms(chest_q):
    centre = posed_head("chest") + chest_q @ (CARRY_CENTRE - rest["chest"][0])
    for side, s in (("l", 1), ("r", -1)):
        wrist = centre + chest_q @ Vector((s * (BOX_HALF_W + .035), .07, -.02))
        pose_arm_ik(side, s, chest_q, wrist, (chest_q @ Vector((-s * .12, -1, -.08))).normalized())

WALK = dict(frames=20, stance=.60, S=.165 * H, strike=14, rise=.62, toe_off=32, lift=.05 * H)
RUN = dict(frames=18, stance=.36, S=.17 * H, strike=6, rise=.45, toe_off=40, lift=.16 * H, kick=.10 * H)
def speed_cm(g): return round(2 * g["S"] / (g["stance"] * g["frames"] / FPS) * 100)
WALK_SPEED_CM, RUN_SPEED_CM = speed_cm(WALK), speed_cm(RUN)

def author_pose(t, kind):
    global CARRY
    CARRY = kind.startswith("Carry")
    kind = kind[len("Carry"):] if CARRY else kind
    reset_pose()
    cos = lambda phase: math.cos(2 * math.pi * phase)
    sin = lambda phase: math.sin(2 * math.pi * phase)
    if kind in ("Walk", "Run"):
        g = WALK if kind == "Walk" else RUN
        if CARRY and kind == "Run": g = dict(RUN, lift=RUN["lift"] * .5, kick=RUN["kick"] * .5)   # knees stay under the box
        mid = g["stance"] / 2                  # left midstance: body highest when walking, lowest when running
        if kind == "Walk":
            z = -.022 * H + .012 * H * cos(2 * (t - mid))
            yaw, roll, lean, sway = -6 * cos(t), -4 * cos(t - mid), 4, .010 * H * cos(t - mid)
        else:
            z = -.035 * H - .012 * H * cos(2 * (t - mid))
            yaw, roll, lean, sway = -8 * cos(t), -3 * cos(t - mid), 11, .006 * H * cos(t - mid)
        if CARRY: lean -= 3 if kind == "Walk" else 8         # upright under the load (running: knees clear the box)
        chest_q = rot(lean + 2, -roll * .4, -yaw * (.3 if CARRY else 1.1))   # shoulders counter the hips
        pose_torso(Vector((sway, 0, z)), rot(lean, roll, yaw), rot(lean + 1, roll * .3, yaw * .2),
                   chest_q, rot(lean * .4, -roll * .2, -yaw * .5), rot(0, 0, 0))
        for side, offset in (("l", 0.0), ("r", .5)):
            pose_leg(side, *gait_foot(side, (t - offset) % 1, g))
        for side, s in (() if CARRY else (("l", 1), ("r", -1))):
            lag = t - .04                                        # arms follow the legs slightly late
            if kind == "Walk":
                swing = -s * 20 * cos(lag)
                pose_arm(side, s, chest_q, swing, 9, 18 + 14 * max(0, swing) / 20)
            else:
                swing = -s * 34 * cos(lag)
                pose_arm(side, s, chest_q, swing, 12, 75 + 12 * max(0, swing) / 34, 4, 15)
    elif kind == "Idle":
        sway, roll = .012 * H * sin(t), -2 * sin(t)             # slow weight shift; the free side's hip drops
        breath = math.sin(4 * math.pi * t)                     # two breaths per 4 s loop
        chest_q = rot(2 - 1.2 * breath, -roll * .5, -1.5 * sin(t))
        pose_torso(Vector((sway, 0, -.006 * H)), rot(2, roll, 1.5 * sin(t)), rot(2.5, roll * .3, 0),
                   chest_q, rot(1, 0, 2 * sin(t + .15)), rot(-1, 0, 4 * sin(t + .15)))
        for side in ("l", "r"):
            pose_leg(side, *gait_foot(side, WALK["stance"] * .5, dict(WALK, S=0)))
        for side, s in (() if CARRY else (("l", 1), ("r", -1))):
            pose_arm(side, s, chest_q, 2 * sin(t + (0 if s > 0 else .5)), 8 + breath, 12)
    else:  # Airborne: one knee up, the other leg trailing, arms out for balance
        wobble = sin(t)
        chest_q = rot(10, 0, 3 * wobble)
        pose_torso(Vector((0, 0, -.02 * H)), rot(8, 0, 0), rot(9, 0, 0), chest_q, rot(4, 0, 0), rot(0, 0, 0))
        pose_leg("l", *foot_pose("l", -.06 * H, 10, .13 * H, "heel"), Quaternion())
        pose_leg("r", *foot_pose("r", .07 * H, -20, .09 * H, "ball"), Quaternion())
        pose_arm("l", 1, chest_q, 25 + 4 * wobble, 38, 35)
        pose_arm("r", -1, chest_q, -12 - 4 * wobble, 38, 30)
    if CARRY: pose_carry_arms(chest_q)
    update()

CLIPS = (("Idle", 120), ("Walk", WALK["frames"]), ("Run", RUN["frames"]), ("Airborne", 30),
         ("CarryIdle", 120), ("CarryWalk", WALK["frames"]), ("CarryRun", RUN["frames"]))
actions = {}
rig.animation_data_create()
for kind, frames in CLIPS:
    action = bpy.data.actions.new(f"{PREFIX}_{kind}"); action.use_fake_user = True
    rig.animation_data.action = action
    for f in range(frames + 1):
        scene.frame_set(f + 1)
        author_pose(f / frames, kind)
        for pb in rig.pose.bones:
            for path in ("location", "rotation_quaternion", "scale"):
                pb.keyframe_insert(path, frame=f + 1, group=pb.name)
    actions[kind] = (action, frames + 1)

# ---------------------------------------------------------------- export ------
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); body.select_set(True)
bpy.context.view_layer.objects.active = rig
rig.animation_data.action = None; reset_pose()
common = dict(use_selection=True, axis_forward='-Y', axis_up='Z', add_leaf_bones=False, use_armature_deform_only=True)
bpy.ops.export_scene.fbx(filepath=str(DEST / f"{PREFIX}_Skeletal.fbx"), object_types={'MESH', 'ARMATURE'},
    path_mode='COPY', embed_textures=True, bake_anim=False, mesh_smooth_type='FACE', **common)
body.select_set(False)
for kind, (action, end) in actions.items():
    rig.animation_data.action = action; scene.frame_start, scene.frame_end = 1, end
    bpy.ops.export_scene.fbx(filepath=str(DEST / f"{PREFIX}_{kind}.fbx"), object_types={'ARMATURE'},
        bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_simplify_factor=0, **common)
rig.animation_data.action = actions["Walk"][0]; scene.frame_start, scene.frame_end = 1, WALK["frames"] + 1
bpy.ops.wm.save_as_mainfile(filepath=str(DEST / f"{PREFIX}_Rig.blend"))

report = {"source": str(SOURCE), "height_m": HEIGHT, "bones": len(rest),
          "triangles": sum(len(p.vertices) - 2 for p in body.data.polygons),
          "vertices": len(body.data.vertices), "unweighted_vertices": unweighted,
          "authored_walk_speed_cm_s": WALK_SPEED_CM, "authored_run_speed_cm_s": RUN_SPEED_CM,
          "animations": {k: {"frames": e, "duration_s": (e - 1) / FPS} for k, (_, e) in actions.items()},
          "landmarks_normalised": {k: (list(map(float, v)) if hasattr(v, "__len__") else float(v)) for k, v in landmarks.items()}}
(DEST / "rig_report.json").write_text(json.dumps(report, indent=2))
print("### RIG", json.dumps(report))

# --------------------------------------------------------------- previews -----
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'; scene.display.shading.color_type = 'TEXTURE'
scene.render.resolution_x, scene.render.resolution_y = 520, 640
cam_data = bpy.data.cameras.new("cam"); cam_data.type = 'ORTHO'; cam_data.ortho_scale = HEIGHT * 1.25
cam = bpy.data.objects.new("cam", cam_data); scene.collection.objects.link(cam); scene.camera = cam
views = {"front": ((0, -6, HEIGHT / 2), (90, 0, 0)), "side": ((6, 0, HEIGHT / 2), (90, 0, 90)),
         "three_quarter": ((4.2, -4.2, HEIGHT * .5 + 1.2), (74, 0, 45))}
shots = [("Idle", 1, "front"), ("Idle", 31, "front")] + \
        [("Walk", f, "side") for f in (1, 4, 7, 10, 13, 16)] + [("Run", f, "side") for f in (1, 4, 7, 10)] + \
        [("Walk", 6, "three_quarter"), ("Run", 6, "three_quarter"), ("Airborne", 1, "three_quarter")] +         [("CarryIdle", 1, "three_quarter"), ("CarryWalk", 6, "side"), ("CarryWalk", 6, "three_quarter"), ("CarryRun", 6, "three_quarter")]
for kind, frame, view in shots:
    rig.animation_data.action = actions[kind][0]; scene.frame_set(frame)
    cam.location, rot = views[view]; cam.rotation_euler = [math.radians(a) for a in rot]
    scene.render.filepath = str(DEST / f"preview_{kind.lower()}_{frame:02d}_{view}.png")
    bpy.ops.render.render(write_still=True)
