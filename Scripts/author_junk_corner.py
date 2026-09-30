"""Blender: rincon de deposito donde estaba la cinta de despacho 1 (28/09).

Piezas (FBX en SourceAssets/Rincon, metros; origen al centro de la base; +X de Blender = +X de Unreal):
- SM_Volquete: contenedor de basura verde (2,2 x 1,4 x 1,25 m) con una tapa abierta y basura asomando
  (bolsas, papeles, una caja rota). UCX: el cuerpo.
- SM_PalletCajas: pallet de madera con cajas de carton apiladas desparejas. UCX: el conjunto.
- SM_BolsasBasura: tres bolsas negras con nudo. Sin colision.
- SM_TablonesAbertura: tablones que tapan la abertura del muro (3,4 x 2,5 m) con dos travesanos en cruz; mira a +X.
  UCX: una placa (el personaje no sale por ahi).

blender -b --factory-startup -P Scripts/author_junk_corner.py
"""
import json
import math
import random
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Rincon"
random.seed(7)
bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, rough=0.7, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


M = {
    "verde": mat("M_VolqueteVerde", (0.10, 0.30, 0.16), 0.55, 0.3),
    "verde_osc": mat("M_VolqueteVerdeOscuro", (0.05, 0.16, 0.09), 0.6, 0.3),
    "negro": mat("M_TapaNegra", (0.03, 0.03, 0.035), 0.5),
    "bolsa": mat("M_BolsaBasura", (0.02, 0.02, 0.025), 0.25),
    "papel": mat("M_Papel", (0.85, 0.83, 0.75), 0.9),
    "carton": mat("M_CajaCarton", (0.78, 0.60, 0.38), 0.85),
    "cinta": mat("M_CintaEmbalar", (0.91, 0.79, 0.56), 0.5),
    "madera": mat("M_MaderaPallet", (0.55, 0.40, 0.24), 0.9),
    "madera_osc": mat("M_MaderaTablon", (0.42, 0.29, 0.17), 0.9),
    "clavo": mat("M_Clavo", (0.25, 0.25, 0.27), 0.4, 0.8),
    "amarillo": mat("M_AvisoAmarillo", (0.85, 0.62, 0.04), 0.5),
}


class Piece:
    def __init__(self, name):
        self.name, self.bm, self.mats, self.ucx = name, bmesh.new(), [], []
        self.bm.loops.layers.uv.new("UVMap")

    def _mat(self, faces, material):
        if material not in self.mats:
            self.mats.append(material)
        for f in faces:
            f.material_index = self.mats.index(material)

    def box(self, lo, hi, material, rot=None, pivot=None, bevel=0.0):
        lo, hi = Vector(lo), Vector(hi)
        vs = bmesh.ops.create_cube(self.bm, size=1.0, calc_uvs=True)["verts"]
        for v in vs:
            v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
        if rot is not None:
            p = Vector(pivot) if pivot is not None else (lo + hi) / 2
            for v in vs:
                v.co = p + rot @ (v.co - p)
        faces = list({f for v in vs for f in v.link_faces})
        if bevel:
            bmesh.ops.bevel(self.bm, geom=list({e for f in faces for e in f.edges}), offset=bevel, segments=1, affect="EDGES")
            faces = list({f for v in vs if v.is_valid for f in v.link_faces})
        self._mat(faces, material)

    def blob(self, centre, size, material, squash=1.0):
        made = bmesh.ops.create_uvsphere(self.bm, u_segments=10, v_segments=7, radius=1.0, calc_uvs=True)
        for v in made["verts"]:
            n = v.co.copy()
            wobble = 1.0 + 0.12 * math.sin(n.x * 5 + n.y * 3) + 0.08 * math.cos(n.z * 7)
            v.co = Vector((n.x * size.x, n.y * size.y, n.z * size.z * squash)) * wobble + Vector(centre)
        self._mat(list({f for v in made["verts"] for f in v.link_faces}), material)

    def build(self):
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me); self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        o = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(o)
        objs = [o]
        for i, (lo, hi) in enumerate(self.ucx):
            cm = bpy.data.meshes.new(f"UCX_{self.name}_{i:02d}")
            b = bmesh.new(); vs = bmesh.ops.create_cube(b, size=1.0)["verts"]
            for v in vs:
                v.co = Vector((v.co.x * (hi[0] - lo[0]), v.co.y * (hi[1] - lo[1]), v.co.z * (hi[2] - lo[2]))) + (Vector(lo) + Vector(hi)) / 2
            b.to_mesh(cm); b.free()
            c = bpy.data.objects.new(cm.name, cm); bpy.context.scene.collection.objects.link(c)
            objs.append(c)
        return objs


