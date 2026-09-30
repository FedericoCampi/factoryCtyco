"""Blender (background): escena del usuario para el estacionamiento de empleados, el piso 3 del ascensor (29/09).

blender -b --factory-startup -P Scripts/author_employee_scene.py

Fuente: 3D assets/GLBs/scenes/esceneStacionamientoOriginal.glb (patio de 24 x 22 m: cajones, cerco, barrera de entrada,
nave con portón, muelle con cinta y una plataforma con escalera y montacargas). Reemplaza a SM_EmpleadosPiso/Decor.
- Se quitan el montacargas decorativo de la plataforma (el ascensor del juego va en el piso) y el cartel "DESPACHO"
  pintado en la nave (esto es el estacionamiento de empleados, no el despacho).
- La barrera de la entrada queda levantada (los autos de los contratados entran por ahí).
- Recepción (pedido del 29/09, opción a): la sala de recepción del usuario (author_reception_room.py;
  apply_employee_scene.py la pone en ROOM) va contra la fachada, con su puerta de entrada sobre la plataforma: se quita
  el tramo de la nave que ocupa (NAVE_CUT, con la puerta de personal "03" y lo que colgaba de esa fachada) y un muro
  de ladrillo cierra el corte del lado de la nave. Van también un zócalo bajo la sala y el hueco de ladrillo del
  ascensor, detrás de la puerta doble de la sala (CABIN; abierto arriba, para ver la cabina).
- Los dos muelles de carga de la nave (rampas con rodillos, aleros, barandas, balizas y las cajas de encima) se quitan
  y su hueco queda como pared de ladrillo (pedido del 29/09).
- Alrededor: pasto y una calle de acceso hasta la entrada (sin colisión: al patio lo cierran paredes invisibles).
- Colisiones UCX como en author_parking_scene.py: obstáculos rasterizados a la altura del personaje y unidos en
  rectángulos, cajas de piso, la plataforma maciza con sus barandas, y la escalera como rampa (envolvente convexa).
Salida: SourceAssets/EmpleadosEscena/empleados_escena.fbx, EmpleadosEscena.blend y empleados_escena_build.json
(cajones, ascensor, recepción, entrada y calle en metros de Blender: Unreal local (x, y, z) cm = (x, -y, z) * 100).
"""
import bpy, bmesh, json, math, sys
from pathlib import Path
from mathutils import Matrix, Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
import floor_holes
from elevator_holes import HOLES

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/scenes/esceneStacionamientoOriginal.glb")
OUT = PROJECT / "SourceAssets/EmpleadosEscena"
NAME = "SM_EmpleadosEscena"
CELL = 0.1
BAND = (0.15, 2.0)
YARD = (-12.0, 12.0, -11.71, 10.3)            # borde de la losa (m)
ENTRANCE_X = (-10.84, -7.66)                  # hueco entre las isletas de la entrada
LANDING = (5.4, 11.4, 5.4, 8.7, 2.5)          # plataforma: x0, x1, y0, y1, arriba
ROAD_Y = (-20.0, -16.5)                       # calle de acceso (tramo este-oeste)
FLOOR_Z = 2.5                                 # piso de la recepcion (el de la plataforma)
WALL = 0.25
FACADE_Y = 8.47                               # la cara de la sala que da al patio (la fachada de la nave esta en 8,6)
# Sala de recepcion del usuario: su centro, girada para que su puerta de entrada (+x de la sala) mire al patio (-y de
# la escena) sobre la plataforma. Sala (x, y) -> escena (ROOM.x + y, ROOM.y - x); en Unreal, yaw +90. Su puerta queda
# en x 6,83..8,26 (centro 7,55), donde estaba la puerta de personal.
ROOM = (5.18, FACADE_Y + 5.13, FLOOR_Z)
ENTRY_DOOR = (ROOM[0] + 2.37, FACADE_Y, FLOOR_Z)
ROOM_OUTER = (ROOM[0] - 4.13, ROOM[0] + 4.12, ROOM[1] - 5.13, ROOM[1] + 5.13)   # x0, x1, y0, y1 con los muros
ROOM_BASE = 0.44                              # la sala trae su base de piedra debajo del piso
# Ascensor detras de la puerta doble de la sala (el muro del fondo de la sala queda en x 9,3), entrada hacia -x.
CABIN = (10.34, ROOM[1], FLOOR_Z)
SHAFT = (9.3, 11.9, CABIN[1] - 1.8, CABIN[1] + 1.8, 5.2)   # hueco de ladrillo: x0, x1, y0, y1, alto
NAVE_CUT = (ROOM_OUTER[0], ROOM_OUTER[1], FACADE_Y, 11.0, -0.5, 7.5)   # tramo de la nave que ocupa la sala
# lo que colgaba de la fachada delante de la sala (lamparas, caños, tableros, la puerta 03 con su marco y numero)
FACADE_ITEMS = (ROOM_OUTER[0] - .05, ROOM_OUTER[1] + .05, 7.7, 8.75, 0.0, 7.5)
DOCKS = ("Conveyor", "Dock ", "Rubber dock", "Loading bay", "Bay overhead masonry", "Centre bay pier", "Amber beacon")
CARTONS = ("Cardboard shipping carton", "Carton tape", "Shipping label", "Label barcode")
# el hueco de los muelles pasa a ser pared; termina donde empieza "Nave cut wall" (30/09: se pisaban en el ultimo
# tramo y sus caras coincidian, y ese pedazo de muro parpadeaba detras de los asientos de la recepcion)
DOCK_WALL = (-2.55, ROOM_OUTER[0] - WALL, 8.6, 9.2, 0.0, 6.0)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))


