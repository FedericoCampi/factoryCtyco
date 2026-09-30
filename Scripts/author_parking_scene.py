"""Blender (background): turn the user's parking GLB into an Unreal-ready FBX.

blender -b --factory-startup -P Scripts/author_parking_scene.py

- Joins the 1422 loose pieces into one visual mesh (materials preserved).
- Adds a flush steel threshold plate over the seam with the factory's west door.
- Builds UCX box collisions: blockers are rasterised at robot height and
  greedily merged into rectangles; floors and the terrace get their own boxes;
  the loading ramp keeps convex hulls so it stays walkable.
"""
import bpy, bmesh, json, math, re, sys
from pathlib import Path
from mathutils import Matrix, Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
import floor_holes  # pozo del ascensor de la terraza (27/09/2026)

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/scenes/sceneStacionamiento.glb")
OUT = PROJECT / "SourceAssets/Parking"
NAME = "SM_Parking"
CELL = 0.1          # rasterisation step (m)
BAND = (0.15, 2.0)  # heights that block a 1.8 m robot
DOOR_Y = (-6.65, -3.35)   # east opening measured in the GLB (Blender metres)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
# Removed on request (2026-09-26): the arcade pier nearest the south gateway (y = -4) and the
# beam that joined it to the back wall, so the car lane between both gateways is clear.
BEAMS = ("Exposed transverse I beam", "Transverse beam flange", "Beam end connection plate", "Connection bolt")
# Removed on request (2026-09-27): west wall bay 3 (y 4..8) below its upper brick, so the
# Despacho_Machine placed in front of it looks built into the wall and fed from outside.
# Piers, upper brick and lintel stay as the opening's frame.
WEST_OPENING = (-11.25, -10.6, 4.0, 8.0, 2.52)  # x0, x1, y0, y1, max top z
def _removed(o):
    if o.name.startswith("Arcade free pier -4 "): return True
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
    x0, x1, y0, y1, top = WEST_OPENING
    if (min(xs) >= x0 and max(xs) <= x1 and min(ys) >= y0 - 1e-3 and max(ys) <= y1 + 1e-3
            and min(zs) >= -0.01 and max(zs) <= top):
        return True
    return o.name.startswith(BEAMS) and min(ys) >= -4.3 and max(ys) <= -3.7
removed = [o.name for o in list(bpy.context.scene.objects) if o.type == 'MESH' and _removed(o)]
for name in removed: bpy.data.objects.remove(bpy.data.objects[name])
print("REMOVED", len(removed), sorted({n.split('.')[0] for n in removed}))
# Split out on request (2026-09-27): the two remaining arcade piers (y = 0 and 4) and their beams
# are now separate actors the user moves by hand (author_parking_columns.py + apply_parking_columns.py).
def _column(o):
    if o.name.startswith(("Arcade free pier 0 ", "Arcade free pier 4 ")): return True
    ys = [(o.matrix_world @ Vector(c)).y for c in o.bound_box]
    mid = (min(ys) + max(ys)) / 2
    return o.name.startswith(BEAMS) and any(abs(mid - y) < 0.3 for y in (0.0, 4.0))
columns = [o.name for o in bpy.context.scene.objects if o.type == 'MESH' and _column(o)]
for name in columns: bpy.data.objects.remove(bpy.data.objects[name])
print("COLUMNS_SPLIT", len(columns))

