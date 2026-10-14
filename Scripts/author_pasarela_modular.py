"""Blender: piezas de las pasarelas para armarlas a medida en Unreal (AFactoryWalkwayL y AFactoryWalkwayStraight, 03/10).

De cada modelo (SourceAssets/Pasarelas/<SM>.fbx, author_pasarelas.py: metros) se cortan tres piezas:
- piso: un tramo con todo el ancho, del suelo hasta deck_cut (sin barandas);
- baranda: un tramo de baranda entre dos postes, de deck_cut para arriba;
- poste: un poste, de deck_cut para arriba.
L (SM_PasarelaL): del brazo que corre a lo largo de Y en x < 0, con su baranda exterior (x ~ -2,49, postes en y -1,14
y 0,34); se gira -90 grados para que corra a lo largo de X. Recta (SM_PasarelaRecta): ya corre a lo largo de X; su
baranda de +Y (y ~ 1,10, postes en x -2,32 y -0,92).
Cada pieza queda centrada en X e Y, con Z desde el suelo, a lo largo de X, y el lado de afuera de la baranda hacia -Y en
Unreal (+Y en Blender). Colision: una caja (UCX) por pieza.
Salida: SourceAssets/Pasarelas/Modular/<pieza>.fbx y modular_build.json (medidas en cm para los actores).

blender -b --factory-startup -P Scripts/author_pasarela_modular.py
"""
import json
import math
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "SourceAssets/Pasarelas/Modular"
MODELS = {
    "L": dict(src="SM_PasarelaL", rotate=-90, deck_top=0.404, deck_cut=0.43, post_spacing=1.48, rail_center=(-2.49, None),
              pieces={"SM_PasarelaPiso": dict(x=(-2.64, -1.21), y=(-1.02, 0.25), deck=True),
                      "SM_PasarelaBaranda": dict(x=(-2.64, -2.34), y=(-1.02, 0.25), ucx_w=0.12, ucx_top=1.36),
                      "SM_PasarelaPoste": dict(x=(-2.64, -2.34), y=(-1.25, -1.02), ucx_w=0.22, ucx_top=1.40)}),
    "Recta": dict(src="SM_PasarelaRecta", rotate=0, deck_top=0.37, deck_cut=0.40, post_spacing=1.40, rail_center=(None, 1.10),
                  pieces={"SM_PasarelaRectaPiso": dict(x=(-2.19, -1.03), y=(-1.27, 1.27), deck=True),
                          "SM_PasarelaRectaBaranda": dict(x=(-2.19, -1.03), y=(0.94, 1.27), ucx_w=0.10, ucx_top=1.34),
                          "SM_PasarelaRectaPoste": dict(x=(-1.04, -0.80), y=(0.94, 1.27), ucx_w=0.24, ucx_top=1.37)}),
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
    bpy.ops.import_scene.fbx(filepath=str(ROOT / f"SourceAssets/Pasarelas/{m['src']}.fbx"))
    source = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
    bpy.context.view_layer.objects.active = source
    bpy.ops.object.select_all(action="DESELECT")
    source.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    rx, ry = m["rail_center"]
    out = {"deck_top_cm": round(m["deck_top"] * 100, 1), "post_spacing_cm": round(m["post_spacing"] * 100, 1), "pieces": {}}
    for name, w in m["pieces"].items():
        piece = source.copy()
        piece.data = source.data.copy()
        piece.name = piece.data.name = name
        bpy.context.scene.collection.objects.link(piece)
        b = bmesh.new()
        b.from_mesh(piece.data)
        z = (-1.0, m["deck_cut"]) if w.get("deck") else (m["deck_cut"], 3.0)
        for axis, (lo, hi) in zip(range(3), (w["x"], w["y"], z)):
            cut(b, axis, lo, True)
            cut(b, axis, hi, False)
        # centrada (la baranda y el poste, en la linea de la baranda); despues, a lo largo de X
        cx = rx if (rx is not None and not w.get("deck")) else (w["x"][0] + w["x"][1]) / 2
        cy = ry if (ry is not None and not w.get("deck")) else (w["y"][0] + w["y"][1]) / 2
        place = Matrix.Rotation(math.radians(m["rotate"]), 4, "Z") @ Matrix.Translation((-cx, -cy, 0))
        bmesh.ops.transform(b, matrix=place, verts=b.verts)
        b.to_mesh(piece.data)
        b.free()
        vs = [v.co for v in piece.data.vertices]
        lo = Vector([min(v[i] for v in vs) for i in range(3)])
        hi = Vector([max(v[i] for v in vs) for i in range(3)])
        if w.get("deck"):
            clo, chi = Vector((lo.x, lo.y, 0.0)), Vector((hi.x, hi.y, m["deck_top"]))
        else:
            clo, chi = Vector((lo.x, -w["ucx_w"] / 2, m["deck_cut"])), Vector((hi.x, w["ucx_w"] / 2, w["ucx_top"]))
        collider = box(f"UCX_{name}_00", clo, chi)
        bpy.ops.object.select_all(action="DESELECT")
        piece.select_set(True)
        collider.select_set(True)
        bpy.ops.export_scene.fbx(filepath=str(OUT / f"{name}.fbx"), use_selection=True, object_types={"MESH"},
                                 apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                                 path_mode="COPY", embed_textures=True, axis_forward="-Y", axis_up="Z")
        out["pieces"][name] = {"size_cm": [round((hi[i] - lo[i]) * 100, 1) for i in range(3)],
                               "min_cm": [round(lo[i] * 100, 1) for i in range(3)],
                               "triangles": sum(len(p.vertices) - 2 for p in piece.data.polygons)}
        bpy.data.objects.remove(collider)
        bpy.data.objects.remove(piece)
    report[model] = out

(OUT / "modular_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("MODULAR_OK", json.dumps(report))