def world_box(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def meshes():
    return [o for o in bpy.context.scene.objects if o.type == 'MESH']


def join(objects, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = joined.data.name = name
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return joined


# --- quitar el montacargas decorativo y el cartel DESPACHO ------------------------------------------
LIFT = ("Lift ", "Lift diamond enclosure")
removed = [o.name for o in meshes() if o.name.startswith(LIFT + ("Faded DESPACHO wall sign",))]
for name in removed:
    bpy.data.objects.remove(bpy.data.objects[name])
print("REMOVED", len(removed))

# --- barrera levantada: el brazo gira 80 grados sobre su pivote -------------------------------------
pivot_lo, pivot_hi = world_box(next(o for o in meshes() if o.name.startswith("Barrier pivot")))
pivot = (pivot_lo + pivot_hi) / 2
lift = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(-80), 4, 'Y') @ Matrix.Translation(-pivot)
raised = 0
for o in meshes():
    if o.name.startswith(("Entrance barrier arm", "Red gate stripe")):
        o.matrix_world = lift @ o.matrix_world
        raised += 1
print("BARRIER_RAISED", raised)


# --- pasto y calle alrededor -------------------------------------------------------------------------
def material(name, color, rough=0.9):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def slab(name, lo, hi, mat):
    me = bpy.data.meshes.new(name)
    b = bmesh.new()
    b.loops.layers.uv.new("UVMap")
    vs = bmesh.ops.create_cube(b, size=1.0, calc_uvs=True)["verts"]
    for v in vs:
        v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
    b.to_mesh(me)
    b.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


grass = material("Surrounding grass", (0.16, 0.30, 0.10))
asphalt = material("Access road asphalt", (0.07, 0.07, 0.075), 0.8)
slab("Surrounding grass", Vector((-36.0, -30.0, -0.08)), Vector((30.0, 24.0, -0.03)), grass)
slab("Access road", Vector((ENTRANCE_X[0] - 0.4, ROAD_Y[0], -0.06)), Vector((ENTRANCE_X[1] + 0.4, YARD[2] + 0.01, -0.01)), asphalt)
slab("Access road", Vector((-36.0, ROAD_Y[0], -0.06)), Vector((ENTRANCE_X[1] + 0.4, ROAD_Y[1], -0.01)), asphalt)
NO_COLLISION = ("Surrounding grass", "Access road")

# --- pozo del ascensor (ya no hay: va detras de la puerta) y vano de la puerta -----------------------
_, hole_cut = floor_holes.cut_visuals(meshes(), "empleados")


def cut_box(box):
    """Abre un hueco (booleano) en las piezas que cruzan la caja; quita las que quedan adentro."""
    x0, x1, y0, y1, z0, z1 = box
    clo, chi = Vector((x0, y0, z0)), Vector((x1, y1, z1))
    cutter = slab("door_cutter", clo, chi, grass)
    cut = []
    for o in [o for o in meshes() if o is not cutter]:
        lo, hi = world_box(o)
        if not all(lo[i] < chi[i] and hi[i] > clo[i] for i in range(3)):
            continue
        if all(lo[i] >= clo[i] - 1e-4 and hi[i] <= chi[i] + 1e-4 for i in range(3)):
            bpy.data.objects.remove(o)
            continue
        o.data = o.data.copy()
        mod = o.modifiers.new("door", "BOOLEAN")
        mod.operation, mod.solver, mod.object = "DIFFERENCE", "EXACT", cutter
        cutter.data.materials.clear()
        if o.data.materials and o.data.materials[0]:
            cutter.data.materials.append(o.data.materials[0])
        mod.material_mode = "TRANSFER"
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=mod.name)
        cut.append(o.name)
    bpy.data.objects.remove(cutter)
    return cut


