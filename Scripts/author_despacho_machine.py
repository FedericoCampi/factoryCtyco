"""Blender: prepara la maquina de despacho del usuario (3D assets/GLBs/despachoMachine.glb).

Escala a 3 m de ancho (~1,73 m de alto, TecJunior mide 1,70 m), origen al centro del piso
(de la maquina sin alargar),
alarga la cinta de rodillos (EXTEND_M) repitiendo un tramo de rodillos enteros, reduce
~700 000 caras y agrega dos colisiones UCX: cuerpo (alto completo) y cinta (hasta las barandas).
Salida: SourceAssets/DespachoMachine/SM_DespachoMachine.fbx y despacho_build.json.

blender -b --factory-startup -P Scripts/author_despacho_machine.py
"""
import json
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

SRC = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/despachoMachine.glb")
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/DespachoMachine"
NAME = "SM_DespachoMachine"
WIDTH_M, DECIMATE = 3.0, 0.22
EXTEND_M = 2.0  # largo que se agrega a la cinta, en metros finales
# medidas del GLB normalizado (1 m de ancho); la cinta sale hacia -Y
BODY_Y = 0.07             # donde termina la cinta y empieza el cuerpo
TABLE_TOP = 0.256         # arriba de las barandas de la cinta
REPEAT = (-0.26, -0.03)   # tramo uniforme (sin patas) donde buscar el corte entre rodillos
# rodillos de verdad (cilindros con material M_Rodillo, que en Unreal gira) encima de los del modelo,
# que vienen pegados a la malla: se buscan a lo largo de la cinta ya alargada, entre barandas.
ROLLER_HALF_X = 0.305     # medio largo del rodillo (barandas por dentro en |x| 0,31)
ROLLER_Y_MAX = 0.30       # hasta el fondo de la camara
ROLLER_R = 0.0078         # radio (los del modelo miden ~0,007): los tapa sin parpadeo
# mini barrera a los costados y al final de la cinta, estilo de la maquina: postes de acero oscuro y
# pasamanos naranja como las barandas. Medidas en el GLB normalizado (x3 = metros).
RAIL_X = 0.333            # centro de las barandas del modelo
RAIL_TOP = 0.237          # arriba de las barandas
BARRIER_H = 0.06          # alto sobre la baranda (18 cm)
POST, BAR = 0.013, 0.016  # lado del poste y del pasamanos
POST_STEP = 0.15          # un poste cada ~45 cm

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
o = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
bpy.ops.object.select_all(action="DESELECT"); o.select_set(True)
bpy.context.view_layer.objects.active = o
o.parent = None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for extra in [x for x in bpy.context.scene.objects if x is not o]:
    bpy.data.objects.remove(extra)
faces_in = len(o.data.polygons)
xs = [v.co.x for v in o.data.vertices]
scale = WIDTH_M / (max(xs) - min(xs))


def roller_gaps():
    """Huecos entre rodillos: minimos de la altura de la franja central a lo largo de Y."""
    step, lo = 0.001, REPEAT[0]
    top = [0.0] * int((REPEAT[1] - lo) / step)
    for v in o.data.vertices:
        c = v.co
        if abs(c.x) < 0.25 and lo <= c.y < REPEAT[1]:
            i = int((c.y - lo) / step)
            top[i] = max(top[i], c.z)
    cut = (min(top) + max(top)) / 2
    gaps, run = [], []
    for i, z in enumerate(top):
        if z < cut:
            run.append(i)
        elif run:
            gaps.append(lo + (run[0] + run[-1] + 1) / 2 * step); run = []
    return gaps[1:]  # el primero puede estar cortado por el borde


