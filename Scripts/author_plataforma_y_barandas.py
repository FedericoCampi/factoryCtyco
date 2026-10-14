"""Blender: piezas de la plataforma industrial y de la baranda de la escalera, para armarlas a medida en Unreal (07/10).

Plataforma (SourceAssets/DespachoEquipos/SM_PlataformaIndustrial.fbx, author_despacho_equipos.py: 2,48 x 2,49 m, 1 m de
alto, piso a 0,975; sin barandas): cuatro patas en las esquinas con diagonales, vigas en los costados y una placa.
Piezas (para AFactoryPlatform), todas con la orientacion de Unreal (Blender (x, y) -> Unreal (x, -y)):
- esquina (SM_PlataformaEsquina): el cuadrado de CORNER m de la esquina (en Unreal la de +X+Y) con las diagonales y
  el remate, de COLUMN_TOP para arriba; origen en la esquina de afuera, la pieza hacia -X y -Y;
- columna (SM_PlataformaColumna): la pata de la esquina entre FOOT_TOP y COLUMN_TOP, con z desde 0 (se estira);
- pie (SM_PlataformaPie): la base de la pata, de 0 a FOOT_TOP;
- costado (SM_PlataformaCostado): un tramo de EDGE_LENGTH m del medio de un costado (en Unreal el de +Y), la viga y el
  borde del piso, de EDGE_DEPTH m hacia adentro; origen en la linea del borde, a lo largo de X, hacia -Y;
- piso (SM_PlataformaPiso): un cuadrado del medio de la placa (DECK m), centrado.
Baranda de la escalera (SourceAssets/EscaleraPlataforma/SM_EscaleraPlataforma.fbx): la de atras de la plataforma
(y ~3,43 en Blender, piso a 2,04), un panel entre dos postes (SM_BarandaEscaleraTramo) y un poste
(SM_BarandaEscaleraPoste), con z desde el piso (0) y el lado de afuera hacia -Y en Unreal (+Y en Blender, como ya esta).
Colision: caja (UCX) en el piso y en las barandas; las otras piezas, su propia malla (en Unreal, complex as simple).
Salida: SourceAssets/Plataformas/<pieza>.fbx y plataforma_build.json (medidas en cm).

blender -b --factory-startup -P Scripts/author_plataforma_y_barandas.py
"""
import json
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "SourceAssets/Plataformas"
CORNER, EDGE_LENGTH, EDGE_DEPTH, DECK = 0.62, 0.60, 0.35, 1.20
FOOT_TOP, COLUMN_TOP, DECK_TOP, TOP = 0.09, 0.32, 0.975, 1.02
RAIL_FLOOR, RAIL_LINE = 2.04, 3.43


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


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    source = [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.name.startswith("UCX")][0]
    for o in [o for o in bpy.context.scene.objects if o is not source]:
        bpy.data.objects.remove(o)
    bpy.context.view_layer.objects.active = source
    source.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return source


def piece(source, name, x, y, z, origin, ucx=None):
    """Cuts source to the box x, y, z (Blender m), moves origin to (0, 0, 0) and exports it (with a UCX box given in
    the piece's own coordinates). Returns its size and bounds in cm."""
    p = source.copy()
    p.data = source.data.copy()
    p.name = p.data.name = name
    bpy.context.scene.collection.objects.link(p)
    b = bmesh.new()
    b.from_mesh(p.data)
    for axis, (lo, hi) in enumerate((x, y, z)):
        cut(b, axis, lo, True)
        cut(b, axis, hi, False)
    bmesh.ops.transform(b, matrix=Matrix.Translation(-Vector(origin)), verts=b.verts)
    b.to_mesh(p.data)
    b.free()
    vs = [v.co for v in p.data.vertices]
    lo = Vector([min(v[i] for v in vs) for i in range(3)])
    hi = Vector([max(v[i] for v in vs) for i in range(3)])
    collider = box(f"UCX_{name}_00", Vector(ucx[0]), Vector(ucx[1])) if ucx else None
    bpy.ops.object.select_all(action="DESELECT")
    p.select_set(True)
    if collider:
        collider.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / f"{name}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                             path_mode="COPY", embed_textures=True, axis_forward="-Y", axis_up="Z")
    info = {"size_cm": [round((hi[i] - lo[i]) * 100, 1) for i in range(3)],
            "min_cm": [round(lo[i] * 100, 1) for i in range(3)], "max_cm": [round(hi[i] * 100, 1) for i in range(3)],
            "triangles": sum(len(f.vertices) - 2 for f in p.data.polygons)}
    if collider:
        bpy.data.objects.remove(collider)
    bpy.data.objects.remove(p)
    return info


