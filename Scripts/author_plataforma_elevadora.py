"""Blender: plataforma elevadora para la linea de cintas (02/10).

Una chapa de 180 x 140 cm (arriba a 30 cm, como el marco de las cintas: la carga viaja a 33), con borde naranja,
travesaños abajo y cuatro guias en las esquinas que abrazan las columnas (las columnas las pone el juego: las patas del
actor, hasta arriba de todo). Origen en el centro de abajo. Dos materiales: M_PlataformaChapa y M_PlataformaBorde
(apply_plataforma_elevadora.py).
Salida: SourceAssets/PlataformaElevadora/SM_PlataformaElevadora.fbx.

blender -b --factory-startup -P Scripts/author_plataforma_elevadora.py
"""
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/PlataformaElevadora"
NAME = "SM_PlataformaElevadora"
L, W = 1.8, 1.4

bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new(NAME)
o = bpy.data.objects.new(NAME, me)
bpy.context.scene.collection.objects.link(o)
for name in ("M_PlataformaChapa", "M_PlataformaBorde"):
    me.materials.append(bpy.data.materials.new(name))
b = bmesh.new()


def box(size, at, slot):
    made = bmesh.ops.create_cube(b, size=1.0)
    bmesh.ops.transform(b, matrix=Matrix.Translation(at) @ Matrix.Diagonal((*size, 1.0)), verts=made["verts"])
    for f in {f for v in made["verts"] for f in v.link_faces}:
        f.material_index = slot


box((L - 0.08, W - 0.08, 0.08), (0, 0, 0.26), 0)                         # chapa
for y in (-1, 1):                                                          # borde naranja a lo largo
    box((L, 0.05, 0.12), (0, y * (W / 2 - 0.025), 0.24), 1)
for x in (-1, 1):                                                          # y a lo ancho
    box((0.05, W, 0.12), (x * (L / 2 - 0.025), 0, 0.24), 1)
for x in (-0.55, 0.0, 0.55):                                               # travesaños abajo
    box((0.08, W - 0.16, 0.1), (x, 0, 0.15), 0)
for x in (-1, 1):                                                          # guias en las esquinas
    for y in (-1, 1):
        box((0.12, 0.12, 0.3), (x * 0.82, y * 0.64, 0.15), 1)
b.to_mesh(me)
b.free()

OUT.mkdir(parents=True, exist_ok=True)
o.select_set(True)
bpy.context.view_layer.objects.active = o
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         axis_forward="-Y", axis_up="Z")
print("PLATAFORMA_OK", [round(d, 3) for d in o.dimensions], len(me.polygons))