def inside(o, box):
    lo, hi = world_box(o)
    x0, x1, y0, y1, z0, z1 = box
    return lo.x >= x0 and hi.x <= x1 and lo.y >= y0 and hi.y <= y1 and lo.z >= z0 - 1e-3 and hi.z <= z1


# los dos muelles de carga, y las cajas que estaban sobre sus rampas (las de los pallets del patio quedan)
docks = [o for o in meshes() if o.name.startswith(DOCKS)
         or o.name.startswith(CARTONS) and (world_box(o)[0].y + world_box(o)[1].y) / 2 > 7.3 and -3.0 < world_box(o)[0].x < 5.0]
for o in docks:
    bpy.data.objects.remove(o)
# lo que colgaba de la fachada donde va la sala, y el tramo de la nave que ocupa
facade_items = [o for o in meshes() if inside(o, FACADE_ITEMS)]
for o in facade_items:
    bpy.data.objects.remove(o)
nave_cut = cut_box(NAVE_CUT)
print("DOCKS", len(docks), "FACADE_ITEMS", len(facade_items), "NAVE_CUT", nave_cut)

brick = bpy.data.materials.get("Varied terracotta brick courses")
concrete = bpy.data.materials.get("Weathered concrete")
V = Vector
sx0, sx1, sy0, sy1, stop = SHAFT
dx0, dx1, dy0, dy1, dz0, dz1 = DOCK_WALL
SOLID = [   # (nombre, desde, hasta, material, con colision)
    ("Dock wall fill", V((dx0, dy0, dz0)), V((dx1, dy1, dz1)), brick, True),
    ("Nave cut wall", V((ROOM_OUTER[0] - WALL, 8.6, 0)), V((ROOM_OUTER[0], 10.9, 6.0)), brick, True),
    ("Reception plinth", V((ROOM_OUTER[0], ROOM_OUTER[2], 0)), V((ROOM_OUTER[1], ROOM_OUTER[3], FLOOR_Z - ROOM_BASE + .02)), concrete, True),
    ("Elevator shaft east", V((sx1 - WALL, sy0, 0)), V((sx1, sy1, stop)), brick, True),
    ("Elevator shaft north", V((sx0, sy1 - WALL, 0)), V((sx1, sy1, stop)), brick, True),
    ("Elevator shaft south", V((sx0, sy0, 0)), V((sx1, sy0 + WALL, stop)), brick, True),
]
reception_ucx = []
for name, lo, hi, mat, collide in SOLID:
    slab(name, lo, hi, mat)
    if collide:
        reception_ucx.append((lo, hi))
# el muro de la nave al este de la sala, en el tramo fuera de la grilla del patio
reception_ucx.append((V((9.3, YARD[3], 0)), V((9.9, 10.9, 6.0))))

# --- colisiones: rasterizar ----------------------------------------------------------------------------
STAIRS = ("Stair tread", "Stair vertical riser", "Stair stringer")
LANDING_SOLID = ("Upper landing slab", "Landing ", "Retaining wall water streak", "Retaining formwork joint")
IGNORE = NO_COLLISION + ("Crack weed tuft", "Scuffed paint fleck", "Foundation weather streak", "Yard thick foundation",
                         "Entrance barrier arm", "Red gate stripe")
parts = [(o, *world_box(o)) for o in meshes()]
lo_all = Vector((YARD[0], YARD[2], 0.0))
hi_all = Vector((YARD[1], YARD[3], 0.0))
nx = int(math.ceil((hi_all.x - lo_all.x) / CELL))
ny = int(math.ceil((hi_all.y - lo_all.y) / CELL))
block = [[0.0] * ny for _ in range(nx)]
floor = [[False] * ny for _ in range(nx)]


def cells(lo, hi):
    i0 = max(0, int((lo.x - lo_all.x) / CELL + 1e-6)); i1 = min(nx - 1, int((hi.x - lo_all.x) / CELL - 1e-6))
    j0 = max(0, int((lo.y - lo_all.y) / CELL + 1e-6)); j1 = min(ny - 1, int((hi.y - lo_all.y) / CELL - 1e-6))
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            yield i, j


