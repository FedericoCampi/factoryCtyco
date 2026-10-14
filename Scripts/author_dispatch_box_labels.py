"""Blender: las cajas de despacho con etiqueta, una por letra de la A a la D (05/10).

La misma caja de author_dispatch_box.py (40 x 40 x 32 cm, cinta a lo largo de Y sobre la tapa y bajando por los lados
+-Y) con una etiqueta blanca de papel y su letra en negro: arriba, al lado de la cinta, y en los dos costados sin cinta
(+-X), asi se lee desde la camara de arriba y de costado. La maquina de despacho (AFactoryDispatchBelt::BoxVariants)
saca una al azar; la letra viaja con la caja (es su malla) hasta el camion.
Salida: SourceAssets/DispatchBox/SM_CajaDespacho_A.fbx .. _D.fbx.

blender -b --factory-startup -P Scripts/author_dispatch_box_labels.py
"""
import math
from pathlib import Path
import bpy

OUT = Path(__file__).resolve().parents[1] / "SourceAssets/DispatchBox"
W, D, H = 0.40, 0.40, 0.32
TAPE = 0.06
LETTERS = "ABCD"
LABEL = (0.13, 0.15)        # etiqueta de papel: ancho x alto
GLYPH = 0.11                # alto de la letra


def material(name, rgb, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    return m


def block(name, size, loc, mat, bevel=0.0):
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


def glyph(letter, mat, location, rotation):
    """La letra como malla, centrada, apenas en relieve."""
    bpy.ops.object.text_add(location=(0, 0, 0))
    t = bpy.context.active_object
    t.data.body = letter
    t.data.align_x, t.data.align_y = "CENTER", "CENTER"
    t.data.size = GLYPH
    t.data.extrude = 0.0006
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.active_object
    o.data.materials.clear()
    o.data.materials.append(mat)
    o.rotation_euler = rotation
    o.location = location
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o


OUT.mkdir(parents=True, exist_ok=True)
for letter in LETTERS:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    card = material("M_Carton", (0.42, 0.27, 0.13), 0.85)
    tape = material("M_CintaEmbalar", (0.62, 0.48, 0.25), 0.35)
    paper = material("M_EtiquetaPapel", (0.92, 0.91, 0.86), 0.7)
    ink = material("M_EtiquetaTinta", (0.03, 0.03, 0.03), 0.6)
    parts = [block("Caja", (W, D, H), (0, 0, H / 2), card, 0.012)]
    parts.append(block("CintaTapa", (TAPE, D + 0.004, 0.003), (0, 0, H + 0.0015), tape))
    for side in (-1, 1):
        parts.append(block("CintaLado", (TAPE, 0.003, 0.10), (0, side * (D / 2 + 0.0015), H - 0.05), tape))
    # arriba: al costado de la cinta, leyendose desde -Y
    top_x = TAPE / 2 + 0.02 + LABEL[0] / 2
    parts.append(block("EtiquetaTapa", (LABEL[0], LABEL[1], 0.002), (top_x, 0, H + 0.001), paper))
    parts.append(glyph(letter, ink, (top_x, 0, H + 0.0021), (0, 0, 0)))
    # costados sin cinta (+-X): de pie, mirando hacia afuera
    for side in (-1, 1):
        x = side * (W / 2 + 0.001)
        parts.append(block("EtiquetaLado", (0.002, LABEL[0], LABEL[1]), (x, 0, H * 0.55), paper))
        parts.append(glyph(letter, ink, (x + side * 0.0011, 0, H * 0.55), (math.pi / 2, 0, side * math.pi / 2)))
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    box = bpy.context.active_object
    box.name = f"SM_CajaDespacho_{letter}"
    bpy.ops.export_scene.fbx(filepath=str(OUT / f"SM_CajaDespacho_{letter}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                             axis_forward="-Y", axis_up="Z")
    print("BOX_LABEL_OK", letter, len(box.data.polygons), [round(d, 3) for d in box.dimensions])
