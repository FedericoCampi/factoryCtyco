"""Blender: escena de muelles de carga del usuario (3D assets/GLBs/scenes/Muelles de carga en patio industrial-complete.glb)
para Unreal (03/10).

El GLB ya viene en metros (49 x 46 m, muelle a 1,2 m, techo a 5 m) y liviano (~9 300 triangulos, 12 materiales con
texturas chicas): se une en una sola malla, sin reducir. El edificio del muelle queda hacia -Y en Unreal (+Y en el
GLB) y el patio con sus tres cajones hacia +Y. Origen del GLB (centro, piso del patio en z 0). Choca con su propia
malla (complex as simple), asi se camina el muelle, las escaleras y el patio.
Salida: SourceAssets/Muelles/SM_Muelles.fbx, SM_PortonMuelle.fbx (portones, 04/10) y muelles_build.json.

blender -b --factory-startup -P Scripts/author_muelles.py
"""
import json
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

SRC = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/scenes/Muelles de carga en patio industrial-complete.glb")
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Muelles"
NAME = "SM_Muelles"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))

# Requested 2026-10-03: the building's back wall (against the parking in Unreal) goes, so the parking walks straight
# into the dock building: the brick parapet and its cap, the vent grilles, the downpipes with their brackets and shoes,
# and the parapet columns and lamps on it. The building block (Dock core) loses its back face and gets its faces
# doubled facing in, so its inside (walls and the roof slab above) can be seen.
BACK = ("Back brick parapet", "Back parapet cap", "Back vent grille", "Downpipe", "Parapet column", "Parapet light")
back = [o.name for o in bpy.context.scene.objects if o.type == "MESH" and o.name.startswith(BACK)]
for name in back:
    bpy.data.objects.remove(bpy.data.objects[name])
core = bpy.data.objects["Dock core"]
core.data = core.data.copy()
b = bmesh.new()
b.from_mesh(core.data)
b.transform(core.matrix_world)
y_back = max(v.co.y for v in b.verts)
bmesh.ops.delete(b, geom=[f for f in b.faces if f.normal.y > 0.9 and abs(f.calc_center_median().y - y_back) < 1e-3], context="FACES")
inside = bmesh.ops.duplicate(b, geom=b.faces[:])["geom"]
bmesh.ops.reverse_faces(b, faces=[g for g in inside if isinstance(g, bmesh.types.BMFace)])
b.transform(core.matrix_world.inverted())
b.to_mesh(core.data)
b.free()
print("BACK_WALL removed", len(back), "pieces; core opened at y", round(y_back, 2))

# Requested 2026-10-03: truck openings in the yard walls where the trucks' line crosses them, written by
# apply_muelles_conexion.py (SourceAssets/Muelles/truck_openings.json: wall Left/Right/Front, centre along it and half
# width, in GLB metres). Every wall piece on that wall (brick, coping, footing, pilasters and their caps) loses what
# lies within the opening; the yard slab and the foundation stay.
WALL_PIECES = ("Brick panel", "Wall coping", "Wall footing", "Wall pilaster", "Pilaster cap")
openings_file = OUT / "truck_openings.json"
openings = json.loads(openings_file.read_text(encoding="utf-8")) if openings_file.exists() else []
cut_report = []
for opening in openings:
    wall, centre, half = opening["wall"], opening["at"], opening["half"]
    along = 1 if wall in ("Left", "Right") else 0     # the wall runs along y (sides) or x (front)
    lo, hi = centre - half, centre + half
    on_wall = {"Left": lambda p: p.x < -23.3, "Right": lambda p: p.x > 23.3, "Front": lambda p: p.y < -21.3}[wall]
    touched = 0
    for o in [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name.startswith(WALL_PIECES)]:
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        if not any(on_wall(p) for p in pts) or max(p[along] for p in pts) <= lo or min(p[along] for p in pts) >= hi:
            continue
        o.data = o.data.copy()
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.transform(o.matrix_world)
        for value in (lo, hi):
            co, no = Vector((0, 0, 0)), Vector((0, 0, 0))
            co[along], no[along] = value, 1.0
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
        inner = [f for f in bm.faces if lo < f.calc_center_median()[along] < hi and on_wall(f.calc_center_median())]
        bmesh.ops.delete(bm, geom=inner, context="FACES")
        bm.transform(o.matrix_world.inverted())
        bm.to_mesh(o.data)
        bm.free()
        if not o.data.polygons:
            bpy.data.objects.remove(o)
        touched += 1
    cut_report.append({"wall": wall, "at": centre, "half": half, "pieces": touched})
