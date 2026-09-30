"""Blender (background): la sala de recepción del usuario, lista para Unreal (29/09).

blender -b --factory-startup -P Scripts/author_reception_room.py

Fuente: 3D assets/GLBs/scenes/recepcion/recepcion (scene.glb con las piezas sueltas y scene_unreal.fbx con sus 32 colisiones
UCX). Sala de 10 x 8 m sin techo (lados bajos con baranda para la cámara isométrica), con mostrador, archivero,
asientos, mesita, reloj y planta; puerta lateral de entrada (abierta hacia afuera, con escalón) y una puerta doble con
franja de peligro en el muro del fondo.
- Se quitan las hojas de la puerta doble (y sus manijas, ventanitas, marcos y bisagras) y sus dos colisiones: el vano
  del muro queda abierto y detrás va el ascensor del juego (apply_employee_scene.py lo pone ahí).
- La hoja de la puerta de entrada (abierta hacia afuera) queda sin colision: en el pasillo angostaba el paso.
- La maceta junto a la entrada tampoco tiene colision: el camino al ascensor pasa pegado a ella.
- Los asientos de espera y la mesita pasan al frente de la sala (del lado de la baranda) y se dan vuelta: el respaldo
  contra la baranda y la mesita delante, mirando hacia el mostrador (pedido del 29/09). Sus colisiones van con ellos.
- El lado de la puerta de entrada (+x de la sala) era un muro bajo con remate; ahora da al patio del estacionamiento y
  pasa a ser muro completo (3,5 m, pedido del 29/09): se apilan copias de las hileras de ladrillo del muro bajo, se sube
  el remate y la columna de la esquina, y la colisión llega arriba.
- La hoja de la puerta de entrada venía fija, abierta hacia afuera: se separa, se cierra y se exporta aparte
  (SM_PuertaRecepcionSala, origen en la bisagra, cerrada hacia -X) para que la abra AFactoryAutoDoor.
- Se une todo en una malla (SM_RecepcionSala) con las colisiones restantes.
Salida: SourceAssets/Recepcion/recepcion_sala.fbx, puerta_recepcion_sala.fbx y recepcion_build.json (metros de Blender de la sala: origen en el
centro del piso, la puerta de entrada en +x, la puerta doble en +y; Unreal local (x, y, z) cm = (x, -y, z) * 100).
"""
import json, math
from pathlib import Path
import bpy, bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/scenes/recepcion/recepcion")
OUT = ROOT / "SourceAssets/Recepcion"
NAME = "SM_RecepcionSala"
DOUBLE_DOOR = ("Closed steel double door", "Door pull", "Door inset dark window", "Window frame", "Door hinge")
OPENING = (-1.25, 1.25, 3.7, 4.2, 0.0, 2.65)   # vano de la puerta doble: x0, x1, y0, y1, z0, z1
SIDE_LEAF = (5.0, 6.45, 2.4, 3.2, 0.0, 2.7)     # hoja de la puerta de entrada, abierta hacia afuera: sin colision
DOOR_PLANT = (4.1, 4.8, 2.9, 3.55, 0.0, 0.8)    # maceta junto a la entrada: sin colision (los empleados la rozaban)
# (caja donde estaban, centro nuevo en la sala); se giran 180 grados
SEATS = ((1.4, 4.0, 2.2, 3.2, -0.01, 1.35), (2.7, -3.2))     # banco de tres asientos
TABLE = ((2.2, 4.0, 0.95, 2.05, -0.01, 0.75), (2.7, -2.1))   # mesita con sus revistas


def moved_there(box, centre):
    x0, x1, y0, y1 = box[:4]
    c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, 0))
    return Matrix.Translation((centre[0], centre[1], 0)) @ Matrix.Rotation(math.pi, 4, 'Z') @ Matrix.Translation(-c)
WALL_TOP = 3.5                                   # altura de los muros completos de la sala
LOW_WALL = (4.85, 5.15, -4.05, 1.66)             # muro bajo del lado de la entrada: x0, x1, y0, y1
CORNER = (4.7, 5.3, -4.3, -3.7)                  # columna de la esquina de ese muro con el frente
LEAF = ("Outward open side door", "Side door lever", "Side door window dark", "Side door window frame")


def world_box(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return (Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)]))


