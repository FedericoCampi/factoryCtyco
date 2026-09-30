"""Blender: cabina de control y barrera para la salida del camion (28/09).

Piezas (FBX en SourceAssets/CabinaBarrera, metros, +X de Blender = +X de Unreal):
- SM_Cabina: cabina de 1,6 x 1,6 x 2,4 m, origen al centro del piso. Puerta de 1 m en el lado -X,
  ventanas en los otros tres lados, mostrador con botonera adentro (lado +X). UCX: las paredes (se entra
  por la puerta) y el mostrador.
- SM_CabinaTecho: techo aparte (Unreal lo oculta con el personaje adentro, la camara mira desde arriba).
- SM_BarreraPoste: poste amarillo y negro de 1,1 m con su caja, origen al centro de la base. UCX: el poste.
- SM_BarreraBrazo: brazo a rayas rojas y blancas de 3,1 m hacia +X, con contrapeso; origen en el eje de giro.

blender -b --factory-startup -P Scripts/author_gate_booth.py
"""
import json
from pathlib import Path
import bmesh
import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/CabinaBarrera"
SIZE, H, T = 1.6, 2.4, 0.08          # cabina: lado, alto de paredes, espesor
SILL, HEAD = 1.0, 2.1                # ventanas: de 1 m a 2,1 m
DOOR = 1.0                           # ancho de la puerta (lado -X)
ARM_LEN, ARM_W, ARM_H = 3.1, 0.07, 0.09
STRIPE = 0.4

bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, rough=0.6, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


M = {
    "pared": mat("M_CabinaPared", (0.78, 0.76, 0.70)),
    "zocalo": mat("M_CabinaZocalo", (0.11, 0.12, 0.13)),
    "vidrio": mat("M_CabinaVidrio", (0.16, 0.24, 0.29), rough=0.08, metal=0.3),
    "acero": mat("M_CabinaAcero", (0.08, 0.10, 0.13), rough=0.4, metal=0.8),
    "amarillo": mat("M_CabinaAmarillo", (0.85, 0.62, 0.04), rough=0.5),
    "rojo": mat("M_BarreraRojo", (0.75, 0.04, 0.03), rough=0.45),
    "blanco": mat("M_BarreraBlanco", (0.88, 0.88, 0.86), rough=0.45),
    "boton": mat("M_CabinaBoton", (0.9, 0.08, 0.05), rough=0.3, emit=1.5),
}


class Piece:
    """Una malla hecha de cajas, cada una con su material."""

    def __init__(self, name):
        self.name, self.bm, self.mats, self.ucx = name, bmesh.new(), [], []
        self.bm.loops.layers.uv.new("UVMap")

    def box(self, lo, hi, material, collide=False):
        if material not in self.mats:
            self.mats.append(material)
        lo, hi = Vector(lo), Vector(hi)
        verts = bmesh.ops.create_cube(self.bm, size=1.0, calc_uvs=True)["verts"]
        for v in verts:
            v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = self.mats.index(material)
        if collide:
            self.ucx.append((lo, hi))

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
                v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
            b.to_mesh(cm); b.free()
            c = bpy.data.objects.new(cm.name, cm); bpy.context.scene.collection.objects.link(c)
            objs.append(c)
        return objs


def wall(p, axis, at, a0, a1, windows=True):
    """Pared a lo largo del eje 'x' o 'y' (de a0 a a1), en la coordenada 'at' del otro eje."""
    def span(lo_a, hi_a, z0, z1, material, inset=0.0):
        if axis == "x":
            p.box((lo_a, at - T / 2 + inset, z0), (hi_a, at + T / 2 - inset, z1), material)
        else:
            p.box((at - T / 2 + inset, lo_a, z0), (at + T / 2 - inset, hi_a, z1), material)
    span(a0, a1, 0.0, 0.18, M["zocalo"])
    if windows:
        span(a0, a1, 0.18, SILL, M["pared"])
        span(a0, a1, SILL, HEAD, M["vidrio"], inset=0.025)
        span(a0, a1, SILL - 0.04, SILL, M["acero"])          # alfeizar
        span(a0, a1, HEAD, H, M["pared"])
    else:
        span(a0, a1, 0.18, H, M["pared"])
    # colision de toda la pared
    if axis == "x":
        p.ucx.append((Vector((a0, at - T / 2, 0)), Vector((a1, at + T / 2, H))))
    else:
        p.ucx.append((Vector((at - T / 2, a0, 0)), Vector((at + T / 2, a1, H))))