OUT.mkdir(parents=True, exist_ok=True)
report = {"platform": {}, "rail": {}}

src = load(ROOT / "SourceAssets/DespachoEquipos/SM_PlataformaIndustrial.fbx")
vs = [v.co for v in src.data.vertices]
hx, hy = max(v.x for v in vs), max(-v.y for v in vs)     # la esquina de Unreal +X+Y es la de Blender +X -Y
corner_x, corner_y = (hx - CORNER, hx + 0.01), (-hy - 0.01, -hy + CORNER)
P = report["platform"]
P["pieces"] = {
    "SM_PlataformaEsquina": piece(src, "SM_PlataformaEsquina", corner_x, corner_y, (COLUMN_TOP, TOP), (hx, -hy, 0)),
    "SM_PlataformaColumna": piece(src, "SM_PlataformaColumna", corner_x, corner_y, (FOOT_TOP, COLUMN_TOP), (hx, -hy, FOOT_TOP)),
    "SM_PlataformaPie": piece(src, "SM_PlataformaPie", corner_x, corner_y, (-0.01, FOOT_TOP), (hx, -hy, 0)),
    "SM_PlataformaCostado": piece(src, "SM_PlataformaCostado", (-EDGE_LENGTH / 2, EDGE_LENGTH / 2),
                                  (-hy - 0.01, -hy + EDGE_DEPTH), (COLUMN_TOP, TOP), (0, -hy, 0)),
    "SM_PlataformaPiso": piece(src, "SM_PlataformaPiso", (-DECK / 2, DECK / 2), (-DECK / 2, DECK / 2), (0.85, TOP), (0, 0, 0),
                               ucx=((-DECK / 2, -DECK / 2, 0.88), (DECK / 2, DECK / 2, DECK_TOP))),
}
P.update(half_cm=[round(hx * 100, 1), round(hy * 100, 1)], corner_cm=CORNER * 100, edge_length_cm=EDGE_LENGTH * 100,
         edge_depth_cm=EDGE_DEPTH * 100, deck_cm=DECK * 100, foot_top_cm=FOOT_TOP * 100, column_top_cm=COLUMN_TOP * 100,
         deck_top_cm=DECK_TOP * 100)

src = load(ROOT / "SourceAssets/EscaleraPlataforma/SM_EscaleraPlataforma.fbx")
R = report["rail"]
rail_y, rail_z = (RAIL_LINE - 0.18, RAIL_LINE + 0.10), (RAIL_FLOOR + 0.01, RAIL_FLOOR + 0.95)
R["pieces"] = {
    "SM_BarandaEscaleraTramo": piece(src, "SM_BarandaEscaleraTramo", (-0.47, 0.43), rail_y, rail_z, (-0.02, RAIL_LINE, RAIL_FLOOR),
                                     ucx=((-0.45, -0.06, 0.0), (0.45, 0.06, 0.82))),
    "SM_BarandaEscaleraPoste": piece(src, "SM_BarandaEscaleraPoste", (-0.70, -0.47), rail_y, rail_z, (-0.585, RAIL_LINE, RAIL_FLOOR),
                                     ucx=((-0.115, -0.08, 0.0), (0.115, 0.08, 0.84))),
}
R.update(rail_length_cm=90.0, post_width_cm=23.0, post_spacing_cm=114.0)

(OUT / "plataforma_build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("PLATAFORMA_OK", json.dumps(report))