def inside(o, box):
    lo, hi = world_box(o)
    x0, x1, y0, y1, z0, z1 = box
    return lo.x >= x0 and hi.x <= x1 and lo.y >= y0 and hi.y <= y1 and lo.z >= z0 - 1e-3 and hi.z <= z1


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE / "scene.glb"))
removed = [o.name for o in bpy.context.scene.objects if o.type == 'MESH' and (o.name.startswith(DOUBLE_DOOR) or inside(o, OPENING))]
for name in removed:
    bpy.data.objects.remove(bpy.data.objects[name])
moved = []
for box, centre in (SEATS, TABLE):
    move = moved_there(box, centre)
    for o in [o for o in bpy.context.scene.objects if o.type == 'MESH' and inside(o, box)]:
        o.matrix_world = move @ o.matrix_world
        moved.append(o.name)
print("SEATS_AND_TABLE_MOVED", len(moved))


# --- el muro bajo de la entrada pasa a muro completo ------------------------------------------------------
low = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith("Right low wall individual brick")]
row_z = sorted({round(world_box(o)[0].z, 3) for o in low})
pitch = min(b - a for a, b in zip(row_z, row_z[1:]))
stack = pitch * len(row_z)                     # alto de un bloque de hileras
raised = []
for k in range(1, 20):
    shift = stack * k
    if row_z[0] + shift >= WALL_TOP - .02:
        break
    for o in low:
        lo, hi = world_box(o)
        if hi.z + shift > WALL_TOP - .15:      # debajo del remate
            continue
        copy = o.copy()
        copy.matrix_world = Matrix.Translation((0, 0, shift)) @ o.matrix_world
        bpy.context.scene.collection.objects.link(copy)
        raised.append(copy)
core = next(o for o in bpy.context.scene.objects if o.name.startswith("Right low wall mortar core"))
clo, chi = world_box(core)
core_copy = core.copy()
core_copy.data = core.data.copy()
bpy.context.scene.collection.objects.link(core_copy)
scale_z = (WALL_TOP - chi.z) / (chi.z - clo.z)
core_copy.matrix_world = Matrix.Translation((0, 0, chi.z)) @ Matrix.Scale(scale_z, 4, (0, 0, 1)) @ Matrix.Translation((0, 0, -clo.z)) @ core.matrix_world
coping = next(o for o in bpy.context.scene.objects if o.name.startswith("Right low coping"))
upper = next(o for o in bpy.context.scene.objects if o.name.startswith("Right upper coping"))
coping.matrix_world = Matrix.Translation((0, 0, world_box(upper)[0].z - world_box(coping)[0].z)) @ coping.matrix_world
# la columna de la esquina (y su corona) llega arriba como las otras
corner = [o for o in bpy.context.scene.objects if o.type == 'MESH' and inside(o, (*CORNER, -0.1, 4.0))]
column = next((o for o in corner if o.name.startswith("Square structural column")), None)
crown = next((o for o in corner if o.name.startswith("Concrete column crown")), None)
if column:
    lo, hi = world_box(column)
    column.matrix_world = Matrix.Translation((0, 0, lo.z)) @ Matrix.Scale((WALL_TOP - lo.z) / (hi.z - lo.z), 4, (0, 0, 1)) @ Matrix.Translation((0, 0, -lo.z)) @ column.matrix_world
    if crown:
        crown.matrix_world = Matrix.Translation((0, 0, WALL_TOP - .03 - world_box(crown)[0].z)) @ crown.matrix_world
print("WALL_RAISED bricks", len(raised), "pitch", round(pitch, 3), "column", bool(column), "crown", bool(crown))

# --- la hoja de la puerta de entrada, aparte y cerrada -----------------------------------------------------
leaf_parts = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith(LEAF)]
panel = next(o for o in leaf_parts if o.name.startswith("Outward open side door"))
plo, phi = world_box(panel)
hinge = Vector((plo.x, phi.y, plo.z))         # queda contra la jamba, del lado de y alto
open_angle = math.atan2(phi.x - plo.x, phi.y - plo.y)   # cuanto giro desde cerrada (hacia -y) hacia afuera (+x)
leaf_width = math.hypot(phi.x - plo.x, phi.y - plo.y)
bpy.ops.object.select_all(action='DESELECT')
for o in leaf_parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = panel
bpy.ops.object.join()
leaf = bpy.context.view_layer.objects.active
leaf.name = leaf.data.name = "SM_PuertaRecepcionSala"
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# cerrarla: girar sobre la bisagra hasta quedar a lo largo de -y; y dejarla a lo largo de -X (como espera AFactoryAutoDoor)
leaf.data.transform(Matrix.Rotation(-math.pi / 2, 4, 'Z') @ Matrix.Rotation(-open_angle, 4, 'Z') @ Matrix.Translation(-hinge))
print("LEAF hinge", [round(v, 2) for v in hinge], "open_deg", round(math.degrees(open_angle), 1), "width", round(leaf_width, 2))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o is not leaf]
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
visual = bpy.context.view_layer.objects.active
visual.name = visual.data.name = NAME
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(bpy.context.scene.objects):
    if o is not visual and o is not leaf:
        bpy.data.objects.remove(o)

