"""Blender: los cuatro modelos del usuario para la escena del despacho (07/10).

- Maquina Industrial de Flejado Amarilla y Gris-complete.glb     -> SM_Flejadora
- Escaner industrial de rayos X con tunel rojo-complete.glb       -> SM_EscanerRayosX
- Pasarela industrial con barandillas verdes-complete.glb         -> SM_PasarelaVerde
- Pasarela industrial elevada en L-complete.glb                   -> SM_PasarelaLElevada
- Tunel industrial de rechazo galvanizado-complete.glb (07/10)    -> SM_TunelRechazo
- Plataforma industrial de acero en 3D (1)-complete.glb (07/10)   -> SM_PlataformaIndustrial (va por piezas, a la fabrica)
- Sistema industrial de tolvas gemelas CUARZO y ARENA-complete.glb (08/10) -> SM_TolvasGemelas (patio de los muelles)

Los GLB vienen normalizados (1 m en su lado mayor, ~700 000 triangulos, una malla con texturas de 2-4K). Las maquinas
se escalan a su alto real (HEIGHT_M); las pasarelas, como author_pasarelas.py, para que la baranda quede a RAIL_M sobre
su piso (la cara hacia arriba de mas area). Origen al centro, abajo de todo; se reducen los triangulos y las texturas
bajan a TEXTURE. Sin caja de colision: en Unreal chocan con su propia malla (complex as simple).
Salida: SourceAssets/DespachoEquipos/<SM>.fbx y despacho_equipos_build.json.

blender -b --factory-startup -P Scripts/author_despacho_equipos.py [-- SM_Nombre ...]   (solo esos)
"""
import collections
import json
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

GLBS = Path(r"C:/Users/Usuario/Desktop/3D assets/GLBs")
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/DespachoEquipos"
# nombre: (glb, alto total en m o None si es pasarela, triangulos)
MODELS = {
    "SM_Flejadora": ("Máquina Industrial de Flejado Amarilla y Gris-complete.glb", 1.75, 100000),
    "SM_EscanerRayosX": ("Escáner industrial de rayos X con túnel rojo-complete.glb", 1.6, 100000),
    "SM_PasarelaVerde": ("Pasarela industrial con barandillas verdes-complete.glb", None, 150000),
    "SM_PasarelaLElevada": ("Pasarela industrial elevada en L-complete.glb", None, 150000),
    "SM_TunelRechazo": ("Túnel industrial de rechazo galvanizado-complete.glb", 2.4, 100000),
    "SM_PlataformaIndustrial": ("Plataforma industrial de acero en 3D (1)-complete.glb", 1.0, 150000),   # 07/10, fabrica: 2,5 x 2,5 m
    "SM_TolvasGemelas": ("Sistema industrial de tolvas gemelas CUARZO y ARENA-complete.glb", 4.0, 150000),   # 08/10: ~6 x 2,7 m
}
ONLY = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(MODELS)
RAIL_M = 1.0          # alto de la baranda sobre el piso de la pasarela
TEXTURE = 2048

OUT.mkdir(parents=True, exist_ok=True)
build = OUT / "despacho_equipos_build.json"
report = json.loads(build.read_text(encoding="utf-8")) if build.exists() else {}
for name, (glb, height, tris) in MODELS.items():
    if name not in ONLY:
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(GLBS / glb))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    for extra in [x for x in bpy.context.scene.objects if x is not o]:
        bpy.data.objects.remove(extra)
    tris_in = sum(len(p.vertices) - 2 for p in o.data.polygons)

    co = [v.co for v in o.data.vertices]
    lo = Vector([min(c[i] for c in co) for i in range(3)])
    hi = Vector([max(c[i] for c in co) for i in range(3)])
    deck = None
    if height is None:
        # el piso: la altura con mas area mirando para arriba
        up = collections.Counter()
        for p in o.data.polygons:
            if p.normal.z > 0.95:
                up[round(p.center.z, 3)] += p.area
        deck = max(up.items(), key=lambda kv: kv[1])[0]
        scale = RAIL_M / (hi.z - deck)
    else:
        scale = height / (hi.z - lo.z)
    o.data.transform(Matrix.Scale(scale, 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    dec = o.modifiers.new("Decimate", "DECIMATE")
    dec.ratio = min(1.0, tris / tris_in)
    dec.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=dec.name)
    o.name = o.data.name = name
    for image in bpy.data.images:
        if image.size[0] > TEXTURE:
            image.scale(TEXTURE, TEXTURE)
            image.pack()

    bpy.ops.export_scene.fbx(filepath=str(OUT / f"{name}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                             path_mode="COPY", embed_textures=True, axis_forward="-Y", axis_up="Z")
    report[name] = {"source": glb, "scale": round(scale, 3),
                    "size_m": [round((hi[i] - lo[i]) * scale, 3) for i in range(3)],
                    "deck_m": round((deck - lo.z) * scale, 3) if deck is not None else None,
                    "triangles_in": tris_in, "triangles": sum(len(p.vertices) - 2 for p in o.data.polygons),
                    "collision": "complex"}

(OUT / "despacho_equipos_build.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
print("DESPACHO_EQUIPOS_OK", json.dumps(report, ensure_ascii=False))
