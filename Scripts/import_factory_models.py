"""Import prepared static meshes with explicit glTF PBR channel handling."""
import json
import traceback
from pathlib import Path
import unreal

PROJECT = Path(unreal.Paths.project_dir()).resolve()
SOURCE = PROJECT / "SourceAssets" / "Factory"
ROOT = "/Game/FactoryCtyco/Factory/Models"
assets = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.EditorAssetLibrary
ml = unreal.MaterialEditingLibrary
report = {"passed": False, "assets": []}


def save(asset):
    if not lib.save_loaded_asset(asset, False): raise RuntimeError("Cannot save " + asset.get_path_name())


def texture(source, folder, name, kind):
    path = folder + "/" + name
    tex = unreal.load_asset(path) if lib.does_asset_exist(path) else None
    if tex is None:
        task = unreal.AssetImportTask()
        task.filename = str(source)
        task.destination_path = folder
        task.destination_name = name
        task.automated = True
        task.save = True
        task.replace_existing = False
        assets.import_asset_tasks([task])
        tex = unreal.load_asset(path)
    assert isinstance(tex, unreal.Texture2D), path
    tex.set_editor_property("srgb", kind == "BaseColor")
    tex.set_editor_property("max_texture_size", 2048)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP if kind == "Normal" else
        unreal.TextureCompressionSettings.TC_DEFAULT if kind == "BaseColor" else unreal.TextureCompressionSettings.TC_MASKS)
    if kind == "Normal": tex.set_editor_property("flip_green_channel", True)
    save(tex)
    return tex


def import_one(entry):
    name = entry["id"]
    folder = ROOT + "/" + name
    lib.make_directory(folder)
    path = folder + "/SM_" + name
    mesh = unreal.load_asset(path) if lib.does_asset_exist(path) else None
    if mesh is None:
        options = unreal.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.import_mesh = True
        options.import_as_skeletal = False
        options.import_materials = False
        options.import_textures = False
        options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
        data = options.static_mesh_import_data
        data.combine_meshes = True
        data.auto_generate_collision = False
        data.convert_scene = True
        data.convert_scene_unit = True
        data.generate_lightmap_u_vs = False
        data.build_nanite = False
        data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task = unreal.AssetImportTask()
        task.filename = str(SOURCE / entry["fbx"])
        task.destination_path = folder
        task.destination_name = "SM_" + name
        task.automated = True
        task.save = True
        task.replace_existing = False
        task.factory = unreal.FbxFactory()
        task.options = options
        assets.import_asset_tasks([task])
        mesh = unreal.load_asset(path)
    assert isinstance(mesh, unreal.StaticMesh), path
    textures = {kind: texture(SOURCE / filename, folder, "T_" + name + "_" + kind, kind) for kind, filename in entry["textures"].items()}
    matpath = folder + "/M_" + name
    material = unreal.load_asset(matpath) if lib.does_asset_exist(matpath) else assets.create_asset("M_" + name, folder, unreal.Material, unreal.MaterialFactoryNew())
    ml.delete_all_material_expressions(material)
    material.set_editor_property("two_sided", False)
    samples = {}
    for index, (kind, tex) in enumerate(textures.items()):
        node = ml.create_material_expression(material, unreal.MaterialExpressionTextureSample, -450, index * 210)
        node.set_editor_property("texture", tex)
        node.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind == "Normal" else
            unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if kind == "BaseColor" else unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        samples[kind] = node
    for kind, channel, prop in [
        ("BaseColor", "RGB", unreal.MaterialProperty.MP_BASE_COLOR),
        ("Normal", "RGB", unreal.MaterialProperty.MP_NORMAL),
        ("ORM", "G", unreal.MaterialProperty.MP_ROUGHNESS),
        ("ORM", "B", unreal.MaterialProperty.MP_METALLIC),
        ("AO", "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
    ]:
        if kind in samples: assert ml.connect_material_property(samples[kind], channel, prop)
    if "BaseColor" not in samples:
        node = ml.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, -240, 0)
        node.set_editor_property("constant", unreal.LinearColor(*entry["base_color_factor"]))
        ml.connect_material_property(node, "", unreal.MaterialProperty.MP_BASE_COLOR)
    if "ORM" not in samples:
        for index, (key, prop) in enumerate([("roughness_factor",unreal.MaterialProperty.MP_ROUGHNESS),("metallic_factor",unreal.MaterialProperty.MP_METALLIC)]):
            node=ml.create_material_expression(material,unreal.MaterialExpressionConstant,-240,120+index*100)
            node.set_editor_property("r",entry[key])
            ml.connect_material_property(node,"",prop)
    ml.recompile_material(material)
    save(material)
    mesh.set_material(0, material)
    collision = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    collision.remove_collisions(mesh)
    collision.add_simple_collisions(mesh, unreal.ScriptingCollisionShapeType.BOX)
    save(mesh)
    bounds = mesh.get_bounding_box()
    size = bounds.max - bounds.min
    assert 90 < max(size.x, size.y, size.z) < 110, str(size)
    result = {"id": name, "source": entry["source"], "mesh": mesh.get_path_name(), "material": material.get_path_name(),
        "triangles": mesh.get_num_triangles(0), "dimensions_cm": [size.x,size.y,size.z], "min_cm": [bounds.min.x,bounds.min.y,bounds.min.z],
        "textures": {kind: tex.get_path_name() for kind, tex in textures.items()}}
    print("[FACTORY_IMPORTED] " + json.dumps(result))
    return result


try:
    for entry in json.loads((SOURCE / "manifest.json").read_text())["assets"]:
        report["assets"].append(import_one(entry))
    report["passed"] = True
except Exception:
    report["error"] = traceback.format_exc()
    raise
finally:
    (PROJECT / "Docs/factory_import.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    unreal.log("[FACTORY_IMPORT_RESULT] " + json.dumps(report))