# colisiones del usuario (del FBX), menos las de las hojas de la puerta doble
before = set(bpy.context.scene.objects)
bpy.ops.import_scene.fbx(filepath=str(SOURCE / "scene_unreal.fbx"))
imported = [o for o in bpy.context.scene.objects if o not in before]
extra_ucx = []   # muro completo de la entrada y la columna de su esquina
ucx, dropped = [], []
for o in sorted(imported, key=lambda o: o.name):
    if not o.name.startswith("UCX_"):
        continue
    if inside(o, OPENING) or inside(o, SIDE_LEAF) or inside(o, DOOR_PLANT):
        dropped.append(o.name)
        continue
    for box, centre in (SEATS, TABLE):
        if inside(o, box):
            o.matrix_world = moved_there(box, centre) @ o.matrix_world
            break
    world = o.matrix_world.copy()
    o.parent = None
    o.matrix_world = world
    o.data = o.data.copy()   # las cajas comparten malla: cada una la suya para aplicar su transformacion
    ucx.append(o)
for o in imported:
    if o not in ucx:
        bpy.data.objects.remove(o)
for index, o in enumerate(ucx):
    o.data.transform(o.matrix_world)
    o.matrix_world.identity()
    o.name = o.data.name = f"UCX_{NAME}_{index:03d}"
for index_lo, index_hi in ((Vector((4.87, -4.0, 0.8)), Vector((5.13, 1.65, WALL_TOP))),
                           (Vector((4.8, -4.21, 1.5)), Vector((5.2, -3.79, WALL_TOP)))):
    me = bpy.data.meshes.new("wall_ucx")
    b = bmesh.new()
    vs = bmesh.ops.create_cube(b, size=1.0)["verts"]
    for v in vs:
        v.co = Vector((v.co.x * (index_hi.x - index_lo.x), v.co.y * (index_hi.y - index_lo.y), v.co.z * (index_hi.z - index_lo.z))) + (index_lo + index_hi) / 2
    b.to_mesh(me)
    b.free()
    extra = bpy.data.objects.new("wall_ucx", me)
    bpy.context.scene.collection.objects.link(extra)
    ucx.append(extra)
for index, o in enumerate(ucx):
    o.name = o.data.name = f"UCX_{NAME}_{index:03d}"
lo, hi = world_box(visual)
if hi.x - lo.x < 9 or hi.y - lo.y < 7:
    raise RuntimeError(f"La sala quedo con otro tamano: {lo} {hi}")

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "RecepcionSala.blend"))
def export(objects, filename):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / filename), use_selection=True, object_types={'MESH'},
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE', path_mode='COPY',
        embed_textures=True, axis_forward='-Y', axis_up='Z')


export([visual] + ucx, "recepcion_sala.fbx")
export([leaf], "puerta_recepcion_sala.fbx")
report = {"source": str(SOURCE), "removed": len(removed), "seats_and_table_moved": len(moved), "ucx": len(ucx), "ucx_dropped": dropped,
          "faces": len(visual.data.polygons), "bounds_m": [[round(v, 2) for v in lo], [round(v, 2) for v in hi]],
          "entry_door_m": {"x": 5.0, "y": [1.65, 3.08]}, "double_door_m": {"x": [-1.17, 1.17], "y": 4.0},
          "outer_m": {"x": [-5.13, 5.13], "y": [-4.13, 4.12]},
          "entry_leaf": {"hinge_m": [round(v, 3) for v in hinge], "width_m": round(leaf_width, 2),
                         "was_open_deg": round(math.degrees(open_angle), 1)},
          "wall_raised_bricks": len(raised)}
(OUT / "recepcion_build.json").write_text(json.dumps(report, indent=1))
print("### RECEPCION", json.dumps(report))
