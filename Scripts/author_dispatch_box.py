"""Blender: caja de carton para las maquinas de despacho (AFactoryDispatchBelt).

40 x 40 x 32 cm, bordes biselados, cinta de embalar arriba y en los costados. Origen al centro
de la base. Sin colision (las cajas viajan sin chocar).
Salida: SourceAssets/DispatchBox/SM_CajaDespacho.fbx.

blender -b --factory-startup -P Scripts/author_dispatch_box.py
"""
from pathlib import Path
import bpy

OUT = Path(__file__).resolve().parents[1] / "SourceAssets/DispatchBox"
W, D, H = 0.40, 0.40, 0.32
TAPE = 0.06

bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, rgb, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    return m


def block(name, size, loc, mat, bevel):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        b = o.modifiers.new("bevel", "BEVEL"); b.width = bevel; b.segments = 2
        bpy.ops.object.modifier_apply(modifier=b.name)
    o.data.materials.append(mat)
    return o


card = material("M_Carton", (0.42, 0.27, 0.13), 0.85)
tape = material("M_CintaEmbalar", (0.62, 0.48, 0.25), 0.35)
parts = [block("Caja", (W, D, H), (0, 0, H / 2), card, 0.012)]
# cinta: franja sobre la tapa y bajando por los dos lados
parts.append(block("CintaTapa", (TAPE, D + 0.004, 0.003), (0, 0, H + 0.0015), tape, 0))
for side in (-1, 1):
    parts.append(block("CintaLado", (TAPE, 0.003, 0.10), (0, side * (D / 2 + 0.0015), H - 0.05), tape, 0))
bpy.ops.object.select_all(action="DESELECT")
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
box = bpy.context.active_object
box.name = "SM_CajaDespacho"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(OUT / "SM_CajaDespacho.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         axis_forward="-Y", axis_up="Z")
print("BOX_OK", len(box.data.polygons), [round(d, 3) for d in box.dimensions])
