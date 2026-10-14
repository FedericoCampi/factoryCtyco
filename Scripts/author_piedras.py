"""Blender: piedras para la linea (03/10).

- SM_Piedra: una piedra irregular de ~30 cm (icosfera deformada con ruido, caras planas), la roca en bruto.
- SM_BloquePiedra: el bloque que sale de la sierra (la caja): 30 x 20 x 16 cm, cantos apenas biselados y dos marcas
  de corte en la cara de arriba.
- SM_PiedraTriturada: un monton de 12 piedritas de 4 a 8 cm, lo que sale de la trituradora para el horno.
Sin texturas: los materiales los pone apply_piedras.py.
Salida: SourceAssets/Piedras/SM_Piedra.fbx, SM_BloquePiedra.fbx y SM_PiedraTriturada.fbx.

blender -b --factory-startup -P Scripts/author_piedras.py
"""
import math
import random
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector, noise

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Piedras"
random.seed(11)


def rock(b, radius, at, seed, squash=0.75, subdivisions=2):
    verts = bmesh.ops.create_icosphere(b, subdivisions=subdivisions, radius=radius)["verts"]
    offset = Vector((seed * 3.1, seed * 1.7, seed * 2.3))
    for v in verts:
        n = noise.noise(v.co / radius * 1.3 + offset)
        v.co = v.co * (1.0 + 0.28 * n)
        v.co.z *= squash
    lo = min(v.co.z for v in verts)
    bmesh.ops.transform(b, matrix=Matrix.Translation((at[0], at[1], at[2] - lo)) @ Matrix.Rotation(random.uniform(0, 6.28), 4, "Z"), verts=verts)


def export(name, build):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    b = bmesh.new()
    build(b)
    me = bpy.data.meshes.new(name)
    b.to_mesh(me)
    b.free()
    for p in me.polygons:
        p.use_smooth = False
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(bpy.data.materials.new("M_" + name[3:]))
    OUT.mkdir(parents=True, exist_ok=True)
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.export_scene.fbx(filepath=str(OUT / f"{name}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                             axis_forward="-Y", axis_up="Z")
    print(name, "OK", [round(d, 3) for d in o.dimensions], len(me.polygons))


export("SM_Piedra", lambda b: rock(b, 0.15, (0, 0, 0), 1))


def block(b):
    L, W, H = 0.30, 0.20, 0.16
    verts = bmesh.ops.create_cube(b, size=1.0)["verts"]
    bmesh.ops.transform(b, matrix=Matrix.Translation((0, 0, H / 2)) @ Matrix.Diagonal((L, W, H, 1.0)), verts=verts)
    bmesh.ops.bevel(b, geom=b.edges[:], offset=0.006, segments=1, affect="EDGES")
    for x in (-0.05, 0.07):   # marcas de la sierra: dos ranuras finas a lo ancho de la cara de arriba
        cut = bmesh.ops.create_cube(b, size=1.0)["verts"]
        bmesh.ops.transform(b, matrix=Matrix.Translation((x, 0, H + 0.001)) @ Matrix.Diagonal((0.004, W * 0.98, 0.004, 1.0)), verts=cut)


export("SM_BloquePiedra", block)


def gravel(b):
    for i in range(12):
        angle, dist = random.uniform(0, 2 * math.pi), random.uniform(0, 0.09)
        r = random.uniform(0.02, 0.04)
        z = 0.0 if dist > 0.05 else random.uniform(0.0, 0.03)
        rock(b, r, (dist * math.cos(angle), dist * math.sin(angle), z), i + 5, squash=0.7, subdivisions=1)


export("SM_PiedraTriturada", gravel)