print("TRUCK_OPENINGS", cut_report)

# Requested 2026-10-04 (east) and 2026-10-05 (west, mirrored): each man door on the dock platform (at 1.18 m, beside the
# end bays) opens into an L-shaped passage through its brick wing, which was solid: leg 1 goes in from the door and
# ramps down to the building floor; leg 2 turns towards the building and comes out of the wing's inner face, inside the
# building, beside and behind the end bay's sectional door. Each door's solid "frame" slab goes and a real frame (two
# jambs and a lintel) lines the doorway; the leaf and its handle leave this mesh: they are exported once as
# SM_MuellePuertaPersonal (origin at the hinge) and stand in Unreal as doors that open by themselves (AFactoryAutoDoor,
# apply_muelles_puertas.py). The way out of each leg 2 gets a steel frame and, above it, a "MUELLE DE CAMIONES" sign.
# GLB metres (in Unreal the docks are at 0.75 in X and Y: 1.6 m wide here is 1.2 m there).
PASSAGE_RAMP_Y = (13.6, 17.0)   # leg 1: from the door (y 13.8) in, floor from DOOR_SILL down to 0
PASSAGE_LEG2_Y = (17.0, 18.6)   # leg 2: across to the wing's inner face and through the core's wall
DOOR_SILL, DOOR_TOP, LEG2_TOP = 1.18, 3.48, 2.5
# per side: door index, wing, its base course, leg 1 across x, the wing's inner face x and which way the building is
PASSAGES = (
    dict(door=1, wing="Right brick wing", base="Right wing base course", x=(11.4, 13.0), inner=10.0, toward=-1),
    dict(door=0, wing="Left brick wing", base="Left wing base course", x=(-20.1, -18.5), inner=-17.5, toward=1),
)
steel = bpy.data.objects["Man door frame 0"].data.materials[0]
leaf_src = bpy.data.objects["Man door leaf 0"]
door_info = {}


def cutter(name, lo, hi, ramp=None, material=None):
    """A box from lo to hi; ramp=(y0, z0, y1, z1) slopes its bottom along y (the floor it leaves)."""
    me = bpy.data.meshes.new(name)
    b = bmesh.new()
    uv = b.loops.layers.uv.new("UVMap")
    vs = bmesh.ops.create_cube(b, size=1.0)["verts"]
    lo, hi = Vector(lo), Vector(hi)
    for v in vs:
        bottom = v.co.z < 0
        v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
        if ramp and bottom:
            y0, z0, y1, z1 = ramp
            v.co.z = z0 + (z1 - z0) * (v.co.y - y0) / (y1 - y0)
    for f in b.faces:   # brick-sized UVs on the new walls
        for loop in f.loops:
            c = loop.vert.co
            loop[uv].uv = (c.x / 2, c.y / 2) if abs(f.normal.z) > 0.5 else ((c.x + c.y) / 2, c.z / 2)
    b.to_mesh(me)
    b.free()
    if material:
        me.materials.append(material)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


# the door leaf (with its handle) as its own mesh: hinge on the edge away from the handle, the leaf running towards
# local -X from it (AFactoryAutoDoor), so it is turned 180 degrees here and stands turned back in Unreal
leaf = leaf_src.copy()
leaf.data = leaf_src.data.copy()
bpy.context.scene.collection.objects.link(leaf)
handle = bpy.data.objects["Man door handle 0"].copy()
handle.data = bpy.data.objects["Man door handle 0"].data.copy()
bpy.context.scene.collection.objects.link(handle)
bpy.ops.object.select_all(action="DESELECT")
for o in (leaf, handle):
    o.parent = None
    o.select_set(True)