def bag(p, centre, scale=1.0):
    p.blob(centre, Vector((0.32, 0.28, 0.3)) * scale, M["bolsa"], 0.9)
    top = Vector(centre) + Vector((0, 0, 0.3 * scale * 0.95))
    p.blob(top, Vector((0.07, 0.07, 0.06)) * scale, M["bolsa"])                      # nudo
    p.blob(top + Vector((0.05, 0, 0.06)) * scale, Vector((0.05, 0.03, 0.06)) * scale, M["bolsa"])


def cardboard(p, lo, hi, rot_deg=0.0):
    lo, hi = Vector(lo), Vector(hi)
    rot = Matrix.Rotation(math.radians(rot_deg), 3, "Z")
    p.box(lo, hi, M["carton"], rot, bevel=0.01)
    cx = (lo.x + hi.x) / 2
    p.box((cx - 0.03, lo.y - 0.002, hi.z - 0.002), (cx + 0.03, hi.y + 0.002, hi.z + 0.003), M["cinta"], rot, pivot=(lo + hi) / 2)


# --- volquete -----------------------------------------------------------------------------------------
vol = Piece("SM_Volquete")
L, W, H = 1.4, 2.2, 1.1          # X (fondo), Y (largo), alto del cuerpo
vol.box((-L / 2 + 0.05, -W / 2 + 0.05, 0.12), (L / 2 - 0.05, W / 2 - 0.05, H), M["verde"], bevel=0.03)
vol.box((-L / 2, -W / 2, H - 0.08), (L / 2, W / 2, H + 0.02), M["verde_osc"], bevel=0.015)          # borde
for x in (-L / 2 + 0.15, L / 2 - 0.15):                                                            # patas/ruedas
    for y in (-W / 2 + 0.2, W / 2 - 0.2):
        vol.box((x - 0.07, y - 0.07, 0.0), (x + 0.07, y + 0.07, 0.14), M["negro"], bevel=0.02)
for y in (-W / 2 + 0.03, W / 2 - 0.03):                                                            # refuerzos
    vol.box((-L / 2 - 0.02, y - 0.04, 0.2), (L / 2 + 0.02, y + 0.04, H - 0.1), M["verde_osc"])
vol.box((L / 2 - 0.02, -0.5, 0.55), (L / 2 + 0.01, 0.5, 0.75), M["amarillo"])                       # franja al frente
# tapas: una cerrada (mitad -Y) y una abierta, levantada hacia atras
vol.box((-L / 2 - 0.03, -W / 2, H + 0.02), (L / 2 + 0.03, 0.0, H + 0.08), M["negro"], bevel=0.015)
open_rot = Matrix.Rotation(math.radians(-70), 3, "Y")
vol.box((-L / 2 - 0.03, 0.02, H + 0.02), (L / 2 + 0.03, W / 2, H + 0.08), M["negro"], open_rot, pivot=(-L / 2, 0, H + 0.05), bevel=0.015)
# basura asomando por la mitad abierta
for c, s in (((0.1, 0.45, H + 0.05), 1.0), ((-0.3, 0.75, H + 0.0), 0.9), ((0.35, 0.8, H - 0.05), 0.8)):
    bag(vol, c, s)
for i in range(6):
    x, y = random.uniform(-0.5, 0.5), random.uniform(0.15, 1.0)
    vol.box((x - 0.12, y - 0.09, H + 0.02), (x + 0.12, y + 0.09, H + 0.035), M["papel"], Matrix.Rotation(random.uniform(-.6, .6), 3, "Z") @ Matrix.Rotation(random.uniform(-.4, .4), 3, "X"))
cardboard(vol, (-0.45, 0.2, H - 0.25), (-0.05, 0.6, H + 0.2), 25)                                    # caja rota
vol.ucx.append(((-L / 2, -W / 2, 0), (L / 2, W / 2, H + 0.08)))
vol_objs = vol.build()

