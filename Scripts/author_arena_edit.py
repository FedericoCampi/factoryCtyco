"""Blender: rehace SourceAssets/SceneRobot/scene_unreal.fbx sin las cuatro barreras del centro.

Mismo armado que el generador de image-to-3d (backend/worker/scene/export_unreal_blender.py):
scene.glb unido en LevelGeometry + colisiones UCX de collision.glb + sockets de calibracion,
exportado con axis_forward -Y / axis_up Z. Antes quita (pedido del usuario, 26/09/2026) las
barreras NE/NW/SE/SW que rodean el circulo amarillo, con sus cajas y bidones, y las colisiones
que les correspondian. Desde el 30/09 tambien cierra el vano oeste copiando el tramo de muro vecino; desde el 07/10 cierra
el vano norte, saca sus franjas amarillas y borra las manchitas de desgaste que flotaban donde estaban las barreras. scene.glb y collision.glb no se modifican. Respaldo del FBX anterior en
SourceAssets/SceneRobot/respaldo_2026-09-26. Informe: arena_edit.json.

blender -b --factory-startup -P Scripts/author_arena_edit.py
"""
import json
import sys
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import floor_holes  # noqa: E402  pozo del ascensor (27/09/2026)

folder = Path(__file__).resolve().parent.parent / "SourceAssets/SceneRobot"
QUADRANTS = ("NE ", "NW ", "SE ", "SW ")
DETAILS = ("Cover blue telltale", "Cover face fastener", "Cover small dark service plate")