def extend_belt():
    gaps = roller_gaps()
    a, b = gaps[0], gaps[-1]
    length = b - a
    copies = max(1, round(EXTEND_M / scale / length))
    bm = bmesh.new(); bm.from_mesh(o.data)
    for y in (a, b):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, y, 0), plane_no=(0, 1, 0))
    mid = lambda f: f.calc_center_median().y
    front = [f for f in bm.faces if mid(f) < a]
    tramo = [f for f in bm.faces if a <= mid(f) <= b]
    # el frente se separa (copia + borrado) para no estirar el tramo al moverlo
    moved = bmesh.ops.duplicate(bm, geom=front)["geom"]
    bmesh.ops.translate(bm, vec=(0, -copies * length, 0),
                        verts=[g for g in moved if isinstance(g, bmesh.types.BMVert)])
    bmesh.ops.delete(bm, geom=front, context="FACES")
    for i in range(1, copies + 1):
        dup = bmesh.ops.duplicate(bm, geom=tramo)["geom"]
        bmesh.ops.translate(bm, vec=(0, -i * length, 0),
                            verts=[g for g in dup if isinstance(g, bmesh.types.BMVert)])
    seams = [a - i * length for i in range(copies + 1)]  # unir solo las costuras
    bmesh.ops.remove_doubles(bm, dist=1e-5, verts=[
        v for v in bm.verts if any(abs(v.co.y - s) < 1e-4 for s in seams)])
    bm.to_mesh(o.data); bm.free()
    return {"rollers_cut_y": [round(a, 4), round(b, 4)], "copies": copies,
            "added": copies * length, "added_m": round(copies * length * scale, 3)}


belt = extend_belt()


def find_rollers():
    """Centros (y, z) de los rodillos: tramos altos del perfil de la cinta en x = 0 (rayos hacia abajo)."""
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    ys = [v.co.y for v in o.data.vertices]
    step, y = 0.001, min(ys)
    runs, run = [], []
    while y < ROLLER_Y_MAX:
        hit = bvh.ray_cast(Vector((0, y, 1)), Vector((0, 0, -1)))[0]
        if hit is not None and 0.185 < hit.z < 0.21:
            run.append((y, hit.z))
        elif run:
            runs.append(run); run = []
        y += step
    # un rodillo es un tramo de 1-2 cm; los mas anchos son el marco de las puntas
    return [((r[0][0] + r[-1][0]) / 2, max(z for _, z in r) - ROLLER_R) for r in runs if 0.008 <= r[-1][0] - r[0][0] <= 0.02]


def add_rollers(centres):
    mat = bpy.data.materials.new("M_Rodillo")
    o.data.materials.append(mat)
    slot = len(o.data.materials) - 1
    bm = bmesh.new(); bm.from_mesh(o.data)
    uv = bm.loops.layers.uv.active or bm.loops.layers.uv.new()
    sides = 12
    for cy, cz in centres:
        rings = []
        for x in (-ROLLER_HALF_X, ROLLER_HALF_X):
            # U da la vuelta al rodillo (el material la desplaza para que gire), V va a lo largo
            rings.append([bm.verts.new((x, cy + ROLLER_R * math.cos(2 * math.pi * k / sides),
                                        cz + ROLLER_R * math.sin(2 * math.pi * k / sides))) for k in range(sides)])
        for k in range(sides):
            n = (k + 1) % sides
            f = bm.faces.new((rings[0][k], rings[0][n], rings[1][n], rings[1][k]))
            f.material_index = slot
            for loop, (u, v) in zip(f.loops, ((k, 0), (k + 1, 0), (k + 1, 1), (k, 1))):
                loop[uv].uv = (u / sides, v)
        for ring in rings:
            cap = bm.faces.new(ring)
            cap.material_index = slot
            for loop in cap.loops:
                loop[uv].uv = (0.0, 0.0)
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[-(len(centres) * (sides + 2)):])
    bm.to_mesh(o.data); bm.free()