rails = []
for o, lo, hi in parts:
    if o.name.startswith(IGNORE + STAIRS) or o.name.startswith(LANDING_SOLID) and not o.name.startswith(("Landing horizontal rail", "Landing guard post")):
        continue
    if o.name.startswith(("Landing horizontal rail", "Landing guard post")):
        rails.append((lo, hi))      # barandas de la plataforma: cajas propias, por encima de la banda
        continue
    if -0.1 <= hi.z <= 0.06 and (hi.x - lo.x) > 0.3 and (hi.y - lo.y) > 0.3:
        for i, j in cells(lo, hi):
            floor[i][j] = True
    elif lo.z < BAND[1] and hi.z > BAND[0]:
        for i, j in cells(lo, hi):
            block[i][j] = max(block[i][j], hi.z)
# la plataforma es un bloque macizo hasta su piso
for i, j in cells(Vector((LANDING[0], LANDING[2], 0)), Vector((LANDING[1], LANDING[3], 0))):
    block[i][j] = max(block[i][j], LANDING[4])
    floor[i][j] = False
# donde va la sala mandan su zocalo y sus propias colisiones
for i, j in cells(Vector((ROOM_OUTER[0], ROOM_OUTER[2], 0)), Vector((ROOM_OUTER[1], ROOM_OUTER[3], 0))):
    block[i][j] = 0.0
    floor[i][j] = False

def rectangles(value):
    used = [[False] * ny for _ in range(nx)]
    out = []
    for i in range(nx):
        for j in range(ny):
            v = value(i, j)
            if not v or used[i][j]:
                continue
            j2 = j
            while j2 + 1 < ny and not used[i][j2 + 1] and value(i, j2 + 1) == v:
                j2 += 1
            i2 = i
            while i2 + 1 < nx and all(not used[i2 + 1][k] and value(i2 + 1, k) == v for k in range(j, j2 + 1)):
                i2 += 1
            for a in range(i, i2 + 1):
                for b in range(j, j2 + 1):
                    used[a][b] = True
            out.append((lo_all.x + i * CELL, lo_all.y + j * CELL, lo_all.x + (i2 + 1) * CELL, lo_all.y + (j2 + 1) * CELL, v))
    return out


# clases de altura: escalones bajos, muros bajos, cerco, plataforma (2,5 m exacto) y altos
def height_class(i, j):
    top = block[i][j]
    if not top:
        return 0
    if abs(top - LANDING[4]) < 1e-6:
        return 4
    return 1 if top <= 0.45 else 2 if top <= 1.4 else 3 if top <= 2.2 else 5


blockers = []
for x0, y0, x1, y1, _ in rectangles(height_class):
    tops = [block[i][j] for i, j in cells(Vector((x0 + CELL / 2, y0 + CELL / 2, 0)), Vector((x1 - CELL / 2, y1 - CELL / 2, 0)))]
    blockers.append((x0, y0, x1, y1, max(tops)))
floors = rectangles(lambda i, j: floor[i][j] and block[i][j] == 0 and 1)

# --- malla visual -------------------------------------------------------------------------------------
all_meshes = meshes()
bpy.ops.object.select_all(action='DESELECT')
for o in all_meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = all_meshes[0]
bpy.ops.object.join()
visual = bpy.context.view_layer.objects.active
visual.name = NAME
visual.data.name = NAME
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(bpy.context.scene.objects):
    if o is not visual and o.type != 'MESH':
        bpy.data.objects.remove(o)

# --- colisiones: cajas ------------------------------------------------------------------------------------
count = 0


def ucx_box(lo, hi):
    global count
    me = bpy.data.meshes.new(f"UCX_{NAME}_{count:03d}")
    b = bmesh.new()
    vs = bmesh.ops.create_cube(b, size=1.0)["verts"]
    c, s = (lo + hi) / 2, hi - lo
    for v in vs:
        v.co = Vector((v.co.x * s.x, v.co.y * s.y, v.co.z * s.z)) + c
    b.to_mesh(me)
    b.free()
    o = bpy.data.objects.new(me.name, me)
    bpy.context.scene.collection.objects.link(o)
    count += 1
    return o


for x0, y0, x1, y1, top in blockers:
    ucx_box(Vector((x0, y0, 0.0)), Vector((x1, y1, top)))
for x0, y0, x1, y1, _ in floors:
    ucx_box(Vector((x0, y0, -0.4)), Vector((x1, y1, 0.0)))
# (la fuente repite dos postes de esquina: sin cajas repetidas, Unreal las descarta)
rails = list({(tuple(round(c, 3) for c in lo), tuple(round(c, 3) for c in hi)): (lo, hi) for lo, hi in rails}.values())
for lo, hi in rails:
    ucx_box(Vector((lo.x, lo.y, LANDING[4])), Vector((hi.x, hi.y, max(hi.z, LANDING[4] + 1.0))))
