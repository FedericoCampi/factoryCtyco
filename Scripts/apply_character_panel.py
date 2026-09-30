"""Editor Python: retrato de TecJunior para el panel del personaje (tecla I), 28/09.

Importa SourceAssets/UI/T_RetratoTecJunior.png (Scripts/author_portrait.py) como /Game/FactoryCtyco/UI/T_RetratoTecJunior
(textura de interfaz, sin mips). El HUD (AFactoryDemoHUD) la carga por esa ruta. Con -unattended cierra al terminar.
Informe: Docs/character_panel.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
DEST, NAME = "/Game/FactoryCtyco/UI", "T_RetratoTecJunior"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
report = {"passed": False}
try:
    task = unreal.AssetImportTask()
    task.filename = str(project / "SourceAssets/UI" / f"{NAME}.png")
    task.destination_path = DEST
    task.destination_name = NAME
    task.automated = True
    task.save = True
    task.replace_existing = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = unreal.load_asset(f"{DEST}/{NAME}")
    if not isinstance(tex, unreal.Texture2D):
        raise RuntimeError("No se importo el retrato")
    tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    unreal.EditorAssetLibrary.save_loaded_asset(tex, False)
    report.update(passed=True, texture=tex.get_path_name(), size=[tex.blueprint_get_size_x(), tex.blueprint_get_size_y()])
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[CHARACTER_PANEL] {error}")
finally:
    (project / "Docs/character_panel.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