# --- cabina ---------------------------------------------------------------------------------------
s = SIZE / 2
cab = Piece("SM_Cabina")
cab.box((-s, -s, 0), (s, s, 0.05), M["zocalo"])                            # piso
wall(cab, "x", -s + T / 2, -s + T, s - T)                                  # sur (-Y)
wall(cab, "x", s - T / 2, -s + T, s - T)                                   # norte (+Y)
wall(cab, "y", s - T / 2, -s, s)                                           # este (+X), con ventana
wall(cab, "y", -s + T / 2, -s, -DOOR / 2, windows=False)                   # oeste, a los lados de la puerta
wall(cab, "y", -s + T / 2, DOOR / 2, s, windows=False)
cab.box((-s, -DOOR / 2, HEAD), (-s + T, DOOR / 2, H), M["pared"])          # dintel
for x in (-s, s - 0.1):                                                    # esquineros de acero
    for y in (-s, s - 0.1):
        cab.box((x, y, 0), (x + 0.1, y + 0.1, H), M["acero"])
for y in (-DOOR / 2 - 0.05, DOOR / 2):                                     # marco de la puerta
    cab.box((-s - 0.01, y, 0), (-s + T + 0.01, y + 0.05, HEAD), M["acero"])
cab.box((-s - 0.01, -DOOR / 2 - 0.05, HEAD), (-s + T + 0.01, DOOR / 2 + 0.05, HEAD + 0.05), M["acero"])
cab.box((s - T - 0.45, -s + T, 0.0), (s - T, s - T, 0.95), M["acero"], collide=True)   # mostrador
cab.box((s - T - 0.45, -s + T, 0.95), (s - T, s - T, 0.99), M["amarillo"])
cab.box((s - T - 0.3, -0.18, 0.99), (s - T - 0.1, 0.18, 1.07), M["zocalo"])            # botonera
cab.box((s - T - 0.24, -0.05, 1.07), (s - T - 0.16, 0.05, 1.11), M["boton"])
cab.box((-s, -s - 0.02, H - 0.25), (s, -s + 0.001, H - 0.12), M["amarillo"])          # franja de aviso al carril
booth = cab.build()

# --- techo ----------------------------------------------------------------------------------------
roof = Piece("SM_CabinaTecho")
roof.box((-s - 0.15, -s - 0.15, H), (s + 0.15, s + 0.15, H + 0.12), M["acero"])
roof.box((-s - 0.1, -s - 0.1, H + 0.12), (s + 0.1, s + 0.1, H + 0.16), M["pared"])
roof_objs = roof.build()

# --- poste ----------------------------------------------------------------------------------------
post = Piece("SM_BarreraPoste")
post.box((-0.15, -0.15, 0), (0.15, 0.15, 0.08), M["zocalo"])
for i in range(5):                                                         # franjas amarillas y negras
    post.box((-0.1, -0.1, 0.08 + i * 0.18), (0.1, 0.1, 0.08 + (i + 1) * 0.18), M["amarillo"] if i % 2 == 0 else M["zocalo"])
post.box((-0.16, -0.14, 0.98), (0.16, 0.14, 1.2), M["acero"])              # caja del motor
post.ucx.append((Vector((-0.16, -0.15, 0)), Vector((0.16, 0.15, 1.2))))
post_objs = post.build()

# --- brazo (origen en el eje de giro; se levanta girando sobre Y) ---------------------------------
arm = Piece("SM_BarreraBrazo")
n = int(ARM_LEN / STRIPE + 0.999)
for i in range(n):
    x0, x1 = 0.12 + i * STRIPE, min(0.12 + (i + 1) * STRIPE, ARM_LEN)
    arm.box((x0, -ARM_W / 2, -ARM_H / 2), (x1, ARM_W / 2, ARM_H / 2), M["rojo"] if i % 2 == 0 else M["blanco"])
arm.box((-0.45, -0.07, -0.08), (-0.1, 0.07, 0.08), M["zocalo"])            # contrapeso
arm.box((-0.1, -0.05, -0.05), (0.12, 0.05, 0.05), M["acero"])              # buje
arm.box((ARM_LEN - 0.04, -0.05, -0.06), (ARM_LEN, 0.05, 0.06), M["boton"]) # luz de la punta
arm_objs = arm.build()

OUT.mkdir(parents=True, exist_ok=True)
for objs in (booth, roof_objs, post_objs, arm_objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / f"{objs[0].name}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                             axis_forward="-Y", axis_up="Z")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "CabinaBarrera.blend"))
report = {"booth_m": [SIZE, SIZE, H], "door_m": DOOR, "arm_length_m": ARM_LEN, "pivot_height_m": 1.09,
          "pieces": {o[0].name: {"faces": len(o[0].data.polygons), "ucx": len(o) - 1} for o in (booth, roof_objs, post_objs, arm_objs)}}
(OUT / "cabina_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("CABINA_OK", json.dumps(report))
