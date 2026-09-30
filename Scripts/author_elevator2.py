"""Blender: prepara el ascensor del usuario (3D assets/GLBs/ascensor2.glb) y sus piezas nuevas.

blender -b --factory-startup -P Scripts/author_elevator2.py

- Cabina: el modelo del usuario, reducido, girado para que la entrada (su lado largo abierto) mire a +X,
  escalado a SCALE y con el origen en el centro de la cara de arriba del piso. Colisiones UCX: piso,
  paneles laterales y fondo. El techo va aparte (SM_Ascensor2Techo) para esconderlo desde la camara.
- Puerta: una hoja (SM_Ascensor2Puerta); AFactoryElevator pone 4, telescopicas, 2 por lado.
- Tubo: pozo bajo el piso (SM_Ascensor2Tubo), origen al centro a nivel del piso, con rieles y borde.
El conjunto cabina + puerta queda centrado en el origen, asi el agujero del piso es simetrico y el
ascensor se puede girar 180 grados sin volver a cortar. Salida: SourceAssets/Ascensor2 y
elevator2_build.json (medidas que usan floor_holes.py y apply_elevator2.py).
"""
import json
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

SRC = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/ascensor2.glb")
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Ascensor2"
SCALE = 3.0          # 0,883 del modelo -> 2,65 m de alto; 2,28 m libres por dentro
DECIMATE = 0.07      # ~699 000 -> ~49 000 caras
TUBE_DEPTH = 3.3     # m bajo el piso
WALL = 0.12          # espesor de las paredes del tubo
MARGIN = 0.03        # luz entre la cabina (con puerta) y el tubo
DOOR_T, DOOR_GAP = 0.04, 0.01   # espesor de cada hoja y separacion entre planos
report = {}


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, color, metallic=0.6, rough=0.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = rough
    return m


def box_mesh(name, lo, hi, mat=None, bevel=0.0):
    me = bpy.data.meshes.new(name)
    b = bmesh.new()
    b.loops.layers.uv.new("UVMap")
    vs = bmesh.ops.create_cube(b, size=1.0, calc_uvs=True)["verts"]
    lo, hi = Vector(lo), Vector(hi)
    for v in vs:
        v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
    if bevel:
        bmesh.ops.bevel(b, geom=b.edges[:], offset=bevel, segments=1, affect="EDGES")
    b.to_mesh(me)
    b.free()
    if mat:
        me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def join(objects, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    o = bpy.context.object
    o.name = name
    return o


def export(objects, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / f"{name}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             mesh_smooth_type="FACE", path_mode="COPY", embed_textures=True,
                             axis_forward="-Y", axis_up="Z")


def ucx(name, index, lo, hi):
    return box_mesh(f"UCX_{name}_{index:02d}", lo, hi)


# --- cabina -----------------------------------------------------------------------------------
clear()
bpy.ops.import_scene.gltf(filepath=str(SRC))
cab = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
for extra in [o for o in bpy.context.scene.objects if o is not cab]:
    bpy.data.objects.remove(extra)
bpy.context.view_layer.objects.active = cab
cab.select_set(True)
cab.parent = None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
dec = cab.modifiers.new("dec", "DECIMATE")
dec.ratio = DECIMATE
bpy.ops.object.modifier_apply(modifier=dec.name)
# Entrada: el lado largo abierto (+Y del GLB) pasa a +X.
cab.data.transform(Matrix.Rotation(-math.pi / 2, 4, "Z") @ Matrix.Scale(SCALE, 4))
vs = [v.co for v in cab.data.vertices]
lo = Vector([min(v[i] for v in vs) for i in range(3)])
hi = Vector([max(v[i] for v in vs) for i in range(3)])
inner = [v for v in vs if abs(v.x - (lo.x + hi.x) / 2) < 0.3 * (hi.x - lo.x) and abs(v.y - (lo.y + hi.y) / 2) < 0.3 * (hi.y - lo.y)]
floor_top = max(v.z for v in inner if v.z < lo.z + 0.4 * (hi.z - lo.z))
roof_bottom = min(v.z for v in inner if v.z > lo.z + 0.5 * (hi.z - lo.z))
# Ancho libre de la entrada: en la cara +X, a media altura, los parantes ocupan los extremos.
mid = [v for v in vs if v.x > hi.x - 0.2 and floor_top + 0.8 < v.z < floor_top + 1.6]
centre_y = (lo.y + hi.y) / 2
opening_half = min(abs(v.y - centre_y) for v in mid if abs(v.y - centre_y) > 0.3)
door_front = hi.x + DOOR_GAP + 2 * DOOR_T + DOOR_GAP
# Centrar cabina + puerta en X, cabina en Y, y poner el piso interior en z = 0.
shift = Vector((-(lo.x + door_front) / 2, -centre_y, -floor_top))
cab.data.transform(Matrix.Translation(shift))
lo, hi = lo + shift, hi + shift
door_front += shift.x
roof_z = roof_bottom - floor_top
height = hi.z
half_x, half_y = door_front, hi.y          # medio largo del conjunto (simetrico en X) y medio ancho

# Techo aparte: caras por encima del borde inferior del techo.
def keep_faces(me, above):
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if (f.calc_center_median().z > roof_z - 0.02) != above],
                     context="FACES")
    bm.to_mesh(me)
    bm.free()


