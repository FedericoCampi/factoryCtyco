"""Editor Python: sonidos de las cajas y de la mision (28/09).

Importa SourceAssets/Audio/caja_agarrar.wav, caja_soltar.wav y mision_completa.wav (make_ui_sounds.py) como
/Game/FactoryCtyco/Audio/S_CajaAgarrar, S_CajaSoltar y S_MisionCompleta. El codigo los carga por esa ruta
(UFactoryCarryComponent y UFactoryMissionSubsystem). Con -unattended cierra al terminar. Informe: Docs/mission_sounds.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
AUDIO = "/Game/FactoryCtyco/Audio"
HEADLESS = "-unattended" in unreal.SystemLibrary.get_command_line().lower()
report = {"passed": False, "sounds": {}}
try:
    for wav, name in (("caja_agarrar", "S_CajaAgarrar"), ("caja_soltar", "S_CajaSoltar"), ("mision_completa", "S_MisionCompleta")):
        task = unreal.AssetImportTask()
        task.filename = str(project / "SourceAssets/Audio" / f"{wav}.wav")
        task.destination_path = AUDIO
        task.destination_name = name
        task.automated = True
        task.save = True
        task.replace_existing = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        sound = unreal.load_asset(f"{AUDIO}/{name}")
        if not isinstance(sound, unreal.SoundWave):
            raise RuntimeError(f"No se importo {name}")
        unreal.EditorAssetLibrary.save_loaded_asset(sound, False)
        report["sounds"][name] = round(sound.get_editor_property("duration"), 2)
    report["passed"] = True
except Exception as error:
    report["error"] = str(error)
    unreal.log_error(f"[MISSION_SOUNDS] {error}")
finally:
    (project / "Docs/mission_sounds.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if HEADLESS:
        unreal.SystemLibrary.quit_editor()
