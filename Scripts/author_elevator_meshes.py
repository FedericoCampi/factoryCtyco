"""Blender: prepara el ascensor del usuario (3D assets/GLBs/ascensorEstructura.glb y ascensorPiso.glb).

- Estructura: jaula de 4 postes con la polea arriba. Escala 4,4 (hueco interior ~1,45 m, alto
  4,4 m), origen al centro del piso, colision UCX solo en los 4 postes (se entra por cualquier lado).
- Piso: plataforma de 1,4 m, con la cara de arriba 6 cm sobre su origen (AFactoryElevator la
  ubica a 6 cm, asi que queda a 12 cm, a la altura que usa para el personaje).
Ambas se reducen de ~700 000 caras a una fraccion. Salida: SourceAssets/Ascensor/*.fbx y
elevator_build.json.

blender -b --factory-startup -P Scripts/author_elevator_meshes.py
"""
import json
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

SRC = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs")
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Ascensor"
FRAME_SCALE, FLOOR_SIZE, FLOOR_TOP = 4.4, 1.4, 0.06
POST = (0.165, 0.265)   # |x| e |y| de cada poste en el GLB normalizado (medido)
report = {}


def load(name, ratio):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SRC / f"{name}.glb"))
    o = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    o.parent = None
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for extra in [x for x in bpy.context.scene.objects if x is not o]:
        bpy.data.objects.remove(extra)
    dec = o.modifiers.new("dec", "DECIMATE"); dec.ratio = ratio
    bpy.ops.object.modifier_apply(modifier=dec.name)
    return o


def ucx(name, lo, hi, index):
    me = bpy.data.meshes.new(f"UCX_{name}_{index:02d}")
    b = bmesh.new(); vs = bmesh.ops.create_cube(b, size=1.0)["verts"]
    c, s = (lo + hi) / 2, hi - lo
    for v in vs:
        v.co = Vector((v.co.x * s.x, v.co.y * s.y, v.co.z * s.z)) + c
    b.to_mesh(me); b.free()
    bpy.context.scene.collection.objects.link(bpy.data.objects.new(me.name, me))


def export(o, name):
    o.name = name
    bpy.ops.object.select_all(action="SELECT")
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / f"{name}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             mesh_smooth_type="FACE", path_mode="COPY", embed_textures=True,
                             axis_forward="-Y", axis_up="Z")
    report[name] = {"faces": len(o.data.polygons), "size_m": [round(d, 3) for d in o.dimensions]}


frame = load("ascensorEstructura", 0.08)
frame.data.transform(Matrix.Scale(FRAME_SCALE, 4))
h = frame.dimensions.z
index = 0
for sx in (-1, 1):
    for sy in (-1, 1):
        a, b = POST[0] * FRAME_SCALE, POST[1] * FRAME_SCALE
        xs, ys = sorted((sx * a, sx * b)), sorted((sy * a, sy * b))
        ucx("SM_AscensorEstructura", Vector((xs[0], ys[0], 0)), Vector((xs[1], ys[1], h)), index); index += 1
export(frame, "SM_AscensorEstructura")
report["SM_AscensorEstructura"]["inner_gap_m"] = round(2 * POST[0] * FRAME_SCALE, 3)

floor = load("ascensorPiso", 0.05)
floor.data.transform(Matrix.Scale(FLOOR_SIZE / max(floor.dimensions.x, floor.dimensions.y), 4))
top = max((v.co.z for v in floor.data.vertices))
floor.data.transform(Matrix.Translation((0, 0, FLOOR_TOP - top)))
export(floor, "SM_AscensorPiso")

(OUT / "elevator_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("ELEVATOR_OK", report)