def box(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def near_centre(lo, hi):
    c = (lo + hi) / 2
    return 1.8 < abs(c.x) < 5.6 and 1.8 < abs(c.y) < 5.6


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.scale_length = 1.0
bpy.ops.import_scene.gltf(filepath=str(folder / "scene.glb"))
removed, areas = [], {}
for o in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
    lo, hi = box(o)
    if near_centre(lo, hi) and o.name.startswith(QUADRANTS + DETAILS):
        key = (lo.x + hi.x > 0, lo.y + hi.y > 0)
        a = areas.get(key)
        areas[key] = (Vector(map(min, a[0], lo)), Vector(map(max, a[1], hi))) if a else (lo.copy(), hi.copy())
        removed.append(o.name)
        bpy.data.objects.remove(o)


# --- vano oeste cerrado (30/09): el tramo de muro entre los contrafuertes de y -7,36 y -3,04 se copia en el hueco
# (-3,04 .. 1,24), con sus detalles; se quitan las franjas amarillas del umbral. Sin lo de los contrafuertes.
WEST_WALL_X = (-11.7, -10.4)
WEST_SEGMENT = (-7.36, -3.04)                 # tramo de muro que se copia
WEST_SHIFT = 1.24 - WEST_SEGMENT[1]           # hasta el contrafuerte del otro lado del vano
BUTTRESS_HALF = 0.47                          # medio ancho de los contrafuertes (sus piezas no se copian)
WEST_SKIP = ("Pipe saddle", "Low wall service conduit", "Deck")   # ni el caño ni los tornillos del piso


def in_west_segment(lo, hi):
    if not (lo.x >= WEST_WALL_X[0] and hi.x <= WEST_WALL_X[1] and lo.z > -0.05):
        return False
    whole = lo.y <= WEST_SEGMENT[0] + 0.05 and hi.y >= WEST_SEGMENT[1] - 0.05          # piezas largas del muro
    inner = lo.y >= WEST_SEGMENT[0] + BUTTRESS_HALF and hi.y <= WEST_SEGMENT[1] - BUTTRESS_HALF + 0.04  # entre contrafuertes
    return whole or inner


west_copies = []
for o in [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.name.startswith(WEST_SKIP)]:
    lo, hi = box(o)
    if in_west_segment(lo, hi):
        c = o.copy()
        c.matrix_world = Matrix.Translation((0, WEST_SHIFT, 0)) @ o.matrix_world
        bpy.context.scene.collection.objects.link(c)
        west_copies.append(c.name)
west_stripes = []
for o in [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name.startswith("Worn diagonal threshold stripe")]:
    lo, hi = box(o)
    if hi.x < -9.0 and -2.6 < lo.y and hi.y < 0.8:
        west_stripes.append(o.name)
        bpy.data.objects.remove(o)
print("WEST_GATE copies", len(west_copies), "stripes", len(west_stripes))


def drop_faces(o, inside):
    """Deletes the faces of o whose centre (world) passes inside(c); returns how many."""
    b = bmesh.new()
    b.from_mesh(o.data)
    m = o.matrix_world
    gone = [f for f in b.faces if inside(m @ f.calc_center_median())]
    bmesh.ops.delete(b, geom=gone, context="FACES")
    b.to_mesh(o.data)
    b.free()
    return len(gone)


# --- (07/10) restos flotando: las mallas de desgaste que cubren toda la arena (oxido, pintura saltada...) seguian
# dibujando sus manchitas donde estaban las cuatro barreras quitadas el 26/09: se borran sus caras dentro de esas zonas
# (por encima del piso; las del piso quedan).
OVERLAYS = ("Armour edge oxidation", "Armour edge paint losses", "Cover chipped orange enamel")
overlay_faces = {}
for o in [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name.startswith(OVERLAYS)]:
    n = drop_faces(o, lambda c: c.z > 0.04 and any(a[0].x - 0.05 <= c.x <= a[1].x + 0.05 and a[0].y - 0.05 <= c.y <= a[1].y + 0.05
                                                   and c.z <= a[1].z + 0.1 for a in areas.values()))
    overlay_faces[o.name] = n
print("OVERLAYS dropped", overlay_faces)

# --- (07/10) vano norte cerrado (detras de la trituradora): entre las jambas (x -2,28 .. 2,28) se copian las piezas
# largas del muro de al lado ("Front fortified wall ...", x -10,77 .. -2,67), estiradas a lo ancho del vano, y dos de
# sus paneles blindados; se quitan las franjas amarillas y la pintura de advertencia del umbral.
NORTH_GAP = (-2.30, 2.30)
NORTH_LONG = ("Front fortified wall", "Front orange belt exposed")
NORTH_PANEL = (-6.61, -4.74)                  # un panel blindado del tramo de al lado (x en Blender)
north_copies = []
for o in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
    lo, hi = box(o)
    if hi.y > -10.0 or lo.z < -0.05:
        continue
    if o.name.startswith(NORTH_LONG) and abs(lo.x + 10.77) < 0.1 and abs(hi.x + 2.67) < 0.1:
        a = (NORTH_GAP[1] - NORTH_GAP[0]) / (hi.x - lo.x)
        c = o.copy()
        c.matrix_world = Matrix.Translation((NORTH_GAP[0] - a * lo.x, 0, 0)) @ Matrix.Scale(a, 4, (1, 0, 0)) @ o.matrix_world
        bpy.context.scene.collection.objects.link(c)
        north_copies.append(c.name)
    elif o.name.startswith("Front individual inset armour panel") and abs(lo.x - NORTH_PANEL[0]) < 0.05 and abs(hi.x - NORTH_PANEL[1]) < 0.05:
        for centre in (-1.12, 1.12):
            c = o.copy()
            c.matrix_world = Matrix.Translation((centre - (lo.x + hi.x) / 2, 0, 0)) @ o.matrix_world
            bpy.context.scene.collection.objects.link(c)
            north_copies.append(c.name)
north_stripes = []
for o in [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name.startswith("Worn diagonal threshold stripe")]:
    lo, hi = box(o)
    if hi.y < -10.0 and -2.4 < lo.x and hi.x < 2.4:
        north_stripes.append(o.name)
        bpy.data.objects.remove(o)
north_paint = sum(drop_faces(o, lambda c: abs(c.x) < 2.6 and c.y < -9.8)
                  for o in bpy.context.scene.objects if o.type == "MESH" and o.name.startswith("Scuffed gateway warning paint"))
print("NORTH_GATE copies", len(north_copies), "stripes", len(north_stripes), "paint faces", north_paint)

visuals = [o for o in bpy.context.scene.objects if o.type == "MESH"]
visuals, hole_cut = floor_holes.cut_visuals(visuals, "arena")
bpy.ops.object.select_all(action="DESELECT")
for o in visuals:
    o.select_set(True)
bpy.context.view_layer.objects.active = visuals[0]
bpy.ops.object.join()
visual = bpy.context.object
visual.name = "LevelGeometry"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(folder / "collision.glb"))
collisions, dropped = [], []
for o in [o for o in bpy.data.objects if o not in before and o.type == "MESH"]:
    lo, hi = box(o)
    c = (lo + hi) / 2
    inside = any(a[0].x - 0.1 <= c.x <= a[1].x + 0.1 and a[0].y - 0.1 <= c.y <= a[1].y + 0.1 and hi.z > 0.2
                 for a in areas.values())
    if inside:
        dropped.append([round(v, 2) for v in (*lo, *hi)])
        bpy.data.objects.remove(o)
    else:
        collisions.append(o)
