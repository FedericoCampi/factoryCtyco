"""Blender: SM_PloteoLado, el panel donde va el ploteo del camion (28/09).

Un rectangulo de 2,95 x 1,04 m (el lateral de la caja del camion, sin los esquineros) en el plano XZ,
centrado en el origen. Ya en Unreal (importado recalculando normales) la cara visible mira a -Y: el lado
izquierdo del camion, el de la puerta. UV: u crece hacia -X, asi la textura se lee de izquierda a derecha
desde -Y. AFactoryVehiclePath pone uno en la puerta (sigue al hueso Puerta) y otro girado 180 en el lado
derecho. Es de una sola cara: tiene que quedar por fuera de la chapa (a 86 cm del centro del camion).
Sin colision. Salida: SourceAssets/Ploteo/SM_PloteoLado.fbx.

blender -b --factory-startup -P Scripts/author_truck_wrap_mesh.py
"""
from pathlib import Path
import bmesh
import bpy

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Ploteo"
WIDTH, HEIGHT = 2.95, 1.04

bpy.ops.wm.read_factory_settings(use_empty=True)
m = bpy.data.materials.new("M_PloteoCamion")
bm = bmesh.new()
uv = bm.loops.layers.uv.new("UVMap")
w, h = WIDTH / 2, HEIGHT / 2
corners = [(w, -h), (-w, -h), (-w, h), (w, h)]   # vistos desde +Y: abajo-izq, abajo-der, arriba-der, arriba-izq
verts = [bm.verts.new((x, 0.0, z)) for x, z in corners]
face = bm.faces.new(verts)
face.normal_update()
if face.normal.y < 0:
    face.normal_flip()
assert face.normal.y > 0.99, face.normal
for loop in face.loops:
    loop[uv].uv = ((w - loop.vert.co.x) / WIDTH, (loop.vert.co.z + h) / HEIGHT)
me = bpy.data.meshes.new("SM_PloteoLado")
bm.to_mesh(me); bm.free()
me.materials.append(m)
obj = bpy.data.objects.new("SM_PloteoLado", me)
bpy.context.scene.collection.objects.link(obj)
OUT.mkdir(parents=True, exist_ok=True)
obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT / "SM_PloteoLado.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         axis_forward="-Y", axis_up="Z")
print("PLOTEO_MESH_OK")
