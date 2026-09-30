"""Prepare game meshes and original PBR textures, preserving the delivered GLBs.

Run with Blender --background --python Scripts/prepare_factory_models.py.
Neutral source IDs do not assume a gameplay role for ambiguously named files.
"""
import hashlib
import json
import shutil
import struct
from pathlib import Path
import bpy
from mathutils import Vector

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\Users\Usuario\Desktop\3D assets\GLBs\robotAutomation")
DEST = PROJECT / "SourceAssets" / "Factory"
FILES = [
    ("Trituradora", "trituradora-optimizada-complete.glb", 100000),
    ("Fundicion", "fundicion.glb", 90000),
    ("Deposito", "deposito.glb", 60000),
    ("Chatarra", "frag_metalicos.glb", 35000),
    ("ArchivoCintaRecta", "cinta_recta.glb", 22000),
    ("ArchivoFragTriturado", "frag_triturado.glb", 70000),
    ("ArchivoAlmacenamiento", "frag_triturado_almacenamiento.glb", 18000),
    ("ArchivoDepositoTriturado", "deposito_triturado.glb", 14000),
]


def glb_parts(path):
    with path.open("rb") as stream:
        magic, version, length = struct.unpack("<III", stream.read(12))
        assert magic == 0x46546C67 and version == 2 and length == path.stat().st_size
        size, kind = struct.unpack("<II", stream.read(8))
        assert kind == 0x4E4F534A
        document = json.loads(stream.read(size))
        size, kind = struct.unpack("<II", stream.read(8))
        assert kind == 0x004E4942
        return document, stream.read(size)


def prepare(asset_id, filename, target):
    path = SOURCE / filename
    folder = DEST / asset_id
    folder.mkdir(parents=True, exist_ok=True)
    originals = DEST / "Originals"
    originals.mkdir(exist_ok=True)
    copy = originals / filename
    if not copy.exists(): shutil.copy2(path, copy)
    doc, binary = glb_parts(path)
    material = doc["materials"][0]
    pbr = material.get("pbrMetallicRoughness", {})
    textures = {}
    for name, texture in [
        ("BaseColor", pbr.get("baseColorTexture")),
        ("ORM", pbr.get("metallicRoughnessTexture")),
        ("Normal", material.get("normalTexture")),
        ("AO", material.get("occlusionTexture")),
    ]:
        if texture is None: continue
        image = doc["images"][doc["textures"][texture["index"]]["source"]]
        view = doc["bufferViews"][image["bufferView"]]
        extension = ".jpg" if image["mimeType"] == "image/jpeg" else ".png"
        destination = folder / ("T_" + asset_id + "_" + name + extension)
        begin = view.get("byteOffset", 0)
        destination.write_bytes(binary[begin:begin+view["byteLength"]])
        textures[name] = str(destination.relative_to(DEST)).replace("\\", "/")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects: obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1: bpy.ops.object.join()
    obj = bpy.context.object
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    low = Vector(tuple(min(vertex.co[axis] for vertex in obj.data.vertices) for axis in range(3)))
    high = Vector(tuple(max(vertex.co[axis] for vertex in obj.data.vertices) for axis in range(3)))
    offset = Vector(((low.x+high.x)/2, (low.y+high.y)/2, low.z))
    for vertex in obj.data.vertices: vertex.co -= offset
    obj.data.calc_loop_triangles()
    before = len(obj.data.loop_triangles)
    modifier = obj.modifiers.new("DemoMeshBudget", "DECIMATE")
    modifier.ratio = min(1.0, target / before)
    modifier.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.name = "SM_" + asset_id
    obj.data.name = obj.name
    obj.data.calc_loop_triangles()
    after = len(obj.data.loop_triangles)
    obj.data.materials.clear()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    fbx = folder / (obj.name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={"MESH"},
        axis_forward="-Y", axis_up="Z", apply_unit_scale=True, bake_space_transform=False,
        mesh_smooth_type="FACE", use_mesh_modifiers=True, add_leaf_bones=False,
        path_mode="AUTO", use_custom_props=False)
    result = dict(id=asset_id, source=filename, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        triangles_original=before, triangles_game=after, textures=textures,
        fbx=str(fbx.relative_to(DEST)).replace("\\", "/"), dimensions_metres=list(high-low),
        base_color_factor=pbr.get("baseColorFactor", [1,1,1,1]),
        metallic_factor=pbr.get("metallicFactor", 1), roughness_factor=pbr.get("roughnessFactor", 1))
    print("[FACTORY_PREPARED] " + json.dumps(result), flush=True)
    return result


DEST.mkdir(parents=True, exist_ok=True)
report = {"originals_preserved": True, "assets": []}
for entry in FILES:
    report["assets"].append(prepare(*entry))
    (DEST / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("[FACTORY_PREPARATION_COMPLETE]", flush=True)
