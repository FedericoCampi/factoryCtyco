"""Blender: prepara la escena del laboratorio del usuario (3D assets/GLBs/scenes/escenaLab1-complete.glb) (30/09).

La escena viene en escala real (20,6 x 18,6 m, 4,8 m de alto, 1139 piezas, ~143 000 triangulos) y sin colisiones.
Se unen todas las piezas en una malla (SM_Lab1), con el origen en el centro del piso tal como viene. La colision la
pone Unreal con la propia malla ("complex as simple", import_lab_scene.py), asi el personaje pisa y choca con
lo que se ve sin cajas aproximadas.
Salida: SourceAssets/Lab1/SM_Lab1.fbx y lab_build.json.

blender -b --factory-startup -P Scripts/author_lab_scene.py
"""
import json
from pathlib import Path
import bpy
from mathutils import Vector

SRC = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/scenes/escenaLab1-complete.glb")
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Lab1"
NAME = "SM_Lab1"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
pieces = len(meshes)
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
lab = bpy.context.view_layer.objects.active
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
lab.name = lab.data.name = NAME
for o in [o for o in bpy.context.scene.objects if o is not lab]:
    bpy.data.objects.remove(o)

pts = [lab.matrix_world @ Vector(c) for c in lab.bound_box]
lo = [min(p[i] for p in pts) for i in range(3)]
hi = [max(p[i] for p in pts) for i in range(3)]
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Lab1.blend"))
lab.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         path_mode="COPY", embed_textures=True, axis_forward="-Y", axis_up="Z")
tris = sum(len(p.vertices) - 2 for p in lab.data.polygons)
(OUT / "lab_build.json").write_text(json.dumps({
    "source": str(SRC), "pieces": pieces, "triangles": tris, "bounds_m": [[round(v, 2) for v in lo], [round(v, 2) for v in hi]],
    "materials": [m.name for m in lab.data.materials if m]}, indent=1), encoding="utf-8")
print("LAB_OK", pieces, tris)