for lo, hi in reception_ucx:
    ucx_box(lo, hi)
# paredes invisibles en el borde de la losa: el personaje no sale del patio (tampoco por la entrada)
# (la del fondo se corta donde esta la sala, que pisa por encima)
for lo, hi in (((YARD[0] - 0.3, YARD[2] - 0.3, 0), (YARD[1] + 0.3, YARD[2], 3.0)),
               ((YARD[0] - 0.3, YARD[3], 0), (ROOM_OUTER[0] - WALL, YARD[3] + 0.3, 3.0)),
               ((ROOM_OUTER[1], YARD[3], 0), (YARD[1] + 0.3, YARD[3] + 0.3, 3.0)),
               ((YARD[0] - 0.3, YARD[2], 0), (YARD[0], YARD[3], 3.0)),
               ((YARD[1], YARD[2], 0), (YARD[1] + 0.3, YARD[3], 3.0))):
    ucx_box(Vector(lo), Vector(hi))
# escalera: rampa (envolvente convexa de peldaños y contrahuellas), de la fuente sin unir
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
stair = bmesh.new()
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith(("Stair tread", "Stair vertical riser"))]:
    b = bmesh.new()
    b.from_mesh(o.data)
    b.transform(o.matrix_world)
    for v in b.verts:
        stair.verts.new(v.co)
    b.free()
bmesh.ops.convex_hull(stair, input=stair.verts[:])
me = bpy.data.meshes.new(f"UCX_{NAME}_{count:03d}")
stair.to_mesh(me)
stair.free()
bpy.context.scene.collection.objects.link(bpy.data.objects.new(me.name, me))
count += 1
for o in list(bpy.context.scene.objects):
    if o is not visual and not o.name.startswith("UCX_"):
        bpy.data.objects.remove(o)


def _hole_box(lo, hi):
    return ucx_box(lo, hi)


_ucx, hole_split = floor_holes.split_collisions([o for o in bpy.context.scene.objects if o.name.startswith("UCX_")], "empleados", _hole_box)
# nombres correlativos (split_collisions borra y agrega)
for index, o in enumerate(sorted(_ucx, key=lambda o: o.name)):
    o.name = o.data.name = f"UCX_{NAME}_tmp{index:03d}"
for index, o in enumerate(sorted(_ucx, key=lambda o: o.name)):
    o.name = o.data.name = f"UCX_{NAME}_{index:03d}"
count = len(_ucx)

# --- datos para Unreal -----------------------------------------------------------------------------------
FRONT = [(-5.9, "F0"), (-3.1, "F1"), (-0.3, "F2"), (2.5, "F3"), (5.3, "F4")]
REAR = [(-8.1, "R0"), (-5.3, "R1"), (-2.5, "R2"), (0.3, "R3"), (3.1, "R4")]
stalls = [{"id": k, "x": x, "y": -7.8, "nose": -1} for x, k in FRONT] + [{"id": k, "x": x, "y": 3.45, "nose": 1} for x, k in REAR]

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "EmpleadosEscena.blend"))
def export(objects, filename):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / filename), use_selection=True, object_types={'MESH'},
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE', path_mode='COPY',
        embed_textures=True, axis_forward='-Y', axis_up='Z')


export([visual] + [o for o in bpy.context.scene.objects if o.name.startswith("UCX_")], "empleados_escena.fbx")
report = {"source": str(SOURCE), "removed": len(removed), "barrier_raised": raised,
          "faces": len(visual.data.polygons), "materials": [m.name for m in visual.data.materials], "ucx": count,
          "elevator": {"centre_m": list(CABIN), "yaw_unreal": 180},
          "reception": {"room_m": list(ROOM), "room_yaw_unreal": 90, "room_outer_m": ROOM_OUTER, "entry_door_m": list(ENTRY_DOOR),
                        "floor_z_m": FLOOR_Z, "shaft_m": SHAFT, "nave_cut": nave_cut, "docks_removed": len(docks),
                        "facade_items_removed": len(facade_items)},
          "blocker_boxes": len(blockers), "floor_boxes": len(floors), "rail_boxes": len(rails),
          "yard_m": YARD, "entrance_x_m": ENTRANCE_X, "road_y_m": ROAD_Y, "landing_m": LANDING, "stalls": stalls}
(OUT / "empleados_escena_build.json").write_text(json.dumps(report, indent=1))
print("### EMPLEADOS_ESCENA", json.dumps({k: v for k, v in report.items() if k != "stalls"}))
