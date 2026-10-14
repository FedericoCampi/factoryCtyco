"""Blender: la oficina del usuario para el piso de administracion (07/10).

Fuente: 3D assets/GLBs/scenes/Oficina industrial minimalista en 3D-complete.glb (ya en metros, ~24 600 triangulos):
salon de 9 x 10 m (piso a z 0, paredes del frente bajas, de 1,2 m, para la vista isometrica; las de atras de 3,3 m con
ventanas), escritorios y sala de reuniones, y dos anexos (A atras, B a la derecha). Se quitan el suelo de 49 x 50 m
("Ground"), la puerta doble con su marco y el felpudo: en Unreal en ese vano (x 3,28 .. 5,12, y 0) va el ascensor.
Todo en una malla, origen donde estaba (la esquina del salon), choca con su propia malla (en Unreal, complex as
simple). Salida: SourceAssets/Oficina/SM_Oficina.fbx y oficina_build.json (con el vano de la puerta).

blender -b --factory-startup -P Scripts/author_oficina.py
"""
import json
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/scenes/Oficina industrial minimalista en 3D-complete.glb")
OUT = ROOT / "SourceAssets/Oficina"
NAME = "SM_Oficina"
DROP = ("Ground", "Door frame", "Door leaf left", "Door leaf right", "Entrance doormat")
DOOR_GAP = (3.28, 5.12)        # vano de la puerta en la pared del frente (y 0), en x; el ascensor va afuera (y < 0)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
dropped = []
for o in list(bpy.context.scene.objects):
    if o.type == "MESH" and o.name.startswith(DROP):
        dropped.append(o.name)
        bpy.data.objects.remove(o)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
bpy.ops.object.join()
o = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for extra in [x for x in bpy.context.scene.objects if x is not o]:
    bpy.data.objects.remove(extra)
o.name = o.data.name = NAME
co = [v.co for v in o.data.vertices]
lo = Vector([min(c[i] for c in co) for i in range(3)])
hi = Vector([max(c[i] for c in co) for i in range(3)])

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
o.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         path_mode="COPY", embed_textures=True, axis_forward="-Y", axis_up="Z")
report = {"source": str(SRC), "dropped": dropped, "pieces_joined": len(meshes),
          "min_m": [round(x, 2) for x in lo], "max_m": [round(x, 2) for x in hi],
          "triangles": sum(len(p.vertices) - 2 for p in o.data.polygons),
          "materials": [m.name for m in o.data.materials if m], "collision": "complex",
          "door_gap_x_m": list(DOOR_GAP), "door_wall_y_m": 0.0, "floor_z_m": 0.0}
(OUT / "oficina_build.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
print("OFICINA_OK", json.dumps(report, ensure_ascii=False))