west_ucx = []
for o in list(collisions):
    lo, hi = box(o)
    if in_west_segment(lo, hi):
        c = o.copy()
        c.data = o.data.copy()
        c.matrix_world = Matrix.Translation((0, WEST_SHIFT, 0)) @ o.matrix_world
        bpy.context.scene.collection.objects.link(c)
        collisions.append(c)
        west_ucx.append(o.name)


def hole_box(lo, hi):
    me = bpy.data.meshes.new("UCX_hole")
    b = bmesh.new()
    for v in bmesh.ops.create_cube(b, size=1.0)["verts"]:
        v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
    b.to_mesh(me)
    b.free()
    o = bpy.data.objects.new(me.name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


# (07/10) el muro nuevo del vano norte choca
collisions.append(hole_box(Vector((NORTH_GAP[0], -11.55, 0.0)), Vector((NORTH_GAP[1], -10.75, 2.2))))
collisions, hole_split = floor_holes.split_collisions(collisions, "arena", hole_box)
for index, o in enumerate(collisions):
    o.name = f"UCX_LevelGeometry_{index:03d}"
    o.hide_set(False)
    o.hide_render = False
sockets = []
for name, point in (("Origin", (0, 0, 0)), ("AxisX", (1, 0, 0)), ("AxisY", (0, 1, 0)), ("AxisZ", (0, 0, 1))):
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=point)
    bpy.context.object.name = f"SOCKET_LevelGeometry_{name}"
    sockets.append(bpy.context.object)
bpy.ops.object.select_all(action="DESELECT")
for o in [visual, *collisions, *sockets]:
    o.select_set(True)
bpy.context.view_layer.objects.active = visual
bpy.ops.export_scene.fbx(filepath=str(folder / "scene_unreal.fbx"), use_selection=True,
    object_types={"MESH", "EMPTY"}, axis_forward="-Y", axis_up="Z", bake_anim=False,
    path_mode="COPY", embed_textures=True, use_mesh_modifiers=True, add_leaf_bones=False)

build = json.loads((folder / "build.json").read_text(encoding="utf-8"))
build["convex_collision_pieces"] = len(collisions)
build["vertex_count"] = len(visual.data.vertices)
(folder / "build.json").write_text(json.dumps(build, indent=1, ensure_ascii=False), encoding="utf-8")
(folder / "arena_edit.json").write_text(json.dumps({
    "removed_pieces": len(removed), "removed_collisions": dropped, "ucx": len(collisions),
    "elevator_hole": {"visual": hole_cut, "collision": hole_split},
    "west_gate_closed": {"copies": len(west_copies), "ucx": west_ucx, "stripes_removed": west_stripes, "shift_m": round(WEST_SHIFT, 3)},
    "north_gate_closed": {"copies": len(north_copies), "stripes_removed": north_stripes, "paint_faces_removed": north_paint},
    "overlay_faces_removed": overlay_faces,
    "areas_m": [[round(v, 2) for v in (*a[0], *a[1])] for a in areas.values()],
}, indent=1), encoding="utf-8")
print("ARENA_OK", len(removed), len(dropped), len(collisions))
