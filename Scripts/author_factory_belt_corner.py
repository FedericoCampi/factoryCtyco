"""Blender: esquina para las cintas de la fabrica (AFactoryBuilding), con el modelo del usuario (30/09).

Fuente: 3D assets/GLBs/esquinaCinta-complete.glb (1 x 1 m, 17 cm de alto, cuarto de circulo que entra por -X y sale
por +Y). Las cintas de la fabrica miden 140 cm de ancho y 30 cm de alto y ocupan una celda de 200 x 200 cm; la
esquina tiene que entrar en una celda: entra por el medio del borde de atras (-100, 0) y sale por el medio del
borde del costado (0, -100) en Unreal (TurnDegrees -90 en DB_BeltCorner), con el eje de la curva a 100 cm de
radio. El modelo tiene una curva mas abierta: se escala al ancho de 140 cm y despues se acerca cada punto al centro
de la curva (se le resta la diferencia de radios), asi la banda conserva su ancho y el radio queda en 100 cm.
Origen: centro de la celda, al piso. Sin colision (la pone la caja del actor). ~126 000 triangulos.
Salida: SourceAssets/CintaEsquinaFabrica/SM_CintaEsquinaFabrica.fbx y build.json.

blender -b --factory-startup -P Scripts/author_factory_belt_corner.py
"""
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

SRC = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/esquinaCinta-complete.glb")
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/CintaEsquinaFabrica"
NAME = "SM_CintaEsquinaFabrica"
WIDTH, HEIGHT = 1.40, 0.30      # como la cinta recta de la fabrica (DB_Belt: 200 x 140 x 30 cm)
RADIUS = None                   # None: la curva del modelo, sin cerrarla (30/09: cerrada a 1 m se veia mal)
DECIMATE = 0.18

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
o = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
bpy.ops.object.select_all(action="DESELECT")
o.select_set(True)
bpy.context.view_layer.objects.active = o
o.parent = None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for extra in [x for x in bpy.context.scene.objects if x is not o]:
    bpy.data.objects.remove(extra)

co = [v.co.copy() for v in o.data.vertices]
xmin, ymax = min(c.x for c in co), max(c.y for c in co)
zmax = max(c.z for c in co)
entry = [c.y for c in co if c.x < xmin + 0.02]
exit_ = [c.x for c in co if c.y > ymax - 0.02]
band = ((max(entry) - min(entry)) + (max(exit_) - min(exit_))) / 2
entry_c, exit_c = (min(entry) + max(entry)) / 2, (min(exit_) + max(exit_)) / 2
radius_n = exit_c - xmin
s = WIDTH / band
sz = HEIGHT / zmax
old_r = radius_n * s
# 1) entrada del eje en (-1, 0) de Blender (Unreal (-100, 0)), ancho de 140 cm, 30 cm de alto
place = Matrix.Translation((-1.0, 0, 0)) @ Matrix.Diagonal((s, s, sz, 1)) @ Matrix.Translation((-xmin, -entry_c, 0))
o.data.transform(place)
# 2) si se pide otro radio, cada punto se acerca al centro de la curva lo que sobra de radio
if RADIUS is not None:
    old_c = Vector((-1.0, old_r))
    new_c = Vector((-1.0, RADIUS))
    for v in o.data.vertices:
        d = Vector((v.co.x, v.co.y)) - old_c
        r = d.length
        if r < 1e-6:
            continue
        p = new_c + d / r * max(r - (old_r - RADIUS), 0.0)
        v.co.x, v.co.y = p.x, p.y
    o.data.update()
radius = RADIUS if RADIUS is not None else old_r
dec = o.modifiers.new("Decimate", "DECIMATE")
dec.ratio = DECIMATE
bpy.ops.object.modifier_apply(modifier=dec.name)
o.name = o.data.name = NAME

pts = [v.co for v in o.data.vertices]
lo = [round(min(p[i] for p in pts), 3) for i in range(3)]
hi = [round(max(p[i] for p in pts), 3) for i in range(3)]
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
o.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         path_mode="COPY", embed_textures=True, axis_forward="-Y", axis_up="Z")
(OUT / "build.json").write_text(json.dumps({
    "source": str(SRC), "width_m": WIDTH, "height_m": HEIGHT, "radius_m": round(radius, 3), "turn_radius_cm": round(radius * 100, 1), "model_radius_m": round(old_r, 3),
    "turn_degrees_unreal": -90, "bounds_blender_m": [lo, hi],
    "triangles": sum(len(p.vertices) - 2 for p in o.data.polygons),
    "materials": [m.name for m in o.data.materials if m]}, indent=1), encoding="utf-8")
print("FACTORY_CORNER_OK", lo, hi)
