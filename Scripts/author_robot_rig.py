"""Author a mechanical humanoid rig, idle, planted-foot walk and airborne pose."""
import json
import math
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix, Quaternion

root = Path(__file__).resolve().parent.parent
dest = root / "SourceAssets/Robot1/Rigged"
dest.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(dest.parent / "robot1.glb"))
robot = next(obj for obj in bpy.context.scene.objects if obj.type == 'MESH')
bpy.context.view_layer.objects.active = robot
robot.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
robot.name = "Robot1_Skinned"
bm = bmesh.new()
bm.from_mesh(robot.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.00001)
bm.to_mesh(robot.data)
bm.free()
decimate = robot.modifiers.new('GameplayTopology', 'DECIMATE')
decimate.ratio = .26
decimate.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier=decimate.name)
coords = np.empty(len(robot.data.vertices)*3, dtype=np.float32)
robot.data.vertices.foreach_get('co', coords)
coords = coords.reshape(-1,3)
normalized = coords.copy()
coords *= 1.8
robot.data.vertices.foreach_set('co', coords.ravel())
robot.data.update()

rest = {}
def bone(name, head, tail, parent=None):
    rest[name] = (Vector(head)*1.8, Vector(tail)*1.8, parent)
bone('root',(0,0,0),(0,0,.08))
bone('pelvis',(0,.02,.50),(0,.02,.55),'root')
bone('spine',(0,.02,.55),(0,.02,.65),'pelvis')
bone('chest',(0,.02,.65),(0,.02,.79),'spine')
bone('neck',(0,.02,.79),(0,.02,.85),'chest')
bone('head',(0,.02,.85),(0,.02,.98),'neck')
for side, sign in [('l',1),('r',-1)]:
    bone(f'clavicle_{side}',(0,.025,.765),(sign*.177,.025,.765),'chest')
    bone(f'upperarm_{side}',(sign*.177,.025,.765),(sign*.23,.040,.605),f'clavicle_{side}')
    bone(f'lowerarm_{side}',(sign*.23,.040,.605),(sign*.275,-.012,.445),f'upperarm_{side}')
    bone(f'hand_{side}',(sign*.275,-.012,.445),(sign*.282,-.038,.355),f'lowerarm_{side}')
    bone(f'thigh_{side}',(sign*.105,.025,.505),(sign*.126,-.017,.292),'pelvis')
    bone(f'shin_{side}',(sign*.126,-.017,.292),(sign*.158,.025,.105),f'thigh_{side}')
    bone(f'foot_{side}',(sign*.158,.025,.105),(sign*.158,-.105,.040),f'shin_{side}')
    bone(f'toe_{side}',(sign*.158,-.105,.040),(sign*.158,-.145,.035),f'foot_{side}')
arm_data = bpy.data.armatures.new('Robot1_Skeleton')
rig = bpy.data.objects.new('Robot1_Rig', arm_data)
bpy.context.collection.objects.link(rig)
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
for name, (head, tail, parent) in rest.items():
    eb = arm_data.edit_bones.new(name)
    eb.head, eb.tail = head, tail
    if parent:
        eb.parent = arm_data.edit_bones[parent]
    eb.use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')
rig.show_in_front = True
robot.parent = rig
modifier = robot.modifiers.new('Robot1_Skin', 'ARMATURE')
modifier.object = rig
modifier.use_deform_preserve_volume = True
groups = {name:robot.vertex_groups.new(name=name) for name in rest}

def blend(z, boundary, width, low, high):
    alpha = max(0, min(1, (z-boundary)/width + .5))
    alpha = alpha*alpha*(3-2*alpha)
    return {low:1-alpha, high:alpha}