# Requested 2026-09-27 for Despacho_Machine2, which the user set into the west wall: the windows of
# bays 1 and 2 (y -4..4) become brick, then the wall behind the machine is cut open (floor to the
# upper brick, 2.48 m) and the cut is lined with a steel frame. The machine's span comes from
# wall_openings.json (Scripts/export_wall_openings.py, run in the editor after moving it).
WINDOW_BAYS = (-11.25, -10.6, -4.0, 4.0, 0.9, 2.52)  # x0, x1, y0, y1, z0, z1
_span = json.loads((OUT / "wall_openings.json").read_text(encoding="utf-8"))[0]["y"]
OPENING2 = (-11.5, -10.4, _span[0], _span[1], 0.0, 2.48)    # x0, x1, y0, y1, z0, z1
print("OPENING2", OPENING2)
def _inside(o, box):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    x0, x1, y0, y1, z0, z1 = box
    return (min(p.x for p in pts) >= x0 and max(p.x for p in pts) <= x1 and min(p.y for p in pts) >= y0 - 1e-3
            and max(p.y for p in pts) <= y1 + 1e-3 and min(p.z for p in pts) >= z0 and max(p.z for p in pts) <= z1)
windows = [o.name for o in bpy.context.scene.objects if o.type == 'MESH' and _inside(o, WINDOW_BAYS)]
for name in windows: bpy.data.objects.remove(bpy.data.objects[name])

def fill_with(src_name, axis, start, stop):
    """Copies src_name along axis (0=x, 2=z) so they cover start..stop, clipping the last one."""
    src = bpy.data.objects[src_name]
    pts = [src.matrix_world @ Vector(c) for c in src.bound_box]
    lo, size = min(p[axis] for p in pts), max(p[axis] for p in pts) - min(p[axis] for p in pts)
    made, offset = [], start - lo
    while lo + offset < stop - 1e-4:
        copy = src.copy(); copy.data = src.data.copy(); copy.name = f"{src_name} fill"
        bpy.context.scene.collection.objects.link(copy)
        shift = Vector((0, 0, 0)); shift[axis] = offset
        copy.matrix_world = Matrix.Translation(shift) @ src.matrix_world
        bm = bmesh.new(); bm.from_mesh(copy.data); bm.transform(copy.matrix_world)
        co, no = Vector((0, 0, 0)), Vector((0, 0, 0)); co[axis] = stop; no[axis] = 1
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no, clear_outer=True)
        bm.transform(copy.matrix_world.inverted()); bm.to_mesh(copy.data); bm.free()
        made.append(copy.name); offset += size
    return made

filled = fill_with("Window bay 1 lower brick", 2, 0.94, 2.48) + fill_with("Window bay 2 lower brick", 2, 0.94, 2.48)
print("WINDOWS_WALLED", len(windows), "fill pieces", len(filled))

def cut_opening(box):
    """Removes every wall piece's geometry inside box (pieces fully within its x span, above the floor)."""
    x0, x1, y0, y1, z0, z1 = box
    cut = 0
    for o in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        if (min(p.x for p in pts) < x0 or max(p.x for p in pts) > x1 or min(p.z for p in pts) < z0 - 0.05
                or max(p.y for p in pts) <= y0 or min(p.y for p in pts) >= y1 or min(p.z for p in pts) >= z1):
            continue
        o.data = o.data.copy()  # las piezas del GLB comparten malla (todos los vanos): cortar solo esta
        bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world)
        for co, no in (((0, y0, 0), (0, 1, 0)), ((0, y1, 0), (0, 1, 0)), ((0, 0, z1), (0, 0, 1))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
        inner = [f for f in bm.faces if (lambda c: y0 < c.y < y1 and c.z < z1)(f.calc_center_median())]
        bmesh.ops.delete(bm, geom=inner, context="FACES")
        bm.transform(o.matrix_world.inverted()); bm.to_mesh(o.data); bm.free()
        if not o.data.polygons:
            bpy.data.objects.remove(o)
        cut += 1
    # marco de acero: dos laterales y dintel, del espesor del muro
    steel = bpy.data.materials.get("Charcoal blue structural steel")
    t = 0.06
    for lo, hi in (((-11.25, y0, 0.0), (-10.75, y0 + t, z1)), ((-11.25, y1 - t, 0.0), (-10.75, y1, z1)),
                   ((-11.25, y0, z1 - t), (-10.75, y1, z1))):
        me = bpy.data.meshes.new("Opening steel frame")
        b = bmesh.new(); uv = b.loops.layers.uv.new("UVMap")
        vs = bmesh.ops.create_cube(b, size=1.0, calc_uvs=True)["verts"]
        lo, hi = Vector(lo), Vector(hi)
        for v in vs: v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
        b.to_mesh(me); b.free()
        if steel: me.materials.append(steel)
        bpy.context.scene.collection.objects.link(bpy.data.objects.new(me.name, me))
    return cut

print("OPENING2 cut pieces", cut_opening(OPENING2))

# Requested 2026-09-28 for the truck, which now drives straight across (west -> east door):
# the south gateway is closed with a copy of the next low wall segment (Perimeter 01, x -7..-3.5,
# moved 3.5 m west) and loses its yellow stripes; west wall bay 0 (y -8..-4, left of the old
# gateway seen from an entering truck) is opened from the floor to its upper brick, like OPENING2.
TRUCK_OPENING = (-11.5, -10.4, -7.69, -4.31, 0.0, 2.48)   # between the end pier and pier -4
stripes = [o.name for o in bpy.context.scene.objects if o.name.startswith("South gateway yellow stripe")]
for name in stripes: bpy.data.objects.remove(bpy.data.objects[name])
gate_fill = []
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith("Perimeter 01 ")]:
    copy = o.copy(); copy.name = o.name.replace("Perimeter 01", "Perimeter gate fill")
    bpy.context.scene.collection.objects.link(copy)
    copy.matrix_world = Matrix.Translation((-3.5, 0, 0)) @ o.matrix_world
    gate_fill.append(copy.name)
