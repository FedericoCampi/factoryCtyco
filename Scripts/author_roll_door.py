"""Blender: porton enrollable para la entrada de los camiones (muro oeste del estacionamiento), 28/09.

Piezas (FBX en SourceAssets/Porton, metros, +X de Blender = +X de Unreal, Y de Blender = -Y de Unreal):
- SM_Porton: cortina de tablillas de acero de 3,26 x 2,44 m, 5 cm de espesor, con zocalo de rayas de
  peligro. Origen en el borde de arriba, al centro: Unreal la achica en Z hacia arriba al abrirse
  (se enrolla en la caja). Sin colision (la abertura ya tiene una pared invisible para el personaje).
- SM_PortonCaja: caja del rollo, 3,6 x 0,35 x 0,35 m, origen al centro, para ir sobre la abertura del lado de adentro.
- SM_PortonBoton: botonera de pared (0,24 x 0,1 x 0,4 m) con hongo verde (abrir) y rojo (cerrar); mira a +X,
  origen al centro de su cara de atras. Material M_PortonLuz con parametro Abierto (0 rojo, 1 verde).

blender -b --factory-startup -P Scripts/author_roll_door.py
"""
import json
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Porton"
W, H, T = 3.26, 2.44, 0.05          # cortina: ancho (en Y), alto, espesor (en X)
SLAT = 0.1                           # alto de cada tablilla

bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, rough=0.5, metal=0.0, emit=0.0):
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
    "tablilla": mat("M_PortonTablilla", (0.42, 0.45, 0.48), 0.45, 0.85),
    "ranura": mat("M_PortonRanura", (0.12, 0.13, 0.15), 0.5, 0.7),
    "amarillo": mat("M_PortonAmarillo", (0.85, 0.62, 0.04), 0.5),
    "negro": mat("M_PortonNegro", (0.04, 0.04, 0.045), 0.6),
    "caja": mat("M_PortonCaja", (0.08, 0.10, 0.13), 0.4, 0.8),
    "luz": mat("M_PortonLuz", (0.9, 0.08, 0.05), 0.3, 0.0, 1.5),
}


class Piece:
    def __init__(self, name):
        self.name, self.bm, self.mats = name, bmesh.new(), []
        self.bm.loops.layers.uv.new("UVMap")

    def box(self, lo, hi, material):
        if material not in self.mats:
            self.mats.append(material)
        lo, hi = Vector(lo), Vector(hi)
        vs = bmesh.ops.create_cube(self.bm, size=1.0, calc_uvs=True)["verts"]
        for v in vs:
            v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
        for f in {f for v in vs for f in v.link_faces}:
            f.material_index = self.mats.index(material)

    def build(self):
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me); self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        o = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(o)
        return o


# --- cortina: tablillas desde el borde de arriba (z 0) hacia abajo ------------------------------
door = Piece("SM_Porton")
n = int(H / SLAT)
for i in range(n):
    z1 = -i * SLAT
    door.box((-T / 2, -W / 2, z1 - SLAT + 0.012), (T / 2, W / 2, z1), M["tablilla"])
    door.box((-T / 2 - 0.004, -W / 2, z1 - SLAT), (T / 2 + 0.004, W / 2, z1 - SLAT + 0.012), M["ranura"])
# zocalo con rayas de peligro (los ultimos 20 cm) y guias laterales
door.box((-T / 2 - 0.008, -W / 2, -H), (T / 2 + 0.008, W / 2, -H + 0.2), M["negro"])
stripe = 0.18
k = 0
y = -W / 2
while y < W / 2 - 1e-3:
    y1 = min(y + stripe / 2, W / 2)
    if k % 2 == 0:
        for side in (-1, 1):
            door.box((side * (T / 2 + 0.008) - 0.001, y, -H + 0.03), (side * (T / 2 + 0.008) + 0.001, y1, -H + 0.17), M["amarillo"])
    y += stripe / 2
    k += 1
door_obj = door.build()

# --- caja del rollo --------------------------------------------------------------------------------
box = Piece("SM_PortonCaja")
box.box((-0.175, -1.8, -0.175), (0.175, 1.8, 0.175), M["caja"])
box.box((-0.18, -1.82, -0.18), (0.18, -1.76, 0.18), M["negro"])
box.box((-0.18, 1.76, -0.18), (0.18, 1.82, 0.18), M["negro"])
box.box((0.176, -1.6, -0.03), (0.182, 1.6, 0.03), M["amarillo"])     # filete amarillo al frente
box_obj = box.build()

# --- botonera de pared (mira a +X) ------------------------------------------------------------------
btn = Piece("SM_PortonBoton")
btn.box((0.0, -0.12, -0.2), (0.1, 0.12, 0.2), M["caja"])
btn.box((0.1, -0.1, 0.12), (0.104, 0.1, 0.18), M["amarillo"])         # franja de aviso arriba
btn.box((0.1, -0.05, -0.02), (0.14, 0.05, 0.08), M["luz"])            # hongo (verde/rojo segun Abierto)
btn.box((0.1, -0.08, -0.15), (0.104, 0.08, -0.07), M["negro"])        # placa
btn_obj = btn.build()

OUT.mkdir(parents=True, exist_ok=True)
for o in (door_obj, box_obj, btn_obj):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / f"{o.name}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                             axis_forward="-Y", axis_up="Z")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Porton.blend"))
report = {"door_m": [W, H, T], "slats": n, "faces": {o.name: len(o.data.polygons) for o in (door_obj, box_obj, btn_obj)}}
(OUT / "porton_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("PORTON_OK", json.dumps(report))