counts = {name:0 for name in rest}
for i, (x,y,z) in enumerate(normalized):
    a = abs(x)
    side = 'l' if x >= 0 else 'r'
    # Narrow transition bands lie inside the robot's dark hinges. The armor
    # plates receive a single rigid influence away from these joints.
    is_arm = (z > .25 and a > (.157 if z > .655 else .197))
    if is_arm:
        if z >= .775:
            weights = {f'upperarm_{side}':1}
        elif z > .625:
            weights = {f'upperarm_{side}':1}
        elif z > .582:
            weights = blend(z,.605,.040,f'lowerarm_{side}',f'upperarm_{side}')
        elif z > .465:
            weights = {f'lowerarm_{side}':1}
        elif z > .425:
            weights = blend(z,.445,.040,f'hand_{side}',f'lowerarm_{side}')
        else:
            weights = {f'hand_{side}':1}
    elif z < .505 and (z < .43 or a > .072):
        if z < .085:
            weights = {f'foot_{side}':1}
        elif z < .127:
            weights = blend(z,.106,.032,f'foot_{side}',f'shin_{side}')
        elif z < .270:
            weights = {f'shin_{side}':1}
        elif z < .32:
            weights = blend(z,.295,.050,f'shin_{side}',f'thigh_{side}')
        elif z < .475:
            weights = {f'thigh_{side}':1}
        else:
            weights = blend(z,.496,.040,f'thigh_{side}','pelvis')
    elif z > .845:
        weights = {'head':1}
    elif z > .81:
        weights = blend(z,.834,.022,'neck','head')
    elif z > .60:
        weights = {'chest':1}
    elif z > .555:
        weights = blend(z,.575,.038,'spine','chest')
    elif z > .525:
        weights = blend(z,.541,.032,'pelvis','spine')
    else:
        weights = {'pelvis':1}
    for name, weight in weights.items():
        if weight > .0001:
            groups[name].add([i],float(weight),'REPLACE')
            counts[name] += 1

for pb in rig.pose.bones:
    pb.rotation_mode = 'QUATERNION'
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene.render.fps = 30

def pose_segment(name, head, tail):
    original_head, original_tail, _ = rest[name]
    aim = (original_tail-original_head).rotation_difference(tail-head)
    rotation = aim @ arm_data.bones[name].matrix_local.to_quaternion()
    rig.pose.bones[name].matrix = Matrix.Translation(head) @ rotation.to_matrix().to_4x4()
    bpy.context.view_layer.update()

def reset_pose():
    for pb in rig.pose.bones:
        pb.matrix_basis.identity()

def solve_knee(hip, ankle, thigh_len, shin_len):
    delta = ankle-hip
    distance = min(delta.length, thigh_len+shin_len-.0001)
    axis = delta.normalized()
    bend = Vector((0,-1,0))
    bend = (bend-axis*bend.dot(axis)).normalized()
    along = (thigh_len**2-shin_len**2+distance**2)/(2*distance)
    height = math.sqrt(max(0,thigh_len**2-along**2))
    return hip+axis*along+bend*height

def author_pose(t, kind):
    reset_pose()
    if kind == 'Idle':
        offset = Vector((0,0,.0025*math.sin(t*2*math.pi)))*1.8
    elif kind == 'Walk':
        offset = Vector((0,0,-.024+.005*math.cos(t*4*math.pi)))*1.8
    else:
        offset = Vector((0,0,-.022))*1.8
    rig.pose.bones['pelvis'].matrix = Matrix.Translation(offset) @ arm_data.bones['pelvis'].matrix_local
    bpy.context.view_layer.update()
    for side, sign in [('l',1),('r',-1)]:
        cycle = (t+(0 if side=='l' else .5)) % 1
        hip = rest[f'thigh_{side}'][0] + offset
        original_ankle = rest[f'foot_{side}'][0]
        ankle = original_ankle.copy()
        if kind == 'Walk':
            if cycle < .5:
                ankle.y += (-.15+.30*(cycle/.5))*1.8
            else:
                u = (cycle-.5)*2
                ankle.y += (.15-.30*(u*u*(3-2*u)))*1.8
                ankle.z += .075*math.sin(math.pi*u)*1.8
        elif kind == 'Airborne':
            ankle.y += .07*1.8
            ankle.z += .06*1.8
        length_a = (rest[f'thigh_{side}'][1]-rest[f'thigh_{side}'][0]).length
        length_b = (rest[f'shin_{side}'][1]-rest[f'shin_{side}'][0]).length
        knee = solve_knee(hip,ankle,length_a,length_b)
        pose_segment(f'thigh_{side}',hip,knee)
        pose_segment(f'shin_{side}',knee,ankle)
        foot_delta = ankle-original_ankle
        for part in ['foot','toe']:
            name=f'{part}_{side}'
            rig.pose.bones[name].matrix=Matrix.Translation(foot_delta) @ arm_data.bones[name].matrix_local
            bpy.context.view_layer.update()
        shoulder = rest[f'upperarm_{side}'][0] + offset
        swing = sign*.26*math.cos(t*2*math.pi) if kind=='Walk' else 0
        if kind=='Airborne': swing=-.45
        qa = Quaternion((1,0,0),swing)
        qb = Quaternion((1,0,0),swing-.075 if kind=='Walk' else swing)
        elbow = shoulder+qa@(rest[f'upperarm_{side}'][1]-rest[f'upperarm_{side}'][0])
        wrist = elbow+qb@(rest[f'lowerarm_{side}'][1]-rest[f'lowerarm_{side}'][0])
        hand_end = wrist+qb@(rest[f'hand_{side}'][1]-rest[f'hand_{side}'][0])
        pose_segment(f'upperarm_{side}',shoulder,elbow)
        pose_segment(f'lowerarm_{side}',elbow,wrist)
        pose_segment(f'hand_{side}',wrist,hand_end)
    bpy.context.view_layer.update()