# --- pallet con cajas ---------------------------------------------------------------------------------
pal = Piece("SM_PalletCajas")
PW, PD = 1.2, 1.0
for y in (-PW / 2 + 0.05, 0, PW / 2 - 0.05):                                                       # tacos
    for x in (-PD / 2 + 0.05, 0, PD / 2 - 0.05):
        pal.box((x - 0.05, y - 0.05, 0.02), (x + 0.05, y + 0.05, 0.12), M["madera"])
for x in (-PD / 2 + 0.05, 0, PD / 2 - 0.05):
    pal.box((x - 0.05, -PW / 2, 0.0), (x + 0.05, PW / 2, 0.02), M["madera"])
for i in range(7):                                                                                  # tablas de arriba
    y = -PW / 2 + 0.06 + i * (PW - 0.12) / 6
    pal.box((-PD / 2, y - 0.05, 0.12), (PD / 2, y + 0.05, 0.145), M["madera"])
z = 0.145
for layer in range(3):
    sizes = [(0.45, 0.55, 0.38), (0.5, 0.5, 0.4), (0.42, 0.6, 0.35)]
    spots = [(-0.24, -0.28), (0.24, -0.28), (-0.24, 0.28), (0.24, 0.28)]
    if layer == 2:
        spots = spots[:2]
    for sx, sy in spots:
        a, b, h = random.choice(sizes)
        jitter = Vector((random.uniform(-.03, .03), random.uniform(-.03, .03), 0))
        cardboard(pal, Vector((sx - a / 2, sy - b / 2, z)) + jitter, Vector((sx + a / 2, sy + b / 2, z + h)) + jitter, random.uniform(-6, 6))
    z += 0.4
pal.ucx.append(((-PD / 2, -PW / 2, 0), (PD / 2, PW / 2, z)))
pal_objs = pal.build()

# --- bolsas de basura ---------------------------------------------------------------------------------
bags = Piece("SM_BolsasBasura")
for c, s in (((0, 0, 0.27), 1.0), ((0.45, 0.25, 0.24), 0.9), ((0.2, -0.4, 0.22), 0.8)):
    bag(bags, c, s)
bag_objs = bags.build()

# --- tablones en la abertura (mira a +X, hacia adentro) -----------------------------------------------
tab = Piece("SM_TablonesAbertura")
OW, OH, T = 3.4, 2.5, 0.05
n = 7
for i in range(n):                                                                                  # tablones verticales
    y0 = -OW / 2 + i * OW / n + 0.01
    tab.box((-T, y0, 0.0), (0.0, y0 + OW / n - 0.02, OH - random.uniform(0, 0.08)), M["madera_osc"] if i % 2 else M["madera"], bevel=0.008)
for z0 in (0.45, OH - 0.55):                                                                        # travesanos
    tab.box((0.0, -OW / 2, z0), (0.04, OW / 2, z0 + 0.14), M["madera"], bevel=0.008)
for sign in (-1, 1):                                                                                # cruz
    rot = Matrix.Rotation(sign * math.atan2(OH - 0.8, OW - 0.4), 3, "X")
    tab.box((0.04, -1.65, OH / 2 - 0.07), (0.08, 1.65, OH / 2 + 0.07), M["madera"], rot, pivot=(0.06, 0, OH / 2), bevel=0.008)
for y in (-1.4, -0.7, 0.0, 0.7, 1.4):                                                               # clavos
    for z0 in (0.52, OH - 0.48):
        tab.box((0.04, y - 0.012, z0 - 0.012), (0.05, y + 0.012, z0 + 0.012), M["clavo"])
tab.box((0.081, -0.55, OH / 2 - 0.1), (0.084, 0.55, OH / 2 + 0.1), M["amarillo"])                   # cartel de obra
tab.ucx.append(((-T, -OW / 2, 0), (0.08, OW / 2, OH)))
tab_objs = tab.build()

OUT.mkdir(parents=True, exist_ok=True)
report = {}
for objs in (vol_objs, pal_objs, bag_objs, tab_objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / f"{objs[0].name}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                             axis_forward="-Y", axis_up="Z")
    report[objs[0].name] = {"faces": len(objs[0].data.polygons), "ucx": len(objs) - 1}
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Rincon.blend"))
(OUT / "rincon_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("RINCON_OK", json.dumps(report))
