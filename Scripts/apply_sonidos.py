"""Editor Python (04/10): musica y sonidos por separado (dos botones al lado del dinero, teclas M y N).

Crea en /Game/FactoryCtyco/Audio dos clases de sonido: SC_Musica (la pone a S_MusicaFabrica) y SC_Sonidos (la pone a
todo otro sonido del proyecto que no tenga clase, y es la clase por defecto del proyecto: Config/DefaultEngine.ini,
[/Script/Engine.AudioSettings] DefaultSoundClassName). AFactoryDemoHUD baja cada una a 0 con su boton.
Informe: Docs/sonidos.json.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.project_dir()).resolve()
AUDIO = "/Game/FactoryCtyco/Audio"
MUSIC = f"{AUDIO}/S_MusicaFabrica"
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
report = {"passed": False}


def sound_class(name):
    path = f"{AUDIO}/{name}"
    if lib.does_asset_exist(path):
        return unreal.load_asset(path)
    made = tools.create_asset(name, AUDIO, unreal.SoundClass, unreal.SoundClassFactory())
    lib.save_loaded_asset(made, False)
    return made


try:
    music_class, sounds_class = sound_class("SC_Musica"), sound_class("SC_Sonidos")
    music = unreal.load_asset(MUSIC)
    if music is None:
        raise RuntimeError(f"No esta {MUSIC}")
    music.set_editor_property("sound_class_object", music_class)
    lib.save_loaded_asset(music, False)
    others = []
    for path in lib.list_assets("/Game/FactoryCtyco", recursive=True):
        data = lib.find_asset_data(path)
        if str(data.asset_class_path.asset_name) not in ("SoundWave", "SoundCue"):
            continue
        sound = unreal.load_asset(path)
        if sound == music:
            continue
        current = sound.get_editor_property("sound_class_object")
        if current is None or current.get_name() == "Master":
            sound.set_editor_property("sound_class_object", sounds_class)
            lib.save_loaded_asset(sound, False)
            others.append(sound.get_name())
    # clase por defecto del proyecto: lo que se importe despues tambien cuenta como sonido
    ini = project / "Config/DefaultEngine.ini"
    text = ini.read_text(encoding="utf-8")
    line = f"DefaultSoundClassName={AUDIO}/SC_Sonidos.SC_Sonidos"
    if line not in text:
        section = "[/Script/Engine.AudioSettings]"
        text = text.replace(section, f"{section}\n{line}", 1) if section in text else text.rstrip() + f"\n\n{section}\n{line}\n"
        ini.write_text(text, encoding="utf-8")
    report.update(passed=True, music=MUSIC, music_class=music_class.get_path_name(),
                  sounds_class=sounds_class.get_path_name(), sounds=sorted(others))
except Exception:
    import traceback
    report["error"] = traceback.format_exc()
    unreal.log_error("[SONIDOS] " + report["error"])
finally:
    (project / "Docs/sonidos.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
