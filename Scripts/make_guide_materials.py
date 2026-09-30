"""Materiales de la guía y del remarcado de clickeables (29/09).

- /Game/FactoryCtyco/UI/M_FlechaGuia: flecha grande de la guía (AFactoryGuide). Unlit, parámetros Color y Brillo.
- /Game/FactoryCtyco/UI/M_ContornoClic: post-proceso del contorno naranja sobre lo clickeable bajo el mouse
  (UFactoryHoverComponent): dibuja alrededor de las mallas con custom depth. Parámetros Color y Ancho (px).
Los borra y los vuelve a crear. Informe: Docs/guide_materials.json.
"""
import json
from pathlib import Path
import unreal

out = {}


def make_arrow():
    path = "/Game/FactoryCtyco/UI/M_FlechaGuia"
    lib = unreal.MaterialEditingLibrary
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    m = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_FlechaGuia", "/Game/FactoryCtyco/UI", unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    color = lib.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -900, 0)
    color.set_editor_property("parameter_name", "Color")
    color.set_editor_property("default_value", unreal.LinearColor(1.0, 0.42, 0.04, 1.0))
    glow = lib.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -900, 200)
    glow.set_editor_property("parameter_name", "Brillo")
    glow.set_editor_property("default_value", 1.0)
    fres = lib.create_material_expression(m, unreal.MaterialExpressionFresnel, -900, 350)
    fres.set_editor_property("exponent", 2.5)
    # Shade = 1 - 0.45 * fresnel: darker toward the silhouette so the cone and shaft read as 3D.
    mul_f = lib.create_material_expression(m, unreal.MaterialExpressionMultiply, -650, 350)
    mul_f.set_editor_property("const_b", 0.45)
    lib.connect_material_expressions(fres, "", mul_f, "A")
    one_minus = lib.create_material_expression(m, unreal.MaterialExpressionOneMinus, -450, 350)
    lib.connect_material_expressions(mul_f, "", one_minus, "")
    m1 = lib.create_material_expression(m, unreal.MaterialExpressionMultiply, -450, 100)
    lib.connect_material_expressions(color, "", m1, "A")
    lib.connect_material_expressions(glow, "", m1, "B")
    m2 = lib.create_material_expression(m, unreal.MaterialExpressionMultiply, -250, 150)
    lib.connect_material_expressions(m1, "", m2, "A")
    lib.connect_material_expressions(one_minus, "", m2, "B")
    lib.connect_material_property(m2, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(m)
    unreal.EditorAssetLibrary.save_asset(path)
    out["M_FlechaGuia"] = unreal.EditorAssetLibrary.does_asset_exist(path)


def make_outline():
    path = "/Game/FactoryCtyco/UI/M_ContornoClic"
    lib = unreal.MaterialEditingLibrary
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    m = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_ContornoClic", "/Game/FactoryCtyco/UI", unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("material_domain", unreal.MaterialDomain.MD_POST_PROCESS)
    m.set_editor_property("blendable_location", unreal.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
    depth = lib.create_material_expression(m, unreal.MaterialExpressionSceneTexture, -900, 0)
    depth.set_editor_property("scene_texture_id", unreal.SceneTextureId.PPI_CUSTOM_DEPTH)
    scene = lib.create_material_expression(m, unreal.MaterialExpressionSceneTexture, -900, 250)
    scene.set_editor_property("scene_texture_id", unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    color = lib.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -900, 450)
    color.set_editor_property("parameter_name", "Color")
    color.set_editor_property("default_value", unreal.LinearColor(1.0, 0.55, 0.08, 1.0))
    width = lib.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -900, 600)
    width.set_editor_property("parameter_name", "Ancho")
    width.set_editor_property("default_value", 3.0)
    custom = lib.create_material_expression(m, unreal.MaterialExpressionCustom, -500, 200)
    custom.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    custom.set_editor_property("description", "Contorno")
    code = r"""
    // Outline around meshes that render custom depth (the hovered clickable), plus a faint tint on them.
    float2 UV = GetDefaultSceneTextureUV(Parameters, 13);
    float Here = SceneTextureLookup(UV, 13, false).r;
    bool Inside = Here < 1e6;
    float Edge = 0;
    const float2 Dirs[8] = { float2(1,0), float2(-1,0), float2(0,1), float2(0,-1), float2(.707,.707), float2(-.707,.707), float2(.707,-.707), float2(-.707,-.707) };
    for (int I = 0; I < 8; ++I)
    {
        float Far = SceneTextureLookup(UV + Dirs[I] * InvSize * Width, 13, false).r;
        float Near = SceneTextureLookup(UV + Dirs[I] * InvSize * Width * .5, 13, false).r;
        Edge = max(Edge, max(Far < 1e6 ? 1.0 : 0.0, Near < 1e6 ? 1.0 : 0.0));
    }
    float3 Result = Scene;
    if (Inside) Result = lerp(Scene, Tint, .12);
    else Result = lerp(Scene, Tint, Edge);
    return Result;
    """
    custom.set_editor_property("code", code)
    inputs = []
    for name in ("InvSize", "Scene", "Tint", "Width"):
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", name)
        inputs.append(ci)
    custom.set_editor_property("inputs", inputs)
    lib.connect_material_expressions(depth, "InvSize", custom, "InvSize")
    lib.connect_material_expressions(scene, "Color", custom, "Scene")
    lib.connect_material_expressions(color, "", custom, "Tint")
    lib.connect_material_expressions(width, "", custom, "Width")
    lib.connect_material_property(custom, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(m)
    unreal.EditorAssetLibrary.save_asset(path)
    out["domain"] = str(m.get_editor_property("material_domain"))
    out["M_ContornoClic"] = unreal.EditorAssetLibrary.does_asset_exist(path)


make_arrow()
make_outline()
(Path(unreal.Paths.project_dir()).resolve() / "Docs/guide_materials.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
unreal.log(f"[GUIDE_MATERIALS] {out}")