print("SOUTH_GATE_CLOSED stripes", len(stripes), "fill pieces", len(gate_fill))
print("TRUCK_OPENING cut pieces", cut_opening(TRUCK_OPENING))

# Outside the opening the ground (Piso_Exterior) is 65 cm lower: a concrete driveway, level for
# 6 m and then sloping down 4 m, so the truck reaches the opening level (climbing right at the wall
# it tipped up and its cab touched the lintel). Only the truck uses it: no collision (IGNORE).
DRIVEWAY = (-17.3, -11.3, TRUCK_OPENING[2] - 0.3, TRUCK_OPENING[3] + 0.3, -0.65)  # x0, x1, y0, y1, bottom
RAMP_RUN = 4.0
def driveway():
    concrete = bpy.data.materials.get("Ramp brushed grey concrete")
    x0, x1, y0, y1, bottom = DRIVEWAY
    me = bpy.data.meshes.new("Truck driveway")
    b = bmesh.new(); b.loops.layers.uv.new("UVMap")
    for lo, hi, slope in (((x0, y0, bottom), (x1, y1, 0.0), False), ((x0 - RAMP_RUN, y0, bottom), (x0, y1, 0.0), True)):
        vs = bmesh.ops.create_cube(b, size=1.0, calc_uvs=True)["verts"]
        lo, hi = Vector(lo), Vector(hi)
        for v in vs:
            outer, top = v.co.x < 0, v.co.z > 0
            v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
            if slope and outer and top: v.co.z = bottom + 0.02  # the ramp meets the ground
    b.to_mesh(me); b.free()
    if concrete: me.materials.append(concrete)
    bpy.context.scene.collection.objects.link(bpy.data.objects.new(me.name, me))
driveway()
_, hole_cut = floor_holes.cut_visuals([o for o in bpy.context.scene.objects if o.type == 'MESH'], "parking")
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']

def world_box(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))

RAMP_HULLS = ("Broad loading ramp", "Ramp raised shoulder")
IGNORE = ("Ramp yellow warning band", "Truck driveway")
boxes = [(o, *world_box(o)) for o in meshes]
lo_all = Vector((min(b[1].x for b in boxes), min(b[1].y for b in boxes), min(b[1].z for b in boxes)))
hi_all = Vector((max(b[2].x for b in boxes), max(b[2].y for b in boxes), max(b[2].z for b in boxes)))