actions = {}
rig.animation_data_create()
for kind, frames in [('Idle',60),('Walk',24),('Airborne',30)]:
    action = bpy.data.actions.new(f'Robot1_{kind}')
    action.use_fake_user = True
    rig.animation_data.action = action
    for frame in range(frames+1):
        scene.frame_set(frame+1)
        author_pose(frame/frames,kind)
        for pb in rig.pose.bones:
            pb.keyframe_insert('location',frame=frame+1,group=pb.name)
            pb.keyframe_insert('rotation_quaternion',frame=frame+1,group=pb.name)
            pb.keyframe_insert('scale',frame=frame+1,group=pb.name)
    actions[kind] = (action,frames+1)

bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
robot.select_set(True)
bpy.context.view_layer.objects.active=rig
rig.animation_data.action=None
reset_pose()
bpy.ops.export_scene.fbx(filepath=str(dest/'Robot1_Skeletal.fbx'),use_selection=True,
    object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',
    path_mode='COPY',embed_textures=True,add_leaf_bones=False,bake_anim=False,
    mesh_smooth_type='FACE',use_armature_deform_only=True)
robot.select_set(False)
for kind,(action,end) in actions.items():
    rig.animation_data.action=action
    scene.frame_start=1
    scene.frame_end=end
    bpy.ops.export_scene.fbx(filepath=str(dest/f'Robot1_{kind}.fbx'),use_selection=True,
        object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_simplify_factor=0,use_armature_deform_only=True)
rig.animation_data.action=actions['Walk'][0]
scene.frame_start=1
scene.frame_end=25
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(dest/'Robot1_Rig.blend'))
report={'bones':len(rest),'weighted_vertices':len(robot.data.vertices),
    'triangles':sum(len(p.vertices)-2 for p in robot.data.polygons),'height_m':1.8,
    'animations':{kind:{'frames':end,'duration_s':(end-1)/30} for kind,(_,end) in actions.items()},
    'authored_walk_speed_cm_s':135,'bone_influences':counts}
(dest/'rig_report.json').write_text(json.dumps(report,indent=2))

scene.render.engine='CYCLES'
scene.cycles.samples=16
scene.render.resolution_x=600
scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('RigPreview')
scene.world.color=(.3,.3,.3)
for location,energy in [((3,-5,5),700),((-3,-2,3),550),((0,4,4),600)]:
    bpy.ops.object.light_add(type='AREA',location=location)
    obj=bpy.context.object
    obj.data.energy=energy
    obj.data.size=4
    obj.rotation_euler=(Vector((0,0,.9))-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(2,-5,2))
camera=bpy.context.object
camera.data.type='ORTHO'
camera.data.ortho_scale=2.2
camera.rotation_euler=(Vector((0,0,.9))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera=camera
for frame in [1,7,13,19]:
    scene.frame_set(frame)
    scene.render.filepath=str(dest/f'walk_{frame:02d}.png')
    bpy.ops.render.render(write_still=True)
print(json.dumps(report))
