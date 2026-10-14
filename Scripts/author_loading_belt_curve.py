"""Blender: cinta de despacho curva (04/10), como SM_CintaCarga pero en un cuarto de circulo.

SM_CintaCargaCurva: la misma cinta de rodillos de SM_CintaCarga (author_loading_belt.py: 0,8 m de ancho, rodillos
arriba a 0,88 m, largueros de acero, barandas naranjas, patas con travesano y pie), doblada 90 grados con el radio de
SM_CintaEsquina (1,538 m en el eje, 241,7 cm de largo): reemplaza a la esquina negra sin mover las cintas. Los rodillos
van radiales, separados como en la recta (11 cm en el eje), en la ranura M_Rodillo (giran en Unreal con
M_DespachoRodillo). Sin la bandeja amarilla de la punta de carga (la curva va entre dos cintas).
Para AFactoryLoadingBelt con TurnDegrees -90 y Length 241,7: entra en el origen mirando a +X y dobla hacia -Y en
Unreal (+Y en Blender). Espejada (escala Y -1) dobla al otro lado. Colision: 8 cajas UCX a lo largo de la curva.
Salida: SourceAssets/CintaCargaCurva/SM_CintaCargaCurva.fbx y cinta_curva_build.json.

blender -b --factory-startup -P Scripts/author_loading_belt_curve.py
"""
import json
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/CintaCargaCurva"
NAME = "SM_CintaCargaCurva"
WIDTH, DECK = 0.8, 0.88
ROLLER_R, ROLLER_STEP = 0.035, 0.11
RADIUS, TURN = 1.538, math.pi / 2       # como SM_CintaEsquina (cinta_esquina_build.json)
ARC = RADIUS * TURN
SEG_DEG = 3.0                           # largueros y barandas: un tramo cada 3 grados
UCX_PIECES = 8

bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, rough=0.5, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


steel = mat("M_CintaAcero", (0.07, 0.08, 0.1), 0.45, 0.8)
orange = mat("M_CintaNaranja", (0.85, 0.32, 0.04))
roller = mat("M_Rodillo", (0.5, 0.5, 0.52), 0.35, 0.85)
mats = [steel, orange, roller]

me = bpy.data.meshes.new(NAME)
bm = bmesh.new()
bm.loops.layers.uv.new("UVMap")


def at(d, angle):
    """Punto del plano a `d` del eje hacia adentro de la curva (+Y en la entrada), a `angle` desde la entrada.
    El centro de la curva esta en (0, RADIUS)."""
    r = RADIUS - d
    return Vector((r * math.sin(angle), RADIUS - r * math.cos(angle), 0))


def placed(made_verts, angle, d, z, material):
    """Pieza armada en su lugar (eje local X a lo largo de la curva, Y hacia adentro), en el angulo dado."""
    m = Matrix.Translation(at(d, angle) + Vector((0, 0, z))) @ Matrix.Rotation(angle, 4, "Z")
    for v in made_verts:
        v.co = m @ v.co
    for f in {f for v in made_verts for f in v.link_faces}:
        f.material_index = mats.index(material)


def block(angle, d, z, size, material):
    """Caja de tamano size (largo, ancho, alto) centrada en (d, z) del perfil, a `angle`."""
    vs = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)["verts"]
    for v in vs:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    placed(vs, angle, d, z, material)


def sweep(d0, d1, z0, z1, material):
    """Perfil rectangular (d0..d1, z0..z1) barrido a lo largo de toda la curva: un tubo cerrado."""
    n = max(1, round(math.degrees(TURN) / SEG_DEG))
    rings = []
    for i in range(n + 1):
        a = TURN * i / n
        ring = []
        for d, z in ((d0, z0), (d1, z0), (d1, z1), (d0, z1)):
            ring.append(bm.verts.new(at(d, a) + Vector((0, 0, z))))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(4):
            faces.append(bm.faces.new((r0[k], r0[(k + 1) % 4], r1[(k + 1) % 4], r1[k])))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[-1]))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.material_index = mats.index(material)


w = WIDTH / 2
top = DECK - ROLLER_R
# largueros y barandas, a los dos lados
for side in (-1, 1):
    d0, d1 = sorted((side * (w - 0.05), side * w))
    sweep(d0, d1, top - 0.14, top + 0.02, steel)
    sweep(d0, d1, DECK + 0.03, DECK + 0.07, orange)
    for frac in (0.02, 0.5, 0.97):                                    # postes de la baranda
        block(TURN * frac, (d0 + d1) / 2, (top + DECK + 0.03) / 2, (0.03, d1 - d0, DECK + 0.03 - top), steel)
# patas (en el borde de adentro y el de afuera), travesano y pie, cerca de cada punta y en el medio
for frac in (0.06, 0.5, 0.94):
    a = TURN * frac
    for side in (-1, 1):
        block(a, side * (w - 0.1), (top - 0.14) / 2, (0.06, 0.06, top - 0.14), steel)
    block(a, 0, 0.145, (0.06, WIDTH - 0.2, 0.05), steel)
    block(a, 0, 0.01, (0.14, WIDTH - 0.1, 0.02), steel)
# rodillos radiales, separados ROLLER_STEP sobre el eje, con UV alrededor del tubo (el material franjea U)
n = int((ARC - 0.06) / ROLLER_STEP)
for i in range(n + 1):
    a = (0.04 + i * (ARC - 0.08) / n) / RADIUS
    made = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=ROLLER_R, radius2=ROLLER_R,
                                 depth=WIDTH - 0.1, calc_uvs=True, matrix=Matrix.Rotation(math.pi / 2, 4, "X"))
    placed(made["verts"], a, 0, top, roller)
bm.to_mesh(me)
bm.free()
for m in mats:
    me.materials.append(m)
obj = bpy.data.objects.new(NAME, me)
bpy.context.scene.collection.objects.link(obj)

# colision: cajas a lo largo de la curva, del piso a las barandas
ucx = []
for i in range(UCX_PIECES):
    a0, a1 = TURN * i / UCX_PIECES, TURN * (i + 1) / UCX_PIECES
    corners = [at(d, a) for a in (a0, a1) for d in (-w, w)]
    cm = bpy.data.meshes.new(f"UCX_{NAME}_{i:02d}")
    b = bmesh.new()
    vs = [b.verts.new((c.x, c.y, z)) for z in (0.0, DECK + 0.07) for c in corners]
    bmesh.ops.convex_hull(b, input=vs)
    b.to_mesh(cm)
    b.free()
    u = bpy.data.objects.new(cm.name, cm)
    bpy.context.scene.collection.objects.link(u)
    ucx.append(u)

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
for x in [obj, *ucx]:
    x.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         axis_forward="-Y", axis_up="Z")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "CintaCargaCurva.blend"))
exit_ = at(0, TURN)
report = {"width_m": WIDTH, "deck_m": DECK, "radius_m": RADIUS, "length_cm": round(ARC * 100, 1),
          "turn_degrees_unreal": -90, "exit_unreal_cm": [round(exit_.x * 100, 1), round(-exit_.y * 100, 1)],
          "rollers": n + 1, "faces": len(me.polygons), "ucx": UCX_PIECES, "materials": [m.name for m in mats]}
(OUT / "cinta_curva_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("CURVA_OK", json.dumps(report))