def add_barrier(y_end):
    """Postes + pasamanos sobre las barandas (de la camara al final) y cruzando el final de la cinta."""
    steel = bpy.data.materials.new("M_BarreraAcero")
    steel.diffuse_color = (0.05, 0.05, 0.055, 1)
    orange = bpy.data.materials.new("M_BarreraNaranja")
    orange.diffuse_color = (0.85, 0.28, 0.04, 1)
    for m in (steel, orange):
        m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = m.diffuse_color
        o.data.materials.append(m)
    s_idx, o_idx = len(o.data.materials) - 2, len(o.data.materials) - 1
    bm = bmesh.new(); bm.from_mesh(o.data)
    top = RAIL_TOP + BARRIER_H

    def box(lo, hi, idx):
        vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        c, sz = (Vector(lo) + Vector(hi)) / 2, Vector(hi) - Vector(lo)
        for v in vs:
            v.co = Vector((v.co.x * sz.x, v.co.y * sz.y, v.co.z * sz.z)) + c
        for f in {f for v in vs for f in v.link_faces}:
            f.material_index = idx

    def posts_along(a, b, fixed, axis):
        n = max(1, round(abs(b - a) / POST_STEP))
        for i in range(n + 1):
            t = a + (b - a) * i / n
            c = (fixed, t) if axis == "y" else (t, fixed)
            box((c[0] - POST / 2, c[1] - POST / 2, RAIL_TOP - 0.004), (c[0] + POST / 2, c[1] + POST / 2, top - BAR / 2), s_idx)

    y0, y1 = y_end + POST / 2, BODY_Y
    for side in (-1, 1):
        x = side * RAIL_X
        posts_along(y0, y1, x, "y")
        box((x - BAR / 2, y0 - BAR / 2, top - BAR), (x + BAR / 2, y1, top), o_idx)
    posts_along(-RAIL_X, RAIL_X, y0, "x")
    box((-RAIL_X - BAR / 2, y0 - BAR / 2, top - BAR), (RAIL_X + BAR / 2, y0 + BAR / 2, top), o_idx)
    bm.to_mesh(o.data); bm.free()


rollers = find_rollers()
dec = o.modifiers.new("dec", "DECIMATE"); dec.ratio = DECIMATE
bpy.ops.object.modifier_apply(modifier=dec.name)
add_rollers(rollers)  # despues de reducir: los cilindros quedan limpios
add_barrier(min(v.co.y for v in o.data.vertices))

# escala y origen al centro del piso de la maquina sin alargar (el cuerpo no se mueve al cambiar EXTEND_M)
co = [v.co for v in o.data.vertices]
lo = Vector((min(v.x for v in co), min(v.y for v in co), min(v.z for v in co)))
hi = Vector((max(v.x for v in co), max(v.y for v in co), max(v.z for v in co)))
center_y = (lo.y + belt.pop("added") + hi.y) / 2
to_final = Matrix.Scale(scale, 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -center_y, -lo.z))
o.data.transform(to_final)
size = (hi - lo) * scale


def ucx(index, box_lo, box_hi):
    box_lo, box_hi = to_final @ box_lo, to_final @ box_hi
    me = bpy.data.meshes.new(f"UCX_{NAME}_{index:02d}")
    b = bmesh.new(); verts = bmesh.ops.create_cube(b, size=1.0)["verts"]
    c, s = (box_lo + box_hi) / 2, box_hi - box_lo
    for v in verts:
        v.co = Vector((v.co.x * s.x, v.co.y * s.y, v.co.z * s.z)) + c
    b.to_mesh(me); b.free()
    bpy.context.scene.collection.objects.link(bpy.data.objects.new(me.name, me))


ucx(0, Vector((lo.x, BODY_Y, lo.z)), hi)
ucx(1, lo, Vector((hi.x, BODY_Y, TABLE_TOP)))

o.name = NAME
bpy.ops.object.select_all(action="SELECT")
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                         mesh_smooth_type="FACE", path_mode="COPY", embed_textures=True,
                         axis_forward="-Y", axis_up="Z")
report = {"faces_in": faces_in, "faces": len(o.data.polygons), "scale": round(scale, 4),
          "size_m": [round(d, 3) for d in size], "belt": belt,
          "rollers": len(rollers)}
(OUT / "despacho_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("DESPACHO_OK", report)