# --- rasterise ---------------------------------------------------------------
nx = int(math.ceil((hi_all.x - lo_all.x) / CELL)); ny = int(math.ceil((hi_all.y - lo_all.y) / CELL))
block = [[0.0] * ny for _ in range(nx)]   # top height of blockers per cell (0 = free)
floor = [[False] * ny for _ in range(nx)]
def cells(lo, hi):
    i0 = max(0, int((lo.x - lo_all.x) / CELL + 1e-6)); i1 = min(nx - 1, int((hi.x - lo_all.x) / CELL - 1e-6))
    j0 = max(0, int((lo.y - lo_all.y) / CELL + 1e-6)); j1 = min(ny - 1, int((hi.y - lo_all.y) / CELL - 1e-6))
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            yield i, j
for o, lo, hi in boxes:
    if o.name.startswith(RAMP_HULLS + IGNORE): continue
    if hi.z <= 0.06 and hi.z >= -0.1 and (hi.x - lo.x) > 0.3 and (hi.y - lo.y) > 0.3:
        for i, j in cells(lo, hi): floor[i][j] = True
    elif lo.z < BAND[1] and hi.z > BAND[0]:
        for i, j in cells(lo, hi): block[i][j] = max(block[i][j], hi.z)

# threshold plate over the seam with the factory (local x 11.0 .. 11.9)
plate_lo, plate_hi = Vector((11.0, DOOR_Y[0], -0.03)), Vector((11.9, DOOR_Y[1], 0.01))
# and over the wall strip of the truck opening (the courtyard slab starts at x -10.99)
plate2_lo, plate2_hi = Vector((-11.3, TRUCK_OPENING[2], -0.03)), Vector((-10.95, TRUCK_OPENING[3], 0.01))

def rectangles(value):
    """Greedy merge of equal-valued cells into maximal rectangles."""
    used = [[False] * ny for _ in range(nx)]
    out = []
    for i in range(nx):
        for j in range(ny):
            v = value(i, j)
            if not v or used[i][j]: continue
            j2 = j
            while j2 + 1 < ny and not used[i][j2 + 1] and value(i, j2 + 1) == v: j2 += 1
            i2 = i
            while i2 + 1 < nx and all(not used[i2 + 1][k] and value(i2 + 1, k) == v for k in range(j, j2 + 1)): i2 += 1
            for a in range(i, i2 + 1):
                for b in range(j, j2 + 1): used[a][b] = True
            out.append((lo_all.x + i * CELL, lo_all.y + j * CELL, lo_all.x + (i2 + 1) * CELL, lo_all.y + (j2 + 1) * CELL, v))
    return out

# Three height classes (walkable platforms such as the 1.35 m terrace, low walls, tall walls)
# keep the rectangle count small; each rectangle then takes the highest top it covers.
# Platforms need their own class: merged with the railings the terrace floor rose to 1.83 m.
blockers = []
for x0, y0, x1, y1, _ in rectangles(lambda i, j: block[i][j] and (1 if block[i][j] <= 1.4 else 2 if block[i][j] <= 2.0 else 3)):
    # Sample cell centres: the rectangle edges rounded into neighbouring cells (a 1.83 m pier cap
    # lifted the whole terrace box).
    tops = [block[i][j] for i, j in cells(Vector((x0 + CELL / 2, y0 + CELL / 2, 0)), Vector((x1 - CELL / 2, y1 - CELL / 2, 0)))]
    blockers.append((x0, y0, x1, y1, max(tops)))
floors = rectangles(lambda i, j: floor[i][j] and block[i][j] == 0 and 1)

# --- visual mesh ---------------------------------------------------------------
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
visual = bpy.context.view_layer.objects.active
visual.name = NAME; visual.data.name = NAME
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(bpy.context.scene.objects):
    if o is not visual and o.type != 'MESH': bpy.data.objects.remove(o)