bpy.context.view_layer.objects.active = leaf
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.join()
corners = [leaf_src.matrix_world @ Vector(c) for c in leaf_src.bound_box]   # in the world (the GLB nests them)
hinge0 = Vector((min(c.x for c in corners), sum(c.y for c in corners) / 8, min(c.z for c in corners)))
leaf.data.transform(Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Translation(-hinge0))
leaf.name = leaf.data.name = "SM_MuellePuertaPersonal"
bpy.ops.object.select_all(action="DESELECT")
leaf.select_set(True)
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(OUT / "SM_MuellePuertaPersonal.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         path_mode="COPY", embed_textures=False, axis_forward="-Y", axis_up="Z")
leaf_width = max(c.x for c in corners) - min(c.x for c in corners)
bpy.data.objects.remove(leaf)

# the sign: a dark plate with white letters, facing +Y here (turned to face into the building where it hangs)
sign_plate = bpy.data.materials.new("M_CartelMuelle")
sign_plate.use_nodes = True
sign_plate.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.05, 0.12, 1)
sign_ink = bpy.data.materials.new("M_CartelMuelleLetras")
sign_ink.use_nodes = True
sign_ink.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.9, 0.9, 0.85, 1)
SIGN_W, SIGN_H = 1.9, 0.38


def sign(name, center, toward):
    plate = cutter(name, (-SIGN_W / 2, -0.02, -SIGN_H / 2), (SIGN_W / 2, 0.0, SIGN_H / 2), material=sign_plate)
    plate.data.materials.clear()
    plate.data.materials.append(sign_plate)
    bpy.ops.object.text_add(location=(0, 0, 0))
    text = bpy.context.active_object
    text.data.body = "MUELLE DE CAMIONES"
    text.data.align_x, text.data.align_y = "CENTER", "CENTER"
    text.data.size = 0.16
    text.data.extrude = 0.004
    bpy.ops.object.convert(target="MESH")
    text = bpy.context.active_object
    text.data.materials.clear()
    text.data.materials.append(sign_ink)
    text.rotation_euler = (math.pi / 2, 0, math.pi)   # standing, reading from +Y
    text.location = (0, 0.004, 0)
    bpy.ops.object.select_all(action="DESELECT")
    text.select_set(True)
    plate.select_set(True)
    bpy.context.view_layer.objects.active = plate
    bpy.ops.object.join()
    # facing +Y; turn so it faces the building (toward: -1 is -X, +1 is +X)
    plate.matrix_world = Matrix.Translation(center) @ Matrix.Rotation(-toward * math.pi / 2, 4, "Z")
    return plate


