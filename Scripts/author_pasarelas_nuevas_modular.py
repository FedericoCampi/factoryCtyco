"""Blender: piezas de las pasarelas nuevas para armarlas a medida en Unreal (07/10), como author_pasarela_modular.py.

Los modelos son los de author_despacho_equipos.py (SourceAssets/DespachoEquipos, metros, origen al centro y abajo):
- Verde (SM_PasarelaVerde, recta): corre a lo largo de Y, barandas en x = +-0,515, postes en y -2,84, -0,96, 0,96 y
  2,84 (cada 1,89 m), patas en las puntas y en y ~0,18, piso a 0,653. Se toma la baranda de +X; se gira +90 grados.
- L (SM_PasarelaLElevada): esquina de afuera en (3,25, -3,215); brazo A hacia -X (barandas en y -3,215 y -2,10),
  brazo B hacia +Y (x 3,25 y 2,12); piso a 0,997. Se toma la baranda de afuera del brazo A (postes en x -1,54 y 0,0)
  y el piso con las patas de x ~0; se gira 180 grados.
De cada uno se cortan tres piezas:
- piso: un tramo con todo el ancho, de leg_top hasta deck_cut (la losa con sus vigas, sin barandas);
- patas: lo de abajo de ese tramo, del suelo hasta leg_top (en Unreal se estiran con la altura del piso; 07/10);
- baranda: un tramo de baranda entre dos postes, de deck_cut para arriba;
- poste: un poste, de deck_cut para arriba.
Cada pieza queda centrada en X e Y, con Z desde el suelo, a lo largo de X, y el lado de afuera de la baranda hacia -Y en
Unreal (+Y en Blender). Colision: una caja (UCX) por pieza; las patas, su propia malla (se pasa por debajo).
Salida: SourceAssets/Pasarelas/ModularNuevas/<pieza>.fbx y modular_nuevas_build.json (medidas en cm para los actores).

blender -b --factory-startup -P Scripts/author_pasarelas_nuevas_modular.py
"""
import json
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "SourceAssets/Pasarelas/ModularNuevas"
# rail: la linea de la baranda tomada (eje, valor); rails_apart: distancia entre las dos barandas de la pasarela
MODELS = {
    "Verde": dict(src="SM_PasarelaVerde", rotate=90, deck_top=0.653, deck_cut=0.70, leg_top=0.45, rail=(0, 0.515), rails_apart=1.03,
                  post_spacing=1.89,
                  pieces={"SM_PasarelaVerdePiso": dict(x=(-0.70, 0.70), y=(-0.77, 1.12), deck=True),
                          "SM_PasarelaVerdeBaranda": dict(x=(0.40, 0.70), y=(-0.85, 0.85), ucx_w=0.10, ucx_top=1.65),
                          "SM_PasarelaVerdePoste": dict(x=(0.40, 0.70), y=(-1.07, -0.85), ucx_w=0.20, ucx_top=1.65),
                          "SM_PasarelaVerdePatas": dict(x=(-0.70, 0.70), y=(-0.77, 1.12), legs=True)}),
    "LElevada": dict(src="SM_PasarelaLElevada", rotate=180, deck_top=0.997, deck_cut=1.04, leg_top=0.70, rail=(1, -3.215),
                     rails_apart=1.115, post_spacing=1.54,
                     pieces={"SM_PasarelaLElevadaPiso": dict(x=(-1.04, 0.96), y=(-3.45, -1.80), deck=True),
                             "SM_PasarelaLElevadaBaranda": dict(x=(-1.46, -0.10), y=(-3.42, -3.02), ucx_w=0.10, ucx_top=1.99),
                             "SM_PasarelaLElevadaPoste": dict(x=(-1.63, -1.46), y=(-3.42, -3.02), ucx_w=0.18, ucx_top=1.99),
                             "SM_PasarelaLElevadaPatas": dict(x=(-1.04, 0.96), y=(-3.45, -1.80), legs=True)}),
}


def cut(bm, axis, value, keep_above):
    normal = Vector((0, 0, 0))
    normal[axis] = 1.0
    co = Vector((0, 0, 0))
    co[axis] = value
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=normal, clear_inner=keep_above, clear_outer=not keep_above)


