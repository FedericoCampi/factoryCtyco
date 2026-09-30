"""Extractor de Silicio v1: tambor y varilla oscilan, mirilla pulsa.
blender -b --factory-startup -P Scripts/animate_extractor_silicio.py -- <glb> <carpeta_salida>
Coordenadas medidas sobre el GLB (Z arriba, frente en -Y)."""
import bpy, bmesh, sys, math
from mathutils import Matrix, Vector

src, outdir = sys.argv[sys.argv.index("--") + 1:][:2]
FPS, FRAMES = 30, 240  # loop de 8 s

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
body = [o for o in bpy.data.objects if o.type == "MESH"][0]
body.name = "Extractor_Cuerpo"
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True); bpy.context.view_layer.objects.active = body
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
root = body.parent
if root:
    body.parent = None
bpy.ops.object.select_all(action="DESELECT")
for o in list(bpy.data.objects):
    if o.type != "MESH":
        bpy.data.objects.remove(o)

scn = bpy.context.scene
scn.render.fps = FPS; scn.frame_start = 1; scn.frame_end = FRAMES


def separate(name, inside, pivot):
    """Separa las caras con todos sus vertices dentro de `inside` y pone el origen en `pivot`."""
    bm = bmesh.new(); bm.from_mesh(body.data)
    for e in (*bm.verts, *bm.edges, *bm.faces):
        e.select = False
    n = 0
    for f in bm.faces:
        if all(inside(v.co) for v in f.verts):
            f.select_set(True); n += 1
    bm.select_mode = {"FACE"}
    bm.to_mesh(body.data); bm.free()
    bpy.context.view_layer.objects.active = body; body.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    part = [o for o in bpy.context.selected_objects if o is not body][0]
    part.name = name
    pv = Vector(pivot)
    part.data.transform(Matrix.Translation(-pv))
    part.location = pv
    part.select_set(False)
    print(f"PART {name}: {n} caras")
    return part


# Tambor del cabrestante: cilindro con eje X en (Y .022, Z .952)
DRUM_AXIS = (0.021, 0.022, 0.952)
drum = separate(
    "Tambor",
    lambda c: -0.021 <= c.x <= 0.063 and math.hypot(c.y - 0.022, c.z - 0.952) <= 0.046,
    DRUM_AXIS,
)
# Varilla y tubo de vidrio: eje Z en (X .003, Y .015)
ROD_AXIS = (0.003, 0.015, 0.78)
rod = separate(
    "Varilla",
    lambda c: 0.676 <= c.z <= 0.888 and math.hypot(c.x - 0.003, c.y - 0.015) <= 0.040,
    ROD_AXIS,
)
bpy.ops.object.select_all(action="DESELECT")

# Mirilla: segundo material en el cuerpo, con emision animada
base = body.data.materials[0]
glow = base.copy(); glow.name = "M_Mirilla"
base.name = "M_Extractor"
body.data.materials.append(glow)
slot = len(body.data.materials) - 1
n = 0
for p in body.data.polygons:
    c = p.center
    if c.y < -0.12 and math.hypot(c.x - 0.005, c.z - 0.41) <= 0.046:
        p.material_index = slot; n += 1
print(f"PART Mirilla: {n} caras")
bsdf = next(nd for nd in glow.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
# emision = textura base tenida de naranja, para conservar el detalle del vidrio
nt = glow.node_tree
tex_link = bsdf.inputs["Base Color"].links[0]
mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
mul.inputs["Factor"].default_value = 1.0
mul.inputs["B"].default_value = (1.0, 0.35, 0.06, 1)
nt.links.new(tex_link.from_socket, mul.inputs["A"])
nt.links.new(mul.outputs["Result"], bsdf.inputs["Emission Color"])
es = bsdf.inputs["Emission Strength"]
for f, v in ((1, 0.8), (61, 4.0), (121, 0.8), (181, 4.0), (241, 0.8)):
    es.default_value = v; es.keyframe_insert("default_value", frame=f)


def spin(obj, axis, turns):
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = (0, 0, 0); obj.keyframe_insert("rotation_euler", frame=1)
    r = [0, 0, 0]; r[axis] = 2 * math.pi * turns
    obj.rotation_euler = r; obj.keyframe_insert("rotation_euler", frame=FRAMES + 1)


# tambor: la cara trasera no esta modelada, asi que enrolla y desenrolla (+-35 grados)
drum.rotation_mode = "XYZ"
for f, a in ((1, -35), (121, 35), (241, -35)):
    drum.rotation_euler = (math.radians(a), 0, 0); drum.keyframe_insert("rotation_euler", frame=f)
# varilla: su costado (tapado por los postes) no esta modelado; gira +-30 grados
rod.rotation_mode = "XYZ"
for f, a in ((1, -30), (121, 30), (241, -30)):
    rod.rotation_euler = (0, 0, math.radians(a)); rod.keyframe_insert("rotation_euler", frame=f)


def force_linear():
    for o in (rod,):
        act = o.animation_data.action
        curves = []
        if hasattr(act, "fcurves"):
            curves = list(act.fcurves)
        else:  # acciones por capas (Blender 4.4+)
            for layer in act.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        curves += list(bag.fcurves)
        for fc in curves:
            for k in fc.keyframe_points:
                k.interpolation = "LINEAR"


for o in (drum, rod):
    o.parent = body
    o.matrix_parent_inverse = body.matrix_world.inverted()

bpy.ops.wm.save_as_mainfile(filepath=f"{outdir}/Extractor_Silicio_v1.blend")
bpy.ops.export_scene.gltf(filepath=f"{outdir}/Extractor_Silicio_v1.glb", export_animations=True,
                          export_frame_range=True, export_force_sampling=True)
bpy.ops.export_scene.fbx(filepath=f"{outdir}/Extractor_Silicio_v1.fbx", bake_anim=True,
                         path_mode="COPY", embed_textures=True, add_leaf_bones=False)
print("DONE")
