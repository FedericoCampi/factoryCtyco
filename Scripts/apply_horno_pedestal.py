"""Editor Python: base de cemento del horno elevable (01/10). Requiere FactoryCtycoRuntime con AFactoryRaisedProp.Pedestal.

Al subir el horno ya no se estira la placa (se veia deformada y con huecos): queda igual bajo el cuerpo y debajo va un
bloque macizo de cemento (cubo del motor, con su caja de colision) del piso a la placa.
- Crea /Game/FactoryCtyco/Environments/HornoFundicion/M_HornoPedestal_Cemento: textura de cemento alineada al mundo
  (WorldAlignedTexture), asi el estiramiento del bloque no se nota.
- Se la pone a `Horno_Fundicion` (PedestalMaterial) y comprueba: lo sube 100 cm, mira que el bloque se vea, choque y
  vaya del piso a la placa, y lo devuelve a su lugar. Sin editor abre el mapa, guarda y cierra.
Informe: Docs/horno_pedestal.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/HornoFundicion"
MAT = "M_HornoPedestal_Cemento"
TEXTURE = "/Game/FactoryCtyco/Environments/Lab1/Concrete_fine_aggregate_and_broad_weathering"
TILE_CM = 150.0    # un mosaico de textura cada 1,5 m
TINT = (0.78, 0.78, 0.76)
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
report = {"passed": False}


def make_material():
    path = f"{DEST}/{MAT}"
    if lib.does_asset_exist(path):
        material = unreal.load_asset(path)
        mel.delete_all_material_expressions(material)
    else:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(MAT, DEST, unreal.Material, unreal.MaterialFactoryNew())
    tex = mel.create_material_expression(material, unreal.MaterialExpressionTextureObject, -900, 0)
    tex.set_editor_property("texture", unreal.load_asset(TEXTURE))
    size = mel.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, -900, 200)
    size.set_editor_property("constant", unreal.LinearColor(TILE_CM, TILE_CM, TILE_CM, 1))
    world = mel.create_material_expression(material, unreal.MaterialExpressionMaterialFunctionCall, -600, 0)
    world.set_editor_property("material_function", unreal.load_asset("/Engine/Functions/Engine_MaterialFunctions01/Texturing/WorldAlignedTexture"))
    mel.connect_material_expressions(tex, "", world, "TextureObject")
    mel.connect_material_expressions(size, "", world, "TextureSize")
    tint = mel.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, -600, 250)
    tint.set_editor_property("constant", unreal.LinearColor(*TINT, 1))
    mul = mel.create_material_expression(material, unreal.MaterialExpressionMultiply, -300, 0)
    mel.connect_material_expressions(world, "XYZ Texture", mul, "A")
    mel.connect_material_expressions(tint, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = mel.create_material_expression(material, unreal.MaterialExpressionConstant, -300, 250)
    rough.set_editor_property("r", 0.9)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(material)
    lib.save_loaded_asset(material, False)
    return material


def check(horno):
    """Lo sube 100 cm, mira el bloque y lo deja como estaba."""
    loc = horno.get_actor_location()
    block = horno.get_editor_property("pedestal")
    plate = horno.get_editor_property("base")
    out = {"z": round(loc.z, 1), "elevation_antes": round(horno.get_editor_property("elevation"), 1)}
    horno.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + 100), False, False)
    horno.refresh()
    bo, be, _ = unreal.SystemLibrary.get_component_bounds(block)
    po, pe, _ = unreal.SystemLibrary.get_component_bounds(plate)
    out.update(elevation_subido=round(horno.get_editor_property("elevation"), 1),
               bloque_visible=block.is_visible(), bloque_colision=str(block.get_collision_enabled()),
               bloque_z=[round(bo.z - be.z, 1), round(bo.z + be.z, 1)],
               placa_abajo_z=round(po.z - pe.z, 1),
               placa_escala=list(plate.get_editor_property("relative_scale3d").to_tuple()),
               bloque_xy_cm=[round(be.x * 2), round(be.y * 2)], placa_xy_cm=[round(pe.x * 2), round(pe.y * 2)])
    horno.set_actor_location(loc, False, False)
    horno.refresh()
    out["elevation_vuelto"] = round(horno.get_editor_property("elevation"), 1)
    floor = loc.z - out["elevation_antes"]
    out["ok"] = (out["bloque_visible"] and "QUERY_AND_PHYSICS" in out["bloque_colision"] and abs(out["bloque_z"][0] - floor) < 2
                 and abs(out["bloque_z"][1] - (loc.z + 100)) < 2 and out["placa_escala"] == [1.0, 1.0, 1.0])
    return out


try:
    if HEADLESS:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/FactoryCtyco/Maps/L_FactoryDemo")
    material = make_material()
    horno = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label() == "Horno_Fundicion"]
    if len(horno) != 1 or not isinstance(horno[0], unreal.FactoryRaisedProp):
        raise RuntimeError("Se esperaba un Horno_Fundicion FactoryRaisedProp")
    horno = horno[0]
    horno.modify()
    horno.set_editor_property("pedestal_material", material)
    horno.refresh()
    report["check"] = check(horno)
    report["pedestal_mesh"] = str(horno.get_editor_property("pedestal_mesh").get_path_name())
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError("No se pudo guardar el nivel")
    report["passed"] = report["check"]["ok"]
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[HORNO_PEDESTAL] " + report["error"])
finally:
    (project / "Docs/horno_pedestal.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