def box(name, lo, hi):
    mesh = bpy.data.meshes.new(name)
    b = bmesh.new()
    bmesh.ops.create_cube(b, size=1.0)
    bmesh.ops.scale(b, vec=hi - lo, verts=b.verts)
    bmesh.ops.translate(b, vec=(lo + hi) / 2, verts=b.verts)
    b.to_mesh(mesh)
    b.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


OUT.mkdir(parents=True, exist_ok=True)
report = {}
for model, m in MODELS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(ROOT / f"SourceAssets/DespachoEquipos/{m['src']}.fbx"))
    source = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
    bpy.context.view_layer.objects.active = source
    bpy.ops.object.select_all(action="DESELECT")
    source.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    rail_axis, rail_at = m["rail"]
    along = 1 - rail_axis
    out = {"deck_top_cm": round(m["deck_top"] * 100, 1), "leg_top_cm": round(m["leg_top"] * 100, 1), "post_spacing_cm": round(m["post_spacing"] * 100, 1),
           "rails_apart_cm": round(m["rails_apart"] * 100, 1), "pieces": {}}
    for name, w in m["pieces"].items():
        piece = source.copy()
        piece.data = source.data.copy()
        piece.name = piece.data.name = name
        bpy.context.scene.collection.objects.link(piece)
        b = bmesh.new()
        b.from_mesh(piece.data)
        z = (m["leg_top"], m["deck_cut"]) if w.get("deck") else (-1.0, m["leg_top"]) if w.get("legs") else (m["deck_cut"], 3.0)
        for axis, (lo, hi) in zip(range(3), (w["x"], w["y"], z)):
            cut(b, axis, lo, True)
            cut(b, axis, hi, False)
        # centrada (la baranda y el poste, en la linea de la baranda); despues, a lo largo de X
        c = [(w["x"][0] + w["x"][1]) / 2, (w["y"][0] + w["y"][1]) / 2]
        if not (w.get("deck") or w.get("legs")):
            c[rail_axis] = rail_at
        place = Matrix.Rotation(math.radians(m["rotate"]), 4, "Z") @ Matrix.Translation((-c[0], -c[1], 0))
        bmesh.ops.transform(b, matrix=place, verts=b.verts)
        b.to_mesh(piece.data)
        b.free()
        vs = [v.co for v in piece.data.vertices]
        lo = Vector([min(v[i] for v in vs) for i in range(3)])
        hi = Vector([max(v[i] for v in vs) for i in range(3)])
        collider = None
        if w.get("deck"):
            clo, chi = Vector((lo.x, lo.y, m["leg_top"])), Vector((hi.x, hi.y, m["deck_top"]))
        elif not w.get("legs"):
            clo, chi = Vector((lo.x, -w["ucx_w"] / 2, m["deck_cut"])), Vector((hi.x, w["ucx_w"] / 2, w["ucx_top"]))
        if not w.get("legs"):
            collider = box(f"UCX_{name}_00", clo, chi)
        bpy.ops.object.select_all(action="DESELECT")
        piece.select_set(True)
        if collider:
            collider.select_set(True)
        bpy.ops.export_scene.fbx(filepath=str(OUT / f"{name}.fbx"), use_selection=True, object_types={"MESH"},
                                 apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                                 path_mode="COPY", embed_textures=True, axis_forward="-Y", axis_up="Z")
        out["pieces"][name] = {"size_cm": [round((hi[i] - lo[i]) * 100, 1) for i in range(3)],
                               "min_cm": [round(lo[i] * 100, 1) for i in range(3)],
                               "max_cm": [round(hi[i] * 100, 1) for i in range(3)],
                               "cut_length_cm": round((w["x" if along == 0 else "y"][1] - w["x" if along == 0 else "y"][0]) * 100, 1),
                               "triangles": sum(len(p.vertices) - 2 for p in piece.data.polygons)}
        if collider:
            bpy.data.objects.remove(collider)
        bpy.data.objects.remove(piece)
    report[model] = out

(OUT / "modular_nuevas_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("MODULAR_NUEVAS_OK", json.dumps(report))
