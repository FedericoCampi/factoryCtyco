"""Blender: botonera para prender la cinta de despacho (AFactoryDispatchBelt).

Pedestal de acero oscuro de 85 cm con marco naranja como las barandas de la maquina, tapa
inclinada y un hongo grande (ranura M_Boton: en Unreal se enciende verde/rojo). Origen al centro
del pie. Salida: SourceAssets/DispatchBox/SM_BotoneraDespacho.fbx.

blender -b --factory-startup -P Scripts/author_dispatch_panel.py
"""
import math
from pathlib import Path
import bpy

OUT = Path(__file__).resolve().parents[1] / "SourceAssets/DispatchBox"
bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, rgb, rough=0.5, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return m


steel = material("M_BotoneraAcero", (0.05, 0.05, 0.055), 0.45, 0.8)
orange = material("M_BotoneraNaranja", (0.85, 0.28, 0.04), 0.5)
button = material("M_Boton", (0.8, 0.1, 0.05), 0.3)
parts = []


def block(size, loc, mat, rot=(0, 0, 0), bevel=0.004):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        b = o.modifiers.new("b", "BEVEL"); b.width = bevel; b.segments = 2
        bpy.ops.object.modifier_apply(modifier=b.name)
    o.data.materials.append(mat)
    parts.append(o)


block((0.22, 0.22, 0.03), (0, 0, 0.015), steel)                 # pie
block((0.12, 0.12, 0.72), (0, 0, 0.39), steel)                  # columna
for z in (0.2, 0.55):                                           # franjas naranjas
    block((0.125, 0.125, 0.03), (0, 0, z), orange, bevel=0)
tilt = math.radians(-30)
block((0.22, 0.18, 0.06), (0, 0.0, 0.78), steel, rot=(tilt, 0, 0))   # cabezal inclinado
block((0.23, 0.19, 0.02), (0, 0.0, 0.78), orange, rot=(tilt, 0, 0), bevel=0.002)  # marco
# hongo: sobre la cara de arriba del cabezal, mirando hacia -Y (el frente)
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.045, depth=0.04,
                                    location=(0, -0.012, 0.832), rotation=(tilt, 0, 0))
cap = bpy.context.active_object
cap.data.materials.append(button)
parts.append(cap)

bpy.ops.object.select_all(action="DESELECT")
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
panel = bpy.context.active_object
panel.name = "SM_BotoneraDespacho"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(OUT / "SM_BotoneraDespacho.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         axis_forward="-Y", axis_up="Z")
print("PANEL_OK", len(panel.data.polygons), [round(d, 3) for d in panel.dimensions])