steel = bpy.data.materials.get("Steel worn edges")
bm = bmesh.new(); bm.from_mesh(visual.data)
slot = list(visual.data.materials).index(steel) if steel else 0
for p_lo, p_hi in ((plate_lo, plate_hi), (plate2_lo, plate2_hi)):
    plate = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    centre = (p_lo + p_hi) / 2; size = p_hi - p_lo
    for v in plate: v.co = Vector((v.co.x * size.x, v.co.y * size.y, v.co.z * size.z)) + centre
    for f in {f for v in plate for f in v.link_faces}: f.material_index = slot
bm.to_mesh(visual.data); bm.free()

# --- collisions ----------------------------------------------------------------
count = 0
def ucx_box(lo, hi):
    global count
    me = bpy.data.meshes.new(f"UCX_{NAME}_{count:03d}")
    b = bmesh.new(); vs = bmesh.ops.create_cube(b, size=1.0)["verts"]
    c = (lo + hi) / 2; s = hi - lo
    for v in vs: v.co = Vector((v.co.x * s.x, v.co.y * s.y, v.co.z * s.z)) + c
    b.to_mesh(me); b.free()
    bpy.context.scene.collection.objects.link(bpy.data.objects.new(me.name, me)); count += 1
for x0, y0, x1, y1, top in blockers: ucx_box(Vector((x0, y0, 0.0)), Vector((x1, y1, top)))
for x0, y0, x1, y1, _ in floors: ucx_box(Vector((x0, y0, -0.4)), Vector((x1, y1, 0.0)))
ucx_box(plate_lo, plate_hi)
ucx_box(plate2_lo, plate2_hi)
# the truck opening is only for the truck (an animation): an invisible wall keeps the character in
ucx_box(Vector((-11.3, TRUCK_OPENING[2], 0.0)), Vector((-10.7, TRUCK_OPENING[3], TRUCK_OPENING[5])))
# Ramp hulls: re-import the source pieces, which were joined into the visual above.
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith(RAMP_HULLS)]:
    b = bmesh.new(); b.from_mesh(o.data); b.transform(o.matrix_world)
    bmesh.ops.convex_hull(b, input=b.verts)
    me = bpy.data.meshes.new(f"UCX_{NAME}_{count:03d}"); b.to_mesh(me); b.free()
    bpy.context.scene.collection.objects.link(bpy.data.objects.new(me.name, me)); count += 1
for o in list(bpy.context.scene.objects):
    if o is not visual and not o.name.startswith("UCX_"): bpy.data.objects.remove(o)
def _hole_box(lo, hi):
    ucx_box(lo, hi); return bpy.data.objects[f"UCX_{NAME}_{count - 1:03d}"]
_ucx, hole_split = floor_holes.split_collisions(
    [o for o in bpy.context.scene.objects if o.name.startswith("UCX_")], "parking", _hole_box)
count = len(_ucx)

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Parking.blend"))
bpy.ops.export_scene.fbx(filepath=str(OUT / "parking_unreal.fbx"), use_selection=False,
    object_types={'MESH'}, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
    mesh_smooth_type='FACE', path_mode='COPY', embed_textures=True, axis_forward='-Y', axis_up='Z')
report = {"source": str(SOURCE), "pieces_joined": len(meshes), "faces": len(visual.data.polygons),
          "materials": [m.name for m in visual.data.materials], "ucx": count,
          "elevator_hole": {"visual": hole_cut, "collision": hole_split},
          "blocker_boxes": len(blockers), "floor_boxes": len(floors),
          "bounds_m": [list(lo_all), list(hi_all)], "door_y_m": DOOR_Y,
          "placement_unreal_cm": {"location": [-2303, -410, 0], "note": "west of SM_SceneRobot, door to door"}}
(OUT / "parking_build.json").write_text(json.dumps(report, indent=1))
print("### PARKING", json.dumps(report))
