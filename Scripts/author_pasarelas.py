"""Blender: las dos pasarelas del usuario (3D assets/GLBs) para Unreal (03/10).

- Pasarela industrial modular con barandillas de malla-complete.glb -> SM_PasarelaRecta
- Pasarela en L con barandillas interiores-complete.glb               -> SM_PasarelaL

Los GLB vienen normalizados (1 m en su lado mayor, ~700 000 triangulos, una malla con texturas de 2-4K). Cada una se
escala para que la baranda quede a RAIL_M sobre el piso de la pasarela (escala real, y las dos parejas entre si): la
recta queda de ~10 x 2,5 m y la L de ~5 x 5 m, con el piso a ~0,4 m. El piso es la cara hacia arriba de mas area.
Origen al centro, abajo de todo; se reduce a ~150 000 triangulos. Sin caja de colision: en Unreal chocan con su propia
malla (complex as simple), asi se camina arriba, como la escalera con plataforma.
Salida: SourceAssets/Pasarelas/<SM>.fbx y pasarelas_build.json.

blender -b --factory-startup -P Scripts/author_pasarelas.py
"""
import collections
import json
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

GLBS = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs")
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Pasarelas"
MODELS = {
    "SM_PasarelaRecta": "Pasarela industrial modular con barandillas de malla-complete.glb",
    "SM_PasarelaL": "Pasarela en L con barandillas interiores-complete.glb",
}
RAIL_M = 1.0          # alto de la baranda sobre el piso de la pasarela
TARGET_TRIS = 150000

OUT.mkdir(parents=True, exist_ok=True)
report = {}
for name, glb in MODELS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(GLBS / glb))
    o = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    o.parent = None
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for extra in [x for x in bpy.context.scene.objects if x is not o]:
        bpy.data.objects.remove(extra)
    tris_in = sum(len(p.vertices) - 2 for p in o.data.polygons)

    co = [v.co for v in o.data.vertices]
    lo = Vector([min(c[i] for c in co) for i in range(3)])
    hi = Vector([max(c[i] for c in co) for i in range(3)])
    # el piso: la altura con mas area mirando para arriba
    up = collections.Counter()
    for p in o.data.polygons:
        if p.normal.z > 0.95:
            up[round(p.center.z, 3)] += p.area
    deck = max(up.items(), key=lambda kv: kv[1])[0]
    scale = RAIL_M / (hi.z - deck)
    o.data.transform(Matrix.Scale(scale, 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    dec = o.modifiers.new("Decimate", "DECIMATE")
    dec.ratio = min(1.0, TARGET_TRIS / tris_in)
    bpy.ops.object.modifier_apply(modifier=dec.name)
    o.name = o.data.name = name

    bpy.ops.export_scene.fbx(filepath=str(OUT / f"{name}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                             path_mode="COPY", embed_textures=True, axis_forward="-Y", axis_up="Z")
    report[name] = {"source": glb, "scale": round(scale, 3),
                    "size_m": [round((hi[i] - lo[i]) * scale, 3) for i in range(3)],
                    "deck_m": round((deck - lo.z) * scale, 3),
                    "triangles_in": tris_in, "triangles": sum(len(p.vertices) - 2 for p in o.data.polygons),
                    "collision": "complex"}

(OUT / "pasarelas_build.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
print("PASARELAS_OK", json.dumps(report))
