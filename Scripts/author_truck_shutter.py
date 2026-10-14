"""Blender: persiana de verdad para la parte de atras del camion (04/10).

Reemplaza a SM_CamionPersiana (la pared de atras del modelo, que Unreal achicaba y se veia mal) por una persiana de
tablillas que suben y se esconden tras un dintel, con los colores del camion (medidos en truck.glb: paneles de la caja
crema claro, marco y postes gris oscuro):
- SM_CamionPersianaLama: una tablilla de aluminio (crema de la caja) con una ranura al medio y la bisagra oscura arriba;
  origen en el medio de su borde de abajo, en el plano de la persiana.
- SM_CamionPersianaZocalo: el zocalo de abajo (barra, burlete de goma y manija); origen en el medio de su borde de abajo.
- SM_CamionPersianaMarco: las dos guias a los costados y el dintel de arriba (gris del marco); origen en el medio del
  borde de arriba del vano (RearDoorTop de AFactoryVehiclePath).
Medidas en el espacio del camion (cm, X hacia el frente): vano de 152,9 x 138,9 (camion_build.json), plano de la
persiana en RearDoorTop. AFactoryVehiclePath apila las tablillas sobre el zocalo y, al abrir, las sube: las que quedan
enteras detras del dintel (RearHeader) desaparecen.
Salida: SourceAssets/Camion/camion_persiana_*.fbx y camion_persiana_build.json.

blender -b --factory-startup -P Scripts/author_truck_shutter.py
"""
import json
from pathlib import Path
import bmesh
import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Camion"
build = json.loads((OUT / "camion_build.json").read_text(encoding="utf-8"))
HEIGHT = build["rear_door_size_m"][2]          # 1.389
OPENING = 2 * 0.147 * 5.2                      # 152,9 cm (REAR de author_truck_loop.py: |y| < 0.147 del GLB, x5,2)
SLATS = 17
BOTTOM = 0.06                                  # zocalo
SLAT = (HEIGHT - BOTTOM) / SLATS               # ~7,8 cm
HEADER = 0.10                                  # dintel: tapa las tablillas que suben
THICK = 0.016
WIDTH = OPENING + 0.02                         # las tablillas entran 1 cm en cada guia

bpy.ops.wm.read_factory_settings(use_empty=True)


def srgb(c):
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def mat(name, color, rough, metal):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*srgb(color), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


# colores medidos en la textura del camion (sRGB)
SLAT_MAT = mat("M_PersianaLama", (0.776, 0.773, 0.714), 0.45, 0.35)      # paneles de la caja
FRAME_MAT = mat("M_PersianaMarco", (0.227, 0.243, 0.231), 0.55, 0.4)     # marco de atras
JOINT_MAT = mat("M_PersianaJunta", (0.325, 0.333, 0.322), 0.6, 0.3)      # postes (bisagras y ranura)
RUBBER_MAT = mat("M_PersianaGoma", (0.05, 0.05, 0.05), 0.9, 0.0)


def piece(name, boxes):
    """Malla de cajas (lo, hi, material) en metros, con UV."""
    mats = []
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")
    for lo, hi, material in boxes:
        if material not in mats:
            mats.append(material)
        lo, hi = Vector(lo), Vector(hi)
        vs = bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)["verts"]
        for v in vs:
            v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (lo + hi) / 2
        for f in {f for v in vs for f in v.link_faces}:
            f.material_index = mats.index(material)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


w, t = WIDTH / 2, THICK / 2
# tablilla: dos mitades al ras por fuera (-X), una ranura hundida al medio y la bisagra arriba, oscura y hundida
groove, hinge = 0.008, 0.005
mid = SLAT / 2
lama = piece("SM_CamionPersianaLama", [
    ((-t, -w, 0.0), (t, w, mid - groove / 2), SLAT_MAT),
    ((-t + 0.004, -w, mid - groove / 2), (t, w, mid + groove / 2), JOINT_MAT),
    ((-t, -w, mid + groove / 2), (t, w, SLAT - hinge), SLAT_MAT),
    ((-t + 0.003, -w, SLAT - hinge), (t, w, SLAT), JOINT_MAT),
])
# zocalo: barra de aluminio, burlete de goma abajo y manija al medio, por fuera
zocalo = piece("SM_CamionPersianaZocalo", [
    ((-0.012, -w, 0.0), (0.012, w, 0.015), RUBBER_MAT),
    ((-0.014, -w, 0.015), (0.014, w, BOTTOM), FRAME_MAT),
    ((-0.04, -0.12, 0.022), (-0.014, -0.105, 0.05), FRAME_MAT),
    ((-0.04, 0.105, 0.022), (-0.014, 0.12, 0.05), FRAME_MAT),
    ((-0.045, -0.12, 0.022), (-0.04, 0.12, 0.034), FRAME_MAT),
])
# marco: guias en U a los costados (de canto) y dintel por fuera de las tablillas
g0 = OPENING / 2 - 0.012
frame = []
for side in (-1, 1):
    y0, y1 = sorted((side * g0, side * (OPENING / 2 + 0.02)))
    frame += [((-0.025, y0, -HEIGHT), (-0.012, y1, 0.0), FRAME_MAT),      # ala de afuera
              ((0.012, y0, -HEIGHT), (0.025, y1, 0.0), FRAME_MAT)]        # ala de adentro
    yb0, yb1 = sorted((side * (OPENING / 2 + 0.008), side * (OPENING / 2 + 0.02)))
    frame.append(((-0.025, yb0, -HEIGHT), (0.025, yb1, 0.0), FRAME_MAT))  # fondo de la U
frame.append(((-0.045, -(OPENING / 2 + 0.02), -HEADER), (-0.012, OPENING / 2 + 0.02, 0.0), FRAME_MAT))
frame.append(((-0.05, -(OPENING / 2 + 0.02), -HEADER), (-0.045, OPENING / 2 + 0.02, -HEADER + 0.012), JOINT_MAT))
marco = piece("SM_CamionPersianaMarco", frame)

OUT.mkdir(parents=True, exist_ok=True)
names = {}
for obj, file in ((lama, "camion_persiana_lama"), (zocalo, "camion_persiana_zocalo"), (marco, "camion_persiana_marco")):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / f"{file}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                             axis_forward="-Y", axis_up="Z")
    names[obj.name] = file
report = {"height_cm": round(HEIGHT * 100, 1), "opening_cm": round(OPENING * 100, 1), "slats": SLATS,
          "slat_cm": round(SLAT * 100, 2), "bottom_cm": BOTTOM * 100, "header_cm": HEADER * 100, "meshes": names,
          "colors_srgb": {"lama": [0.776, 0.773, 0.714], "marco": [0.227, 0.243, 0.231], "junta": [0.325, 0.333, 0.322]}}
(OUT / "camion_persiana_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("PERSIANA_OK", json.dumps(report))