roof = bpy.data.objects.new("SM_Ascensor2Techo", cab.data.copy())
bpy.context.scene.collection.objects.link(roof)
keep_faces(roof.data, True)
keep_faces(cab.data, False)
cab.name = "SM_Ascensor2Cabina"

# Piso aparte (28/09): la cabina y la puerta quedan fijas y solo el piso sube o baja con el personaje.
def split_floor(me, keep_floor):
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if (f.calc_center_median().z < 0.02) != keep_floor], context="FACES")
    bm.to_mesh(me)
    bm.free()


floor = bpy.data.objects.new("SM_Ascensor2Piso", cab.data.copy())
bpy.context.scene.collection.objects.link(floor)
split_floor(floor.data, True)
split_floor(cab.data, False)

# Colisiones: piso entero, paneles laterales (media altura), fondo (alto completo), parantes del frente.
W = 0.12
side_top = 1.3
cols = [
    ucx(cab.name, 0, (lo.x, lo.y, 0.0), (hi.x, lo.y + W, side_top)),
    ucx(cab.name, 1, (lo.x, hi.y - W, 0.0), (hi.x, hi.y, side_top)),
    ucx(cab.name, 2, (lo.x, lo.y, 0.0), (lo.x + W, hi.y, roof_z)),
    ucx(cab.name, 3, (hi.x - 0.25, lo.y, 0.0), (hi.x, -opening_half, roof_z)),
    ucx(cab.name, 4, (hi.x - 0.25, opening_half, 0.0), (hi.x, hi.y, roof_z)),
]
export([cab, *cols], "SM_Ascensor2Cabina")
export([floor, ucx(floor.name, 0, (lo.x, lo.y, -0.15), (hi.x, hi.y, 0.0))], "SM_Ascensor2Piso")
export([roof], "SM_Ascensor2Techo")
report["cabin"] = {"faces": len(cab.data.polygons), "roof_faces": len(roof.data.polygons),
                   "floor_faces": len(floor.data.polygons),
                   "size_m": [round(hi.x - lo.x, 3), round(hi.y - lo.y, 3), round(height, 3)],
                   "floor_below_m": round(-lo.z, 3), "clear_height_m": round(roof_z, 3),
                   "opening_half_m": round(opening_half, 3), "cabin_front_x_m": round(hi.x, 3)}

