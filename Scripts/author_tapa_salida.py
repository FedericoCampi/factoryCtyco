"""Blender: tapa de salida de la trituradora (02/10), la boca de abajo por donde sale lo triturado a la cinta.

Una campana de chapa: placa de atras (va contra la trituradora), techo que baja hacia adelante, dos costados, bulones
en la placa y una pestaña adelante. Abierta abajo y adelante:
la carga aparece debajo y sale sobre la cinta.
Origen en el centro de abajo de la placa de atras; la boca mira a +X. Mide ~48 x 80 x 50 cm.
Material: M_TapaSalida (apply_tunel_lavadora.py).
Salida: SourceAssets/TapaSalida/SM_TapaSalida.fbx.

blender -b --factory-startup -P Scripts/author_tapa_salida.py
"""
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/TapaSalida"
NAME = "SM_TapaSalida"
W, D, H, T = 0.76, 0.45, 0.5, 0.025   # ancho (Y), fondo (X), alto, espesor de la chapa

bpy.ops.wm.read_factory_settings(use_empty=True)
b = bmesh.new()


def box(size, at, rot=Matrix.Identity(4)):
    verts = bmesh.ops.create_cube(b, size=1.0)["verts"]
    bmesh.ops.transform(b, matrix=Matrix.Translation(at) @ rot @ Matrix.Diagonal((*size, 1.0)), verts=verts)


box((T, W, H), (T / 2, 0, H / 2))                                      # placa de atras
roof = Matrix.Rotation(math.radians(-14), 4, "Y")
box((D + 0.03, W, T), (D / 2, 0, H - 0.04), roof)                       # techo, baja hacia adelante
for side in (-1, 1):                                                   # costados: trapecio (caja cortada)
    box((D, T, H * 0.72), (D / 2, side * (W / 2 - T / 2), H * 0.5))
box((0.04, W + 0.04, 0.05), (D + 0.02, 0, H - 0.17))                   # pestaña de adelante
for y in (-0.28, 0.28):                                                # bulones de la placa
    for z in (0.08, H - 0.08):
        verts = bmesh.ops.create_cone(b, cap_ends=True, segments=6, radius1=0.022, radius2=0.022, depth=0.03)["verts"]
        bmesh.ops.transform(b, matrix=Matrix.Translation((0.03, y, z)) @ Matrix.Rotation(math.radians(90), 4, "Y"), verts=verts)
me = bpy.data.meshes.new(NAME)
b.to_mesh(me)
b.free()
o = bpy.data.objects.new(NAME, me)
bpy.context.scene.collection.objects.link(o)
me.materials.append(bpy.data.materials.new("M_TapaSalida"))

OUT.mkdir(parents=True, exist_ok=True)
o.select_set(True)
bpy.context.view_layer.objects.active = o
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         axis_forward="-Y", axis_up="Z")
print("TAPA_OK", [round(d, 3) for d in o.dimensions], len(me.polygons))
