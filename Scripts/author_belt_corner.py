"""Blender: esquina de cinta del usuario (3D assets/GLBs/esquinaCinta-complete.glb) como cinta de carga curva (30/09).

El GLB viene normalizado (1 x 1 m, 17 cm de alto, ~700 000 triangulos, una sola malla con texturas): un cuarto de
circulo de cinta plana que entra por -X y sale por +Y (Blender), sin patas. Se prepara para AFactoryLoadingBelt con
TurnDegrees -90 (en Unreal sale hacia -Y):
- ancho de la cinta como SM_CintaCarga (0,8 m); rodillos a DECK (0,88 m, como las demas cintas de carga): se sube
  el modelo y se le ponen cuatro patas de acero (material M_CintaAcero, el mismo que usan los postes);
- origen en el centro de la punta de entrada, al piso, mirando a +X (como SM_CintaCarga);
- ~125 000 triangulos; colision: 8 cajas UCX a lo largo de la curva.
Salida: SourceAssets/CintaEsquina/SM_CintaEsquina.fbx y cinta_esquina_build.json (con el largo de la curva, que
va en la propiedad Length del actor).

blender -b --factory-startup -P Scripts/author_belt_corner.py
"""
import json
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

SRC = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs/esquinaCinta-complete.glb")
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/CintaEsquina"
NAME = "SM_CintaEsquina"
WIDTH, DECK = 0.8, 0.88          # como SM_CintaCarga
DECIMATE = 0.18
LEG = 0.06                       # lado de las patas
UCX_PIECES = 8

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
o = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
bpy.ops.object.select_all(action="DESELECT")
o.select_set(True)
bpy.context.view_layer.objects.active = o
o.parent = None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for extra in [x for x in bpy.context.scene.objects if x is not o]:
    bpy.data.objects.remove(extra)
tris_in = sum(len(p.vertices) - 2 for p in o.data.polygons)

# medidas del modelo normalizado: el brazo de entrada (borde -X) y el de salida (borde +Y)
co = [v.co.copy() for v in o.data.vertices]
xmin, ymax = min(c.x for c in co), max(c.y for c in co)
entry = [c.y for c in co if c.x < xmin + 0.02]
exit_ = [c.x for c in co if c.y > ymax - 0.02]
band = ((max(entry) - min(entry)) + (max(exit_) - min(exit_))) / 2
entry_c, exit_c = (min(entry) + max(entry)) / 2, (min(exit_) + max(exit_)) / 2
radius_n = exit_c - xmin                       # radio del eje de la curva (centro en (xmin, entry_c + radio))
roller_top_n = 0.15                            # superficie de rodillos del modelo (las barandas llegan a 0,17)
scale = WIDTH / band
lift = DECK - roller_top_n * scale
# entrada en el origen, mirando a +X, al piso
o.data.transform(Matrix.Translation((0, 0, lift)) @ Matrix.Scale(scale, 4) @ Matrix.Translation((-xmin, -entry_c, 0)))
dec = o.modifiers.new("Decimate", "DECIMATE")
dec.ratio = DECIMATE
bpy.ops.object.modifier_apply(modifier=dec.name)
o.name = o.data.name = NAME
radius = radius_n * scale
arc = math.pi / 2 * radius                     # Length del actor (m)


def at(r, angle):
    """Punto a distancia r del centro de la curva, a `angle` desde la entrada (Blender: dobla hacia +Y)."""
    return Vector((r * math.sin(angle), radius - r * math.cos(angle)))


# patas: cuatro, en el borde interior y exterior a 20 y 70 grados, del piso a la cinta
steel = bpy.data.materials.new("M_CintaAcero")
steel.use_nodes = True
bsdf = steel.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.07, 0.08, 0.1, 1)
bsdf.inputs["Metallic"].default_value = 0.8
bsdf.inputs["Roughness"].default_value = 0.45
o.data.materials.append(steel)
slot = len(o.data.materials) - 1
bm = bmesh.new()
bm.from_mesh(o.data)
for r in (radius - WIDTH / 2 + 0.08, radius + WIDTH / 2 - 0.08):
    for deg in (20, 70):
        p = at(r, math.radians(deg))
        verts = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        for v in verts:
            v.co = Vector((p.x + v.co.x * LEG, p.y + v.co.y * LEG, (v.co.z + 0.5) * (lift + 0.02)))
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = slot
bm.to_mesh(o.data)
bm.free()

# colision: cajas a lo largo de la curva, del piso a las barandas
top = DECK + 0.03
ucx = []
for i in range(UCX_PIECES):
    a0, a1 = math.pi / 2 * i / UCX_PIECES, math.pi / 2 * (i + 1) / UCX_PIECES
    corners = [at(r, a) for a in (a0, a1) for r in (radius - WIDTH / 2, radius + WIDTH / 2)]
    me = bpy.data.meshes.new(f"UCX_{NAME}_{i:02d}")
    b = bmesh.new()
    vs = [b.verts.new((c.x, c.y, z)) for z in (0.0, top) for c in corners]
    bmesh.ops.convex_hull(b, input=vs)
    b.to_mesh(me)
    b.free()
    u = bpy.data.objects.new(me.name, me)
    bpy.context.scene.collection.objects.link(u)
    ucx.append(u)

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
for x in [o, *ucx]:
    x.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT / f"{NAME}.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                         path_mode="COPY", embed_textures=True, axis_forward="-Y", axis_up="Z")
tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
(OUT / "cinta_esquina_build.json").write_text(json.dumps({
    "source": str(SRC), "scale": round(scale, 4), "width_m": WIDTH, "deck_m": DECK, "lift_m": round(lift, 3),
    "radius_m": round(radius, 3), "length_cm": round(arc * 100, 1), "turn_degrees_unreal": -90,
    "exit_unreal_cm": [round(radius * 100, 1), round(-radius * 100, 1)],
    "triangles_in": tris_in, "triangles": tris, "ucx": UCX_PIECES,
    "materials": [m.name for m in o.data.materials if m]}, indent=1), encoding="utf-8")
print("CORNER_OK", round(scale, 3), round(radius, 3), round(arc, 3), tris)