for p in PASSAGES:
    i, (x0, x1), inner, toward = p["door"], p["x"], p["inner"], p["toward"]
    leaf_o = bpy.data.objects[f"Man door leaf {i}"]
    lc = [leaf_o.matrix_world @ Vector(c) for c in leaf_o.bound_box]
    hinge = Vector((min(c.x for c in lc), sum(c.y for c in lc) / 8, min(c.z for c in lc)))
    door_info[i] = {"hinge_m": [round(hinge.x, 3), round(hinge.y, 3), round(hinge.z, 3)], "width_m": round(leaf_width, 3),
                   "opening_m": [x0, x1, DOOR_SILL, DOOR_TOP]}   # the doorway inside the frame: the leaf fills it in Unreal
    for name in (f"Man door leaf {i}", f"Man door handle {i}", f"Man door frame {i}"):
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name])
    wing = bpy.data.objects[p["wing"]]
    brick = wing.data.materials[0] if wing.data.materials else None
    far = x1 if toward < 0 else x0          # leg 1's side away from the building
    leg1 = cutter(f"Passage {i} leg 1", (x0, PASSAGE_RAMP_Y[0], -1.0), (x1, PASSAGE_RAMP_Y[1], DOOR_TOP),
                  ramp=(PASSAGE_RAMP_Y[0], DOOR_SILL, PASSAGE_RAMP_Y[1], 0.0), material=brick)
    # leg 2 runs from leg 1's far side through the wing's inner face, 10 cm into the building
    leg2 = cutter(f"Passage {i} leg 2", (min(far, inner + toward * 0.1), PASSAGE_LEG2_Y[0], 0.0),
                  (max(far, inner + toward * 0.1), PASSAGE_LEG2_Y[1], LEG2_TOP), material=brick)
    for target in (wing, bpy.data.objects[p["base"]]):
        bpy.context.view_layer.objects.active = target
        for c in (leg1, leg2):
            mod = target.modifiers.new(f"Cut {c.name}", "BOOLEAN")
            mod.operation, mod.solver, mod.object = "DIFFERENCE", "EXACT", c
            mod.material_mode = "TRANSFER"
            bpy.ops.object.modifier_apply(modifier=mod.name)
    for c in (leg1, leg2):
        bpy.data.objects.remove(c)
    # the doorway's frame: two jambs and a lintel
    for k, (lo, hi) in enumerate((((x0 - 0.1, 13.70, DOOR_SILL), (x0, 13.82, DOOR_TOP + 0.1)),
                                  ((x1, 13.70, DOOR_SILL), (x1 + 0.1, 13.82, DOOR_TOP + 0.1)),
                                  ((x0 - 0.1, 13.70, DOOR_TOP), (x1 + 0.1, 13.82, DOOR_TOP + 0.1)))):
        cutter(f"Man door frame {i} piece {k}", lo, hi, material=steel)
    # the way out on the building side: a steel frame on the wing's inner face, and the sign above it
    face0, face1 = sorted((inner, inner + toward * 0.1))
    y0, y1 = PASSAGE_LEG2_Y
    for k, (lo, hi) in enumerate((((face0, y0 - 0.1, 0.0), (face1, y0, LEG2_TOP + 0.1)),
                                  ((face0, y1, 0.0), (face1, y1 + 0.1, LEG2_TOP + 0.1)),
                                  ((face0, y0 - 0.1, LEG2_TOP), (face1, y1 + 0.1, LEG2_TOP + 0.1)))):
        cutter(f"Passage {i} exit frame {k}", lo, hi, material=steel)
    sign(f"Passage {i} sign", Vector((inner + toward * 0.03, (y0 + y1) / 2, LEG2_TOP + 0.45)), toward)
    # the building's (double-sided) wall on that side sits inside the wing: open it where leg 2 comes out
    b = bmesh.new()
    b.from_mesh(core.data)
    b.transform(core.matrix_world)
    x_wall = max(v.co.x for v in b.verts) if toward < 0 else min(v.co.x for v in b.verts)
    for value in PASSAGE_LEG2_Y:
        bmesh.ops.bisect_plane(b, geom=b.verts[:] + b.edges[:] + b.faces[:], plane_co=(0, value, 0), plane_no=(0, 1, 0))
    bmesh.ops.bisect_plane(b, geom=b.verts[:] + b.edges[:] + b.faces[:], plane_co=(0, 0, LEG2_TOP), plane_no=(0, 0, 1))
    opened = [f for f in b.faces if abs(f.calc_center_median().x - x_wall) < 1e-3
              and PASSAGE_LEG2_Y[0] < f.calc_center_median().y < PASSAGE_LEG2_Y[1] and f.calc_center_median().z < LEG2_TOP]
    bmesh.ops.delete(b, geom=opened, context="FACES")
    b.transform(core.matrix_world.inverted())
    b.to_mesh(core.data)
    b.free()
    door_info[i]["core_faces_opened"] = len(opened)