# --- puerta (una hoja; 4 en el juego) --------------------------------------------------------
clear()
dark = material("Ascensor2 Puerta", (0.045, 0.047, 0.05), 0.7, 0.4)
orange = material("Ascensor2 Naranja", (0.85, 0.36, 0.03), 0.3, 0.45)
glass = material("Ascensor2 Visor", (0.02, 0.03, 0.035), 0.9, 0.12)
panel_w = opening_half / 2 + 0.02
door_h = roof_z - 0.02
t = DOOR_T
parts = [
    box_mesh("hoja", (-t / 2, -panel_w / 2, 0.0), (t / 2, panel_w / 2, door_h), dark, 0.006),
    # canto naranja del lado que cierra (-Y) y franja baja
    box_mesh("canto", (-t / 2 - 0.004, -panel_w / 2, 0.0), (t / 2 + 0.004, -panel_w / 2 + 0.05, door_h), orange),
    box_mesh("zocalo", (-t / 2 - 0.003, -panel_w / 2, 0.08), (t / 2 + 0.003, panel_w / 2, 0.14), orange),
    # visor alto
    box_mesh("visor", (-t / 2 - 0.002, -panel_w / 2 + 0.12, door_h * 0.62), (t / 2 + 0.002, panel_w / 2 - 0.08, door_h * 0.88), glass),
]
door = join(parts, "SM_Ascensor2Puerta")
export([door], "SM_Ascensor2Puerta")
report["door"] = {"panel_width_m": round(panel_w, 3), "height_m": round(door_h, 3), "thickness_m": t,
                  "inner_plane_x_m": round(hi.x + DOOR_GAP + t / 2, 3),
                  "outer_plane_x_m": round(hi.x + DOOR_GAP + t + DOOR_GAP + t / 2, 3),
                  "closing_edge": "-Y (espejar para el lado izquierdo)"}

# --- tubo ------------------------------------------------------------------------------------
clear()
wall = material("Ascensor2 Tubo", (0.035, 0.036, 0.04), 0.5, 0.7)
rail = material("Ascensor2 Riel", (0.2, 0.2, 0.21), 0.9, 0.35)
rim = material("Ascensor2 Borde", (0.85, 0.36, 0.03), 0.3, 0.5)
ix, iy = half_x + MARGIN, half_y + MARGIN      # medio interior del tubo
ox, oy = ix + WALL, iy + WALL                  # medio exterior (lo que se corta del piso)
D = TUBE_DEPTH
parts = [
    box_mesh("pared+x", (ix, -oy, -D), (ox, oy, 0.0), wall),
    box_mesh("pared-x", (-ox, -oy, -D), (-ix, oy, 0.0), wall),
    box_mesh("pared+y", (-ix, iy, -D), (ix, oy, 0.0), wall),
    box_mesh("pared-y", (-ix, -oy, -D), (ix, -iy, 0.0), wall),
    box_mesh("fondo", (-ox, -oy, -D - 0.15), (ox, oy, -D), wall),
]
for sy in (-1, 1):   # rieles guia en las paredes laterales
    for x in (-0.6, 0.6):
        y0, y1 = sorted((sy * (iy - 0.06), sy * iy))
        parts.append(box_mesh("riel", (x - 0.05, y0, -D), (x + 0.05, y1, -0.02), rail, 0.01))
b = 0.1   # borde sobre el piso, montado sobre la junta
for lo_, hi_ in (((-ox - 0.02, -oy - 0.02, 0.0), (ox + 0.02, -iy + 0.0, 0.012)),
                 ((-ox - 0.02, iy, 0.0), (ox + 0.02, oy + 0.02, 0.012)),
                 ((-ox - 0.02, -iy, 0.0), (-ix, iy, 0.012)),
                 ((ix, -iy, 0.0), (ox + 0.02, iy, 0.012))):
    parts.append(box_mesh("borde", lo_, hi_, rim, 0.004))
tube = join(parts, "SM_Ascensor2Tubo")
export([tube], "SM_Ascensor2Tubo")
report["tube"] = {"inner_half_m": [round(ix, 3), round(iy, 3)], "outer_half_m": [round(ox, 3), round(oy, 3)],
                  "depth_m": D, "hole_half_m": [round(ox, 3), round(oy, 3)]}
report["travel_m"] = round(height + 0.1, 3)   # baja hasta que el techo pasa el piso

(OUT / "elevator2_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("ELEVATOR2_OK", json.dumps(report))
