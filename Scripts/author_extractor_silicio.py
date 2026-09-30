"""Blender: arma el Extractor de Silicio animado para Unreal (malla con esqueleto rigido).

Entrada: SourceAssets/ExtractorSilicio/Extractor_Silicio_v1.blend (Cuerpo + Tambor + Varilla,
animados por objeto). Salida: extractor_unreal.fbx y extractor_build.json en la misma carpeta.

Huesos: Root (cuerpo), Tambor (oscila +-35 grados en X), Varilla (gira en Z). Loop de 240
frames a 30 fps. La mirilla es el material M_Mirilla; su pulso se hace en Unreal.

blender -b --factory-startup -P Scripts/author_extractor_silicio.py
"""
import json
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

HEIGHT_M = 2.5  # altura en el juego (TecJunior mide 1,70 m)
DECIMATE = 0.22  # ~700k -> ~150k triangulos
folder = Path(__file__).resolve().parent.parent / "SourceAssets/ExtractorSilicio"
bpy.ops.wm.open_mainfile(filepath=str(folder / "Extractor_Silicio_v1.blend"))
scn = bpy.context.scene
body, drum, rod = (bpy.data.objects[n] for n in ("Extractor_Cuerpo", "Tambor", "Varilla"))
scale = HEIGHT_M / body.dimensions.z

# muestrear la animacion de cada pieza (rotacion local respecto del cuerpo)
frames = range(scn.frame_start, scn.frame_end + 1)
samples = {}
for o in (drum, rod):
    samples[o.name] = []
    for f in frames:
        scn.frame_set(f)
        samples[o.name].append(o.rotation_euler.copy())
scn.frame_set(scn.frame_start)
pivots = {o.name: o.matrix_world.translation.copy() for o in (drum, rod)}

# armadura en la escala final
arm_data = bpy.data.armatures.new("SK_ExtractorSilicio")
arm = bpy.data.objects.new("ExtractorSilicio", arm_data)
scn.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
root = arm_data.edit_bones.new("Root"); root.head = (0, 0, 0); root.tail = (0, 0, 0.3 * scale)
for name, axis in (("Tambor", Vector((0.05, 0, 0))), ("Varilla", Vector((0, 0, 0.05)))):
    b = arm_data.edit_bones.new(name)
    b.head = pivots[name] * scale; b.tail = (pivots[name] + axis) * scale
    b.parent = root
bpy.ops.object.mode_set(mode="OBJECT")

# bajar las piezas a la pose de reposo, unir y pesar cada una a su hueso
for o in (drum, rod):
    o.animation_data_clear(); o.rotation_euler = (0, 0, 0)
    o.parent = None; o.matrix_world = Matrix.Translation(pivots[o.name])
for o in (body, drum, rod):
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    o.data.transform(Matrix.Scale(scale, 4))
    vg = o.vertex_groups.new(name="Root" if o is body else o.name)
    vg.add(range(len(o.data.vertices)), 1.0, "REPLACE")
bpy.ops.object.select_all(action="DESELECT")
for o in (drum, rod, body):
    o.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
mesh = body; mesh.name = "SK_ExtractorSilicio_Mesh"
dec = mesh.modifiers.new("Decimate", "DECIMATE"); dec.ratio = DECIMATE
bpy.ops.object.modifier_apply(modifier=dec.name)
mesh.parent = arm
mod = mesh.modifiers.new("Armature", "ARMATURE"); mod.object = arm

# animacion en los huesos (el eje X/Z del objeto es el eje Y local del hueso)
arm.animation_data_create()
action = bpy.data.actions.new("Extractor_Loop"); arm.animation_data.action = action
for name, axis in (("Tambor", 0), ("Varilla", 2)):
    pb = arm.pose.bones[name]; pb.rotation_mode = "XYZ"
    rest = pb.bone.matrix_local.to_3x3()
    for f, rot in zip(frames, samples[name]):
        world_rot = rot.to_matrix()
        local = rest.inverted() @ world_rot @ rest
        pb.rotation_euler = local.to_euler("XYZ")
        pb.keyframe_insert("rotation_euler", frame=f)

tris = sum(len(p.vertices) - 2 for p in mesh.data.polygons)
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True); mesh.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(folder / "extractor_unreal.fbx"), use_selection=True,
                         object_types={"ARMATURE", "MESH"}, add_leaf_bones=False,
                         bake_anim=True, bake_anim_use_all_actions=False,
                         bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
                         path_mode="COPY", embed_textures=True, mesh_smooth_type="FACE",
                         primary_bone_axis="Y", secondary_bone_axis="X")
bpy.ops.wm.save_as_mainfile(filepath=str(folder / "ExtractorSilicio_unreal.blend"))
(folder / "extractor_build.json").write_text(json.dumps({
    "height_m": HEIGHT_M, "scale": scale, "triangles": tris,
    "bones": ["Root", "Tambor", "Varilla"], "frames": [scn.frame_start, scn.frame_end],
    "fps": scn.render.fps, "materials": [m.name for m in mesh.data.materials],
}, indent=1), encoding="utf-8")
print("EXTRACTOR_OK", tris)