print("PASSAGES", door_info)
# Requested 2026-10-04: the three sectional doors open: in Unreal each one (Porton_Muelle_N) rolls up into its top edge
# while a truck is parked in its bay (AFactoryTruckBay). The doors and their bottom seals leave the building mesh; door 0
# with its seal is exported as SM_PortonMuelle (all three are the same), origin at the middle of its top edge, and the
# places of the three go in the report. The building block's front face (and its inside copy) opens behind each door.
DOOR_INSET = 0.02     # the opening is a little inside the door, so the closed door covers its edges
doors = []
for i in range(3):
    leaf, seal = bpy.data.objects[f"Sectional door {i}"], bpy.data.objects[f"Door bottom seal {i}"]
    corners = [leaf.matrix_world @ Vector(c) for c in leaf.bound_box]
    lo_d = Vector([min(c[k] for c in corners) for k in range(3)])
    hi_d = Vector([max(c[k] for c in corners) for k in range(3)])
    doors.append({"leaf": leaf, "seal": seal, "lo": lo_d, "hi": hi_d,
                  "top": Vector(((lo_d.x + hi_d.x) / 2, (lo_d.y + hi_d.y) / 2, hi_d.z))})
b = bmesh.new()
b.from_mesh(core.data)
b.transform(core.matrix_world)
y_front = min(v.co.y for v in b.verts)
for d in doors:
    for x in (d["lo"].x + DOOR_INSET, d["hi"].x - DOOR_INSET):
        bmesh.ops.bisect_plane(b, geom=b.verts[:] + b.edges[:] + b.faces[:], plane_co=(x, 0, 0), plane_no=(1, 0, 0))
for z in (doors[0]["lo"].z + DOOR_INSET, doors[0]["hi"].z - DOOR_INSET):
    bmesh.ops.bisect_plane(b, geom=b.verts[:] + b.edges[:] + b.faces[:], plane_co=(0, 0, z), plane_no=(0, 0, 1))
holes = []
for f in b.faces:
    c = f.calc_center_median()
    if abs(c.y - y_front) < 1e-3 and any(d["lo"].x < c.x < d["hi"].x and d["lo"].z < c.z < d["hi"].z for d in doors):
        holes.append(f)
bmesh.ops.delete(b, geom=holes, context="FACES")
b.transform(core.matrix_world.inverted())
b.to_mesh(core.data)
b.free()
# door 0 and its seal: one mesh, origin at the top edge's middle
first = doors[0]
bpy.ops.object.select_all(action="DESELECT")
for o in (first["leaf"], first["seal"]):
    o.data = o.data.copy()
    o.parent = None
    o.select_set(True)
bpy.context.view_layer.objects.active = first["leaf"]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.join()
porton = bpy.context.view_layer.objects.active
porton.data.transform(Matrix.Translation(-first["top"]))
porton.name = porton.data.name = "SM_PortonMuelle"
OUT.mkdir(parents=True, exist_ok=True)
# with its textures: the door's material (Sectional door) is not in SM_Muelles any more, Unreal makes it from here
bpy.ops.export_scene.fbx(filepath=str(OUT / "SM_PortonMuelle.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         path_mode="COPY", embed_textures=True, axis_forward="-Y", axis_up="Z")
door_report = [{"top_m": [round(d["top"][k], 3) for k in range(3)], "size_m": [round(d["hi"][k] - d["lo"][k], 3) for k in range(3)]}
               for d in doors]
for d in doors[1:]:
    bpy.data.objects.remove(d["leaf"])
    bpy.data.objects.remove(d["seal"])
bpy.data.objects.remove(porton)
print("DOORS cut", len(holes), "faces; doors", door_report)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
o = bpy.context.view_layer.objects.active
o.parent = None
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
report = {"source": str(SRC), "pieces_joined": len(meshes), "size_m": [round(hi[i] - lo[i], 2) for i in range(3)],
          "min_m": [round(x, 2) for x in lo], "max_m": [round(x, 2) for x in hi],
          "triangles": sum(len(p.vertices) - 2 for p in o.data.polygons),
          "materials": [m.name for m in o.data.materials if m], "collision": "complex", "truck_openings": cut_report,
          "doors": door_report, "man_doors": door_info}
(OUT / "muelles_build.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
print("MUELLES_OK", json.dumps(report))
