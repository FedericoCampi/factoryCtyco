"""Blender: cartel de "cinta llena" y pedazo de pared de ladrillos para colocar a mano.

- SM_CartelLleno: tablero rojo (ranura M_CartelRojo, emisivo en Unreal) con marco de acero oscuro,
  130 x 50 cm, 5 cm de espesor; el frente mira a +X (AFactoryDispatchBelt lo gira hacia la camara
  y le pone el texto encima). Origen al centro.
- SM_ParedLadrillo: 2 m de largo (X) x 0,40 m x 2,5 m de alto, origen al centro de la base, colision
  UCX. Ranura M_ParedLadrillo: en Unreal usa un material alineado al mundo, asi al escalarla los
  ladrillos no se estiran.
Salida: SourceAssets/DispatchBox/SM_CartelLleno.fbx y SourceAssets/ParedLadrillo/SM_ParedLadrillo.fbx.

blender -b --factory-startup -P Scripts/author_sign_and_wall.py
"""
from pathlib import Path
import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1] / "SourceAssets"


def material(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1)
    return m


def block(name, size, loc, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        b = o.modifiers.new("b", "BEVEL"); b.width = bevel; b.segments = 2
        bpy.ops.object.modifier_apply(modifier=b.name)
    o.data.materials.append(mat)
    return o


def export(objs, path, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    joined = bpy.context.active_object
    joined.name = name
    for o in bpy.context.scene.objects:
        if o.name.startswith("UCX_"):
            o.select_set(True)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                             axis_forward="-Y", axis_up="Z")
    print("EXPORTED", name, len(joined.data.polygons), [round(d, 3) for d in joined.dimensions])


# --- cartel ---
bpy.ops.wm.read_factory_settings(use_empty=True)
red = material("M_CartelRojo", (0.8, 0.04, 0.03))
frame = material("M_CartelMarco", (0.04, 0.04, 0.045))
parts = [block("Tablero", (0.04, 1.22, 0.42), (0.005, 0, 0), red)]
for z in (-0.23, 0.23):
    parts.append(block("MarcoH", (0.05, 1.30, 0.04), (0, 0, z), frame, 0.004))
for y in (-0.63, 0.63):
    parts.append(block("MarcoV", (0.05, 0.04, 0.50), (0, y, 0), frame, 0.004))
export(parts, ROOT / "DispatchBox/SM_CartelLleno.fbx", "SM_CartelLleno")

# --- pared ---
bpy.ops.wm.read_factory_settings(use_empty=True)
brick = material("M_ParedLadrillo", (0.55, 0.28, 0.16))
L, T, H = 2.0, 0.40, 2.5
wall = block("Pared", (L, T, H), (0, 0, H / 2), brick, 0.01)
# UV en metros (u a lo largo, v hacia arriba) por si se usa un material comun
bm = bmesh.new(); bm.from_mesh(wall.data)
uv = bm.loops.layers.uv.verify()
for f in bm.faces:
    n = f.normal
    for loop in f.loops:
        co = loop.vert.co
        loop[uv].uv = (co.y, co.z) if abs(n.x) > 0.7 else ((co.x, co.y) if abs(n.z) > 0.7 else (co.x, co.z))
bm.to_mesh(wall.data); bm.free()
me = bpy.data.meshes.new("UCX_SM_ParedLadrillo_00")
b = bmesh.new(); vs = bmesh.ops.create_cube(b, size=1.0)["verts"]
for v in vs:
    v.co = Vector((v.co.x * L, v.co.y * T, v.co.z * H + H / 2))
b.to_mesh(me); b.free()
bpy.context.scene.collection.objects.link(bpy.data.objects.new(me.name, me))
export([wall], ROOT / "ParedLadrillo/SM_ParedLadrillo.fbx", "SM_ParedLadrillo")
