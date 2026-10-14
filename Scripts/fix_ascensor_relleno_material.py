"""Editor Python (04/10): el relleno de las paredes del ascensor (SM_Ascensor2Relleno) quedo sin material (se veia la
grilla gris de Unreal). Crea M_Ascensor2Relleno (el color de los paneles de la cabina, de elevator_paneles.json) y se
lo pone a la malla. Informe: Docs/ascensor_relleno_material.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/FactoryCtyco/Environments/Ascensor2"
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
report = {"passed": False}
try:
    color = json.loads((project / "SourceAssets/Ascensor2/elevator_paneles.json").read_text(encoding="utf-8"))["color_linear"]
    path = f"{DEST}/M_Ascensor2Relleno"
    mat = unreal.load_asset(path) if lib.does_asset_exist(path) else None
    if not isinstance(mat, unreal.Material):
        if lib.does_asset_exist(path):
            lib.delete_asset(path)
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_Ascensor2Relleno", DEST, unreal.Material, unreal.MaterialFactoryNew())
    base = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
    base.set_editor_property("constant", unreal.LinearColor(*color, 1.0))
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 200)
    rough.set_editor_property("r", 0.6)
    metal = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 300)
    metal.set_editor_property("r", 0.3)
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
    mel.recompile_material(mat)
    lib.save_loaded_asset(mat, False)
    mesh = unreal.load_asset(f"{DEST}/SM_Ascensor2Relleno")
    mesh.modify()
    mesh.set_material(0, mat)
    lib.save_loaded_asset(mesh, False)
    report.update(passed=True, color=color, material=mat.get_path_name())
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
(project / "Docs/ascensor_relleno_material.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
